"""C H13 evidence importer; requires numpy; never assigns training labels."""
import argparse,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath
import numpy as np

def require(ok,message):
    if not ok:raise ValueError(message)
def sha(b):return hashlib.sha256(b).hexdigest()
def import_h13(source,out):
    out=Path(out);require(not out.exists(),'Output exists')
    with zipfile.ZipFile(source) as z:
        require(len(z.namelist())==len(set(z.namelist())),'Duplicate archive members')
        payload={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
    for n in payload:
        q=PurePosixPath(n);require(not q.is_absolute() and '..' not in q.parts and ':' not in n and '\\' not in n,'Unsafe path')
    docs=[json.loads(b.decode('utf-8-sig')) for n,b in payload.items() if n.endswith('.json')]
    idx=next(x for x in docs if isinstance(x,list) and x and 'sha256' in x[0])
    ref=next(x for x in docs if isinstance(x,dict) and x.get('status')=='H13_SOURCE_AND_TWO_ORIGINAL_PAIRS_REVERIFIED')
    for e in idx:
        names=[n for n in payload if n.endswith('/'+e['file'])];require(len(names)==1,'Missing/ambiguous indexed member');require(sha(payload[names[0]])==e['sha256'],'SHA mismatch')
    name=next(n for n in payload if '/01_' in n and n.endswith('/terminal.log'))
    lines=payload[name].decode('utf-8-sig').splitlines();pairs=[]
    for e in ref['checks']:
        feature=json.loads(lines[e['feature_log_line']-1])['feature'];rawlog=json.loads(lines[e['raw_log_line']-1])['raw']
        n=next(n for n in payload if '/01_' in n and n.endswith('/'+e['raw_npz']))
        with np.load(io.BytesIO(payload[n]),allow_pickle=False) as a:
            meta=json.loads(str(a['metadata'].item()));words=a['words'];ch1=a['CH1'];ch2=a['CH2']
            require(words.dtype==np.dtype('uint32') and words.shape==(2048,),'words format')
            require(ch1.dtype==np.dtype('int16') and ch2.dtype==np.dtype('int16') and ch1.shape==ch2.shape==(2048,),'channel format')
            require(np.array_equal((words&65535).astype(np.uint16).view(np.int16),ch1),'CH1 unpack')
            require(np.array_equal((words>>16).astype(np.uint16).view(np.int16),ch2),'CH2 unpack')
        require(meta==rawlog,'NPZ/log metadata differs')
        for k in ['epoch','frame_id','token','bank']:require(meta[k]==e[k],'Identity mismatch '+k)
        require(meta['ack_result']==1 and meta['association']=='MATCHED' and meta['owner_valid'] and meta['frame_valid'],'Raw validity')
        require(feature['session']['epoch']==e['epoch'] and feature['frame_id']==e['frame_id'] and feature['raw']['FRAME_ID']==e['frame_id'],'Feature identity')
        require(feature['seq_before']==feature['seq_after']==e['frame_id']+1 and feature['status']=='CONSISTENT' and feature['stale'] is False and feature['snapshot_valid'],'Feature snapshot')
        require(feature['channels']['CH1']['numeric_valid'] is True,'CH1 numeric')
        r=feature['raw'];require(r['CH1_H1']>0,'H1 zero')
        six=[100*r['CH1_H'+str(k)]/r['CH1_H1'] for k in [3,5,7,9]]+[100*r['CH1_THD_ODD_3_5_7_9']/65536,r['CH1_CREST']/1024]
        require(np.allclose(six,e['derived_ch1_six_values'],rtol=0,atol=1e-10),'Arithmetic mismatch')
        pairs.append(dict(frame_id=e['frame_id'],epoch=e['epoch'],lineage_group_id='H13_Combined_Formal_20261024_yD7F3l',feature=feature,raw_metadata=meta,raw_member=n,association='MATCHED',six_arithmetic_only=six,source_label=None,training_eligible=False))
    require({p['frame_id'] for p in pairs}=={7235,7236} and len(pairs)==2,'Expected two H13 frames')
    out.mkdir(parents=True)
    for n,b in payload.items():
        p=out/'originals'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    report=dict(status='SOURCE_HASH_AND_PAIR_CHECKS_PASS',delivery_sha256=sha(Path(source).read_bytes()),indexed_hashes_checked=len(idx),pairs=2,historical_archive_reverified=False,independent_reference_obtained=False,numeric_duty_obtained=False,training_eligible=False)
    (out/'pairs.json').write_text(json.dumps(pairs,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'import_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--zip',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    print(json.dumps(import_h13(a.zip,a.output),indent=2))
