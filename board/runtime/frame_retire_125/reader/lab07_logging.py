"""CSV/config contracts shared by offline replay and future hardware runner."""
import csv
import json
from pathlib import Path
from lab07_registers import BASIC_FIELDS, SPECTRAL_FIELDS
from lab07_read_snapshot import ReaderConfig

PAYLOAD_FIELDS = BASIC_FIELDS + SPECTRAL_FIELDS["CH1"] + SPECTRAL_FIELDS["CH2"]
CSV_FIELDS = ("evidence_scope", "case_label", "host_time", "status", "seq_before", "seq_after",
              "frame_id", "snapshot_valid", "consistent", "retry", "elapsed_s", "stale", "skip",
              "FEATURE_VALID_MASK", "FEATURE_ACQUISITION_VALID", "TIME_STATUS",
              "SPECTRAL_NUMERIC_STATUS", "SPECTRAL_STATUS", "FORMAL_IDENTITY", "reasons",
              "session_id", "boot_id", "reload_generation")
CSV_FIELDS += tuple(n + suffix for n in PAYLOAD_FIELDS for suffix in ("_raw", "_decoded", "_valid"))
CSV_FIELDS += tuple(ch + suffix for ch in ("CH1", "CH2") for suffix in
                    ("_numeric_valid", "_numeric_status", "_formal_identity", "_formal_acceptance", "_THD_percent"))


def csv_row(result, scope, case_label):
    data = result.to_dict()
    row = {n: data.get(n, "") for n in CSV_FIELDS}
    row.update(evidence_scope=scope, case_label=case_label, reasons=";".join(result.reasons))
    row.update({n: result.session.get(n, "") for n in ("session_id", "boot_id", "reload_generation")})
    for n in ("FEATURE_VALID_MASK", "FEATURE_ACQUISITION_VALID", "TIME_STATUS",
              "SPECTRAL_NUMERIC_STATUS", "SPECTRAL_STATUS", "FORMAL_IDENTITY"):
        row[n] = result.raw.get(n, "")
    for n in PAYLOAD_FIELDS:
        value = result.basic.get(n, {})
        if not value:
            value = result.channels.get(n[:3], {}).get("features", {}).get(n, {})
        row[n + "_raw"] = result.raw.get(n, "")
        row[n + "_decoded"] = value.get("value", "")
        row[n + "_valid"] = value.get("valid", result.channels.get(n[:3], {}).get("consumable", ""))
    for ch, value in result.channels.items():
        for key in ("numeric_valid", "numeric_status", "formal_identity", "formal_acceptance"):
            row[ch + "_" + key] = value[key]
        row[ch + "_THD_percent"] = value["features"][SPECTRAL_FIELDS[ch][-1]]["percent"]
    return row


def write_csv(path, results, scope, case_label):
    path = Path(path)
    if scope != "HARDWARE_RUNTIME_OBSERVATION" and not path.name.startswith(("mock_", "offline_")):
        raise ValueError("offline outputs require mock_/offline_ filename prefix")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(csv_row(r, scope, case_label) for r in results)


DEFAULT_CONFIG = {"retry": 3, "safety_window_s": 1.0, "required_channels": ["CH1", "CH2"],
                  "required_basic": [], "poll_interval_s": 0.05, "liveness_timeout_s": 10.0,
                  "samples": 8}


def load_config(path=None):
    config = dict(DEFAULT_CONFIG)
    if path:
        supplied = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(supplied, dict) or set(supplied) - set(config):
            raise ValueError("unknown configuration field")
        config.update(supplied)
    reader = ReaderConfig(config["retry"], config["safety_window_s"],
                          tuple(config["required_channels"]), tuple(config["required_basic"]))
    for key, upper in (("poll_interval_s", 10), ("liveness_timeout_s", 3600)):
        if type(config[key]) not in (int, float) or not 0 < config[key] <= upper:
            raise ValueError(key + " outside permitted bounds")
    if type(config["samples"]) is not int or not 2 <= config["samples"] <= 100000:
        raise ValueError("samples must be 2..100000")
    return reader, config


UNIFIED_RECORD_SCHEMA = {
    'scope':'OFFLINE_OR_EXPLICIT_FUTURE_HARDWARE_OBSERVATION',
    'feature':['host_time','session.epoch','seq_before','seq_after','frame_id','snapshot_valid','basic.raw/value/valid','channels.numeric_valid/status/reasons','channels.features.raw/value','channels.formal_identity/acceptance','retry','stale','skip'],
    'raw':['host_time','epoch','bank','token','frame_id','sample_count','channel_mask','owner_valid','frame_valid','status','format','copy_duration','ack_result','drop_diagnostics','association','association_reason'],
    'raw_storage':'npz: local uint32 words + local CH1/CH2 int16 arrays + JSON metadata; no live device view',
    'timing':'host/copy observation only, not ADC capture timestamp or performance acceptance',
}
