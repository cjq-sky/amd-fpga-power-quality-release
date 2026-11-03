"""Read Linux single-touch evdev; no module-import I/O or DMA lifecycle changes."""
import json,os,select,struct,time
from pathlib import Path
from touch_pages import PAGES,hit_test,scale_point

class TouchDecoder:
    def __init__(self):
        self.x=self.y=0
        self.pressed=False
        self.release_pending=False
        self.dropped=False
    def feed(self,kind,code,value):
        if kind==0 and code==3:  # SYN_DROPPED: discard contact, don't fabricate a click.
            self.pressed=self.release_pending=False
            self.dropped=True
            return None
        if self.dropped:
            if kind==0 and code==0:self.dropped=False
            return None
        if kind==3:
            if code==0:self.x=value
            elif code==1:self.y=value
        elif kind==1 and code==0x14a:
            if value==1:self.pressed=True
            elif value==0 and self.pressed:self.release_pending=True
        elif kind==0 and code==0 and self.release_pending:
            self.pressed=self.release_pending=False
            return self.x,self.y
        return None

def find_touch_device():
    matches=[]
    for path in Path("/sys/class/input").glob("event*/device/name"):
        if path.read_text().strip()=="wch.cn USB2IIC_CTP_CONTROL":
            matches.append(Path("/dev/input")/path.parents[1].name)
    if len(matches)!=1:
        raise RuntimeError("Need one verified USB2IIC touch device, got "+str(matches))
    return matches[0]

def run_touch(dma,log_path,duration_seconds=None):
    """Explicit foreground loop. Ctrl+C closes input only; leaves DMA and pages held."""
    import fcntl  # Only on Linux when explicitly called.
    if duration_seconds is not None and duration_seconds<=0:
        raise ValueError("Positive duration required")
    device=find_touch_device()
    fd=os.open(device,os.O_RDONLY|os.O_NONBLOCK)
    event=struct.Struct("@llHHi")
    decoder=TouchDecoder()
    pending=b""
    started=time.monotonic()
    last_click=-float("inf")
    last_health=started
    log=None;first=None
    try:
        log=Path(log_path).open("a",encoding="utf-8",buffering=1)
        def record(kind,**fields):
            item=dict(event=kind,monotonic=time.monotonic(),**fields)
            log.write(json.dumps(item,ensure_ascii=False)+chr(10));log.flush()
            return item
        try:
            ranges=[]
            for axis in (0,1):
                request=0x80000000|(24<<16)|(ord("E")<<8)|(0x40+axis)
                values=struct.unpack("=6i",fcntl.ioctl(fd,request,bytes(24)))
                ranges.append((values[1],values[2]))
                if axis==0:decoder.x=values[0]
                else:decoder.y=values[0]
                if values[2]<=values[1]:raise ValueError("Invalid ABS range")
            record("touch_ready",device=str(device),ranges=ranges,
                   current_requested_page=PAGES[dma.requested_slot])
            print("触摸监听已启动；只选择帧槽。Ctrl+C仅结束监听，显示继续。",flush=True)
            while duration_seconds is None or time.monotonic()-started<duration_seconds:
                if time.monotonic()-last_health>=5:
                    if dma.owner!="dma" or dma.faulted or dma.status()&1 or not dma.read(0)&1:
                        raise RuntimeError("DMA health check failed; keep all buffers")
                    last_health=time.monotonic()
                ready,_,_=select.select([fd],[],[],0.2)
                if not ready:continue
                chunk=os.read(fd,event.size*64)
                if not chunk:raise OSError("Touch device disconnected")
                pending+=chunk
                while len(pending)>=event.size:
                    _,_,kind,code,value=event.unpack(pending[:event.size])
                    pending=pending[event.size:]
                    was_dropped=decoder.dropped
                    point=decoder.feed(kind,code,value)
                    if was_dropped and kind==0 and code==0:
                        for axis in (0,1):
                            req=0x80000000|(24<<16)|(ord("E")<<8)|(0x40+axis)
                            pos=struct.unpack("=6i",fcntl.ioctl(fd,req,bytes(24)))[0]
                            if axis==0:decoder.x=pos
                            else:decoder.y=pos
                    if point is None:continue
                    now=time.monotonic()
                    if now-last_click<0.12:continue
                    last_click=now
                    x,y=scale_point(*point,*ranges)
                    page=hit_test(x,y)
                    if page is None:
                        record("touch_outside_navigation",raw=list(point),x=x,y=y)
                        continue
                    slot=PAGES.index(page)
                    dma.select_page(slot)
                    item=record("page_request_sent",raw=list(point),x=x,y=y,
                                slot=slot,requested_page=page,
                                visual_confirmation="PENDING")
                    print(json.dumps(item,ensure_ascii=False),flush=True)
        except KeyboardInterrupt:
            record("input_listener_interrupted",dma_owner=dma.owner)
            print("监听已结束；未stop、未释放Buffer。",flush=True)
        except BaseException as exc:
            try:record("listener_failed",error=repr(exc),dma_owner=dma.owner)
            except BaseException as cleanup:exc.cleanup_errors=list(getattr(exc,'cleanup_errors',[]))+[repr(cleanup)]
            raise
    except BaseException as exc:
        first=exc;raise
    finally:
        errors=[]
        for close in (lambda:os.close(fd),lambda:log.close() if log is not None else None):
            try:close()
            except BaseException as exc:errors.append(exc)
        if errors:
            if first is not None:first.cleanup_errors=list(getattr(first,'cleanup_errors',[]))+[repr(e) for e in errors]
            else:raise errors[0]


