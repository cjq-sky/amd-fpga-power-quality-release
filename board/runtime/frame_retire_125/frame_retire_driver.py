"""Frozen 125MHz Frame Retire protocol. Inject logged, ordered 32-bit MMIO."""
import time


class FrameRetire:
    def __init__(self, io, *, timeout=2.0, now=time.monotonic, sleep=time.sleep):
        if not 0 < timeout <= 5:
            raise ValueError('Finite wall-clock timeout required')
        self.io, self.timeout, self.now, self.sleep = io, timeout, now, sleep
        self.failed = self.armed = self.attempted = False
        self.generation = None
        self.bases = ()
        self.active = 0
        self.cpu_owned = set()
        self.last_seq = 0

    def require(self, ok, message):
        if not ok:
            self.failed = True
            raise RuntimeError(message)

    def read(self, offset):
        try:
            return int(self.io.read(offset))
        except BaseException:
            self.failed = True
            raise

    def write(self, offset, value):
        try:
            self.io.write(offset, value)
        except BaseException:
            self.failed = True
            raise

    def wide(self, offset, words):
        return sum(self.read(offset + i * 4) << (32 * i) for i in range(words))

    def write_wide(self, offset, value, words):
        for i in range(words):
            self.write(offset + i * 4, (value >> (32 * i)) & 0xffffffff)

    def status(self):
        s, error = self.read(0x104), self.read(0x108)
        self.require(not self.failed and not s & ~0x3f and not s & 0x20 and error == 0,
                     'Frame Retire fault/invalid status; isolate all unreturned buffers')
        return s

    def arm(self, bases, generation):
        self.require(not self.attempted and not self.failed, 'Arm once per proven cold configuration')
        self.attempted = True
        self.require(type(generation) is int and 0 < generation < 1 << 128, 'Nonzero 128-bit generation required')
        self.require(len(bases) == 4 and all(type(b) is int and b >= 0 and b % 4096 == 0
                                          and b + 2764800 <= 0x20000000 for b in bases),
                     'Four allocator-owned aligned low-DDR buffers required')
        ordered = sorted(bases)
        self.require(all(a + 2764800 <= b for a, b in zip(ordered, ordered[1:])), 'Overlapping buffers')
        self.require(self.read(0x100) == 0x46520101 and self.status() == 0, 'Not a fresh FR configuration')
        for i, base in enumerate(bases):
            self.write(0x130 + i * 4, base)
        self.write_wide(0x110, generation, 4)
        self.require(tuple(self.read(0x130 + i * 4) for i in range(4)) == tuple(bases)
                     and self.wide(0x110, 4) == generation, 'Cold configuration readback mismatch')
        self.generation, self.bases = generation, tuple(bases)
        self.write(0x10c, 1)
        self.require(self.status() == 1 and self.read(0x154) == 0
                     and self.wide(0x110, 4) == generation, 'SESSION enable not confirmed')
        self.armed = True
        self.cpu_owned = {1, 2, 3}

    def can_draw(self, slot):
        return self.armed and not self.failed and slot in self.cpu_owned

    def exchange(self, slot, seq):
        """Caller holds sole submission lock and has completed render/flush/ordering."""
        self.require(self.can_draw(slot) and type(slot) is int and slot in range(4), 'Target is not CPU-owned')
        self.require(type(seq) is int and self.last_seq < seq < 1 << 64, 'Nonzero increasing full 64-bit seq required')
        self.require(self.status() & 0x1f == 3 and self.wide(0x110, 4) == self.generation
                     and self.read(0x154) == self.active
                     and self.read(0x130 + slot * 4) == self.bases[slot], 'Session/base not idle/started/current')
        old = self.active
        self.cpu_owned.remove(slot)  # Uncertain command can never return this buffer automatically.
        self.write_wide(0x180, self.generation, 4)
        self.write_wide(0x120, seq, 2)
        self.write(0x128, slot)
        self.write(0x12c, 1)  # Doorbell last, never replay.
        deadline = self.now() + self.timeout
        while True:
            s = self.status()
            self.require(s & 3 == 3 and self.wide(0x110, 4) == self.generation, 'Session invalidated')
            accepted = self.wide(0x140, 2)
            if s & 8:
                self.require(accepted == seq, 'Accepted sequence mismatch')
            if s & 0x10:
                self.require(s & 0xc == 0xc, 'Retire without accepted/busy')
                retire_seq, retire_slot = self.wide(0x148, 2), self.read(0x150)
                active = self.read(0x154)
                s2, gen2 = self.status(), self.wide(0x110, 4)
                seq2, slot2 = self.wide(0x148, 2), self.read(0x150)
                self.require(s2 & 0x1f == 0x1f and gen2 == self.generation
                             and retire_seq == seq2 == seq and retire_slot == slot2 == old
                             and active == slot, 'Unstable or mismatched RETIRE; no ACK/reuse')
                break
            self.require(self.now() < deadline, 'RETIRE wall-clock timeout; no retry/reuse')
            self.sleep(.001)
        self.write_wide(0x170, self.generation, 4)
        self.write_wide(0x160, seq, 2)
        self.write(0x168, 1)  # Consume existing valid record, never replay.
        deadline = self.now() + self.timeout
        while True:
            s = self.status()
            self.require(self.wide(0x110, 4) == self.generation and s & 3 == 3, 'ACK session changed')
            if not s & 0x1c:
                break
            self.require(self.now() < deadline, 'ACK consumption uncertain; no retry/reuse')
            self.sleep(.001)
        self.require(self.read(0x154) == slot, 'Active slot changed after ACK')
        self.cpu_owned.add(old)  # Only after full consumption confirmation.
        self.active, self.last_seq = slot, seq
        return dict(generation='%032x' % self.generation, commit_seq=seq, commit_slot=slot,
                    buffer_base=hex(self.bases[slot]), accepted_seq=accepted, active_slot=slot,
                    retire_seq=retire_seq, retire_slot=retire_slot, retire_ack_seq=seq,
                    retire_ack_generation='%032x' % self.generation, ack_after_status=s,
                    FR_ERROR=0, cpu_owned=sorted(self.cpu_owned))
