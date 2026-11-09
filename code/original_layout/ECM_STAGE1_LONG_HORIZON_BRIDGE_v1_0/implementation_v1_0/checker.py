"""Existing reduced epigraph/finite-sign, exact SMT and full-sign reference routes."""
from common import *
from model import *
import numpy as np,scipy,z3,itertools,warnings,math
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,hstack,vstack
OPTIONS=dict(method='highs',primal_feasibility_tolerance=1e-7,dual_feasibility_tolerance=1e-7,ipm_optimality_tolerance=1e-8,presolve=True,threads=1)
DECISION_TOL=1e-8;COMPARE_TOL=1e-7;MAX_LP=262144
class BudgetTime(Exception):pass
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
def sparse_rows(rows,n):
    rr=[];cc=[];vv=[]
    for i,r in enumerate(rows):
        for k,v in r['co'].items():rr.append(i);cc.append(k);vv.append(float(v))
    return csr_matrix((vv,(rr,cc)),shape=(len(rows),n)),np.array([float(r['rhs']) for r in rows])
def run_lp(obj,A,b,E,e,bounds,deadline,counter):
    remain=deadline-time.perf_counter()
    if remain<=0:raise BudgetTime()
    opts={k:v for k,v in OPTIONS.items() if k!='method'};opts['time_limit']=max(.001,remain)
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message='Unrecognized options detected:.*')
        ans=linprog(obj,A_ub=A,b_ub=b,A_eq=E,b_eq=e,bounds=bounds,method='highs',options=opts)
    counter[0]+=1
    if ans.status==1:raise BudgetTime()
    if ans.status not in [0,2]:raise RuntimeError('LP_SOLVER_STATUS_'+str(ans.status)+':'+ans.message)
    return ans
def floating_witness(m,x):
    if x is None:return None
    T=m['T'];x=list(map(float,x[:m['n']]));out=dict(witness_type='FLOAT_WITNESS_ONLY',relaxed_vector=x,certified=False)
    for bounded in [False,True]:
        flow=[F(str(v)).limit_denominator(10**9) if bounded else F(str(v)) for v in x[:2*T]];E=[];e=m['e0']
        for t in range(T):e+=m['h']*(m['eta']*flow[t]-flow[T+t]-AUX);E.append(e)
        w=verify_witness(m,flow+E)
        if w['certified']:w['witness_type']='RATIONAL_REVERIFIED_LP';w['rational_conversion']='limit_denominator_1e9' if bounded else 'exact_decimal_strings';return w
    return out
def reduced_route(m,tr,deadline,regression=False):
    start=time.perf_counter();chosen=tr if regression else [r for r in tr if not r['auto']];planned=1+sum(2**len(r['positive']) for r in chosen);base=dict(route='R1',predicted_subproblem_count=planned,auto_preserved_rows=0 if regression else sum(r['auto'] for r in tr),margin_scope='ALL_6T_LIFTED_TARGETS' if regression else 'NON_AUTOMATIC_TARGETS_PLUS_ZERO_UPPER_BOUNDS')
    if planned>MAX_LP:return dict(base,status='BUDGET_EXCEEDED',LP_calls=0,wall_time=time.perf_counter()-start,max_value=None)
    A,b=sparse_rows(m['rows'],m['n']);E,e=sparse_rows(m['eq'],m['n']);count=[0];rowout=[];best=None;winner=None;feasible=None
    try:
        ans=run_lp(np.zeros(m['n']),A,b,E,e,[(None,None)]*m['n'],deadline,count);feasible=ans.status==0
        if not feasible:return dict(base,status='COMPLETED',LP_verdict='EMPTY',LP_calls=count[0],wall_time=time.perf_counter()-start,max_value=None,feasible=False,row_results=[])
        for z in tr:
            if z['auto'] and not regression:rowout.append(dict(row_name=z['row']['name'],mode='AUTO_PRESERVED',upper_bound=0,max_value=None));continue
            neg=z['negative'];n=m['n']+len(neg);Ap=hstack([A,csr_matrix((A.shape[0],len(neg)))]).tocsr();Ep=hstack([E,csr_matrix((E.shape[0],len(neg)))]).tocsr();ex=[]
            for j,t in enumerate(neg):
                for sign in [-1,1]:ex.append(row('epi','EPI',t,{m['T']+t:sign,t:-sign,m['n']+j:-1},0))
            if ex:extra,eb=sparse_rows(ex,n);Ap=vstack([Ap,extra]).tocsr();bp=np.r_[b,eb]
            else:bp=b
            rb=None;rx=None
            for signs in itertools.product([-1,1],repeat=len(z['positive'])):
                coef=np.array(list(map(float,z['ell'])))
                for t,sign in zip(z['positive'],signs):coef[t]+=float(z['v'][t])*sign
                obj=np.r_[coef,-coef,np.zeros(m['T']),[-float(z['v'][t]) for t in neg]]
                ans=run_lp(obj,Ap,bp,Ep,e,[(None,None)]*m['n']+[(0,None)]*len(neg),deadline,count)
                if ans.status!=0:raise AssertionError('EPIGRAPH_UNEXPECTED_INFEASIBLE')
                val=float(z['const'])-ans.fun
                if rb is None or val>rb:rb=val;rx=ans.x[:m['n']]
            rowout.append(dict(row_name=z['row']['name'],family=z['row']['family'],period=z['row']['period'],mode='REDUCED_FINITE_LP',max_value=rb,subproblems=2**len(z['positive'])))
            if best is None or rb>best:best=rb;winner=rx
        status='COMPLETED'
    except BudgetTime:status='TIMEOUT'
    witness=floating_witness(m,winner) if best is not None and best>DECISION_TOL else None
    return dict(base,status=status,LP_verdict='POSITIVE' if best is not None and best>DECISION_TOL else 'NONPOSITIVE_WITH_TOLERANCE' if status=='COMPLETED' else 'UNRESOLVED',max_value=best,global_max_value=best if status=='COMPLETED' and (regression or (best is not None and best>0)) else None,global_max_note='Floating optimum across all targets only when complete and all optimized or positive maximum dominates auto-preserved targets; otherwise NOT_COMPUTED, partial best is a lower bound',LP_calls=count[0],wall_time=time.perf_counter()-start,feasible=feasible,row_results=rowout,witness=witness)
def full_route(m,tr,deadline,regression=False):
    start=time.perf_counter();T=m['T'];A,b=sparse_rows(m['rows'],m['n']);E,e=sparse_rows(m['eq'],m['n']);count=[0];best=None;powerbest=None;winner=None;feasible=False;chosen=tr if regression else [z for z in tr if not z['auto']];planned=2**T*(1+len(chosen)+4*T)
    try:
        for signs in itertools.product([-1,1],repeat=T):
            sg=[row('sign','SIGN',t,{t:sign,T+t:-sign},0) for t,sign in enumerate(signs)];As,bs=sparse_rows(sg,m['n']);AA=vstack([A,As]).tocsr();bb=np.r_[b,bs]
            ans=run_lp(np.zeros(m['n']),AA,bb,E,e,[(None,None)]*m['n'],deadline,count)
            if ans.status==2:continue
            feasible=True;linear=[]
            for z in tr:
                co=[float(x+v*s) for x,v,s in zip(z['ell'],z['v'],signs)];vec=np.r_[-np.array(co),co,np.zeros(T)];linear.append((z,vec))
                if z['auto'] and not regression:continue
                ans=run_lp(-vec,AA,bb,E,e,[(None,None)]*m['n'],deadline,count)
                if ans.status!=0:raise AssertionError('SIGN_FEASIBLE_BUT_TARGET_INFEASIBLE')
                val=-ans.fun+float(z['const'])
                if best is None or val>best:best=val;winner=ans.x
            if True: # Existing SOC-constrained power endpoint, restricted to permitted full-sign horizons.
                soc=[(z,vec) for z,vec in linear if z['row']['family'].startswith('SOC_')];AAS=vstack([AA,csr_matrix(np.array([vec for z,vec in soc]))]).tocsr();bbs=np.r_[bb,[-float(z['const']) for z,vec in soc]]
                for z,vec in linear:
                    if z['row']['family'].startswith('SOC_'):continue
                    ans=run_lp(-vec,AAS,bbs,E,e,[(None,None)]*m['n'],deadline,count)
                    if ans.status==0:
                        val=-ans.fun+float(z['const']);powerbest=val if powerbest is None else max(powerbest,val)
        status='COMPLETED'
    except BudgetTime:status='TIMEOUT'
    return dict(route='R3',status=status,LP_calls=count[0],predicted_subproblem_count=planned,feasible=feasible,max_value=best,max_SOC_valid_power_excess=powerbest if status=='COMPLETED' else None,SOC_power_partial_lower_bound=powerbest if status!='COMPLETED' else None,SOC_max_note='Existing SOC-constrained power endpoint computed only where R3 permitted; at larger T exact existence and witness retained without a new optimizer',wall_time=time.perf_counter()-start,LP_verdict='EMPTY' if not feasible and status=='COMPLETED' else 'POSITIVE' if best is not None and best>DECISION_TOL else 'NONPOSITIVE_WITH_TOLERANCE' if status=='COMPLETED' else 'UNRESOLVED',witness=floating_witness(m,winner) if best is not None and best>DECISION_TOL else None)
def run_state(inp,partial_path):
    start=time.perf_counter();cpu=time.process_time();deadline=start+1800;routes={};errors=[];tick=time.perf_counter();m=build(inp);buildtime=time.perf_counter()-tick;tick=time.perf_counter();tr=transforms(m);transformtime=time.perf_counter()-tick
    def savepartial():atomic(partial_path,dict(input=inp,routes=routes,model_construction_time=buildtime,transform_time=transformtime,total_wall_time=time.perf_counter()-start,errors=errors),replace=True)
    routes['R2']=exact_route(m,deadline);savepartial()
    routes['R1']=reduced_route(m,tr,deadline,inp['phase']=='REGRESSION');savepartial()
    routes['R3']=full_route(m,tr,deadline,inp['phase']=='REGRESSION') if inp['T']<=8 else dict(route='R3',status='SKIPPED_BY_PREDECLARED_RULE',reason='T>8',wall_time=0.,LP_calls=0);savepartial()
    r2=routes['R2'];cert=[w for w in r2['witnesses'] if w['certified']]
    for name in ['R1','R3']:
        r=routes[name]
        if r.get('witness',{}):
            if r['witness'].get('certified'):cert.append(r['witness'])
        if r['status']=='COMPLETED':
            if r2['exact']=='EQ' and r.get('max_value') is not None and r['max_value']>DECISION_TOL:errors.append(name+'_POSITIVE_EXACT_EQ')
            if r2['exact']=='EMPTY' and r.get('feasible'):errors.append(name+'_FEASIBLE_EXACT_EMPTY')
            if r2['exact'] in ['EQ','STRICT'] and r.get('feasible') is False:errors.append(name+'_EMPTY_EXACT_NONEMPTY')
            if r2['exact']=='STRICT' and r.get('max_value') is not None and r['max_value'] < -COMPARE_TOL:errors.append(name+'_NEGATIVE_EXACT_STRICT')
    a=routes['R1'];b=routes['R3']
    if a['status']==b['status']=='COMPLETED' and a.get('max_value') is not None and b.get('max_value') is not None and abs(a['max_value']-b['max_value'])>COMPARE_TOL:errors.append('R1_R3_MAXIMUM_DISAGREEMENT')
    if cert and r2['exact'] in ['EQ','EMPTY']:errors.append('RATIONAL_WITNESS_CONTRADICTS_EXACT_'+r2['exact'])
    exact='STRICT' if cert else r2['exact']
    if exact=='STRICT' and F(inp['eta_c'])==1:errors.append('LOSSLESS_CONTROL_ALERT')
    status=exact if exact in ['EQ','STRICT','EMPTY'] else 'TIMEOUT' if any(r['status']=='TIMEOUT' for r in routes.values()) else 'UNKNOWN'
    return dict(input=inp,classification=status,certificate_level=exact+'_CERTIFIED' if exact in ['EQ','STRICT','EMPTY'] else 'NONE',routes=routes,witnesses=cert,model_construction_time=buildtime,transform_time=transformtime,total_wall_time=time.perf_counter()-start,cpu_time=time.process_time()-cpu,peak_memory=peak_memory(),errors=errors,process_status='PASS' if not errors else 'GLOBAL_SEMANTIC_QA_FAILURE')
if __name__=='__main__':
    import argparse,traceback
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);args=ap.parse_args();out=Path(args.output)
    try:
        verify_freeze();inp=read(args.input);result=run_state(inp,out.with_suffix('.partial.json'));atomic(out,result)
    except Exception as e:
        atomic(out,dict(classification='ERROR',process_status='ERROR',error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc()))
        raise
