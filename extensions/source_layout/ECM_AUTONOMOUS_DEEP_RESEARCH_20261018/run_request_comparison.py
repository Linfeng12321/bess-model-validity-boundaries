"""Registered24output/48freshprocess finite diagnostic, with censored failures."""
from pathlib import Path
import csv,datetime,hashlib,json,os,subprocess,sys,time
import psutil
D=Path(__file__).resolve().parent;OUT=D/'04_CERTIFICATION_METHODS/REQUEST_RECOVERY_COMPARISON';OUT.mkdir(exist_ok=True)
def main():
    designs=json.loads((D/'01_SCIENTIFIC_PROTOCOL/REGISTERED_REQUEST_COMPARISON.json').read_text());rows=[];start=time.perf_counter()
    for task in designs['executions']:
        dest=OUT/(task['id']+'.json');receipt=OUT/(task['id']+'_PROCESS.json')
        if receipt.exists():
            record=json.loads(receipt.read_text());assert record['task']==task;rows.append(record);continue
        command=[sys.executable,'-B',str(D/'request_comparison_worker.py'),'--case',task['case_id'],'--stage',task['stage'],'--route',task['route'],'--out',str(dest)];peak=0;cpu=0;t=time.perf_counter();utc=datetime.datetime.now(datetime.timezone.utc).isoformat();timedout=False
        with (OUT/(task['id']+'.stdout.txt')).open('w') as so,(OUT/(task['id']+'.stderr.txt')).open('w') as se:
            p=subprocess.Popen(command,stdout=so,stderr=se,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
            try:psutil.Process(p.pid).cpu_affinity([psutil.Process().cpu_affinity()[0]])
            except psutil.Error:pass
            while p.poll() is None:
                try:
                    tree=[psutil.Process(p.pid)]+psutil.Process(p.pid).children(recursive=True);peak=max(peak,sum(x.memory_info().rss for x in tree));cpu=max(cpu,sum(sum(x.cpu_times()[:2]) for x in tree))
                except psutil.Error:pass
                if time.perf_counter()-t>20 or peak>6*1024**3:
                    timedout=True
                    if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True)
                    break
                time.sleep(.05)
            code=p.wait()
        result=json.loads(dest.read_text()) if dest.exists() else None
        row=dict(task=task,command=command,started_utc=utc,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=code,outer_wall_seconds=time.perf_counter()-t,peak_rss_bytes=peak,cpu_seconds_sampled=cpu,status='TIMEOUT_PROCESS' if timedout else 'ERROR' if code else result['status'],result_sha256=hashlib.sha256(dest.read_bytes()).hexdigest() if dest.exists() else None)
        receipt.write_text(json.dumps(row,indent=2));rows.append(row)
        with (D/'RUN_JOURNAL.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(event='FAIR_DIAGNOSTIC_EXECUTION',**row))+'\n')
        print(task['id'],row['status'],round(row['outer_wall_seconds'],3),flush=True)
        # Persist each completed execution; interruption resumes remaining tasks.
        (OUT/'CHECKPOINT.json').write_text(json.dumps(dict(completed_execution_ids=[r['task']['id'] for r in rows],last=task['id'],wall_seconds=time.perf_counter()-start),indent=2))
    with (D/'04_CERTIFICATION_METHODS/METHOD_BENCHMARK_WITH_CENSORED_TIMES.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['case_id','stage','route','development_or_holdout','status','outer_wall_seconds','cpu_seconds_sampled','peak_rss_bytes','exit_code']);w.writeheader()
        for r in rows:w.writerow(dict(case_id=r['task']['case_id'],stage=r['task']['stage'],route=r['task']['route'],development_or_holdout=r['task']['split'],**{k:r[k] for k in ['status','outer_wall_seconds','cpu_seconds_sampled','peak_rss_bytes','exit_code']}))
    counts={route:{s:sum(r['task']['route']==route and r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})} for route in ('baseline','candidate')}
    (OUT/'SUMMARY.json').write_text(json.dumps(dict(executions=len(rows),fixed_saved_outputs=24,underlying_model_states=4,development_outputs=4,holdout_outputs=20,counts=counts,total_new_driver_wall_seconds=time.perf_counter()-start,censored_speedup_not_computed=True),indent=2));print(json.dumps(counts,indent=2))
if __name__=='__main__':main()
