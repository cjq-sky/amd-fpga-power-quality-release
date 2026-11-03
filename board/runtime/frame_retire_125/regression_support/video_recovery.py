"""unified_2 injected recovery controller; import never maps or loads hardware.
Polling deadlines apply only to returning accesses, not a blocked AXI transaction.
"""
import math,time
HWH_SHA = '54980f765756f8dc64ade54af7969c7b96054c816a31d88ab9d2c07fbce05b6f'
from offline_prepare import check_buffer
PIXEL_HZ=74_285_714.285714

class RecoveryTimeout(TimeoutError):pass

class WarmReset:
    VLNV='pq.local:user:lab08_warm_reset_ctrl:1.0'
    def __init__(self,io):self.io=io
    def read(self,offset):
        if offset not in (0,4,8,12):raise ValueError('Exact reset offsets only')
        value=self.io.read(offset)
        if type(value) is not int or not 0<=value<2**32:raise ValueError('Reset returned non-U32')
        return value
    def write(self,offset,value):
        if offset!=4 or type(value) is not int or value not in (0,1):raise ValueError('Only HOLD bit0 is writable')
        self.io.write(offset,value)

def check_frame(buffer):
    if (tuple(buffer.shape)!=(720,1280,3) or tuple(buffer.strides)!=(3840,3,1)
        or buffer.dtype.name!='uint8' or getattr(buffer,'freed',False)):
        raise ValueError('Live contiguous BGR24 allocation required')
    return check_buffer(int(buffer.physical_address),int(buffer.nbytes))

class CPUFrame:
    """Keep the actual allocator result; never fabricate a pointer from a log."""
    def __init__(self,allocator,allocation_source):
        if not callable(allocator) or not isinstance(allocation_source,str) or not allocation_source.strip():raise ValueError('Allocator and evidence source required')
        self.buffer=allocator(shape=(720,1280,3),dtype='u1')
        self.source=allocation_source;self.owner='cpu';self.ready=False
        check_frame(self.buffer)
    def complete_draw(self):
        if self.owner!='cpu' or not self.buffer.flags.writeable:raise ValueError('CPU drawing ownership required')
        check_frame(self.buffer);self.ready=True

class RecoveryController:
    def __init__(self,bindings,driver,cold_session,*,now=time.monotonic,sleep=time.sleep,timeout=.5,pixel_hz=PIXEL_HZ):
        if not isinstance(timeout,(int,float)) or not math.isfinite(timeout) or not 0<timeout<=.5:raise ValueError('Returning-access timeout must be in (0,500ms]')
        if not isinstance(pixel_hz,(int,float)) or not math.isfinite(pixel_hz) or abs(pixel_hz-PIXEL_HZ)>PIXEL_HZ*1e-6:raise ValueError('Frozen mode0 pixel clock required')
        self.bindings,self.driver,self.cold=bindings,driver,cold_session
        self.reset=WarmReset(bindings.ios['reset'])
        self.now,self.sleep,self.timeout,self.pixel_hz=now,sleep,timeout,pixel_hz
        self.state='RUNNING';self.failed=False;self.trace=[];self.last_time=None
        if not hasattr(driver,'recovery_frames'):driver.recovery_frames=[]
        self.frames=driver.recovery_frames
        # Old DMA references remain strongly held, even after a successful recovery.
        held=tuple(getattr(driver,'pages',()))+(driver.buffer,)+tuple(f.buffer for f in self.frames)
        self.retained=tuple({id(f):f for f in held if f is not None}.values())
        self.records=[]
    def timestamp(self):
        current=self.now()
        if not isinstance(current,(int,float)) or not math.isfinite(current) or self.last_time is not None and current<self.last_time:raise ValueError('Monotonic clock invalid')
        self.last_time=current
        return current
    def context_check(self):self.bindings.check_context()
    def read(self,ip,offset):
        self.context_check()
        io=self.reset if ip=='reset' else self.driver.mmio
        value=io.read(offset)
        self.trace.append(dict(op='read',ip=ip,offset=offset,value=value,phase=self.state,monotonic=self.timestamp()))
        if type(value) is not int or not 0<=value<2**32:raise ValueError('Non-U32 response')
        if ip=='dma' and offset==4 and value&0xf0:raise RuntimeError('VDMA error '+hex(value))
        return value
    def write(self,ip,offset,value):
        self.context_check()
        self.trace.append(dict(op='write_attempt',ip=ip,offset=offset,value=value,phase=self.state,monotonic=self.timestamp()))
        io=self.reset if ip=='reset' else self.driver.mmio
        io.write(offset,value)
    def wait(self,ip,offset,predicate,label):
        deadline=self.timestamp()+self.timeout
        # An attempt bound also protects a broken injected monotonic/sleep source.
        for _ in range(math.ceil(self.timeout/.0001)+2):
            value=self.read(ip,offset)
            completed=self.timestamp()
            if completed>deadline:raise RecoveryTimeout(label+' (access returned after deadline)')
            if predicate(value):return value
            if completed>=deadline:break
            self.sleep(.0001)
        raise RecoveryTimeout(label)
    def elapsed(self,duration):
        # Absolute deadline plus 1us engineering guard avoids subtraction/cancellation
        # at later recovery cycles and guarantees at least the requested interval.
        deadline=self.timestamp()+duration+1e-6
        for _ in range(math.ceil(duration/.0001)+2):
            remaining=deadline-self.timestamp()
            if remaining<=0:return
            self.sleep(max(remaining,1e-6))
        raise RecoveryTimeout('Required timing-frame observation interval')
    def preflight(self,frame):
        record=self.bindings.revalidate()
        d=self.driver;c=self.cold
        if (d.mmio is not self.bindings.ios['dma'] or d.lock is not c.io_lock or c.failed or not c.used
            or c.records.get('candidate_sha')!=HWH_SHA or not c.records.get('cold_init_completed')
            or c.records.get('programming')!=record or c.records.get('G1')!='CLOCK_SETTLED_FOR_PROBE'
            or c.records.get('G2')!='ACCESS_CHECKS_COMPLETED' or d.owner!='dma' or getattr(d,'faulted',False)):
            raise ValueError('Matching successful guarded cold initialization required')
        if not isinstance(frame,CPUFrame) or frame.owner!='cpu' or not frame.ready or not frame.buffer.flags.writeable:
            raise ValueError('Completed fresh CPU-owned frame required')
        check_frame(frame.buffer)
        a=int(frame.buffer.physical_address);end=a+int(frame.buffer.nbytes)
        for held in list(self.retained)+[f.buffer for f in self.frames]:
            if held is None:continue
            b=int(held.physical_address)
            if a<b+int(held.nbytes) and b<end:raise ValueError('New allocation overlaps a retained DMA allocation')
        if self.read('reset',0)!=0x57520201 or self.read('reset',12)!=32:raise ValueError('Wrong warm_reset ID/MIN_CYCLES')
        if self.read('reset',4)!=0 or self.read('reset',8)&1:raise ValueError('Unresolved HOLD/HELD')
    def recover(self,frame,*,stop_request=None):
        d=self.driver
        if not d.lock.acquire(blocking=False):raise RuntimeError('Concurrent display control rejected')
        touched=False;record=dict(status='IN_PROGRESS',trace_start=len(self.trace))
        try:
            if self.failed:raise RuntimeError('Failed recovery session; automatic retry forbidden')
            if stop_request is not None and not callable(stop_request):raise ValueError('Callable stop request required')
            self.preflight(frame)
            self.frames.append(frame)  # Keep new allocation before the first possible write.
            record.update(programming=dict(self.bindings.record),cold_clock=self.cold.records.get('clock'),fclk_source=self.cold.records.get('fclk_source'),pixel_hz=self.pixel_hz,started=self.timestamp())
            self.records.append(record)
            self.state='STOPPING';touched=True
            record['before']={hex(o):self.read('dma',o) for o in (0,4,0x28,0x50,0x54,0x58,0x5c,0x60,0x64,0x68)}
            if stop_request is None:self.write('dma',0,0x10000)
            else:record['stop_trigger']=stop_request(self)
            self.wait('dma',4,lambda x:bool(x&1),'MM2S HALTED')
            if self.read('dma',0)&1:raise RecoveryTimeout('MM2S RS not cleared')
            self.state='DRAINING';self.elapsed(2*1650*750/self.pixel_hz)
            self.wait('reset',8,lambda x:not x&2,'OLD VIDEO LOCK DROPPED')
            self.state='HOLDING';self.write('reset',4,1)
            if self.read('reset',4)!=1:raise RuntimeError('HOLD request not retained')
            self.wait('reset',8,lambda x:bool(x&1),'RESET HELD >=32 cycles')
            self.state='RELEASING';self.write('reset',4,0)
            if self.read('reset',4)!=0:raise RuntimeError('HOLD release not retained')
            self.wait('reset',8,lambda x:not x&1,'RESET RELEASED')
            self.state='SUBMITTING'
            frame.buffer.flush()
            self.trace.append(dict(op='flush_complete',monotonic=self.timestamp(),source=frame.source))
            frame.buffer.setflags(write=False)
            frame.owner='dma'  # Before any address/RS/VSIZE programming, including failed writes.
            d.video_mode='STATIC_RECOVERY'
            park=self.read('dma',0x28)
            self.write('dma',0x28,park&~0x1f)
            for offset in (0x5c,0x60,0x64,0x68):self.write('dma',offset,int(frame.buffer.physical_address))
            self.write('dma',0x54,3840);self.write('dma',0x58,3840)
            self.write('dma',0,0x10001);self.write('dma',0x50,720)
            self.wait('dma',4,lambda x:not x&1,'MM2S RUNNING')
            if not self.read('dma',0)&1:raise RecoveryTimeout('MM2S RS cleared after submission')
            self.state='RELOCKING'
            self.wait('reset',8,lambda x:bool(x&2),'VIDEO OUT RELOCK')
            self.state='OBSERVING';self.elapsed(1650*750/self.pixel_hz)
            sr=self.read('dma',4);cr=self.read('dma',0);status=self.read('reset',8)
            if sr&1 or not cr&1 or not status&2 or status&1:raise RecoveryTimeout('Lost running/lock during observation frame')
            record['after']={hex(o):self.read('dma',o) for o in (0,4,0x28,0x50,0x54,0x58,0x5c,0x60,0x64,0x68)}
            self.context_check()
            self.state='STATIC_RECOVERED';d.buffer=frame.buffer;d.requested_slot=0
            record.update(status='LOCK_OBSERVED_OUTPUT_NOT_ACCEPTED',output_validation_required=True,completed=self.timestamp(),dma_status=sr,reset_status=status)
            return record
        except BaseException as first:
            failed_phase=self.state
            self.failed=True;d.faulted=True;self.state='FAULT'
            record.update(status='FAILED',first_error=repr(first),failed_monotonic=self.last_time,last_phase=failed_phase)
            if record not in self.records:self.records.append(record)
            if touched:
                errors=[]
                # Independent best effort requests: preserve the FIRST error even if cleanup fails.
                for ip,offset,value in [('dma',0,0x10000),('reset',4,1)]:
                    try:self.write(ip,offset,value)
                    except BaseException as cleanup:errors.append(repr(cleanup))
                if errors:record['cleanup_errors']=errors
            raise
        finally:d.lock.release()
