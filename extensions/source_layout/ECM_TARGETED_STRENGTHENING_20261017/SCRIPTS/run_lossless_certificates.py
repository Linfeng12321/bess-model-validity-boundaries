from pathlib import Path
from fractions import Fraction as F
import json,csv,hashlib,time,os
from independent_native import lossless_nonempty,verify_lossless_certificate
W=Path(__file__).resolve().parents[1];C=W/'04_CERTIFICATION';d=json.loads((C/'REGISTERED_CERTIFICATION_INPUTS.json').read_text());out=C/'M1_EXACT_CERTIFICATES';out.mkdir(exist_ok=True)
rows=[];reg=[];start=time.perf_counter()
for category,items in [('REGRESSION',d['regression']),('NEW_SIDECAR',d['all_unresolved'])]:
    for r in items:
        i=r['input'];begin=time.perf_counter();name=i['case_id']
        if F(i['eta_c'])!=1:
            if category=='REGRESSION':reg.append(dict(case_id=name,original_status=r['original_status'],method_status='INAPPLICABLE',false_classification=False))
            continue
        v,check=lossless_nonempty(i)
        if not check['pass_all']:raise RuntimeError('Lossless nonemptiness witness failed '+name)
        proof=dict(method='M1_LOSSLESS_NATIVE_PRESERVATION',model_contract='FROZEN_INTERNAL_N_G_V1',input=i,original_status=r['original_status'],new_status='EQ',original_source_sha256=r['source_sha256'],nonempty_vector=list(map(str,v)),covered_native_families=['flow_nonnegativity','shared_rating','energy_bounds','energy_dynamics','charge_start','charge_end','discharge_start','discharge_end'],argument='eta_c=eta_d=rho=1: removing commonflow preserves p andE; nonnegative powers reconstructed; sharedrating decreases; N rows unchanged; G leftpower decreases; complete listednative rows and bothdynamicdirections checked.')
        assert verify_lossless_certificate(proof)
        if category=='REGRESSION':assert r['original_status']=='EQ';reg.append(dict(case_id=name,original_status='EQ',method_status='EQ_CERTIFIED',false_classification=False))
        else:
            p=out/(name+'.json');text=json.dumps(proof,indent=2)
            if p.exists():assert p.read_text(encoding='utf-8')==text
            else:tmp=p.with_suffix('.partial');tmp.write_text(text,encoding='utf-8');os.replace(tmp,p)
            rows.append(dict(case_id=name,ORIGINAL_STATUS='TIMEOUT',NEW_STATUS='EQ',method='M1',horizon=i['T'],eta_c=i['eta_c'],row_form=i['row_form'],certificate_file=p.relative_to(W).as_posix(),certificate_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),wall_seconds=time.perf_counter()-begin,independent_exact_check='PASS'))
assert len(rows)==104,len(rows)
for name,rr in [('M1_NEW_CERTIFICATES.csv',rows),('M1_REGRESSION_RESULTS.csv',reg)]:
    with (C/name).open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
(C/'M1_SUMMARY.json').write_text(json.dumps(dict(new_exact_EQ=len(rows),original_statuses_unchanged=True,new_theorem_claimed=False,regression_checked=len(reg),false_classifications=0,wall_seconds=time.perf_counter()-start),indent=2),encoding='utf-8')
print((C/'M1_SUMMARY.json').read_text(encoding='utf-8'))
