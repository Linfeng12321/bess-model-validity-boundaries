"""Public three-bus DC dispatch, with an explicitly study-specified battery."""
from pathlib import Path
from fractions import Fraction as F
import json,time
import numpy as np
from scipy.optimize import linprog,milp,Bounds,LinearConstraint
import z3
def structure(cfg,exclusive=False):
    T=cfg['T'];n=12*T+(T if exclusive else 0);rows=[];eq=[];rhs=[];erhs=[];names=[];enames=[]
    def g(t,b):return 3*t+b
    def flow(t,l):return 3*T+3*t+l
    def angle(t,b):return 6*T+3*t+b
    def c(t):return 9*T+t
    def d(t):return 10*T+t
    def e(t):return 11*T+t
    def add(co,b,name):rows.append(co);rhs.append(F(b));names.append(name)
    def equal(co,b,name):eq.append(co);erhs.append(F(b));enames.append(name)
    bounds=[(F(0),F(100))]*(3*T)+[(-F(s),F(s)) for _ in range(T) for s in [100,100,10]]+[(F(-1000),F(1000))]*(3*T)+[(F(0),F(1))]*(2*T)+[(F(0),F(6))]*T
    if exclusive:bounds +=[(F(0),F(1))]*T
    costs=[F(0)]*n;service=[F(0)]*n
    for t in range(T):
        costs[g(t,0)]=10;costs[g(t,1)]=20;costs[g(t,2)]=100
        equal({flow(t,0):1,angle(t,0):-1,angle(t,1):1},0,f'flow12_{t}')
        equal({flow(t,1):1,angle(t,1):-1,angle(t,2):1},0,f'flow23_{t}')
        equal({flow(t,2):1,angle(t,0):-1,angle(t,2):1},0,f'flow13_{t}')
        equal({angle(t,2):1},0,f'reference_angle_{t}')
        equal({g(t,0):1,flow(t,0):-1,flow(t,2):-1,d(t):1,c(t):-1},0,f'balance1_{t}')
        equal({g(t,1):1,flow(t,0):1,flow(t,1):-1},0,f'balance2_{t}')
        equal({g(t,2):1,flow(t,1):1,flow(t,2):1},F(cfg['load'][t]),f'balance3_{t}')
        co={e(t):1,c(t):-F(cfg['eta_c']),d(t):1/F(cfg['eta_d'])};b=F(0)
        if t:co[e(t-1)]=-F(cfg['rho'])
        else:b=F(cfg['rho'])*F(cfg['e0'])
        equal(co,b,f'energy_{t}')
        add({c(t):1,d(t):1},1,f'shared_rating_{t}')
        if cfg['device']=='TAPER':add({c(t):1,d(t):-1,e(t):F(1,6)},1,f'end_taper_{t}')
        if exclusive:
            mode=12*T+t;add({c(t):1,mode:-1},0,f'charge_mode_{t}');add({d(t):1,mode:1},1,f'discharge_mode_{t}')
        if not cfg.get('battery_enabled',True):equal({c(t):1},0,f'no_battery_charge_{t}');equal({d(t):1},0,f'no_battery_discharge_{t}')
        if t>=T-2:service[c(t)]=-1;service[d(t)]=1
    return dict(n=n,T=T,A=rows,b=rhs,E=eq,f=erhs,names=names,enames=enames,bounds=bounds,cost=costs,service=service)
def dense(rows,n):
    a=np.zeros((len(rows),n))
    for i,row in enumerate(rows):
        for j,v in row.items():a[i,j]=float(v)
    return a
def numerical(cfg,exclusive=False,objective='cost',budget=None,fixed_service=None):
    m=structure(cfg,exclusive);A=list(m['A']);b=list(m['b']);E=list(m['E']);f=list(m['f'])
    if budget is not None:A.append({j:a for j,a in enumerate(m['cost']) if a});b.append(F(budget))
    if fixed_service is not None:E.append({j:a for j,a in enumerate(m['service']) if a});f.append(F(fixed_service))
    cost=np.array(list(map(float,m[objective])));lo,hi=np.array([[float(a),float(b)] for a,b in m['bounds']]).T;start=time.perf_counter()
    if exclusive:
        constraints=[LinearConstraint(dense(A,m['n']),-np.inf,np.array(list(map(float,b)))),LinearConstraint(dense(E,m['n']),np.array(list(map(float,f))),np.array(list(map(float,f))))]
        integrality=np.r_[np.zeros(12*m['T']),np.ones(m['T'])];r=milp(cost,integrality=integrality,bounds=Bounds(lo,hi),constraints=constraints,options={'time_limit':60,'mip_rel_gap':0.0})
    else:r=linprog(cost,A_ub=dense(A,m['n']),b_ub=np.array(list(map(float,b))),A_eq=dense(E,m['n']),b_eq=np.array(list(map(float,f))),bounds=list(zip(lo,hi)),method='highs',options={'time_limit':60})
    return dict(status=int(r.status),success=bool(r.success),message=r.message,objective=float(r.fun) if r.fun is not None else None,vector=r.x.tolist() if r.x is not None else None,wall_seconds=time.perf_counter()-start,objective_kind=objective)

def exact_constraints(cfg,exclusive=False):
    """Independent Z3 construction: physical equations, not numerical matrix translation."""
    T=cfg['T'];g=[[z3.Real(f'g_{t}_{b}') for b in range(3)] for t in range(T)];f=[[z3.Real(f'f_{t}_{l}') for l in range(3)] for t in range(T)];a=[[z3.Real(f'a_{t}_{b}') for b in range(3)] for t in range(T)];c=z3.Reals(' '.join(f'c_{t}' for t in range(T)));d=z3.Reals(' '.join(f'd_{t}' for t in range(T)));e=z3.Reals(' '.join(f'e_{t}' for t in range(T)));cons=[];q=lambda v:z3.RealVal(str(v))
    for t in range(T):
        cons += [v>=0 for v in g[t]]+[v<=100 for v in g[t]]
        for l,rating in enumerate([100,100,10]):cons +=[f[t][l]>=-rating,f[t][l]<=rating]
        cons +=[f[t][0]==a[t][0]-a[t][1],f[t][1]==a[t][1]-a[t][2],f[t][2]==a[t][0]-a[t][2],a[t][2]==0]
        cons +=[g[t][0]+d[t]-c[t]==f[t][0]+f[t][2],g[t][1]+f[t][0]==f[t][1],g[t][2]+f[t][1]+f[t][2]==q(cfg['load'][t])]
        cons +=[c[t]>=0,d[t]>=0,c[t]+d[t]<=1,e[t]>=0,e[t]<=6,e[t]==q(cfg['rho'])*(e[t-1] if t else q(cfg['e0']))+q(cfg['eta_c'])*c[t]-d[t]/q(cfg['eta_d'])]
        if cfg['device']=='TAPER':cons.append(c[t]-d[t]+e[t]/6<=1)
        if exclusive:cons.append(z3.Or(c[t]==0,d[t]==0))
        if not cfg.get('battery_enabled',True):cons +=[c[t]==0,d[t]==0]
    cost=z3.Sum([10*g[t][0]+20*g[t][1]+100*g[t][2] for t in range(T)]);service=z3.Sum([d[t]-c[t] for t in range(max(0,T-2),T)])
    vector=[v for x in g for v in x]+[v for x in f for v in x]+[v for x in a for v in x]+list(c)+list(d)+list(e)
    return cons,vector,c,d,e,cost,service
def rational(v):
    v=z3.simplify(v)
    assert z3.is_rational_value(v),str(v)
    return F(v.numerator_as_long(),v.denominator_as_long())
def exact_optimum(cfg,exclusive=False,service_budget=None,timeout_s=60):
    cons,vec,c,d,e,cost,service=exact_constraints(cfg,exclusive);o=z3.Optimize();o.set(timeout=int(timeout_s*1000));o.add(cons)
    if service_budget is not None:o.add(cost<=z3.RealVal(str(service_budget)));h1=o.minimize(service);h2=o.minimize(cost)
    else:h1=o.minimize(cost);h2=None
    start=time.perf_counter();s=o.check();out=dict(status=str(s),wall_seconds=time.perf_counter()-start,exclusive=exclusive)
    if s!=z3.sat:return out
    model=o.model();v=[rational(model.eval(x,model_completion=True)) for x in vec];value=rational(model.eval(cost));sv=rational(model.eval(service));out.update(vector=list(map(str,v)),cost=str(value),service_objective=str(sv),lower_bound=str(h1.lower()),upper_bound=str(h1.upper()))
    # Fresh decision solver certifies the primary bound exactly; optimum equality is not rounded.
    bound=z3.Solver();bound.set(timeout=int(timeout_s*1000),random_seed=0);bound.add(cons)
    if service_budget is not None:bound.add(cost<=z3.RealVal(str(service_budget)),service<z3.RealVal(str(sv)))
    else:bound.add(cost<z3.RealVal(str(value)))
    result=bound.check();out['exact_better_primary_query']=str(result);out['primary_optimum_certified']=result==z3.unsat
    out['bound_query_smt2']=bound.to_smt2()
    if service_budget is not None:
        secondary=z3.Solver();secondary.set(timeout=int(timeout_s*1000),random_seed=0);secondary.add(cons);secondary.add(cost<=z3.RealVal(str(service_budget)),service==z3.RealVal(str(sv)),cost<z3.RealVal(str(value)))
        status=secondary.check();out['exact_better_secondary_query']=str(status);out['secondary_optimum_certified']=status==z3.unsat;out['secondary_bound_query_smt2']=secondary.to_smt2()
    return out
def check(cfg,vector,exclusive=False):
    T=cfg['T'];v=list(map(F,vector));assert len(v)==12*T
    g=[v[3*t:3*t+3] for t in range(T)];f=[v[3*T+3*t:3*T+3*t+3] for t in range(T)];a=[v[6*T+3*t:6*T+3*t+3] for t in range(T)];c=v[9*T:10*T];d=v[10*T:11*T];e=v[11*T:12*T];bad={};count=0
    def row(name,value,equality=False):
        nonlocal count;count+=1
        if (value!=0 if equality else value>0):bad[name]=str(value)
    last=F(cfg['e0'])
    for t in range(T):
        for b in range(3):row(f'gen_lower_{t}_{b}',-g[t][b]);row(f'gen_upper_{t}_{b}',g[t][b]-100)
        for l,cap in enumerate([100,100,10]):row(f'line_upper_{t}_{l}',f[t][l]-cap);row(f'line_lower_{t}_{l}',-f[t][l]-cap)
        row(f'flow12_{t}',f[t][0]-a[t][0]+a[t][1],True);row(f'flow23_{t}',f[t][1]-a[t][1]+a[t][2],True);row(f'flow13_{t}',f[t][2]-a[t][0]+a[t][2],True);row(f'angle_ref_{t}',a[t][2],True)
        row(f'balance1_{t}',g[t][0]+d[t]-c[t]-f[t][0]-f[t][2],True);row(f'balance2_{t}',g[t][1]+f[t][0]-f[t][1],True);row(f'balance3_{t}',g[t][2]+f[t][1]+f[t][2]-F(cfg['load'][t]),True)
        row(f'charge_nonnegative_{t}',-c[t]);row(f'discharge_nonnegative_{t}',-d[t]);row(f'shared_power_{t}',c[t]+d[t]-1);row(f'energy_lower_{t}',-e[t]);row(f'energy_upper_{t}',e[t]-6)
        row(f'energy_dynamics_{t}',e[t]-F(cfg['rho'])*last-F(cfg['eta_c'])*c[t]+d[t]/F(cfg['eta_d']),True)
        if cfg['device']=='TAPER':row(f'charge_end_taper_{t}',c[t]-d[t]+e[t]/6-1)
        if exclusive:row(f'exclusivity_{t}',c[t]*d[t])
        if not cfg.get('battery_enabled',True):row(f'no_battery_charge_{t}',c[t],True);row(f'no_battery_discharge_{t}',d[t],True)
        last=e[t]
    return dict(pass_all=not bad,violations=bad,checked_rows=count,cost=str(sum((10*x[0]+20*x[1]+100*x[2] for x in g),F(0))),net_power=list(map(str,[d[t]-c[t] for t in range(T)])))
def reconstruct(cfg,vector):
    T=cfg['T'];v=list(map(F,vector));p=[v[10*T+t]-v[9*T+t] for t in range(T)];c=[max(-x,F(0)) for x in p];d=[max(x,F(0)) for x in p];e=[];state=F(cfg['e0'])
    for t in range(T):state=F(cfg['rho'])*state+F(cfg['eta_c'])*c[t]-d[t]/F(cfg['eta_d']);e.append(state)
    out=v[:9*T]+c+d+e;assert all(out[10*T+t]-out[9*T+t]==p[t] for t in range(T));assert out[:9*T]==v[:9*T]
    return list(map(str,out))
def counterquery(cfg,face=None,timeout_s=60):
    cons,vec,c,d,e,cost,service=exact_constraints(cfg,False);s=z3.Solver();s.set(timeout=int(timeout_s*1000),random_seed=0);s.add(cons)
    if face and 'cost' in face:s.add(cost==z3.RealVal(face['cost']))
    if face and 'budget' in face:s.add(cost<=z3.RealVal(face['budget']))
    if face and 'service' in face:s.add(service==z3.RealVal(face['service']))
    state=z3.RealVal(cfg['e0']);bad=[]
    for t in range(cfg['T']):
        power=d[t]-c[t];ch=z3.If(power<0,-power,0);dis=z3.If(power>0,power,0);state=z3.RealVal(cfg['rho'])*state+z3.RealVal(cfg['eta_c'])*ch-dis/z3.RealVal(cfg['eta_d']);bad +=[state<0,state>6]
        if cfg['device']=='TAPER':bad.append(ch-dis+state/6>1)
    s.add(z3.Or(bad));start=time.perf_counter();status=s.check();out=dict(status=str(status),wall_seconds=time.perf_counter()-start,scope='entire feasible query set' if face is None else face,encoding_smt2=s.to_smt2())
    if status==z3.sat:
        m=s.model();v=[str(rational(m.eval(x,model_completion=True))) for x in vec];out['relaxed_vector']=v;out['relaxed_check']=check(cfg,v);lift=reconstruct(cfg,v);out['reconstructed_vector']=lift;out['reconstructed_check']=check(cfg,lift,True);assert out['relaxed_check']['pass_all'] and not out['reconstructed_check']['pass_all']
    return out
