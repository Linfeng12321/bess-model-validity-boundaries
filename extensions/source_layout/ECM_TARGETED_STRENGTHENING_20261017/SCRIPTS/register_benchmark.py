from pathlib import Path
import json,datetime,hashlib,ast
W=Path(__file__).resolve().parents[1];C=W/'04_CERTIFICATION';py=str(W/'ENV/runtime/Scripts/python.exe')
source=W.parent/'ECM_STAGE1_LONG_HORIZON_BRIDGE_v1_0/implementation_v1_0/checker.py'
tree=ast.parse(source.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['zr','exact_route']]
text='from frozen_internal_model import *\nfrom fractions import Fraction as F\nimport time,z3\n\n'+'\n\n'.join(ast.get_source_segment(source.read_text(),n) for n in nodes)+'\n'
(W/'SCRIPTS/original_primary_smt.py').write_text(text,encoding='utf-8')
allinputs=json.loads((C/'ORIGINAL_UNRESOLVED_INPUTS.json').read_text());panel=[]
for T in [14,32,256]:
    for family in ['N','G']:
        panel.append(sorted([i for i in allinputs if i['T']==T and i['row_form']==family],key=lambda i:i['case_id'])[0])
obj=dict(registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selection='First lexical original unresolved case in each horizon {14,32,256} x native row family {N,G}; no outcome filter.',cases=panel,repeats=3,budget_per_route_seconds=30,primary_endpoint='Exact EQ/STRICT versus unresolved under identical original input and total route budget, including model and validation; no relative comparison to historical wall times.',order='Alternate original/new versus new/original by case plus repeat parity. Fresh process per route. One allowed processor affinity for both.',original_source=str(source),original_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),original_extraction='Unchanged original exact_route and zr AST function bodies; no import or write into original project. Includes its extra SOC-constrained query.',noncomparability_note='Original route includes an optional additional SOC-constrained witness query within the same budget. New route seeks the same primary EQ/STRICT decision. Timing reported as full certification-route comparison, not isolated solver-kernel speedup.')
(C/'MATCHED_BENCHMARK_CARD.json').write_text(json.dumps(obj,indent=2),encoding='utf-8')
q=W/'00_CONTROL/QUEUE.json';queue=json.loads(q.read_text())
def add(id,script,args,ins,outs,timeout):
    if not any(j['id']==id for j in queue['jobs']):queue['jobs'].append(dict(id=id,argv=[py,'-B',str(W/'SCRIPTS'/script)]+args,inputs=[str(W/p) for p in ins],outputs=[str(W/p) for p in outs],timeout_s=timeout))
add('system_context','run_system_study.py',['--stage','context'],['03_SYSTEM_CASE/PILOT_SUMMARY.json','03_SYSTEM_CASE/REGISTERED_SYSTEM_CASES.json','03_SYSTEM_CASE/SYSTEM_CASE_DESIGN.md','SCRIPTS/system_model.py'],['03_SYSTEM_CASE/CONTEXT_SUMMARY.json','03_SYSTEM_CASE/CONTEXT_RESULTS.csv'],14400)
add('matched_certification_benchmark','run_matched_benchmark.py',[],['04_CERTIFICATION/MATCHED_BENCHMARK_CARD.json','SCRIPTS/original_primary_smt.py','SCRIPTS/certification_routes.py','SCRIPTS/run_matched_benchmark.py'],['04_CERTIFICATION/MATCHED_BENCHMARK_RESULTS.csv','04_CERTIFICATION/MATCHED_BENCHMARK_SUMMARY.json'],1800)
q.write_text(json.dumps(queue,indent=2),encoding='utf-8');print([i['case_id'] for i in panel])
