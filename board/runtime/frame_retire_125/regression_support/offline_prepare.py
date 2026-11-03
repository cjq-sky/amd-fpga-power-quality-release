"""Offline software model only. No PYNQ, MMIO, overlay or hardware backend."""
import argparse
import csv
import hashlib
import json
import threading
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path


def check_metadata(package, expected_sha=None):
    from joint_adapter import validate_package, HWH_SHA
    return validate_package(package, expected_sha or HWH_SHA)["windows"]


def check_buffer(base, size, stride=3840, mode=0):
    # Only the documented 720p mode0 candidate is modeled, not an approved runtime format.
    if any(type(x) is not int for x in (base, size, stride, mode)):
        raise ValueError("Integer parameters required")
    if mode != 0 or base < 0 or base % 4 or stride < 3840 or stride % 4:
        raise ValueError("Unsupported mode/alignment/stride")
    required = stride * 720
    if size < required or base + size > 0x20000000:
        raise ValueError("Allocation too small or outside HP0 low DDR")
    return required


class Mock:
    """Synthetic lifecycle and local register rules; NOT a VDMA/VTC simulator."""
    def __init__(self):
        self.trace = []
        self.registers = {}
        self.state = "empty"
        self.flushed = False
        self.source_cleared = False
        self.lock = threading.Lock()

    def log(self, event, **fields):
        self.trace.append(dict(event=event, **fields))

    def write(self, ip, offset, value):
        allowed = (ip == "unpack" and offset == 0x10 and type(value) is int and value == 0
                   or ip == "csc" and offset in range(0x10, 0x69, 8)
                   and type(value) is int and 0 <= value <= 0x3ff)
        if self.state == "running" or not allowed:
            raise ValueError("Register access denied")
        self.registers[ip, offset] = value
        self.log("write", ip=ip, offset=offset, value=value)

    def configure_color(self):
        self.write("unpack", 0x10, 0)
        for offset in range(0x10, 0x69, 8):
            self.write("csc", offset, 256 if offset in (0x10, 0x30, 0x50) else 0)

    def allocate(self, base, size, stride=3840):
        if self.state not in ("empty", "freed"):
            raise RuntimeError("Allocation still owned")
        check_buffer(base, size, stride)
        self.state, self.flushed = "cpu", False
        self.log("allocate", base=base, size=size, stride=stride)

    def flush(self):
        if self.state != "cpu":
            raise RuntimeError("CPU ownership required")
        self.flushed = True
        self.log("flush")

    def start(self):
        expected = {("unpack", 0x10): 0}
        expected.update({("csc", o): 256 if o in (0x10, 0x30, 0x50) else 0
                         for o in range(0x10, 0x69, 8)})
        if self.state != "cpu" or not self.flushed or self.registers != expected:
            raise RuntimeError("Buffer flush and complete nonblack color setup required")
        self.state = "running"
        self.log("synthetic_start")

    def wait(self, observations, attempts):
        if type(attempts) is not int or attempts < 1:
            raise ValueError("Positive bounded attempts required")
        iterator = iter(observations)
        for _ in range(attempts):
            if next(iterator, False):
                self.log("synthetic_wait_complete")
                return
        self.log("timeout")
        raise TimeoutError("Synthetic wait exhausted")

    def stop(self, observations=(True,), attempts=3):
        if self.state != "running":
            raise RuntimeError("Not running")
        self.wait(observations, attempts)
        self.state, self.flushed = "cpu", False
        self.log("synthetic_stop")

    def free(self):
        if self.state != "cpu":
            raise RuntimeError("Cannot release unallocated or DMA-owned memory")
        self.state = "freed"
        self.log("free")

    @contextmanager
    def reader(self):
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("Concurrent reader rejected")
        try:
            yield
        finally:
            self.lock.release()

    def clear_irq_source(self):
        self.source_cleared = True
        self.log("synthetic_irq_source_clear")

    def ack_irq(self):
        if not self.source_cleared:
            raise RuntimeError("Clear source before acknowledging INTC")
        self.source_cleared = False
        self.log("synthetic_intc_ack")


def require_hardware_ready():
    raise RuntimeError("BLOCKED: DRP/reset/format/driver and PL/A authorization unconfirmed")


def main():
    raise SystemExit("Use ../run_offline.py for the joint Mock suite")

if __name__=="__main__":main()
