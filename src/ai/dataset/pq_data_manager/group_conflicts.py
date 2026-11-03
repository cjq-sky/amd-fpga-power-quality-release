"""Conservative metadata grouping checks; never rewrites groups or splits."""
from collections import defaultdict
import re

def conflicts(records):
    findings=[]
    def val(r,k):
        v=r.get(k)
        return v if isinstance(v,str) and v.strip() else None
    def grouped(key):
        g=defaultdict(list)
        for r in records:
            v=val(r,key)
            if v:
                if key.endswith('sha256'):
                    if not re.fullmatch('[a-fA-F0-9]{64}',v): continue
                    v=v.lower()
                g[v].append(r)
        return g
    def add(code,level,key,value,rs):
        findings.append(dict(code=code,severity=level,key=key,value=value,runs=sorted({r['run_path'] for r in rs})))
    for key in ['run_id','record_id']:
        for value,rs in grouped(key).items():
            if len(rs)>1:add('DUPLICATE_ID','conflict',key,value,rs)
    for key in ['waveform_id','parameter_set_id']:
        for value,rs in grouped(key).items():
            if len({val(r,'waveform_sha256') for r in rs if val(r,'waveform_sha256')})>1:
                add('ID_MULTIPLE_HASHES','review',key,value,rs)
            if len({val(r,'lineage_group_id') for r in rs if val(r,'lineage_group_id')})>1:
                add('ID_MULTIPLE_LINEAGES','conflict',key,value,rs)
    for key in ['waveform_sha256','source_sha256','numeric_sha256']:
        for value,rs in grouped(key).items():
            if len(rs)>1:
                add('REPEATED_SOURCE','info',key,value,rs)
                if len({val(r,'lineage_group_id') for r in rs if val(r,'lineage_group_id')})>1:
                    add('SAME_HASH_MULTIPLE_LINEAGES','conflict',key,value,rs)
    for value,rs in grouped('lineage_group_id').items():
        roles={val(r,'split_role') for r in rs}-{None}
        if len(roles)>1:add('LINEAGE_MULTIPLE_ROLES','review','lineage_group_id',value,rs)
        if roles & {'test_internal','test_external'} and roles & {'train','validation','calibration_dev'}:
            add('TEST_LINEAGE_LEAKAGE','conflict','lineage_group_id',value,rs)
    # Actual capture hashes are recomputed by the single-Run checker.
    files=defaultdict(list)
    for r in records:
        for f in r.get('inventory',[]):
            category=f['path'].replace('\\','/').split('/')[0]
            if f['size_bytes']>0:files[(category,f['sha256'])].append(r)
    for (category,h),rs in files.items():
        if len({r['run_path'] for r in rs})>1:
            add('IDENTICAL_CAPTURE_FILE','review',category,h,rs)
    return findings
