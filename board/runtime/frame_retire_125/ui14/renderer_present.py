"""Renderer-to-FrameRetire adapter; caller owns existing board leases and log context."""
import json
import time


def present_snapshot(driver, renderer, snapshot, page, seq, record, iteration_log):
    # This function consumes a local snapshot; it never opens Reader/Event/model instances.
    with driver.lock:
        slot = 1 if driver.fr.active == 0 else 0
        if not driver.fr.can_draw(slot):
            raise RuntimeError('No CPU-owned render target; preserve latest request without writing')
        pixels = renderer.bgr(snapshot, page)
        frame = driver.pages[slot]
        if pixels.shape != (720, 1280, 3) or pixels.nbytes != 2764800:
            raise ValueError('Invalid BGR24 renderer output')
        frame.setflags(write=True)
        frame[:] = pixels
        frame.flush()
        frame.setflags(write=False)
        record('DRAW_FLUSH_COMPLETE', iteration=seq, slot=slot, view=page,
               base=hex(int(frame.physical_address)), buffer_bytes=int(frame.nbytes),
               renderer='UI14_DISPLAY_SNAPSHOT', snapshot_source=snapshot.source_note)
        result = driver.fr.exchange(slot, seq)
        driver.requested_slot = slot
        result.update(iteration=seq, monotonic=time.monotonic(), view=page,
                      renderer='UI14_DISPLAY_SNAPSHOT', screen_result='PENDING',
                      underflow='NOT_MEASURED', tear='NOT_MEASURED')
        iteration_log.write(json.dumps(result) + '\n')
        iteration_log.flush()
        record('FRAME_RETIRE_ITERATION', **result)
        return result
