"""One fresh-process exact-repair attempt; both routes share acceptance checks."""
import argparse,hashlib,importlib.util,json,sys,time
from pathlib import Path
START=time.perf_counter();D=Path(__file__).resolve().parent;K=D/'00_AUTHORITY_CONTROL/PREVIOUS_CORE'
def main():
    p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--stage',required=True);p.add_argument('--route',required=True,choices=['baseline','candidate']);p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out)
    record=json.loads((K/'03_SYSTEM_FINAL/RUNS'/(a.case+'_old.json')).read_text());cfg=record['input'];original=record['stages'][a.stage];budget=record.get('service_budget') if a.stage.startswith('service') else None
    fixed=record['stages']['service_primary_'+('exclusive' if original['exclusive'] else 'relaxed')]['service_objective'] if a.stage.startswith('service_secondary') else None
    if a.route=='baseline':
        spec=importlib.util.spec_from_file_location('old_near_repair',D/'00_AUTHORITY_CONTROL/FAILURE_SOURCES/system_model.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref);ref.U=K;original_decide=ref.cvc5_decide
        def saved_decide(query,timeout_ms,count):
            out.with_suffix('.smt2').write_text(query,encoding='utf-8');return original_decide(query,timeout_ms,count)
        ref.cvc5_decide=saved_decide;result=ref.rational_repair(cfg,original,budget,fixed);vector=result.get('vector');status=result['status'];extra=None
    else:
        import recover_requests,fresh_request_map
        sys.argv=['recover_requests.py','--case',a.case,'--stage',a.stage];recover_requests.main();file=D/'04_CERTIFICATION_METHODS/R1_REQUEST_RECOVERY'/(a.case+'_'+a.stage+'_EXACT_RECOVERY.json');result=json.loads(file.read_text());vector=result.get('exact_vector');status=result['status'];extra=fresh_request_map.LAST_PREPROCESS
    valid=False;qa=None
    if vector is not None:
        from independent_verify import physics,reconstruct,C,A0,S,G,Q
        qa=physics(cfg,vector,original['exclusive']);assert qa['pass_all'];v=list(map(Q,vector));old=original['vector']
        assert all(abs(x-Q(str(y)))<=(Q(1,10**7) if A0<=j<C else Q(1,10**5)) for j,(x,y) in enumerate(zip(v,old)))
        cost=sum((v[t*G+j]*Q(g['cost']) for t in range(24) for j,g in enumerate(S['generators'])),Q(0));assert cost<=Q(str(original['cost']))+max(Q(1,100),abs(Q(str(original['cost'])))/10**8)
        service=sum((v[C+t]-v[C+24+t] for t in S['service_hours_zero_based']),Q(0))
        if budget is not None:assert cost<=Q(budget) and service<=Q(str(original['service_objective']))+Q(1,10**6)
        if fixed is not None:assert abs(service-Q(str(fixed)))<=Q(1,10**6)
        qa['reconstruction']=physics(cfg,reconstruct(cfg,vector),True);valid=True
    wall=time.perf_counter()-START
    saved=dict(case_id=a.case,stage=a.stage,route=a.route,status='CERTIFIED_NEARBY_FEASIBLE' if valid and wall<=15 else 'BUDGET_EXCEEDED' if valid else 'UNRESOLVED',raw_solver_status=status,algorithm_including_import_build_validation_seconds=wall,valid=valid,independent_qa=qa,cold_preprocessing=extra,raw_result=result)
    out.write_text(json.dumps(saved,indent=2));print(json.dumps({k:v for k,v in saved.items() if k not in ('raw_result','independent_qa')},indent=2))
if __name__=='__main__':main()
