"""Explicit major/minor compatibility, capability names and missing-field policy."""
from dataclasses import dataclass
from lab07_registers import *
from lab07_errors import Lab07Error

class AbiMismatch(Lab07Error,ValueError):pass

def capability(word,bits):
    defined=sum(1<<b for b in bits.values())
    return {'raw':word,'supported':[n for n,b in bits.items() if word&(1<<b)],
            'unsupported':[n for n,b in bits.items() if not word&(1<<b)],'unknown_bits':word&~defined}

@dataclass(frozen=True)
class AbiInfo:
    major:int;minor:int;mode:str;raw_supported:bool
    feature:dict;raw:dict;identification:dict

def negotiate(mmio):
    actual={}
    for n in IDENTIFICATION:
        v=mmio.read(offset(n))
        if type(v) is not int or not 0<=v<=0xffffffff:raise AbiMismatch('MMIO_ERROR',n+' non-U32')
        actual[n]=v
    major,minor=actual['REGMAP_VERSION']>>16,actual['REGMAP_VERSION']&0xffff
    if (major,minor) not in (ABI_SUPPORTED,ABI_LEGACY):raise AbiMismatch('ABI_UNSUPPORTED',f'{major}.{minor}')
    for n in ('MAGIC','CORE_ID','BASELINE_ID','FRAME_SAMPLES','SAMPLE_RATE_NOMINAL_HZ'):
        if actual[n]!=IDENTIFICATION[n]:raise AbiMismatch('ABI_UNSUPPORTED',n+' mismatch')
    f=capability(actual['FEATURE_CAPABILITY'],FEATURE_CAPABILITY_BITS)
    raw=capability(actual['RAW_CAPABILITY'],RAW_CAPABILITY_BITS)
    if not actual['FEATURE_CAPABILITY']&(1<<FEATURE_CAPABILITY_BITS['ATOMIC_SNAPSHOT_SEQ']):
        raise AbiMismatch('FEATURE_CAPABILITY_MISMATCH','atomic seq read unavailable')
    legacy=(major,minor)==ABI_LEGACY
    available=not legacy and actual['RAW_CAPABILITY']&RAW_CAP==RAW_CAP
    return AbiInfo(major,minor,'LEGACY_FEATURE_ONLY' if legacy else 'SUPPORTED',available,f,raw,actual)

def apply_capabilities(result,config,info):
    cap=info['FEATURE_CAPABILITY'] if isinstance(info,dict) else info.identification['FEATURE_CAPABILITY']
    for n,v in result.basic.items():
        bit=0 if n.endswith(('RMS','PEAK')) else 1 if n.endswith('CREST') else 2
        if not cap&(1<<bit):
            v['valid']=False;v['value']=None;v['capability_available']=False
            if n in config.required_basic:result.reasons.append(n+': capability unavailable');result.status='INVALID'
    for ch,v in result.channels.items():
        if cap&((1<<3)|(1<<4))!=((1<<3)|(1<<4)):
            v['consumable']=False;v['capability_available']=False
            for field in v['features'].values():
                field['value']=None
                if 'percent' in field:field['percent']=None
            if ch in config.required_channels:result.reasons.append(ch+': capability unavailable');result.status='INVALID'
        if not cap&(1<<8):v['formal_identity']=None;v['formal_acceptance']=None;v['formal_diagnostics_available']=False

