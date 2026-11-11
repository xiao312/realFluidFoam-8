"""Fixed paper-curve metrics. No candidate import, chemistry, fitting or acceptance."""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path


HERE=Path(__file__).resolve().parent


def number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def prediction_at(curve,queries):
    if curve is None:return [None]*len(queries)
    x,y=curve['x'],curve['y']
    if len(x)!=len(y) or len(x)<2:raise ValueError('Invalid curve dimensions')
    if not all(number(v) for v in x):raise ValueError('Invalid x')
    if any(b<=a for a,b in zip(x,x[1:])):raise ValueError('x must increase strictly')
    if any(v is not None and not number(v) for v in y):raise ValueError('Invalid y; use null for missing')
    output=[]
    for value in queries:
        hi=bisect.bisect_left(x,value)
        if hi<len(x) and x[hi]==value:output.append(y[hi]);continue
        if hi==0 or hi==len(x) or y[hi-1] is None or y[hi] is None:
            output.append(None);continue
        w=(value-x[hi-1])/(x[hi]-x[hi-1])
        output.append((1-w)*y[hi-1]+w*y[hi])
    return output


def evaluate(prediction,reference):
    results={};groups={1:[],2:[]};coverage=[]
    for ref in reference['curves']:
        points=ref['points'];x=[p[0] for p in points];truth=[p[1] for p in points]
        if len(x)<2 or any(b<=a for a,b in zip(x,x[1:])):raise ValueError('Invalid fixed reference')
        pred=prediction_at(prediction.get('curves',{}).get(ref['id']),x)
        bounds=(0.,6000.) if ref['quantity']=='T' else (-1e-8,1+1e-8)
        if any(v is not None and not bounds[0]<=v<=bounds[1] for v in pred):
            raise ValueError('Gross physical range violation: '+ref['id'])
        weights=[(x[1]-x[0])/2]+[(x[i+1]-x[i-1])/2 for i in range(1,len(x)-1)]+[(x[-1]-x[-2])/2]
        total=sum(weights);valid=[i for i,v in enumerate(pred) if v is not None]
        covered=sum(weights[i] for i in valid)/total
        # A missing value is worse than either admissible bound at this reference
        # point. Deleting a difficult prediction cannot improve its loss.
        mse=sum(w*((p-t)/ref['scale'])**2 if p is not None else
                w*(1+max(((bound-t)/ref['scale'])**2 for bound in bounds))
                for w,p,t in zip(weights,pred,truth))/total
        valid_weight=sum(weights[i] for i in valid)
        rmse=math.sqrt(sum(weights[i]*(pred[i]-truth[i])**2 for i in valid)/valid_weight) if valid else None
        results[ref['id']]={'RMSE':rmse,'unit':ref['unit'],'normalized_RMSE_with_missing_penalty':math.sqrt(mse),
            'coverage':covered,'reference_samples':len(x),'covered_samples':len(valid)}
        groups[ref['figure']].append(mse);coverage.append(covered)
    group={str(k):math.sqrt(sum(v)/len(v)) for k,v in groups.items()}
    mean_coverage=sum(coverage)/len(coverage)
    loss=.8*group['2']+.2*group['1']
    return {'schema':'sharma-paper-metrics/v1','curves':results,'figure_normalized_RMSE':group,
        'mean_coverage':mean_coverage,'combined_score':math.exp(-10*loss-2*(1-mean_coverage)),
        'validity':1,'scientific_acceptance':False,
        'scope':'Curve agreement only. Physical evidence and independent replay are reviewed separately.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prediction',type=Path)
    parser.add_argument('--reference',type=Path,default=HERE/'references/curves.json')
    parser.add_argument('--out',type=Path);parser.add_argument('--plan',action='store_true');args=parser.parse_args()
    reference=json.loads(args.reference.read_text(encoding='utf-8'))
    if args.plan:
        print(json.dumps({k:v for k,v in reference.items() if k!='curves'}));
        print(json.dumps([{'id':v['id'],'samples':len(v['points']),'scale':v['scale']} for v in reference['curves']],indent=2));return
    if args.prediction is None:parser.error('--prediction is required')
    result=evaluate(json.loads(args.prediction.read_text(encoding='utf-8')),reference)
    result.update(reference_sha256=hashlib.sha256(args.reference.read_bytes()).hexdigest(),
        prediction_sha256=hashlib.sha256(args.prediction.read_bytes()).hexdigest(),
        evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if args.out:
        if args.out.exists():raise ValueError('Refusing existing metrics file')
        args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
