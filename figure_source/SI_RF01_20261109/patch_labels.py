"""Display-only Origin patch. Run with Python+originpro and Origin 2026.
Replays into a new directory: python patch_labels.py --output NEW_DIRECTORY.
No optimization, data classification, or network calls.
"""
from pathlib import Path
import sys,json,hashlib,argparse,subprocess,time
HERE=Path(__file__).resolve().parent
runtime=HERE.parent/'review/_runtime'
if runtime.exists():sys.path.insert(0,str(runtime))
import originpro as op

def procs():
 r=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-CimInstance Win32_Process -Filter \"Name='Origin64.exe'\" | Select-Object ProcessId,ExecutablePath) | ConvertTo-Json -Compress"],capture_output=True,text=True,check=True)
 a=json.loads(r.stdout.strip() or '[]');return a if isinstance(a,list) else [a]
def snap():
 return [dict(book=b.name,sheet=s.name,columns=[s.to_list(i) for i in range(s.cols)]) for b in op.pages('w') for s in b]
def digest(a):return hashlib.sha256(json.dumps(a,sort_keys=True,allow_nan=True).encode()).hexdigest()
def txt(l,n,t,x,y,size=8):
 l.activate();l.lt_exec(f'label -n {n} "Text";');q=l.label(n);q.text=t.replace('\\n','\r\n')
 q.set_int('font',op.lt_int('font(Times New Roman)'));q.set_float('fsize',size)
 q.set_int('background',0);q.set_int('whiteout',0);q.color='#29363C'
 q.set_int('attach',2);q.set_int('anchor',0);q.set_float('x',x);q.set_float('y',y)
 return q
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();dest=a.output.resolve()
 assert not dest.exists(), 'Choose a new output directory';dest.mkdir(parents=True)
 before=procs();op.set_show(False);owned=[x for x in procs() if x['ProcessId'] not in {b['ProcessId'] for b in before}]
 assert len(owned)==1 and abs(op.org_ver()-10.30018)<1e-6
 try:
  op.open(str(HERE/'source/SI_RF01_INPUT.opju'));old=snap();g=op.find_graph('Graph1');l=g[0]
  # 170 mm width is the existing SM insertion width; preserve its aspect ratio.
  g.set_int('unit',1);g.set_int('autosize',2);g.set_int('kar',0)
  g.set_float('width',170/25.4*g.get_float('resx'));g.set_float('height',143.56/25.4*g.get_float('resy'))
  l.set_int('unit',1);l.set_int('fixed',1);l.set_int('showFrame',0)
  for k,v in zip(['left','top','width','height'],[47,13,51,76]):l.set_float(k,v)
  # The 3 existing plots, their symbols/colors, all X/Y values and axis ranges remain.
  for ax in ['x','y']:
   l.set_int(ax+'.opposite',0);l.set_int(ax+'2.opposite',0);l.set_int(ax+'2.ticks',0)
   l.set_float(ax+'.label.pt',8);l.set_int(ax+'.label.bold',0);l.set_float(ax+'.thickness',.5)
  l.set_int('y.showAxes',0);l.set_int('y.showLabels',0);l.set_int('y.ticks',0)
  l.set_int('x.showAxes',0);l.set_int('x.ticks',0);l.set_int('x.label.bold',0)
  for n in ['NText1','NText7','YL','YR','XT','XB']:
   q=l.label(n)
   if q:q.remove()
  # Missing-design dash labels retain their exact data coordinates.
  for obj in l.obj.GraphObjects:
   q=l.label(obj.GetName())
   if q and q.get_int('type')==0 and q.text=='-':q.set_float('fsize',8)
  for p in l.plot_list():p.symbol_size=3.3;p.set_float('symbol.edgewidth',.65)
  # A transparent native label layer; all labels and rules remain editable.
  t=g.add_layer();t.set_int('unit',1);t.set_int('fixed',1)
  for k,v in zip(['left','top','width','height'],[0,0,100,100]):t.set_float(k,v)
  t.axis('x').set_limits(0,100,10);t.axis('y').set_limits(0,100,10)
  for ax in ['x','y','x2','y2']:
   for k in ['showAxes','showLabels','showGrids','ticks','opposite']:t.set_int(ax+'.'+k,0)
  for n in ['XB','YL','XT','YR','Legend']:
   q=t.label(n)
   if q:q.remove()
  # Link legend symbols to original plot layer; native legend stays with plot layer.
  leg=txt(l,'Legend','\\l(1) EQ     \\l(2) Unresolved     \\l(3) Inapplicable     - Outside design',1.4,27.1,8.5)
  # The legend above spans the page; its position is in plot coordinates.
  leg.set_float('x',2.5);leg.set_float('y',27.0)
  for n,s,x in [('Interval','Interval',6),('Form','Formulation',20),('Init','Initialization',33),('State','State',42)]:txt(t,n,'\\b('+s+')',x,90.5,8)
  yy=lambda row:87-(row+.5)*76/24
  for group,mins in enumerate([1,5,15]):
   base=group*8
   txt(t,'Time'+str(group),'\\b('+str(mins)+' min)',6,yy(base+3.5),8.5)
   for model,name in enumerate(['Net power\\nrelaxation','Gross power\\ntightening']):
    b=base+model*4;txt(t,f'Form{group}{model}',name,20,yy(b+1.5),8)
    for init,label in enumerate(['Source','Boundary']):
     c=b+init*2;txt(t,f'Init{group}{model}{init}',label,33,yy(c+.5),8)
     for phase,lab in enumerate(['Before','After']):txt(t,f'State{c+phase}',lab,42,yy(c+phase),8)
  # Horizontal rules mark durations; thin lines never encode outcomes.
  for i,y in enumerate([87,87-8*76/24,87-16*76/24,11]):
   t.activate();t.lt_exec(f'draw -l {{1,{y},98,{y}}};')
  for obj in t.obj.GraphObjects:
   q=t.label(obj.GetName())
   if q and q.get_int('type')!=0:q.set_float('lineWidth',.35);q.color='#A9B2B6'
  txt(t,'Horizon','Horizon (intervals)',72.5,2.3,8.5)
  assert digest(old)==digest(snap())
  op.save(str(dest/'SI_RF01_GROUPED.opju'));g.activate();op.lt_exec('doc -uw;')
  g.save_fig(str(dest/'SI_RF01_GROUPED.png'),width=round(170/25.4*1000))
  g.save_fig(str(dest/'SI_RF01_GROUPED.svg'),type='svg',ratio=100)
  op.lt_exec(f'expgraph -sw type:=pdf filename:="SI_RF01_GROUPED" path:="{dest}" overwrite:=replace tr2.PDF.Fonts.Embed:=1;')
  op.open(str(dest/'SI_RF01_GROUPED.opju'))
  assert digest(old)==digest(snap());g=op.find_graph('Graph1');g.activate()
  g.save_fig(str(dest/'REOPEN.png'),width=1700)
  report={'status':'PASS','owned_process':owned,'original_data_digest':digest(old),'reopened_data_digest':digest(snap()),'native_graphs':1,'data_layers':1,'label_layers':1,'native_plots':len(g[0].plot_list()),'axis_ranges':{'x':list(g[0].xlim),'y':list(g[0].ylim)},'publication_width_mm':170,'height_mm':143.56,'native_data':old}
  (dest/'NATIVE_PATCH_QA.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 finally:op.exit()
if __name__=='__main__':main()
