"""Raster worker only: no PYNQ, Reader, Event, model or framebuffer mappings."""
import json
import os
import sys
import time
import importlib
from pathlib import Path
from display_snapshot import DisplaySnapshot
from hdmi_renderer import Renderer, PAGES


def main():
    if hasattr(os, 'sched_getaffinity'):
        available = os.sched_getaffinity(0)
        if len(available) > 1:
            os.sched_setaffinity(0, {max(available)})
        os.nice(5)
    renderer = Renderer(sys.argv[1])
    renderer_module = importlib.import_module('hdmi_renderer')
    renderer_path = Path(renderer_module.__file__)
    renderer_stamp = renderer_path.stat().st_mtime_ns
    waiting = DisplaySnapshot.capture(dict(status='WAITING', metrics={}, age_s=None),
                                      source_note='等待真实采集快照')
    for page in PAGES:
        renderer.render(waiting, page)
    output = sys.stdout.buffer
    output.write((json.dumps(dict(event='RENDER_WORKER_READY', pid=os.getpid(), sensor_access=False,
                                 chinese_font=renderer.font_path, latin_font=renderer.latin_font_path,
                                 cpu_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None))+'\n').encode())
    output.flush()
    for line in sys.stdin.buffer:
        request = json.loads(line)
        stamp = renderer_path.stat().st_mtime_ns
        if stamp != renderer_stamp:
            # This child owns raster pixels only: replace text/render code between requests.
            renderer_module = importlib.reload(renderer_module)
            renderer = renderer_module.Renderer(sys.argv[1])
            renderer_stamp = stamp
        snapshot = DisplaySnapshot(request['payload'], request['captured_at'], request['source_note'])
        start = time.monotonic()
        pixels = renderer.bgr(snapshot, request['page'])
        header = dict(event='RASTER_COMPLETE', id=request['id'], bytes=pixels.nbytes,
                      raster_seconds=time.monotonic()-start)
        output.write((json.dumps(header)+'\n').encode())
        output.write(pixels.tobytes()); output.flush()


if __name__ == '__main__':
    main()
