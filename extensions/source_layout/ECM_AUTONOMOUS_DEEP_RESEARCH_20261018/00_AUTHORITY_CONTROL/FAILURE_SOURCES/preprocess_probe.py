"""Single fixed-input verification diagnostic. Standard equation elimination only."""
from pathlib import Path
from fractions import Fraction as F
import argparse,faulthandler,json,subprocess,sys,time
U=Path(__file__).resolve().parent;sys.path.insert(0,str(U/'_deps'))
import z3,cvc5
def reduced_decide(query,timeout_ms,count):
    start=time.perf_counter();goal=z3.Goal();goal.add(z3.parse_smt2_string(query));reduced=z3.Then('simplify','solve-eqs')(goal)
    assert len(reduced)==1
    small=reduced[0];export=z3.Solver();export.add(small)
    text='(set-logic QF_LRA)\n'+export.to_smt2();solver=cvc5.Solver();solver.setOption('produce-models','true');solver.setOption('tlimit-per',str(max(1,int(timeout_ms-1000*(time.perf_counter()-start)))))
    parser=cvc5.InputParser(solver);parser.setStringInput(cvc5.InputLanguage.SMT_LIB_2_6,text,'same_fixed_reduced_query');ans=None
    while True:
        cmd=parser.nextCommand()
        if cmd.isNull():break
        if cmd.getCommandName()=='check-sat':ans=solver.checkSat()
        else:cmd.invoke(solver,parser.getSymbolManager())
    result=dict(status=str(ans),solver='cvc5 '+cvc5.__version__+' with standard Z3 solve-eqs preprocessing',original_assertions=len(goal),reduced_assertions=len(small),reduced_declared_terms=len(parser.getSymbolManager().getDeclaredTerms()),wall_seconds=time.perf_counter()-start)
    if ans.isSat():
        model=z3.Model()
        for term in parser.getSymbolManager().getDeclaredTerms():
            val=solver.getValue(term);model.update_value(z3.Real(str(term)),z3.RealVal(str(F(val.getRealValue()))))
        full=small.convert_model(model)
        vv=[full.eval(z3.Real(f'x{i}'),model_completion=True) for i in range(count)]
        result['vector']=[str(F(v.numerator_as_long(),v.denominator_as_long())) for v in vv]
    else:result['reason']=str(ans.getUnknownExplanation()) if ans.isUnknown() else ''
    (U/'06_INDEPENDENT_CHECKS/PREPROCESS_DIAGNOSTIC_DECISION.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.worker:
        proc=subprocess.Popen([sys.executable,'-B',__file__,'--worker'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8')
        try:out,err=proc.communicate(timeout=35)
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);out,err=proc.communicate();out+='\nHARD35_SECOND_DIAGNOSTIC_STOP\n'
        (U/'06_INDEPENDENT_CHECKS/PREPROCESS_DIAGNOSTIC_STDOUT.txt').write_text(out,encoding='utf-8');(U/'06_INDEPENDENT_CHECKS/PREPROCESS_DIAGNOSTIC_STDERR.txt').write_text(err,encoding='utf-8');print(out,err);return
    import system_model as sm
    f=(U/'06_INDEPENDENT_CHECKS/PREPROCESS_DIAGNOSTIC_STACK.txt').open('w');faulthandler.dump_traceback_later(5,repeat=True,file=f)
    # Tiny model-converter sanity check, not a new study parameter case.
    q='(declare-fun x0 () Real)(declare-fun x1 () Real)(assert (= (+ x0 x1) 1))(assert (= x1 (/ 1 3)))(check-sat)'
    test=reduced_decide(q,1000,2);assert list(map(F,test['vector']))==[F(2,3),F(1,3)]
    obj=json.loads((U/'03_SYSTEM_V3/RUNS/RTS_L0_T0_N1_old.json').read_text());cfg=obj['input'];sm.cvc5_decide=reduced_decide
    repair=sm.rational_repair(cfg,obj['stages']['economic_relaxed'])
    if repair['status']=='sat':
        from independent_physics import check
        repair['direct_physics']=check(cfg,repair['vector']);assert repair['direct_physics']['pass_all']
    (U/'06_INDEPENDENT_CHECKS/PREPROCESS_DIAGNOSTIC_REPAIR.json').write_text(json.dumps(repair,indent=2),encoding='utf-8');faulthandler.cancel_dump_traceback_later();f.close();print(repair['status'],repair['wall_seconds'],flush=True)
if __name__=='__main__':main()
