"""One explicit frozen-pair load; identity reads only, no video/Reader start."""
import argparse
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time

PAIR = {
    'bit': '45197bb23c05e8f8c73e4cbbced7c12ce66599a4b54a407d77fefd94a08820f4',
    'hwh': '54980f765756f8dc64ade54af7969c7b96054c816a31d88ab9d2c07fbce05b6f',
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cold-boot', required=True,
                        help='Operator confirms no custom BIT/DMA since this boot')
    args = parser.parse_args()
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    require(args.cold_boot == boot, 'Boot changed; stop and report')
    root = Path(__file__).resolve().parent
    bit = root / 'final_frame_retire_fclk1_125.bit'
    for suffix, sha in PAIR.items():
        require(hashlib.sha256(bit.with_suffix('.' + suffix).read_bytes()).hexdigest()
                == sha, 'Frozen pair SHA mismatch: ' + suffix)
    with ExitStack() as stack:
        for name in ('pq_lab07_feature_overlay', 'pq_pl_programming', 'pq_unified2_hardware'):
            lease = stack.enter_context(open('/tmp/' + name + '.lock', 'a+'))
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lease.seek(0)
            prior = lease.read().strip()
            require(not prior, 'Existing lease journal; stop for review: ' + name)
        results = root / 'results'
        results.mkdir(exist_ok=True)
        log = stack.enter_context((results / ('load_identity_' + boot + '.jsonl')).open('x'))

        def record(event, **values):
            row = dict(event=event, monotonic=time.monotonic(), boot=boot, **values)
            text = json.dumps(row)
            log.write(text + '\n')
            log.flush()
            os.fsync(log.fileno())
            print(text, flush=True)

        record('BEGIN', bit=str(bit), hwh=str(bit.with_suffix('.hwh')), hashes=PAIR,
               operator_history='Only terminal checks since power-on; no custom BIT/DMA',
               cold_bus_evidence='Operator history only; A review pending; no dynamic arm')
        try:
            from pynq import Overlay, MMIO, Clocks
            overlay = Overlay(str(bit), download=False)
            expected = ((0x43000000, 0x10000, 'user.org:user:lab08_vdma_frame_retire:1.0'),
                        (0x43C00000, 0x1000, 'pq.local:user:lab07_feature_mmio:1.0'),
                        (0x43C10000, 0x2000, 'pq.local:user:lab07_raw_window:1.0'))
            for base, span, vlnv in expected:
                matches = [v for v in overlay.ip_dict.values() if v.get('phys_addr') == base]
                require(len(matches) == 1 and matches[0]['addr_range'] == span
                        and matches[0]['type'] == vlnv, 'PYNQ metadata mismatch: ' + hex(base))
            record('DOWNLOAD_ATTEMPT')
            overlay.download()
            state = Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()
            record('DOWNLOAD_RETURNED', fpga_state=state,
                   fclk0_mhz=float(Clocks.fclk0_mhz), fclk1_mhz=float(Clocks.fclk1_mhz))
            require(state == 'operating', 'FPGA not operating')
            require(abs(Clocks.fclk0_mhz - 100) < .1 and abs(Clocks.fclk1_mhz - 125) < .1,
                    'Live PS clock mismatch')
            for base, span, offsets in ((0x43C00000, 0x1000, (0, 4, 8, 12, 16)),
                                        (0x43000000, 0x10000, (0x100, 0x104, 0x108, 0x154))):
                mmio = MMIO(base, span)
                for offset in offsets:
                    address = base + offset
                    try:
                        value = int(mmio.read(offset))
                    except BaseException as error:
                        record('R', address=hex(address), exception=repr(error))
                        raise
                    record('R', address=hex(address), value=hex(value), result='CALL_RETURNED')
                    checks = {0x43C00000: 0x50514D37, 0x43C00004: 0x00070001,
                              0x43C00008: 0x00020001, 0x43000100: 0x46520101,
                              0x43000104: 0, 0x43000108: 0, 0x43000154: 0}
                    if address in checks:
                        require(value == checks[address], 'Initial identity/state mismatch: ' + hex(address))
            record('IDENTITY_CHECK_PASS', video_started=False, session_armed=False,
                   legacy_managed_attach_ready=False, board_regression='NOT_RUN')
        except BaseException as error:
            record('STOP', exception=repr(error), action='No retry/reload/reset; report log')
            raise


if __name__ == '__main__':
    main()
