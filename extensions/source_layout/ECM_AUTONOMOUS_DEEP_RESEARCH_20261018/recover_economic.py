"""R1 exact active-face recovery after physical network elimination.

Uses the OLD saved economic exclusive output only, never new state selection.
Full exact-row replay and original nearby/cost limits control acceptance.
"""
from fractions import Fraction as F
import argparse,json,time
import sympy as sp
from model import D,K,build,check,configs
from network import load_map
OUT=D/'03_RTS_EXACT_NETWORK/R1';OUT.mkdir(exist_ok=True)
class Aff:
    def __init__(self,c=F(0),a=None):self.c=F(c);self.a=a or {}
    def scale(self,k):return Aff(self.c*k,{j:v*k for j,v in self.a.items() if v*k})
    def add(self,other):
        a=dict(self.a)
        for j,v in other.a.items():
            a[j]=a.get(j,F(0))+v
            if not a[j]:del a[j]
        return Aff(self.c+other.c,a)
    def evaluate(self,x):return self.c+sum((v*x[j] for j,v in self.a.items()),F(0))
def sumaff(items):
    out=Aff()
    for x in items:out=out.add(x)
    return out
def main():
    p=argparse.ArgumentParser();p.add_argument('--case',required=True);args=p.parse_args();start=time.perf_counter();cfg=next(c for c in configs() if c['case_id']==args.case);m=build(cfg);ix=m['ix'];src=m['src'];inv=load_map()
    saved_path=K/'03_SYSTEM_FINAL/RUNS'/(args.case+'_old.json');saved=json.loads(saved_path.read_text());original=saved['stages']['economic_exclusive'];v=original['vector'];free=[];expressions=[None]*ix['n']
    def variable(k,lo,hi):
        if abs(v[k]-float(lo))<1e-7:return Aff(lo)
        if abs(v[k]-float(hi))<1e-7:return Aff(hi)
        j=len(free);free.append(k);return Aff(0,{j:F(1)})
    for t in range(24):
        for j,g in enumerate(src['generators']):expressions[t*ix['G']+j]=variable(t*ix['G']+j,0,F(g['upper'][t]))
        expressions[ix['c']+t]=variable(ix['c']+t,0,50);expressions[ix['d']+t]=variable(ix['d']+t,0,50)
    previous=Aff(F(cfg['e0']));bi={b['id']:i for i,b in enumerate(src['buses'])}
    for t in range(24):
        previous=previous.add(expressions[ix['c']+t].scale(m['eta'])).add(expressions[ix['d']+t].scale(-1));expressions[ix['e']+t]=previous
        injection=[Aff(-F(b['load'][t])) for b in src['buses']]
        for j,g in enumerate(src['generators']):injection[bi[g['bus']]]=injection[bi[g['bus']]].add(expressions[t*ix['G']+j])
        injection[bi[313]]=injection[bi[313]].add(expressions[ix['d']+t]).add(expressions[ix['c']+t].scale(-1))
        angles=[Aff()]+[sumaff(injection[j+1].scale(a) for j,a in enumerate(row) if a) for row in inv]
        for j,a in enumerate(angles):expressions[ix['a']+t*ix['B']+j]=a
        for j,l in enumerate(src['lines']):expressions[ix['f']+t*ix['L']+j]=angles[bi[l['from_bus']]].add(angles[bi[l['to_bus']]].scale(-1)).scale(F(l['susceptance']))
    eqs=[];used=[];constant_bad=[]
    for row in m['rows']:
        if not row['equality']:
            numeric=sum(float(a)*v[j] for j,a in row['coeff'].items())-float(row['rhs'])
            if abs(numeric)>1e-7:continue
        ex=sumaff(expressions[j].scale(a) for j,a in row['coeff'].items()).add(Aff(-row['rhs']))
        if ex.a:eqs.append(ex);used.append(row['id'])
        elif ex.c:constant_bad.append(dict(row=row['id'],residual=str(ex.c)))
    assert not constant_bad,constant_bad[:10]
    A=sp.Matrix([[sp.Rational(ex.a.get(j,F(0)).numerator,ex.a.get(j,F(0)).denominator) for j in range(len(free))] for ex in eqs]);b=sp.Matrix([-sp.Rational(ex.c.numerator,ex.c.denominator) for ex in eqs])
    solution,parameters,indices=A.gauss_jordan_solve(b,freevar=True)
    attempts=[];accepted=None
    for den in (10**6,10**9,10**12):
        sub={p:sp.Rational(F(str(v[free[k]])).limit_denominator(den)) for p,k in zip(parameters,indices)}
        exactfree=[]
        for expr in solution:
            x=expr.subs(sub);exactfree.append(F(int(x.p),int(x.q)))
        exact=[ex.evaluate(exactfree) for ex in expressions];qa=check(m,exact,True)
        change_by_unit=dict(MW_MWh=max(abs(exact[j]-F(str(v[j]))) for j in range(ix['n']) if not ix['a']<=j<ix['c']),rad=max(abs(exact[j]-F(str(v[j]))) for j in range(ix['a'],ix['c'])))
        nearby=change_by_unit['MW_MWh']<=F(1,10**5) and change_by_unit['rad']<=F(1,10**7)
        cost=sum((exact[t*ix['G']+j]*F(g['cost']) for t in range(24) for j,g in enumerate(src['generators'])),F(0));cap=F(str(original['cost']))+max(F(1,100),abs(F(str(original['cost'])))/10**8);costpass=cost<=cap
        attempts.append(dict(denominator_limit=den,full_native_pass=qa['pass_all'],nearby_pass=nearby,original_cost_cap_pass=costpass,changes={k:str(x) for k,x in change_by_unit.items()},violations=qa['violations'][:10]))
        if qa['pass_all'] and nearby and costpass:accepted=exact;break
    result=dict(input=cfg,status='EXACT_NEARBY_FEASIBLE' if accepted is not None else 'UNKNOWN',method='exact physical network elimination and active-face rational solve',free_physical_variables=len(free),nonzero_active_equations=len(eqs),free_parameters=len(indices),active_rows=used,attempts=attempts,wall_seconds=time.perf_counter()-start,meaning='nearby exact feasible exclusive economic representation;not a certified exact optimum')
    if accepted is not None:result.update(exact_vector=list(map(str,accepted)),native_check=qa,cost=str(cost),first_action=dict(c=str(accepted[ix['c']]),d=str(accepted[ix['d']]),E1=str(accepted[ix['e']]),original_numerical_c=str(v[ix['c']]),original_numerical_d=str(v[ix['d']])))
    (OUT/(args.case+'_old_EXACT_ECONOMIC_RECOVERY.json')).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('exact_vector','active_rows')},indent=2))
if __name__=='__main__':main()
