"""Fresh complete native-row builder from frozen rational RTS inputs.

No old classification labels are read. Original variable order is retained only
to allow exact comparison to saved trajectories; checks use independent physics.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json
D=Path(__file__).resolve().parent;K=D/'00_AUTHORITY_CONTROL/PREVIOUS_CORE'
def data():return json.loads((K/'02_PROTOCOL/NORMALIZED_RTS_INPUT.json').read_text())
def configs():return [x for x in json.loads((K/'02_PROTOCOL/REGISTERED_SYSTEM_DESIGNS.json').read_text()) if x['network']]
def build(cfg):
    src=data();T=src['T'];G=len(src['generators']);B=len(src['buses']);L=len(src['lines']);assert cfg['network'] and T==24
    ix=dict(g=0,f=T*G,a=T*(G+L),c=T*(G+L+B),d=T*(G+L+B)+T,e=T*(G+L+B)+2*T,G=G,B=B,L=L,T=T,n=T*(G+L+B+3))
    rows=[];bi={b['id']:i for i,b in enumerate(src['buses'])};eta=F(17,20) if cfg['loss'] else F(1)
    def add(name,family,period,coeff,rhs,eq=False,unit='MW',scope='QUERY_SET_NATIVE',redundant=False):
        rows.append(dict(id=name,family=family,period=period,coeff={int(j):F(v) for j,v in coeff.items() if v},rhs=F(rhs),equality=eq,unit=unit,scope=scope,redundant_in_old_builder=redundant))
    names=[]
    for t in range(T):
        names += [f'g_{t}_{g["id"]}' for g in src['generators']]
    names +=[f'f_{t}_{l["id"]}' for t in range(T) for l in src['lines']]
    names +=[f'angle_{t}_{b["id"]}' for t in range(T) for b in src['buses']]
    names +=[f'{v}_{t}' for v in ('charge','discharge','energy') for t in range(T)]
    for t in range(T):
        for j,g in enumerate(src['generators']):
            k=t*G+j;upper=F(g['upper'][t]);ramp=F(g['ramp']);add(f'g_lo_{t}_{j}','GEN_LOWER',t,{k:-1},0);add(f'g_hi_{t}_{j}','GEN_UPPER',t,{k:1},upper)
            if t:
                red=ramp>=max(map(F,g['upper']));add(f'ramp_up_{t}_{j}','GEN_RAMP',t,{k:1,k-G:-1},ramp,redundant=red);add(f'ramp_down_{t}_{j}','GEN_RAMP',t,{k:-1,k-G:1},ramp,redundant=red)
        for k,l in enumerate(src['lines']):
            fi=ix['f']+t*L+k;beta=F(l['susceptance']);add(f'f_hi_{t}_{k}','LINE_LIMIT',t,{fi:1},F(l['limit']));add(f'f_lo_{t}_{k}','LINE_LIMIT',t,{fi:-1},F(l['limit']))
            add(f'dc_{t}_{k}','DC_FLOW',t,{fi:1,ix['a']+t*B+bi[l['from_bus']]:-beta,ix['a']+t*B+bi[l['to_bus']]:beta},0,True)
        add(f'reference_{t}','REFERENCE_ANGLE',t,{ix['a']+t*B:1},0,True,'rad')
        for b in src['buses']:
            coeff={t*G+j:F(1) for j,g in enumerate(src['generators']) if g['bus']==b['id']}
            if b['id']==313:coeff.update({ix['c']+t:F(-1),ix['d']+t:F(1)})
            for j,l in enumerate(src['lines']):
                if l['from_bus']==b['id']:coeff[ix['f']+t*L+j]=-F(1)
                if l['to_bus']==b['id']:coeff[ix['f']+t*L+j]=F(1)
            add(f'balance_{t}_{b["id"]}','BUS_BALANCE',t,coeff,F(b['load'][t]),True)
        c=ix['c']+t;dd=ix['d']+t;e=ix['e']+t
        add(f'c_lo_{t}','CHARGE_LOWER',t,{c:-1},0);add(f'c_hi_{t}','CHARGE_UPPER',t,{c:1},50)
        add(f'd_lo_{t}','DISCHARGE_LOWER',t,{dd:-1},0);add(f'd_hi_{t}','DISCHARGE_UPPER',t,{dd:1},50)
        add(f'e_lo_{t}','ENERGY_LOWER',t,{e:-1},0,unit='MWh');add(f'e_hi_{t}','ENERGY_UPPER',t,{e:1},150,unit='MWh')
        add(f'tail_lo_{t}','TAIL_LOWER_REDUNDANT',t,{e:1},150,unit='MWh',redundant=True);add(f'tail_hi_{t}','TAIL_UPPER_REDUNDANT',t,{e:-1},0,unit='MWh',redundant=True)
        dyn={e:F(1),c:-eta,dd:F(1)}
        if t:dyn[e-1]=-F(1)
        add(f'energy_{t}','ENERGY_RECURSION',t,dyn,F(cfg['e0']) if not t else F(0),True,'MWh')
        add(f'shared_{t}','SHARED_POWER',t,{c:1,dd:1},50)
        if cfg['taper']:add(f'taper_{t}','CHARGE_SOC_END',t,{c:1,e:F(1,3)},50)
    return dict(cfg=cfg,src=src,ix=ix,names=names,rows=rows,eta=eta)
def value(row,v):return sum((a*v[j] for j,a in row['coeff'].items()),F(0))-row['rhs']
def check(m,vector,exclusive=False):
    x=list(map(F,vector));assert len(x)==m['ix']['n'];bad=[];checks=0
    for row in m['rows']:
        r=value(row,x);checks+=1
        if (r!=0 if row['equality'] else r>0):bad.append(dict(row=row['id'],family=row['family'],residual=str(r),unit=row['unit']))
    if exclusive:
        for t in range(24):
            checks+=1
            if x[m['ix']['c']+t]*x[m['ix']['d']+t]!=0:bad.append(dict(row='exclusivity_'+str(t),family='EXCLUSIVITY'))
    return dict(pass_all=not bad,checked_rows=checks,violations=bad)
def lift(m,vector):
    v=list(map(F,vector));ix=m['ix'];c=[];d=[];ee=[];old=F(m['cfg']['e0'])
    for t in range(24):
        p=v[ix['d']+t]-v[ix['c']+t];cc=max(-p,F(0));dd=max(p,F(0));old+=m['eta']*cc-dd;c.append(cc);d.append(dd);ee.append(old)
    out=v[:ix['c']]+c+d+ee;assert out[:ix['c']]==v[:ix['c']]
    assert all(out[ix['d']+t]-out[ix['c']+t]==v[ix['d']+t]-v[ix['c']+t] for t in range(24))
    return out
def fingerprint(m):
    raw=[dict(r,coeff={str(k):str(v) for k,v in sorted(r['coeff'].items())},rhs=str(r['rhs'])) for r in m['rows']]
    return hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()
