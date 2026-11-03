"""Shared real-time UI: automatic refresh and serial USB Touch view selection."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boot', required=True)
    parser.add_argument('--cold-session-confirmed', action='store_true', required=True,
                        help='Operator confirms power cycle, no HDMI/frame commands since power-on, only step 01 run')
    args = parser.parse_args()
    import fcntl  # Linux board only; --help is available on the Windows preparation host.
    root = Path(__file__).resolve().parent
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    require(boot == args.boot, 'Boot changed')
    for name, expected in json.loads((root / '11_payload_sha256.json').read_text()).items():
        require(sha(root / name) == expected, 'Payload mismatch: ' + name)
    load_path = root / 'results' / ('load_identity_' + boot + '.jsonl')
    load = [json.loads(line) for line in load_path.read_text().splitlines()]
    require(load[-1]['event'] == 'IDENTITY_CHECK_PASS' and load[-1]['boot'] == boot,
            'Missing step 01 identity')
    pair = {'bit': '45197bb23c05e8f8c73e4cbbced7c12ce66599a4b54a407d77fefd94a08820f4',
            'hwh': '54980f765756f8dc64ade54af7969c7b96054c816a31d88ab9d2c07fbce05b6f'}
    require(load[0]['hashes'] == pair, 'Wrong loader release')
    for suffix, expected in pair.items():
        require(sha(root / ('final_frame_retire_fclk1_125.' + suffix)) == expected, 'Pair changed')
    with ExitStack() as stack:
        for name in ('pq_lab07_feature_overlay', 'pq_pl_programming', 'pq_unified2_hardware'):
            lease = stack.enter_context(open('/tmp/' + name + '.lock', 'a+'))
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lease.seek(0)
            require(not lease.read().strip(), 'Other managed load; stop')
        require(not any((root / 'results' / (prefix + boot)).exists()
                        for prefix in ('static_pages_', 'static_regression_')),
                'Static display already attempted in this boot; not a cold dynamic session')
        out = root / 'results' / ('live_ui4_' + boot)
        out.mkdir()
        log = stack.enter_context((out / 'events.jsonl').open('x'))

        trace_context = dict(iteration=0, session='COLD_INITIALIZATION')
        def record(event, **values):
            row = dict(event=event, monotonic=time.monotonic(), boot=boot, **trace_context)
            row.update(values)
            text = json.dumps(row)
            log.write(text + '\n'); log.flush()
            critical = event in ('FRAME_RETIRE_ITERATION', 'STOP', 'STAGE4_READY')
            doorbell = event == 'W_ATTEMPT' and values.get('address') in ('0x4300010c', '0x4300012c', '0x43000168')
            if critical or doorbell:
                os.fsync(log.fileno())
            if event not in ('R', 'W_ATTEMPT', 'W_RETURNED', 'DRAW_FLUSH_COMPLETE', 'FRAME_RETIRE_ITERATION', 'RENDER_PIPELINE_TIMING', 'SHARED_SNAPSHOT_PRESENTED'):
                print(text, flush=True)

        sys.path.insert(0, str(root / 'regression_support'))
        from pynq import MMIO, allocate, Clocks
        from initialization import Session, initialize
        from dynamic_video import DynamicMM2S
        from touch_pages import PAGES
        buffers = []
        driver = None
        runtime = None
        touch = None
        iteration_log = stack.enter_context((out / 'FRAME_RETIRE_ITERATIONS.jsonl').open('x'))
        sys.path.insert(0, str(root / 'ui14'))

        def hold():
            print('HOLD: keep this process/terminal alive; DMA buffer references retained.', flush=True)
            while True:
                try:
                    time.sleep(30)
                except KeyboardInterrupt:
                    pass

        def interrupted(signum, frame):
            print('Signal %d received; no reset/free/exit. Keep owner alive.' % signum, flush=True)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, interrupted)

        class IO:
            def __init__(self, base):
                self.base = base
                self.mmio = MMIO(base, 0x10000)

            def read(self, off):
                try:
                    value = int(self.mmio.read(off))
                except BaseException as e:
                    record('R_ERROR', address=hex(self.base + off), exception=repr(e))
                    raise
                record('R', address=hex(self.base + off), value=hex(value), result='CALL_RETURNED')
                return value

            def write(self, off, value):
                record('W_ATTEMPT', address=hex(self.base + off), value=hex(value))
                self.mmio.write(off, value)
                record('W_RETURNED', address=hex(self.base + off), value=hex(value))

        try:
            record('BEGIN', load_log_sha256=sha(load_path),
                   content='Real shared snapshots with serial auto refresh and USB Touch',
                   dynamic_session='COLD_ARM_REQUESTED', independent_bus_response='NOT_MEASURED',
                   cold_method='Operator confirms full power cycle; only step 01 this boot',
                   HP0_clean_session_review='Previously approved method; full power cycle; no independent HP0 observer')
            clocks = dict(fclk0_mhz=float(Clocks.fclk0_mhz), fclk1_mhz=float(Clocks.fclk1_mhz))
            require(abs(clocks['fclk0_mhz'] - 100) < .1 and abs(clocks['fclk1_mhz'] - 125) < .1,
                    'PS clock mismatch')
            bases = dict(dma=0x43000000, reset=0x43C40000, clock=0x43C30000,
                         vtc=0x43C20000, csc=0x43C60000, unpack=0x43C70000,
                         intc=0x41800000, gpio=0x41230000)
            ios = {name: IO(base) for name, base in bases.items()}
            require(ios['dma'].read(0x100) == 0x46520101
                    and ios['dma'].read(0x104) == 0 and ios['dma'].read(0x108) == 0,
                    'Unexpected Frame Retire state')
            reset = ios['reset']
            require(reset.read(0) == 0x57520201 and reset.read(12) == 32
                    and reset.read(4) == 0 and not reset.read(8) & 1, 'Warm reset prerequisites mismatch')
            driver = DynamicMM2S(ios['dma'])
            from live_runtime import LiveUI
            runtime = LiveUI(root, out, driver, record, iteration_log, boot, sha(load_path))
            require(not driver.read(0) & 5 and driver.status() & 1, 'DMA not fresh/stopped')
            for _ in range(4):
                buffers.append(allocate(shape=(720, 1280, 3), dtype='u1'))
            driver.stage_pages(buffers)
            record('BUFFERS', slots=[dict(slot=i, base=hex(int(p.physical_address)), bytes=int(p.nbytes))
                                     for i, p in enumerate(buffers)])
            session = Session(boot, pair['hwh'], str(load_path) + ':sha256=' + sha(load_path), json.dumps(clocks))
            initialize(**{k: ios[k] for k in ('clock', 'csc', 'unpack', 'vtc', 'intc', 'gpio')},
                       dma=driver, buffer=buffers[0], fill=lambda _: driver.fill_pages(root / 'live_boot_assets'),
                       session=session)
            for _ in range(100):
                value = reset.read(8)
                require(not value & 1, 'Unexpected reset HOLD')
                if value & 2:
                    break
                time.sleep(.005)
            else:
                raise TimeoutError('VIDEO_LOCKED not observed')
            require(driver.fr.status() == 3, 'Dynamic enable/started not confirmed')
            trace_context['session'] = '%032x' % driver.fr.generation
            runtime.start()
            record('STAGE4_READY', generation='%032x' % driver.fr.generation,
                   active_slot=driver.fr.active, http='http://192.168.2.99:8765',
                   mode='SHARED_SNAPSHOT_AUTO_AND_TOUCH_READY', automatic_refresh=False)
            from touch_input import TouchInput
            touch = TouchInput(record)
            import select
            automatic = False
            current_page = 'overview'
            next_refresh = time.monotonic()
            touch_pending = False
            print('Commands: auto on/off | touch on/off | capture <view> | status | hold.', flush=True)
            while True:
                watchers = [sys.stdin]
                if touch.fd is not None:
                    watchers.append(touch.fd)
                timeout = max(0, next_refresh-time.monotonic()) if automatic or touch_pending else None
                ready, _, _ = select.select(watchers, [], [], timeout)
                if touch.fd is not None and touch.fd in ready:
                    requested = touch.poll()
                    if requested is not None:
                        current_page = requested
                        touch_pending = True
                        next_refresh = time.monotonic()
                if sys.stdin in ready:
                    command = input('ui4> ').strip()
                    if not command:
                        continue
                    if command in ('touch on','touch off'):
                        if command == 'touch off':
                            touch.close()
                            record('TOUCH_OFF')
                        else:
                            try:
                                touch.open()
                            except Exception as error:
                                record('TOUCH_UNAVAILABLE', exception=repr(error), action='Keep video/Reader; reconnect and touch on')
                    elif command in ('auto on','auto off'):
                        automatic = command == 'auto on'
                        next_refresh = time.monotonic()
                        record('REFRESH_MODE', automatic=automatic, minimum_wait_seconds=1.0)
                    elif command.startswith('capture '):
                        page = command[8:]
                        if page not in PAGES:
                            record('INPUT_REJECTED', reason='Unknown view')
                            continue
                        current_page = page
                        trace_context['iteration'] = runtime.seq+1
                        runtime.capture(current_page, automatic=automatic)
                        next_refresh = time.monotonic()+1.0
                        record('CAPTURE_COMPLETE', seq=runtime.seq, view=current_page)
                    elif command == 'status':
                        view = runtime.state.view()
                        timing = view.get('worker_timing') or {}
                        record('LIVE_UI_STATUS', FR_STATUS=hex(driver.fr.status()),
                               FR_ERROR=hex(driver.fr.read(0x108)), seq=runtime.seq,
                               video_status=hex(reset.read(8)), acquisition_status=view.get('status'),
                               event_status=view.get('event',{}).get('status'),
                               CH2_event_status=(view.get('event',{}).get('channels') or {}).get('CH2',{}).get('status'),
                               event_error=timing.get('event_error'), drop_count=timing.get('drop_after'),
                               snapshot_id=runtime.store.view().get('shared_snapshot_id'),
                               generation='%032x'%driver.fr.generation, view=current_page,
                               automatic=automatic, touch_enabled=touch.fd is not None)
                    elif command == 'hold':
                        hold()
                    else:
                        record('INPUT_REJECTED', reason='Unknown command; no write')
                if (automatic or touch_pending) and time.monotonic() >= next_refresh:
                    trace_context['iteration'] = runtime.seq+1
                    runtime.capture(current_page, automatic=automatic)
                    touch_pending = False
                    next_refresh = time.monotonic()+1.0
        except BaseException as error:
            try:
                record('STOP', exception=repr(error), action='No retry/free/reset/reload')
            finally:
                if touch is not None:
                    touch.close()
                if runtime is not None:
                    runtime.shutdown_acquisition()
                if driver is not None and driver.ever_started:
                    hold()
            raise


if __name__ == '__main__':
    main()
