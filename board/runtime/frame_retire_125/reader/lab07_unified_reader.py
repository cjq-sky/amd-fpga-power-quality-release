"""Shared session, bounded equal-fid association; no validity upgrade."""
from dataclasses import dataclass
import time
from lab07_feature_reader import SnapshotReader,ReaderConfig
from lab07_raw_reader import RawReader,FeatureCache,RawReadError,descriptor
from lab07_registers import offset
from lab07_errors import Lab07Error
from lab07_abi import negotiate
@dataclass(frozen=True)
class Association:
    status:str;reason:str;feature:object=None
def associate_feature_raw(feature,raw,epoch,now,max_age=5.0):
    if feature is None:return Association('RAW_VALID_FEATURE_UNMATCHED','no retained feature')
    if raw.epoch!=epoch or feature.session.get('epoch')!=raw.epoch:return Association('UNMATCHED','different epoch/session')
    if not feature.consistent or not feature.snapshot_valid:return Association('UNMATCHED','feature tuple unavailable')
    if feature.frame_id!=raw.descriptor.frame_id:return Association('UNMATCHED','unequal source frame_id')
    observed=feature.session.get('observed_at');promotion=raw.promotion_observed_at
    if observed is None or promotion is None or not 0<=now-observed<=max_age or not 0<=now-promotion<=max_age:return Association('UNMATCHED','old/unknown age; fid wrap safety')
    return Association('MATCHED','same bounded epoch/source frame_id; validity unchanged',feature)
class UnifiedReader:
    def __init__(self,feature_mmio,raw_mmio,session,config=None,clock=time.monotonic,cache_age=5.0):
        self.control,self.data,self.session,self.clock=feature_mmio,raw_mmio,session,clock
        self.cache=FeatureCache(cache_age);self.lease=session.raw_lease
        self.feature_reader=SnapshotReader(feature_mmio,config,clock,session.token)
        self.raw_reader=RawReader(feature_mmio,raw_mmio,self.lease,clock,cache=self.cache)
        self.last_epoch=session.token();self.session.register(self.invalidate)
        self.quarantine=2;self.last_raw_service=None;self.last_feature_id=None
    def invalidate(self):
        self.feature_reader.state.clear();self.cache.entries.clear()
        self.raw_reader.previous=self.raw_reader.promotion_at=self.raw_reader.previous_seen=None
        self.quarantine=2;self.last_raw_service=None;self.last_feature_id=None
    def _epoch(self):
        current=self.session.token()
        if current!=self.last_epoch:self.invalidate();self.last_epoch=current
        return current
    def preflight(self):self._epoch();return negotiate(self.control)
    def feature(self):
        epoch=self._epoch()
        try:result=self.feature_reader.read()
        except Lab07Error:raise
        except Exception as e:raise Lab07Error('MMIO_ERROR','feature read exception') from e
        result.session.update(epoch=epoch,observed_at=self.clock())
        if result.status=='RETRY_EXHAUSTED':result.session['error_code']='FEATURE_SNAPSHOT_RETRY_EXHAUSTED'
        elif any('epoch changed' in r for r in result.reasons):result.session['error_code']='EPOCH_CHANGED'
        elif result.status=='ABI_MISMATCH':result.session.setdefault('error_code','ABI_UNSUPPORTED')
        if result.consistent and result.snapshot_valid and not result.stale and self.session.token()==epoch:self.cache.add(epoch,result.frame_id,result,result.session['observed_at'])
        if result.consistent and result.snapshot_valid and not result.stale:
            if self.last_feature_id is not None and result.frame_id<self.last_feature_id:
                self.cache.entries.clear();self.quarantine=2
            self.last_feature_id=result.frame_id
        return result
    def raw(self,mode='explicit'):
        if mode=='auto':
            if not getattr(self.data,'verified_u32_mapping',False):return self.raw('explicit')
            epoch=self.session.token()
            try:return self.raw('mapped')
            except RawReadError as e:
                if getattr(self.raw_reader,'phase',None)!='COPY' or self.session.token()!=epoch:raise
                # One complete fresh explicit retry; never after an ACK or epoch uncertainty.
                return self.raw('explicit')
        self._epoch();info=self.preflight()
        if not info.raw_supported:raise RawReadError('RAW_CAPABILITY_UNAVAILABLE '+info.mode)
        now=self.clock()
        if self.last_raw_service is None or not 0<=now-self.last_raw_service<=self.raw_reader.window:self.quarantine=2
        epoch=self.session.token()
        try:frame=self.raw_reader.read(mode)
        except Exception as e:
            if getattr(self.raw_reader,'phase',None)=='ACK':
                recovery={'policy':'QUERY_CURRENT_DESCRIPTOR_NEVER_REPLAY_ACK'}
                if self.session.token()!=epoch:recovery['state']='EPOCH_CHANGED'
                else:
                    try:
                        with self.lease.acquire() as current:
                            if self.control.read(offset('RAW_DESCRIPTOR_VALID'))==0:recovery['state']='NO_OWNER'
                            else:recovery.update(state='OWNED',descriptor=descriptor(self.control,self.lease,current))
                    except Exception as query_error:recovery.update(state='QUERY_UNAVAILABLE',reason=str(query_error))
                raise RawReadError('ACK result uncertain; descriptor queried, no command replay',recovery) from e
            raise
        frame.promotion_observed_at=self.raw_reader.promotion_at
        entry=self.cache.entries.get((frame.epoch,frame.descriptor.frame_id))
        match=associate_feature_raw(entry[1] if entry else None,frame,self.session.token(),self.clock(),self.cache.max_age)
        # Promotion age alone cannot certify capture age of an old pending bank.
        # At most two retained banks predate a restart/gap/wrap; both must drain.
        if self.quarantine:
            if match.status=='MATCHED':match=Association('UNMATCHED','two-bank backlog capture age unverified')
            self.quarantine-=1
        self.last_raw_service=self.clock()
        frame.association=match.status;frame.feature=match.feature;frame.association_reason=match.reason
        return frame
