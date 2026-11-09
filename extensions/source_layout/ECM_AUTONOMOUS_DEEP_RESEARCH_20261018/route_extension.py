"""R2: frozen full-network max-margin feasibility and exact affine policy."""
from fractions import Fraction as F
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from scipy.sparse import coo_matrix
from scipy.optimize import linprog
from model import D,K,build,check,data,configs,lift,fingerprint
from network import load_map,complete
OUT=D/'03_RTS_EXACT_NETWORK/R2';OUT.mkdir(exist_ok=True)
def main():
    start=time.perf_counter();cfg=configs()[0];m=build(cfg);src=m['src'];ix=m['ix'];n=ix['n'];target=next(j for j,g in enumerate(src['generators']) if g['id']=='313_CC_1');assert src['generators'][target]['bus']==313
    rr=[];cc=[];vv=[];br=[];er=[];ec=[];ev=[];be=[]
    bounds=[(None,None)]*(n+1);bounds[-1]=(0,1)
    for row in m['rows']:
        coeff=dict(row['coeff'])
        if row['equality']:
            i=len(be);be.append(float(row['rhs']));er.extend([i]*len(coeff));ec.extend(coeff);ev.extend(map(float,coeff.values()))
        else:
            family=row['family'];margin=F(0)
            if family in ('GEN_LOWER','GEN_UPPER'):
                k=next(iter(coeff));t=k//ix['G'];j=k%ix['G'];upper=F(src['generators'][j]['upper'][t])
                if upper and j!=target:margin=min(F(1),upper/4)
            elif family=='LINE_LIMIT':margin=F(1)
            elif family=='GEN_RAMP' and not row['redundant_in_old_builder']:margin=F(1)
            if margin:coeff[n]=margin
            i=len(br);br.append(float(row['rhs']));rr.extend([i]*len(coeff));cc.extend(coeff);vv.extend(map(float,coeff.values()))
    for t in range(24):
        bounds[t*ix['G']+target]=(177.5,177.5);bounds[ix['c']+t]=(0,0);bounds[ix['d']+t]=(0,0)
    obj=np.zeros(n+1);obj[-1]=-1
    r=linprog(obj,A_ub=coo_matrix((vv,(rr,cc)),shape=(len(br),n+1)).tocsr(),b_ub=np.array(br),A_eq=coo_matrix((ev,(er,ec)),shape=(len(be),n+1)).tocsr(),b_eq=np.array(be),bounds=bounds,method='highs',options={'time_limit':60})
    numeric=dict(success=bool(r.success),status=int(r.status),message=r.message,margin=float(r.x[-1]) if r.x is not None else None,vector=r.x[:n].tolist() if r.x is not None else None,wall_seconds=time.perf_counter()-start,purpose='nonempty/fullbox network extension;not economic dispatch')
    (OUT/'BASELINE_NUMERICAL_SEARCH.json').write_text(json.dumps(numeric,indent=2))
    if not r.success:raise RuntimeError('Fixed affine policy baseline failed; keep NO-GO and do not substitute another source choice')
    inv=load_map();tries=[];exact=None
    for den in (10**6,10**9,10**12):
        g=[F(str(v)).limit_denominator(den) for v in r.x[:24*ix['G']]]
        for t in range(24):
            g[t*ix['G']+target]=F(355,2)
            # Deterministic largest numeric two-sided generator margin at this hour.
            candidates=[(min(float(r.x[t*ix['G']+j]),float(F(gen['upper'][t]))-float(r.x[t*ix['G']+j])),j) for j,gen in enumerate(src['generators']) if j!=target and F(gen['upper'][t])>0]
            balance=max(candidates)[1];res=sum((F(b['load'][t]) for b in src['buses']),F(0))-sum(g[t*ix['G']:(t+1)*ix['G']],F(0));g[t*ix['G']+balance]+=res
        retained=complete(src,g,[F(0)]*24,[F(0)]*24,inv);full=retained+[F(0)]*48+[F(75)]*24;qa=check(m,full,True)
        tries.append(dict(denominator_limit=den,pass_all=qa['pass_all'],violations=qa['violations'][:10]))
        if qa['pass_all']:exact=full;break
    (OUT/'RATIONAL_RECOVERY_ATTEMPTS.json').write_text(json.dumps(tries,indent=2))
    assert exact is not None,'No exact baseline at fixed ladder; no certificate'
    # Verify universal box support. All other network/generator coordinates fixed.
    gen=src['generators'][target];center=F(355,2);radius=F(50)
    assert all(F(0)<=center-radius and center+radius<=F(upper) for upper in gen['upper'])
    assert 2*radius<=F(gen['ramp'])
    row_identity=[]
    for row in m['rows']:
        a=row['coeff'];family=row['family'];terms={}
        if family in ('BUS_BALANCE','DC_FLOW','REFERENCE_ANGLE'):
            # Change for a symbolic p_t: generator -p plus device d-c=+p.
            for t in range(24):
                coefficient=-a.get(t*ix['G']+target,F(0))+a.get(ix['d']+t,F(0))
                # Original p is d-c; substitute d=p,c=0 for checking balance
                # identities only. Never used for device energy/box rows.
                if coefficient:terms[str(t)]=str(coefficient)
            assert not terms,(row['id'],terms)
        row_identity.append(row['id'])
    obj=dict(status='EXACT_UNIVERSAL_NETWORK_EXTENSION',model_sha256=fingerprint(m),source_sha256=hashlib.sha256((K/'02_PROTOCOL/NORMALIZED_RTS_INPUT.json').read_bytes()).hexdigest(),query='p plus ALL g/f/angles',generator_id=gen['id'],generator_index=target,policy='g313[t]=355/2-p[t]; all other retained coordinates equal exact baseline',power_box=['-50','50'],generator_policy_range=[str(center-radius),str(center+radius)],worst_ramp='100',source_ramp=gen['ramp'],baseline_vector=list(map(str,exact)),native_baseline_qa=qa,scope='Every24h power-box trajectory has an exact retained-network completion;not economic-optimality or field validation',maximum_rounding_denominator=den,construction_wall_seconds=time.perf_counter()-start,new_theorem=False)
    (OUT/'UNIVERSAL_NETWORK_EXTENSION_CERTIFICATE.json').write_text(json.dumps(obj,indent=2));print(json.dumps({k:v for k,v in obj.items() if k not in ('baseline_vector','native_baseline_qa')},indent=2))
if __name__=='__main__':main()
