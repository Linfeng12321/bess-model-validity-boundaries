"""Read saved evidence using standard-library exact arithmetic; never invoke a solver."""
from pathlib import Path
from fractions import Fraction as F
import json,csv,sys,importlib.util,collections,argparse,hashlib
ROOT=Path(__file__).resolve().parent
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'code'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def csvrows(name):
    with (ROOT/'data'/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def jsonlines(name):
    with (ROOT/'data'/name).open(encoding='utf-8') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def generic_check(model,x):
    vals=list(map(F,x));T=model['T'];e=F(model['e0']);cc=[];dd=[];es=[]
    for t in range(T):
        c=max(vals[t]-vals[T+t],F(0));d=max(vals[T+t]-vals[t],F(0));cc.append(c);dd.append(d)
        e=F(model['rho'])*e+F(model['h'])*(F(model['eta_c'])*c-d/F(model['eta_d'])-F(model['aux']));es.append(e)
    lifted=cc+dd+es
    def residual(row,vec):return sum((F(a)*vec[int(k)] for k,a in row['co'].items()),F(0))-F(row['rhs'])
    assert all(residual(row,vals)<=0 for row in model['rows'])
    assert all(residual(row,vals)==0 for row in model['eq'])
    assert all(vals[T+t]-vals[t]==lifted[T+t]-lifted[t] for t in range(T))
    assert all(cc[t]*dd[t]==0 for t in range(T))
    bad=[row['name'] for row in model['rows'] if residual(row,lifted)>0]
    bad+=[row['name'] for row in model['eq'] if residual(row,lifted)!=0]
    assert bad
    return lifted,len(model['rows'])+len(model['eq']),bad
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path);args=parser.parse_args()
    internal=module('internal_model');external=module('external_mapping')
    states=csvrows('Internal_Assessments.csv');pairs=csvrows('Internal_Pairs.csv');ext=csvrows('External_Assessments.csv');instances=csvrows('External_Instances.csv')
    assert len(states)==936 and len(pairs)==468 and len(ext)==3772 and len(instances)==34
    counts=collections.Counter(x['exact_status'] for x in states);assert counts=={'EQ':277,'STRICT':331,'TIMEOUT':152,'NOT_APPLICABLE':176}
    extcounts=collections.Counter(x['classification'] for x in ext);assert extcounts=={'EQ':113,'STRICT':3659}
    insaved={d['input']['case_id']:d for d in jsonlines('Internal_Saved_States.jsonl')};assert len(insaved)==936
    native_checked=0;internal_witnesses=0
    for case,d in insaved.items():
        if d['classification']!='STRICT':continue
        candidates=list(d.get('witnesses',[]))
        for route in d['routes'].values():
            candidates+=route.get('witnesses',[])
            if route.get('witness'):candidates.append(route['witness'])
        w=next(x for x in candidates if x.get('certified'));m=internal.build(d['input']);v=internal.verify_witness(m,w['relaxed_vector'])
        assert v['certified'] and v['relaxed_native_pass'] and v['exclusive_pass']
        assert v['recovered_vector']==w['recovered_vector'];native_checked+=len(m['rows'])+len(m['eq']);internal_witnesses+=1
    flips=0
    for pair in pairs:
        if pair['old']=='EQ' and pair['new']=='STRICT':
            assert insaved[pair['old_case_id']]['classification']=='EQ';assert insaved[pair['new_case_id']]['classification']=='STRICT';flips+=1
    assert flips==64
    external_witnesses=0;records=0;external_eq_records=0
    for d in jsonlines('External_Saved_States.jsonl'):
        records+=1;job=d['input'];result=d['result'];p=job['parameters'];model=external.build(p,job['e0'])
        if p.get('terminal')=='fixed_floor':model['rows'].append(external.row('terminal_floor','TERMINAL_LOWER',p['T']-1,{3*p['T']-1:-1},-F(p['terminal_floor'])))
        if result['classification']=='STRICT':
            w=next(x for x in result['witnesses'] if x.get('certified'));lifted,n,bad=generic_check(model,w['relaxed_vector']);assert list(map(str,lifted))==w['recovered_vector'];native_checked+=n;external_witnesses+=1
        else:
            # Preserve the saved exact equality certificate. This audit does not rerun an UNSAT proof.
            assert result['classification']=='EQ';external_eq_records+=1
        if records%500==0:print('External saved records checked',records,flush=True)
    assert records==3772 and external_witnesses==3659 and external_eq_records==113
    directional=csvrows('Directional_Objective_Values.csv');zeros={}
    for energy in [F(41,50),F(9,10),F(1)]:
        rr=[x for x in directional if F(x['state_id'])==energy];assert len(rr)==8
        assert all(F(x['gap_exact_MW'])>=0 for x in rr);zeros[str(energy)]=sum(F(x['gap_exact_MW'])==0 for x in rr)
    assert list(zeros.values())==[8,7,5]
    windows=csvrows('Measured_Window_Summaries.csv');assert len(windows)==9
    assert sum(int(x['timestamps']) for x in windows)==14121
    assert sum(int(x['unique_physical_state_tuples']) for x in windows)==7729
    assert all(x['full_queries_evaluated']=='0' for x in windows)
    simulation=csvrows('Source_Driven_Simulation.csv');assert len(simulation)==507
    assert len({x['complete_model_state_hash'] for x in simulation})==86
    simulated_witnesses=0
    for d in jsonlines('Simulation_Saved_States.jsonl'):
        job=d['input'];result=d['result'];assert result['classification']=='STRICT'
        m=external.build(job['parameters'],job['e0']);w=next(x for x in result['witnesses'] if x.get('certified'))
        y,n,bad=generic_check(m,w['relaxed_vector']);assert list(map(str,y))==w['recovered_vector'];simulated_witnesses+=1
    assert simulated_witnesses==86
    grid=json.loads((ROOT/'data/Boundary_Grid_Checks.json').read_text());assert len(grid)==330
    domain=json.loads((ROOT/'data/Boundary_Quantified_Results.json').read_text());assert sum(len(v['checks']) for v in domain.values())==12
    assert all(x['status']=='unsat' for v in domain.values() for x in v['checks'].values())
    query=csvrows('Temporal_Query_Classifications.csv');assert len(query)==65
    hull=json.loads((ROOT/'data/Exact_Hull_Constructions.json').read_text());controls=0
    for rec in hull['records']:
        inp=dict(T=2,eta_c=rec['eta_c'],h='1/4',effective_initial_energy=rec['current_state_MWh'],row_form='N');m=internal.build(inp)
        for endpoint in rec['two_physical_components']:
            fl=endpoint['flows'];vec=[F(v[0]) for v in fl]+[F(v[1]) for v in fl]+list(map(F,endpoint['states']))
            assert all(internal.value(row,vec)<=0 for row in m['rows']);assert all(internal.value(row,vec)==0 for row in m['eq'])
        de=F(1,4)*(1-F(rec['eta_c']))*F(rec['amplitude_MW'])/2
        assert F(50,3)*de==F(rec['native_power_violation_MW']);controls+=1
    assert controls==9
    # Historical content interfaces preserve existing objects, not new state assessments.
    profile_records=profile_fields=0
    for name,expected in [('Source_Screening_Descriptions.json',59),('Device_Mapping_Descriptions.json',34),('Operational_Source_Descriptions.json',39)]:
        profile=json.loads((ROOT/'data'/name).read_text(encoding='utf-8'))
        assert profile['record_count']==len(profile['records'])==expected
        assert len(profile['source_sha256'])==64
        assert all(r['legacy_heading'] and r['fields'] for r in profile['records'])
        profile_records+=expected;profile_fields+=sum(len(r['fields']) for r in profile['records'])
    assert profile_records==132 and profile_fields==1493
    assert len(csvrows('Historical_Computational_Settings.csv'))==32
    lookup=csvrows('Two_Interval_Control_Lookup.csv')
    older={r['case_id']:r for r in json.loads((ROOT/'data/Two_Interval_Control_Records.json').read_text(encoding='utf-8'))}
    regression={r['case_id']:r for r in csvrows('Regression_Assessments.csv')}
    assert len(lookup)==len(older)==9 and len(regression)==72
    for r in lookup:
        old=older[r['case_id']];saved=old['saved_record']['new'];reg=regression[r['generalized_regression_case_id']]
        assert old['original_sha256']==r['source_sha256']
        assert F(saved['e0_MWh'])==F(r['new_e0_MWh'])==F(reg['effective_initial_energy'])
        assert F(saved['eta_c'])==F(r['eta_c'])==F(reg['eta_c'])
        assert F(saved['step_hours'])==F(reg['interval_duration'])
        assert saved['row_form']==r['row_form']==reg['row_form']
        assert saved['SOC_pass_power_fail_smt']==r['saved_SOC_pass_power_fail_smt']
        assert abs(max(0,1000*float(saved['lp_max_SOC_valid_power_excess_MW']))-float(r['display_positive_part_kW']))<1e-10
    lossless=csvrows('Lossless_Control_Factor_Lookup.csv');assert len(lossless)==312
    state_by_id={r['case_id']:r for r in states}
    assert len({r['case_id'] for r in lossless})==312
    for r in lossless:
        assert F(r['eta_c'])==1
        assert all(state_by_id[r['case_id']][k]==v for k,v in r.items())
    assert collections.Counter(r['exact_status'] for r in lossless)=={'EQ':144,'TIMEOUT':104,'NOT_APPLICABLE':64}
    report={'saved_record_audit':'PASS','internal_states':936,'external_states':3772,'paired_settings':468,'certified_transitions_preserved':64,'internal_saved_native_witnesses_rechecked':internal_witnesses,'external_saved_native_witnesses_rechecked':external_witnesses,'saved_external_EQ_records_preserved_not_resolved_again':external_eq_records,'relaxed_native_rows_checked':native_checked,'directional_zero_gaps':zeros,'measured_windows':9,'measured_timestamps':14121,'measured_physical_tuple_count_from_frozen_summaries':7729,'simulated_timestamps':507,'complete_simulated_model_states':86,'simulated_saved_witnesses_rechecked':simulated_witnesses,'saved_quantified_results_preserved':12,'temporal_query_classifications':65,'saved_hull_controls':9,'solver_calls':0,'new_scientific_cases':0}
    report.update(historical_profile_records=profile_records,historical_profile_fields=profile_fields,historical_setting_rows=32,earlier_T2_controls_matched_to_existing_regression=9,lossless_factor_rows=312)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
