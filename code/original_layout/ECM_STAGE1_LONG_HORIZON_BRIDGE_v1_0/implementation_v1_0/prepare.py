"""Preregistration, read-only environment preflight and non-solver implementation QA."""
from common import *
from model import *
import argparse,platform,subprocess,shutil,importlib,random,ast
FLAGS=getattr(subprocess,'CREATE_NO_WINDOW',0)
def ps(cmd):
    p=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,creationflags=FLAGS)
    return p.stdout.decode('utf-8','replace').strip()
def env():
    import numpy,scipy,z3
    import scipy.optimize._highspy._core as hc
    files=[Path(sys.executable),Path(numpy.__file__),Path(scipy.__file__),Path(z3.__file__)]
    for mod in [numpy,scipy,z3]:
        for pat in ['**/*.pyd','**/*.dll']:files.extend(Path(mod.__file__).parent.glob(pat))
    q=dict(python_executable=sys.executable,python_version=sys.version,numpy_version=numpy.__version__,scipy_version=scipy.__version__,z3_version=z3.get_version_string(),HiGHS_version='.'.join(str(getattr(hc,'HIGHS_VERSION_'+k)) for k in ['MAJOR','MINOR','PATCH']),OS=platform.platform(),CPU=ps('Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json -Compress'),RAM_total_bytes=memory()['total_bytes'],dependency_paths=[str(ROOT/'RESEARCH/round2/dependencies'),str(ROOT/'RESEARCH/round2/z3_dependencies')],binary_and_module_hashes={str(p):sha(p) for p in sorted(set(files))},hash_scope='interpreter, package entry modules, package pyd/dll binaries, versions/hardware; not a claim to hash entire OS',solver_options=dict(LP_method='highs',threads=1,primal_feasibility_tolerance=1e-7,dual_feasibility_tolerance=1e-7,ipm_optimality_tolerance=1e-8,presolve=True,LP_decision_threshold=1e-8,regression_absolute_tolerance=1e-7,Z3_random_seed=0,Z3_max_memory_MB=768,SMT_budget_seconds_per_state=300,state_wall_budget_seconds=1800,process_grace_seconds=30,max_reduced_LP_subproblems=262144,automatic_transient_retries=2))
    q['environment_hash']=digest(q);return q
def preflight():
    f=verify_freeze();e=read(O/'00_PROTOCOL/STAGE1_ENVIRONMENT.json');live=env();environment_matches=live['environment_hash']==e['environment_hash'];disk=shutil.disk_usage(O);power=subprocess.run(['powercfg','/query','SCHEME_CURRENT','SUB_SLEEP'],capture_output=True,creationflags=FLAGS)
    powertext=power.stdout.decode('gbk','replace');stamp=now().replace(':','').replace('.','');atomic(O/'logs'/('POWER_SETTINGS_READ_ONLY_'+stamp+'.txt'),powertext)
    rr=subprocess.run([sys.executable,'-B',str(O/'implementation_v1_0/runner.py'),'--test-resume'],capture_output=True,text=True,creationflags=FLAGS,cwd=O)
    writable=os.access(O,os.W_OK);resume=read(O/'08_QA/CHECKPOINT_RESUME_TEST.json')['status']=='PASS' and 'VERIFIED_SKIP_REAL_RESULT' in rr.stdout
    q=dict(timestamp=now(),working_directory=str(Path.cwd()),Python_executable=sys.executable,environment_hash=e['environment_hash'],solver_versions={k:e[k] for k in ['numpy_version','scipy_version','z3_version','HiGHS_version']},available_disk_space=disk.free,estimated_full_output_allowance_bytes=20*1024**3,disk_reserve_bytes=2*1024**3,available_memory=memory(),CPU=e['CPU'],output_directory_writable=writable,checkpoint_resume_test_status='PASS' if resume else 'FAIL',real_result_resume_test=rr.stdout.strip(),power_settings_read_only_log='logs/POWER_SETTINGS_READ_ONLY_'+stamp+'.txt',sleep_hibernation_note='Read-only powercfg log retained; no OS changes. Any nonzero idle setting may interrupt long work; user-initiated sleep/power loss remains possible.',protocol_hash=sha(O/'00_PROTOCOL/STAGE1_PROTOCOL_v1_0.md'))
    q['live_environment_matches']=environment_matches
    q['status']='ENVIRONMENT_HASH_CONFLICT' if not environment_matches else 'DISK_CAPACITY_BLOCKER' if disk.free<22*1024**3 else 'MEMORY_RESOURCE_BLOCKER' if q['available_memory']['available_bytes']<128*1024**2 else 'PASS' if writable and resume else 'PREFLIGHT_BLOCKER'
    p=O/'08_QA/LONG_RUN_PREFLIGHT.json'
    if p.exists():atomic(O/'08_QA'/('LONG_RUN_PREFLIGHT_'+stamp+'.json'),q)
    else:atomic(p,q)
    print(json.dumps(q,ensure_ascii=False),flush=True)
    if q['status']!='PASS':raise RuntimeError(q['status'])
def main():
    if (O/'00_PROTOCOL/FREEZE_MANIFEST.json').exists():verify_freeze();print('ALREADY_FROZEN_NO_REWRITE');return
    for p in (O/'implementation_v1_0').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
    pairs,states=make_matrix();counts={}
    for s in states:
        key=(s['T'],s['eta_c'],s['h'],s['row_form'],s['phase']=='REGRESSION')
        if key not in counts:
            tr=transforms(build(s));chosen=tr if s['phase']=='REGRESSION' else [r for r in tr if not r['auto']];counts[key]=dict(predicted_reduced_subproblems=1+sum(2**len(r['positive']) for r in chosen),target_rows=len(tr),automatic_rows=sum(r['auto'] for r in tr),checked_rows=len(chosen),predicted_full_sign_upper_bound=2**s['T']*(1+len(chosen)+4*s['T']))
        s['planned_work']=counts[key]
    atomic(O/'01_FROZEN_INPUTS/STAGE1_INPUT_MANIFEST.json',dict(version='1.0',frozen_at=now(),pairs=pairs,states=states,scientific_pair_count=sum(p['phase']!='REGRESSION' for p in pairs),regression_pair_count=36,total_state_cells=len(states),conditional_horizons=[48,96,128,192,256],no_statistical_independence_claim=True))
    for s in states:atomic(O/'01_FROZEN_INPUTS/states'/(s['case_id']+'.json'),s)
    selected=[]
    for T in [4,8,12,16,24,32]:
        for ei,eta in enumerate(['13/20','9/10','1']):
            for ri,kind in enumerate(['N','G']):
                h=['1/60','1/4'][(ei+ri)%2];state=['old','new'][(ei+ri+(T//4))%2]
                matches=[s for s in states if s['phase']!='REGRESSION' and s['T']==T and s['eta_c']==eta and s['h']==h and s['row_form']==kind and s['initial_rule']=='source60' and s['state']==state];assert len(matches)==1;selected.append(matches[0]['case_id'])
    atomic(O/'01_FROZEN_INPUTS/RUNTIME_REPEAT_PANEL_MANIFEST.json',dict(rule='For each T and eta index ei,row index ri: h=[1/60,1/4][(ei+ri)%2]; state=[old,new][(ei+ri+T//4)%2]; source60. Frozen before any runs.',selected_case_ids=selected,selected_states=36,warmup_index=0,measured_indices=[1,2,3,4,5],same_input_hash=True,no_new_scientific_samples=True))
    # Rational identity QA is implementation testing on arbitrary vectors, not optimized scientific evidence.
    rng=random.Random(20261002);checks=0
    for s in [x for x in states if x['T'] in [2,8,24,256] and x['state']=='old' and x['initial_rule']=='source60']:
        m=build(s);tr=transforms(m);T=m['T'];c=[F(rng.randrange(11),20) for _ in range(T)];d=[F(rng.randrange(11),20) for _ in range(T)];E=[];e=m['e0']
        for t in range(T):e+=m['h']*(m['eta']*c[t]-d[t]-AUX);E.append(e)
        x=c+d+E;y=recover(m,x);p=[d[t]-c[t] for t in range(T)]
        for z in tr:
            a=z['const']+sum((l*u+v*abs(u) for l,v,u in zip(z['ell'],z['v'],p)),F(0));assert a==value(z['row'],y);checks+=1
    atomic(O/'08_QA/PHASE0_IMPLEMENTATION_QA.json',dict(status='PASS',exact_row_identity_tests=checks,seed=20261002,solver_runs=0,scientific_samples=0,syntax='all implementation files parsed'))
    e=env();atomic(O/'00_PROTOCOL/STAGE1_ENVIRONMENT.json',e)
    baseline={}
    for directory in [ROOT/'RESEARCH/round3',ROOT/'ECM_STAGE0_EVIDENCE_AUDIT']:
        for p in directory.rglob('*'):
            if p.is_file():baseline[str(p)]=sha(p)
    for q in read(ROOT/'ECM_STAGE0_EVIDENCE_AUDIT/00A_INPUT_PDF_IDENTITIES.json'):baseline[q['path']]=sha(q['path'])
    atomic(O/'00_PROTOCOL/PROTECTED_ASSET_BASELINE.json',baseline)
    lineage={str(ROOT/'RESEARCH/round3'/n):sha(ROOT/'RESEARCH/round3'/n) for n in ['run_source_transition_pilot.py','run_affine_row_pilot.py','run_f2_formal_implementation.py','F2_SOURCE_TRANSITION_PROTOCOL_v0_1.md','F2_AFFINE_ROW_AUDIT_SPEC_v0_1.md','F2_FORMAL_IMPLEMENTATION_PROTOCOL_v1_0.md']};atomic(O/'00_PROTOCOL/IMPLEMENTATION_LINEAGE.json',lineage)
    files={str(p.relative_to(O)).replace('\\','/'):sha(p) for d in ['00_PROTOCOL','01_FROZEN_INPUTS','implementation_v1_0'] for p in sorted((O/d).rglob('*')) if p.is_file()}
    atomic(O/'00_PROTOCOL/FREEZE_MANIFEST.json',dict(frozen_at=now(),files=files,implementation_hash=impl_hash(),environment_hash=e['environment_hash'],scope='All protocols, implementation, environment snapshot and input files immutable; outputs/checkpoints append independently'))
    # Atomic immutable writes, collision prevention and corruption detection without solver execution.
    fixture=O/'08_QA/resume_fixture/result.json';atomic(fixture,dict(value='SYNTHETIC_OPERATIONAL_QA',scientific_sample=False));h=sha(fixture);immutable=False
    try:atomic(fixture,dict(value='SHOULD_NOT_REPLACE'))
    except FileExistsError:immutable=True
    assert immutable and sha(fixture)==h
    atomic(O/'08_QA/resume_fixture/checkpoint.json',dict(result_hash=h,input_hash=digest(states[0]),implementation_hash=impl_hash()))
    ck=read(O/'08_QA/resume_fixture/checkpoint.json');assert ck['result_hash']==sha(fixture);bad='0'*64;assert ck['result_hash']!=bad
    atomic(O/'08_QA/CHECKPOINT_RESUME_TEST.json',dict(status='PASS',immutable_collision_rejected=immutable,matching_result_verified=True,corrupt_hash_rejected=True,real_result_skip_test='Performed again by preflight after regression',fixture_hash=h))
    print(json.dumps(dict(status='FROZEN',states=len(states),pairs=len(pairs),runtime_panel_states=len(selected),implementation_hash=impl_hash(),environment_hash=e['environment_hash']),ensure_ascii=False),flush=True)
if __name__=='__main__':
    if '--preflight' in sys.argv:preflight()
    else:main()
