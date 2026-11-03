"""One bound 14 worker and one shared snapshot source for PC/HDMI. No PL programming."""
import hashlib
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from display_snapshot import DisplaySnapshot
from hdmi_renderer import PAGES
from process_renderer import ProcessRenderer
from renderer_present import present_snapshot


class SnapshotStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.latest = None

    def publish(self, snapshot):
        with self.lock:
            self.latest = snapshot

    def view(self):
        with self.lock:
            snapshot = self.latest
        return snapshot.view() if snapshot else dict(status='WAITING', metrics={}, reason='等待手动捕获共享快照')


class LiveUI:
    def __init__(self, root, out, driver, record, iteration_log, boot, load_sha):
        import sys
        self.root, self.out, self.driver, self.record, self.iteration_log = root, out, driver, record, iteration_log
        self.store = SnapshotStore()
        self.stop = threading.Event()
        self.seq, self.capture_count = 0, 0
        sys.path.insert(0, str(root / 'reader'))
        sys.path.insert(0, str(root / 'ui14_service'))
        from ui14_bound_worker import DisplayState, hardware
        from ui_physical import load_portable
        from platform_guard import qualify_explicit_platform
        from lab07_mmio_impl import PynqMMIOAdapter
        from lab07_session import Session
        from lab07_unified_reader import UnifiedReader
        from lab07_feature_reader import ReaderConfig
        qualified = qualify_explicit_platform()
        if not qualified['explicit_platform_qualified']:
            raise RuntimeError('Accepted explicit-copy environment identity changed')
        self.record('PLATFORM_IDENTITY', qualification=qualified)
        models = Path('/home/xilinx/jupyter_notebooks/lab07_bai_integration/physical_portable_v11_ge8e6qs4')
        model = load_portable(models, 'logistic_regression')
        font = Path('/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf')
        if not font.is_file():
            raise RuntimeError('Confirmed Chinese font missing')
        self.renderer = ProcessRenderer(font, out / 'render_worker.stderr.log')
        self.record('RASTER_PROCESS_READY', identity=self.renderer.identity,
                    reader_in_raster_process=False, model_in_raster_process=False)
        epoch = (str(uuid.uuid4()), boot, 1)
        managed = SimpleNamespace(token=lambda: epoch,
                                  metadata=lambda: dict(session_id=epoch[0], boot_id=boot, reload_generation=1))
        control = PynqMMIOAdapter()
        data = PynqMMIOAdapter(0x43C10000, 0x2000, control, True, False)
        reader = UnifiedReader(control, data, Session(managed), ReaderConfig(required_channels=()))
        info = reader.preflight()
        if not info.raw_supported:
            raise RuntimeError('ABI2.1 Raw capability missing')
        self.state = DisplayState('hardware')
        args = SimpleNamespace(reader_dir=str(root / 'reader'), bound_reader=reader, bound_control=control,
                 bound_session=reader.session, bound_managed=managed, bound_info=info, bound_model=model,
                 release_audit=dict(bit_sha256='45197bb23c05e8f8c73e4cbbced7c12ce66599a4b54a407d77fefd94a08820f4',
                                    hwh_sha256='54980f765756f8dc64ade54af7969c7b96054c816a31d88ab9d2c07fbce05b6f',
                                    load_log_sha256=load_sha),
                 physical_model_dir=models, model_algorithm='logistic_regression', raw=True, harmonic=True,
                 events=True, baseline=str(root / 'ui14_service/NOMINAL_BASELINE_001.json'),
                 baseline_ch2=str(root / 'ui14_service/NOMINAL_BASELINE_CH2_20261103.json'),
                 event_log=str(out / 'event_results.jsonl'), model_log=str(out / 'model_results.jsonl'))
        self.worker_output = (out / 'ui_worker.log').open('x', encoding='utf-8', buffering=1)
        def worker_print(*values, **options):
            text = ' '.join(str(v) for v in values)
            self.worker_output.write(text + '\n')
            if text.startswith(('HARDWARE STOP:', 'EVENT_MONITOR_STOPPED:')):
                print(text, flush=True)
        args.bound_print = worker_print
        def run_original_worker():
            import os
            try:
                if hasattr(os, 'sched_getaffinity'):
                    available = os.sched_getaffinity(0)
                    if len(available) > 1:
                        os.sched_setaffinity(0, {min(available)})
                    worker_print('READER_CPU_AFFINITY =', sorted(os.sched_getaffinity(0)))
            except Exception as error:
                self.state.fail(str(error))
                worker_print('HARDWARE STOP:', str(error))
                return
            hardware(self.state, self.stop, args)
        self.worker = threading.Thread(target=run_original_worker, daemon=True)
        page = (root / 'ui14_service/index.html').read_bytes()
        store = self.store
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/api/state':
                    body = json.dumps(store.view(), ensure_ascii=False, allow_nan=False).encode()
                    kind = 'application/json; charset=utf-8'
                elif self.path in ('/', '/index.html'):
                    body, kind = page, 'text/html; charset=utf-8'
                else:
                    self.send_error(404); return
                self.send_response(200)
                self.send_header('Content-Type', kind)
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers(); self.wfile.write(body)
            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(('192.168.2.99', 8765), Handler)
        self.http = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.record('SINGLE_CHAIN_CREATED', reader_epoch=epoch, model_version=model.original_hash,
                    model_scope='TRAINING_ONLY', worker_build='20261103_event_fastpath_v1_BOUND',
                    snapshot_source='ONE_SHARED_STORE', http='http://192.168.2.99:8765')

    def start(self):
        self.worker.start(); self.http.start()
        self.record('LIVE_UI_READY', mode='STAGE2_MANUAL_SNAPSHOTS', automatic_refresh=False)

    def capture(self, page, *, automatic=False):
        if page not in PAGES:
            raise ValueError('Unknown view')
        view = self.state.view()
        if view.get('status') == 'ERROR':
            raise RuntimeError('Existing acquisition chain failed: ' + str(view.get('reason')))
        if view.get('status') != 'LIVE':
            self.record('CAPTURE_WAITING', status=view.get('status'), reason=view.get('reason'))
            return
        self.capture_count += 1
        wave = view.get('waveform') or {}
        view['shared_snapshot_id'] = self.capture_count
        view['identity'] = dict(feature_frame_id=view.get('frame_id'), raw_frame_id=wave.get('frame_id'),
                               reader_epoch=wave.get('epoch'), association=wave.get('association'),
                               frame_retire_generation='%032x' % self.driver.fr.generation)
        snapshot = DisplaySnapshot.capture(view, source_note='真实采集快照 · ' + ('自动刷新' if automatic else '手动更新'))
        dest = self.out / ('snapshot_%04d.json' % self.capture_count)
        dest.write_text(snapshot.payload, encoding='utf-8')
        self.seq += 1
        before_timing = view.get('worker_timing') or {}
        pipeline_started = time.monotonic()
        result = present_snapshot(self.driver, self.renderer, snapshot, page, self.seq,
                                  self.record, self.iteration_log)
        after_view = self.state.view()
        after_timing = after_view.get('worker_timing') or {}
        self.record('RENDER_PIPELINE_TIMING', elapsed=time.monotonic()-pipeline_started,
                    raster=getattr(self.renderer, 'last_timing', None),
                    raw_loop_before=before_timing.get('seq'), raw_loop_after=after_timing.get('seq'),
                    drop_before=before_timing.get('drop_after'), drop_after=after_timing.get('drop_after'),
                    event_error_after=after_timing.get('event_error'))
        self.store.publish(snapshot)
        self.record('SHARED_SNAPSHOT_PRESENTED', snapshot_id=self.capture_count, page=page,
                    seq=self.seq, identity=view['identity'], snapshot_path=str(dest),
                    snapshot_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
                    event_status=view.get('event', {}).get('status'),
                    current_event_status=after_view.get('event', {}).get('status'),
                    CH2_event_status=(view.get('event', {}).get('channels') or {}).get('CH2', {}).get('status'),
                    model_status=view.get('harmonic', {}).get('physical_model', {}).get('input_status'),
                    model_scope='TRAINING_ONLY', ack_after_status=result['ack_after_status'])

    def shutdown_acquisition(self):
        self.stop.set()
        if self.worker.is_alive():
            self.worker.join(timeout=3)
        if self.http.is_alive():
            self.server.shutdown()
        self.server.server_close()
        self.renderer.close()
        self.worker_output.close()
