from pathlib import Path
import csv,json,collections,shutil,argparse
from fractions import Fraction as F
D=Path(__file__).resolve().parent
def table(p,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def plot():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=D/'REVIEW_REPRODUCIBILITY/data/Lossless_Control_Factor_Lookup.csv');parser.add_argument('--output',type=Path,default=D/'09_FINAL_SI_SOURCE_AND_PDF');args=parser.parse_args()
    rows=list(csv.DictReader(args.data.open(encoding='utf-8-sig')))
    horizons=[4,5,6,7,8,10,12,14,16,20,24,32,48,96,128,192,256]
    factors=[(h,row,init,state) for h in [F(1,60),F(1,12),F(1,4)] for row in ['N','G'] for init in ['source60','charged_boundary'] for state in ['old','new']]
    # The actual initialization key is read from the frozen records, not guessed.
    initializations=sorted({r['initial_rule'] for r in rows})
    boundary=next(x for x in initializations if x!='source60')
    factors=[(h,row,init,state) for h in [F(1,60),F(1,12),F(1,4)] for row in ['N','G'] for init in ['source60',boundary] for state in ['old','new']]
    lookup={(int(r['horizon_T']),F(r['interval_duration']),r['row_form'],r['initial_rule'],r['old_or_new_state']):r for r in rows}
    assert len(lookup)==312 and len({r['case_id'] for r in rows})==312
    derived=[]
    for y,factor in enumerate(factors):
        for x,T in enumerate(horizons):
            r=lookup.get((T,*factor));derived.append({'horizon':T,'row_index':y,'duration_h':str(factor[0]),'row_form':factor[1],'initialization':factor[2],'state':factor[3],'status':r['exact_status'] if r else 'OUTSIDE_DESIGN','case_id':r['case_id'] if r else ''})
    assert collections.Counter(r['status'] for r in derived)=={'EQ':144,'TIMEOUT':104,'NOT_APPLICABLE':64,'OUTSIDE_DESIGN':96}
    args.output.mkdir(parents=True,exist_ok=True);table(args.output/'Lossless_Figure_Cells.csv',derived)
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':9,'pdf.fonttype':42,'svg.fonttype':'none'})
    fig,ax=plt.subplots(figsize=(6.4,7.5));fig.subplots_adjust(left=.405,right=.99,bottom=.105,top=.88)
    styles={'EQ':('s','#20675D'),'TIMEOUT':('^','#294D7C'),'NOT_APPLICABLE':('o','#595959')}
    for status,(marker,color) in styles.items():
        data=[r for r in derived if r['status']==status]
        ax.scatter([horizons.index(r['horizon']) for r in data],[r['row_index'] for r in data],s=19,marker=marker,c=color,linewidths=.5,edgecolors='black',zorder=3)
    for r in derived:
        if r['status']=='OUTSIDE_DESIGN':ax.text(horizons.index(r['horizon']),r['row_index'],'–',ha='center',va='center',fontsize=9,color='#555555')
    labels=[]
    for h,row,init,state in factors:labels.append(f'{int(h*60)} min / {row} / '+('source' if init=='source60' else 'boundary')+' / '+('before' if state=='old' else 'after'))
    ax.set(xticks=range(len(horizons)),xticklabels=horizons,yticks=range(len(factors)),yticklabels=labels,xlim=(-.6,16.6),ylim=(23.7,-.7),xlabel='Horizon (intervals)')
    ax.tick_params(axis='x',rotation=90,length=2,pad=4);ax.tick_params(axis='y',length=0,pad=5,labelsize=8.5)
    for pos in [7.5,15.5]:ax.axhline(pos,color='.75',lw=.6,zorder=0)
    handles=[Line2D([],[],marker=m,color='none',markerfacecolor=c,markeredgecolor='black',markeredgewidth=.5,markersize=4.5,label={'EQ':'EQ','TIMEOUT':'Unresolved','NOT_APPLICABLE':'Inapplicable'}[s]) for s,(m,c) in styles.items()]
    handles.append(Line2D([],[],marker='$-$',color='#555555',linestyle='none',markersize=6,label='Outside design'))
    fig.suptitle('Lossless control: joint factor outcomes',y=.972,fontsize=11)
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.53,.948),ncol=2,frameon=False,fontsize=9,handletextpad=.5,columnspacing=1.5)
    out=args.output
    fig.savefig(out/'SI_Lossless_Factors_Verified.pdf',metadata={'Title':'Lossless control joint factor outcomes','Author':'Authors; candidate rendering from frozen records'})
    fig.savefig(out/'SI_Lossless_Factors_Verified.png',dpi=600)
    plt.close(fig)
    (out/'LOSSLESS_PLOT_COUNTS.json').write_text(json.dumps({'assessed':312,'outside_design':96,'counts':dict(collections.Counter(r['status'] for r in derived)),'data_source':str(args.data),'dpi':600,'matplotlib':matplotlib.__version__},indent=2),encoding='utf-8')
if __name__=='__main__':plot()
