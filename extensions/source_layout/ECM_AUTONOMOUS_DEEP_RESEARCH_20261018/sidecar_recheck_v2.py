"""New direct internal-device row/dual reconstruction, no frozen-builder import."""
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
import copy,csv,hashlib,itertools,json,time
D=Path(__file__).resolve().parent;K=D/'00_AUTHORITY_CONTROL/PREVIOUS_CORE';W=K/'00_PREVIOUS_EVIDENCE'
def model(i):
    T=i['T'];eta=F(i['eta_c']);h=F(i['h']);e0=F(i['effective_initial_energy']);assert F(i['eta_d'])==F(i['rho'])==1;A=[];b=[];families=[];eq=[];rhs=[]
    def row(f,co,limit):A.append({j:F(a) for j,a in co.items() if a});b.append(F(limit));families.append(f)
    for t in range(T):
        c=t;d=T+t;e=2*T+t
        row('NONNEG',{c:-1},0);row('NONNEG',{d:-1},0);row('HULL',{c:1,d:1},F(1,2));row('E_UP',{e:1},F(57,100));row('E_LO',{e:-1},-F(3,25))
        co={e:F(1),c:-h*eta,d:h}
        if t:co[e-1]=-F(1)
        eq.append(co);rhs.append(e0-h*F(7,1000) if not t else -h*F(7,1000))
        for j in (t-1,t):
            cc={c:F(1)};dd={d:F(1)}
            if i['row_form']=='N':cc[d]=-F(1);dd[c]=-F(1)
            cr=F(50,3)*F(57,100);dr=-F(25,3)*F(3,25)
            if j<0:cr-=F(50,3)*e0;dr+=F(25,3)*e0
            else:cc[2*T+j]=F(50,3);dd[2*T+j]=-F(25,3)
            row('CHARGE',cc,cr);row('DISCHARGE',dd,dr)
    return T,eta,h,e0,A,b,families,eq,rhs
def feasible(m,v):
    T,eta,h,e0,A,b,fam,E,f=m;v=list(map(F,v));assert len(v)==3*T
    assert all(sum((a*v[j] for j,a in co.items()),F(0))<=r for co,r in zip(A,b));assert all(sum((a*v[j] for j,a in co.items()),F(0))==r for co,r in zip(E,f));return v
def reconstruct(m,v):
    T,eta,h,e0,*_=m;outc=[];outd=[];en=[];e=e0
    for t in range(T):
        p=v[T+t]-v[t];c=max(-p,F(0));d=max(p,F(0));e+=h*(eta*c-d-F(7,1000));outc.append(c);outd.append(d);en.append(e)
    return outc+outd+en
def m1(p):
    m=model(p['input']);T,eta,h,e0,A,b,fam,E,f=m;assert eta==1
    assert set(p['covered_native_families'])=={'flow_nonnegativity','shared_rating','energy_bounds','energy_dynamics','charge_start','charge_end','discharge_start','discharge_end'}
    x=feasible(m,p['nonempty_vector']);assert reconstruct(m,x)==x
    for co,k in zip(A,fam):
        if k!='NONNEG':assert all(co.get(t,0)+co.get(T+t,0)>=0 for t in range(T))
    assert all(co.get(t,0)+co.get(T+t,0)==0 for co in E for t in range(T));return len(A)+len(E)
def transforms(m):
    T,eta,h,e0,A,b,fam,E,f=m;alpha=(eta+1)/2;kappa=1-eta;out={}
    for k,(co,r,family) in enumerate(zip(A,b,fam)):
        if family not in ('E_UP','E_LO','CHARGE','DISCHARGE'):continue
        ell=[];v=[]
        for t in range(T):
            propagated=h*sum((co.get(2*T+j,F(0)) for j in range(t,T)),F(0));ac=co.get(t,F(0));ad=co.get(T+t,F(0))
            ell.append((ad-ac)/2-alpha*propagated);v.append((ac+ad-kappa*propagated)/2)
        constant=sum((co.get(2*T+j,F(0))*(e0-(j+1)*h*F(7,1000)) for j in range(T)),F(0))-r
        out[k]=dict(ell=ell,v=v,constant=constant,positive=[j for j,x in enumerate(v) if x>0])
    return out
def m2(p):
    m=model(p['input']);T,eta,h,e0,A,b,fam,E,f=m;feasible(m,p['nonempty_vector']);tr=transforms(m);assert set(tr)==set(p['full_target_rows']);auto=set(p['automatic_native_rows']);seen={}
    for k in auto:assert k in tr and all(x>=0 for x in tr[k]['v'])
    A=list(A);b=list(b)
    for t in range(T):A.extend([{T+t:F(1),t:F(-1),3*T+t:F(-1)},{t:F(1),T+t:F(-1),3*T+t:F(-1)}]);b.extend([F(0),F(0)])
    box=[(F(0),F(1,2))]*(2*T)+[(F(3,25),F(57,100))]*T+[(F(0),F(1,2))]*T
    for proof in p['row_upper_certificates']:
        k=proof['native_row_index'];t=tr[k];assert k not in auto;s={int(j):v for j,v in proof['positive_signs'].items()};assert set(s)==set(t['positive']) and set(s.values())<={-1,1}
        target=[-x for x in t['ell']]+t['ell']+[F(0)]*T+t['v'][:];upper=t['constant']
        for j,sign in s.items():a=target[3*T+j];target[j]-=a*sign;target[T+j]+=a*sign;target[3*T+j]=F(0)
        for j,weight in proof['lambda'].items():
            j=int(j);weight=F(weight);assert weight>=0;upper+=weight*b[j]
            for col,a in A[j].items():target[col]-=weight*a
        for j,weight in proof['mu'].items():
            j=int(j);weight=F(weight);upper+=weight*f[j]
            for col,a in E[j].items():target[col]-=weight*a
        upper+=sum((a*(hi if a>=0 else lo) for a,(lo,hi) in zip(target,box)),F(0));assert upper==F(proof['exact_upper_bound']) and upper<=0
        seen.setdefault(k,set()).add(tuple(s[j] for j in sorted(s)))
    for k,t in tr.items():
        if k not in auto:assert seen.get(k)==set(itertools.product((-1,1),repeat=len(t['positive'])))
    return len(p['row_upper_certificates'])
def m3(p):
    m=model(p['input']);x=feasible(m,p['relaxed_vector']);y=reconstruct(m,x);A,b=m[4:6];bad=[k for k,(co,r) in enumerate(zip(A,b)) if sum((a*y[j] for j,a in co.items()),F(0))>r];assert bad;return len(bad)
def main():
    start=time.perf_counter();old=json.loads((W/'04_CERTIFICATION/ORIGINAL_936_INPUTS_AND_STATUSES.json').read_text());byid={r['input']['case_id']:r for r in old};assert Counter(r['original_status'] for r in old)=={'EQ':277,'STRICT':331,'TIMEOUT':152,'NOT_APPLICABLE':176}
    rows=list(csv.DictReader((W/'04_CERTIFICATION/NEW_CERTIFICATE_SIDECAR.csv').open(encoding='utf-8-sig')));summ=[];examples={};newstatus={}
    for r in rows:
        file=W/r['certificate_file'];assert hashlib.sha256(file.read_bytes()).hexdigest()==r['certificate_sha256'];o=json.loads(file.read_text());p=o if r['method']=='M1' else o['proof'];assert p['input']==byid[r['case_id']]['input'] and byid[r['case_id']]['original_status']=='TIMEOUT'
        count={'M1':m1,'M2':m2,'M3':m3}[r['method']](p);summ.append(dict(case_id=r['case_id'],method=r['method'],new_status=r['NEW_STATUS'],checked_objects=count));examples.setdefault(r['method'],p);newstatus[r['case_id']]=r['NEW_STATUS']
    assert Counter(r['method'] for r in summ)=={'M1':104,'M2':45,'M3':3};assert sum(r['checked_objects'] for r in summ if r['method']=='M2')==3417
    negative=[]
    def rejects(name,obj,fn):
        try:fn(obj)
        except (AssertionError,KeyError,ValueError,IndexError):negative.append(dict(test=name,rejected=True));return
        raise AssertionError('Forged proof accepted')
    p=copy.deepcopy(examples['M2']);p['row_upper_certificates'][0]['lambda']['0']='-1';rejects('negative_dual_multiplier',p,m2)
    p=copy.deepcopy(examples['M2']);p['row_upper_certificates'].pop();rejects('missing_EQ_sign_branch',p,m2)
    pairs={r['input']['paired_setting_id'] for r in old};combinations=Counter();added=[]
    for pid in sorted(pairs):
        before=byid[pid+'_old'];after=byid[pid+'_new'];a=newstatus.get(pid+'_old',before['original_status']);b=newstatus.get(pid+'_new',after['original_status']);combinations[a+'/'+b]+=1
        if a=='EQ' and b=='STRICT' and before['original_status']!='EQ':
            i=before['input'];assert F(after['input']['effective_initial_energy'])==F(i['effective_initial_energy'])+F(i['h'])*(F(i['eta_c'])/2-F(7,1000))
            one=dict(i,T=1);action=[F(1,2),F(0),F(after['input']['effective_initial_energy'])];feasible(model(one),action)
            original=K/'08_RESULTS_AND_ADMISSION/DERIVED_TRANSITIONS'/(pid+'_new.json');assert hashlib.sha256(original.read_bytes()).hexdigest()==after['source_sha256'];obj=json.loads(original.read_text());w=list(obj.get('witnesses',[]))
            for route in obj['routes'].values():
                w+=route.get('witnesses',[])
                if route.get('witness'):w.append(route['witness'])
            w=[x for x in w if x.get('certified')];qualified=False
            for witness in w:
                m=model(after['input']);v=feasible(m,witness['relaxed_vector']);rec=reconstruct(m,v);T=m[0];A,rhs=m[4:6];failed=[k for k,(co,r) in enumerate(zip(A,rhs)) if sum((aa*rec[j] for j,aa in co.items()),F(0))>r]
                if all(F(3,25)<=x<=F(57,100) for x in rec[2*T:]) and any(m[6][k] in ('CHARGE','DISCHARGE') for k in failed):qualified=True
            assert qualified;added.append(pid)
    assert len(added)==18 and combinations=={'EQ/EQ':172,'EQ/STRICT':82,'STRICT/STRICT':126,'NOT_APPLICABLE/NOT_APPLICABLE':88}
    result=dict(status='PASS',original936=dict(Counter(r['original_status'] for r in old)),same152_methods=dict(Counter(r['method'] for r in summ)),M2_bound_objects=3417,newly_qualified_pairs=added,pair_combinations=dict(combinations),negative_tests=negative,independence='New direct native-matrix/propagation/weak-dual arithmetic;no frozen builder or its transforms imported',wall_seconds=time.perf_counter()-start)
    (D/'05_INDEPENDENT_CHECKS/SIDECAR_AND_PAIR_NEW_IMPLEMENTATION_QA.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
