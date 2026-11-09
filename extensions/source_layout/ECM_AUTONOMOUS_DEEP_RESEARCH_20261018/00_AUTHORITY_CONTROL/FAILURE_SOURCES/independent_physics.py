"""Direct source-based native-row Fraction checker. No producer imports."""
from pathlib import Path
from fractions import Fraction as F
import json
U=Path(__file__).resolve().parent
def data():return json.loads((U/'02_PROTOCOL/NORMALIZED_RTS_INPUT.json').read_text())
def check(cfg,vector,exclusive=False,numerical=False,budget=None):
    src=data();T=24;G=len(src['generators']);L=len(src['lines']) if cfg['network'] else 0;B=len(src['buses']) if cfg['network'] else 0
    fo=T*G;ao=fo+T*L;ci=ao+T*B;di=ci+T;ei=di+T;v=list(map(F,vector));assert len(v)==ei+T
    g=[v[t*G:(t+1)*G] for t in range(T)];c=v[ci:di];d=v[di:ei];en=v[ei:];eta=F(17,20) if cfg['loss'] else F(1);previous=F(cfg['e0']);bad={};count=0;maxima={};exactmax={}
    def row(name,value,equality=False,scale=F(1),unit='MW'):
        nonlocal count
        count+=1;res=abs(value) if equality else max(value,F(0));threshold=max(F(1,10**5),abs(scale)/10**8) if numerical else F(0)
        maxima[unit]=max(maxima.get(unit,0),float(res))
        if res>threshold:bad[name]=dict(residual=str(value),unit=unit)
    genbus={b['id']:[j for j,x in enumerate(src['generators']) if x['bus']==b['id']] for b in src['buses']}
    bi={b['id']:k for k,b in enumerate(src['buses'])}
    for t in range(T):
        for j,x in enumerate(src['generators']):
            row(f'generator_lower_{t}_{j}',-g[t][j]);row(f'generator_upper_{t}_{j}',g[t][j]-F(x['upper'][t]),scale=F(x['upper'][t]))
            if t:
                row(f'ramp_up_{t}_{j}',g[t][j]-g[t-1][j]-F(x['ramp']),scale=F(x['ramp']))
                row(f'ramp_dn_{t}_{j}',g[t-1][j]-g[t][j]-F(x['ramp']),scale=F(x['ramp']))
        if cfg['network']:
            fl=v[fo+t*L:fo+(t+1)*L];ang=v[ao+t*B:ao+(t+1)*B]
            row(f'angle_reference_{t}',ang[0],True,unit='rad')
            for j,l in enumerate(src['lines']):
                lim=F(l['limit']);row(f'flow_upper_{t}_{j}',fl[j]-lim,scale=lim);row(f'flow_lower_{t}_{j}',-fl[j]-lim,scale=lim)
                row(f'dc_flow_{t}_{j}',fl[j]-F(l['susceptance'])*(ang[bi[l['from_bus']]]-ang[bi[l['to_bus']]]),True,scale=lim)
            for b in src['buses']:
                balance=sum((g[t][j] for j in genbus[b['id']]),F(0))-F(b['load'][t])
                if b['id']==313:balance+=d[t]-c[t]
                for j,l in enumerate(src['lines']):
                    if l['from_bus']==b['id']:balance-=fl[j]
                    if l['to_bus']==b['id']:balance+=fl[j]
                row(f'bus_balance_{t}_{b["id"]}',balance,True,scale=F(b['load'][t]))
        else:row(f'copperplate_balance_{t}',sum(g[t],F(0))+d[t]-c[t]-sum((F(b['load'][t]) for b in src['buses']),F(0)),True,scale=sum(g[t],F(0)))
        row(f'charge_lower_{t}',-c[t]);row(f'discharge_lower_{t}',-d[t]);row(f'shared_rating_{t}',c[t]+d[t]-50,scale=F(50))
        row(f'head_energy_lower_{t}',-en[t],unit='MWh');row(f'head_energy_upper_{t}',en[t]-150,unit='MWh')
        tail=150-en[t];row(f'tail_energy_lower_{t}',-tail,unit='MWh');row(f'tail_energy_upper_{t}',tail-150,unit='MWh')
        row(f'energy_recursion_{t}',en[t]-previous-eta*c[t]+d[t],True,unit='MWh')
        if cfg['taper']:row(f'charge_end_taper_{t}',c[t]+en[t]/3-50,scale=F(50))
        if exclusive:row(f'exclusivity_{t}',min(abs(c[t]),abs(d[t])))
        previous=en[t]
    cost=sum((g[t][j]*F(x['cost']) for t in range(T) for j,x in enumerate(src['generators'])),F(0))
    service=sum((c[t]-d[t] for t in src['service_hours_zero_based']),F(0))
    if budget is not None:row('service_budget',cost-F(budget),scale=F(budget),unit='cost_units')
    return dict(pass_all=not bad,checked_rows=count,violations=bad,maximum_residual_by_unit=maxima,cost=str(cost),service_objective=str(service),
                net_power=list(map(str,[d[t]-c[t] for t in range(T)])),numerical_tolerance_applied=numerical)
def lift(cfg,vector):
    src=data();G=len(src['generators']);L=len(src['lines']) if cfg['network'] else 0;B=len(src['buses']) if cfg['network'] else 0
    ci=24*(G+L+B);v=list(map(F,vector));p=[v[ci+24+t]-v[ci+t] for t in range(24)];c=[max(-q,F(0)) for q in p];d=[max(q,F(0)) for q in p];ee=[];old=F(cfg['e0']);eta=F(17,20) if cfg['loss'] else F(1)
    for t in range(24):old+=eta*c[t]-d[t];ee.append(old)
    out=v[:ci]+c+d+ee
    assert out[:ci]==v[:ci] and all(out[ci+24+t]-out[ci+t]==p[t] for t in range(24))
    return list(map(str,out))
