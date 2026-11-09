from pathlib import Path
from fractions import Fraction as F
import itertools,json,sys
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1];sys.path.insert(0,str(ROOT/'RUN_CONTROL'));import run_health as h
out=BASE/'F2_IDEAL_HULL_EXACT_v0_1.json'
assert not out.exists(),'Preserve existing result; verified tests must not be rerun here'
step=F(1,4);drain=F(7,1000);P=F(1,2);lo=F(3,25);hi=F(57,100);bc=F(50,3);bd=F(25,3);initial=F(519,1000)
def simulate(e0,eta,flows):
 e=e0;states=[];margins=[]
 for c,d in flows:
  q=c-d;prev=e;e+=step*(eta*c-d-drain);states.append(e)
  margins += [-c,-d,c+d-P,lo-e,e-hi]
  for v in [prev,e]:margins += [q+bc*v-bc*hi,-q-bd*v+bd*lo]
 return states,margins
records=[]
for eta,a in itertools.product([F(13,20),F(9,10),F(1)],[F(0),F(1,20),F(1,10)]):
 components=[]
 for q1 in [a,-a]:
  c1=max(q1,F(0));d1=max(-q1,F(0));e1=initial+step*(eta*c1-d1-drain)
  c2=bc*(hi-e1+step*drain)/(1+bc*step*eta)
  flows=[(c1,d1),(c2,F(0))];states,margins=simulate(initial,eta,flows)
  assert all(x<=0 for x in margins) and all(c*d==0 for c,d in flows)
  components.append({'flows':flows,'states':states})
 mid=[tuple((components[0]['flows'][t][j]+components[1]['flows'][t][j])/2 for j in range(2)) for t in range(2)]
 rel,rm=simulate(initial,eta,mid);assert all(x<=0 for x in rm)
 assert rel==[(components[0]['states'][t]+components[1]['states'][t])/2 for t in range(2)]
 net=[(max(c-d,F(0)),max(d-c,F(0))) for c,d in mid]
 phys,pm=simulate(initial,eta,net);assert all(lo<=v<=hi for v in phys)
 excess=net[1][0]+bc*phys[1]-bc*hi;expected=bc*step*(1-eta)*a/2
 assert excess==expected
 assert (max(pm)>0)==(eta<1 and a>0)
 old=initial-2*step*(eta*P-drain);oldstates,oldrows=simulate(old,eta,[(P,F(0)),(P,F(0))]);assert oldstates[-1]==initial and all(v<=0 for v in oldrows)
 assert old+2*step*(eta*P-drain)==initial<hi-P/bc
 records.append({'eta_c':str(eta),'amplitude_MW':str(a),'earlier_state_MWh':str(old),'current_state_MWh':str(initial),'two_physical_components':components,'convex_weights':['1/2','1/2'],'midpoint_relaxed_flows':mid,'midpoint_relaxed_energy':rel,'net_executed_flows':net,'net_executed_energy':phys,'physical_SOC_pass':True,'native_power_violation_MW':str(excess),'fraction_rated_power':str(excess/P),'inside_exact_convex_hull':True,'full_native_checker_rejects':max(pm)>0})
result={'timestamp':h.now(),'risk_closed':'C5 strongest convex relaxation and C4 beyond SOC','constructed_cases':len(records),'SOC_valid_native_fail':sum(F(r['native_power_violation_MW'])>0 for r in records),'zero_difference_controls':sum(F(r['native_power_violation_MW'])==0 for r in records),'qa_failures':0,'records':records,'script_sha256':h.sha(Path(__file__)),'protocol_sha256':h.sha(BASE/'F2_IDEAL_HULL_TEST_PROTOCOL_v0_1.md')}
with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,default=str)
s=h.read(ROOT/'CURRENT_STATE.json');h.event(ROOT,'F2_IDEAL_HULL_BOUNDARY_VERIFIED',s,{k:v for k,v in result.items() if k!='records'},'PASS',scientific_risk='C5_C4')
print(json.dumps({k:v for k,v in result.items() if k!='records'}))
