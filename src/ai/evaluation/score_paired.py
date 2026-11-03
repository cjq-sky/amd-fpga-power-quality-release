"""Score two independently executed models on one approved, frozen cohort; no inference."""
import argparse,hashlib,json,math,re
from pathlib import Path

def index(rows):
    if not isinstance(rows,list) or not rows:raise ValueError('Expected nonempty rows')
    result={}
    for r in rows:
        if not isinstance(r,dict) or not isinstance(r.get('id'),str) or not r['id'] or r['id'] in result:raise ValueError('Missing or duplicate row id')
        result[r['id']]=r
    return result

def score(cohort,prediction):
    labels=cohort.get('labels');features=cohort.get('feature_order')
    for v in [labels,features]:
        if not isinstance(v,list) or not v or any(not isinstance(x,str) or not x for x in v) or len(set(v))!=len(v):raise ValueError('Invalid labels or feature_order')
    if prediction.get('labels')!=labels or prediction.get('feature_order')!=features:raise ValueError('Prediction contract mismatch')
    if not re.fullmatch('[a-f0-9]{64}',prediction.get('model_sha256','')):raise ValueError('Model SHA256 required')
    truth=index(cohort['rows']);items=prediction.get('rows')
    found=index(items) if items else {}
    if set(found)-set(truth):raise ValueError('Unexpected prediction ids')
    n=len(labels);matrix=[[0]*(n+1) for _ in labels];events=[];runs={}
    for ident,row in truth.items():
        x=row.get('input');label=row.get('source_label');run=row.get('run_id')
        if row.get('eligible') is not True or label not in labels or not isinstance(run,str) or not run:raise ValueError('Cohort needs released labels, eligibility and Run ids')
        if not isinstance(x,list) or len(x)!=len(features) or any(type(v) not in (int,float) or not math.isfinite(v) for v in x):raise ValueError('Invalid frozen input')
        pred=found.get(ident);actual=None;reason='MISSING_OUTPUT'
        if pred:
            if pred.get('input')!=x:raise ValueError('Input mismatch: '+ident)
            status=pred.get('status')
            if status=='ACCEPTED':
                if pred.get('label') not in labels:raise ValueError('Accepted output has invalid label')
                probs=pred.get('probabilities')
                if not isinstance(probs,list) or len(probs)!=n or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in probs) or abs(sum(probs)-1)>1e-6:raise ValueError('Invalid probabilities')
                actual=pred['label'];reason=None
            elif status in ['REJECTED','ERROR']:
                if 'label' not in pred or 'probabilities' not in pred or pred['label'] is not None or pred['probabilities'] is not None:raise ValueError('Failed output must have explicit null prediction')
                reason=status
            else:raise ValueError('Invalid prediction status')
        correct=actual==label;matrix[labels.index(label)][labels.index(actual) if actual else n]+=1
        rr=runs.setdefault(run,{'total':0,'correct':0});rr['total']+=1;rr['correct']+=int(correct)
        events.append(dict(id=ident,run_id=run,source_label=label,prediction=actual,correct=correct,failure_reason=reason))
    per=[]
    for k,label in enumerate(labels):
        support=sum(matrix[k]);accepted_support=sum(matrix[k][:n]);tp=matrix[k][k];predicted=sum(row[k] for row in matrix)
        precision=tp/predicted if predicted else None;recall=tp/accepted_support if accepted_support else None
        per.append(dict(label=label,support=support,accepted_support=accepted_support,correct=tp,service_recall=tp/support if support else None,precision=precision,conditional_recall=recall,conditional_f1=2*tp/(accepted_support+predicted) if accepted_support+predicted else None,failed_outputs=matrix[k][n]))
    accepted=sum(sum(r[:n]) for r in matrix);correct=sum(matrix[k][k] for k in range(n))
    for r in runs.values():r['accuracy']=r['correct']/r['total']
    complete=all(p['support'] and p['accepted_support'] for p in per)
    return dict(model_sha256=prediction['model_sha256'],total=len(truth),correct=correct,service_accuracy=correct/len(truth),accepted_outputs=accepted,failed_outputs=len(truth)-accepted,conditional_accuracy=correct/accepted if accepted else None,run_equal_weight_accuracy=sum(r['accuracy'] for r in runs.values())/len(runs),conditional_macro_f1=sum(p['conditional_f1'] for p in per)/n if complete else None,operation_matrix=matrix,row_labels=labels,column_labels=labels+['ABSTAIN_OR_ERROR'],confusion_matrix=[r[:n] for r in matrix],per_class=per,per_run=runs,all_results=events,independent_source_assessment='Not inferred by scorer; disclose cohort source/family history')

def paired(cohort,left,right):
    a,b=score(cohort,left),score(cohort,right)
    return dict(status='SCORED',left=a,right=b,disagreements=[dict(id=x['id'],left=x['prediction'],right=y['prediction']) for x,y in zip(a['all_results'],b['all_results']) if x['prediction']!=y['prediction']],notes='All approved cohort rows remain in each service denominator; missing/rejected/error is not a fifth label. No model selection is automated.')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['cohort','left','right','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Choose a new output path')
    try:
        paths=[a.cohort,a.left,a.right];blobs=[x.read_bytes() for x in paths]
        report=paired(*(json.loads(b.decode('utf-8-sig')) for b in blobs))
        report['file_sha256']={str(x):hashlib.sha256(b).hexdigest() for x,b in zip(paths,blobs)}
    except (OSError,TypeError,KeyError,ValueError) as e:report=dict(status='INVALID_INPUT',error=str(e))
    with a.output.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in report.items() if k in ['status','error']},ensure_ascii=False))
    return 0 if report['status']=='SCORED' else 2
if __name__=='__main__':raise SystemExit(main())
