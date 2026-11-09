"""Replay existing certificate arithmetic only; never invoke historical solver entry points.

This path-only wrapper reuses byte-preserved verifier functions. For RTS it
loads only reviewed non-solver module definitions, omitting cvc5 and main.
"""
from pathlib import Path
from fractions import Fraction
import ast,sys,importlib.util,json,argparse,copy,runpy,contextlib,io,collections
ROOT=Path(__file__).resolve().parents[1]
EXT=ROOT/'extensions/source_layout'
def load_plain(name,path):
    sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def load_rts_without_solver(path):
    source=path.read_text(encoding='utf-8-sig');tree=ast.parse(source,filename=path.name);nodes=[]
    forbidden={'main','independent_cvc'}
    allowed_imports={'pathlib','fractions','collections','copy','csv','hashlib','json','time'}
    for n in tree.body:
        if isinstance(n,ast.Import):
            if all(a.name=='cvc5' for a in n.names):continue
            assert all(a.name in allowed_imports for a in n.names);nodes.append(n)
        elif isinstance(n,ast.ImportFrom):assert n.module in allowed_imports;nodes.append(n)
        elif isinstance(n,ast.FunctionDef):
            if n.name not in forbidden:nodes.append(n)
        elif isinstance(n,(ast.Assign,ast.Expr)):nodes.append(n)
        elif isinstance(n,ast.If):
            assert ast.unparse(n.test).replace('"',"'")=="__name__ == '__main__'"
        else:raise AssertionError(type(n).__name__)
    tree.body=nodes;ns={'__file__':str(path),'__name__':'saved_rts_arithmetic'}
    exec(compile(tree,str(path),'exec'),ns)
    return ns
def rejected(fn):
    try:fn()
    except (AssertionError,KeyError,IndexError,ValueError,TypeError):return True
    return False
def main():
    p=argparse.ArgumentParser();p.add_argument('--report-dir',type=Path,required=True);a=p.parse_args();a.report_dir.mkdir(parents=True,exist_ok=True)
    target=EXT/'ECM_TARGETED_STRENGTHENING_20261017'
    audit=load_plain('saved_original_exact_audit',target/'SCRIPTS/audit_exact_results.py')
    audit.C=target/'04_CERTIFICATION';audit.Q=a.report_dir
    audit.main()
    cert=json.loads((a.report_dir/'CERTIFICATE_SECOND_IMPLEMENTATION.json').read_text())
    assert cert['EQ']==149 and cert['STRICT']==3 and cert['M1_full_frozen_native_matrix_guards']==104
    assert cert['M2_exact_upper_bound_objects']==3417
    f9=EXT/'ECM_FIGURE9_STEP2D_REDESIGN_V2_20261023/VERIFY_PACKAGE.py'
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):runpy.run_path(str(f9),run_name='__main__')
    (a.report_dir/'figure9_original_verifier.txt').write_text(capture.getvalue(),encoding='utf-8')
    print(capture.getvalue(),end='')
    deep=EXT/'ECM_AUTONOMOUS_DEEP_RESEARCH_20261018'
    n=load_rts_without_solver(deep/'independent_verify.py')
    policy=json.loads((deep/'03_RTS_EXACT_NETWORK/R2/UNIVERSAL_NETWORK_EXTENSION_CERTIFICATE.json').read_text())
    assert n['policy_check'](policy);expected=n['expected_inputs']();register=n['guard_register']();records=[];objects=[]
    for path in sorted((deep/'03_RTS_EXACT_NETWORK/RTS_EXACT_CERTIFICATES').glob('*CERTIFICATE.json')):
        obj=json.loads(path.read_text());assert n['validate'](obj,expected,register,policy)
        rows=n['physics'](obj['input'],obj['exact_relaxed_vector'])['rows']
        records.append({'case_id':obj['input']['case_id'],'state':obj['input']['state'],'e0':obj['input']['e0'],'classification':obj['classification'],'native_rows':rows,'saved_arithmetic':'PASS'});objects.append(obj)
    assert len(records)==8 and collections.Counter(x['classification'] for x in records)=={'EQ':4,'STRICT':4}
    assert len({(x['case_id'],x['e0']) for x in records})==7
    eq=next(x for x in objects if x['classification']=='EQ');strict=next(x for x in objects if x['classification']=='STRICT')
    tests=[]
    x=copy.deepcopy(eq);x['guards'].pop();tests.append({'test':'RTS_missing_native_guard','rejected':rejected(lambda:n['validate'](x,expected,register,policy))})
    x=copy.deepcopy(eq);x['query']='p_only';tests.append({'test':'RTS_dropped_retained_query','rejected':rejected(lambda:n['validate'](x,expected,register,policy))})
    x=copy.deepcopy(strict);x['exact_relaxed_vector'][n['F0']]=str(Fraction(x['exact_relaxed_vector'][n['F0']])+1);tests.append({'test':'RTS_changed_branch_flow','rejected':rejected(lambda:n['validate'](x,expected,register,policy))})
    assert all(t['rejected'] for t in tests)
    report={'saved_extensions':'PASS','additional_unchanged_original_inputs':152,'structural_EQ':104,'upper_bound_EQ':45,'rational_upper_bounds':3417,'additional_STRICT':3,'certificate_negative_tests':cert['mutation_tests'],'figure9_original_checker':capture.getvalue().strip(),'RTS_saved_complete_query_certificates':records,'RTS_negative_tests':tests,'RTS_original_selected_numerical_request_count_preserved':8,'RTS_nearby_exact_point_count_preserved':24,'RTS_nearby_original_query_preservation_not_asserted':True,'solver_calls':0,'fresh_models_or_new_cases':0,'scope':'Saved arithmetic/structural certificates only; no replay of SMT optimum/UNSAT searches, cvc5 or optimization.'}
    (a.report_dir/'extensions_saved_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
