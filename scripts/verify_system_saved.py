"""Replay all stored synthetic request vectors and strict witnesses without solving."""
from pathlib import Path
from fractions import Fraction as F
import ast,json,argparse,collections,copy
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'extensions/source_layout'
def functions(path,names):
    t=ast.parse(path.read_text(encoding='utf-8-sig'));t.body=[x for x in t.body if isinstance(x,ast.FunctionDef) and x.name in names]
    assert {x.name for x in t.body}==set(names)
    ns={'F':F};exec(compile(t,str(path),'exec'),ns);return ns
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    direct=functions(BASE/'ECM_FIGURE9_STEP2D_REDESIGN_V2_20261023/VERIFY_PACKAGE.py',['check'])['check']
    reconstruct=functions(BASE/'ECM_TARGETED_STRENGTHENING_20261017/SCRIPTS/system_model.py',['reconstruct'])['reconstruct']
    points=0;global_strict=0;statuses=collections.Counter();rows=[];negatives=[]
    for f in sorted((BASE/'ECM_TARGETED_STRENGTHENING_20261017/03_SYSTEM_CASE/RESULTS').glob('*.json')):
        o=json.loads(f.read_text());cfg=o['input'];T=cfg['T'];assert T==4
        cap=F(o['service_budget']);assert cap==F(101,100)*F(o['economic']['exclusive']['exact']['cost'])
        for kind in ['economic','service']:
            for mode in ['relaxed','exclusive']:
                rec=o[kind][mode];ex=rec['exact'];v=list(map(F,ex['vector']));bad,n,power=direct(cfg,v,mode=='exclusive');assert not bad
                cost=sum((10*v[3*t]+20*v[3*t+1]+100*v[3*t+2] for t in range(T)),F(0));assert cost==F(ex['cost'])
                assert sum(power[-2:],F(0))==F(ex['service_objective'])
                assert ex['primary_optimum_certified'] and ex['exact_better_primary_query']=='unsat'
                if kind=='service':assert cost<=cap and ex['secondary_optimum_certified'] and ex['exact_better_secondary_query']=='unsat'
                lift=reconstruct(cfg,ex['vector']);assert lift==rec['reconstructed_vector'];assert v[:9*T]==list(map(F,lift[:9*T]));assert direct(cfg,lift,True)[2]==power;points+=1
        g=o['global_query_check'];statuses[g['status']]+=1
        if g['status']=='sat':
            bad,n,power=direct(cfg,g['relaxed_vector'],False);assert not bad
            lift=reconstruct(cfg,g['relaxed_vector']);assert lift==g['reconstructed_vector'] and direct(cfg,lift,True)[0];global_strict+=1
        else:assert g['status']=='unsat'
        rows.append({'case_id':cfg['case_id'],'state':cfg['state'],'cost_cap_exact':str(cap),'complete_relation_saved':'EQ' if g['status']=='unsat' else 'STRICT','full_original_logical_decision_replayed':False})
    assert points==104 and len(rows)==26 and statuses=={'unsat':7,'sat':19} and global_strict==19
    sample=json.loads(f.read_text());v=list(map(F,sample['economic']['exclusive']['exact']['vector']));v[0]+=1
    assert direct(sample['input'],v,True)[0];negatives.append({'test':'changed_generator_coordinate','rejected':True})
    out={'status':'PASS','stored_selected_vectors_checked':104,'original_states':26,'saved_global_EQ_decisions_preserved_not_resolved':7,'saved_global_STRICT_witnesses_rechecked':19,'exact_shared_service_cap':'101/100 times exclusive economic optimum at that state','objective_values_and_saved_bound_flags_reconciled':True,'UNSAT_optimality_replay':False,'negative_tests':negatives,'source_scope':'Original native check/reconstruction function bodies, path/AST loading only; no system_model optimizer imports','solver_calls':0,'records':rows}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='records'},indent=2))
if __name__=='__main__':main()
