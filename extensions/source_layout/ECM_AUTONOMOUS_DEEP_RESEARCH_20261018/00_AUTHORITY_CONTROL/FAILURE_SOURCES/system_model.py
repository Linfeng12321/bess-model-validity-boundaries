"""Sparse continuous RTS dispatch and exact feasibility, no old witness imports."""
from pathlib import Path
from fractions import Fraction as F
import json,time,sys
import numpy as np
from scipy.sparse import coo_matrix
from scipy.optimize import linprog,milp,Bounds,LinearConstraint
import z3
U=Path(__file__).resolve().parent
sys.path.insert(0,str(U/'_deps'))
def cvc5_decide(query,timeout_ms,count):
    import cvc5
    solver=cvc5.Solver();solver.setOption('produce-models','true');solver.setOption('tlimit-per',str(timeout_ms))
    if '(set-logic ' not in query:query='(set-logic QF_LRA)\n'+query
    parser=cvc5.InputParser(solver);parser.setStringInput(cvc5.InputLanguage.SMT_LIB_2_6,query,'fixed_RTS_query');answer=None
    while True:
        cmd=parser.nextCommand()
        if cmd.isNull():break
        if cmd.getCommandName()=='check-sat':answer=solver.checkSat()
        else:cmd.invoke(solver,parser.getSymbolManager())
    assert answer is not None
    out=dict(status=str(answer),solver='cvc5 '+cvc5.__version__)
    if answer.isSat():
        values={str(t):str(F(solver.getValue(t).getRealValue())) for t in parser.getSymbolManager().getDeclaredTerms() if str(t).startswith('x') and str(t)[1:].isdigit()}
        out['vector']=[values[f'x{i}'] for i in range(count)]
    elif answer.isUnknown():out['reason']=str(answer.getUnknownExplanation())
    return out
def read_input():return json.loads((U/'02_PROTOCOL/NORMALIZED_RTS_INPUT.json').read_text())
def structure(cfg,exclusive=False):
    data=read_input();T=data['T'];G=len(data['generators']);B=len(data['buses']) if cfg['network'] else 0;L=len(data['lines']) if cfg['network'] else 0
    go=0;fo=T*G;ao=fo+T*L;co=ao+T*B;do=co+T;eo=do+T;bo=eo+T;n=bo+(T if exclusive else 0)
    ix=dict(g=go,f=fo,a=ao,c=co,d=do,e=eo,mode=bo,G=G,B=B,L=L,T=T,n=n)
    rows=[];eq=[];names=[];enames=[];rhs=[];erhs=[];bounds=[(None,None)]*n
    def add(r,b,name):rows.append({i:F(a) for i,a in r.items() if a});rhs.append(F(b));names.append(name)
    def equal(r,b,name):eq.append({i:F(a) for i,a in r.items() if a});erhs.append(F(b));enames.append(name)
    cost=[F(0)]*n;service=[F(0)]*n;P=F(50);UC=F(150);eta=F('17/20') if cfg['loss'] else F(1)
    bus_index={b['id']:k for k,b in enumerate(data['buses'])}
    genbus={b['id']:[j for j,g in enumerate(data['generators']) if g['bus']==b['id']] for b in data['buses']}
    for t in range(T):
        for j,g in enumerate(data['generators']):
            gi=t*G+j;bounds[gi]=(F(0),F(g['upper'][t]));cost[gi]=F(g['cost'])
            if t and F(g['ramp'])<max(map(F,g['upper'])):
                add({gi:1,gi-G:-1},F(g['ramp']),f'ramp_up_{t}_{j}');add({gi:-1,gi-G:1},F(g['ramp']),f'ramp_dn_{t}_{j}')
        if cfg['network']:
            for k,l in enumerate(data['lines']):
                fi=fo+t*L+k;bounds[fi]=(-F(l['limit']),F(l['limit']))
                equal({fi:1,ao+t*B+bus_index[l['from_bus']]:-F(l['susceptance']),ao+t*B+bus_index[l['to_bus']]:F(l['susceptance'])},0,f'dc_{t}_{k}')
            equal({ao+t*B:1},0,f'reference_{t}')
            for bi,b in enumerate(data['buses']):
                rr={t*G+j:F(1) for j in genbus[b['id']]}
                if b['id']==313:rr[do+t]=1;rr[co+t]=-1
                for k,l in enumerate(data['lines']):
                    if l['from_bus']==b['id']:rr[fo+t*L+k]=-1
                    if l['to_bus']==b['id']:rr[fo+t*L+k]=1
                equal(rr,F(b['load'][t]),f'balance_{t}_{b["id"]}')
        else:equal({**{t*G+j:1 for j in range(G)},do+t:1,co+t:-1},sum((F(b['load'][t]) for b in data['buses']),F(0)),f'copperplate_{t}')
        bounds[co+t]=(F(0),P);bounds[do+t]=(F(0),P);bounds[eo+t]=(F(0),UC)
        rr={eo+t:1,co+t:-eta,do+t:1}
        if t:rr[eo+t-1]=-1
        equal(rr,F(cfg['e0']) if not t else F(0),f'energy_{t}')
        add({co+t:1,do+t:1},P,f'shared_{t}')
        if cfg['taper']:add({co+t:1,eo+t:F(1,3)},P,f'taper_{t}')
        if exclusive:
            bounds[bo+t]=(F(0),F(1));add({co+t:1,bo+t:-P},0,f'charge_mode_{t}');add({do+t:1,bo+t:P},P,f'discharge_mode_{t}')
        if t in data['service_hours_zero_based']:service[co+t]=1;service[do+t]=-1
    return dict(n=n,ix=ix,rows=rows,rhs=rhs,eq=eq,erhs=erhs,names=names,enames=enames,bounds=bounds,cost=cost,service=service,cfg=cfg,eta=eta)
def sparse(rows,n):
    rr=[];cc=[];vv=[]
    for i,row in enumerate(rows):
        for j,a in row.items():rr.append(i);cc.append(j);vv.append(float(a))
    return coo_matrix((vv,(rr,cc)),shape=(len(rows),n)).tocsr()
def numerical(cfg,exclusive=False,objective='cost',budget=None,fixed_service=None):
    m=structure(cfg,exclusive);A=m['rows'][:];b=m['rhs'][:];E=m['eq'][:];f=m['erhs'][:]
    if budget is not None:A.append({j:a for j,a in enumerate(m['cost']) if a});b.append(F(budget))
    if fixed_service is not None:
        rr={j:a for j,a in enumerate(m['service']) if a};A.extend([rr,{j:-a for j,a in rr.items()}]);b.extend([F(str(fixed_service))+F(1,10**6),-F(str(fixed_service))+F(1,10**6)])
    lo=[-np.inf if x is None else float(x) for x,y in m['bounds']];hi=[np.inf if y is None else float(y) for x,y in m['bounds']]
    a=sparse(A,m['n']);ee=sparse(E,m['n']);start=time.perf_counter();obj=np.array(list(map(float,m[objective])))
    if exclusive:
        integ=np.zeros(m['n']);integ[m['ix']['mode']:]=1
        r=milp(obj,integrality=integ,bounds=Bounds(lo,hi),constraints=[LinearConstraint(a,-np.inf,np.array(list(map(float,b)))),LinearConstraint(ee,np.array(list(map(float,f))),np.array(list(map(float,f))))],options={'time_limit':30,'mip_rel_gap':0})
    else:r=linprog(obj,A_ub=a,b_ub=np.array(list(map(float,b))),A_eq=ee,b_eq=np.array(list(map(float,f))),bounds=list(zip(lo,hi)),method='highs',options={'time_limit':30})
    vector=r.x[:m['ix']['mode']].tolist() if r.x is not None else None
    result=dict(success=bool(r.success),status=int(r.status),message=r.message,objective=float(r.fun) if r.fun is not None else None,vector=vector,
                wall_seconds=time.perf_counter()-start,objective_kind=objective,exclusive=exclusive,variables=m['n'],inequalities=len(A),equalities=len(E))
    if vector is not None:
        result['cost']=sum(float(a)*v for a,v in zip(m['cost'],vector));result['service_objective']=sum(float(a)*v for a,v in zip(m['service'],vector))
    if hasattr(r,'mip_gap'):result['mip_gap']=float(r.mip_gap)
    return result
def exact_constraints(m):
    x=z3.Reals(' '.join(f'x{i}' for i in range(m['ix']['mode'])));Q=lambda a:z3.RealVal(str(a));cons=[]
    for j,(lo,hi) in enumerate(m['bounds'][:len(x)]):
        if lo is not None:cons.append(x[j]>=Q(lo))
        if hi is not None:cons.append(x[j]<=Q(hi))
    def val(rr):
        terms=[Q(a)*x[j] for j,a in rr.items()]
        return terms[0] if len(terms)==1 else z3.Sum(terms)
    for row,b,name in zip(m['rows'],m['rhs'],m['names']):
        if 'mode_' not in name:cons.append(val(row)<=Q(b))
    for row,b in zip(m['eq'],m['erhs']):cons.append(val(row)==Q(b))
    if m['n']>len(x):
        for t in range(24):cons.append(z3.Or(x[m['ix']['c']+t]==0,x[m['ix']['d']+t]==0))
    cost=z3.Sum([Q(a)*x[j] for j,a in enumerate(m['cost'][:len(x)]) if a]);service=z3.Sum([Q(a)*x[j] for j,a in enumerate(m['service'][:len(x)]) if a])
    return x,cons,cost,service
def rational_repair(cfg,result,budget=None,fixed_service=None):
    if not result['success']:return dict(status='SKIPPED_NUMERICAL_FAILURE')
    start=time.perf_counter();m=structure(cfg,result['exclusive']);ix=m['ix'];x,cons,cost,service=exact_constraints(m);s=z3.SolverFor('QF_LRA');s.set(timeout=15000);s.add(cons)
    v=result['vector'];Q=lambda a:z3.RealVal(str(a))
    for j,value in enumerate(v):
        lo,hi=m['bounds'][j];delta=F(1,10**7) if ix['a']<=j<ix['c'] else F(1,10**5)
        if ix['c']<=j<ix['e'] and abs(value)<1e-7:s.add(x[j]==0)
        elif lo is not None and abs(value-float(lo))<1e-7:s.add(x[j]==Q(lo))
        elif hi is not None and abs(value-float(hi))<1e-7:s.add(x[j]==Q(hi))
        else:s.add(x[j]>=Q(F(str(value))-delta),x[j]<=Q(F(str(value))+delta))
    if result['exclusive']:
        for t in range(24):
            if v[ix['c']+t]<=v[ix['d']+t]:s.add(x[ix['c']+t]==0)
            else:s.add(x[ix['d']+t]==0)
    cap=max(F(1,100),abs(F(str(result['cost'])))/10**8);s.add(cost<=Q(F(str(result['cost']))+cap))
    if budget is not None:s.add(cost<=Q(F(budget)),service<=Q(F(str(result['service_objective']))+F(1,10**6)))
    if fixed_service is not None:s.add(service>=Q(F(str(fixed_service))-F(1,10**6)),service<=Q(F(str(fixed_service))+F(1,10**6)))
    decision=cvc5_decide(s.to_smt2(),15000,len(x));ans=decision['status'];out=dict(status=ans,solver=decision['solver'],wall_seconds=time.perf_counter()-start,timeout_seconds=15,meaning='Nearby exact-feasible representation; not an exact optimality certificate')
    if ans=='sat':
        vv=list(map(F,decision['vector']));out['vector']=list(map(str,vv));out['maximum_variable_change']=max(abs(float(a)-b) for a,b in zip(vv,v))
        out['cost']=str(sum((a*b for a,b in zip(m['cost'],vv)),F(0)));out['service_objective']=str(sum((a*b for a,b in zip(m['service'],vv)),F(0)))
    else:out['reason']=decision.get('reason','No exact feasible vector within preregistered neighborhood')
    return out
def reconstruct(cfg,vector):
    m=structure(cfg);ix=m['ix'];v=list(map(F,vector));p=[v[ix['d']+t]-v[ix['c']+t] for t in range(24)];c=[max(-a,F(0)) for a in p];d=[max(a,F(0)) for a in p];ee=[];old=F(cfg['e0'])
    for cc,dd in zip(c,d):old+=m['eta']*cc-dd;ee.append(old)
    return list(map(str,v[:ix['c']]+c+d+ee))
def global_query(cfg):
    start=time.perf_counter();m=structure(cfg);ix=m['ix'];x,cons,_,_=exact_constraints(m);s=z3.SolverFor('QF_LRA');s.set(timeout=20000);s.add(cons);states=z3.Reals(' '.join(f'liftE{t}' for t in range(24)));bad=[]
    for t in range(24):
        pp=x[ix['d']+t]-x[ix['c']+t];cc=z3.If(pp<0,-pp,0);dd=z3.If(pp>0,pp,0)
        s.add(states[t]==(states[t-1] if t else z3.RealVal(cfg['e0']))+z3.RealVal(str(m['eta']))*cc-dd)
        bad += [cc<0,dd<0,cc+dd>50,states[t]<0,states[t]>150]
        if cfg['taper']:bad.append(cc+states[t]/3>50)
    s.add(z3.Or(bad));query=s.to_smt2();decision=cvc5_decide(query,20000,len(x));ans=decision['status'];out=dict(status=ans,solver=decision['solver'],encoding_smt2=query,wall_seconds=time.perf_counter()-start,timeout_seconds=20)
    if ans=='sat':out['vector']=decision['vector']
    else:out['reason']=decision.get('reason','')
    return out
