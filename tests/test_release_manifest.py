"""Test the transport manifest with tiny text fixtures, never scientific samples."""
from pathlib import Path
import argparse,csv,hashlib,runpy,json
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work-dir',type=Path,required=True);a=p.parse_args()
    mini=a.work_dir.resolve();mini.mkdir(parents=True,exist_ok=True);(mini/'release_manifest').mkdir(exist_ok=True)
    ns=runpy.run_path(str(ROOT/'scripts/verify_release.py'),run_name='manifest_fixture_test')
    check=ns['check_manifest'];check.__globals__['ROOT']=mini
    f=mini/'tiny.txt';f.write_text('transport fixture',encoding='utf-8')
    row={'path':'tiny.txt','bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
    def manifest(rr):
        with (mini/'release_manifest/SHA256SUMS.csv').open('w',encoding='utf-8-sig',newline='') as h:
            w=csv.DictWriter(h,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(rr)
    def reject(fn):
        try:fn()
        except (AssertionError,ValueError,FileNotFoundError):return True
        return False
    manifest([row]);assert check()['files_checked']==1
    results=[{'test':'valid_tiny_manifest','pass':True}]
    bad=dict(row,sha256='0'*64);manifest([bad]);results.append({'test':'changed_digest_rejected','pass':reject(check)})
    bad=dict(row,path='missing.txt');manifest([bad]);results.append({'test':'missing_file_rejected','pass':reject(check)})
    bad=dict(row,path='../outside.txt');manifest([bad]);results.append({'test':'escaping_path_rejected','pass':reject(check)})
    manifest([row,row]);results.append({'test':'duplicate_manifest_member_rejected','pass':reject(check)})
    assert all(x['pass'] for x in results)
    (mini/'TEST_RESULTS.json').write_text(json.dumps({'tests':results,'scientific_data_modified':False,'scientific_solver_calls':0},indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
if __name__=='__main__':main()
