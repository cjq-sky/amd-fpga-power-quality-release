"""Default OFFLINE. --hardware is for the future PYNQ session only."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import time
from lab07_registers import INSTANCE_NAME, BASE_ADDRESS, APERTURE, RELEASE_STEM
from lab07_mmio import audit_release, audit_hwh, verify_abi, PynqMMIOAdapter
from lab07_read_snapshot import SnapshotReader
from lab07_logging import load_config, write_csv
from mock_mmio import MockMMIO
from lab07_session import ManagedEpoch

STAGE = Path(__file__).resolve().parents[1]


@contextmanager
def exclusive_overlay_session():
    # Advisory lock only coordinates cooperating processes. No uncoordinated JTAG/reload is allowed.
    import fcntl
    with os.fdopen(os.open("/tmp/pq_lab07_feature_overlay.lock", os.O_RDWR | os.O_CREAT, 0o600), "r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            yield ManagedEpoch(lock, boot_id)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def offline(args, reader_config):
    if bool(args.bit) != bool(args.hwh):
        raise ValueError("supply both --bit and --hwh for release audit")
    if args.bit:
        print(json.dumps(audit_release(args.bit, args.hwh), indent=2))
    fixture = json.loads((STAGE / "fixtures/offline_numeric_replay.json").read_text(encoding="utf-8"))
    mmio = MockMMIO()
    reader = SnapshotReader(mmio, reader_config, epoch_getter=lambda: mmio.epoch)
    results = []
    for frame in fixture["frames"]:
        mmio.update(frame["registers"])
        result = reader.read()
        results.append(result)
        print(json.dumps(result.to_dict(), ensure_ascii=False))
    if args.csv:
        write_csv(args.csv, results, fixture["provenance"], "offline_existing_sim_replay")
    print("NOT HARDWARE VALIDATED; offline replay only")
    return 0 if all(r.consistent for r in results) else 2


def hardware(args, reader_config, config):
    if not args.bit or not args.hwh:
        raise ValueError('--hardware requires --bit and --hwh')
    from lab07_hardware_smoke import main as unified_main
    argv=['--hardware','--feature-only','--bit',args.bit,'--hwh',args.hwh,
          '--case',args.case_label.split('_')[0],'--timeout',str(config['liveness_timeout_s'])]
    if args.attach:argv.append('--attach')
    return unified_main(argv)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hardware", action="store_true", help="PYNQ only: explicitly load overlay and read real MMIO")
    parser.add_argument("--attach", action="store_true", help="with --hardware: reuse the completed managed overlay, do not reload")
    parser.add_argument("--bit")
    parser.add_argument("--hwh")
    parser.add_argument("--config")
    parser.add_argument("--csv")
    parser.add_argument("--case-label", choices=("CASE0_no_input", "CASE1_CH1_50Hz", "CASE2_dual", "CASE3_controlled_harmonic"), default="CASE0_no_input")
    args = parser.parse_args(argv)
    if args.attach and not args.hardware:
        raise ValueError("--attach requires --hardware")
    reader_config, config = load_config(args.config)
    return hardware(args, reader_config, config) if args.hardware else offline(args, reader_config)


if __name__ == "__main__":
    raise SystemExit(main())
