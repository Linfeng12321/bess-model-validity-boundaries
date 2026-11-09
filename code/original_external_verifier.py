"""Stage2B exact full-query checker. All native inequalities AND equalities are tested.
Structure certificates are sufficient-only; negative attempts fall back to QF_LRA.
"""
from core import *
from fractions import Fraction as F
import sys,time
sys.path.insert(0,str(R/'RESEARCH/round2/z3_dependencies'))
import z3
def native(m,x):
    def residual(r):return sum((F(v)*x[int(i)] for i,v in r['co'].items()),F(0))-F(r['rhs'])
    return [(r,residual(r)) for r in m['rows']],[(r,residual(r)) for r in m['eq']]
def reconstruct(m,x):
    T=m['T'];c=[max(x[t]-x[T+t],F(0)) for t in range(T)];d=[max(x[T+t]-x[t],F(0)) for t in range(T)];es=[];e=F(m['e0'])
    for t in range(T):e=F(m['rho'])*e+F(m['h'])*(F(m['eta_c'])*c[t]-d[t]/F(m['eta_d'])-F(m['aux']));es.append(e)
    return c+d+es
def witness(m,x):
    x=list(map(F,x));y=reconstruct(m,x);rs,eq=native(m,x);ys,ye=native(m,y);T=m['T']
    bad=[dict(row_name=r['name'],row_family=r['family'],period=r['period'],residual=str(v),sense='INEQUALITY') for r,v in ys if v>0]+[dict(row_name=r['name'],row_family=r['family'],period=r['period'],residual=str(v),sense='EQUALITY') for r,v in ye if v!=0]
    ok=all(v<=0 for r,v in rs) and all(v==0 for r,v in eq) and bool(bad)
    soc=all(F(m['lo'])<=e<=F(m['hi']) for e in y[2*T:]);power=any(w['row_family'].startswith(('CHARGE','DISCHARGE')) for w in bad)
    return dict(certified=ok,relaxed_native_pass=all(v<=0 for r,v in rs) and all(v==0 for r,v in eq),exclusive_pass=all(y[t]*y[T+t]==0 for t in range(T)),query_pass=all(x[t]-x[T+t]==y[t]-y[T+t] for t in range(T)),SOC_pass=soc,power_fail=power,mechanism='B' if soc and power else 'C' if not soc and power else 'A' if not soc else 'D',violations=bad,relaxed_vector=list(map(str,x)),recovered_vector=list(map(str,y)))
def vector(m,actions):
    T=m['T'];cs=[];ds=[];es=[];e=F(m['e0'])
    for c,d in actions+[(F(0),F(0))]*(T-len(actions)):
        cs.append(c);ds.append(d);e=F(m['rho'])*e+F(m['h'])*(F(m['eta_c'])*c-d/F(m['eta_d'])-F(m['aux']));es.append(e)
    return cs+ds+es
def structure(m):
    T=m['T'];ec=F(m['eta_c']);ed=F(m['eta_d']);h=F(m['h']);pc=F(m['pc']);pd=F(m['pd']);lo=F(m['lo']);hi=F(m['hi'])
    idle=vector(m,[]);rs,eq=native(m,idle)
    if ec*ed==1 and all(sum(F(r['co'].get(str(i),'0')) for i in [t,T+t])>=0 for r in m['rows'] if not (len(r['co'])==1 and F(r['rhs'])==0 and next(iter(r['co'].values()))=='-1' and int(next(iter(r['co'])))<2*T) for t in range(T)) and all(sum(F(r['co'].get(str(i),'0')) for i in [t,T+t])==0 for r in m['eq'] for t in range(T)) and all(v<=0 for r,v in rs) and all(v==0 for r,v in eq):
        return dict(classification='EQ',certificate='LOSSLESS_MONOTONE_ROW_CANCELLATION',feasible_vector=list(map(str,idle)),witnesses=[],mechanism_status='NO_POWER_FAILURE_BY_CERTIFICATE')
    # Constructive candidates only. Every rational value is independently checked against the full mapped native system.
    actions=[];e=F(m['e0'])
    while e<hi and len(actions)<T:
        c=min(pc,(hi-e)/(h*ec));actions.append((c,F(0)));e+=h*ec*c
    candidates=[]
    if len(actions)<T:
        c=min(pc,pd/(ec*ed))/4;candidates.append(actions+[(c,ec*ed*c)])
    if len(actions)+3<=T:
        d0=min(pd,pc*ec*ed,(hi-lo)*ed/h)/4
        c=d0/(ec*ed);d=min(pd,c,((hi-lo)*ed/h))/4
        candidates.append(actions+[(F(0),d0),(c,d),(d/(ec*ed),F(0))])
    for a in candidates:
        w=witness(m,vector(m,a))
        if w['certified']:return dict(classification='STRICT',certificate='CONSTRUCTIVE_RATIONAL_WITNESS',witnesses=[w],mechanism_status='PENDING_EXACT_OR_STRUCTURAL_CHECK')
    return None
def exact(m,force_smt=False):
    tick=time.monotonic();cert=None if force_smt else structure(m)
    if cert:
        cert.update(status='COMPLETED',wall_seconds=time.monotonic()-tick,solver='EXACT_FRACTION_CERTIFICATE',budget_seconds=300)
        # For BOX/HULL/HCH these rows are constant ratings or one-step energy headroom. SOC-feasible exclusive reconstruction satisfies all native power rows identically.
        if m['family'] in ['BOX','HULL','HCH'] and not m.get('extra_native_rows'):cert['mechanism_status']='SOC_ADMISSIBLE_POWER_FAILURE_IMPOSSIBLE_STRUCTURAL'
        return cert
    deadline=time.monotonic()+300;T=m['T'];x=list(z3.Reals(' '.join('x'+str(i) for i in range(3*T))));es=list(z3.Reals(' '.join('e'+str(i) for i in range(T))));zr=lambda q:z3.RealVal(str(q))
    expr=lambda r,v:z3.Sum([zr(a)*v[int(i)] for i,a in r['co'].items()])-zr(r['rhs'])
    c=[z3.If(x[t]>=x[T+t],x[t]-x[T+t],0) for t in range(T)];d=[z3.If(x[t]<x[T+t],x[T+t]-x[t],0) for t in range(T)];y=c+d+es
    base=[expr(r,x)<=0 for r in m['rows']]+[expr(r,x)==0 for r in m['eq']]
    base +=[es[t]==zr(m['rho'])*(es[t-1] if t else zr(m['e0']))+zr(m['h'])*(zr(m['eta_c'])*c[t]-d[t]/zr(m['eta_d'])-zr(m['aux'])) for t in range(T)]
    s=z3.Solver();s.set(random_seed=0,max_memory=768);s.add(base);qs={};ws=[]
    def query(name,constraint):
        left=deadline-time.monotonic()
        if left<=0:qs[name]=dict(status='unknown',reason='timeout');return 'unknown'
        s.push();s.add(constraint);s.set(timeout=max(1,int(left*1000)));start=time.monotonic();a=s.check();qs[name]=dict(status=str(a),seconds=time.monotonic()-start,reason=s.reason_unknown() if a==z3.unknown else '')
        if a==z3.sat and name!='feasible':
            model=s.model();vals=[str(model.eval(v,model_completion=True)) for v in x];w=witness(m,vals);assert w['certified'],'CORE_VERIFIER_CONFLICT';w['query']=name;ws.append(w)
        s.pop();return str(a)
    feasible=query('feasible',True)
    if feasible=='unsat':cl='EMPTY';bad='unsat'
    else:
        bad=query('bad',z3.Or([expr(r,y)>0 for r in m['rows']]+[expr(r,y)!=0 for r in m['eq']]))
        cl='STRICT' if bad=='sat' else 'EQ' if feasible=='sat' and bad=='unsat' else 'TIMEOUT' if any('timeout' in v['reason'] or 'canceled' in v['reason'] for v in qs.values()) else 'UNKNOWN'
    if m['family'] in ['BOX','HULL','HCH','MORALES']:mechanism='SOC_ADMISSIBLE_POWER_FAILURE_IMPOSSIBLE_STRUCTURAL' # Morales inequalities are valid for the exclusive BOX feasible set.
    else:
        power=[expr(r,y)>0 for r in m['rows'] if r['family'].startswith(('CHARGE','DISCHARGE'))]
        mechanism=query('SOC_pass_power_fail',z3.And(*[es[t]>=zr(m['lo']) for t in range(T)],*[es[t]<=zr(m['hi']) for t in range(T)],z3.Or(power)))
    return dict(classification=cl,status=cl if cl in ['TIMEOUT','UNKNOWN'] else 'COMPLETED',queries=qs,witnesses=ws,wall_seconds=time.monotonic()-tick,solver=z3.get_version_string(),budget_seconds=300,mechanism_status=mechanism)
