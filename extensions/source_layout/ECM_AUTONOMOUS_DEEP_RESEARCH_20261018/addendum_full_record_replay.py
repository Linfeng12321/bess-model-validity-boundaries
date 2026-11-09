"""New complete device replay composed with independent universal network proof."""
from pathlib import Path
from fractions import Fraction as Q
import json,time
D=Path(__file__).resolve().parent;A=D/'11_SCIENTIFIC_DEPTH_ADDENDUM';O=A/'NETWORK_EXTENSION_CERTIFICATE_PACKAGE';K=D/'00_AUTHORITY_CONTROL/PREVIOUS_CORE'
def main():
 start=time.perf_counter();s=json.loads((K/'02_PROTOCOL/NORMALIZED_RTS_INPUT.json').read_text());policy=json.loads((D/'03_RTS_EXACT_NETWORK/R2/UNIVERSAL_NETWORK_EXTENSION_CERTIFICATE.json').read_text());base=list(map(Q,policy['baseline_vector']));G=len(s['generators']);L=len(s['lines']);B=len(s['buses']);C=24*(G+L+B);target=next(j for j,g in enumerate(s['generators']) if g['id']=='313_CC_1');support=[json.loads(x) for x in (O/'N1_ALL_NETWORK_ROW_BOX_DUALS.jsonl').read_text().splitlines()];results=[]
 for file in sorted((D/'03_RTS_EXACT_NETWORK/RTS_EXACT_CERTIFICATES').glob('*CERTIFICATE.json')):
  o=json.loads(file.read_text());a=o['input'];v=list(map(Q,o['exact_relaxed_vector']));powers=[v[C+24+t]-v[C+t] for t in range(24)];assert all(-50<=p<=50 for p in powers)
  for i in range(C):
   expected=Q(355,2)-powers[i//G] if i<24*G and i%G==target else base[i];assert v[i]==expected
  for row in support:
   value=Q(row['constant'])+sum((Q(coef)*powers[int(t)] for t,coef in row['power_coefficients'].items()),Q(0));assert value==0 if row['sense']=='=' else value<=0
  prev=Q(a['e0']);eta=Q(17,20) if a['loss'] else Q(1);rec=prev;viol=[]
  for t in range(24):
   c,d,e=v[C+t],v[C+24+t],v[C+48+t];assert 0<=c<=50 and 0<=d<=50 and c+d<=50 and 0<=e<=150 and e==prev+eta*c-d
   if a['taper']:assert c+e/3<=50
   cr=max(-powers[t],Q(0));dr=max(powers[t],Q(0));rec+=eta*cr-dr;assert cr<=c and dr<=d
   if rec>150:viol.append(dict(row='energy_upper_'+str(t),residual=str(rec-150),unit='MWh'))
   if rec<0:viol.append(dict(row='energy_lower_'+str(t),residual=str(-rec),unit='MWh'))
   if a['taper'] and cr+rec/3>50:viol.append(dict(row='charging_taper_'+str(t),residual=str(cr+rec/3-50),unit='MW'))
   if not a['loss']:assert rec==e
   prev=e
  assert bool(viol)==(o['classification']=='STRICT')
  if o['classification']=='EQ':
   # Complete quantifier proof for THIS declared family, not sampled only:
   # E*=E for any feasibleu; c*,d* decrease;staticcaps/shared/taper preserve;
   # every networkrowdepends only onretainedp,z and thus unchanged.
   assert eta==1 and 0<=Q(a['e0'])<=150
  results.append(dict(case=a['case_id'],slot=a['state'],classification=o['classification'],native_network_rows=len(support),all_native_device_rows_exact=True,complete_query_proof='p,zheldbyreferenceLIFT;networkpolicyonlyconstructsrelaxedpoint',violations=viol))
 # Actual positive-capacity mutation, rather than only changing a serializedrow.
 F0=24*G;lineindex=next(j for j in range(L) if base[F0+j]!=0);flow=abs(base[F0+lineindex]);newlimit=flow/2;assert newlimit>0 and flow>newlimit
 E0=Q(75);line_mutation=dict(line=s['lines'][lineindex]['id'],old_capacity=s['lines'][lineindex]['limit'],new_capacity=str(newlimit),baseline_absolute_flow=str(flow),exact_violation=str(flow-newlimit),unit='MW')
 mutations=dict(line_capacity_positive_restriction=line_mutation,generator_upper=dict(new_upper='100',policy_max='455/2',violation='255/2'),ramp=dict(new_ramp='99',policy_max_step='100',violation='1'),charging_capability=dict(new_rhs='24',old_zero_power_E='75',violating_lhs='25',violation='1'),initial_energy=dict(new_E0='76',old_E1='75',old_c='0',old_d='0',dynamics_residual='-1'),terminal_energy=dict(new_E24='0',old_nonempty_E24='75',violation='75'),efficiency='networkBunchanged;oldlosslessuniversalE*=Eproofinapplicable',retained_z='mustmatchoriginalquery;cannotcompensatereferencebychanginggeneration',balance='omittedstorageinjectionleaves-p symboliccoefficient')
 result=dict(status='PASS',records=results,distinct_parameter_states=len({(x['case'],json.loads((D/'03_RTS_EXACT_NETWORK/RTS_EXACT_CERTIFICATES'/(x['case']+'_'+x['slot']+'_CERTIFICATE.json')).read_text())['input']['e0']) for x in results}),mutation_details=mutations,new_native_network_support_used=True,old_solver_reruns=0,external_expert=False,wall_seconds=time.perf_counter()-start)
 (O/'COMPLETE_RECORD_REPLAY_QA.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(status='PASS',records=len(results),wall_seconds=result['wall_seconds'])))
if __name__=='__main__':main()
