"""Offline preflight and lazy PYNQ3.1.1 two-region adapters."""
import hashlib
from pathlib import Path
from typing import Protocol
import xml.etree.ElementTree as ET
from lab07_registers import *
from lab07_abi import negotiate,AbiMismatch
from lab07_errors import Lab07Error
class MMIO(Protocol):
    def read(self,offset:int)->int:...
    def write(self,offset:int,value:int)->None:...
def read_name(mmio,name):
    value=mmio.read(offset(name))
    if type(value) is not int or not 0<=value<=0xffffffff:raise Lab07Error('MMIO_ERROR',name+' non-U32')
    return value
def verify_abi(mmio):return negotiate(mmio).identification
def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()
def audit_hwh(path):
    root=ET.parse(path).getroot();ps=[m for m in root.iter('MODULE') if m.get('MODTYPE')=='processing_system7']
    if len(ps)!=1:raise Lab07Error('HWH_ADDRESS_MISMATCH','PS7 missing/ambiguous')
    regions={}
    for plane,base,span in [('feature',FEATURE_BASE,FEATURE_RANGE),('raw',RAW_BASE,RAW_RANGE)]:
        matches=[r for r in root.iter('MEMRANGE') if int(r.get('BASEVALUE','0'),0)==base and r.get('SLAVEBUSINTERFACE')=='S_AXI']
        if len(matches)!=1:raise Lab07Error('HWH_ADDRESS_MISMATCH',plane+' base missing/ambiguous')
        r=matches[0];instance=r.get('INSTANCE')
        if int(r.get('HIGHVALUE'),0)-base+1!=span or r.get('MASTERBUSINTERFACE')!='M_AXI_GP0':raise Lab07Error('HWH_ADDRESS_MISMATCH',plane+' range/master mismatch')
        if len([m for m in root.iter('MODULE') if m.get('INSTANCE')==instance])!=1:raise Lab07Error('HWH_ADDRESS_MISMATCH',plane+' instance missing/ambiguous')
        regions[plane]={'instance':instance,'base':base,'range':span,'high':base+span-1}
    return {'scope':'OFFLINE_XML_CONSISTENCY_ONLY','instance':regions['feature']['instance'],'regions':regions,'ps':ps[0].get('INSTANCE')}
def audit_release(bitfile,hwhfile):
    b,h=Path(bitfile),Path(hwhfile)
    if b.stem!=h.stem or b.parent.resolve()!=h.parent.resolve():raise Lab07Error('RELEASE_PAIR_MISMATCH','pair naming/directory')
    hashes={'bit_sha256':sha256(b),'hwh_sha256':sha256(h)}
    if hashes['bit_sha256']!=BIT_SHA256 or hashes['hwh_sha256']!=HWH_SHA256:raise Lab07Error('RELEASE_PAIR_MISMATCH','authoritative SHA256 mismatch')
    return dict(audit_hwh(h),**hashes)
class PynqMMIOAdapter:
    provenance='HARDWARE_RUNTIME_OBSERVATION'
    def __init__(self,base=FEATURE_BASE,span=FEATURE_RANGE,control=None,ordering_confirmed=False,mapped_confirmed=False):
        from pynq import MMIO as PynqMMIO
        self.base,self.span,self.control=base,span,control;self._mmio=PynqMMIO(base,span)
        self.ordering_confirmed=ordering_confirmed;self.verified_u32_mapping=mapped_confirmed and ordering_confirmed
    def read(self,off):
        if type(off) is not int or off%4 or not 0<=off<self.span:raise Lab07Error('MMIO_ERROR','unaligned/outside aperture')
        try:return int(self._mmio.read(off))
        except Exception as e:raise Lab07Error('MMIO_ERROR','platform read exception; no zero substitution') from e
    def write(self,off,value):
        if self.base!=FEATURE_BASE or off not in [offset(n) for n in ('RAW_ACK_BANK','RAW_ACK_TOKEN','RAW_ACK')]:raise PermissionError('RO or unsupported command write')
        if type(value) is not int or not 0<=value<=0xffffffff:raise ValueError('U32 write required')
        if not negotiate(self).raw_supported:raise Lab07Error('RAW_CAPABILITY_UNAVAILABLE')
        self._mmio.write(off,value)
    def copy_u32(self,count):
        if not self.verified_u32_mapping or count!=SAMPLES:raise Lab07Error('RAW_PARTIAL_COPY','mapped platform contract unconfirmed')
        return self._mmio.array[:count].copy()
    def read_completion_barrier(self):
        # Device mapping/CPU ordering must be validated on the target image; no DSB claim.
        if not self.ordering_confirmed or self.control is None:raise Lab07Error('PYNQ_ORDERING_BARRIER_HW_VALIDATION_PENDING')
        self.control.read(offset('RAW_OWNER_TOKEN'))
def read_live_diagnostics(mmio):return {n:read_name(mmio,n) for n,s in REGISTERS.items() if s.region=='live'}
