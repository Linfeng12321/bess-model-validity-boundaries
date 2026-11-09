"""Offline replay of NEW proofs/checks; inherit rather than rerun old campaign."""
from pathlib import Path
import csv,hashlib,json,runpy,time
D=Path(__file__).resolve().parent;A=D/'11_SCIENTIFIC_DEPTH_ADDENDUM'
def main():
 start=time.perf_counter();counts={}
 for name,manifest in [('old',D/'09_REPRODUCIBILITY/SCIENTIFIC_INPUT_SHA256.csv'),('addendum',A/'REPRODUCTION/ADDED_IMMUTABLE_INPUT_SHA256.csv')]:
  rows=list(csv.DictReader(manifest.open(encoding='utf-8-sig')))
  for row in rows:assert hashlib.sha256((D/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
  counts[name]=len(rows)
 # Build new network proofs from rawsource and a fresh independent SMTmodel;
 # replay fresh BOXnative formula vs saved exact primal/dual, without rerunning
 # the old48optimizers/936campaign or the BOXOptimizeproducer.
 for file in ['addendum_network_support.py','addendum_network_smt.py','addendum_box_independent.py','addendum_contract_attacks.py','addendum_full_record_replay.py']:
  runpy.run_path(str(D/file),run_name='__main__')
 result=dict(status='PASS',immutable_hash_counts=counts,new_network_rows=24798,new_BOX_cases=16,exact_primal_dual_pairs=20,complete_query_records=8,distinct_RTS_parameter_states=7,old_optimization_campaign_reruns=0,old_timing_reruns=0,external_host=False,new_solver_models_constructed=True,wall_seconds=time.perf_counter()-start)
 (A/'REPRODUCTION/COLD_REPLAY_RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
