"""Module 1: non-destructive capture registration. Standard library only."""
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',value):
        raise ValueError('IDs must contain 1..100 ASCII letters, digits, underscores or hyphens.')
    return value

def register(manifest_path, waveform_id, root, run_id, session_id, device_id='unknown', write_markdown=True):
    for value in [waveform_id,run_id,session_id,device_id]: identifier(value)
    blob=manifest_path.read_bytes()
    rows=json.loads(blob.decode('utf-8-sig'))
    if not isinstance(rows,list): raise ValueError('Manifest must be a list.')
    matches=[r for r in rows if r.get('waveform_id')==waveform_id]
    if len(matches)!=1: raise ValueError('Waveform ID must match exactly one record.')
    source=matches[0]
    role=source.get('split_role',source.get('split'))
    if role!='calibration_dev': raise ValueError('This module only registers calibration_dev records.')
    group=source.get('lineage_group_id')
    if not group: raise ValueError('Missing lineage_group_id; do not invent lineage.')
    identifier(group)
    root=root.resolve(); target=root/run_id
    if target.exists(): raise ValueError('Run already exists; nothing overwritten.')
    fields=['awg_actual_settings','independent_output_verification','adc_actual_configuration',
            'firmware_bit_sha256','firmware_hwh_sha256','abi_version','adapter_version',
            'raw_files','feature_files','reference_files','frame_association_evidence']
    record=dict(schema_version='capture-registration-0.1',record_id=run_id,run_id=run_id,
        session_id=session_id,device_id=device_id,channel='CH1',waveform_id=waveform_id,
        parameter_set_id=source.get('parameter_set_id'),lineage_group_id=group,
        source_record_id=source.get('source_record_id'),source_type=source.get('source_type'),
        source_manifest_path=str(manifest_path.resolve()),source_manifest_sha256=hashlib.sha256(blob).hexdigest(),
        waveform_sha256=source.get('waveform_sha256',source.get('source_sha256')),
        split_role='calibration_dev',source_label=None,label=None,label_status='LABEL_REVIEW',
        label_spec_version=None,capture_status='NOT_CAPTURED',association='unmatched',
        created_at_utc=datetime.now(timezone.utc).isoformat(),adc_range_volts=[-10,10],
        adc_range_note='Project-confirmed range; actual session configuration still requires recording.',
        pending_fields=fields,notes='Registration only; no hardware measurement or validation performed.')
    for field in fields: record[field]=None
    # exist_ok=False protects existing runs, including repeated invocations.
    target.mkdir(parents=True,exist_ok=False)
    for name in ['raw','feature','reference']: (target/name).mkdir()
    (target/'metadata.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    (target/'source_record.json').write_text(json.dumps(source,ensure_ascii=False,indent=2),encoding='utf-8')
    (target/'review.json').write_text(json.dumps(dict(status='PENDING',reviewer=None,reviewed_at=None,findings=[],formal_training_eligible=False),indent=2),encoding='utf-8')
    if write_markdown:
        (target/'待补信息.md').write_text('# 本 Run 待补信息\n\n仅已登记，未采集、未验收。保留原始文件，不修改源标签或关联状态来绕过审核。\n\n'+''.join('- '+f+'\n' for f in fields)+'\n设备身份、标签版本及原始帧关联信息也需现场核对。pending_fields 为初始清单，不会自动更新。\n',encoding='utf-8')
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True,type=Path);p.add_argument('--waveform',required=True)
    p.add_argument('--root',required=True,type=Path);p.add_argument('--run',required=True)
    p.add_argument('--session',required=True);p.add_argument('--device',default='unknown')
    a=p.parse_args()
    try: print(register(a.manifest,a.waveform,a.root,a.run,a.session,a.device))
    except (ValueError,OSError,KeyError,TypeError) as e: p.exit(2,f'Registration failed: {e}\n')
