"""Nonblocking USB view requests only; never writes VDMA or owns a framebuffer."""
import os
import struct
import time


class TouchInput:
    def __init__(self, record):
        self.record = record
        self.fd = None
        self.pending = b''
        self.event = struct.Struct('@llHHi')
        self.last_click = -float('inf')

    def open(self):
        import fcntl
        from usb_touch import find_touch_device, TouchDecoder
        self.close()
        device = find_touch_device()
        fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
        try:
            self.decoder = TouchDecoder()
            self.ranges = []
            for axis in (0, 1):
                request = 0x80000000 | (24 << 16) | (ord('E') << 8) | (0x40 + axis)
                values = struct.unpack('=6i', fcntl.ioctl(fd, request, bytes(24)))
                if values[2] <= values[1]:
                    raise RuntimeError('Invalid touch axis range')
                self.ranges.append((values[1], values[2]))
                if axis == 0:
                    self.decoder.x = values[0]
                else:
                    self.decoder.y = values[0]
            self.fd = fd
            self.pending = b''
            self.record('TOUCH_READY', device=str(device), ranges=self.ranges, policy='LATEST_LOGICAL_VIEW_ONLY')
        except BaseException:
            os.close(fd)
            raise

    def decode(self, data):
        from touch_pages import scale_point, hit_test
        self.pending += data
        latest = None
        while len(self.pending) >= self.event.size:
            _, _, kind, code, value = self.event.unpack(self.pending[:self.event.size])
            self.pending = self.pending[self.event.size:]
            was_dropped = self.decoder.dropped
            point = self.decoder.feed(kind, code, value)
            if was_dropped and kind == 0 and code == 0 and self.fd is not None:
                import fcntl
                for axis in (0,1):
                    request = 0x80000000 | (24 << 16) | (ord('E') << 8) | (0x40 + axis)
                    values = struct.unpack('=6i', fcntl.ioctl(self.fd, request, bytes(24)))
                    if axis == 0:
                        self.decoder.x = values[0]
                    else:
                        self.decoder.y = values[0]
            if kind == 0 and code == 3:
                self.record('TOUCH_SYN_DROPPED', action='Discard contact; require a new press/release')
            if point is None:
                continue
            now = time.monotonic()
            if now - self.last_click < .12:
                continue
            self.last_click = now
            x, y = scale_point(*point, *self.ranges)
            page = hit_test(x, y)
            self.record('TOUCH_VIEW_REQUEST', x=x, y=y, page=page, raw=list(point))
            if page is not None:
                latest = page
        return latest

    def poll(self):
        latest = None
        if self.fd is None:
            return None
        try:
            for _ in range(16):
                try:
                    data = os.read(self.fd, self.event.size * 64)
                except BlockingIOError:
                    break
                if not data:
                    raise OSError('Touch device disconnected')
                page = self.decode(data)
                if page is not None:
                    latest = page
        except OSError as error:
            self.record('TOUCH_DISCONNECTED', exception=repr(error), action='Keep acquisition/video; touch on after reconnect')
            self.close()
        return latest

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        self.pending = b''
