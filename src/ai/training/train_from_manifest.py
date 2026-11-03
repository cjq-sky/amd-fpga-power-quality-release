"""Train original limited-scope LR/RF settings from an already released Manifest.

Packaging adapter for train_physical_limited_v1.py; does not repeat raw auditing.
Requires trusted, released data. Hash verification is not approval verification.
"""
import argparse,hashlib,json,math
from pathlib import Path
from collections import Counter

LABELS=['CLEAN','H3_DOMINANT','H5_DOMINANT','MIXED']
ORDER=['H3_pct','H5_pct','H7_pct','H9_pct','THD_ODD_pct','Crest']
ORIGINAL_MANIFEST_SHA256='8b0c5ccc7a84f10906f3e6d17542013d3800f16426bacbb4d1786f58272e9185'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected-manifest-sha256',default=ORIGINAL_MANIFEST_SHA256)
    a=p.parse_args()
    if a.output.exists():p.error('Output must be a new directory')
    data=a.manifest.read_bytes();actual=hashlib.sha256(data).hexdigest()
    if actual!=a.expected_manifest_sha256:p.error('Manifest hash mismatch')
    rows=json.loads(data.decode('utf-8-sig'));seen=set()
    if not isinstance(rows,list) or not rows:p.error('Expected nonempty released Manifest')
    for r in rows:
        if r.get('record_id') in seen:p.error('Duplicate record_id')
        seen.add(r['record_id'])
        if not (r.get('training_eligible') is True and r.get('split_role')=='TRAIN' and r.get('source_label') in LABELS and r.get('lineage_group_id') and r.get('feature_order')==ORDER and r.get('feature_config_version')=='lab07-harmonic-6d-0.1' and r.get('input_channel')=='CH1'):p.error('Manifest eligibility or feature contract mismatch')
        x=r.get('features')
        if not isinstance(x,list) or len(x)!=6 or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in x) or x[-1]<1:p.error('Invalid input')
    if {r['source_label'] for r in rows}!=set(LABELS):p.error('Four released classes required')
    import numpy as np,sklearn,joblib,platform
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    X=np.array([r['features'] for r in rows],dtype=np.float32)
    if not np.isfinite(X).all():p.error('float32 overflow')
    y=np.array([LABELS.index(r['source_label']) for r in rows]);g=[r['lineage_group_id'] for r in rows]
    counts=Counter(g);weights=np.array([1/counts[v] for v in g]);weights*=len(weights)/weights.sum()
    models={'logistic_regression':make_pipeline(StandardScaler(),LogisticRegression(max_iter=3000,random_state=20261102)),
            'random_forest':RandomForestClassifier(n_estimators=160,max_depth=12,min_samples_leaf=2,random_state=20261102,n_jobs=1)}
    a.output.mkdir(parents=True);hashes={}
    for name,model in models.items():
        if name=='logistic_regression':model.fit(X,y,standardscaler__sample_weight=weights,logisticregression__sample_weight=weights)
        else:model.fit(X,y,sample_weight=weights)
        path=a.output/(name+'.joblib');joblib.dump(model,path);hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest=dict(model_version='limited-scope-physical-reproduction',feature_order=ORDER,feature_config_version='lab07-harmonic-6d-0.1',input_channel='CH1',shape=[6],labels=[dict(id=i,name=c) for i,c in enumerate(LABELS)],release_scope='TRAINING_ONLY',training_manifest_sha256=actual,models=hashes,dependencies=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__,joblib=joblib.__version__),production_or_board_release=False)
    (a.output/'model_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status='RETRAINED_NEW_ARTIFACTS_NOT_ORIGINAL_RELEASE',rows=len(rows),lineages=len(counts),models=hashes)))
if __name__=='__main__':main()
