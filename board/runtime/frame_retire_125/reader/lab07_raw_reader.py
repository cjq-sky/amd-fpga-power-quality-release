"""Offline-first raw lifecycle. No PYNQ import, no hardware epoch assumption."""
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
import time
import numpy as np
from datetime import datetime,timezone
from lab07_raw_registers import *

from lab07_errors import RawReadError

class ReaderLease:
    """All participants (read, ACK and controlled reload) must share this owner."""
    def __init__(self,epoch_getter):self._lock=Lock();self.epoch_getter=epoch_getter;self.active=False
    @contextmanager
    def acquire(self):
        if not self._lock.acquire(blocking=False):raise RawReadError('single-reader lease busy')
        self.active=True;epoch=self.epoch_getter()
        try:yield epoch
        finally:self.active=False;self._lock.release()
    def check(self,epoch):
        if not self.active or self.epoch_getter()!=epoch:raise RawReadError('lease/epoch invalidated')

@dataclass(frozen=True)
class Descriptor:
    bank:int;token:int;frame_id:int;status:int
    sample_count:int;channel_mask:int;frame_bytes:int;window_offset:int;window_size:int;format:int

@dataclass
class RawFrame:
    descriptor:Descriptor
    epoch:object
    CH1:np.ndarray
    CH2:np.ndarray
    words:np.ndarray
    evidence_scope:str
    association:str='UNMATCHED'
    feature:object=None
    host_time:str=''
    copy_duration:float=0.0
    ack_result:int=0
    drop_diagnostics:object=None
    promotion_observed_at:object=None

def get(mmio,name):
    value=mmio.read(offset(name))
    if type(value) is not int or not 0<=value<=0xffffffff:raise RawReadError('non-U32 '+name)
    return value

def check_abi(mmio):
    from lab07_abi import negotiate
    info=negotiate(mmio)
    if not info.raw_supported:raise RawReadError('RAW_CAPABILITY_UNAVAILABLE '+info.mode)
    return info

def descriptor(mmio,lease,epoch,retry=3,clock=time.monotonic,window=1.0):
    if type(retry) is not int or not 1<=retry<=100 or not 0<window<34.359738368:raise ValueError('bounded retry/window required')
    for _ in range(retry):
        lease.check(epoch);start=clock();before=get(mmio,'RAW_OWNER_TOKEN')
        values={n:get(mmio,n) for n in RAW_FIELDS}
        after=get(mmio,'RAW_OWNER_TOKEN');valid_after=get(mmio,'RAW_DESCRIPTOR_VALID')
        lease.check(epoch)
        if not 0<=clock()-start<window:continue
        if values['RAW_DESCRIPTOR_VALID']!=1 or valid_after!=1 or before!=after or before==0:continue
        if values['RAW_BANK_ID'] not in (0,1):raise RawReadError('invalid bank')
        if (values['RAW_SAMPLE_COUNT']!=SAMPLES or values['RAW_CHANNEL_MASK']!=3 or
            values['RAW_FRAME_STATUS']!=1 or values['RAW_FRAME_BYTES']!=FRAME_BYTES or
            values['RAW_WINDOW_OFFSET']!=0 or values['RAW_WINDOW_SIZE_BYTES']!=FRAME_BYTES or
            values['RAW_FORMAT']!=FORMAT):raise RawReadError('RAW_SAMPLE_COUNT_MISMATCH' if values['RAW_SAMPLE_COUNT']!=SAMPLES else 'raw metadata/geometry invalid')
        return Descriptor(values['RAW_BANK_ID'],before,values['RAW_FRAME_ID'],values['RAW_FRAME_STATUS'],
          values['RAW_SAMPLE_COUNT'],values['RAW_CHANNEL_MASK'],values['RAW_FRAME_BYTES'],
          values['RAW_WINDOW_OFFSET'],values['RAW_WINDOW_SIZE_BYTES'],values['RAW_FORMAT'])
    raise RawReadError('descriptor RETRY_EXHAUSTED / unavailable')

def acknowledge(mmio,desc,lease,epoch,clock=time.monotonic,window=1.0,retry=8):
    # Caller must finish device reads, descriptor recheck, and local copy BEFORE here.
    lease.check(epoch)
    mmio.write(offset('RAW_ACK_BANK'),desc.bank)
    mmio.write(offset('RAW_ACK_TOKEN'),desc.token)
    mmio.write(offset('RAW_ACK'),1)
    start=clock()
    for _ in range(retry):
        lease.check(epoch)
        result=get(mmio,'RAW_ACK_RESULT');done=get(mmio,'RAW_ACK_COMPLETED_TOKEN')
        if result & ~(ACK_BUSY|0xff):raise RawReadError('reserved ACK result bits')
        if not 0<=clock()-start<window:break
        if not result & ACK_BUSY:
            code=result&0xff
            if done!=desc.token or code!=1:raise RawReadError('ACK refused/uncertain '+ACK_RESULTS.get(code,'UNKNOWN'))
            return
    raise RawReadError('ACK timeout; query descriptor, never blindly replay')

class FeatureCache:
    """Bounded software observations; no nearest/latest matching, no fid permanent uniqueness."""
    def __init__(self,max_age=5.0,capacity=32):
        if not 0<max_age<=60 or not 1<=capacity<=1024:raise ValueError('bounded cache required')
        self.max_age=max_age;self.capacity=capacity;self.entries={}
    def add(self,epoch,frame_id,payload,observed_at):
        self.entries[(epoch,frame_id)]=(observed_at,payload)
        if len(self.entries)>self.capacity:
            del self.entries[min(self.entries,key=lambda k:self.entries[k][0])]
    def associate(self,epoch,frame_id,promotion_observed_at,now):
        # First attached old owner has UNKNOWN promotion age; refuse association.
        if promotion_observed_at is None or not 0<=now-promotion_observed_at<=self.max_age:return None
        entry=self.entries.get((epoch,frame_id))
        if not entry or not 0<=now-entry[0]<=self.max_age:return None
        return entry[1]

class RawReader:
    def __init__(self,control,data,lease,clock=time.monotonic,retry=3,window=1.0,cache=None):
        self.control,self.data,self.lease=control,data,lease
        self.clock,self.retry,self.window,self.cache=clock,retry,window,cache
        self.previous=None;self.promotion_at=None;self.previous_seen=None
    def read(self,mode='explicit'):
        self.phase='PREFLIGHT'
        with self.lease.acquire() as epoch:
            check_abi(self.control)
            desc=descriptor(self.control,self.lease,epoch,self.retry,self.clock,self.window)
            now=self.clock();identity=(epoch,desc.token,desc.bank,desc.frame_id)
            if self.previous is not None and self.previous[0]==epoch:
                old=self.previous
                if desc.token<old[1] or (desc.token==old[1] and identity!=old):
                    raise RawReadError('lease/epoch invalidated: token reverse/reuse reset suspected')
            if identity!=self.previous:
                # Only a bounded observed transition certifies recent promotion.
                self.promotion_at=now if self.previous is not None and self.previous[0]==epoch and 0<=now-self.previous_seen<=self.window else None
                self.previous=identity
            self.previous_seen=now
            started=now
            self.phase='COPY'
            try:
                if mode=='explicit':
                    words=np.empty(SAMPLES,dtype=np.uint32)
                    for i in range(SAMPLES):
                        self.lease.check(epoch)
                        if not 0<=self.clock()-started<self.window:raise RawReadError('partial copy timeout')
                        value=self.data.read(i*4)
                        if type(value) is not int or not 0<=value<=0xffffffff:raise RawReadError('invalid data response')
                        words[i]=value
                elif mode=='mapped':
                    # A future adapter must affirm its device width/ordering contract explicitly.
                    if not getattr(self.data,'verified_u32_mapping',False):raise RawReadError('mapped API not platform verified')
                    candidate=np.asarray(self.data.copy_u32(SAMPLES))
                    if candidate.dtype!=np.dtype(np.uint32) or candidate.shape!=(SAMPLES,):
                        raise RawReadError('mapped adapter did not return exact uint32[2048]')
                    words=candidate.copy()
                else:raise ValueError('unknown copy mode')
                self.data.read_completion_barrier()
                self.lease.check(epoch)
                if words.shape!=(SAMPLES,) or words.nbytes!=FRAME_BYTES or not 0<=self.clock()-started<self.window:raise RawReadError('partial/expired block')
                after=descriptor(self.control,self.lease,epoch,self.retry,self.clock,self.window)
                if after!=desc:raise RawReadError('descriptor changed during local copy')
            except Exception as e:
                # Never ACK/return any partial frame. Caller may re-acquire and retry entire frame.
                if isinstance(e,RawReadError):raise
                raise RawReadError('copy failed; owner not ACKed') from e
            # Decode only LOCAL bytes, and make independent signed arrays before release.
            payload=words.astype('<u4',copy=False).tobytes()
            pairs=np.frombuffer(payload,dtype='<i2').reshape(SAMPLES,2)
            ch1=pairs[:,0].astype(np.int16,copy=True);ch2=pairs[:,1].astype(np.int16,copy=True)
            feature=self.cache.associate(epoch,desc.frame_id,self.promotion_at,self.clock()) if self.cache else None
            elapsed=self.clock()-started
            diagnostics={n:get(self.control,n) for n in ('RAW_DROP_COUNT','RAW_DROP_STICKY','RAW_PROTOCOL_STICKY','RAW_ACK_ERROR_STICKY','RAW_TOKEN_EXHAUSTED_STICKY')}
            self.phase='ACK'
            acknowledge(self.control,desc,self.lease,epoch,self.clock,self.window)
            self.phase='COMPLETE'
            return RawFrame(desc,epoch,ch1,ch2,words.copy(),getattr(self.data,'provenance','UNVERIFIED'),
                            'MATCHED_EQUAL_FID' if feature is not None else 'UNMATCHED',feature,
                            datetime.now(timezone.utc).isoformat(),elapsed,1,diagnostics,self.promotion_at)
