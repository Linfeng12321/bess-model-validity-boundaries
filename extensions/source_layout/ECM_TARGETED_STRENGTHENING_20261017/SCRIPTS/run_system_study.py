from pathlib import Path
from fractions import Fraction as F
import json,csv,argparse,time,hashlib,os,copy,datetime
from system_model import numerical,exact_optimum,check,reconstruct,counterquery
W=Path(__file__).resolve().parents[1];D=W/'03_SYSTEM_CASE';D.joinpath('RESULTS').mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,obj):
    tmp=path.with_suffix('.partial');tmp.write_text(json.dumps(obj,indent=2),encoding='utf-8');os.replace(tmp,path)
def outcome(cfg):
    out=dict(input=cfg,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),implementation_sha256=sha(W/'SCRIPTS/system_model.py'));begin=time.perf_counter();economic={};service={}
    for exclusive in [False,True]:
        key='exclusive' if exclusive else 'relaxed';nu=numerical(cfg,exclusive);ex=exact_optimum(cfg,exclusive)
        assert nu['success'],(cfg['case_id'],nu)
        if ex['status']!='sat' or not ex.get('primary_optimum_certified'):
            out.update(status='EXACT_OPTIMUM_UNRESOLVED',failed_object=key,numerical=nu,exact=ex,wall_seconds=time.perf_counter()-begin);return out
        own=check(cfg,ex['vector'],exclusive);assert own['pass_all']
        assert abs(float(F(ex['cost']))-nu['objective'])<1e-6*max(1,abs(nu['objective']))
        rec=reconstruct(cfg,ex['vector']);lift=check(cfg,rec,True)
        economic[key]=dict(numerical=nu,exact=ex,native_check=own,reconstructed_vector=rec,reconstructed_check=lift)
    out['economic']=economic;er=F(economic['relaxed']['exact']['cost']);ee=F(economic['exclusive']['exact']['cost']);assert er<=ee
    out['exact_cost_gap']=str(ee-er);out['exact_costs_agree']=ee==er
    budget=ee*F(101,100);out['service_budget']=str(budget)
    for exclusive in [False,True]:
        key='exclusive' if exclusive else 'relaxed';nu=numerical(cfg,exclusive,objective='service',budget=budget);ex=exact_optimum(cfg,exclusive,service_budget=budget)
        if not nu['success'] or ex['status']!='sat' or not ex.get('primary_optimum_certified') or not ex.get('secondary_optimum_certified'):
            service[key]=dict(status='UNRESOLVED',numerical=nu,exact=ex);continue
        own=check(cfg,ex['vector'],exclusive);assert own['pass_all'];assert F(ex['cost'])<=budget
        assert abs(float(F(ex['service_objective']))-nu['objective'])<1e-6
        rec=reconstruct(cfg,ex['vector']);lift=check(cfg,rec,True);service[key]=dict(status='CERTIFIED_OPTIMAL_VALUES',numerical=nu,exact=ex,native_check=own,reconstructed_vector=rec,reconstructed_check=lift)
    out['service']=service
    out['global_query_check']=counterquery(cfg)
    out['economic_optimal_face_check']=counterquery(cfg,{'cost':str(er)})
    if service.get('relaxed',{}).get('status')=='CERTIFIED_OPTIMAL_VALUES':out['service_optimal_face_check']=counterquery(cfg,{'budget':str(budget),'service':service['relaxed']['exact']['service_objective']})
    out.update(status='COMPLETED',wall_seconds=time.perf_counter()-begin)
    return out
def summary_row(obj):
    c=obj['input'];r=dict(case_id=c['case_id'],profile=c['profile'],device=c['device'],e0=c['e0'],eta_c=c['eta_c'],eta_d=c['eta_d'],state=c.get('state','old'),status=obj['status'],wall_seconds=obj['wall_seconds'])
    if obj['status']=='COMPLETED':
        eq=obj['economic'];sv=obj['service'];r.update(relaxed_cost=eq['relaxed']['exact']['cost'],exclusive_cost=eq['exclusive']['exact']['cost'],cost_gap=obj['exact_cost_gap'],costs_agree=obj['exact_costs_agree'],economic_selected_request_realisable=eq['relaxed']['reconstructed_check']['pass_all'],complete_query_relation={'sat':'STRICT','unsat':'EQ','unknown':'UNRESOLVED'}[obj['global_query_check']['status']],bad_economic_optimal_query_exists=obj['economic_optimal_face_check']['status'])
        if all(sv.get(k,{}).get('status')=='CERTIFIED_OPTIMAL_VALUES' for k in ['relaxed','exclusive']):r.update(relaxed_service_net_charge=str(-F(sv['relaxed']['exact']['service_objective'])),exclusive_service_net_charge=str(-F(sv['exclusive']['exact']['service_objective'])),service_selected_request_realisable=sv['relaxed']['reconstructed_check']['pass_all'],bad_service_optimal_query_exists=obj.get('service_optimal_face_check',{}).get('status'))
    return r
def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['pilot','context'],required=True);args=p.parse_args();registered=json.loads((D/'REGISTERED_SYSTEM_CASES.json').read_text());cases=[c for c in registered['cases'] if c['stage']==('PILOT' if args.stage=='pilot' else 'CONTEXT_EXTENSION')]
    if args.stage=='context':assert json.loads((D/'PILOT_SUMMARY.json').read_text())['decision_evidence_gain']
    start=time.perf_counter();rows=[];gain=False
    for cfg in cases:
        cfg=dict(cfg,state='old');path=D/'RESULTS'/(cfg['case_id']+'_old.json')
        if path.exists():old=json.loads(path.read_text());assert old['input']==cfg
        else:old=outcome(cfg);save(path,old)
        rows.append(summary_row(old));print(json.dumps(rows[-1]),flush=True)
        if old['status']=='COMPLETED':
            gain|=F(old['exact_cost_gap'])!=0 or not old['economic']['relaxed']['reconstructed_check']['pass_all']
            sv=old['service']
            if all(sv.get(k,{}).get('status')=='CERTIFIED_OPTIMAL_VALUES' for k in ['relaxed','exclusive']):gain|=F(sv['relaxed']['exact']['service_objective'])!=F(sv['exclusive']['exact']['service_objective']) or not sv['relaxed']['reconstructed_check']['pass_all']
            # A feasible exclusive first action updates only initial energy; fixed same request profile.
            original=old['economic']['exclusive']['exact']['vector'];e1=original[11*cfg['T']];newcfg=dict(cfg,e0=e1,state='new',paired_initial_state=cfg['e0']);newpath=D/'RESULTS'/(cfg['case_id']+'_new.json')
            if newpath.exists():new=json.loads(newpath.read_text());assert new['input']==newcfg
            else:new=outcome(newcfg);new['state_update_source']=dict(reference_case=cfg['case_id'],action_c=original[9*cfg['T']],action_d=original[10*cfg['T']],new_e0=e1,feasible_reference_trajectory_checked=True);save(newpath,new)
            rows.append(summary_row(new));print(json.dumps(rows[-1]),flush=True)
    with (D/(args.stage.upper()+'_RESULTS.csv')).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
    summary=dict(stage=args.stage,paired_settings=len(cases),state_assessments=len(rows),completed=sum(r['status']=='COMPLETED' for r in rows),decision_evidence_gain=gain,extension_permitted=gain if args.stage=='pilot' else False,wall_seconds=time.perf_counter()-start,original_frozen_witnesses_used_as_system_inputs=0)
    save(D/(args.stage.upper()+'_SUMMARY.json'),summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
