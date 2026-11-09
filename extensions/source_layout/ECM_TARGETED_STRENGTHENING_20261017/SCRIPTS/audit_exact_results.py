"""Independent certificate arithmetic uses frozen rows, not the producer's matrix code."""
from pathlib import Path
from fractions import Fraction as F
import json,csv,time,copy,itertools,hashlib
import frozen_internal_model as frozen
W=Path(__file__).resolve().parents[1];C=W/'04_CERTIFICATION';Q=W/'06_INDEPENDENT_QA'
def native(m,v):
    v=list(map(F,v));assert len(v)==m['n'];assert all(frozen.value(r,v)<=0 for r in m['rows']);assert all(frozen.value(r,v)==0 for r in m['eq']);return v
def lossless(p):
    i=p['input'];assert F(i['eta_c'])==F(i['eta_d'])==F(i['rho'])==1
    assert set(p['covered_native_families'])=={'flow_nonnegativity','shared_rating','energy_bounds','energy_dynamics','charge_start','charge_end','discharge_start','discharge_end'}
    m=frozen.build(i);T=m['T'];v=native(m,p['nonempty_vector'])
    for r in m['rows']:
        if r['family']=='FLOW_NONNEG':continue
        assert all(r['co'].get(t,0)+r['co'].get(T+t,0)>=0 for t in range(T))
    for r in m['eq']:assert all(r['co'].get(t,0)+r['co'].get(T+t,0)==0 for t in range(T))
    assert frozen.recover(m,v)==v
    return len(m['rows'])+len(m['eq'])
def eq(p):
    i=p['input'];m=frozen.build(i);T=m['T'];native(m,p['nonempty_vector']);transforms={m['rows'].index(t['row']):t for t in frozen.transforms(m)}
    assert set(transforms)==set(p['full_target_rows']);auto=set(p['automatic_native_rows']);seen={};total=0
    for k in auto:assert k in transforms and all(v>=0 for v in transforms[k]['v'])
    A=[r['co'] for r in m['rows']];b=[r['rhs'] for r in m['rows']]
    for t in range(T):A +=[{T+t:F(1),t:F(-1),3*T+t:F(-1)},{T+t:F(-1),t:F(1),3*T+t:F(-1)}];b +=[F(0),F(0)]
    box=[(F(0),F(1,2))]*(2*T)+[(F(3,25),F(57,100))]*T+[(F(0),F(1,2))]*T
    for item in p['row_upper_certificates']:
        k=item['native_row_index'];tr=transforms[k];assert k not in auto
        signs={int(j):s for j,s in item['positive_signs'].items()};assert set(signs)==set(tr['positive']);assert all(s in [-1,1] for s in signs.values())
        r=[-v for v in tr['ell']]+tr['ell']+[F(0)]*T+tr['v'][:];value=tr['const']
        for t,s in signs.items():a=r[3*T+t];r[t]-=a*s;r[T+t]+=a*s;r[3*T+t]=0
        for j,v in item['lambda'].items():
            j=int(j);v=F(v);assert v>=0;value+=v*b[j]
            for col,a in A[j].items():r[col]-=v*a
        for j,v in item['mu'].items():
            rr=m['eq'][int(j)];v=F(v);value+=v*rr['rhs']
            for col,a in rr['co'].items():r[col]-=v*a
        value+=sum((a*(box[j][1] if a>=0 else box[j][0]) for j,a in enumerate(r)),F(0));assert value==F(item['exact_upper_bound']) and value<=0
        seen.setdefault(k,set()).add(tuple(signs[t] for t in sorted(signs)));total+=1
    for k,tr in transforms.items():
        if k not in auto:assert seen[k]==set(itertools.product([-1,1],repeat=len(tr['positive'])))
    return total
def rejected(fn,p):
    try:fn(p)
    except (AssertionError,KeyError,ValueError,IndexError):return True
    return False
def main():
    start=time.perf_counter();rows=[];ms=[];ep=[];sp=[]
    for f in sorted((C/'M1_EXACT_CERTIFICATES').glob('*.json')):
        p=json.loads(f.read_text());count=lossless(p);rows.append(dict(case_id=p['input']['case_id'],method='M1',status='EQ',independent_check='PASS',checked_objects=count));ms.append(p)
    for f in sorted((C/'CENSUS_RESULTS').glob('*.json')):
        r=json.loads(f.read_text());p=r['proof'];m=frozen.build(p['input'])
        if r['status']=='EQ':count=eq(p);ep.append(p)
        else:
            native(m,p['relaxed_vector']);test=frozen.verify_witness(m,p['relaxed_vector']);assert test['certified'] and test['recovered_dynamics_pass'] and test['exclusive_pass'];count=len(m['rows'])+len(m['eq']);sp.append(p)
        rows.append(dict(case_id=p['input']['case_id'],method=r['method'],status=r['status'],independent_check='PASS',checked_objects=count))
    assert len(rows)==len({r['case_id'] for r in rows})==152
    mutations=[]
    p=copy.deepcopy(ms[0]);p['input']['eta_c']='9/10';mutations.append(('M1_changed_efficiency',rejected(lossless,p)))
    p=copy.deepcopy(ms[0]);p['covered_native_families'].remove('charge_end');mutations.append(('M1_missing_family',rejected(lossless,p)))
    p=copy.deepcopy(ms[0]);p['nonempty_vector'][0]='100';mutations.append(('M1_invalid_feasibility',rejected(lossless,p)))
    p=copy.deepcopy(ep[0]);p['row_upper_certificates'].pop();mutations.append(('M2_missing_branch',rejected(eq,p)))
    p=copy.deepcopy(ep[0]);p['row_upper_certificates'][0]['exact_upper_bound']='-999999';mutations.append(('M2_forged_upper',rejected(eq,p)))
    p=copy.deepcopy(ep[0]);p['row_upper_certificates'][0]['lambda']['0']='-1';mutations.append(('M2_negative_multiplier',rejected(eq,p)))
    p=copy.deepcopy(sp[0]);p['relaxed_vector'][0]='100';mutations.append(('M3_infeasible_witness',rejected(lambda p:native(frozen.build(p['input']),p['relaxed_vector']),p)))
    assert all(v for _,v in mutations)
    with (Q/'CERTIFICATE_SECOND_IMPLEMENTATION.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result=dict(status='PASS',unique_original_inputs=152,EQ=len(ms)+len(ep),STRICT=len(sp),M1_full_frozen_native_matrix_guards=len(ms),M2_exact_upper_bound_objects=sum(r['checked_objects'] for r in rows if r['method']=='M2'),mutation_tests=[dict(test=n,rejected=v) for n,v in mutations],independence='Producer uses direct second native matrix builder; this audit uses original byte-preserved frozen matrix/transforms and separate arithmetic.',wall_seconds=time.perf_counter()-start)
    (Q/'CERTIFICATE_SECOND_IMPLEMENTATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
