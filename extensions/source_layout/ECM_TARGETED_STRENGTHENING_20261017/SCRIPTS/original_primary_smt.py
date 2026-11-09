from frozen_internal_model import *
from fractions import Fraction as F
import time,z3

def zr(x):return z3.RealVal(str(x))

def exact_route(m,deadline):
    start=time.perf_counter();end=min(deadline,start+300);T=m['T'];xs=z3.Reals(' '.join('x'+str(i) for i in range(m['n'])));ss=z3.Reals(' '.join('s'+str(i) for i in range(T)))
    def expr(r,xx):return z3.Sum([zr(a)*xx[i] for i,a in r['co'].items()])-zr(r['rhs'])
    cc=[z3.If(xs[t]>=xs[T+t],xs[t]-xs[T+t],zr(0)) for t in range(T)];dd=[z3.If(xs[T+t]>=xs[t],xs[T+t]-xs[t],zr(0)) for t in range(T)];yy=cc+dd+list(ss)
    cons=[expr(r,xs)<=0 for r in m['rows']]+[expr(r,xs)==0 for r in m['eq']]
    cons += [ss[t]==(ss[t-1] if t else zr(m['e0']))+zr(m['h'])*(zr(m['eta'])*cc[t]-dd[t]-zr(AUX)) for t in range(T)]
    s=z3.Solver();s.set(random_seed=0,max_memory=768);s.add(cons);q={};witnesses=[];wt=0.
    def query(key,extra):
        nonlocal wt
        remain=end-time.perf_counter()
        if remain<=0:q[key]=dict(status='unknown',reason='state SMT budget exhausted',time=0.,timeout=True);return 'unknown'
        s.push();s.add(extra);s.set(timeout=max(1,int(remain*1000)));st=time.perf_counter();ans=s.check();elapsed=time.perf_counter()-st;reason=s.reason_unknown() if ans==z3.unknown else '';q[key]=dict(status=str(ans),reason=reason,time=elapsed,timeout=ans==z3.unknown and ('timeout' in reason or 'canceled' in reason))
        if ans==z3.sat and key!='feasible_smt':
            tick=time.perf_counter();vals=[str(s.model().eval(x,model_completion=True)) for x in xs];w=verify_witness(m,vals);w['query']=key;w['witness_type']='EXACT_RATIONAL'
            if not w['certified']:raise AssertionError('EXACT_WITNESS_RECHECK_FAILED')
            if key=='SOC_pass_power_fail_smt' and not w['SOC_pass']:raise AssertionError('SOC_CONSTRAINED_WITNESS_FAILED')
            witnesses.append(w);wt+=time.perf_counter()-tick
        s.pop();return str(ans)
    fa=query('feasible_smt',z3.BoolVal(True))
    if fa=='unsat':ba=pa='unsat';q['bad_smt']=dict(status=ba,reason='IMPLIED_BY_EMPTY',time=0.,timeout=False);q['SOC_pass_power_fail_smt']=dict(status=pa,reason='IMPLIED_BY_EMPTY',time=0.,timeout=False)
    else:
        ba=query('bad_smt',z3.Or([expr(r,yy)>0 for r in m['targets']]))
        pa=query('SOC_pass_power_fail_smt',z3.And(*[expr(r,yy)<=0 for r in m['targets'] if r['family'].startswith('SOC_')],z3.Or([expr(r,yy)>0 for r in m['targets'] if not r['family'].startswith('SOC_')])))
    exact='EMPTY' if fa=='unsat' else 'STRICT' if ba=='sat' or pa=='sat' else 'EQ' if fa=='sat' and ba=='unsat' else 'UNKNOWN'
    return dict(route='R2',status='TIMEOUT' if exact=='UNKNOWN' and any(x['timeout'] for x in q.values()) else 'UNKNOWN' if exact=='UNKNOWN' else 'COMPLETED',exact=exact,queries=q,witnesses=witnesses,witness_verification_time=wt,wall_time=time.perf_counter()-start,LP_calls=0,solver_version=z3.get_version_string())
