"""Import indexed C H12 original logs, preserving Feature-only provenance."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def parse_log(blob,expected_frames):
    objects=[];errors=[]
    for line_no,line in enumerate(blob.decode('utf-8-sig').splitlines(),1):
        if not line.strip():continue
        try:
            obj=json.loads(line)
            if not isinstance(obj,dict):raise ValueError('Expected object')
            objects.append((line_no,obj))
        except ValueError as e:errors.append(dict(line=line_no,error=str(e)))
    selected=[]
    for e in expected_frames:
        matches=[(ln,o['feature']) for ln,o in objects if isinstance(o.get('feature'),dict) and o['feature'].get('frame_id')==e['frame_id'] and o['feature'].get('status')=='CONSISTENT' and o['feature'].get('stale') is False]
        if len(matches)!=1:raise ValueError(f"Expected exactly one current frame {e['frame_id']}; found {len(matches)}")
        ln,f=matches[0];raw=f.get('raw',{});ch=f.get('channels',{}).get('CH1',{})
        checks=[f.get('snapshot_valid') is True,f.get('consistent') is True,f.get('seq_before')==f.get('seq_after')==e['seq'],f.get('session',{}).get('epoch')==e['epoch'],all(k in raw for k in e['raw_fields']),raw.get('FRAME_ID')==e['frame_id'],raw.get('SNAPSHOT_VALID')==1,raw.get('FEATURE_ACQUISITION_VALID')==1,ch.get('numeric_valid') is True,ch.get('consumable') is True,ch.get('numeric_reasons')==[],ch.get('protocol_errors')==[],ch.get('boundary_warning') is False,type(raw.get('CH1_H1')) is int and raw['CH1_H1']>0]
        if not all(checks):raise ValueError(f"Indexed frame {e['frame_id']} failed source checks")
        selected.append(dict(source_line=ln,frame_id=e['frame_id'],epoch=e['epoch'],seq=e['seq'],association='FEATURE_ONLY',source_label=None,label=None,training_eligible=False,feature=f,note='feature.raw contains integer registers, NOT ADC waveform samples. Indexed checks do not replace full v05 Adapter qualification.'))
    return objects,errors,selected

def import_zip(source,out):
    source=Path(source);out=Path(out)
    if out.exists():raise ValueError('Output exists; no overwrite.')
    archive=source.read_bytes();plans=[]
    with zipfile.ZipFile(source) as z:
        indices=[]
        for n in z.namelist():
            if n.endswith('.json'):
                obj=json.loads(z.read(n).decode('utf-8-sig'))
                if isinstance(obj,dict) and isinstance(obj.get('items'),list):indices.append((n,obj))
        if len(indices)!=1:raise ValueError('Expected one H12 source index.')
        index_name,index=indices[0];cases=set()
        for item in index['items']:
            case=item['case']
            if case not in ['CASE1','CASE2'] or case in cases:raise ValueError('Unexpected/duplicate case.')
            cases.add(case)
            members=[n for n in z.namelist() if n.endswith('/'+item['archive_member']) or n==item['archive_member']]
            if len(members)!=1:raise ValueError('Missing or ambiguous log member.')
            blob=z.read(members[0])
            if sha(blob)!=item['sha256']:raise ValueError('Log SHA256 mismatch.')
            objects,errors,selected=parse_log(blob,item['matched_frames'])
            plans.append((case,members[0],blob,objects,errors,selected,item))
    if cases!={'CASE1','CASE2'}:raise ValueError('Both cases required.')
    out.mkdir(parents=True)
    (out/'source_delivery.zip').write_bytes(archive)
    (out/'source_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
    summary=[]
    for case,member,blob,objects,errors,selected,item in plans:
        d=out/case;d.mkdir();(d/'terminal.log').write_bytes(blob)
        (d/'selected_features.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in selected),encoding='utf-8')
        (d/'all_records.jsonl').write_text(''.join(json.dumps(dict(source_line=ln,original=o),ensure_ascii=False)+'\n' for ln,o in objects),encoding='utf-8')
        row=dict(case=case,source_member=member,log_sha256=sha(blob),source_archive_claim=item.get('source_archive_sha256'),historical_archive_reverified=False,selected_frames=[r['frame_id'] for r in selected],total_records=len(objects),stale_records=sum(o.get('feature',{}).get('stale') is True for _,o in objects if isinstance(o.get('feature',{}),dict)),parse_errors=errors,association='FEATURE_ONLY',source_label=None,training_eligible=False,split_role='calibration_dev',lineage_group_id='H12_'+sha(blob))
        (d/'import_record.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8');summary.append(row)
    report=dict(module='h12-import-0.1',delivery_sha256=sha(archive),source_index_member=index_name,cases=summary,selected_count=sum(len(r['selected_frames']) for r in summary),status='IMPORTED_WITH_PARSE_ERRORS' if any(r['parse_errors'] for r in summary) else 'INDEXED_FEATURE_CHECKS_PASS',formal_training_ready=False)
    (out/'import_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--zip',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:
        r=import_zip(a.zip,a.output);print(json.dumps(r,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError,zipfile.BadZipFile) as e:p.exit(2,str(e)+'\n')
