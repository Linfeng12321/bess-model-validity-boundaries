from pathlib import Path
from fractions import Fraction as F
import sys,json,itertools,time,os
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1];OLD=BASE.parent/'round2';OUT=BASE/'f2_parametric_region_v1'
sys.path[:0]=[str(OLD/'dependencies'),str(OLD/'z3_dependencies'),str(ROOT/'RUN_CONTROL')]
import numpy as np
import z3
from scipy.optimize import linprog
import run_health as h
def save(p,x):
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,default=str,allow_nan=False)
def Q(x):return z3.RealVal(str(x))
def has_quant(expr):return z3.is_quantifier(expr) or any(has_quant(x) for x in expr.children())
e,A=z3.Reals('initial ceiling');xs=z3.Reals('c0 d0 c1 d1');DOMAIN=z3.And(e>=0,e<=1,A>=Q(F(1,5)),A<=2)
def build(regime,sign):
 # Each affine expression is (coefficients of c0,d0,c1,d1, constant with symbolic e/A).
 E=e;S=e;constraints=[];bad=[];lp_rows=[];lift=[]
 er=np.zeros(4);sr=np.zeros(4)
 for t in range(2):
  c,d=xs[2*t:2*t+2];prev=E;sprev=S;pr=er.copy();ps=sr.copy()
  E=E+Q(F(9,100))*c-Q(F(1,9))*d
  er[2*t]+=0.09;er[2*t+1]-=1/9
  charging=sign[t]==0
  C=c-d if charging else Q(0);D=Q(0) if charging else d-c
  cr=np.zeros(4);dr=np.zeros(4)
  if charging:cr[2*t]=1;cr[2*t+1]=-1
  else:dr[2*t]=-1;dr[2*t+1]=1
  S=S+Q(F(9,100))*C-Q(F(1,9))*D;sr=sr+.09*cr-(1/9)*dr
  constraints += [c>=0,d>=0,c+d<=1,E>=0,E<=1,c>=d if charging else d>=c]
  row=np.zeros(4);row[2*t]=1;row[2*t+1]=1;lp_rows.append((row,0.,0.,1.))
  lp_rows.extend([(er.copy(),-1.,0.,1.),(-er.copy(),1.,0.,0.)])
  sg=np.zeros(4);sg[2*t]=-1 if charging else 1;sg[2*t+1]=1 if charging else -1;lp_rows.append((sg,0.,0.,0.))
  bad += [S<0,S>1];lift.extend([(-sr.copy(),-1.,0.,0.),(sr.copy(),1.,0.,-1.)])
  if regime!='BOX':
   ref=E if regime=='END' else prev;sref=S if regime=='END' else sprev
   rr=er if regime=='END' else pr;ss=sr if regime=='END' else ps
   constraints.append(c+ref<=A);bad.append(C+sref>A)
   cc=np.zeros(4);cc[2*t]=1
   lp_rows.append((cc+rr,-1.,1.,0.));lift.append((cr+ss,1.,-1.,0.))
 return z3.And(constraints),z3.Or(bad),lp_rows,lift
def qe(expr):
 start=time.perf_counter()
 try:
  result=z3.TryFor(z3.Tactic('qe'),10000)(expr).as_expr()
  return result,{'status':'UNKNOWN_QUANTIFIERS' if has_quant(result) else 'ELIMINATED','seconds':time.perf_counter()-start,'formula_chars':len(result.sexpr())}
 except z3.Z3Exception as exc:return None,{'status':'UNKNOWN_TIMEOUT_OR_ERROR','seconds':time.perf_counter()-start,'error':str(exc)}
def lp_check(parts,ev,av):
 best=None;feasible=False
 for _,_,rows,objectives in parts:
  mat=np.array([r[0] for r in rows]);rhs=np.array([r[1]*float(ev)+r[2]*float(av)+r[3] for r in rows])
  for vec,ce,ca,k in objectives:
   ans=linprog(-vec,A_ub=mat,b_ub=rhs,bounds=[(0,1)]*4,method='highs')
   assert ans.status in (0,2),ans.message
   if ans.status==0:
    feasible=True;v=float(vec@ans.x+ce*float(ev)+ca*float(av)+k)
    best=v if best is None else max(best,v)
 return feasible,best
if __name__=='__main__':
 OUT.mkdir(exist_ok=True);start=h.now();sh=h.sha(Path(__file__))
 if (OUT/'RECEIPT.json').exists():
  r=h.read(OUT/'RECEIPT.json');assert all(h.sha(OUT/a['path'])==a['sha256'] for a in r['artifacts']);print('VERIFIED_SKIP');sys.exit()
 allrec=[];qes=[]
 for regime in ['BOX','END','START']:
  parts=[build(regime,s) for s in itertools.product([0,1],repeat=2)]
  badexpr=z3.Or([z3.And(c,b) for c,b,_,_ in parts]);feasexpr=z3.Or([c for c,_,_,_ in parts])
  fp=OUT/(regime+'_formulas.smt2');meta=OUT/(regime+'_qe.json')
  if meta.exists():
   old=h.read(meta);assert old['script_sha256']==sh and old['formula_sha256']==h.sha(fp)
   forms=z3.parse_smt2_file(str(fp));fqe=forms[0] if old['feasible_complete'] else None;bqe=forms[1] if old['bad_complete'] else None;qerec=old
  else:
   fqe,fmeta=qe(z3.Exists(xs,feasexpr));badforms=[];bm=[]
   for c,b,_,_ in parts:
    form,info=qe(z3.Exists(xs,z3.And(c,b)));badforms.append(form);bm.append(info)
   complete=all(f is not None and not has_quant(f) for f in badforms)
   bqe=z3.simplify(z3.Or(badforms)) if complete else None
   fcomplete=fqe is not None and not has_quant(fqe)
   solver=z3.Solver();solver.add(fqe if fcomplete else z3.BoolVal(False));solver.add(bqe if complete else z3.BoolVal(False))
   with fp.open('x',encoding='utf-8') as f:f.write(solver.to_smt2())
   qerec={'regime':regime,'feasible_qe':fmeta,'bad_branch_qe':bm,'feasible_complete':fcomplete,'bad_complete':complete,'formula_sha256':h.sha(fp),'script_sha256':sh}
   save(meta,qerec)
  qes.append(qerec)
  for i,(ev,av) in enumerate(itertools.product([F(k,10) for k in range(11)],[F(k,5) for k in range(1,11)])):
   path=OUT/f'{regime}_{i:03d}.json';check=path.with_suffix('.verified.json')
   if check.exists():
    ck=h.read(check);assert ck['script_sha256']==sh and ck['sha256']==h.sha(path);allrec.append(h.read(path));continue
   fixed=[e==Q(ev),A==Q(av)];s=z3.Solver();s.set(timeout=5000);s.add(*fixed,feasexpr);fa=s.check();s2=z3.Solver();s2.set(timeout=5000);s2.add(*fixed,badexpr);ba=s2.check()
   r={'regime':regime,'e0':str(ev),'ceiling':str(av),'feasible_smt':str(fa),'bad_smt':str(ba),'errors':[]}
   if ba==z3.sat:r['witness']={str(x):str(s2.model().eval(x,model_completion=True)) for x in xs}
   for key,form,expected in [('feasible_qe',fqe,fa),('bad_qe',bqe,ba)]:
    if form is None or has_quant(form):r[key]='UNKNOWN';continue
    value=z3.simplify(z3.substitute(form,(e,Q(ev)),(A,Q(av))));assert z3.is_true(value) or z3.is_false(value)
    r[key]=str(value)
    if expected!=z3.unknown and z3.is_true(value)!=(expected==z3.sat):r['errors'].append(key+'_MISMATCH')
   lpf,margin=lp_check(parts,ev,av);r.update(lp_feasible=lpf,lp_max_margin=margin)
   if fa!=z3.unknown and lpf!=(fa==z3.sat):r['errors'].append('LP_FEASIBILITY_MISMATCH')
   if margin is not None and ba!=z3.unknown:
    if margin>1e-8 and ba!=z3.sat:r['errors'].append('LP_FALSE_VIOLATION')
    if margin < -1e-8 and ba==z3.sat:r['errors'].append('LP_MISSED_VIOLATION')
   save(path,r);save(check,{'script_sha256':sh,'sha256':h.sha(path)});allrec.append(r)
  print(json.dumps({'regime':regime,'points':110,'qe_complete':qerec['bad_complete'],'errors':sum(len(r['errors']) for r in allrec)}),flush=True)
 summary={'parameter_points':len(allrec),'qa_failures':sum(len(r['errors']) for r in allrec),'SMT_unknown':sum(r['bad_smt']=='unknown' or r['feasible_smt']=='unknown' for r in allrec),'regimes':{}}
 for regime in ['BOX','END','START']:
  rr=[r for r in allrec if r['regime']==regime];summary['regimes'][regime]={'empty':sum(r['feasible_smt']=='unsat' for r in rr),'strict':sum(r['bad_smt']=='sat' for r in rr),'nonempty_equal':sum(r['feasible_smt']=='sat' and r['bad_smt']=='unsat' for r in rr),'strict_below_SOC_headroom':sum(r['bad_smt']=='sat' and F(r['e0'])<=F(41,50) for r in rr),'qe_complete':next(q['bad_complete'] for q in qes if q['regime']==regime)}
 save(OUT/'SUMMARY.json',summary)
 save(OUT/'RECEIPT.json',{'execution_qa':'PASS' if summary['qa_failures']==0 else 'FAIL','start_utc':start,'end_utc':h.now(),'pid':os.getpid(),'script_sha256':sh,'protocol_sha256':h.sha(BASE/'F2_PARAMETRIC_REGION_PROTOCOL_v0_1.md'),'artifacts':[{'path':p.name,'sha256':h.sha(p)} for p in sorted(OUT.iterdir()) if p.is_file()],'research_gate_decision':'SCREENING_PARAMETRIC_REGION_TESTED','next_action':'Review formula complexity, nonvacuous applicability and known parametric baseline; no automatic novelty promotion.'})
 print(json.dumps(summary),flush=True)
