from fractions import Fraction as F
from fractions import Fraction as F
def row(name,family,t,co,rhs):return dict(name=name,family=family,period=t,co={str(k):str(F(v)) for k,v in co.items() if F(v)},rhs=str(F(rhs)))
def build(p,e0):
    T=p['T'];h=F(p['h']);ec=F(p['eta_c']);ed=F(p['eta_d']);lo=F(p['lo']);hi=F(p['hi']);pc=F(p['pc']);pd=F(p['pd']);e0=F(e0);rs=[];eq=[]
    for t in range(T):
        c,d,e=t,T+t,2*T+t
        rs +=[row('c_lo_'+str(t),'FLOW_NONNEG',t,{c:-1},0),row('d_lo_'+str(t),'FLOW_NONNEG',t,{d:-1},0),row('c_hi_'+str(t),'CHARGE_RATING',t,{c:1},pc),row('d_hi_'+str(t),'DISCHARGE_RATING',t,{d:1},pd),row('E_lo_'+str(t),'SOC_LOWER',t,{e:-1},-lo),row('E_hi_'+str(t),'SOC_UPPER',t,{e:1},hi)]
        co={e:1,c:-h*ec,d:h/ed};rhs=e0 if t==0 else 0
        if t:co[e-1]=-1
        eq.append(row('dynamics_'+str(t),'DYNAMICS',t,co,rhs))
        if p['family'] in ['HULL','HCH','MORALES']:
            rs.append(row('power_hull_'+str(t),'POWER_HULL',t,{c:1/pc,d:1/pd},1))
        if p['family'] in ['HCH','MORALES']:
            co_c={c:h*ec};co_d={d:h/ed};rc=hi;rd=-lo
            if t:co_c[e-1]=1;co_d[e-1]=-1
            else:rc-=e0;rd+=e0
            rs+=[row('charge_headroom_'+str(t),'CHARGE_START',t,co_c,rc),row('discharge_headroom_'+str(t),'DISCHARGE_START',t,co_d,rd)]
    if p['family']=='MORALES':
        mins=[e0];maxs=[e0]
        for t in range(1,T):mins.append(max(lo,mins[-1]-h*pd/ed));maxs.append(min(hi,maxs[-1]+h*ec*pc))
        bc=[min(pc,max((hi-lo)/(h*ec)-t*pc,0)) for t in range(T)]
        bd=[min(pd,max((hi-lo)*ed/h-t*pd,0)) for t in range(T)]
        cs=[[min(pc,max((hi-mins[t])/(h*ec)-tau*pc,0)) for tau in range(T-t)] for t in range(T)]
        ds=[[min(pd,max((maxs[t]-lo)*ed/h-tau*pd,0)) for tau in range(T-t)] for t in range(T)]
        PCs=[x[0] for x in cs];PDs=[x[0] for x in ds]
        for t in range(T):
            # Exact limiting handling at zero availability: zero variable explicitly fixed; its coefficient is irrelevant.
            rs +=[row('reachable_c_'+str(t),'CHARGE_REACHABLE',t,{t:1},PCs[t]),row('reachable_d_'+str(t),'DISCHARGE_REACHABLE',t,{T+t:1},PDs[t])]
            for bt in range(T-t):
                cc={};dd={}
                for tau in range(bt+1):
                    rc=max(-PDs[t+tau]/(ec*ed),sum(cs[t][tau:bt+1])-sum(bc[:bt-tau]))
                    rd=max(-PCs[t+tau]*ec*ed,sum(ds[t][tau:bt+1])-sum(bd[:bt-tau]))
                    ac=-1/(ec*ed) if rc<0 else rc/PDs[t+tau] if PDs[t+tau] else F(0)
                    ad=-ec*ed if rd<0 else rd/PCs[t+tau] if PCs[t+tau] else F(0)
                    cc[t+tau]=1;cc[T+t+tau]=ac;dd[T+t+tau]=1;dd[t+tau]=ad
                rs +=[row(f'MC_{t}_{bt}','CHARGE_MULTIPERIOD',t,cc,sum(cs[t][:bt+1])),row(f'MD_{t}_{bt}','DISCHARGE_MULTIPERIOD',t,dd,sum(ds[t][:bt+1]))]
    # Terminal constraints only if specified by an individual published mapping.
    if p.get('terminal')=='equal_initial':eq.append(row('terminal','TERMINAL_EQUALITY',T-1,{3*T-1:1},e0))
    return dict(T=T,h=str(h),eta_c=str(ec),eta_d=str(ed),rho='1',aux='0',e0=str(e0),lo=str(lo),hi=str(hi),power_rating=str(max(pc,pd)),pc=str(pc),pd=str(pd),family=p['family'],rows=rs,eq=eq,source_parameters=p)
