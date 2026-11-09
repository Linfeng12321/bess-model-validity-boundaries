"""Verify the fixed publication snapshot; never invoke a scientific solver."""
from pathlib import Path
import argparse,sys,json,runpy,contextlib,io,hashlib,csv,time
ROOT=Path(__file__).resolve().parents[1]

def check_manifest():
    p=ROOT/'release_manifest/SHA256SUMS.csv'
    if not p.is_file():
        return {'status':'NOT_PRESENT_DURING_ENGINEERING','files_checked':0}
    n=0;seen=set()
    with p.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            rel=Path(r['path']);assert not rel.is_absolute(),r['path']
            q=(ROOT/rel).resolve();q.relative_to(ROOT.resolve())
            assert r['path'] not in seen,r['path'];seen.add(r['path'])
            assert q.is_file() and q.stat().st_size==int(r['bytes']),r['path']
            assert hashlib.sha256(q.read_bytes()).hexdigest()==r['sha256'],r['path']
            n+=1
    return {'status':'PASS','files_checked':n}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir',type=Path,required=True)
    a=parser.parse_args();out=a.report_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    expected=json.loads((ROOT/'expected_outputs/REGRESSION_EXPECTATIONS.json').read_text(encoding='utf-8'))
    manifest=check_manifest();executed=[]
    commands=[
        ('canonical',ROOT/'verify_saved_records.py',['--report',str(out/'canonical.json')]),
        ('extensions',ROOT/'scripts/verify_extensions_saved.py',['--report-dir',str(out)]),
        ('rts_requests',ROOT/'scripts/verify_rts_requests_saved.py',['--report-dir',str(out)]),
        ('summary',ROOT/'scripts/summarize_saved.py',['--output',str(out/'display_summary.json')]),
        ('system',ROOT/'scripts/verify_system_saved.py',['--output',str(out/'system_saved.json')]),
    ]
    previous=sys.argv[:]
    for name,p,args in commands:
        start=time.perf_counter();capture=io.StringIO();sys.argv=[str(p)]+args
        try:
            with contextlib.redirect_stdout(capture):runpy.run_path(str(p),run_name='__main__')
        finally:
            sys.argv=previous
            (out/(name+'_stdout.txt')).write_text(capture.getvalue(),encoding='utf-8')
        executed.append({'step':name,'status':'PASS','seconds':time.perf_counter()-start})
        print(name+': PASS',flush=True)
    actual={
        'canonical':json.loads((out/'canonical.json').read_text(encoding='utf-8')),
        'extensions':json.loads((out/'extensions_saved_verification.json').read_text(encoding='utf-8')),
        'summary':json.loads((out/'display_summary.json').read_text(encoding='utf-8')),
        'system':json.loads((out/'system_saved.json').read_text(encoding='utf-8')),
    }
    for group in actual:
        for k,v in expected[group].items():assert actual[group][k]==v,(group,k)
    rts=json.loads((out/'rts_request_evidence_verification.json').read_text(encoding='utf-8'))
    assert rts['status']=='PASS'
    result={'status':'PASS','manifest':manifest,'steps':executed,'expected_frozen_values':'PASS','scientific_solver_calls':0,'new_cases':0,'full_scientific_rerun':'NOT_RUN_BY_DESIGN','scope':'Saved arithmetic/native checks and fixed summaries; preserved logical outcomes are not fresh UNSAT proofs'}
    (out/'RELEASE_VERIFICATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
