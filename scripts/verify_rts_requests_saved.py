"""Check frozen numerical requests and nearby exact points, keeping their meanings distinct."""
from pathlib import Path
from fractions import Fraction as F
import argparse,json,sys,collections
from verify_extensions_saved import load_rts_without_solver,load_plain,EXT
def main():
    p=argparse.ArgumentParser();p.add_argument('--report-dir',type=Path,required=True);a=p.parse_args();a.report_dir.mkdir(parents=True,exist_ok=True)
    D=EXT/'ECM_AUTONOMOUS_DEEP_RESEARCH_20261018';n=load_rts_without_solver(D/'independent_verify.py');model=load_plain('rts_saved_native_rows',D/'model.py')
    G=n['G'];C=n['C'];A0=n['A0'];source=n['S'];exact=[];numeric=[]
    originals={}
    for f in sorted((D/'00_AUTHORITY_CONTROL/PREVIOUS_CORE/03_SYSTEM_FINAL/RUNS').glob('*_old.json')):
        o=json.loads(f.read_text());originals[o['input']['case_id']]=o
        m=model.build(o['input'])
        for stage in ['economic_relaxed','service_secondary_relaxed']:
            r=o['stages'][stage];assert r['success'] and r['numerical_reconstructed_native']['pass_all']
            v=list(map(lambda x:F(str(x)),r['vector']));rec=model.lift(m,v)
            assert v[:C]==rec[:C] and all(v[C+24+t]-v[C+t]==rec[C+24+t]-rec[C+t] for t in range(24))
            maximum=F(0)
            for row in m['rows']:
                rv=model.value(row,rec);positive=abs(rv) if row['equality'] else max(rv,F(0));maximum=max(maximum,positive)
                tol=F(1,10**7) if row['unit']=='rad' else F(1,10**5)
                assert positive<=tol
            assert all(rec[C+t]*rec[C+24+t]==0 for t in range(24))
            numeric.append({'case_id':o['input']['case_id'],'stage':stage,'numerical_reconstruction_pass':True,'maximum_native_residual':str(maximum),'exact_feasibility_claimed':False})
    assert len(originals)==4 and len(numeric)==8
    for f in sorted((D/'04_CERTIFICATION_METHODS/R1_REQUEST_RECOVERY').glob('*EXACT_RECOVERY.json')):
        r=json.loads(f.read_text());assert r['status']=='EXACT_NEARBY_FEASIBLE';cfg=r['input'];original=originals[cfg['case_id']];stage=original['stages'][r['stage']]
        assert n['physics'](cfg,r['exact_vector'],r['exclusive'])['pass_all']
        v=list(map(F,r['exact_vector']));old=list(map(lambda x:F(str(x)),stage['vector']))
        assert len(v)==len(old)==C+72
        assert all(abs(x-y)<=(F(1,10**7) if A0<=j<C else F(1,10**5)) for j,(x,y) in enumerate(zip(v,old)))
        cost=sum((v[t*G+j]*F(g['cost']) for t in range(24) for j,g in enumerate(source['generators'])),F(0))
        assert cost==F(r['cost']) and cost<=F(str(stage['cost']))+max(F(1,100),abs(F(str(stage['cost'])))/10**8)
        service=sum((v[C+t]-v[C+24+t] for t in source['service_hours_zero_based']),F(0))
        if r['stage'].startswith('service'):
            assert cost<=F(original['service_budget']) and service<=F(str(stage['service_objective']))+F(1,10**6)
        if r['stage'].startswith('service_secondary'):
            primary=original['stages']['service_primary_'+('exclusive' if r['exclusive'] else 'relaxed')]['service_objective']
            assert abs(service-F(str(primary)))<=F(1,10**6)
        p_same=all(v[C+24+t]-v[C+t]==old[C+24+t]-old[C+t] for t in range(24));z_same=v[:C]==old[:C]
        exact.append({'case_id':cfg['case_id'],'stage':r['stage'],'native_feasible':True,'near_original_within_recorded_bounds':True,'same_p':p_same,'same_z':z_same,'same_complete_query':p_same and z_same,'exact_optimality_claimed':False})
    assert len(exact)==24 and not any(x['same_complete_query'] for x in exact)
    out={'status':'PASS','original_selected_numerical_requests':numeric,'nearby_exact_points':exact,'original_request_count':8,'nearby_point_count':24,'nearby_points_preserving_original_full_query':0,'solver_calls':0,'scope':'Replayed native rows and recorded proximity/cost/primary-value limits on saved outputs; neither new repair nor optimality certification.'}
    (a.report_dir/'rts_request_evidence_verification.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if not isinstance(v,list)},indent=2))
if __name__=='__main__':main()
