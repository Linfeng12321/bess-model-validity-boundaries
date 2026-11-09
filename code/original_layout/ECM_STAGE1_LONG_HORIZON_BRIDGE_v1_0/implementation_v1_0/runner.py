"""Serial, immutable, resumable campaign supervisor. All writes confined to Stage1."""
from common import *
from model import *
import subprocess,shutil,collections,threading,traceback
PY=sys.executable;FLAGS=getattr(subprocess,'CREATE_NO_WINDOW',0)
STOP_STATUSES={'UNKNOWN','TIMEOUT','BUDGET_EXCEEDED'}
def folder(inp):return O/('02_REGRESSION_T2' if inp['phase']=='REGRESSION' else '03_MAIN_HORIZON_MATRIX' if inp['phase'] in ['PHASE2','PHASE2B'] else '04_PRESSURE_TEST')
def resultpath(inp,runid=None):return (O/'06_RUNTIME/results'/runid if runid else folder(inp)/'results'/inp['case_id']).with_suffix('.json')
def load_result(inp,runid=None):
    p=resultpath(inp,runid)
    if not p.exists():return None
    q=read(p);f=read(O/'00_PROTOCOL/FREEZE_MANIFEST.json');payload=dict(q);stored=payload.pop('payload_sha256',None)
    if stored!=digest(payload):raise RuntimeError('RESULT_PAYLOAD_HASH_CONFLICT:'+str(p))
    rp=p.with_suffix('.receipt.json')
    if not rp.exists():
        if q['input_hash']!=digest(inp) or q['implementation_hash']!=f['implementation_hash'] or q['environment_hash']!=f['environment_hash']:raise RuntimeError('UNCOMMITTED_RESULT_IDENTITY_CONFLICT')
        atomic(rp,dict(result_sha256=sha(p),input_hash=digest(inp),implementation_hash=f['implementation_hash'],environment_hash=f['environment_hash'],status='PASS',recovered_missing_sidecar_after_atomic_commit=True))
    r=read(rp)
    if sha(p)!=r['result_sha256'] or r['input_hash']!=digest(inp) or r['implementation_hash']!=f['implementation_hash'] or r['environment_hash']!=f['environment_hash']:raise RuntimeError('RESUME_HASH_CONFLICT:'+str(p))
    for i,w in enumerate(q.get('witnesses',[])):
        wp=O/'05_WITNESSES'/((runid or inp['case_id'])+f'_W{i:02d}.json')
        if not wp.exists():atomic(wp,dict(case_id=inp['case_id'],execution_id=runid or inp['case_id'],input_hash=digest(inp),witness=w))
    return q
class Campaign:
    def __init__(self):
        self.freeze=verify_freeze();self.matrix=read(O/'01_FROZEN_INPUTS/STAGE1_INPUT_MANIFEST.json');self.states=self.matrix['states'];self.panel=read(O/'01_FROZEN_INPUTS/RUNTIME_REPEAT_PANEL_MANIFEST.json');self.counts=collections.Counter();self.completed=0;self.expected=len(self.states)+len(self.panel['selected_case_ids'])*6;self.phase='STARTING';self.T=None;self.last=None;self.current=None;self.latest=None;self.start=time.monotonic();self.exit=False
        for inp in self.states:
            q=load_result(inp)
            if q:self.completed+=1;self.counts[q['classification']]+=1;self.last=inp['case_id']
        byid={x['case_id']:x for x in self.states}
        for cid in self.panel['selected_case_ids']:
            for i in range(6):
                q=load_result(byid[cid],cid+f'_repeat{i}')
                if q:self.completed+=1;self.counts[q['classification']]+=1
    def heartbeat(self):
        q=dict(timestamp=now(),pid=os.getpid(),last_completed_case=self.last,current_case=self.current,current_phase=self.phase,current_horizon=self.T,completed_cells=self.completed,expected_cells=self.expected,cell_unit='state execution incl regression and warmup/repeats; route coverage reported separately',elapsed_wall_time=time.monotonic()-self.start,latest_checkpoint=self.latest,free_disk_space=shutil.disk_usage(O).free,available_memory=memory()['available_bytes'])
        for key in ['EQ','STRICT','EMPTY','UNKNOWN','TIMEOUT','BUDGET_EXCEEDED','NOT_APPLICABLE','ERROR','SKIPPED_BY_PREDECLARED_RULE']:q[key]=self.counts[key]
        atomic(O/'RUN_HEARTBEAT.json',q,replace=True)
    def pulse(self):
        while not self.exit:
            try:self.heartbeat()
            except Exception as e:
                with (O/'logs/heartbeat_errors.log').open('a',encoding='utf-8') as f:f.write(now()+' '+repr(e)+'\n')
            for _ in range(15):
                if self.exit:return
                time.sleep(1)
    def record(self,inp,q,runid=None):
        p=resultpath(inp,runid);q.update(input=inp,input_hash=digest(inp),implementation_hash=self.freeze['implementation_hash'],environment_hash=self.freeze['environment_hash'],completed_utc=now(),execution_id=runid or inp['case_id'])
        q['payload_sha256']=digest(q);atomic(p,q);receipt=dict(result_sha256=sha(p),input_hash=digest(inp),implementation_hash=self.freeze['implementation_hash'],environment_hash=self.freeze['environment_hash'],status='PASS',process_status=q.get('process_status'),path=str(p));atomic(p.with_suffix('.receipt.json'),receipt)
        for i,w in enumerate(q.get('witnesses',[])):
            wp=O/'05_WITNESSES'/((runid or inp['case_id'])+f'_W{i:02d}.json');atomic(wp,dict(case_id=inp['case_id'],execution_id=runid or inp['case_id'],input_hash=digest(inp),witness=w))
        event=dict(timestamp=now(),case_id=inp['case_id'],execution_id=runid or inp['case_id'],phase=self.phase,T=inp['T'],classification=q['classification'],result_hash=receipt['result_sha256'],result_path=str(p),input_hash=digest(inp),implementation_hash=self.freeze['implementation_hash'])
        log=O/'RUN_PROGRESS.csv';exists=log.exists()
        with log.open('a',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,list(event))
            if not exists:w.writeheader()
            w.writerow(event);f.flush();os.fsync(f.fileno())
        self.completed+=1;self.counts[q['classification']]+=1;self.last=runid or inp['case_id']
        print(json.dumps(dict(completed=self.completed,expected=self.expected,phase=self.phase,case=self.last,status=q['classification'],errors=q.get('errors',[])),ensure_ascii=False),flush=True)
        return q
    def execute(self,inp,runid=None,skip=None):
        q=load_result(inp,runid)
        if q:return q
        self.current=runid or inp['case_id'];self.T=inp['T']
        if skip or not inp['eligible']:
            st='SKIPPED_BY_PREDECLARED_RULE' if skip else 'NOT_APPLICABLE';return self.record(inp,dict(classification=st,reason=skip or inp['not_applicable_reason'],process_status='PASS',routes={r:dict(status=st,reason=skip or inp['not_applicable_reason'],wall_time=0.,LP_calls=0) for r in ['R1','R2','R3']},witnesses=[],errors=[],total_wall_time=0.),runid)
        if shutil.disk_usage(O).free<2*1024**3:raise RuntimeError('DISK_CAPACITY_BLOCKER')
        if memory()['available_bytes']<128*1024**2:raise MemoryError('GLOBAL_MEMORY_RESOURCE_BLOCKER')
        inputpath=O/'01_FROZEN_INPUTS/states'/(inp['case_id']+'.json');attempts=[];q=None
        for attempt in range(3):
            out=O/'logs/attempts'/((runid or inp['case_id'])+f'_attempt{attempt}.json');stdout=out.with_suffix('.log');out.parent.mkdir(exist_ok=True,parents=True)
            if out.exists():
                prior=read(out)
                if prior.get('process_status')!='ERROR':q=prior;break
                attempts.append(dict(attempt=attempt,status='RECOVERED_PRIOR_ERROR',error=prior.get('error')));continue
            try:
                with stdout.open('x',encoding='utf-8') as log:
                    p=subprocess.Popen([PY,'-B',str(O/'implementation_v1_0/checker.py'),'--input',str(inputpath),'--output',str(out)],cwd=O,stdout=log,stderr=subprocess.STDOUT,creationflags=FLAGS)
                    atomic(O/'checkpoints/ACTIVE_CHILD.json',dict(pid=p.pid,parent_pid=os.getpid(),execution_id=self.current,started=now(),input_hash=digest(inp),argv_input=str(inputpath)),replace=True)
                    try:rc=p.wait(timeout=1830)
                    except subprocess.TimeoutExpired:
                        p.kill();p.wait();partial=out.with_suffix('.partial.json');v=read(partial) if partial.exists() else {};routes=v.get('routes',{})
                        for r in ['R1','R2','R3']:
                            if r not in routes:routes[r]=dict(status='TIMEOUT',reason='STATE_WALL_BUDGET',wall_time=None,LP_calls=None)
                        r2=routes.get('R2',{});exact=r2.get('exact','UNKNOWN');witnesses=list(r2.get('witnesses',[]))
                        for r in ['R1','R3']:
                            w=routes.get(r,{}).get('witness')
                            if w and w.get('certified'):witnesses.append(w)
                        status='STRICT' if witnesses else exact if exact in ['EQ','EMPTY'] else 'TIMEOUT'
                        q=dict(v,classification=status,routes=routes,process_status='PASS',errors=[],timeout_reason='1800s worker budget plus30s process overhead',witnesses=witnesses);break
                if out.exists():
                    q=read(out)
                    if q.get('error_type') in ['AssertionError','ValueError','KeyError','TypeError','NameError'] or 'FROZEN_HASH_CONFLICT' in q.get('error',''):
                        q['process_status']='GLOBAL_SEMANTIC_QA_FAILURE';q['errors']=[q.get('error')];break
                    if q.get('process_status')!='ERROR':break
                if rc==0 and not out.exists():q=dict(error='MISSING_WORKER_RESULT',process_status='ERROR')
                attempts.append(dict(attempt=attempt,returncode=rc,error=(q or {}).get('error','PROCESS_CRASH')))
            except (OSError,PermissionError) as e:attempts.append(dict(attempt=attempt,error=repr(e)));q=None
            if attempt<2:time.sleep(2)
        if q is None or q.get('process_status')=='ERROR':q=dict(classification='ERROR',process_status='ERROR_PERSISTENT',errors=[],attempts=attempts,witnesses=[],routes={r:dict(status='ERROR',reason='ERROR_PERSISTENT') for r in ['R1','R2','R3']})
        q['attempt_history']=attempts;q=self.record(inp,q,runid)
        if q.get('errors'):raise RuntimeError('GLOBAL_SEMANTIC_QA_FAILURE:'+inp['case_id']+':'+repr(q['errors']))
        return q
    def checkpoint(self,pair):
        cp=O/'checkpoints'/(pair['paired_setting_id']+'.json')
        if not cp.exists():atomic(cp,dict(paired_setting_id=pair['paired_setting_id'],completed_utc=now(),implementation_hash=self.freeze['implementation_hash'],input_manifest_hash=sha(O/'01_FROZEN_INPUTS/STAGE1_INPUT_MANIFEST.json')))
        self.latest=str(cp)
    def regression(self):
        self.phase='REGRESSION';gate=O/'08_QA/T2_REGRESSION_GATE.json'
        if gate.exists():
            if read(gate)['status']!='PASS':raise RuntimeError('PRIOR_REGRESSION_FAILURE_STOP')
            return
        checks=[]
        for pair in self.matrix['pairs']:
            if pair['phase']!='REGRESSION':continue
            results={}
            for inp in [x for x in self.states if x['paired_setting_id']==pair['paired_setting_id']]:results[inp['state']]=self.execute(inp)
            legacy=read(ROOT/'RESEARCH/round3/f2_source_transition_v1'/f"case_{pair['legacy_case_index']:03d}.json")
            errors=[];witness_checks=[]
            for state in ['old','new']:
                q=results[state];old=legacy[state];routes=q.get('routes',{});r2=routes.get('R2',{});r1=routes.get('R1',{});r3=routes.get('R3',{})
                for key in ['feasible_smt','bad_smt','SOC_pass_power_fail_smt']:
                    if r2.get('queries',{}).get(key,{}).get('status')!=old[key]:errors.append(state+':'+key)
                for key,got in [('lp_max_all_row_margin',r1.get('global_max_value')),('lp_max_all_row_margin',r3.get('max_value')),('lp_max_SOC_valid_power_excess_MW',r3.get('max_SOC_valid_power_excess'))]:
                    expected=old[key]
                    if (expected is None)!=(got is None) or (expected is not None and abs(expected-got)>1e-7):errors.append(state+':'+key+':'+str(got)+' vs '+str(expected))
                if 'exact_witness' in old:
                    inp=q['input'];m=build(inp);v=list(map(F,old['exact_witness']['variables']));c=v[::2];d=v[1::2];e=m['e0'];E=[]
                    for t in range(2):e+=m['h']*(m['eta']*c[t]-d[t]-AUX);E.append(e)
                    w=verify_witness(m,c+d+E);ok=w['certified'] and w['SOC_pass'];witness_checks.append(dict(state=state,pass_check=ok,legacy_witness_preserved=True))
                    if not ok:errors.append(state+':LEGACY_WITNESS')
            o=results['old'].get('routes',{}).get('R2',{}).get('queries',{});n=results['new'].get('routes',{}).get('R2',{}).get('queries',{})
            stale=pair['eligible'] and o.get('bad_smt',{}).get('status')=='unsat' and o.get('feasible_smt',{}).get('status')=='sat' and n.get('SOC_pass_power_fail_smt',{}).get('status')=='sat'
            if stale!=legacy['stale_GO_native_failure']:errors.append('STALE_GO_MISMATCH')
            if pair['valid_first_charge']!=legacy['valid_first_charge']:errors.append('FIRST_ACTION_MISMATCH')
            checks.append(dict(pair=pair['paired_setting_id'],errors=errors,exact_witness_checks=witness_checks))
            self.checkpoint(pair)
            if errors:
                atomic(gate,dict(status='FAIL',checks=checks,reason='UNEXPLAINED_SCIENTIFIC_DISAGREEMENT'));raise RuntimeError('REGRESSION_DISAGREEMENT_GLOBAL_STOP:'+repr(errors))
        atomic(gate,dict(status='PASS',paired_settings=36,states=72,float_absolute_tolerance=1e-7,checks=checks,counts_as_new_scientific_samples=False));atomic(O/'02_REGRESSION_T2/T2_REGRESSION_REPORT.md','# T=2 regression\n\nPASS: all36 pairs /72 states match exact classifications, both existing LP endpoints, first-action and stale-GO labels. Existing rational witnesses reverified; witness coordinates need not match a nonunique solver choice. Absolute float tolerance1e-7 preregistered. These are software regression cells, not new scientific samples. Detailed gate:08_QA/T2_REGRESSION_GATE.json.\n')
    def run_phase(self,name,horizons,skip_reason=None):
        self.phase=name;out=[]
        for T in horizons:
            self.T=T
            for pair in [p for p in self.matrix['pairs'] if p['phase']==name and p['T']==T]:
                for inp in [x for x in self.states if x['paired_setting_id']==pair['paired_setting_id']]:out.append(self.execute(inp,skip=skip_reason))
                self.checkpoint(pair)
        return out
    def saturated(self,results):
        eligible=[q for q in results if q['input']['eligible']]
        return bool(eligible) and all(q['classification'] not in ['EQ','STRICT','EMPTY'] and all(q.get('routes',{}).get(r,{}).get('status') in STOP_STATUSES for r in ['R1','R2']) for q in eligible)
    def main(self):
        th=threading.Thread(target=self.pulse,daemon=True);th.start()
        try:
            self.regression()
            subprocess.run([PY,'-B',str(O/'implementation_v1_0/prepare.py'),'--preflight'],cwd=O,check=True,creationflags=FLAGS)
            if read(O/'08_QA/LONG_RUN_PREFLIGHT.json')['status']!='PASS':raise RuntimeError('PREFLIGHT_BLOCKER')
            self.run_phase('PHASE2',[4,6,8,12,16,24]);self.run_phase('PHASE2B',[5,7,10,14,20])
            stopped=False;last=[]
            for T in [32,48,96]:
                last=self.run_phase('PHASE3',[T],'PRESSURE_ESCALATION_STOPPED_BY_PREDECLARED_RULE' if stopped else None)
                if not stopped and self.saturated(last):stopped=True
            extend=not stopped and any(q['classification'] in ['EQ','STRICT'] or q.get('routes',{}).get('R1',{}).get('status')=='COMPLETED' for q in last if q['input']['eligible'])
            streak=0
            for T in [128,192,256]:
                rr=self.run_phase('PHASE4',[T],'EXTENSION_ENTRY_OR_TWO_HORIZON_SATURATION_RULE' if not extend or streak>=2 else None)
                if extend and streak<2:streak=streak+1 if self.saturated(rr) else 0
            subprocess.run([PY,'-B',str(O/'implementation_v1_0/prepare.py'),'--preflight'],cwd=O,check=True,creationflags=FLAGS)
            self.phase='PHASE5';byid={x['case_id']:x for x in self.states}
            for cid in self.panel['selected_case_ids']:
                for i in range(6):self.execute(byid[cid],cid+f'_repeat{i}')
                atomic(O/'checkpoints'/('RUNTIME_'+cid+'.json'),dict(case_id=cid,repeats_including_warmup=6,finished=now())) if not (O/'checkpoints'/('RUNTIME_'+cid+'.json')).exists() else None
            self.phase='FINAL_QA';subprocess.run([PY,'-B',str(O/'implementation_v1_0/report.py')],cwd=O,check=True,creationflags=FLAGS)
            self.phase='STAGE1_STOP';atomic(O/'RUN_STATUS.json',dict(status='STAGE1_STOP',reason='ALL_PREDECLARED_CELLS_ACCOUNTED_AND_QA_COMPLETE',timestamp=now(),pid=os.getpid()),replace=True)
        except Exception as e:
            self.phase='GLOBAL_STOP';atomic(O/'RUN_STATUS.json',dict(status='GLOBAL_STOP',reason=str(e),traceback=traceback.format_exc(),timestamp=now(),pid=os.getpid()),replace=True);raise
        finally:self.exit=True;th.join(timeout=20);self.heartbeat()
if __name__=='__main__':
    if '--test-resume' in sys.argv:
        # Resume validator exercised on an actual immutable result, no computation rerun.
        matrix=read(O/'01_FROZEN_INPUTS/STAGE1_INPUT_MANIFEST.json');inp=matrix['states'][0];p=resultpath(inp)
        if p.exists():assert load_result(inp) is not None;print('VERIFIED_SKIP_REAL_RESULT')
        else:print('NO_REAL_RESULT_YET')
    else:
        lock=O/'RUNNING.lock'
        if lock.exists():
            prior=read(lock);pid=prior['pid'];ctypes.windll.kernel32.OpenProcess.restype=ctypes.c_void_p;handle=ctypes.windll.kernel32.OpenProcess(0x1000,False,pid)
            if handle:
                ec=ctypes.c_ulong();ctypes.windll.kernel32.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(ec));ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(handle))
                if ec.value==259:raise RuntimeError('EXISTING_SUPERVISOR_PID_ALIVE:'+str(pid))
        child=O/'checkpoints/ACTIVE_CHILD.json'
        if child.exists():
            old=read(child);ctypes.windll.kernel32.OpenProcess.restype=ctypes.c_void_p;h=ctypes.windll.kernel32.OpenProcess(0x1000,False,old['pid'])
            if h:
                ec=ctypes.c_ulong();ctypes.windll.kernel32.GetExitCodeProcess(ctypes.c_void_p(h),ctypes.byref(ec));ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(h))
                if ec.value==259:raise RuntimeError('PRIOR_OWNED_CHILD_STILL_ALIVE_WAIT_BEFORE_RESUME:'+str(old['pid']))
        atomic(lock,dict(pid=os.getpid(),started=now(),script=str(Path(__file__).resolve())),replace=True)
        Campaign().main()
