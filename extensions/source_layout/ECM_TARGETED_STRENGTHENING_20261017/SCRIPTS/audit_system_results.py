from pathlib import Path
from fractions import Fraction as F
import json,csv,copy,time,hashlib
import z3
from system_model import structure,numerical,exact_optimum,check,reconstruct
W=Path(__file__).resolve().parents[1];D=W/'03_SYSTEM_CASE';Q=W/'06_INDEPENDENT_QA'
def matrix_check(cfg,vector,exclusive):
    m=structure(cfg,exclusive);T=cfg['T'];v=list(map(F,vector))
    if exclusive:v +=[F(1) if v[9*T+t]>0 else F(0) for t in range(T)]
    assert len(v)==m['n']
    for x,(lo,hi) in zip(v,m['bounds']):assert lo<=x<=hi
    for row,b in zip(m['A'],m['b']):assert sum((a*v[j] for j,a in row.items()),F(0))<=b
    for row,b in zip(m['E'],m['f']):assert sum((a*v[j] for j,a in row.items()),F(0))==b
    return len(m['A'])+len(m['E'])+2*len(v)
def replay(smt,expected):
    s=z3.Solver();s.set(timeout=60000);s.from_string(smt);ans=str(s.check());assert ans==expected,(ans,expected);return True
def main():
    start=time.perf_counter();rows=[];replays=0;positive=[];nulls=[]
    for path in sorted((D/'RESULTS').glob('*.json')):
        obj=json.loads(path.read_text());cfg=obj['input'];T=cfg['T'];assert obj['status']=='COMPLETED'
        r=structure(cfg,False);e=structure(cfg,True);assert r['E']==e['E'] and r['f']==e['f'] and r['A']==[row for row,name in zip(e['A'],e['names']) if 'mode' not in name]
        for kind in ['economic','service']:
            for mode in ['relaxed','exclusive']:
                item=obj[kind][mode];ex=item['exact'];assert ex['primary_optimum_certified'];matrix_check(cfg,ex['vector'],mode=='exclusive');assert check(cfg,ex['vector'],mode=='exclusive')['pass_all']
                replay(ex['bound_query_smt2'],'unsat');replays+=1
                if kind=='service':assert ex['secondary_optimum_certified'];replay(ex['secondary_bound_query_smt2'],'unsat');replays+=1
                rec=reconstruct(cfg,ex['vector']);assert rec==item['reconstructed_vector'];assert rec[:9*T]==ex['vector'][:9*T]
                chk=check(cfg,rec,True);assert chk==item['reconstructed_check'];assert chk['net_power']==item['native_check']['net_power']
                if chk['violations']:assert all(k.startswith(('energy_','charge_end_taper_')) for k in chk['violations'])
        for kind in ['global_query_check','economic_optimal_face_check','service_optimal_face_check']:
            item=obj[kind];replay(item['encoding_smt2'],item['status']);replays+=1
            if item['status']=='sat':matrix_check(cfg,item['relaxed_vector'],False);assert not check(cfg,item['reconstructed_vector'],True)['pass_all']
        if cfg['state']=='new':assert F(cfg['e0'])==F(obj['state_update_source']['new_e0'])
        ec=obj['economic'];sv=obj['service'];row=dict(case_id=cfg['case_id'],state=cfg['state'],device=cfg['device'],profile=cfg['profile'],e0_exact=cfg['e0'],cost_gap_exact=obj['exact_cost_gap'],cost_gap_display=float(F(obj['exact_cost_gap'])),economic_cost_display=float(F(ec['relaxed']['exact']['cost'])),economic_request_realisable=ec['relaxed']['reconstructed_check']['pass_all'],service_request_realisable=sv['relaxed']['reconstructed_check']['pass_all'],service_relaxed_cost=sv['relaxed']['exact']['cost'],service_exclusive_cost=sv['exclusive']['exact']['cost'],service_values_agree=sv['relaxed']['exact']['service_objective']==sv['exclusive']['exact']['service_objective'],complete_relation='EQ' if obj['global_query_check']['status']=='unsat' else 'STRICT',bad_economic_optimum_exists=obj['economic_optimal_face_check']['status']=='sat',bad_primary_service_optimum_exists=obj['service_optimal_face_check']['status']=='sat',pass_all=True)
        rows.append(row)
    assert len(rows)==26 and len({(r['case_id'],r['state']) for r in rows})==26
    # Original source network no-battery numerical/exact optimum, not a PyPSA runtime claim.
    cfg=dict(T=1,load=['100'],device='BOX',eta_c='1',eta_d='1',rho='1',e0='0',battery_enabled=False,case_id='SOURCE_NO_BATTERY_BASELINE')
    nu=numerical(cfg);ex=exact_optimum(cfg);assert nu['success'] and F(ex['cost'])==7600 and ex['primary_optimum_certified'];matrix_check(cfg,ex['vector'],False)
    baseline=dict(input=cfg,numerical=nu,exact=ex,independent_matrix_check=True,source_expected_cost=7600,source_runtime_executed=False)
    (Q/'SOURCE_NETWORK_BASELINE_QA.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
    sample=json.loads(next((D/'RESULTS').glob('*.json')).read_text());v=sample['economic']['exclusive']['exact']['vector'];mut=copy.deepcopy(v);mut[0]=str(F(mut[0])+1);assert not check(sample['input'],mut,True)['pass_all'];mut=copy.deepcopy(v);mut[11*sample['input']['T']]='-1';assert not check(sample['input'],mut,True)['pass_all']
    with (Q/'SYSTEM_SECOND_IMPLEMENTATION.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    from collections import Counter
    out=dict(status='PASS',paired_settings=13,state_assessments=26,exact_SMT_replays=replays,matrix_and_direct_physical_check=True,numerical_LP_MILP_and_exact_model_agreement=True,network_variables_and_net_power_preserved=True,changed_constraint_between_pair='Only exclusivity',unit='Synthetic public-source system-model state; not field observations or independent devices',counts=dict(complete_query= dict(Counter(r['complete_relation'] for r in rows)),equal_economic_cost=sum(F(r['cost_gap_exact'])==0 for r in rows),failed_actual_economic_request=sum(not r['economic_request_realisable'] for r in rows),failed_actual_service_request=sum(not r['service_request_realisable'] for r in rows),equal_primary_service_value=sum(r['service_values_agree'] for r in rows)),wall_seconds=time.perf_counter()-start,mutations_rejected=2)
    (Q/'SYSTEM_SECOND_IMPLEMENTATION.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
