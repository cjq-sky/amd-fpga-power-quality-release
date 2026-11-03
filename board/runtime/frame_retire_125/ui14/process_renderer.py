"""Raster-only subprocess; the parent remains the sole Reader and DMA owner."""
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import numpy as np


class ProcessRenderer:
    def __init__(self, font_path, error_path, timeout=20):
        self.timeout, self.request_id = timeout, 0
        self.lock, self.responses = threading.Lock(), queue.Queue()
        self.errors = Path(error_path).open('ab', buffering=0)
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        self.process = subprocess.Popen([sys.executable, '-u', str(Path(__file__).with_name('render_worker.py')),
                                        str(font_path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=self.errors, bufsize=0, creationflags=flags)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            ready = self._response()
        except BaseException:
            self.close()
            raise
        if ready.get('event') != 'RENDER_WORKER_READY':
            self.close(); raise RuntimeError('Raster worker failed to start: ' + str(ready))
        self.identity = ready

    def _read(self):
        try:
            while True:
                line = self.process.stdout.readline()
                if not line:
                    raise RuntimeError('Raster worker exited')
                header = json.loads(line)
                count = header.get('bytes', 0)
                if count not in (0, 2764800):
                    raise RuntimeError('Unexpected raster payload size')
                chunks, received = [], 0
                while received < count:
                    chunk = self.process.stdout.read(count - received)
                    if not chunk:
                        raise RuntimeError('Partial raster output')
                    chunks.append(chunk); received += len(chunk)
                self.responses.put((header, b''.join(chunks)))
        except BaseException as error:
            self.responses.put((dict(error=repr(error)), b''))

    def _response(self):
        try:
            header, data = self.responses.get(timeout=self.timeout)
        except queue.Empty:
            self.close(); raise TimeoutError('Raster worker wall-clock timeout')
        if 'error' in header:
            raise RuntimeError('Raster worker: ' + header['error'])
        self.last_bytes = data
        return header

    def bgr(self, snapshot, page):
        with self.lock:
            self.request_id += 1
            request = dict(id=self.request_id, page=page, payload=snapshot.payload,
                           captured_at=snapshot.captured_at, source_note=snapshot.source_note)
            packet = (json.dumps(request, ensure_ascii=False) + '\n').encode('utf-8')
            # Unbuffered pipe writes may be partial; keep the one request complete.
            sent = 0
            while sent < len(packet):
                count = self.process.stdin.write(packet[sent:])
                if not count:
                    raise RuntimeError('Raster request pipe closed')
                sent += count
            header = self._response()
            if header.get('id') != self.request_id or len(self.last_bytes) != 2764800:
                raise RuntimeError('Raster response identity/length mismatch')
            self.last_timing = header
            return np.frombuffer(self.last_bytes, dtype='u1').reshape(720, 1280, 3)

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=2)
        for pipe in (self.process.stdin, self.process.stdout):
            if pipe:
                pipe.close()
        self.errors.close()
