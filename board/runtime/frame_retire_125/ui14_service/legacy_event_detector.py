"""CH1 streaming event detection using the frozen Lab07 explicit-copy reader."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time

import numpy as np


def classify(value):
    if value < .1:
        return "INTERRUPTION"
    if value < .9:
        return "SAG"
    if value > 1.1:
        return "SWELL"
    return "NORMAL"


def check_live(diagnostics):
    code = diagnostics.get("ACQUISITION_FAULT_CODE", 0)
    if diagnostics.get("ACQUISITION_FAULT", 0) or code:
        raise ValueError(f"ACQUISITION_FAULT code=0x{code:02x}; no event consumption")
    for name in ("BRANCH_MISMATCH_STICKY", "ORDER_UNKNOWN_STICKY",
                 "LAB05_SUMMARY_OVERRUN", "LAB05_RESULT_OVERRUN",
                 "LAB06_BANK_OVERRUN_STICKY", "LAB06_FRAME_ERROR_STICKY",
                 "LAB06_PROTOCOL_ERROR_STICKY", "RAW_PROTOCOL_STICKY",
                 "RAW_ACK_ERROR_STICKY", "RAW_TOKEN_EXHAUSTED_STICKY"):
        if diagnostics.get(name, 0):
            raise ValueError("LIVE_DIAGNOSTIC_FAULT: " + name)


def check_drop_change(previous, current):
    for name in ("RAW_DROP_COUNT", "RAW_DROP_STICKY"):
        if previous.get(name) != current.get(name):
            raise ValueError("DATA_GAP: " + name + " changed")


class EventDetector:
    def __init__(self, nominal_rms_code, fs=10000, f0=50, hold_seconds=.010):
        if not all(math.isfinite(v) and v > 0 for v in (nominal_rms_code, fs, f0, hold_seconds)):
            raise ValueError("Positive finite nominal/Fs/f0/hold required")
        self.nominal, self.fs = float(nominal_rms_code), float(fs)
        self.window = round(fs / f0)
        self.hold = math.ceil(hold_seconds * fs)
        if not 2 <= self.window <= 2048:
            raise ValueError("RMS window outside supported 2..2048 samples")
        self.segment = 0
        self.event_number = 0
        self.active = None
        self._reset()

    def _reset(self):
        self.tail = np.empty(0, dtype=float)
        self.samples = 0
        self.state = self.candidate = self.previous = None
        self.last_rms_pu = None

    def _close(self, recovered=False, end=None, end_confirmed=None, reason="RUN_END", data_gap=False):
        if self.active is None:
            return []
        event, self.active = self.active, None
        states = event["states"]
        low = "SAG" in states or "INTERRUPTION" in states
        event.update(type="MIXED" if low and "SWELL" in states else
                     "INTERRUPTION" if "INTERRUPTION" in states else
                     "SAG" if "SAG" in states else "SWELL",
                     end_time=end if recovered else None,
                     end_confirmed_time=end_confirmed if recovered else None,
                     complete=bool(recovered and event["start_observed"] and not data_gap),
                     data_gap=data_gap, source_valid=not data_gap, reason=reason)
        event["duration"] = end - event["start_time"] if event["complete"] else None
        event["confirmed_duration"] = end_confirmed - event["confirmed_time"] if event["complete"] else None
        event["observed_duration"] = event["observed_until"] - event["start_time"]
        return [event]

    def finish(self):
        return self._close()

    def gap(self, reason):
        records = self._close(reason=reason, data_gap=True)
        records.append({"record": "DATA_GAP", "reason": reason, "segment_id": self.segment,
                        "last_frame_id": self.previous["frame_id"] if self.previous else None})
        self.segment += 1
        self._reset()
        return records

    def push(self, samples, meta):
        if (samples.dtype != np.dtype("int16") or samples.shape != (2048,) or
                meta["ack_result"] != 1 or not meta["owner_valid"] or not meta["frame_valid"] or
                meta["sample_count"] != 2048 or meta["frame_bytes"] != 8192 or
                meta["channel_mask"] != 3 or meta["format"] != 65537):
            raise ValueError("Invalid complete Raw frame/geometry/ACK")
        diag = meta["drop_diagnostics"]
        check_live(diag)
        if self.previous is not None:
            p = self.previous
            reasons = []
            if meta["epoch"] != p["epoch"]:
                reasons.append("session/epoch changed")
            if meta["frame_id"] != (p["frame_id"] + 1) % 2 ** 32:
                reasons.append("frame_id gap")
            if meta["token"] != p["token"] + 1:
                reasons.append("token discontinuity")
            if diag["RAW_DROP_COUNT"] != p["drop_diagnostics"]["RAW_DROP_COUNT"]:
                reasons.append("drop count changed")
            if diag.get("RAW_DROP_STICKY") != p["drop_diagnostics"].get("RAW_DROP_STICKY"):
                reasons.append("drop sticky changed")
            if reasons:
                records = self.gap("; ".join(reasons))
                records[-1]["discarded_frame_id"] = meta["frame_id"]
                return records  # Never join either side of a gap.
        self.previous = meta
        x = np.concatenate((self.tail, samples.astype(np.float64)))
        first = self.samples - len(self.tail) + self.window - 1
        square_sum = np.r_[0., np.cumsum(x * x)]
        rms = np.sqrt(np.maximum((square_sum[self.window:] - square_sum[:-self.window]) / self.window, 0)) / self.nominal
        self.tail = x[-(self.window - 1):].copy()
        self.samples += len(samples)
        records = []
        for offset, value in enumerate(rms):
            index = first + offset
            now = index / self.fs
            value = float(value)
            self.last_rms_pu = value
            if self.active is not None:
                self.active["min_rms_pu"] = min(self.active["min_rms_pu"], value)
                self.active["max_rms_pu"] = max(self.active["max_rms_pu"], value)
                self.active.update(last_frame_id=meta["frame_id"], observed_until=now)
            proposed = classify(value)
            if proposed == self.state:
                self.candidate = None
                continue
            if self.candidate is None or proposed != self.candidate["state"]:
                self.candidate = {"state": proposed, "index": index, "time": now,
                                  "frame_id": meta["frame_id"], "min": value, "max": value}
            c = self.candidate
            c["min"], c["max"] = min(c["min"], value), max(c["max"], value)
            if index - c["index"] < self.hold:
                continue
            records.append({"record": "transition", "from": self.state or "WARMUP", "to": proposed,
                            "crossing_time": c["time"], "confirmed_time": now,
                            "frame_id": meta["frame_id"], "rms_pu": value,
                            "segment_id": self.segment, "epoch": meta["epoch"]})
            if proposed == "NORMAL":
                records += self._close(True, c["time"], now, "NORMAL_RECOVERED")
            elif self.active is None:
                self.event_number += 1
                self.active = {"record": "event", "event_id": self.event_number,
                               "states": [proposed], "start_time": c["time"], "confirmed_time": now,
                               "start_observed": self.state == "NORMAL", "observed_until": now,
                               "min_rms_pu": c["min"], "max_rms_pu": c["max"],
                               "nominal_rms_code": self.nominal, "channel": "CH1",
                               "first_frame_id": c["frame_id"], "last_frame_id": meta["frame_id"],
                               "session": meta["epoch"][0], "epoch": meta["epoch"],
                               "segment_id": self.segment, "time_basis": "segment sample index / nominal Fs"}
            else:
                self.active["states"].append(proposed)
            self.state, self.candidate = proposed, None
        return records


def hardware(args, base=None, reader_dir=None):
    # Import the frozen reader unchanged; PYNQ is needed only inside this function.
    reader_dir = reader_dir or Path("/home/xilinx/jupyter_notebooks/lab07_unified/python")
    sys.path.insert(0, str(reader_dir))
    from lab07_hardware_smoke import managed_session, raw_record, save_raw
    from lab07_mmio import audit_release, audit_hwh, PynqMMIOAdapter, read_live_diagnostics
    from lab07_registers import RAW_BASE, RAW_RANGE
    from lab07_unified_reader import UnifiedReader
    from lab07_session import Session
    from lab07_feature_reader import ReaderConfig
    from lab07_errors import Lab07Error
    from pynq import Overlay

    base = base or Path("/home/xilinx/jupyter_notebooks/lab07_event_detector")
    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8-sig"))
    if baseline["channel"] != "CH1":
        raise ValueError("Baseline channel must be CH1")
    detector = EventDetector(baseline["nominal_rms_code"], baseline["fs_hz"], baseline["f0_hz"])
    run_id = args.run_id or "LIVE_" + args.case.upper() + "_001"
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", run_id):
        raise ValueError("Invalid run_id")
    out = base / "results" / run_id
    out.mkdir(parents=True, exist_ok=False)
    bit = reader_dir.parent / "release/pq_lab07_feature_raw_mmio_v1.bit"
    hwh = bit.with_suffix(".hwh")
    budget = 64 if args.case == "normal" else 180
    count = 0
    processed = 0
    gap_reported = False
    transitions = []
    event_count = 0
    diagnostics = {}
    previous_live = None
    last_frame = None
    failure = None
    settings = {"run_id": run_id, "case": args.case, "baseline": baseline,
                "fs_hz": detector.fs, "f0_hz": baseline["f0_hz"], "rms_window_samples": detector.window,
                "hold_seconds": .010, "thresholds": {"interruption": .1, "sag": .9, "swell": 1.1},
                "copy": "explicit", "ordering_basis": "previously accepted PYNQ explicit-copy platform contract",
                "quarantine_frames": 2, "frame_budget": budget, "time_basis": "segment samples / nominal Fs",
                "min_max_scope": "candidate onset through recovery confirmation; includes recovery hold",
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    if args.case == "normal":
        print("REAL-TIME NORMAL TEST: keep CH1 at 1.0 Vpp throughout; no amplitude changes.", flush=True)
    else:
        print("REAL-TIME TEST: keep CH1 at 1.0 Vpp; wait for >>> NOW <<<.", flush=True)
    print("Results: " + str(out), flush=True)
    with (out / "records.jsonl").open("x", encoding="utf-8") as log:
        def emit(record):
            nonlocal event_count, gap_reported
            log.write(json.dumps(record, default=str) + "\n")
            log.flush()
            if record["record"] == "transition":
                transitions.append(record["to"])
                print(f"[STATE] {record['from']} -> {record['to']}  "
                      f"t={record['confirmed_time']:.4f}s  pu={record['rms_pu']:.3f}", flush=True)
            elif record["record"] == "event":
                event_count += 1
                duration = f"{record['duration']:.3f}s" if record["duration"] is not None else "incomplete"
                print(f"[EVENT] {record['type']}  duration={duration}  complete={record['complete']}", flush=True)
            elif record["record"] == "DATA_GAP":
                gap_reported = True
                print("[DATA_GAP] " + record["reason"], flush=True)

        try:
            audit = audit_release(bit, hwh)
            emit({"record": "release", "audit": audit})
            with managed_session() as managed:
                managed.require_attach()  # Attach only; never reload to obtain a passing run.
                session = Session(managed)
                overlay = Overlay(str(bit), download=False)
                for plane, region in audit_hwh(hwh)["regions"].items():
                    matches = [v for v in overlay.ip_dict.values()
                               if int(v.get("phys_addr", -1)) == region["base"] and
                               int(v.get("addr_range", -1)) == region["range"]]
                    if len(matches) != 1:
                        raise ValueError("PYNQ HWH region mismatch: " + plane)
                control = PynqMMIOAdapter()
                diagnostics = read_live_diagnostics(control)
                emit({"record": "preflight_live", "diagnostics": diagnostics, "session": managed.metadata()})
                check_live(diagnostics)
                from lab07_abi import negotiate
                info = negotiate(control)
                if not info.raw_supported or info.identification["SAMPLE_RATE_NOMINAL_HZ"] != detector.fs:
                    raise ValueError("Raw capability or nominal Fs mismatch")
                emit({"record": "abi", "info": asdict(info)})
                data = PynqMMIOAdapter(RAW_BASE, RAW_RANGE, control, ordering_confirmed=True)
                reader = UnifiedReader(control, data, session, ReaderConfig(required_channels=()))
                started = last_service = time.monotonic()
                while count < budget:
                    if time.monotonic() - started > 90 or time.monotonic() - last_service > 3:
                        raise ValueError("RAW_STALL_OR_RUN_TIMEOUT")
                    diagnostics = read_live_diagnostics(control)
                    check_live(diagnostics)
                    if previous_live is not None:
                        check_drop_change(previous_live, diagnostics)
                    before = diagnostics
                    try:
                        frame = reader.raw("explicit")
                    except Lab07Error as error:
                        if error.code != "RAW_DESCRIPTOR_INCOHERENT":
                            raise  # In particular never replay an uncertain ACK.
                        emit({"record": "reader_retry", "code": error.code, "detail": error.detail})
                        time.sleep(.01)
                        continue
                    count += 1
                    last_service = time.monotonic()
                    meta = raw_record(frame)
                    last_frame = meta
                    diagnostics = read_live_diagnostics(control)
                    save_raw(frame, out / "raw.npz")
                    emit({"record": "raw_frame", "quarantined": count <= 2, "raw": meta,
                          "live_before": before, "live_after": diagnostics})
                    check_live(diagnostics)  # Reject a newly latched fault before event consumption.
                    if count <= 2:
                        continue
                    check_drop_change(before, meta["drop_diagnostics"])
                    check_drop_change(meta["drop_diagnostics"], diagnostics)
                    records = detector.push(frame.CH1, meta)
                    for record in records:
                        emit(record)
                    if any(record["record"] == "DATA_GAP" for record in records):
                        raise ValueError("Continuity lost; current test stopped")
                    processed += 1
                    previous_live = diagnostics
                    fresh = count - 2
                    if args.case != "normal" and fresh in (50, 100):
                        action = {"sag": "0.8 Vpp", "swell": "1.2 Vpp", "interruption": "0.05 Vpp"}[args.case]
                        if fresh == 100:
                            action = "1.0 Vpp"
                        emit({"record": "operator_cue", "fresh_frames": fresh, "action": action})
                        print("\a>>> NOW: CH1 -> " + action + " <<<", flush=True)
                    elif fresh % 25 == 0:
                        print(f"Frames={fresh}  state={detector.state}  pu={detector.last_rms_pu:.3f}", flush=True)
                diagnostics = read_live_diagnostics(control)
                check_live(diagnostics)
                if previous_live is not None:
                    check_drop_change(previous_live, diagnostics)
                emit({"record": "final_live", "diagnostics": diagnostics})
                for record in detector.finish():
                    emit(record)
        except (Exception, KeyboardInterrupt) as error:
            failure = {"error": str(error), "code": getattr(error, "code", None),
                       "recovery": getattr(error, "recovery", None), "live": diagnostics,
                       "last_frame": last_frame}
            if not gap_reported:
                for record in detector.gap(str(error)):
                    emit(record)
            emit({"record": "failure", **failure})
            print("STOP: " + str(error), flush=True)
    expected = ["NORMAL"] if args.case == "normal" else ["NORMAL", args.case.upper(), "NORMAL"]
    summary = {"run_id": run_id, "raw_frames": count, "processed_frames": processed,
               "transitions": transitions, "events": event_count,
               "expected_path_observed": transitions == expected,
               "status": "STOPPED_INVALID" if failure else "COMPLETED_REQUIRES_REVIEW",
               "failure": failure, "integration_acceptance": "PENDING_HARDWARE_EVIDENCE_REVIEW"}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print("SUMMARY: " + json.dumps({k: v for k, v in summary.items() if k != "failure"}), flush=True)
    return 2 if failure else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("normal", "sag", "swell", "interruption"), default="sag")
    parser.add_argument("--run-id")
    parser.add_argument("--baseline", default=str(Path(__file__).with_name("NOMINAL_BASELINE_001.json")))
    try:
        raise SystemExit(hardware(parser.parse_args()))
    except (Exception, KeyboardInterrupt) as error:
        print("STOP: " + str(error), file=sys.stderr)
        raise SystemExit(2)
