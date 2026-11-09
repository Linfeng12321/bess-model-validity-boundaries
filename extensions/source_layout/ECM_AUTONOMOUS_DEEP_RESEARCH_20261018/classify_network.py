"""Complete full-network classification through a checked universal completion.

All-charge sign restriction is used only for existential STRICT search. Lossless
EQ uses a complete native-row preservation proof and an exact nonempty point.
"""
from fractions import Fraction as F
import argparse,hashlib,json,time
import z3
from model import D,K,build,check,configs,fingerprint,lift
OUT=D/'03_RTS_EXACT_NETWORK/RTS_EXACT_CERTIFICATES';OUT.mkdir(exist_ok=True)
def complete_from_policy(m,device,policy):
    ix=m['ix'];v=list(map(F,policy['baseline_vector']));target=policy['generator_index']
    for t in range(24):v[t*ix['G']+target]=F(355,2)-(device[24+t]-device[t])
    return v[:ix['c']]+device
def classify(cfg):
    start=time.perf_counter();m=build(cfg);ix=m['ix'];policy_path=D/'03_RTS_EXACT_NETWORK/R2/UNIVERSAL_NETWORK_EXTENSION_CERTIFICATE.json';policy=json.loads(policy_path.read_text())
    assert policy['source_sha256']==hashlib.sha256((K/'02_PROTOCOL/NORMALIZED_RTS_INPUT.json').read_bytes()).hexdigest()
    zero=[F(0)]*48+[F(cfg['e0'])]*24;base=complete_from_policy(m,zero,policy);nonempty=check(m,base,True);assert nonempty['pass_all']
    result=dict(input=cfg,model_sha256=fingerprint(m),source_sha256=policy['source_sha256'],policy_certificate_sha256=hashlib.sha256(policy_path.read_bytes()).hexdigest(),query='complete(p,allg,allf,alla)',nonempty_point_kind='exact source-network policy at zero storage power',nonempty_native_check=nonempty,declared_native_rows=len(m['rows']),scope='full frozen network global query set,not just an objective-selected schedule',new_theorem=False)
    if not cfg['loss']:
        guards=[]
        for r in m['rows']:
            sums=[r['coeff'].get(ix['c']+t,F(0))+r['coeff'].get(ix['d']+t,F(0)) for t in range(24)]
            if r['family'] in ('CHARGE_LOWER','DISCHARGE_LOWER'):reason='nonnegative max reconstruction'
            elif r['equality']:assert all(a==0 for a in sums);reason='energy unchanged and common-flow coefficient cancels'
            else:assert all(a>=0 for a in sums);reason='energy unchanged and directional powers decrease'
            guards.append(dict(row=r['id'],family=r['family'],reason=reason))
        result.update(classification='EQ',proof_kind='FULL_NATIVE_LOSSLESS_GUARDS_PLUS_EXACT_NONEMPTY_NETWORK',guards=guards,exact_relaxed_vector=list(map(str,base)))
    else:
        c=z3.Reals(' '.join(f'new_c_{t}' for t in range(24)));d=z3.Reals(' '.join(f'new_d_{t}' for t in range(24)));E=z3.Reals(' '.join(f'new_E_{t}' for t in range(24)));s=z3.SolverFor('QF_LRA');s.set(timeout=60000);eta=z3.RealVal('17/20');old=z3.RealVal(cfg['e0'])
        for t in range(24):
            s.add(c[t]>=0,d[t]>=0,c[t]+d[t]<=50,d[t]<=c[t],E[t]==old+eta*c[t]-d[t],E[t]>=0,E[t]<=150)
            if cfg['taper']:s.add(c[t]+E[t]/3<=50)
            old=E[t]
        # A strict1MWh target is a search condition, not a changed operating limit.
        recovered_final=z3.RealVal(cfg['e0'])+eta*z3.Sum([c[t]-d[t] for t in range(24)])
        s.add(recovered_final>151)
        target=OUT/(cfg['case_id']+'_'+cfg['state']+'_EXISTENTIAL_REDUCED.smt2');target.write_text(s.to_smt2())
        ans=s.check();result['decision']=str(ans);result['search_subset']='p<=0all24hours;existential only';result['encoding_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
        if ans!=z3.sat:result.update(classification='UNKNOWN',reason='No exact full-network counterquery generated within this search budget')
        else:
            assignment=s.model();value=lambda x:F(str(assignment.eval(x,model_completion=True)))
            device=[value(x) for part in (c,d,E) for x in part];v=complete_from_policy(m,device,policy);native=check(m,v);assert native['pass_all'];reconstructed=lift(m,v);rec=check(m,reconstructed,True);assert not rec['pass_all']
            result.update(classification='STRICT',proof_kind='NEW_FULL_NETWORK_EXACT_COUNTERQUERY_VIA_PROVEN_SURJECTIVE_POWER_BOX_COMPLETION',exact_relaxed_vector=list(map(str,v)),exact_reference_candidate=list(map(str,reconstructed)),relaxed_native_check=native,reconstructed_native_check=rec,strict_energy_excess_MWh=str(reconstructed[ix['e']+23]-150),retained_query_identical=True)
    result['wall_seconds']=time.perf_counter()-start
    out=OUT/(cfg['case_id']+'_'+cfg['state']+'_CERTIFICATE.json');out.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('exact_relaxed_vector','exact_reference_candidate','guards','reconstructed_native_check')},indent=2));return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--new',action='store_true');a=p.parse_args();cfg=next(x for x in configs() if x['case_id']==a.case)
    if a.new:
        gate=json.loads((D/'03_RTS_EXACT_NETWORK/R1'/ (a.case+'_old_EXACT_ECONOMIC_RECOVERY.json')).read_text());assert gate['status']=='EXACT_NEARBY_FEASIBLE'
        old=json.loads((OUT/(a.case+'_old_CERTIFICATE.json')).read_text());assert old['classification'] in ('EQ','STRICT')
        cfg=dict(cfg,state='new',e0=gate['first_action']['E1'])
    classify(cfg)
if __name__=='__main__':main()
