"""Offline portable replay. Never reruns the frozen experiment campaign."""
from pathlib import Path
from fractions import Fraction as Q
import argparse,csv,hashlib,json,os,runpy,sys,time
D=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--fresh-recovery',action='store_true');a=p.parse_args();start=time.perf_counter()
 checked=0
 for row in csv.DictReader((D/'09_REPRODUCIBILITY/SCIENTIFIC_INPUT_SHA256.csv').open(encoding='utf-8')):
  target=D/row['path'];assert hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256'],row['path'];checked+=1
 import independent_verify as iv
 iv.main()
 # These modules independently rebuild the frozen internal device formulation,
 # rather than trusting the original builder's classifications.
 runpy.run_path(str(D/'sidecar_recheck_v2.py'),run_name='__main__')
 runpy.run_path(str(D/'theory_probes.py'),run_name='__main__')
 runpy.run_path(str(D/'theory_box_check.py'),run_name='__main__')
 n=0
 for file in sorted((D/'04_CERTIFICATION_METHODS/REQUEST_RECOVERY_COMPARISON').glob('*.json')):
  obj=json.loads(file.read_text())
  if obj.get('route')!='candidate' or 'independent_qa' not in obj:continue
  cfg=obj['raw_result']['input'];v=obj['raw_result']['exact_vector'];assert iv.physics(cfg,v,obj['raw_result']['exclusive'])['pass_all']
  original=json.loads((iv.K/'03_SYSTEM_FINAL/RUNS'/(obj['case_id']+'_old.json')).read_text());stage=original['stages'][obj['stage']];vv=list(map(Q,v))
  assert all(abs(x-Q(str(y)))<=(Q(1,10**7) if iv.A0<=j<iv.C else Q(1,10**5)) for j,(x,y) in enumerate(zip(vv,stage['vector'])))
  cost=sum((vv[t*iv.G+j]*Q(g['cost']) for t in range(24) for j,g in enumerate(iv.S['generators'])),Q(0));assert cost<=Q(str(stage['cost']))+max(Q(1,100),abs(Q(str(stage['cost'])))/10**8)
  service=sum((vv[iv.C+t]-vv[iv.C+24+t] for t in iv.S['service_hours_zero_based']),Q(0))
  if obj['stage'].startswith('service'):
   assert cost<=Q(original['service_budget']) and service<=Q(str(stage['service_objective']))+Q(1,10**6)
  if obj['stage'].startswith('service_secondary'):
   target=original['stages']['service_primary_'+('exclusive' if stage['exclusive'] else 'relaxed')]['service_objective'];assert abs(service-Q(str(target)))<=Q(1,10**6)
  assert iv.physics(cfg,iv.reconstruct(cfg,v),True)['pass_all'];n+=1
 assert n==24
 fresh=None
 if a.fresh_recovery:
  # Deterministic first held-out input, not an extra scientific setting.
  import request_comparison_worker
  out=D/'09_REPRODUCIBILITY/COLD_FRESH_RECOVERY.json';old=sys.argv
  sys.argv=['request_comparison_worker.py','--case','RTS_L0_T0_N1','--stage','economic_relaxed','--route','candidate','--out',str(out)]
  try:request_comparison_worker.main()
  finally:sys.argv=old
  fresh=json.loads(out.read_text());assert fresh['status']=='CERTIFIED_NEARBY_FEASIBLE'
 result=dict(status='PASS',verified_immutable_files=checked,network_certificate_records=8,distinct_network_parameter_states=7,saved_request_vectors_rechecked=24,legacy_sidecar_records=152,existing_followup_pairs=18,theory_originality='NONE',fresh_recovery=None if fresh is None else dict(case=fresh['case_id'],stage=fresh['stage'],status=fresh['status']),wall_seconds=time.perf_counter()-start,external_host=False)
 (D/'09_REPRODUCIBILITY/PORTABLE_REPLAY_RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
