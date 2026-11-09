"""Versioned extension of source-transition native equations; no original code imported."""
from fractions import Fraction as F
import itertools,time
P=F(1,2); LO=F(3,25); HI=F(57,100); BC=F(50,3); BD=F(25,3); AUX=F(7,1000)
def row(name,family,period,co,rhs):return dict(name=name,family=family,period=period,co={int(i):F(v) for i,v in co.items() if v},rhs=F(rhs))
def build(inp):
    T=inp['T'];eta=F(inp['eta_c']);h=F(inp['h']);e0=F(inp['effective_initial_energy']);rows=[];eq=[];targets=[]
    for t in range(T):
        c=t;d=T+t;e=2*T+t
        rows.extend([row('c_lo_'+str(t),'FLOW_NONNEG',t,{c:-1},0),row('d_lo_'+str(t),'FLOW_NONNEG',t,{d:-1},0),row('hull_'+str(t),'POWER_HULL',t,{c:1,d:1},P)])
        soc=[row('E_hi_'+str(t),'SOC_UPPER',t,{e:1},HI),row('E_lo_'+str(t),'SOC_LOWER',t,{e:-1},-LO)];rows.extend(soc);targets.extend(soc)
        co={e:F(1),c:-h*eta,d:h};rhs=-h*AUX
        if t:co[e-1]=-1
        else:rhs+=e0
        eq.append(row('dynamics_'+str(t),'DYNAMICS',t,co,rhs))
        for k,endpoint in [(t-1,'START'),(t,'END')]:
            cc={c:F(1)};dd={d:F(1)}
            if inp['row_form']=='N':cc[d]=-1;dd[c]=-1
            cr=BC*HI;dr=-BD*LO
            if k<0:cr-=BC*e0;dr+=BD*e0
            else:cc[2*T+k]=BC;dd[2*T+k]=-BD
            rs=[row('CHARGE_'+endpoint+'_'+str(t),'CHARGE_'+endpoint,t,cc,cr),row('DISCHARGE_'+endpoint+'_'+str(t),'DISCHARGE_'+endpoint,t,dd,dr)]
            rows.extend(rs);targets.extend(rs)
    return dict(T=T,eta=eta,h=h,e0=e0,rows=rows,eq=eq,targets=targets,n=3*T)
def value(r,x):return sum((a*x[i] for i,a in r['co'].items()),F(0))-r['rhs']
def recover(m,x):
    T=m['T'];c=[max(x[t]-x[T+t],F(0)) for t in range(T)];d=[max(x[T+t]-x[t],F(0)) for t in range(T)];E=[];e=m['e0']
    for t in range(T):e+=m['h']*(m['eta']*c[t]-d[t]-AUX);E.append(e)
    return c+d+E
def verify_witness(m,values):
    x=list(map(F,values));y=recover(m,x);bad=[]
    for i,r in enumerate(m['rows']):
        v=value(r,y)
        if v>0:bad.append(dict(row_index=i,row_name=r['name'],row_family=r['family'],period=r['period'],violation=str(v)))
    relaxed=all(value(r,x)<=0 for r in m['rows']) and all(value(r,x)==0 for r in m['eq'])
    return dict(relaxed_native_pass=relaxed,recovered_dynamics_pass=all(value(r,y)==0 for r in m['eq']),exclusive_pass=all(y[t]*y[m['T']+t]==0 for t in range(m['T'])),SOC_pass=all(LO<=e<=HI for e in y[2*m['T']:]),violations=bad,relaxed_vector=list(map(str,x)),recovered_vector=list(map(str,y)),certified=relaxed and bool(bad),max_violation=str(max((F(v['violation']) for v in bad),default=F(0))))
def first_action(e0,eta,h,kind):
    e1=e0+h*(eta*P-AUX);inp=dict(T=1,eta_c=str(eta),h=str(h),effective_initial_energy=str(e0),row_form=kind);m=build(inp);x=[P,F(0),e1]
    valid=LO<=e0<=HI and LO<=e1<=HI and all(value(r,x)<=0 for r in m['rows']) and all(value(r,x)==0 for r in m['eq'])
    return e1,valid
def transforms(m):
    T=m['T'];out=[]
    for r in m['targets']:
        a=[r['co'].get(2*T+k,F(0)) for k in range(T)];b=[r['co'].get(k,F(0)) for k in range(T)];g=[r['co'].get(T+k,F(0)) for k in range(T)]
        s=[];running=F(0)
        for v in reversed(a):running+=v;s.append(running)
        s=list(reversed(s));alpha=(m['eta']+1)/2;kappa=1-m['eta']
        ell=[(g[t]-b[t])/2-m['h']*alpha*s[t] for t in range(T)]
        v=[(b[t]+g[t]-m['h']*kappa*s[t])/2 for t in range(T)]
        const=sum((a[k]*(m['e0']-(k+1)*m['h']*AUX) for k in range(T)),F(0))-r['rhs']
        out.append(dict(row=r,const=const,ell=ell,v=v,positive=[i for i,x in enumerate(v) if x>0],negative=[i for i,x in enumerate(v) if x<0],auto=all(x>=0 for x in v)))
    return out
def make_matrix():
    phases=[('REGRESSION',[2]),('PHASE2',[4,6,8,12,16,24]),('PHASE2B',[5,7,10,14,20]),('PHASE3',[32,48,96]),('PHASE4',[128,192,256])];pairs=[];states=[]
    for phase,hs in phases:
        pressure=phase in ['PHASE3','PHASE4']
        for T in hs:
            for i,(eta,h,kind,rule) in enumerate(itertools.product([F(13,20),F(9,10),F(1)],[F(1,60),F(1,4)] if pressure else [F(1,60),F(1,12),F(1,4)],['N','G'],['source60'] if pressure else ['source60','boundary_relative'])):
                gain=h*(eta*P-AUX);e0=F(9,25) if rule=='source60' else F(54,100)-T*gain-F(3,1000);e1,eligible=first_action(e0,eta,h,kind);pid=f'{phase}_T{T:03d}_P{i:02d}'
                pair=dict(paired_setting_id=pid,phase=phase,T=T,eta_c=str(eta),eta_d='1',rho='1',h=str(h),row_form=kind,initial_rule=rule,e0=str(e0),e1=str(e1),gain=str(gain),eligible=eligible,valid_first_charge=eligible,not_applicable_reason='' if eligible else 'INITIAL_STATE_OR_FIRST_NATIVE_ACTION_INVALID',legacy_case_index=i if T==2 else None)
                pairs.append(pair)
                for state,e in [('old',e0),('new',e1)]:states.append(dict(pair,case_id=pid+'_'+state,state=state,effective_initial_energy=str(e)))
    return pairs,states
