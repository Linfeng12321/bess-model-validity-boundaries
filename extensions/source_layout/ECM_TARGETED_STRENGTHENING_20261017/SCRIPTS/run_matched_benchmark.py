from pathlib import Path
import json,time,subprocess,sys,csv,os,ctypes,argparse,platform
W=Path(__file__).resolve().parents[1];C=W/'04_CERTIFICATION';D=C/'MATCHED_BENCHMARK_RUNS';D.mkdir(exist_ok=True)
def worker(item,route,out):
    # Use the same single permitted CPU for both routes; no system affinity change.
    k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p;h=k.GetCurrentProcess();pm=ctypes.c_size_t();sm=ctypes.c_size_t()
    assert k.GetProcessAffinityMask(ctypes.c_void_p(h),ctypes.byref(pm),ctypes.byref(sm));mask=pm.value&-pm.value;assert k.SetProcessAffinityMask(ctypes.c_void_p(h),ctypes.c_size_t(mask))
    import frozen_internal_model as frozen
    from independent_native import verify_lossless_certificate,lossless_nonempty,verify_strict
    from certification_routes import certify,verify_eq
    from original_primary_smt import exact_route
    case=json.loads(Path(item).read_text());start=time.perf_counter();cpu=time.process_time();budget=30
    if route=='original':
        result=exact_route(frozen.build(case),start+budget);status=result['exact'];status=status if status in ['EQ','STRICT'] else 'UNRESOLVED'
    else:
        if case['eta_c']=='1':
            v,qa=lossless_nonempty(case);assert qa['pass_all'];result=dict(method='M1',nonempty_vector=list(map(str,v)));status='EQ'
        else:
            result=certify(case,budget)
            status=result['status']
            if status=='EQ':verify_eq(result['proof'])
            elif status=='STRICT':assert verify_strict(case,result['proof']['relaxed_vector'])['certified']
    record=dict(case_id=case['case_id'],route=route,status=status,wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,processor_affinity=mask,versions=dict(python=platform.python_version()),result=result)
    Path(out).write_text(json.dumps(record,indent=2),encoding='utf-8')
def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',nargs=3);a=p.parse_args()
    if a.worker:worker(*a.worker);return
    card=json.loads((C/'MATCHED_BENCHMARK_CARD.json').read_text());rows=[];start=time.perf_counter()
    for index,case in enumerate(card['cases']):
        inp=D/(case['case_id']+'_INPUT.json');inp.write_text(json.dumps(case,indent=2),encoding='utf-8')
        for repeat in range(card['repeats']):
            for route in (['original','new'] if (index+repeat)%2==0 else ['new','original']):
                target=D/(case['case_id']+f'_R{repeat}_{route}.json')
                if not target.exists():
                    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1');r=subprocess.run([sys.executable,'-B',__file__,'--worker',str(inp),route,str(target)],env=env,capture_output=True,text=True,timeout=65)
                    (D/(target.stem+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0,r.stderr
                data=json.loads(target.read_text());rows.append({k:data[k] for k in ['case_id','route','status','wall_seconds','cpu_seconds','processor_affinity']}|dict(repeat=repeat,result_file=target.relative_to(W).as_posix()))
                print(json.dumps(rows[-1]),flush=True)
    with (C/'MATCHED_BENCHMARK_RESULTS.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    from collections import Counter
    summary=dict(case_inputs=len(card['cases']),repeats=card['repeats'],route_executions=len(rows),outcomes={route:dict(Counter(r['status'] for r in rows if r['route']==route)) for route in ['original','new']},wall_seconds=time.perf_counter()-start,scientific_sample_size=len(card['cases']),interpretation='Repeated timings are not additional scientific states. Same 30 s primary route budget. Preprocessing/validation may add bounded small overhead.')
    (C/'MATCHED_BENCHMARK_SUMMARY.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
if __name__=='__main__':main()
