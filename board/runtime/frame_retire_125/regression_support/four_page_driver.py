"""Immutable four-page driver for guarded unified_2; no import-time I/O."""
import hashlib,json
from pathlib import Path
from closure_driver import MM2S,VLNV,validate_description,check_buffer
from touch_pages import PAGES

class FourPageMM2S(MM2S):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.pages=()
        self.filled=False
        self.ever_started=False
        self.faulted=False
        self.requested_slot=0
        self._freed_ids=set()
        self._release_failed=False

    def stage_pages(self,pages):
        with self.lock:
            if self.pages or self.buffer is not None or self.owner!="none":
                raise RuntimeError("Cannot replace a held page group")
            pages=tuple(pages)
            if len(pages)!=4 or len({id(p) for p in pages})!=4:
                raise ValueError("Exactly four distinct buffers required")
            ranges=[]
            for frame in pages:
                if getattr(frame,"freed",False):
                    raise ValueError("Freed buffer")
                if tuple(frame.shape)!=(720,1280,3) or tuple(frame.strides)!=(3840,3,1) or frame.dtype.name!="uint8":
                    raise ValueError("Tight BGR24 uint8 required")
                base,size=int(frame.physical_address),int(frame.nbytes)
                check_buffer(base,size)
                ranges.append((base,base+size))
            ordered=sorted(ranges)
            if any(a[1]>b[0] for a,b in zip(ordered,ordered[1:])):
                raise ValueError("Physical allocations overlap")
            self.pages=pages  # Strong references retained before any MMIO.

    def attach(self,frame):
        with self.lock:
            if not self.pages or frame is not self.pages[0]:
                raise RuntimeError("Attach the first staged immutable page")
            super().attach(frame)

    def fill_pages(self,assets):
        with self.lock:
            if self.owner!="cpu" or self.ever_started:
                raise RuntimeError("Fill only before the first DMA start")
            blobs=[]
            for page in PAGES:
                folder=Path(assets)/page
                manifest=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
                blob=(folder/"ui_frame.bgr").read_bytes()
                if len(blob)!=2764800 or hashlib.sha256(blob).hexdigest()!=manifest["bgr_sha256"]:
                    raise ValueError("Page identity mismatch: "+page)
                blobs.append(blob)
            import numpy as np
            for frame,blob in zip(self.pages,blobs):
                frame[:]=np.frombuffer(blob,dtype="uint8").reshape(720,1280,3)
            self.filled=True

    def write(self,offset,value):
        if offset==0x28:
            if type(value) is not int or value not in range(4):
                raise ValueError("Park reference must be 0..3")
            self.park(value)
        else:
            super().write(offset,value)

    def start(self):
        with self.lock:
            if self.owner!="cpu" or not self.filled or len(self.pages)!=4 or self.ever_started or self.faulted:
                raise RuntimeError("Fresh fully prepared page group required; no warm restart")
            if not self.status()&1 or self.read(0)&4:
                raise RuntimeError("Channel not reset/stopped")
            for frame in self.pages:
                frame.flush()
            for frame in self.pages:
                frame.setflags(write=False)
            self.ever_started=True
            self.owner="dma"  # Before first programming write; failures quarantine all pages.
            try:
                self.write(0x28,0)
                for index,frame in enumerate(self.pages):
                    self.write(0x5c+4*index,int(frame.physical_address))
                self.write(0x54,3840)
                self.write(0x58,3840)
                self.write(0,0x10001)
                self.write(0x50,720)
                self.wait(lambda:not self.status()&1)
                if not self.read(0)&1:
                    raise RuntimeError("Run bit cleared")
            except BaseException:
                self.faulted=True
                raise

    def select_page(self,slot):
        from joint_adapter import select_static_page
        return select_static_page(self,slot)

    def stop(self):
        from joint_adapter import stop_video
        return stop_video(self)

    def release(self):
        if self.ever_started:
            raise RuntimeError("PL drain fence unavailable; retain all references")
        return super().release()


def register_four_page_driver(default_ip=None,bindings=None):
    if bindings is None:raise RuntimeError("Verified unified_2 programming bindings required")
    bindings.revalidate()
    if default_ip is None:
        from pynq import DefaultIP
        default_ip=DefaultIP
    class SnapshotPagesVDMA(default_ip):
        bindto=[VLNV]
        def __init__(self,description):
            bindings.revalidate()
            validate_description(description)
            super().__init__(description)
            self.channel=FourPageMM2S(bindings.ios["dma"])
    return SnapshotPagesVDMA

