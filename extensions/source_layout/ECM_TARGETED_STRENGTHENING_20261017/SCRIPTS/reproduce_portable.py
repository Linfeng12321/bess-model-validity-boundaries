from pathlib import Path
import argparse,sys,json,time,hashlib,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(Path(__file__).resolve().parent))
def main():
    p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');p.add_argument('--run-minimal',action='store_true');p.add_argument('--deny-root');a=p.parse_args()
    # Relocation QA may actively deny reads/writes to the original research tree.
    if a.deny_root:
        deny=Path(a.deny_root).resolve();runtime=Path(sys.prefix).resolve()
        def guard(event,args):
            if event!='open' or not isinstance(args[0],(str,bytes)):return
            try:q=Path(os.fsdecode(args[0])).resolve()
            except (OSError,ValueError):return
            if q.is_relative_to(deny) and not q.is_relative_to(ROOT) and not q.is_relative_to(runtime):raise PermissionError('Original project access denied: '+str(q))
        sys.addaudithook(guard)
    start=time.perf_counter();manifest=json.loads((ROOT/'CORE_MANIFEST.json').read_text(encoding='utf-8'))
    for rel,expected in manifest['files'].items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==expected,rel
    from audit_exact_results import main as audit_cert
    audit_cert()
    if a.run_minimal:
        from certification_routes import certify,verify_eq
        from independent_native import verify_strict
        from run_system_study import outcome
        reg=json.loads((ROOT/'04_CERTIFICATION/REGISTERED_CERTIFICATION_INPUTS.json').read_text(encoding='utf-8'));case=next(r['input'] for r in reg['all_unresolved'] if r['input']['eta_c']!='1');cert=certify(case,30)
        if cert['status']=='EQ':verify_eq(cert['proof'])
        elif cert['status']=='STRICT':assert verify_strict(case,cert['proof']['relaxed_vector'])['certified']
        assert cert['status'] in ['EQ','STRICT']
        cases=json.loads((ROOT/'03_SYSTEM_CASE/REGISTERED_SYSTEM_CASES.json').read_text(encoding='utf-8'))['cases'];cfg=dict(next(c for c in cases if c['case_id']=='PUBLIC_FIRST_FOUR_BOX_E4of5'),state='old');result=outcome(cfg);assert result['status']=='COMPLETED';assert result['exact_costs_agree'];assert not result['service']['relaxed']['reconstructed_check']['pass_all']
        (ROOT/'06_INDEPENDENT_QA/PORTABLE_FRESH_MINIMAL_RESULTS.json').write_text(json.dumps(dict(certificate=cert,system=result),indent=2),encoding='utf-8')
    report=dict(status='PASS',mode='fresh minimal solve and full saved certificate check' if a.run_minimal else 'saved certificate exact arithmetic; no optimization',protected_project_access_denied=bool(a.deny_root),manifest_files=len(manifest['files']),relocated_root=str(ROOT),wall_seconds=time.perf_counter()-start)
    (ROOT/'06_INDEPENDENT_QA/PORTABLE_ENTRY_QA.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
