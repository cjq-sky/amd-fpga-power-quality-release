"""Run a frozen model on saved checked Adapter results. Does not own a Reader."""
import argparse,json,copy
from pathlib import Path
from portable_model import PortableModel

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir',type=Path,required=True)
    p.add_argument('--algorithm',choices=['logistic_regression','random_forest'],default='logistic_regression')
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.output.resolve()==a.input.resolve():p.error('Choose new output path')
    data=json.loads(a.input.read_text(encoding='utf-8-sig'))
    if not isinstance(data,list) or not data:p.error('Input must be a nonempty list of {id, checked}')
    ids=[r['id'] for r in data]
    if len(ids)!=len(set(ids)):p.error('Duplicate id')
    model=PortableModel(a.model_dir,a.algorithm);out=[]
    for r in data:
        try:result=model.predict_checked(copy.deepcopy(r['checked']))
        except Exception as exc:result=dict(input_status='ERROR',class_id=None,model_prediction=None,probabilities=None,error=type(exc).__name__+': '+str(exc))
        out.append(dict(id=r['id'],result=result))
    with a.output.open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps(dict(rows=len(out),algorithm=a.algorithm,model_sha256=model.model_hash)))
if __name__=='__main__':main()
