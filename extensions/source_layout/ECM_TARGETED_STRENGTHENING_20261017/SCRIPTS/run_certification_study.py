from pathlib import Path
import json,argparse,time,hashlib,os,csv,datetime
from certification_routes import certify,verify_eq
from independent_native import verify_strict
W=Path(__file__).resolve().parents[1];C=W/'04_CERTIFICATION'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['regression','pilot','census'],required=True);p.add_argument('--budget',type=float,default=300);a=p.parse_args();reg=json.loads((C/'REGISTERED_CERTIFICATION_INPUTS.json').read_text());items=reg[{'regression':'regression','pilot':'unresolved_pilot','census':'all_unresolved'}[a.phase]]
    if a.phase!='regression':
        summary=json.loads((C/'REGRESSION_SUMMARY.json').read_text());assert summary['false_classifications']==0
    if a.phase=='census':
        summary=json.loads((C/'PILOT_SUMMARY.json').read_text());assert summary['new_exact_certificates']>0
    directory=C/(a.phase.upper()+'_RESULTS');directory.mkdir(exist_ok=True);rows=[];false=0;start=time.perf_counter();skipped=[]
    for r in items:
        inp=r['input'];case=inp['case_id']
        # M1 already supplies the full lossless census. Regression still runs general routes.
        if a.phase!='regression' and inp['eta_c']=='1':skipped.append(case);continue
        path=directory/(case+'.json')
        fingerprint=hashlib.sha256(json.dumps(inp,sort_keys=True).encode()).hexdigest()
        if path.exists():
            result=json.loads(path.read_text());assert result['input_fingerprint']==fingerprint
        else:
            result=certify(inp,a.budget);result.update(case_id=case,ORIGINAL_STATUS=r['original_status'],NEW_STATUS=result['status'],input_fingerprint=fingerprint,original_source_sha256=r['source_sha256'],registered_phase=a.phase,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),implementation_sha256=sha(W/'SCRIPTS/certification_routes.py'))
            if result['status']=='EQ':assert verify_eq(result['proof'])
            elif result['status']=='STRICT':assert verify_strict(inp,result['proof']['relaxed_vector'])['certified']
            tmp=path.with_suffix('.partial');tmp.write_text(json.dumps(result,indent=2),encoding='utf-8');os.replace(tmp,path)
        if result['status']=='EQ':assert verify_eq(result['proof'])
        elif result['status']=='STRICT':assert verify_strict(inp,result['proof']['relaxed_vector'])['certified']
        if a.phase=='regression' and result['status'] in ['EQ','STRICT'] and result['status']!=r['original_status']:false+=1
        rows.append(dict(case_id=case,ORIGINAL_STATUS=r['original_status'],NEW_STATUS=result['status'],method=result['method'],horizon=inp['T'],eta_c=inp['eta_c'],row_form=inp['row_form'],LP_calls=result.get('LP_calls',0),wall_seconds=result['wall_seconds'],reason=result.get('reason',''),certificate_file=path.relative_to(W).as_posix(),certificate_sha256=sha(path),independent_exact_check='PASS' if result['status'] in ['EQ','STRICT'] else 'NO_CERTIFICATE'))
        print(json.dumps({k:rows[-1][k] for k in ['case_id','ORIGINAL_STATUS','NEW_STATUS','method','wall_seconds','reason']}),flush=True)
        if false:raise RuntimeError('False classification; route halted')
    from collections import Counter
    with (C/(a.phase.upper()+'_RESULTS.csv')).open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=dict(phase=a.phase,cases_run=len(rows),lossless_already_certified_by_M1=len(skipped),outcomes=dict(Counter(r['NEW_STATUS'] for r in rows)),new_exact_certificates=sum(r['NEW_STATUS'] in ['EQ','STRICT'] for r in rows),false_classifications=false,wall_seconds=time.perf_counter()-start,budget_per_state=a.budget)
    (C/(a.phase.upper()+'_SUMMARY.json')).write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
