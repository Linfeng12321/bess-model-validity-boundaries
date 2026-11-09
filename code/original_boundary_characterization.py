from pathlib import Path
from fractions import Fraction as F
import sys,json,time,itertools,os
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE));import run_parametric_region_pilot as m
z3=m.z3;h=m.h;e=m.e;A=m.A;xs=m.xs;Q=m.Q
OUT=BASE/'f2_closed_region_v1';OUT.mkdir(exist_ok=True)
def save(p,x):
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,default=str)
def check(expr,seconds=10):
 s=z3.Solver();s.set(timeout=seconds*1000);s.add(expr);t=time.perf_counter();ans=s.check()
 r={'status':str(ans),'seconds':time.perf_counter()-t}
 if ans==z3.sat:r['counterexample']={str(x):str(s.model().eval(x,model_completion=True)) for x in [e,A,*xs]}
 if ans==z3.unknown:r['reason']=s.reason_unknown()
 return r
start=h.now();sh=h.sha(Path(__file__))
if (OUT/'RECEIPT.json').exists():
 old=h.read(OUT/'RECEIPT.json');assert all(h.sha(OUT/a['path'])==a['sha256'] for a in old['artifacts']);print('VERIFIED_SKIP');sys.exit()
checks=[]
for regime in ['BOX','END','START']:
 path=OUT/(regime+'.json')
 if path.exists():
  r=h.read(path);assert r['script_sha256']==sh;checks.append(r);continue
 parts=[m.build(regime,s) for s in itertools.product([0,1],repeat=2)]
 feas=z3.Or([c for c,b,_,_ in parts]);bad=z3.Or([z3.And(c,b) for c,b,_,_ in parts])
 D=z3.BoolVal(True) if regime=='BOX' else A>=e-Q(F(1,9)) if regime=='END' else A>=e
 V=e<=Q(F(41,50)) if regime=='BOX' else z3.Or(A==e-Q(F(1,9)),z3.And(e<=Q(F(41,50)),A>=e+Q(F(59,50)))) if regime=='END' else z3.Or(A==e,z3.And(e<=Q(F(41,50)),A>=e+Q(F(109,100))))
 r={'regime':regime,'script_sha256':sh,'checks':{}}
 r['checks']['feasible_outside_predicted_D']=check(z3.And(m.DOMAIN,z3.Not(D),feas))
 r['checks']['predicted_D_but_empty']=check(z3.And(m.DOMAIN,D,z3.ForAll(xs,z3.Not(feas))))
 r['checks']['bad_inside_predicted_V']=check(z3.And(m.DOMAIN,V,bad))
 r['checks']['good_outside_predicted_V']=check(z3.And(m.DOMAIN,D,z3.Not(V),z3.ForAll(xs,z3.Not(bad))))
 save(path,r);checks.append(r);print(json.dumps(r),flush=True)
e0=F(1,5);ceiling=F(7,5);hstep=F(1,10);eta=F(9,10)
current=e0+hstep*eta
c1=F(19,20);d1=F(1,20);er1=current+hstep*(eta*c1-d1/eta);es1=current+hstep*eta*(c1-d1)
c2=(ceiling-er1)/(1+hstep*eta);er2=er1+hstep*eta*c2;es2=es1+hstep*eta*c2
assert c1+d1<=1 and 0<c2<1 and c1+er1<=ceiling and c2+er2==ceiling
assert 0<=es1<=1 and 0<=es2<=1 and (c1-d1)+es1<=ceiling and c2+es2>ceiling
assert 1+current<=ceiling
parts=[m.build('END',s) for s in itertools.product([0,1],repeat=2)]
bad=z3.Or([z3.And(c,b) for c,b,_,_ in parts])
before=check(z3.And(e==Q(e0),A==Q(ceiling),bad));after=check(z3.And(e==Q(current),A==Q(ceiling),bad))
assert before['status']=='unsat' and after['status']=='sat'
w={'initial_e':str(e0),'ceiling':str(ceiling),'after_valid_charge_e':str(current),'new_relaxed_c1':str(c1),'new_relaxed_d1':str(d1),'new_relaxed_c2':str(c2),'relaxed_energies':list(map(str,[er1,er2])),'executed_energies':list(map(str,[es1,es2])),'native_power_row_violation_MW':str(c2+es2-ceiling),'ordinary_executed_SOC_check':'PASS','full_native_row_check':'FAIL','initial_bad_query':before,'new_state_bad_query':after}
save(OUT/'TRANSITION.json',w)
summary={'hypothesis_checks':sum(len(r['checks']) for r in checks),'proved_unsat':sum(c['status']=='unsat' for r in checks for c in r['checks'].values()),'counterexamples':sum(c['status']=='sat' for r in checks for c in r['checks'].values()),'unknown':sum(c['status']=='unknown' for r in checks for c in r['checks'].values()),'state_transition_SOC_pass_native_fail':True,'power_row_violation_MW':w['native_power_row_violation_MW'],'execution_qa_failures':0}
save(OUT/'SUMMARY.json',summary)
save(OUT/'RECEIPT.json',{'execution_qa':'PASS','start_utc':start,'end_utc':h.now(),'pid':os.getpid(),'script_sha256':sh,'protocol_sha256':h.sha(BASE/'F2_CLOSED_REGION_HYPOTHESES_v0_1.md'),'artifacts':[{'path':p.name,'sha256':h.sha(p)} for p in sorted(OUT.glob('*.json'))],'research_gate_decision':'F2_CLOSURE_C2_C3_C4_INTERNAL_CHECK','next_action':'Interpret analytical counterexamples/UNKNOWN honestly; close source-faithful net versus gross power-row semantics and engineering scaling.'})
print(json.dumps(summary),flush=True)
