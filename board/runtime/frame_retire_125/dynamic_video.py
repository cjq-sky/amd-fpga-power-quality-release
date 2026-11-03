"""Cold dynamic start and frame exchange; never writes legacy VDMA after start."""
import time
import uuid
from four_page_driver import FourPageMM2S
from frame_retire_driver import FrameRetire


class DynamicMM2S(FourPageMM2S):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fr = FrameRetire(self.mmio)

    def start(self):
        with self.lock:
            if self.owner != 'cpu' or not self.filled or len(self.pages) != 4 or self.ever_started:
                raise RuntimeError('Fresh prepared four-buffer group required')
            if not self.status() & 1 or self.read(0) & 4:
                raise RuntimeError('DMA not reset/stopped')
            for frame in self.pages:
                frame.flush()
                frame.setflags(write=False)
            # Initial legacy geometry before SESSION/first frame; fixed base table thereafter.
            self.park(0)
            for index, frame in enumerate(self.pages):
                self.write(0x5c + 4 * index, int(frame.physical_address))
            self.write(0x54, 3840)
            self.write(0x58, 3840)
            self.ever_started = True  # Retain allocations even for uncertain SESSION arm.
            self.owner = 'dma'
            self.fr.arm([int(f.physical_address) for f in self.pages], uuid.uuid4().int)
            self.write(0, 0x10001)
            self.write(0x50, 720)  # First frame command; no further legacy writes.
            self.wait(lambda: not self.status() & 1)
            self.requested_slot = 0

    def present(self, assets, view, record, iteration_log, seq):
        """One caller/lock: immutable page asset is a protocol-test pattern only."""
        from pathlib import Path
        import hashlib
        import json
        import numpy as np
        with self.lock:
            if self.fr.failed:
                raise RuntimeError('Quarantined session')
            slot = 1 if self.fr.active == 0 else 0  # A/B alternation, four bases unchanged.
            if not self.fr.can_draw(slot):
                raise RuntimeError('No CPU-owned target')
            folder = Path(assets) / view
            blob = (folder / 'ui_frame.bgr').read_bytes()
            expected = json.loads((folder / 'manifest.json').read_text())['bgr_sha256']
            if len(blob) != 2764800 or hashlib.sha256(blob).hexdigest() != expected:
                raise RuntimeError('Protocol-test pattern changed')
            frame = self.pages[slot]
            frame.setflags(write=True)
            frame[:] = np.frombuffer(blob, dtype='u1').reshape(720, 1280, 3)
            # A changing top marker helps distinguish submissions without claiming pixel completion.
            frame[:12, :] = (seq % 256, (seq * 61) % 256, (seq * 113) % 256)
            frame.flush()
            frame.setflags(write=False)
            record('DRAW_FLUSH_COMPLETE', iteration=seq, slot=slot, base=hex(int(frame.physical_address)),
                   view=view, buffer_bytes=int(frame.nbytes))
            result = self.fr.exchange(slot, seq)
            self.requested_slot = slot
            result.update(iteration=seq, session='%032x' % self.fr.generation,
                          view=view, monotonic=time.monotonic(), screen_result='PENDING',
                          underflow='NOT_MEASURED', tear='NOT_MEASURED')
            iteration_log.write(json.dumps(result) + '\n')
            iteration_log.flush()
            record('FRAME_RETIRE_ITERATION', **result)
            return result
