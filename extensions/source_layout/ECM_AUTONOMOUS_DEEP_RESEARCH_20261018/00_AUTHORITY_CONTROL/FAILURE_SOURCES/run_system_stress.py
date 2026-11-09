from pathlib import Path
from fractions import Fraction as F
import argparse,hashlib,json,os,subprocess,sys,time
U=Path(__file__).resolve().parent
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_suffix('.partial');temp.write_text(json.dumps(obj,indent=2),encoding='utf-8');os.replace(temp,p)
def outcome(cfg,path):
    from system_model import numerical,rational_repair,global_query,reconstruct
    from independent_physics import check,lift
    start=time.perf_counter();out=dict(input=cfg,status='RUNNING',stages={})
    def stage(key,exclusive,objective='cost',budget=None,fixed=None):
        result=numerical(cfg,exclusive,objective,budget,fixed)
        out['stages'][key]=result;save(path,out)
        if result.get('vector') is not None:
            result['independent_numeric_native']=check(cfg,list(map(str,result['vector'])),exclusive,numerical=True,budget=budget)
            if not result['independent_numeric_native']['pass_all']:raise AssertionError('Independent numerical native check failed: '+key)
            nearby=rational_repair(cfg,result,budget,fixed)
            if nearby['status']=='sat':
                nearby['independent_exact_native']=check(cfg,nearby['vector'],exclusive,budget=budget)
                assert nearby['independent_exact_native']['pass_all']
                recovered=lift(cfg,nearby['vector']);assert recovered==reconstruct(cfg,nearby['vector'])
                nearby['reconstructed_vector']=recovered;nearby['reconstructed_native']=check(cfg,recovered,True,budget=budget)
                nearby['query_preserved']=nearby['independent_exact_native']['net_power']==nearby['reconstructed_native']['net_power']
                assert nearby['query_preserved']
                nearby['material_request_failure']=any(abs(F(r['residual']))>F(1,1000) and r['unit'] in ('MW','MWh') for r in nearby['reconstructed_native']['violations'].values())
            result['nearby_exact']=nearby
        out['stages'][key]=result;out['wall_seconds']=time.perf_counter()-start;save(path,out);print(cfg['case_id'],cfg['state'],key,result['status'],flush=True)
        return result
    re=stage('economic_relaxed',False);ex=stage('economic_exclusive',True)
    if ex['success']:
        budget=str(F(str(ex['cost']))*F(101,100));out['service_budget']=budget
        for mode,exc in [('relaxed',False),('exclusive',True)]:
            primary=stage('service_primary_'+mode,exc,'service',budget)
            if primary['success']:stage('service_secondary_'+mode,exc,'cost',budget,primary['service_objective'])
    feasible=any(r.get('nearby_exact',{}).get('status')=='sat' for r in out['stages'].values())
    if not cfg['loss'] and feasible:
        out['global_query']=dict(status='EQ_STRUCTURAL',nonempty_exact=True,
          guards=dict(lossless=True,retained_network_and_ramp_unchanged=True,energy_unchanged=True,nonnegative_flow_reconstruction=True,shared_rating_decreases=True,taper_charge_decreases=True),
          meaning='Complete declared native constraints preserved; not losslessness for arbitrary added constraints')
    elif cfg['loss']:
        glob=global_query(cfg)
        if glob['status']=='sat':
            glob['independent_relaxed_check']=check(cfg,glob['vector']);assert glob['independent_relaxed_check']['pass_all']
            rv=lift(cfg,glob['vector']);glob['reconstructed_vector']=rv;glob['independent_reconstructed_check']=check(cfg,rv,True)
            assert not glob['independent_reconstructed_check']['pass_all']
            glob['relation']='STRICT'
        elif glob['status']=='unsat':glob['relation']='EQ' if feasible else 'UNRESOLVED_NONEMPTY'
        else:glob['relation']='UNRESOLVED'
        out['global_query']=glob
    else:out['global_query']=dict(status='UNRESOLVED_NONEMPTY')
    out['status']='COMPLETED';out['wall_seconds']=time.perf_counter()-start;save(path,out);return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--worker',nargs=2);ap.add_argument('--max-controls',type=int);args=ap.parse_args()
    if args.worker:
        cfg=json.loads(Path(args.worker[0]).read_text());outcome(cfg,Path(args.worker[1]));return
    designs=json.loads((U/'02_PROTOCOL/REGISTERED_SYSTEM_DESIGNS.json').read_text());D=U/'03_SYSTEM_V3/RUNS';D.mkdir(parents=True,exist_ok=True)
    processed=0
    for base in designs:
        previous=None
        for state in ('old','new'):
            cfg=dict(base,state=state)
            if state=='new':
                near=previous.get('stages',{}).get('economic_exclusive',{}).get('nearby_exact',{})
                if near.get('status')!='sat' or not near.get('independent_exact_native',{}).get('pass_all'):
                    save(D/(cfg['case_id']+'_new.json'),dict(input=cfg,status='INAPPLICABLE_UPDATE',reason='No verified exclusive first action'));continue
                # Energy is last24 coordinates; consume the first exclusive action.
                cfg['e0']=near['vector'][-24];cfg['update_source']='old economic exclusive nearby exact trajectory interval1'
            name=cfg['case_id']+'_'+state;target=D/(name+'.json');inp=D/(name+'_INPUT.json')
            if not inp.exists():save(inp,cfg)
            else:assert json.loads(inp.read_text())==cfg
            if target.exists() and json.loads(target.read_text()).get('status')!='RUNNING':
                previous=json.loads(target.read_text());continue
            env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
            try:
                p=subprocess.Popen([sys.executable,'-B',__file__,'--worker',str(inp),str(target)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8')
                try:stdout,stderr=p.communicate(timeout=240)
                except subprocess.TimeoutExpired:
                    if os.name=='nt':subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True)
                    else:p.kill()
                    stdout,stderr=p.communicate();(D/(name+'.stdout.txt')).write_text(stdout,encoding='utf-8');(D/(name+'.stderr.txt')).write_text(stderr,encoding='utf-8');raise
                (D/(name+'.stdout.txt')).write_text(stdout,encoding='utf-8');(D/(name+'.stderr.txt')).write_text(stderr,encoding='utf-8')
                if p.returncode:raise RuntimeError(stderr)
                previous=json.loads(target.read_text());print(name,previous['status'],previous.get('global_query',{}).get('relation',previous.get('global_query',{}).get('status')),round(previous.get('wall_seconds',0),2),flush=True)
            except (subprocess.TimeoutExpired,RuntimeError) as err:
                previous=json.loads(target.read_text()) if target.exists() else dict(input=cfg)
                previous['status']='PROCESS_TIMEOUT' if isinstance(err,subprocess.TimeoutExpired) else 'ERROR';previous['error']=str(err);save(target,previous);print(name,previous['status'],flush=True)
        processed+=1
        if args.max_controls and processed>=args.max_controls:
            save(U/'03_SYSTEM_V3/CONTROLLED_STOP.json',dict(controls_completed=processed,requested_exit=75));sys.exit(75)
    save(U/'03_SYSTEM_V3/QUEUE_COMPLETE.json',dict(controls=8,no_more_cases_authorized=True,background_worker=False))
if __name__=='__main__':main()
