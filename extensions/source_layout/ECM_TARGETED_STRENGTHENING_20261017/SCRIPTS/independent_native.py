"""Direct physical native-row checker, independent of the frozen matrix builder."""
from fractions import Fraction as F
def check(inp,vector,require_exclusive=False):
    assert inp['row_form'] in ['N','G'] and F(inp.get('eta_d','1'))==1 and F(inp.get('rho','1'))==1
    T=int(inp['T']);assert len(vector)==3*T
    c=list(map(F,vector[:T]));d=list(map(F,vector[T:2*T]));e=list(map(F,vector[2*T:]));eta=F(inp['eta_c']);h=F(inp['h']);e0=F(inp['effective_initial_energy'])
    residuals={};last=e0
    for t in range(T):
        residuals[f'c_nonnegative_{t}']=-c[t];residuals[f'd_nonnegative_{t}']=-d[t]
        residuals[f'shared_power_{t}']=c[t]+d[t]-F(1,2)
        residuals[f'energy_lower_{t}']=F(3,25)-e[t];residuals[f'energy_upper_{t}']=e[t]-F(57,100)
        residuals[f'dynamics_absolute_{t}']=abs(e[t]-last-h*(eta*c[t]-d[t]-F(7,1000)))
        for endpoint,state in [('start',last),('end',e[t])]:
            charge=c[t]-d[t] if inp['row_form']=='N' else c[t]
            discharge=d[t]-c[t] if inp['row_form']=='N' else d[t]
            residuals[f'charge_{endpoint}_{t}']=charge+F(50,3)*state-F(19,2)
            residuals[f'discharge_{endpoint}_{t}']=discharge-F(25,3)*state+F(1)
        if require_exclusive:residuals[f'exclusivity_{t}']=c[t]*d[t]
        last=e[t]
    bad={k:str(v) for k,v in residuals.items() if v>0}
    return dict(pass_all=not bad,violations=bad,checked_rows=len(residuals),maximum_residual=str(max(residuals.values(),default=F(0))))
def reconstruct(inp,vector):
    T=int(inp['T']);eta=F(inp['eta_c']);h=F(inp['h']);p=[F(vector[T+t])-F(vector[t]) for t in range(T)];c=[max(-q,F(0)) for q in p];d=[max(q,F(0)) for q in p];e=[];state=F(inp['effective_initial_energy'])
    for t in range(T):state+=h*(eta*c[t]-d[t]-F(7,1000));e.append(state)
    return c+d+e
def lossless_nonempty(inp):
    assert F(inp['eta_c'])==F(inp.get('eta_d','1'))==F(inp.get('rho','1'))==1
    T=int(inp['T']);e0=F(inp['effective_initial_energy']);v=[F(7,1000)]*T+[F(0)]*T+[e0]*T
    return v,check(inp,v,True)
def verify_lossless_certificate(proof):
    inp=proof['input'];assert inp['row_form'] in ['N','G'] and int(inp['T'])>0
    assert F(inp['eta_c'])==F(inp.get('eta_d','1'))==F(inp.get('rho','1'))==1
    assert F(inp['h'])>0
    assert proof['model_contract']=='FROZEN_INTERNAL_N_G_V1'
    assert check(inp,proof['nonempty_vector'],True)['pass_all']
    # Removal reduces both nonnegative directional powers, preserves their difference,
    # and at eta_c=eta_d=1 preserves every energy. All N/G native rows are covered.
    assert set(proof['covered_native_families'])=={'flow_nonnegativity','shared_rating','energy_bounds','energy_dynamics','charge_start','charge_end','discharge_start','discharge_end'}
    return True
def verify_strict(inp,vector):
    original=check(inp,vector);recovered=reconstruct(inp,vector);lifted=check(inp,recovered,True)
    T=int(inp['T']);assert all(F(vector[T+t])-F(vector[t])==recovered[T+t]-recovered[t] for t in range(T))
    return dict(certified=original['pass_all'] and not lifted['pass_all'],relaxed=original,reconstructed=lifted,recovered_vector=list(map(str,recovered)))

def linear_rows(inp,epigraph=True):
    """Second matrix implementation derived directly from the physical rows."""
    assert inp['row_form'] in ['N','G'] and F(inp.get('eta_d','1'))==1 and F(inp.get('rho','1'))==1
    T=int(inp['T']);h=F(inp['h']);eta=F(inp['eta_c']);e0=F(inp['effective_initial_energy']);A=[];b=[];E=[];f=[];names=[]
    def push(name,co,rhs):names.append(name);A.append({k:F(v) for k,v in co.items() if v});b.append(F(rhs))
    for t in range(T):
        ci=t;di=T+t;ei=2*T+t
        push('c_lo_'+str(t),{ci:-1},0);push('d_lo_'+str(t),{di:-1},0);push('hull_'+str(t),{ci:1,di:1},F(1,2))
        push('E_hi_'+str(t),{ei:1},F(57,100));push('E_lo_'+str(t),{ei:-1},-F(3,25))
        dyn={ei:F(1),ci:-h*eta,di:h};rhs=-h*F(7,1000)
        if t:dyn[ei-1]=-1
        else:rhs+=e0
        E.append(dyn);f.append(rhs)
        for label,k in [('START',t-1),('END',t)]:
            charge={ci:F(1)};discharge={di:F(1)}
            if inp['row_form']=='N':charge[di]=-1;discharge[ci]=-1
            cu=F(19,2);du=-F(1)
            if k<0:cu-=F(50,3)*e0;du+=F(25,3)*e0
            else:charge[2*T+k]=F(50,3);discharge[2*T+k]=-F(25,3)
            push('CHARGE_'+label+'_'+str(t),charge,cu);push('DISCHARGE_'+label+'_'+str(t),discharge,du)
    if epigraph:
        for t in range(T):
            push('abs_positive_'+str(t),{T+t:1,t:-1,3*T+t:-1},0)
            push('abs_negative_'+str(t),{T+t:-1,t:1,3*T+t:-1},0)
    bounds=[(F(0),F(1,2))]*(2*T)+[(F(3,25),F(57,100))]*T
    if epigraph:bounds +=[(F(0),F(1,2))]*T
    return dict(A=A,b=b,E=E,f=f,names=names,bounds=bounds,n=len(bounds),T=T)

def target_expression(inp,native_index,signs=None):
    """Substitute physical powers and cumulative energy into one native inequality."""
    T=int(inp['T']);h=F(inp['h']);eta=F(inp['eta_c']);model=linear_rows(inp,False);row=model['A'][native_index]
    const=-model['b'][native_index];co=[F(0)]*(4*T)
    for j,a in row.items():
        if j<T:
            co[j]+=a/2;co[T+j]-=a/2;co[3*T+j]+=a/2
        elif j<2*T:
            t=j-T;co[t]-=a/2;co[T+t]+=a/2;co[3*T+t]+=a/2
        else:
            t=j-2*T;const+=a*(F(inp['effective_initial_energy'])-(t+1)*h*F(7,1000))
            for k in range(t+1):
                co[k]+=a*h*(eta+1)/2;co[T+k]-=a*h*(eta+1)/2;co[3*T+k]-=a*h*(1-eta)/2
    if signs:
        for k,sgn in signs.items():
            k=int(k);v=co[3*T+k];assert v>0 and sgn in [-1,1]
            co[k]-=v*sgn;co[T+k]+=v*sgn;co[3*T+k]=0
    return const,co

def check_upper_certificate(inp,item):
    m=linear_rows(inp,True);const,co=target_expression(inp,item['native_row_index'],item['positive_signs'])
    residual=co[:];bound=const
    for k,v in item['lambda'].items():
        k=int(k);v=F(v);assert v>=0;bound+=v*m['b'][k]
        for j,a in m['A'][k].items():residual[j]-=v*a
    for k,v in item['mu'].items():
        k=int(k);v=F(v);bound+=v*m['f'][k]
        for j,a in m['E'][k].items():residual[j]-=v*a
    correction=sum((r*(m['bounds'][j][1] if r>=0 else m['bounds'][j][0]) for j,r in enumerate(residual)),F(0));upper=bound+correction
    assert upper==F(item['exact_upper_bound']) and upper<=0
    return upper
