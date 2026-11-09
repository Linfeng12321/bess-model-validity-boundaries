"""Independent unlifted cvc5 BOX query and direct Fraction/dual-row check.
No LP producer or original reconstruction functions imported.
"""
from pathlib import Path
from fractions import Fraction as Q
import copy,json,time,cvc5
D=Path(__file__).resolve().parent;O=D/'11_SCIENTIFIC_DEPTH_ADDENDUM/BOX_EXACT_LP'
def main():
 start=time.perf_counter();cases=json.loads((O/'REGISTERED_CASES.json').read_text())['cases'];results=[];dual_count=0
 for cfg in cases:
  cert=json.loads((O/(cfg['id']+'_EXACT_LP_CERTIFICATE.json')).read_text());assert cert['input']==cfg;T=cfg['T'];s=cvc5.Solver();s.setLogic('QF_LRA');s.setOption('produce-models','true');s.setOption('tlimit-per','10000');real=s.getRealSort();k=cvc5.Kind
  num=lambda x:s.mkReal(str(Q(x)));add=lambda xs:xs[0] if len(xs)==1 else s.mkTerm(k.ADD,*xs) if xs else num(0);mul=lambda a,b:s.mkTerm(k.MULT,a,b);sub=lambda a,b:s.mkTerm(k.SUB,a,b)
  # Interleaved native variables, independent of the producer's vector layout.
  native=[[s.mkConst(real,f'physical_{cfg["id"]}_{t}_{tag}') for tag in ['charge','discharge','energy']] for t in range(T)];bad=[];prev=num(cfg['e0']);recprev=prev
  for t,(c,d,e) in enumerate(native):
   for x,upper in [(c,cfg['C'][t]),(d,cfg['D'][t])]:s.assertFormula(s.mkTerm(k.GEQ,x,num(0)));s.assertFormula(s.mkTerm(k.LEQ,x,num(upper)))
   s.assertFormula(s.mkTerm(k.GEQ,e,num(cfg['lower'][t])));s.assertFormula(s.mkTerm(k.LEQ,e,num(cfg['upper'][t])))
   rhs=add([mul(num(cfg['rho'][t]),prev),mul(num(Q(cfg['h'][t])*Q(cfg['eta_c'][t])),c),mul(num(-Q(cfg['h'][t])/Q(cfg['eta_d'][t])),d),num(cfg['b'][t])]);s.assertFormula(s.mkTerm(k.EQUAL,e,rhs))
   if cfg['shared'][t] is not None:s.assertFormula(s.mkTerm(k.LEQ,add([c,d]),num(cfg['shared'][t])))
   x=sub(c,d);charged=mul(num(cfg['eta_c'][t]),x);discharged=mul(num(1/Q(cfg['eta_d'][t])),x);u=s.mkTerm(k.ITE,s.mkTerm(k.GEQ,x,num(0)),charged,discharged)
   recprev=add([mul(num(cfg['rho'][t]),recprev),mul(num(cfg['h'][t]),u),num(cfg['b'][t])]);bad.extend([s.mkTerm(k.GT,recprev,num(cfg['upper'][t])),s.mkTerm(k.LT,recprev,num(cfg['lower'][t]))]);prev=e
  if cfg['terminal'] is not None:
   lo,hi=cfg['terminal'];s.assertFormula(s.mkTerm(k.GEQ,native[-1][2],num(lo)));s.assertFormula(s.mkTerm(k.LEQ,native[-1][2],num(hi)));bad.extend([s.mkTerm(k.LT,recprev,num(lo)),s.mkTerm(k.GT,recprev,num(hi))])
  s.push();feas=s.checkSat();s.pop();s.assertFormula(s.mkTerm(k.OR,*bad));decision=s.checkSat();label='EMPTY' if feas.isUnsat() else 'STRICT' if decision.isSat() else 'EQ' if decision.isUnsat() else 'UNKNOWN';assert label==cert['classification'],(cfg['id'],label,cert['classification'])
  # Independently rebuild every standard-form row with named native variables.
  expected=[];up=list(map(Q,cfg['upper']));lo=list(map(Q,cfg['lower']))
  if cfg['terminal'] is not None:lo[-1]=max(lo[-1],Q(cfg['terminal'][0]));up[-1]=min(up[-1],Q(cfg['terminal'][1]))
  def push(name,co,rhs):expected.append(dict(id=name,a={int(j):Q(x) for j,x in co.items() if x},b=Q(rhs)))
  for t in range(T):
   for name,idx,low,high in [('c',t,0,Q(cfg['C'][t])),('d',T+t,0,Q(cfg['D'][t])),('e',2*T+t,lo[t],up[t])]:push(name+'_lower_'+str(t),{idx:-1},-Q(low));push(name+'_upper_'+str(t),{idx:1},high)
   h=Q(cfg['h'][t]);eta=Q(cfg['eta_c'][t]);ed=Q(cfg['eta_d'][t]);rho=Q(cfg['rho'][t]);co={2*T+t:Q(1),t:-h*eta,T+t:h/ed};rhs=Q(cfg['b'][t])
   if t:co[2*T+t-1]=-rho
   else:rhs+=rho*Q(cfg['e0'])
   push('dyn_plus_'+str(t),co,rhs);push('dyn_minus_'+str(t),{j:-a for j,a in co.items()},-rhs)
   if cfg['shared'][t] is not None:push('shared_'+str(t),{t:1,T+t:1},cfg['shared'][t])
   push('hyp_charge_'+str(t),{3*T+t:1,t:-eta,T+t:eta},0);push('hyp_discharge_'+str(t),{3*T+t:1,t:-1/ed,T+t:1/ed},0)
  assert expected==[dict(id=r['id'],a={int(j):Q(v) for j,v in r['a'].items()},b=Q(r['b'])) for r in cert['rows']]
  for p in cert['prefixes']:
   values=list(map(Q,p['primal_vector']));lam=list(map(Q,p['dual_multipliers']));coeff={int(j):Q(v) for j,v in p['objective_coefficients'].items()};constant=Q(p['objective_constant']);kk=p['k'];f=Q(cfg['e0'])
   for t in range(kk+1):f=Q(cfg['rho'][t])*f+Q(cfg['b'][t])
   wanted={}
   for t in range(kk+1):
    coefficient=Q(cfg['h'][t])
    for r in range(t+1,kk+1):coefficient*=Q(cfg['rho'][r])
    if coefficient:wanted[3*T+t]=coefficient
   assert coeff==wanted and constant==f-up[kk];assert all(x>=0 for x in lam)
   assert all(sum((a*values[j] for j,a in r['a'].items()),Q(0))<=r['b'] for r in expected)
   assert all(sum((r['a'].get(j,Q(0))*x for r,x in zip(expected,lam)),Q(0))==coeff.get(j,Q(0)) for j in range(4*T))
   primal=sum((v*values[j] for j,v in coeff.items()),Q(0))+constant;dual=sum((r['b']*v for r,v in zip(expected,lam)),Q(0))+constant;assert primal==dual==Q(p['maximum_residual']);dual_count+=1
   if primal>0:
    e=Q(cfg['e0']);rec=[]
    for t in range(T):
     x=values[t]-values[T+t];e=Q(cfg['rho'][t])*e+Q(cfg['h'][t])*(Q(cfg['eta_c'][t])*max(x,Q(0))-max(-x,Q(0))/Q(cfg['eta_d'][t]))+Q(cfg['b'][t]);rec.append(e)
    assert rec[kk]>up[kk]
  results.append(dict(id=cfg['id'],classification=label,cvc5_nonempty=str(feas),cvc5_original_query_decision=str(decision),exact_lp_dual='PASS'))
 # Boundary-only nonconvex validity example is exact analytically, not a grid estimate.
 assert {x['id']:x['classification'] for x in results if x['id'].startswith('param_')}=={'param_endpoint0':'EQ','param_interior':'STRICT','param_endpoint1':'EQ'}
 # Out-of-scope SOC power row: energy remains feasible but native power fails.
 c=Q(3,5);d=Q(3,20);e0=Q(7,10);er=e0+c/2-d;ex=e0+(c-d)/2
 assert c+d<=1 and c+4*er<=4 and 0<=er<=Q(3,2) and 0<=ex<=Q(3,2) and c-d+4*ex>4
 negative=dict(energy_only_criterion_invalid_for_extra_SOC_row=True,relaxed_E=str(er),exclusive_E=str(ex),native_power_excess=str(c-d+4*ex-4),negative_retention_outside_nonnegative_weight_premise=True)
 result=dict(status='PASS',cases=len(cases),independent_direct_cvc5=True,independent_standard_row_rebuild=True,primal_dual_pairs_verified=dual_count,results=results,scope_attacks=negative,new_original_theorem=False,wall_seconds=time.perf_counter()-start)
 (O/'BOX_INDEPENDENT_QA.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
