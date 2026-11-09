from pathlib import Path
from collections import defaultdict
import json,hashlib,datetime
W=Path(__file__).resolve().parents[1];C=W/'04_CERTIFICATION'
a=json.loads((C/'ORIGINAL_936_INPUTS_AND_STATUSES.json').read_text());groups=defaultdict(list)
for r in a:
    i=r['input']
    if r['original_status'] in ['EQ','STRICT']:groups[(r['original_status'],i['eta_c'],i['row_form'])].append(r)
reg=[r for k in sorted(groups) for r in sorted(groups[k],key=lambda r:r['input']['case_id'])[:2]]
ug=defaultdict(list)
for r in a:
    if r['original_status']=='TIMEOUT':i=r['input'];ug[(i['T'],i['eta_c'],i['row_form'])].append(r)
pilot=[sorted(ug[k],key=lambda r:r['input']['case_id'])[0] for k in sorted(ug)]
obj=dict(registration_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),regression=reg,unresolved_pilot=pilot,all_unresolved=[r for r in a if r['original_status']=='TIMEOUT'],selection='first2 per original certified status/efficiency/row stratum; first1 per unresolved horizon/efficiency/row stratum; no new result inspected')
(C/'REGISTERED_CERTIFICATION_INPUTS.json').write_text(json.dumps(obj,indent=2),encoding='utf-8')
with (C/'ALGORITHM_EXPERIMENT_CARD.md').open('a',encoding='utf-8') as f:f.write('\nPre-run refinement of M3: an exact stationary-flow candidate c=(P+aux)/(eta+1),d=eta*c-aux keeps original relaxed energy constant and can be checked before the linear SMT repair. It is tried uniformly where applicable, never copied from a saved vector. It is ordinary constructive certificate extraction, not a new theorem or a change of model. This refinement precedes all new optimization results.\n')
print({'regression':len(reg),'unresolved_pilot':len(pilot),'unresolved_census':len(obj['all_unresolved'])})
