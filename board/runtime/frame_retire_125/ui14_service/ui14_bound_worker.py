"""Lab07 feature display. HTTP clients never access MMIO; one worker owns reader."""
import argparse
import asyncio
import json
import math
import signal
from pathlib import Path
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UI_BUILD = '20261103_event_fastpath_v1'


def clear_model(result, reason):
    result = dict(result)
    if isinstance(result.get('physical_model'), dict):
        result['physical_model'] = dict(result['physical_model'],
            input_status='REJECTED', class_id=None, model_prediction=None,
            probabilities=None, error=reason)
    return result


def invalidate_event(event, status, reason):
    result = dict(event,status=status,rms_pu=None,active=None,reason=reason)
    if isinstance(event.get('channels'),dict):
        result['channels'] = {ch:dict(v,status=status,rms_pu=None,active=None,reason=reason)
                              for ch,v in event['channels'].items()}
    return result


class DisplayState:
    def __init__(self, source, clock=time.monotonic):
        self.source, self.clock = source, clock
        self.lock = threading.Lock()
        self.data = dict(status='WAITING', metrics={}, reason='等待新帧')
        self.worker_timing = None
        self.updated = None
        self.waveform = dict(status='WAITING', reason='Raw 未启用或等待新帧')
        self.wave_updated = None
        self.event = dict(status='DISABLED', reason='事件检测未启用')
        self.event_updated = None
        self.harmonic = dict(status='DISABLED', reason='B六维输入适配未启用')
        self.harmonic_updated = None

    def publish_timing(self, timing):
        with self.lock:
            self.worker_timing = dict(timing)

    def publish_harmonic(self, result):
        with self.lock:
            self.harmonic = result if result.get('input_status') == 'accepted' else clear_model(result, result.get('error_code', 'ADAPTER_REJECTED'))
            self.harmonic_updated = self.clock()

    def publish_event(self, event):
        with self.lock:
            self.event = event
            self.event_updated = self.clock()

    def publish_waveform(self, frame):
        d = frame.descriptor
        if (frame.ack_result != 1 or d.sample_count != 2048 or d.frame_bytes != 8192
                or d.channel_mask != 3 or d.format != 65537
                or any(a.shape != (2048,) or str(a.dtype) != 'int16'
                       for a in (frame.CH1, frame.CH2))):
            raise ValueError('Waveform requires complete int16[2048] copies and confirmed ACK')
        with self.lock:
            self.waveform = dict(status='LIVE', frame_id=d.frame_id, token=d.token,
                epoch=frame.epoch, association=frame.association, fs_nominal_hz=10000,
                sample_count=2048, CH1=frame.CH1.tolist(), CH2=frame.CH2.tolist(),
                drop_diagnostics=frame.drop_diagnostics)
            self.wave_updated = self.clock()

    def publish(self, result):
        with self.lock:
            if result.get('stale'):
                return  # A repeated seq never refreshes the age of old values.
            metrics = {}
            good = (result.get('status') == 'CONSISTENT' and result.get('consistent')
                    and result.get('snapshot_valid'))
            if good:
                for name, value in result.get('basic', {}).items():
                    metrics[name] = value.get('value') if value.get('valid') else None
                for channel in result.get('channels', {}).values():
                    for name, value in channel.get('features', {}).items():
                        key = 'percent' if '_THD_ODD_' in name else 'value'
                        metrics[name] = value.get(key) if channel.get('consumable') else None
            self.data = dict(status='LIVE' if good else 'INVALID', metrics=metrics,
                             frame_id=result.get('frame_id'), seq=result.get('seq_after'),
                             reason='; '.join(result.get('reasons', [])))
            self.updated = self.clock()

    def fail(self, reason):
        with self.lock:
            self.data = dict(status='ERROR', metrics={}, reason=str(reason))
            self.waveform = dict(status='ERROR', reason=str(reason))
            self.event = invalidate_event(self.event, 'ERROR', str(reason))
            self.harmonic = dict(self.harmonic, status='invalid_input', input_status='rejected',
                error_code='HARDWARE_STOP', features=None, class_id=None, class_name=None,
                confidence=None, reason=str(reason))
            self.harmonic = clear_model(self.harmonic, 'HARDWARE_STOP')

    def view(self):
        with self.lock:
            data = dict(self.data, source=self.source)
            age = None if self.updated is None else self.clock() - self.updated
            data['age_s'] = age
            data['worker_timing'] = self.worker_timing
            wave = dict(self.waveform)
            wave_age = None if self.wave_updated is None else self.clock() - self.wave_updated
            if wave_age is not None and wave_age > 3 and wave['status'] != 'ERROR':
                wave = dict(status='STALE', reason='超过3秒没有新Raw副本')
            data['waveform'] = dict(wave, age_s=wave_age)
            event = dict(self.event)
            event_age = None if self.event_updated is None else self.clock() - self.event_updated
            if event_age is not None and event_age > 3 and event['status'] != 'ERROR':
                event = invalidate_event(event, 'STALE', '事件数据已陈旧')
            data['event'] = dict(event, age_s=event_age)
            harmonic = dict(self.harmonic)
            h_age = None if self.harmonic_updated is None else self.clock() - self.harmonic_updated
            if h_age is not None and (not math.isfinite(h_age) or not 0 <= h_age <= .5):
                harmonic.update(status='invalid_input', input_status='rejected', error_code='STALE_INPUT',
                    features=None, class_id=None, class_name=None, confidence=None)
            if harmonic.get('input_status') != 'accepted':
                harmonic = clear_model(harmonic, harmonic.get('error_code', 'ADAPTER_REJECTED'))
            data['harmonic'] = dict(harmonic, display_age_s=h_age)
            if age is not None and age > 3 and data['status'] != 'ERROR':
                data.update(status='STALE', metrics={}, reason='超过 3 秒没有新 Feature；这是 UI 陈旧门限')
            return data


def demo(state, stop):
    fid = 0
    while not stop.is_set():
        fid += 1
        state.publish(dict(status='CONSISTENT', consistent=True, snapshot_valid=True,
                           frame_id=fid, seq_after=fid * 2, basic={
                               'CH1_RMS': dict(valid=True, value=1152 + 10 * math.sin(fid / 5)),
                               'CH2_RMS': dict(valid=True, value=690),
                               'CH1_PEAK': dict(valid=True, value=1630),
                               'CH2_PEAK': dict(valid=True, value=980),
                               'CH1_FREQUENCY_MHZ': dict(valid=True, value=50)}, channels={}))
        stop.wait(.25)


def hardware(state, stop, args):
    # PYNQ dependencies may request the current loop during import/initialization.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    monitor = event_log = model_log = None
    try:
        args.bound_print('ASYNC_WORKER_LOOP = READY', flush=True)
        model = None
        if getattr(args, 'physical_model_dir', None):
            from ui_physical import load_portable
            model = args.bound_model
            model_log = Path(args.model_log).open('x', encoding='utf-8')
            args.bound_print('PHYSICAL_MODEL = LOADED: '+args.model_algorithm, flush=True)
        sys.path.insert(0, str(Path(args.reader_dir).resolve()))
        from contextlib import nullcontext
        from lab07_mmio import read_live_diagnostics
        from lab07_errors import Lab07Error
        release_audit = args.release_audit
        with nullcontext(args.bound_managed) as managed:
            session = args.bound_session
            control = args.bound_control
            reader = args.bound_reader
            info = args.bound_info
            raw_enabled = True
            args.bound_print('LAB07_FEATURE_READER_PREFLIGHT = PASS', flush=True)
            b_monitor = None
            if getattr(args, 'harmonic', False):
                from ui_harmonic import HarmonicMonitor
                ids = info.identification
                release = dict(abi=f'{info.major}.{info.minor}', regmap_version=ids['REGMAP_VERSION'],
                    feature_capability=ids['FEATURE_CAPABILITY'], raw_capability=ids['RAW_CAPABILITY'],
                    frame_samples=ids['FRAME_SAMPLES'], sample_rate_nominal_hz=ids['SAMPLE_RATE_NOMINAL_HZ'],
                    bit_sha256=release_audit['bit_sha256'], hwh_sha256=release_audit['hwh_sha256'],
                    verified_by_reader=True)
                b_monitor = HarmonicMonitor(release, session.token(), model=model)
                args.bound_print('B_HARMONIC_ADAPTER = READY; MODEL = '+('CANDIDATE' if model is not None else 'NOT_READY'), flush=True)
            if getattr(args, 'events', False):
                from ui_events import EventMonitor
                baseline = json.loads(Path(args.baseline).read_text(encoding='utf-8-sig'))
                baseline_ch2 = json.loads(Path(args.baseline_ch2).read_text(encoding='utf-8-sig')) if getattr(args,'baseline_ch2',None) else None
                event_log = Path(args.event_log).open('x', encoding='utf-8')
                def emit_event(record):
                    event_log.write(json.dumps(record, ensure_ascii=False, default=str) + '\n')
                    event_log.flush()
                emit_event(dict(record='context', build=UI_BUILD, baseline=baseline, baseline_ch2=baseline_ch2,
                    release=release_audit, session=managed.metadata(), copy='explicit',
                    time_basis='segment samples / nominal Fs; not calibrated wall clock'))
                monitor = EventMonitor(baseline, emit_event, baseline_ch2=baseline_ch2)
                state.publish_event(monitor.snapshot())
                args.bound_print('EVENT_CHANNELS = '+('CH1,CH2' if baseline_ch2 is not None else 'CH1')+'; WARMUP', flush=True)
            raw_count = missing_raw = 0
            timing_seq = 0
            previous_drop = None
            last_feature_at = None
            while not stop.is_set():
                loop_started = time.monotonic()
                diag = read_live_diagnostics(control)
                fault_names = ('ACQUISITION_FAULT', 'ACQUISITION_FAULT_CODE',
                               'BRANCH_MISMATCH_STICKY', 'ORDER_UNKNOWN_STICKY',
                               'LAB05_SUMMARY_OVERRUN', 'LAB05_RESULT_OVERRUN',
                               'LAB06_BANK_OVERRUN_STICKY', 'LAB06_FRAME_ERROR_STICKY',
                               'LAB06_PROTOCOL_ERROR_STICKY')
                faults = {k: diag[k] for k in fault_names if diag.get(k)}
                if raw_enabled:
                    faults.update({k: diag[k] for k in ('RAW_PROTOCOL_STICKY',
                        'RAW_ACK_ERROR_STICKY', 'RAW_TOKEN_EXHAUSTED_STICKY') if diag.get(k)})
                if faults:
                    raise RuntimeError('LIVE_DIAGNOSTIC_FAULT: ' + str(faults))
                feature_started = feature_done = time.monotonic()
                # Raw needs every 204.8 ms frame. Refresh Feature/model about every
                # two Raw frames; skipped reads must not refresh old result ages.
                refresh_feature = (last_feature_at is None or not raw_enabled
                    or feature_started-last_feature_at >= .35
                    or feature_started < last_feature_at)
                if refresh_feature:
                    last_feature_at = feature_started
                    snapshot = reader.feature()
                    received = time.monotonic()
                    result = snapshot.to_dict()
                    if result.get('status') == 'ABI_MISMATCH':
                        raise RuntimeError('ABI_MISMATCH')
                    state.publish(result)
                    feature_done = time.monotonic()
                    if b_monitor is not None and not result.get('stale'):
                        post_feature = read_live_diagnostics(control)
                        if any(post_feature.get(k) for k in tuple(fault_names) + (
                                'RAW_PROTOCOL_STICKY', 'RAW_ACK_ERROR_STICKY', 'RAW_TOKEN_EXHAUSTED_STICKY')):
                            raise RuntimeError('Live fault after Feature read; B input rejected')
                        checked = b_monitor.process(result, received, time.monotonic())
                        if model_log is not None:
                            model_log.write(json.dumps(dict(record='physical_model', harmonic=checked,
                                monotonic=time.monotonic()), ensure_ascii=False, allow_nan=False)+'\n')
                            model_log.flush()
                        state.publish_harmonic(checked)
                model_done = time.monotonic()
                raw_done = event_done = model_done
                copy_duration = None
                drop_after = diag.get('RAW_DROP_COUNT')
                if raw_enabled:
                    try:
                        frame = reader.raw('explicit')
                        raw_done = time.monotonic()
                        copy_duration = getattr(frame,'copy_duration',None)
                    except Lab07Error as exc:
                        if exc.code != 'RAW_DESCRIPTOR_INCOHERENT':
                            raise  # In particular never replay an uncertain ACK.
                        missing_raw += 1
                        if missing_raw >= 100:
                            raise RuntimeError('Raw unavailable after 100 bounded fresh-descriptor attempts') from exc
                        stop.wait(.01)
                        continue
                    missing_raw = 0
                    raw_count += 1
                    after = read_live_diagnostics(control)
                    drop_after = after.get('RAW_DROP_COUNT')
                    if any(after.get(k) for k in tuple(fault_names) + (
                            'RAW_PROTOCOL_STICKY', 'RAW_ACK_ERROR_STICKY', 'RAW_TOKEN_EXHAUSTED_STICKY')):
                        raise RuntimeError('Fault latched during Raw copy; waveform not published')
                    if raw_count > 2:  # Drain both possible pre-attach backlog banks.
                        state.publish_waveform(frame)
                        if monitor is not None:
                            previous_error = monitor.error
                            monitor.push(frame, diag, after)
                            state.publish_event(monitor.snapshot())
                            if monitor.error and not previous_error:
                                args.bound_print('EVENT_MONITOR_STOPPED:', monitor.error, flush=True)
                        if raw_count == 3:
                            args.bound_print('RAW_WAVEFORM_FIRST_FRESH_COPY = PUBLISHED', flush=True)
                event_done = time.monotonic()
                timing_seq += 1
                timing = dict(seq=timing_seq,monotonic=event_done,
                    feature_frame_id=result.get('frame_id'),feature_processed=refresh_feature,
                    raw_frame_id=frame.descriptor.frame_id if raw_enabled else None,
                    diagnostics_seconds=feature_started-loop_started,
                    feature_seconds=feature_done-feature_started,
                    adapter_model_log_seconds=model_done-feature_done,
                    raw_read_seconds=raw_done-model_done,
                    raw_copy_seconds=copy_duration,
                    post_raw_publish_events_seconds=event_done-raw_done,
                    work_seconds=event_done-loop_started,
                    nominal_raw_frame_seconds=.2048,
                    scheduled_wait_seconds=.001 if raw_enabled else .1,
                    drop_previous_loop=previous_drop,
                    drop_before=diag.get('RAW_DROP_COUNT'),drop_after=drop_after,
                    event_error=monitor.error if monitor is not None else None,
                    raw_descriptor_retry_count=missing_raw)
                state.publish_timing(timing)
                if timing_seq % 10 == 0 or previous_drop != drop_after:
                    args.bound_print('UI_TIMING = '+json.dumps(timing,allow_nan=False),flush=True)
                previous_drop = drop_after
                stop.wait(.001 if raw_enabled else .1)
    except Exception as exc:
        if monitor is not None:
            monitor.stop(str(exc))
            state.publish_event(monitor.snapshot())
        state.fail(str(exc))
        traceback.print_exc()
        args.bound_print('HARDWARE STOP:', exc, flush=True)
    finally:
        if monitor is not None:
            monitor.finish()
        if event_log is not None:
            event_log.close()
        if model_log is not None:
            model_log.close()
        loop.close()
        asyncio.set_event_loop(None)


