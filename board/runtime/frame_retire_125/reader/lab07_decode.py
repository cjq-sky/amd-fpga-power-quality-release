"""Raw-bit transparent decoding; no calibration or load classification."""
from lab07_registers import REGISTERS, IDENTITY_NAMES


def decode_register(name, raw):
    spec = REGISTERS[name]
    if type(raw) is not int or not 0 <= raw <= 0xffffffff:
        raise ValueError("MMIO word must be U32")
    if raw >> spec.bits:
        raise ValueError(name + ": nonzero reserved upper bits")
    result = {"raw": raw, "value": raw / spec.scale if spec.scale != 1 else raw,
              "encoding": spec.encoding, "unit": spec.unit}
    if "_THD_ODD_" in name:
        result["percent"] = result["value"] * 100.0
    return result


def identity_name(code):
    if code not in IDENTITY_NAMES:
        raise ValueError("invalid identity code")
    return IDENTITY_NAMES[code]
