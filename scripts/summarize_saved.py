"""Recreate display summaries from frozen records; no optimization or new model states."""
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,defaultdict
from bisect import bisect_right
import csv,json,argparse,hashlib
ROOT=Path(__file__).resolve().parents[1]
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 states=rows(ROOT/'data/Internal_Assessments.csv');original=Counter(r['exact_status'] for r in states)
 later=rows(ROOT/'extensions/certification/152_EXISTING_CERTIFICATE_IDENTITIES.csv')
 assert len(later)==len({r['case_id'] for r in later})==152
 changes={r['case_id']:r['subsequent'] for r in later};byid={r['case_id']:r for r in states}
 for r in later:
  assert byid[r['case_id']]['exact_status']=='TIMEOUT'
  branch='M1_EXACT_CERTIFICATES' if r['method']=='M1' else 'CENSUS_RESULTS'
  f=ROOT/'extensions/source_layout/ECM_TARGETED_STRENGTHENING_20261017/04_CERTIFICATION'/branch/(r['case_id']+'.json')
  assert hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256']
  obj=json.loads(f.read_text());inp=obj['input'] if r['method']=='M1' else obj['proof']['input'];assert inp['case_id']==r['case_id']
 final=Counter(changes.get(r['case_id'],r['exact_status']) for r in states);assert final=={'EQ':426,'STRICT':334,'NOT_APPLICABLE':176}
 pairs=rows(ROOT/'data/Internal_Pairs.csv');oldpairs=Counter(r['old']+'/'+r['new'] for r in pairs)
 newpairs=Counter(changes.get(r['old_case_id'],r['old'])+'/'+changes.get(r['new_case_id'],r['new']) for r in pairs)
 assert len(pairs)==468 and oldpairs['EQ/STRICT']==64 and newpairs['EQ/STRICT']==82
 horizons=rows(ROOT/'extensions/certification/17_HORIZON_VERSION_ACCOUNTING.csv');assert len(horizons)==17
 for h in horizons:
  rr=[r for r in states if int(r['horizon_T'])==int(h['horizon'])];fin=Counter(changes.get(r['case_id'],r['exact_status']) for r in rr)
  assert len(rr)==int(h['assessments']) and fin['EQ']==int(h['final_EQ']) and fin['STRICT']==int(h['final_STRICT'])
 assert next(h for h in horizons if h['horizon']=='256')['final_EQ']=='8'
 ext=[];cats=Counter();instances=defaultdict(Counter);unique=set()
 with (ROOT/'data/External_Saved_States.jsonl').open(encoding='utf-8') as f:
  for line in f:
   d=json.loads(line);i=d['input'];r=d['result'];key=(i['parameters']['id'],F(i['e0']));assert key not in unique;unique.add(key)
   instances[i['parameters']['id']][r['classification']]+=1
   if r['classification']=='STRICT':
    w=next(x for x in r['witnesses'] if x.get('certified'));assert not w['SOC_pass']
    cats['energy_and_power' if w['power_fail'] else 'energy_only']+=1
   ext.append(r['classification'])
 assert len(instances)==34 and len(ext)==3772 and Counter(ext)=={'EQ':113,'STRICT':3659}
 assert cats=={'energy_and_power':329,'energy_only':3330}
 directional=rows(ROOT/'data/Directional_Objective_Values.csv');display=[]
 for r in directional:
  if F(r['state_id']) in [F(41,50),F(9,10),F(1)]:display.append(r)
 assert len(display)==24
 f9=ROOT/'extensions/source_layout/ECM_FIGURE9_STEP2D_REDESIGN_V2_20261023/01_SOURCE_AND_NUMERICAL_QA'
 system=rows(f9/'FIGURE9_26_STATE_SOURCE_MAPPING.csv');outcomes={}
 for k,col in [('economic','economic_optima_agree'),('service','service_primary_values_agree')]:
  equal=[r for r in system if r[col]=='TRUE'];bad=lambda rs:sum(r['selected_'+k+'_query_realisable']=='FALSE' for r in rs)
  outcomes[k]={'all':len(system),'unrealizable':bad(system),'equal_objective_states':len(equal),'unrealizable_with_equal_objective':bad(equal)}
 assert outcomes=={'economic':{'all':26,'unrealizable':16,'equal_objective_states':10,'unrealizable_with_equal_objective':0},'service':{'all':26,'unrealizable':17,'equal_objective_states':14,'unrealizable_with_equal_objective':5}}
 energy=rows(f9/'FIGURE9_SERVICE_ENERGY_EXACT.csv');excess=F(energy[-1]['violation_exact_kWh']);assert excess==F(4521359289,220281250)
 timing=rows(ROOT/'data/Repeated_Timing_Summaries.csv');assert len(timing)==108
 windows=rows(ROOT/'data/Measured_Window_Summaries.csv');assert len(windows)==9 and sum(int(r['timestamps']) for r in windows)==14121 and sum(int(r['unique_physical_state_tuples']) for r in windows)==7729
 # Verify the existing simulated action/energy rows against the actual frozen price input.
 raw=ROOT/'external_data/energinet/Elspotprices_DK1_2025_01.json';b=raw.read_bytes();assert hashlib.sha256(b).hexdigest()=='9da54c4e2b45bd8d780e3fdc23100d0b0151316a4d814eb9e483984c843725b7'
 prices=json.loads(b,parse_float=str)['records'];lookup={r['HourDK']:r for r in prices};cal=sorted(F(r['SpotPriceEUR']) for r in prices[:168]);sim=rows(ROOT/'data/Source_Driven_Simulation.csv');assert len(sim)==507
 for r in sim:
  e=F(r['energy_kWh']);c=F(r['charge_kW']);d=F(r['discharge_kW']);en=F(r['next_energy_kWh']);assert c*d==0 and F(30)<=e<=60 and F(30)<=en<=60
  endpoint=str(r['endpoint']).lower()=='true';price=None if endpoint else F(lookup[r['timestamp_local']]['SpotPriceEUR'])
  target=e if endpoint else F(30)+30*F(bisect_right(cal,price),len(cal))
  assert target==F(r['target_energy_kWh']) and c==min(F(20),max(F(0),(target-e)/F(9,10))) and d==min(F(20),max(F(0),(e-target)*F(19,20)))
  assert en==e+F(9,10)*c-d/F(19,20)
 summary={'original_classifications':dict(original),'cumulative_classifications':dict(final),'paired_settings':len(pairs),'original_pair_outcomes':dict(oldpairs),'cumulative_pair_outcomes':dict(newpairs),'horizons':horizons,'external_classifications':dict(Counter(ext)),'external_retained_witness_categories':dict(cats),'external_instances':{k:dict(v) for k,v in instances.items()},'directional_display_records':display,'system_requests':outcomes,'representative_service_excess_exact_kWh':str(excess),'representative_service_excess_display_kWh':float(excess),'measured_summary_windows':9,'measured_summary_timestamps':14121,'measured_summary_physical_tuples':7729,'measured_raw_tuple_recount':'NOT_PERFORMED; provider raw trajectories not redistributed','simulated_saved_timestamp_rows':507,'price_calibration_records':168,'price_response_records':len(prices),'solver_calls':0,'new_scientific_cases':0,'scope':'Display-level reconciliation of fixed saved evidence, not new statistics or classification changes.'}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(summary,indent=2),encoding='utf-8')
 print(json.dumps({'status':'PASS','original_states':len(states),'final_EQ':final['EQ'],'final_STRICT':final['STRICT'],'same_pairs':len(pairs),'EQ_to_STRICT':newpairs['EQ/STRICT'],'external_saved_witnesses':cats,'displayed_directions':len(display),'saved_simulation_rows_verified_against_frozen_prices':len(sim),'solver_calls':0},indent=2))
if __name__=='__main__':main()
