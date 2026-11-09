"""Complete the independent lexicographic secondary-cost check for every fixed case."""
from pathlib import Path
from fractions import Fraction as F
import json,time,csv
from system_model import numerical
W=Path(__file__).resolve().parents[1];Q=W/'06_INDEPENDENT_QA';D=Q/'SERVICE_SECONDARY_RUNS';D.mkdir(exist_ok=True)
rows=[];start=time.perf_counter()
for path in sorted((W/'03_SYSTEM_CASE/RESULTS').glob('*.json')):
    obj=json.loads(path.read_text());cfg=obj['input']
    for mode in ['relaxed','exclusive']:
        target=D/(path.stem+'_'+mode+'.json')
        if target.exists():r=json.loads(target.read_text(encoding='utf-8'))
        else:
            ex=obj['service'][mode]['exact'];r=numerical(cfg,mode=='exclusive',objective='cost',budget=obj['service_budget'],fixed_service=ex['service_objective']);r.update(input_case=path.stem,mode=mode,exact_secondary_cost=ex['cost']);assert r['success'];assert abs(r['objective']-float(F(ex['cost'])))<1e-6*max(1,abs(r['objective']));target.write_text(json.dumps(r,indent=2),encoding='utf-8')
        rows.append(dict(case=path.stem,mode=mode,numerical_cost=r['objective'],exact_cost=r['exact_secondary_cost'],difference=r['objective']-float(F(r['exact_secondary_cost'])),wall_seconds=r['wall_seconds'],pass_all=True))
with (Q/'SERVICE_SECONDARY_QA.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(Q/'SERVICE_SECONDARY_QA.json').write_text(json.dumps(dict(status='PASS',independent_secondary_optimizations=len(rows),all_cases_checked=True,maximum_absolute_difference=max(abs(r['difference']) for r in rows),reason='Initial independent numerical comparison covered the primary service optimum only. This review adds the fixed-service secondary cost check, without changing any inputs, exact outputs, or classifications.',wall_seconds=time.perf_counter()-start),indent=2),encoding='utf-8')
print((Q/'SERVICE_SECONDARY_QA.json').read_text(encoding='utf-8'))
