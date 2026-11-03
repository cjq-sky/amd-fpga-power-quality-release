"""Read-only structural checks; never grants measurement or training approval."""
import argparse, hashlib, json, re
from pathlib import Path, PureWindowsPath

def check(run):
    run=Path(run).resolve(); issues=[]; inventory=[]
    def issue(code,field,message): issues.append(dict(code=code,field=field,message=message))
    def load(name):
        try:
            p=(run/name).resolve()
            if not p.is_relative_to(run): raise ValueError('Path escapes Run.')
            x=json.loads(p.read_text(encoding='utf-8-sig'))
            if not isinstance(x,dict): raise ValueError('Expected object.')
            return x
        except (OSError,ValueError) as e:
            issue('INVALID_JSON',name,str(e)); return {}
    m=load('metadata.json'); s=load('source_record.json'); review=load('review.json')
    for f in ['record_id','run_id','session_id','waveform_id','parameter_set_id','lineage_group_id','source_type','source_manifest_sha256','waveform_sha256']:
        if not m.get(f): issue('MISSING',f,'Required registration field absent.')
    if m.get('schema_version')!='capture-registration-0.1': issue('SCHEMA','schema_version','Unsupported schema.')
    if m.get('run_id')!=run.name: issue('IDENTITY','run_id','Directory and run_id differ.')
    for f in ['waveform_id','parameter_set_id','lineage_group_id','source_type']:
        if m.get(f)!=s.get(f): issue('SOURCE_MISMATCH',f,'Registration differs from source snapshot.')
    expected=s.get('waveform_sha256',s.get('source_sha256'))
    if m.get('waveform_sha256')!=expected: issue('SOURCE_MISMATCH','waveform_sha256','Source digest differs.')
    if m.get('split_role')!='calibration_dev': issue('SCOPE','split_role','Only calibration_dev supported.')
    for f in ['source_manifest_sha256','waveform_sha256','firmware_bit_sha256','firmware_hwh_sha256']:
        if not isinstance(m.get(f),str) or not re.fullmatch('[0-9a-fA-F]{64}',m[f]): issue('DIGEST',f,'Expected 64 hexadecimal characters.')
    for f in ['awg_actual_settings','independent_output_verification','adc_actual_configuration','frame_association_evidence']:
        if not isinstance(m.get(f),dict) or not m[f]: issue('MISSING_DETAILS',f,'Expected nonempty object; contents require manual review.')
    for f in ['abi_version','adapter_version']:
        if not isinstance(m.get(f),str) or not m[f].strip(): issue('MISSING',f,'Version required.')
    if m.get('device_id') in [None,'','unknown']: issue('MISSING','device_id','Record laboratory identity.')
    if m.get('capture_status')!='CAPTURED': issue('NOT_CAPTURED','capture_status','Expected CAPTURED after actual acquisition.')
    if m.get('association') not in ['runtime_matched','offline_verified_same_frame']:
        issue('ASSOCIATION','association','No declared supported same-frame association; not a hardware verification.')
    seen=set()
    for field,folder in [('raw_files','raw'),('feature_files','feature'),('reference_files','reference')]:
        entries=m.get(field)
        if not isinstance(entries,list) or not entries:
            issue('MISSING_FILES',field,'Expected nonempty list of {path, sha256}.'); continue
        for e in entries:
            if not isinstance(e,dict) or not isinstance(e.get('path'),str):
                issue('FILE_SCHEMA',field,'Expected path and sha256 object.'); continue
            name=e['path']; path=Path(name); win=PureWindowsPath(name)
            if path.is_absolute() or win.drive or win.root or '..' in win.parts or '..' in path.parts or ':' in name:
                issue('UNSAFE_PATH',field,name); continue
            target=(run/path).resolve()
            if not target.is_relative_to(run/folder): issue('UNSAFE_PATH',field,name); continue
            key=str(target).casefold()
            if key in seen: issue('DUPLICATE_FILE',field,name)
            seen.add(key)
            try:
                h=hashlib.sha256(); size=0
                with target.open('rb') as src:
                    for chunk in iter(lambda:src.read(1024*1024),b''): h.update(chunk);size+=len(chunk)
                actual=h.hexdigest();inventory.append(dict(path=name,size_bytes=size,sha256=actual))
                if not size: issue('EMPTY_FILE',field,name)
                if not isinstance(e.get('sha256'),str) or e['sha256'].lower()!=actual: issue('HASH_MISMATCH',field,name)
            except OSError as ex: issue('FILE_READ',field,str(ex))
    return dict(module='capture-integrity-0.1',run=str(run),structural_status='INCOMPLETE' if issues else 'STRUCTURALLY_COMPLETE',issues=issues,inventory=inventory,review_status=review.get('status'),measurement_validity='NOT_ASSESSED',formal_training_eligible=False,source_manifest_reverified=False,note='Only source snapshot consistency checked. No parsing of Raw/Feature, frame proof, voltage calibration or label approval.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--report',type=Path)
    a=p.parse_args(); report=check(a.run); text=json.dumps(report,ensure_ascii=False,indent=2)
    if a.report:
        # Reports must not alter the evidence directory and must not overwrite.
        if a.report.resolve().is_relative_to(a.run.resolve()): p.error('Save report outside the Run.')
        try:
            with a.report.open('x',encoding='utf-8') as f:f.write(text)
        except OSError as e:p.error(str(e))
    print(text)
    raise SystemExit(1 if report['issues'] else 0)
