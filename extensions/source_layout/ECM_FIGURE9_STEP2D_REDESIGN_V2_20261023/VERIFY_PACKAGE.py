from pathlib import Path
from fractions import Fraction as F
import csv,json,hashlib
ROOT=Path(__file__).resolve().parent
D=ROOT/'01_SOURCE_AND_NUMERICAL_QA'
def check(cfg,v,exclusive):
 T=cfg['T']; v=list(map(F,v)); assert len(v)==12*T; bad={};count=0
 def test(n,value,eq=False):
  nonlocal count;count+=1
  if (value!=0 if eq else value>0):bad[n]=str(value)
 last=F(cfg['e0']); pp=[]
 for t in range(T):
  g=v[3*t:3*t+3];f=v[3*T+3*t:3*T+3*t+3];a=v[6*T+3*t:6*T+3*t+3];c=v[9*T+t];d=v[10*T+t];e=v[11*T+t]
  for b in range(3):test(f'g_lower_{t}_{b}',-g[b]);test(f'g_upper_{t}_{b}',g[b]-100)
  for l,cap in enumerate([100,100,10]):test(f'f_upper_{t}_{l}',f[l]-cap);test(f'f_lower_{t}_{l}',-f[l]-cap)
  for b in range(3):test(f'angle_lower_{t}_{b}',-1000-a[b]);test(f'angle_upper_{t}_{b}',a[b]-1000)
  for n,res in [('flow12',f[0]-a[0]+a[1]),('flow23',f[1]-a[1]+a[2]),('flow13',f[2]-a[0]+a[2]),('angle_ref',a[2]),('bus1',g[0]+d-c-f[0]-f[2]),('bus2',g[1]+f[0]-f[1]),('bus3',g[2]+f[1]+f[2]-F(cfg['load'][t])),('recursion',e-F(cfg['rho'])*last-F(cfg['eta_c'])*c+d/F(cfg['eta_d']))]:test(f'{n}_{t}',res,True)
  for n,res in [('c_lower',-c),('d_lower',-d),('shared',c+d-1),('E_lower',-e),('E_upper',e-6)]:test(f'{n}_{t}',res)
  if cfg['device']=='TAPER':test(f'taper_{t}',c-d+e/6-1)
  if exclusive:test(f'exclusivity_{t}',c*d)
  pp.append(d-c);last=e
 return bad,count,pp
def read(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
rows=read(D/'FIGURE9_26_STATE_SOURCE_MAPPING.csv');assert len(rows)==26 and len({r['pair_id'] for r in rows})==13
nr=0
for r in rows:
 d=json.loads((D/'certificates'/f"{r['pair_id']}_{r['state_slot']}.json").read_text())
 for kind in ['economic','service']:
  s=d[kind]['relaxed'];v=list(map(F,s['exact']['vector']));x=list(map(F,s['reconstructed_vector']))
  b,n,p=check(d['input'],v,False);bb,nn,pp=check(d['input'],x,True);nr+=n+nn
  assert not b and v[:36]==x[:36] and p==pp
  assert (not bb)==(r[f'selected_{kind}_query_realisable']=='TRUE')
for r in read(D/'FIGURE9_SERVICE_ENERGY_EXACT.csv'):
 e=F(r['relaxed_exact_MWh']);ex=F(r['exclusive_exact_MWh']);u=F(r['upper_exact_MWh'])
 assert F(r['headroom_exact_kWh'])==1000*(u-e) and F(r['shift_exact_kWh'])==1000*(ex-e)
 assert F(r['margin_exact_kWh'])==1000*(u-ex) and F(r['violation_exact_kWh'])==max(F(0),1000*(ex-u))
for r in read(D/'FIGURE9_COUNTS_FROM_RAW.csv'):
 k=r['request'].lower();agree='economic_optima_agree' if k=='economic' else 'service_primary_values_agree';subset=[x for x in rows if x[agree]=='TRUE']
 assert sum(x[f'selected_{k}_query_realisable']=='FALSE' for x in rows)==int(r['unrealizable'])
 assert len(subset)==int(r['equal_primary_states']) and sum(x[f'selected_{k}_query_realisable']=='FALSE' for x in subset)==int(r['equal_primary_unrealizable'])
m=ROOT/'OUTPUT_SHA256_MANIFEST.csv'
if m.exists():
 for r in read(m):
  p=ROOT/r['relative_path'];assert p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],str(p)
print('VERIFY PASS: 26 states, 13 pairs, 52 selected requests,',nr,'exact native rows; energy fractions, counts and any present manifest. Scientific solver calls: 0.')
