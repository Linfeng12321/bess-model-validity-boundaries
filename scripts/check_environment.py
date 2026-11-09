"""Report the minimal verification environment without importing scientific packages."""
import sys,json,argparse
def main():
    p=argparse.ArgumentParser(description=__doc__);p.parse_args()
    system='Windows' if sys.platform=='win32' else sys.platform
    print(json.dumps({'python':'.'.join(map(str,sys.version_info[:3])),'platform':system,'verification_dependencies':'Python standard library','tested_baseline':'Python3.12.14; Windows','this_platform_matches_tested_family':sys.version_info[:2]==(3,12) and sys.platform=='win32','scientific_packages_imported':False,'full_scientific_rerun':'NOT_RUN_BY_DESIGN'},indent=2))
if __name__=='__main__':main()
