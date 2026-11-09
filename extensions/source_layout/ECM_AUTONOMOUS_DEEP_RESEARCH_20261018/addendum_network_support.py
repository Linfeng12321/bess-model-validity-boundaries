"""Route N1: independent RAW-CSV affine network row support/box dual proof.
No original row builder, checker, affine object or network inverse is imported.
"""
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
import csv,hashlib,json,time
D=Path(__file__).resolve().parent;A=D/'11_SCIENTIFIC_DEPTH_ADDENDUM';K=D/'00_AUTHORITY_CONTROL/PREVIOUS_CORE';O=A/'NETWORK_EXTENSION_CERTIFICATE_PACKAGE'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csvs(name):return list(csv.DictReader((K/'01_SOURCES'/name).open(encoding='utf-8-sig')))
def main():
 start=time.perf_counter();s=json.loads((K/'02_PROTOCOL/NORMALIZED_RTS_INPUT.json').read_text());proof=json.loads((D/'03_RTS_EXACT_NETWORK/R2/UNIVERSAL_NETWORK_EXTENSION_CERTIFICATE.json').read_text());v=list(map(F,proof['baseline_vector']));G=len(s['generators']);L=len(s['lines']);B=len(s['buses']);fi=24*G;ai=24*(G+L)
 rawbus={int(r['Bus ID']):r for r in csvs('RTS_Data__SourceData__bus.csv')};rawgen={r['GEN UID']:r for r in csvs('RTS_Data__SourceData__gen.csv')};rawline={r['UID']:r for r in csvs('RTS_Data__SourceData__branch.csv')};load=csvs('RTS_Data__timeseries_data_files__Load__DAY_AHEAD_regional_Load.csv')[:24]
 assert [(x['Year'],x['Month'],x['Day'],x['Period']) for x in load]==[('2020','1','1',str(t+1)) for t in range(24)]
 profiles=[]
 for folder,name in [('WIND','wind'),('PV','pv'),('RTPV','rtpv'),('Hydro','hydro')]:profiles.append(csvs('RTS_Data__timeseries_data_files__'+folder+'__DAY_AHEAD_'+name+'.csv')[:24])
 gen=[]
 for g in s['generators']:
  r=rawgen[g['id']];p=next((x for x in profiles if g['id'] in x[0]),None);up=[min(F(r['PMax MW']),F(p[t][g['id']])) if p is not None else F(r['PMax MW']) for t in range(24)]
  assert up==list(map(F,g['upper'])) and 60*F(r['Ramp Rate MW/Min'])==F(g['ramp'])
  gen.append(dict(id=g['id'],bus=int(r['Bus ID']),up=up,ramp=60*F(r['Ramp Rate MW/Min'])))
 lines=[]
 for line in s['lines']:
  r=rawline[line['id']];b=F(100)/(F(r['X'])*(F(r['Tr Ratio']) or 1));assert b==F(line['susceptance']) and F(r['Cont Rating'])==F(line['limit'])
  lines.append(dict(id=line['id'],frm=int(r['From Bus']),to=int(r['To Bus']),beta=b,limit=F(r['Cont Rating'])))
 target=next(j for j,g in enumerate(gen) if g['id']=='313_CC_1');assert gen[target]['bus']==313
 for t in range(24):assert v[t*G+target]==F(355,2)
 bidx={b['id']:i for i,b in enumerate(s['buses'])};rows=[]
 def row(name,family,c,a=None,equality=False):
  a={int(k):F(x) for k,x in (a or {}).items() if x};upper=F(c)+50*sum(map(abs,a.values()),F(0));valid=(F(c)==0 and not a) if equality else upper<=0
  rows.append(dict(id=name,family=family,sense='=' if equality else '<=',constant=str(c),power_coefficients={str(k):str(x) for k,x in a.items()},exact_upper=str(upper),valid=valid,box_dual_plus={str(k):str(max(x,F(0))) for k,x in a.items() if x>0},box_dual_minus={str(k):str(max(-x,F(0))) for k,x in a.items() if x<0}))
 for t in range(24):
  for j,g in enumerate(gen):
   x=v[t*G+j];a={t:F(-1)} if j==target else {}
   row(f'g_hi_{t}_{j}','GEN_UPPER',x-g['up'][t],a);row(f'g_lo_{t}_{j}','GEN_LOWER',-x,{k:-x for k,x in a.items()})
   if t:
    ar={t:F(-1),t-1:F(1)} if j==target else {};diff=x-v[(t-1)*G+j]
    row(f'ramp_up_{t}_{j}','GEN_RAMP',diff-g['ramp'],ar);row(f'ramp_down_{t}_{j}','GEN_RAMP',-diff-g['ramp'],{k:-x for k,x in ar.items()})
  for j,l in enumerate(lines):
   x=v[fi+t*L+j];row(f'f_hi_{t}_{j}','LINE_LIMIT',x-l['limit']);row(f'f_lo_{t}_{j}','LINE_LIMIT',-x-l['limit']);row(f'dc_{t}_{j}','DC_FLOW',x-l['beta']*(v[ai+t*B+bidx[l['frm']]]-v[ai+t*B+bidx[l['to']]]),equality=True)
  row(f'reference_{t}','REFERENCE_ANGLE',v[ai+t*B],equality=True)
  for b in s['buses']:
   raw=rawbus[b['id']];area=raw['Area'];den=sum((F(x['MW Load']) for x in rawbus.values() if x['Area']==area),F(0));demand=F(raw['MW Load'])*F(load[t][area])/den;assert demand==F(b['load'][t])
   residual=sum((v[t*G+j] for j,g in enumerate(gen) if g['bus']==b['id']),F(0))-demand
   residual+=sum((v[fi+t*L+j] for j,l in enumerate(lines) if l['to']==b['id']),F(0))-sum((v[fi+t*L+j] for j,l in enumerate(lines) if l['frm']==b['id']),F(0))
   coefficient=sum((-F(1) for j,g in enumerate(gen) if j==target and g['bus']==b['id']),F(0))+(F(1) if b['id']==313 else F(0))
   row(f'balance_{t}_{b["id"]}','BUS_BALANCE',residual,{t:coefficient},True)
 assert len(rows)==24798 and all(r['valid'] for r in rows)
 with (O/'N1_ALL_NETWORK_ROW_BOX_DUALS.jsonl').open('w') as f:
  for r in rows:f.write(json.dumps(r)+'\n')
 result=dict(status='PASS',claim='B_NETWORK_ONLY:forallp in[-50,50]^24 exists z(p);not preservation of a previously givenz',source='RAW_CSV_REBUILD',rows=len(rows),families=dict(Counter(r['family'] for r in rows)),equalities=sum(r['sense']=='=' for r in rows),support_formula='max(c+a^Tp)=c+50sum(abs(a));dual multipliers stored;equalities constantandallcoefficientszero',source_sha256=sha(K/'02_PROTOCOL/NORMALIZED_RTS_INPUT.json'),baseline_certificate_sha256=sha(D/'03_RTS_EXACT_NETWORK/R2/UNIVERSAL_NETWORK_EXTENSION_CERTIFICATE.json'),max_charge_discharge_box='p box is only network domain; device feasibility separately required',construction_wall_seconds=time.perf_counter()-start,proof_kind='AFFINE_SUPPORT_AND_EXPLICIT_BOX_DUALS',new_original_theorem=False)
 (O/'N1_RAW_SOURCE_ROBUST_CERTIFICATE.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
