"""Default OFFLINE. Explicit future hardware stages; no inferred CASE/performance acceptance."""
import argparse,json,time,os
from pathlib import Path
from dataclasses import asdict
from contextlib import contextmanager
from lab07_registers import *
from lab07_mmio import audit_release,audit_hwh,PynqMMIOAdapter
from lab07_unified_reader import UnifiedReader
from lab07_session import Session,ManagedEpoch
from lab07_errors import Lab07Error
from lab07_feature_reader import ReaderConfig
from mock_unified_mmio import MockUnifiedMMIO
S=Path(__file__).resolve().parents[1]

def raw_record(frame):
    return dict(host_time=frame.host_time,epoch=frame.epoch,**asdict(frame.descriptor),
                owner_valid=True,frame_valid=True,copy_duration=frame.copy_duration,
                ack_result=frame.ack_result,drop_diagnostics=frame.drop_diagnostics,
                association=frame.association,association_reason=frame.association_reason,
                evidence_scope=frame.evidence_scope)
def save_raw(frame,path):
    import numpy as np
    path=Path(path)
    session=str(frame.epoch[0]).replace('-','')[:8]
    dest=path.with_name(f'{path.stem}_session{session}_fid{frame.descriptor.frame_id:08x}_token{frame.descriptor.token:08x}.npz')
    with dest.open('xb') as f:
        np.savez(f,CH1=frame.CH1,CH2=frame.CH2,words=frame.words,metadata=json.dumps(raw_record(frame)))
    return dest

@contextmanager
def managed_session():
    import fcntl
    # Same lease path as historical C loader; all cooperating users/reloads must use it.
    with os.fdopen(os.open('/tmp/pq_lab07_feature_overlay.lock',os.O_RDWR|os.O_CREAT,0o600),'r+') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield ManagedEpoch(f,Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        finally:fcntl.flock(f,fcntl.LOCK_UN)

def offline(args):
    print('MOCK / OFFLINE EXAMPLE; NOT HARDWARE VALIDATED')
    if args.bit:print(json.dumps(audit_release(args.bit,args.hwh)))
    model=MockUnifiedMMIO();session=Session();reader=UnifiedReader(model.control,model.data,session)
    print(json.dumps(asdict(reader.preflight())))
    if args.mode!='raw-only':print(json.dumps(reader.feature().to_dict()))
    if args.mode!='feature-only':
        frame=reader.raw();print(json.dumps(raw_record(frame)))
        if args.output:
            p=Path(args.output)
            if not p.name.startswith(('mock_','offline_')):raise ValueError('offline output requires mock_/offline_ prefix')
            save_raw(frame,p)
    print('PYNQ_ORDERING_BARRIER_HW_VALIDATION_PENDING; hardware/performance NOT RUN')
    return 0

def validate_hardware_args(args):
    if not args.bit or not args.hwh:raise ValueError('--hardware requires --bit/--hwh')
    if args.mode!='feature-only' and not args.feature_path_confirmed:
        raise ValueError('raw/combined requires prior feature hardware review: --feature-path-confirmed')
    if args.mode!='feature-only' and not args.ordering_contract_confirmed:
        raise Lab07Error('PYNQ_ORDERING_BARRIER_HW_VALIDATION_PENDING','validate target device mapping/load completion first; flag is an operator declaration, not evidence')
    if args.copy=='mapped' and not args.mapped_u32_confirmed:raise ValueError('mapped U32 contract must be platform-confirmed; explicit fallback is default')

def hardware(args):
    validate_hardware_args(args)
    # A: immutable hashes + offline address audit before any PYNQ import/MMIO.
    audit=audit_release(args.bit,args.hwh);print(json.dumps({'phase':'A_RELEASE_PREFLIGHT','audit':audit}))
    from pynq import Overlay
    with managed_session() as managed:
        session=Session(managed);overlay=Overlay(str(Path(args.bit).resolve()),download=False)
        if args.attach:managed.require_attach()
        else:session.begin_new_epoch();overlay.download()
        regions=audit_hwh(args.hwh)['regions']
        for plane,region in regions.items():
            matches=[v for v in overlay.ip_dict.values() if int(v.get('phys_addr',-1))==region['base'] and int(v.get('addr_range',-1))==region['range']]
            if len(matches)!=1:raise Lab07Error('HWH_ADDRESS_MISMATCH','PYNQ parser '+plane)
        control=PynqMMIOAdapter();info=__import__('lab07_abi').negotiate(control)
        print(json.dumps({'phase':'D_ABI_CAPABILITY','info':asdict(info)}))
        # Raw mapping constructed only after ABI/capability approves it.
        data=None
        if args.mode!='feature-only':
            if not info.raw_supported:raise Lab07Error('RAW_CAPABILITY_UNAVAILABLE')
            data=PynqMMIOAdapter(RAW_BASE,RAW_RANGE,control,args.ordering_contract_confirmed,args.mapped_u32_confirmed)
        if not args.attach:managed.complete_reload()
        reader=UnifiedReader(control,data,session,ReaderConfig(required_channels=()))
        seqs=set();fids=set();raws=0;started=time.monotonic();done=False
        while time.monotonic()-started<args.timeout:
            if args.mode!='raw-only':
                result=reader.feature();print(json.dumps({'feature':result.to_dict(),'case':args.case,'case_acceptance':'REQUIRES_REVIEW'}))
                if result.consistent and result.snapshot_valid and not result.stale:seqs.add(result.seq_after);fids.add(result.frame_id)
            if data is not None:
                try:
                    frame=reader.raw(args.copy)
                    print(json.dumps({'raw':raw_record(frame)}));raws+=1
                    if args.output:save_raw(frame,args.output)
                except Lab07Error as e:
                    print(json.dumps({'code':e.code,'detail':e.detail,'recovery':str(e.recovery)}))
                    # Retry fresh descriptor only for no/torn owner; uncertain ACK ends this run.
                    if e.code!='RAW_DESCRIPTOR_INCOHERENT':raise
            done=(args.mode=='feature-only' and len(seqs)>=2 and len(fids)>=2) or (args.mode=='raw-only' and raws>=args.raw_frames) or (args.mode=='combined' and raws>=args.raw_frames and len(seqs)>=2)
            if done:break
            time.sleep(0.05)
        print(json.dumps({'runtime_observations_only':True,'distinct_seq':len(seqs),'distinct_fid':len(fids),'raw_frames':raws,'review_required':True,'ordering_and_performance_acceptance':'NOT_AUTOMATIC'}))
        return 0 if done else 3

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group();g.add_argument('--hardware',action='store_true');g.add_argument('--offline',action='store_true')
    p.add_argument('--mode',choices=('feature-only','raw-only','combined'),default='feature-only')
    for mode in ('feature-only','raw-only','combined'):p.add_argument('--'+mode,dest='mode',action='store_const',const=mode)
    p.add_argument('--bit');p.add_argument('--hwh');p.add_argument('--attach',action='store_true')
    p.add_argument('--feature-path-confirmed',action='store_true');p.add_argument('--ordering-contract-confirmed',action='store_true')
    p.add_argument('--mapped-u32-confirmed',action='store_true');p.add_argument('--copy',choices=('explicit','mapped','auto'),default='explicit')
    p.add_argument('--case',choices=('CASE0','CASE1','CASE2','CASE3'),default='CASE0');p.add_argument('--timeout',type=float,default=10.0);p.add_argument('--output')
    p.add_argument('--raw-frames',type=int,default=4,help='includes at most two quarantined backlog frames; default leaves later frames for association')
    args=p.parse_args(argv)
    if bool(args.bit)!=bool(args.hwh):raise ValueError('provide matching BIT/HWH pair')
    if args.attach and not args.hardware:raise ValueError('--attach requires --hardware')
    if not 0<args.timeout<=3600:raise ValueError('finite timeout required')
    if not 1<=args.raw_frames<=1000:raise ValueError('raw frame budget must be1..1000')
    return hardware(args) if args.hardware else offline(args)
if __name__=='__main__':
    try:raise SystemExit(main())
    except Lab07Error as e:print(json.dumps({'code':e.code,'detail':e.detail,'recovery':str(e.recovery)}));raise SystemExit(2)
