"""Bounded seq double-read. Caller owns the overlay/reset epoch exclusively."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import time
from lab07_registers import (SNAPSHOT_BODY, REGISTERS, BASIC_FIELDS, SPECTRAL_FIELDS,
                             VALID_BITS, NUMERIC_BITS, NUMERIC_FATAL_MASK,
                             NUMERIC_DEFINED_MASK, FORMAL_DEFINED_MASK,
                             SEQ_MODULUS, SEQ_HALF_SPACE, MAX_SAFE_WINDOW,
                             CHANNEL_STATUS_SHIFT, CHANNEL_IDENTITY_SHIFT, FORMAL_BITS)
from lab07_decode import decode_register, identity_name
from lab07_mmio import verify_abi, read_name, AbiMismatch


@dataclass(frozen=True)
class ReaderConfig:
    retry: int = 3
    safety_window_s: float = 1.0
    required_channels: tuple = ("CH1", "CH2")
    required_basic: tuple = ()

    def __post_init__(self):
        if type(self.retry) is not int or not 1 <= self.retry <= 100:
            raise ValueError("retry must be finite, in 1..100")
        if not 0 < self.safety_window_s < MAX_SAFE_WINDOW:
            raise ValueError("window must be below the 125 MHz seq-wrap bound")
        if any(c not in SPECTRAL_FIELDS for c in self.required_channels):
            raise ValueError("unknown required channel")
        if any(n not in BASIC_FIELDS for n in self.required_basic):
            raise ValueError("unknown required basic field")


@dataclass
class ReaderState:
    last_seq: int = None
    last_frame_id: int = None
    epoch: object = None

    def clear(self, epoch=None):
        self.last_seq = self.last_frame_id = None
        self.epoch = epoch


@dataclass
class SnapshotResult:
    status: str
    host_time: str
    seq_before: int = None
    seq_after: int = None
    frame_id: int = None
    snapshot_valid: bool = False
    consistent: bool = False
    retry: int = 0  # Additional attempts, not total attempts.
    elapsed_s: float = 0.0
    stale: bool = False
    skip: int = 0  # Skipped PUBLICATIONS, not raw/acquisition frames.
    raw: dict = field(default_factory=dict)
    basic: dict = field(default_factory=dict)
    channels: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)
    session: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    def spectral_inputs(self, channel):
        """Strict default consumption: no stale/invalid/torn/missing-feature fallback."""
        if self.status != "CONSISTENT" or not self.channels[channel]["consumable"]:
            return None
        return {name: v["value"] for name, v in self.channels[channel]["features"].items()}


def _decode_tuple(result, config):
    raw = result.raw
    acquisition = bool(raw["FEATURE_ACQUISITION_VALID"])
    mask = raw["FEATURE_VALID_MASK"]
    errors = result.reasons
    for name in raw:
        if raw[name] >> REGISTERS[name].bits:
            errors.append(name + ": reserved upper bits nonzero")
    for name in BASIC_FIELDS:
        try:
            value = decode_register(name, raw[name])
        except ValueError as e:
            errors.append(str(e))
            value = {"raw": raw[name], "value": None}
        value["valid"] = acquisition and bool(mask & (1 << VALID_BITS[name]))
        if not value["valid"]:
            value["value"] = None
        result.basic[name] = value
    if not acquisition:
        errors.append("FEATURE_ACQUISITION_VALID=0")
    for index, channel in enumerate(("CH1", "CH2")):
        numeric = (raw["SPECTRAL_NUMERIC_STATUS"] >> CHANNEL_STATUS_SHIFT[channel]) & 0xffff
        formal = (raw["SPECTRAL_STATUS"] >> CHANNEL_STATUS_SHIFT[channel]) & 0xffff
        identity = (raw["FORMAL_IDENTITY"] >> CHANNEL_IDENTITY_SHIFT[channel]) & 3
        valid = bool(numeric & (1 << NUMERIC_BITS["VALID"]))
        fatal = numeric & NUMERIC_FATAL_MASK
        channel_errors = []
        if numeric & ~NUMERIC_DEFINED_MASK or formal & ~FORMAL_DEFINED_MASK:
            channel_errors.append("reserved status bits nonzero")
        if valid != bool(mask & (1 << VALID_BITS[channel + "_SPECTRAL"])):
            channel_errors.append("numeric status/mask disagreement")
        if valid == bool(fatal):
            channel_errors.append("numeric valid/fatal contract disagreement")
        if not valid and any(raw[n] for n in SPECTRAL_FIELDS[channel]):
            channel_errors.append("invalid group must publish six zero words")
        features = {n: decode_register(n, raw[n]) for n in SPECTRAL_FIELDS[channel]}
        consumable = acquisition and valid and not channel_errors
        if not consumable:
            for v in features.values():
                v["value"] = None
                if "percent" in v:
                    v["percent"] = None
        result.channels[channel] = {
            "numeric_valid": valid, "numeric_status": numeric,
            "numeric_reasons": [n for n, bit in NUMERIC_BITS.items()
                                if n != "VALID" and numeric & (1 << bit)],
            "boundary_warning": bool(numeric & (1 << NUMERIC_BITS["RANGE_BOUNDARY_GUARD_USED"])),
            "formal_status": formal, "formal_identity": identity_name(identity),
            "formal_acceptance": bool(formal & (1 << FORMAL_BITS["ACCEPTANCE"])), "consumable": consumable,
            "features": features, "protocol_errors": channel_errors,
            "load_class": None, "accuracy_qualified": False}
        errors.extend(channel + ": " + e for e in channel_errors)
        if channel in config.required_channels and not consumable:
            errors.append(channel + ": required numeric group unavailable")
    for name in config.required_basic:
        if not result.basic[name]["valid"]:
            errors.append(name + ": required basic feature unavailable")
    if errors:
        result.status = "INVALID"


def read_consistent_snapshot(mmio, config=None, state=None, clock=time.monotonic,
                             epoch_getter=lambda: 0):
    config = config or ReaderConfig()
    state = state if state is not None else ReaderState()
    result = SnapshotResult("RETRY_EXHAUSTED", datetime.now(timezone.utc).isoformat())
    abi_epoch = epoch_getter()
    try:
        abi_info = verify_abi(mmio)
    except AbiMismatch as e:
        result.status, result.reasons = "ABI_MISMATCH", [str(e)]
        result.session['error_code'] = getattr(e,'code','ABI_UNSUPPORTED')
        return result
    for attempt in range(config.retry):
        started, epoch = clock(), epoch_getter()
        if epoch != abi_epoch:
            state.clear()
            result.status, result.reasons = "INVALID", ["epoch changed across ABI verification"]
            return result
        if state.epoch != epoch:
            state.clear(epoch)
        before = read_name(mmio, "SNAPSHOT_SEQ")
        raw = {n: read_name(mmio, n) for n in SNAPSHOT_BODY}
        after = read_name(mmio, "SNAPSHOT_SEQ")
        elapsed = clock() - started
        result = SnapshotResult("RETRY_EXHAUSTED", result.host_time, before, after,
                                raw["FRAME_ID"], raw["SNAPSHOT_VALID"] == 1,
                                retry=attempt, elapsed_s=elapsed)
        if epoch_getter() != epoch:
            state.clear()
            result.status, result.reasons = "INVALID", ["epoch changed during read"]
            return result
        if before != after or not 0 <= elapsed < config.safety_window_s:
            result.reasons = ["sequence changed" if before != after else "safety window exceeded"]
            continue  # Discard the entire torn/expired tuple.
        result.consistent, result.raw = True, raw
        if raw["SNAPSHOT_VALID"] != 1:
            result.status = "NO_NEW_FRAME" if raw["SNAPSHOT_VALID"] == 0 else "INVALID"
            result.reasons = ["snapshot not published" if result.status == "NO_NEW_FRAME"
                              else "SNAPSHOT_VALID reserved bits nonzero"]
            return result
        if state.last_seq is not None:
            delta = (after - state.last_seq) % SEQ_MODULUS
            if delta == 0:
                result.status, result.stale = "STALE", True
                result.reasons = ["same publication sequence repeated"]
                return result
            if delta >= SEQ_HALF_SPACE:
                result.status, result.reasons = "INVALID", ["sequence order ambiguous/reset suspected"]
                return result
            result.skip = delta - 1
        state.last_seq, state.last_frame_id = after, result.frame_id
        result.status = "CONSISTENT"
        _decode_tuple(result, config)
        from lab07_abi import apply_capabilities
        apply_capabilities(result, config, abi_info)
        result.session['epoch'] = epoch
        return result
    return result


class SnapshotReader:
    def __init__(self, mmio, config=None, clock=time.monotonic, epoch_getter=lambda: 0):
        self.mmio, self.config, self.clock = mmio, config, clock
        self.state, self.epoch_getter = ReaderState(), epoch_getter

    def read(self):
        return read_consistent_snapshot(self.mmio, self.config, self.state,
                                        self.clock, self.epoch_getter)
