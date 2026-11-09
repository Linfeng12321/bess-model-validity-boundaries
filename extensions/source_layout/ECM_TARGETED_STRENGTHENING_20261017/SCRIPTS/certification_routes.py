"""Candidate exact certificate routes. Numerical outputs alone never decide EQ."""
from pathlib import Path
from fractions import Fraction as F
import time,itertools,json,hashlib
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
import z3
import frozen_internal_model as frozen
from independent_native import linear_rows,target_expression,check,verify_strict,check_upper_certificate

def stationary(inp):
    eta=F(inp['eta_c']);T=int(inp['T']);c=(F(1,2)+F(7,1000))/(eta+1);d=eta*c-F(7,1000);v=[c]*T+[d]*T+[F(inp['effective_initial_energy'])]*T
    q=verify_strict(inp,v)
    return dict(method='M3_STATIONARY_EXACT_CANDIDATE',input=inp,new_status='STRICT',relaxed_vector=list(map(str,v)),independent_verification=q) if q['certified'] else None

def sparse(rows,n):
    rr=[];cc=[];vv=[]
    for i,r in enumerate(rows):
        for j,a in r.items():rr.append(i);cc.append(j);vv.append(float(a))
    return csr_matrix((vv,(rr,cc)),shape=(len(rows),n))

def exact_feasible(inp,m,co=None,const=F(0),timeout_s=30):
    n=m['n'];x=z3.Reals(' '.join('v'+str(i) for i in range(n)));s=z3.SolverFor('QF_LRA');s.set(timeout=max(1,int(timeout_s*1000)),random_seed=0)
    qr=lambda a:z3.RealVal(str(a))
    for row,rhs in zip(m['A'],m['b']):s.add(z3.Sum([qr(v)*x[k] for k,v in row.items()])<=qr(rhs))
    for row,rhs in zip(m['E'],m['f']):s.add(z3.Sum([qr(v)*x[k] for k,v in row.items()])==qr(rhs))
    for j,(lo,hi) in enumerate(m['bounds']):s.add(x[j]>=qr(lo),x[j]<=qr(hi))
    if co is not None:s.add(qr(const)+z3.Sum([qr(a)*x[j] for j,a in enumerate(co) if a])>0)
    status=s.check();out=dict(status=str(status),reason=s.reason_unknown() if status==z3.unknown else '')
    if status==z3.sat:
        model=s.model();v=[F(str(model.eval(q,model_completion=True))) for q in x];out['vector']=list(map(str,v));out['native_verification']=check(inp,v[:3*int(inp['T'])])
    return out

def certify(inp,budget_s=300,include_stationary=True):
    start=time.perf_counter();deadline=start+budget_s;T=int(inp['T'])
    if include_stationary:
        proof=stationary(inp)
        if proof:return dict(status='STRICT',method='M3',proof=proof,LP_calls=0,wall_seconds=time.perf_counter()-start)
    prep=time.perf_counter();m=linear_rows(inp,True);fm=frozen.build(inp)
    assert [r['co'] for r in fm['rows']]==m['A'][:9*T] and [r['rhs'] for r in fm['rows']]==m['b'][:9*T]
    assert [r['co'] for r in fm['eq']]==m['E'] and [r['rhs'] for r in fm['eq']]==m['f']
    # Exact constant-energy exclusive trajectory establishes nonemptiness independently.
    feasible=[F(7,1000)/F(inp['eta_c'])]*T+[F(0)]*T+[F(inp['effective_initial_energy'])]*T
    feasible_check=check(inp,feasible,True)
    if not feasible_check['pass_all']:
        f=exact_feasible(inp,m,timeout_s=min(30,max(.001,deadline-time.perf_counter())))
        if f['status']!='sat' or not f['native_verification']['pass_all']:return dict(status='UNRESOLVED',method='M2',reason='nonemptiness_certificate_missing',wall_seconds=time.perf_counter()-start)
        feasible=list(map(F,f['vector'][:3*T]))
    A=sparse(m['A'],m['n']);E=sparse(m['E'],m['n']);bb=np.array(list(map(float,m['b'])));ff=np.array(list(map(float,m['f'])));bounds=[tuple(map(float,b)) for b in m['bounds']]
    setup_s=time.perf_counter()-prep;certificates=[];automatic=[];calls=0;logs=[]
    transforms=frozen.transforms(fm)
    for tr in transforms:
        idx=m['names'].index(tr['row']['name']);const,co0=target_expression(inp,idx)
        assert const==tr['const'] and co0[3*T:]==tr['v'] and co0[:T]==[-e for e in tr['ell']] and co0[T:2*T]==tr['ell']
        if all(v>=0 for v in co0[3*T:]):automatic.append(idx);continue
        pos=[j for j,v in enumerate(co0[3*T:]) if v>0]
        if len(pos)>10:return dict(status='UNRESOLVED',method='M2',reason='prespecified_sign_cap',wall_seconds=time.perf_counter()-start)
        for signs in itertools.product([-1,1],repeat=len(pos)):
            if time.perf_counter()>=deadline:return dict(status='UNRESOLVED',method='M2',reason='state_budget',LP_calls=calls,wall_seconds=time.perf_counter()-start)
            signs=dict(zip(pos,signs));const,co=target_expression(inp,idx,signs);begin=time.perf_counter()
            result=linprog(-np.array(list(map(float,co))),A_ub=A,b_ub=bb,A_eq=E,b_eq=ff,bounds=bounds,method='highs',options={'time_limit':max(.001,deadline-time.perf_counter()),'primal_feasibility_tolerance':1e-7,'dual_feasibility_tolerance':1e-7})
            calls+=1;entry=dict(native_row_index=idx,native_row_name=m['names'][idx],positive_signs=signs,numerical_status=result.status,LP_seconds=time.perf_counter()-begin)
            if not result.success:return dict(status='UNRESOLVED',method='M2',reason='LP_NOT_OPTIMAL',LP_calls=calls,log=entry,wall_seconds=time.perf_counter()-start)
            lm={i:max(F(0),F(float(-v)).limit_denominator(10**9)) for i,v in enumerate(result.ineqlin.marginals) if v!=0};mu={i:F(float(-v)).limit_denominator(10**9) for i,v in enumerate(result.eqlin.marginals) if v!=0}
            residual=co[:];bound=const
            for i,v in lm.items():
                bound+=v*m['b'][i]
                for j,a in m['A'][i].items():residual[j]-=v*a
            for i,v in mu.items():
                bound+=v*m['f'][i]
                for j,a in m['E'][i].items():residual[j]-=v*a
            correction=sum((v*(m['bounds'][j][1] if v>=0 else m['bounds'][j][0]) for j,v in enumerate(residual)),F(0));upper=bound+correction
            entry.update(lambda_={str(i):str(v) for i,v in lm.items()},mu={str(i):str(v) for i,v in mu.items()},exact_upper_bound=str(upper),residual_correction=str(correction),floating_residual_max=float(-result.fun+float(const)))
            entry['lambda']=entry.pop('lambda_')
            if upper<=0:
                check_upper_certificate(inp,entry);certificates.append(entry);continue
            if -result.fun+float(const)>1e-8:
                exact=exact_feasible(inp,m,co,const,timeout_s=min(30,max(.001,deadline-time.perf_counter())))
                if exact['status']=='sat':
                    v=exact['vector'][:3*T];ind=verify_strict(inp,v)
                    if ind['certified']:return dict(status='STRICT',method='M3',proof=dict(method='M3_LINEAR_EXACT_REPAIR',input=inp,relaxed_vector=v,independent_verification=ind,selected_row=m['names'][idx],positive_signs=signs),LP_calls=calls,preprocessing_seconds=setup_s,wall_seconds=time.perf_counter()-start)
                logs.append(dict(row=m['names'][idx],exact_linear_query=exact['status'],reason=exact.get('reason','')))
            return dict(status='UNRESOLVED',method='M2',reason='EXACT_UPPER_POSITIVE_OR_REPAIR_FAILED',LP_calls=calls,failed_certificate=entry,logs=logs,wall_seconds=time.perf_counter()-start)
    proof=dict(method='M2_EXACT_ROW_UPPER_BOUNDS',input=inp,nonempty_vector=list(map(str,feasible)),automatic_native_rows=automatic,row_upper_certificates=certificates,full_target_rows=[m['names'].index(t['row']['name']) for t in transforms],LP_calls=calls,argument='Every positive-absolute coefficient is enumerated by its finite linear maximum; every negative coefficient uses a bounded epigraph. Exact nonnegative multipliers and box-bounded stationarity residuals prove each upper bound. Other rows follow from nonnegative reconstructed flows, decreasing shared power and deterministic dynamics.')
    return dict(status='EQ',method='M2',proof=proof,LP_calls=calls,preprocessing_seconds=setup_s,wall_seconds=time.perf_counter()-start)

def verify_eq(proof):
    i=proof['input'];assert check(i,proof['nonempty_vector'])['pass_all'];m=linear_rows(i,True);T=int(i['T'])
    expected=[k for k,n in enumerate(m['names'][:9*T]) if n.startswith(('E_','CHARGE_','DISCHARGE_'))];assert proof['full_target_rows']==expected
    automatic=set(proof['automatic_native_rows']);seen={}
    for idx in automatic:
        _,co=target_expression(i,idx);assert all(v>=0 for v in co[3*T:])
    for item in proof['row_upper_certificates']:
        idx=item['native_row_index'];assert idx in expected and idx not in automatic
        _,co=target_expression(i,idx);pos=[k for k,v in enumerate(co[3*T:]) if v>0];signs={int(k):v for k,v in item['positive_signs'].items()};assert set(signs)==set(pos)
        check_upper_certificate(i,item);seen.setdefault(idx,set()).add(tuple(signs[k] for k in pos))
    for idx in set(expected)-automatic:
        _,co=target_expression(i,idx);pos=[k for k,v in enumerate(co[3*T:]) if v>0];assert seen[idx]==set(itertools.product([-1,1],repeat=len(pos)))
    return True
