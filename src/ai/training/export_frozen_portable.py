"""Export trusted original frozen joblib weights to the exact portable JSON format.

Packaging adapter of export_portable_v11.py. Does not retrain or generate golden data.
"""
import argparse,hashlib,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--models-dir',type=Path,required=True)
    p.add_argument('--deployment-template',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Output must be a new directory')
    template_bytes=a.deployment_template.read_bytes()
    if hashlib.sha256(template_bytes).hexdigest()!='5516b50719be3a0e0cc170a96d72f2e7498686477fdf32a0297a9dcf38003928':p.error('Expected original portable1.1 manifest template')
    original=json.loads((a.models_dir/'model_manifest.json').read_text(encoding='utf-8-sig'))
    template=json.loads(template_bytes);payload={}
    # Verify the trusted release bytes before unpickling.
    for name,entry in template['models'].items():
        path=a.models_dir/(name+'.joblib')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['original_model_sha256'] or original['models'][name]!=entry['original_model_sha256']:p.error('Original model hash mismatch')
    import joblib
    for name,entry in template['models'].items():
        path=a.models_dir/(name+'.joblib');model=joblib.load(path)
        base=dict(algorithm=name,model_version=original['model_version'],original_model_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),input_shape=[6],feature_config_version=original['feature_config_version'],feature_order=original['feature_order'],input_dtype='float32',classes=[0,1,2,3],labels=[x['name'] for x in original['labels']],release_scope='TRAINING_ONLY')
        if name=='logistic_regression':
            s=model.steps[0][1];c=model.steps[1][1];base.update(mean=s.mean_.tolist(),scale=s.scale_.tolist(),coef=c.coef_.tolist(),intercept=c.intercept_.tolist())
        else:
            trees=[]
            for estimator in model.estimators_:
                t=estimator.tree_;trees.append(dict(left=t.children_left.tolist(),right=t.children_right.tolist(),feature=t.feature.tolist(),threshold=t.threshold.tolist(),value=t.value[:,0,:].tolist()))
            base['trees']=trees
        # Original Windows export used CRLF; preserve bytes on every platform.
        data=json.dumps(base,ensure_ascii=False,indent=2,allow_nan=False).replace('\n','\r\n').encode('utf-8')
        if hashlib.sha256(data).hexdigest()!=entry['sha256']:p.error('Export differs from frozen JSON; check original environment')
        payload[entry['file']]=data
    a.output.mkdir(parents=True)
    for name,data in payload.items():(a.output/name).write_bytes(data)
    (a.output/'deployment_manifest.json').write_bytes(template_bytes)
    print(json.dumps(dict(status='EXACT_ORIGINAL_PORTABLE_JSON_REPRODUCED',models=list(payload),golden='External controlled TRAIN golden remains outside repository')))
if __name__=='__main__':main()
