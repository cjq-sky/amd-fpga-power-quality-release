"""Compare independently produced replay results; standard library, no model execution."""
import argparse,hashlib,json,math,re
from pathlib import Path

def finite(x): return type(x) in (int,float) and math.isfinite(x)
def compare(contract,expected,actual):
    errors=[]; max_diff=0.0
    features=contract.get('feature_order'); labels=contract.get('labels'); tolerance=contract.get('probability_tolerance'); model=contract.get('model_sha256')
    def unique_strings(x): return isinstance(x,list) and bool(x) and all(isinstance(v,str) and v for v in x) and len(x)==len(set(x))
    if not unique_strings(features) or not unique_strings(labels): raise ValueError('Contract needs unique nonempty feature_order and labels')
    if not finite(tolerance) or tolerance<0: raise ValueError('Invalid frozen probability tolerance')
    if not isinstance(model,str) or not re.fullmatch('[a-fA-F0-9]{64}',model): raise ValueError('Invalid model SHA256')
    def rows(doc,side):
        for key in ['feature_order','labels','model_sha256']:
            if doc.get(key)!=contract[key]: errors.append(side+': CONTRACT_MISMATCH '+key)
        items=doc.get('rows')
        if not isinstance(items,list) or not items: raise ValueError(side+': expected nonempty rows')
        found={}
        for row in items:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id']: raise ValueError(side+': invalid row id')
            key=row['id']
            if key in found: errors.append(side+': DUPLICATE_ID '+key)
            found[key]=row
            if 'input' not in row: errors.append(side+': MISSING_INPUT '+key)
            if row.get('status')=='REJECTED':
                if 'label' not in row or 'probabilities' not in row or row['label'] is not None or row['probabilities'] is not None: errors.append(side+': REJECTED_HAS_PREDICTION '+key)
            elif row.get('status')=='ACCEPTED':
                x=row.get('input'); p=row.get('probabilities')
                if not isinstance(x,list) or len(x)!=len(features) or not all(finite(v) for v in x): errors.append(side+': INVALID_INPUT '+key)
                if row.get('label') not in labels: errors.append(side+': INVALID_LABEL '+key)
                if not isinstance(p,list) or len(p)!=len(labels) or not all(finite(v) and 0<=v<=1 for v in p) or abs(sum(p)-1)>1e-6: errors.append(side+': INVALID_PROBABILITIES '+key)
            else: errors.append(side+': INVALID_STATUS '+key)
        return found
    left=rows(expected,'expected');right=rows(actual,'actual')
    if left.keys()!=right.keys(): errors.append('ROW_SET_MISMATCH')
    for key in left.keys() & right.keys():
        a,b=left[key],right[key]
        if a.get('input')!=b.get('input'): errors.append('INPUT_MISMATCH '+key)
        if a.get('status')!=b.get('status'): errors.append('STATUS_MISMATCH '+key)
        if a.get('label')!=b.get('label'): errors.append('CLASS_MISMATCH '+key)
        if a.get('status')==b.get('status')=='ACCEPTED':
            pa,pb=a.get('probabilities'),b.get('probabilities')
            if isinstance(pa,list) and isinstance(pb,list) and len(pa)==len(pb)==len(labels) and all(finite(v) for v in pa+pb):
                delta=max(abs(x-y) for x,y in zip(pa,pb));max_diff=max(max_diff,delta)
                if delta>tolerance:errors.append('PROBABILITY_MISMATCH '+key)
    return dict(status='FAIL' if errors else 'PASS',errors=errors,expected_rows=len(left),actual_rows=len(right),max_probability_abs_difference=max_diff,probability_tolerance=tolerance,scope='Numerical replay comparison only',independent_performance_assessed=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['contract','expected','actual','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.output.resolve() in [x.resolve() for x in [a.contract,a.expected,a.actual]]:p.error('Choose a new report path')
    try:
        paths=[a.contract,a.expected,a.actual]; blobs=[x.read_bytes() for x in paths]
        report=compare(*(json.loads(b.decode('utf-8-sig')) for b in blobs))
        report['input_sha256']={str(x):hashlib.sha256(b).hexdigest() for x,b in zip(paths,blobs)}
    except (ValueError,OSError,TypeError,KeyError) as e:report=dict(status='FAIL',error=str(e))
    try:
        with a.output.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
    except OSError as e:p.error(str(e))
    print(json.dumps(report,ensure_ascii=False));return 0 if report['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
