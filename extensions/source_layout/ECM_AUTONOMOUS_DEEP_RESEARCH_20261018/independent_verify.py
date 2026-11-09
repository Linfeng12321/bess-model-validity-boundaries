"""Independent physical equations and cvc5 formulation. No model.py import.

All rationals come from exact strings. This verifies full retained g/f/angles,
not just device projections or outcomes of the producer's selected LP.
"""
from pathlib import Path
from fractions import Fraction as Q
from collections import Counter
import copy,csv,hashlib,json,time
import cvc5
D=Path(__file__).resolve().parent;K=D/'00_AUTHORITY_CONTROL/PREVIOUS_CORE';S=json.loads((K/'02_PROTOCOL/NORMALIZED_RTS_INPUT.json').read_text())
G=len(S['generators']);L=len(S['lines']);B=len(S['buses']);C=24*(G+L+B);F0=24*G;A0=24*(G+L)
def read_vector(v):
    assert len(v)==C+72
    assert all(type(x) is str for x in v),'Exact proof coordinates must be rational strings, not floating objects'
    return list(map(Q,v))
def physics(cfg,values,exclusive=False):
    v=read_vector(values);eta=Q(17,20) if cfg['loss'] else Q(1);energy=Q(cfg['e0']);bad=[];count=0;bi={b['id']:i for i,b in enumerate(S['buses'])}
    def test(name,x,equal=False):
        nonlocal count
        count+=1
        if x!=0 if equal else x>0:bad.append((name,str(x)))
    for t in range(24):
        for j,g in enumerate(S['generators']):
            x=v[t*G+j];test('g_lower',-x);test('g_upper',x-Q(g['upper'][t]))
            if t:test('g_ramp_up',x-v[(t-1)*G+j]-Q(g['ramp']));test('g_ramp_down',v[(t-1)*G+j]-x-Q(g['ramp']))
        a=v[A0+t*B:A0+(t+1)*B];fl=v[F0+t*L:F0+(t+1)*L];test('reference',a[0],True)
        for j,line in enumerate(S['lines']):
            test('flow_upper',fl[j]-Q(line['limit']));test('flow_lower',-fl[j]-Q(line['limit']));test('dc_flow',fl[j]-Q(line['susceptance'])*(a[bi[line['from_bus']]]-a[bi[line['to_bus']]]),True)
        cc,dd,ee=v[C+t],v[C+24+t],v[C+48+t]
        for bus in S['buses']:
            value=sum((v[t*G+j] for j,g in enumerate(S['generators']) if g['bus']==bus['id']),Q(0))-Q(bus['load'][t])
            if bus['id']==313:value+=dd-cc
            value+=sum((fl[j] for j,line in enumerate(S['lines']) if line['to_bus']==bus['id']),Q(0));value-=sum((fl[j] for j,line in enumerate(S['lines']) if line['from_bus']==bus['id']),Q(0));test('nodal_balance',value,True)
        test('charge_lower',-cc);test('charge_upper',cc-50);test('discharge_lower',-dd);test('discharge_upper',dd-50);test('shared',cc+dd-50)
        test('energy_lower',-ee);test('energy_upper',ee-150);test('tail_lower',ee-150);test('tail_upper',-ee)
        test('energy_balance',ee-energy-eta*cc+dd,True);energy=ee
        if cfg['taper']:test('taper',cc+ee/3-50)
        if exclusive:test('exclusive',cc*dd,True)
    return dict(pass_all=not bad,rows=count,violations=bad)
def reconstruct(cfg,values):
    v=read_vector(values);c=[];d=[];en=[];energy=Q(cfg['e0']);eta=Q(17,20) if cfg['loss'] else Q(1)
    for t in range(24):
        p=v[C+24+t]-v[C+t];ct=max(-p,Q(0));dt=max(p,Q(0));energy+=eta*ct-dt;c.append(ct);d.append(dt);en.append(energy)
    return list(map(str,v[:C]+c+d+en))
def policy_check(policy):
    assert policy['source_sha256']==hashlib.sha256((K/'02_PROTOCOL/NORMALIZED_RTS_INPUT.json').read_bytes()).hexdigest()
    assert policy['query']=='p plus ALL g/f/angles' and policy['power_box']==['-50','50']
    j=policy['generator_index'];gen=S['generators'][j];assert gen['id']==policy['generator_id']=='313_CC_1' and gen['bus']==313
    assert policy['policy']=='g313[t]=355/2-p[t]; all other retained coordinates equal exact baseline'
    baseline=read_vector(policy['baseline_vector']);basecfg=dict(network=True,loss=False,taper=False,e0='75')
    assert physics(basecfg,policy['baseline_vector'],True)['pass_all']
    for t in range(24):
        assert baseline[t*G+j]==Q(355,2)
        assert baseline[C+t]==baseline[C+24+t]==0 and baseline[C+48+t]==75
        assert Q(355,2)-50>=0 and Q(355,2)+50<=Q(gen['upper'][t])
        if t:assert 100<=Q(gen['ramp'])
    # Every original bus/flow/ramp row is present in the direct physical replay;
    # symbolic retained injection change is (-p from colocated gen)+(p storage)=0.
    assert Q(policy['worst_ramp'])==100 and policy['generator_policy_range']==['255/2','455/2']
    assert Q(policy['source_ramp'])==Q(gen['ramp'])
    return True
def taper_coefficient(row):
    t=int(row['hour'])-1;co={k:Q(v) for k,v in json.loads(row['coefficients_json']).items()}
    assert co=={'charge_'+str(t):Q(1),'energy_'+str(t):Q(1,3)} and Q(row['rhs'])==50 and row['sense']=='<='
def expected_inputs():
    out={}
    for cfg in json.loads((K/'02_PROTOCOL/REGISTERED_SYSTEM_DESIGNS.json').read_text()):
        if not cfg['network']:continue
        cid=cfg['case_id'];out[(cid,'old')]=cfg
        r=json.loads((D/'03_RTS_EXACT_NETWORK/R1'/(cid+'_old_EXACT_ECONOMIC_RECOVERY.json')).read_text());assert r['status']=='EXACT_NEARBY_FEASIBLE'
        assert physics(cfg,r['exact_vector'],True)['pass_all'];v=read_vector(r['exact_vector']);assert str(v[C+48])==r['first_action']['E1']
        original=json.loads((K/'03_SYSTEM_FINAL/RUNS'/(cid+'_old.json')).read_text())['stages']['economic_exclusive']
        for j,(x,y) in enumerate(zip(v,original['vector'])):assert abs(x-Q(str(y)))<=(Q(1,10**7) if A0<=j<C else Q(1,10**5))
        cost=sum((v[t*G+j]*Q(g['cost']) for t in range(24) for j,g in enumerate(S['generators'])),Q(0));assert cost==Q(r['cost']) and cost<=Q(str(original['cost']))+max(Q(1,100),abs(Q(str(original['cost'])))/10**8)
        out[(cid,'new')]=dict(cfg,state='new',e0=str(v[C+48]))
    return out
def guard_register():
    rows=list(csv.DictReader((D/'03_RTS_EXACT_NETWORK/FULL_NETWORK_NATIVE_ROW_REGISTER.csv').open(encoding='utf-8')))
    return {cid:{r['row_id']:r for r in rows if r['case_id']==cid and r['scope']=='QUERY_SET_NATIVE'} for cid in {r['case_id'] for r in rows}}
def validate(obj,expected,register,policy):
    cfg=obj['input'];key=(cfg['case_id'],cfg['state']);assert cfg==expected[key],('INPUT_ID_OR_COEFFICIENT_MISMATCH',key)
    assert set(cfg)=={'case_id','state','e0','network','loss','taper'}
    assert obj['query']=='complete(p,allg,allf,alla)'
    assert obj['source_sha256']==policy['source_sha256'];assert obj['policy_certificate_sha256']==hashlib.sha256((D/'03_RTS_EXACT_NETWORK/R2/UNIVERSAL_NETWORK_EXTENSION_CERTIFICATE.json').read_bytes()).hexdigest()
    assert physics(cfg,obj['exact_relaxed_vector'])['pass_all']
    if obj['classification']=='EQ':
        assert not cfg['loss'] and physics(cfg,obj['exact_relaxed_vector'],True)['pass_all']
        guards={r['row']:r for r in obj['guards']};assert len(guards)==len(obj['guards'])==obj['declared_native_rows']==len(register[cfg['case_id']]);assert set(guards)==set(register[cfg['case_id']])
        for name,guard in guards.items():
            row=register[cfg['case_id']][name];co=json.loads(row['coefficients_json']);assert guard['family']==row['family']
            if row['family']=='CHARGE_SOC_END':taper_coefficient(row)
            if row['family'] in ('CHARGE_LOWER','DISCHARGE_LOWER'):continue
            coeff=[Q(co.get('charge_'+str(t),'0'))+Q(co.get('discharge_'+str(t),'0')) for t in range(24)]
            if row['sense']=='=':assert all(x==0 for x in coeff)
            else:assert all(x>=0 for x in coeff)
    else:
        assert obj['classification']=='STRICT';lift=reconstruct(cfg,obj['exact_relaxed_vector']);assert lift==obj['exact_reference_candidate']
        assert lift[:C]==obj['exact_relaxed_vector'][:C]
        assert all(Q(lift[C+24+t])-Q(lift[C+t])==Q(obj['exact_relaxed_vector'][C+24+t])-Q(obj['exact_relaxed_vector'][C+t]) for t in range(24))
        failed=physics(cfg,lift,True);assert not failed['pass_all'] and any(name=='energy_upper' and Q(v)>0 for name,v in failed['violations'])
    return True
def independent_cvc(cfg,policy):
    solver=cvc5.Solver();solver.setLogic('QF_LRA');solver.setOption('produce-models','true');solver.setOption('tlimit-per','60000');real=solver.getRealSort();kind=cvc5.Kind
    const=lambda x:solver.mkReal(str(Q(x)))
    add=lambda xs:xs[0] if len(xs)==1 else solver.mkTerm(kind.ADD,*xs) if xs else const(0)
    mul=lambda a,b:solver.mkTerm(kind.MULT,a,b)
    sub=lambda a,b:solver.mkTerm(kind.SUB,a,b)
    cc=[solver.mkConst(real,'independent_c_'+str(t)) for t in range(24)];dd=[solver.mkConst(real,'independent_d_'+str(t)) for t in range(24)];ee=[solver.mkConst(real,'independent_e_'+str(t)) for t in range(24)];eta=const(Q(17,20) if cfg['loss'] else 1)
    for t in range(24):
        for x in (cc[t],dd[t],ee[t]):solver.assertFormula(solver.mkTerm(kind.GEQ,x,const(0)))
        solver.assertFormula(solver.mkTerm(kind.LEQ,add([cc[t],dd[t]]),const(50)));solver.assertFormula(solver.mkTerm(kind.LEQ,ee[t],const(150)));solver.assertFormula(solver.mkTerm(kind.LEQ,dd[t],cc[t]))
        solver.assertFormula(solver.mkTerm(kind.EQUAL,ee[t],add([ee[t-1] if t else const(cfg['e0']),mul(eta,cc[t]),mul(const(-1),dd[t])])))
        if cfg['taper']:solver.assertFormula(solver.mkTerm(kind.LEQ,add([cc[t],mul(const(Q(1,3)),ee[t])]),const(50)))
    exclusive_final=add([const(cfg['e0'])]+[mul(eta,sub(c,d)) for c,d in zip(cc,dd)]);solver.assertFormula(solver.mkTerm(kind.GT,exclusive_final,const(151)))
    start=time.perf_counter();ans=solver.checkSat();out=dict(input=cfg,status=str(ans),wall_seconds=time.perf_counter()-start,meaning='Independent all-charge existential search after verified full-box network completion;UNSATsubsetaloneisNOTglobalEQ')
    if ans.isSat():
        val=lambda x:Q(solver.getValue(x).getRealValue());device=[val(x) for part in (cc,dd,ee) for x in part];v=read_vector(policy['baseline_vector']);j=policy['generator_index']
        for t in range(24):v[t*G+j]=Q(355,2)-(device[24+t]-device[t])
        full=list(map(str,v[:C]+device));assert physics(cfg,full)['pass_all'];assert not physics(cfg,reconstruct(cfg,full),True)['pass_all'];out['exact_full_vector']=full
    return out
def main():
    start=time.perf_counter();policy=json.loads((D/'03_RTS_EXACT_NETWORK/R2/UNIVERSAL_NETWORK_EXTENSION_CERTIFICATE.json').read_text());policy_check(policy);expected=expected_inputs();register=guard_register();rows=[];objects=[]
    cross=D/'05_INDEPENDENT_CHECKS/CVC5_INDEPENDENT_MODELS';cross.mkdir(exist_ok=True)
    for p in sorted((D/'03_RTS_EXACT_NETWORK/RTS_EXACT_CERTIFICATES').glob('*CERTIFICATE.json')):
        obj=json.loads(p.read_text());validate(obj,expected,register,policy);alt=independent_cvc(obj['input'],policy);assert alt['status']==('sat' if obj['input']['loss'] else 'unsat')
        (cross/p.name).write_text(json.dumps(alt,indent=2));objects.append(obj);rows.append(dict(case_id=obj['input']['case_id'],state=obj['input']['state'],e0=obj['input']['e0'],classification=obj['classification'],native_and_query='PASS',independent_solver='cvc5',existential_subset_result=alt['status'],EQ_full_native_guard_checked=obj['classification']=='EQ'))
    assert len(rows)==8 and Counter(x['classification'] for x in rows)=={'EQ':4,'STRICT':4}
    rejected=[]
    def attack(name,operation):
        try:operation()
        except (AssertionError,KeyError,IndexError,ValueError,TypeError):rejected.append(dict(test=name,rejected=True));return
        raise AssertionError('Corruption accepted: '+name)
    eq=next(o for o in objects if o['classification']=='EQ' and o['input']['taper']);strict=next(o for o in objects if o['classification']=='STRICT')
    x=copy.deepcopy(eq);x['guards'].pop();attack('missing_native_row_guard',lambda:validate(x,expected,register,policy))
    x=copy.deepcopy(eq);x['query']='p_only';attack('dropped_retained_generation_flow_angle_query',lambda:validate(x,expected,register,policy))
    for name,value in [('eta_c','1'),('rho','99/100'),('h','60')]:
        x=copy.deepcopy(strict);x['input'][name]=value;attack('undeclared_or_changed_'+name,lambda:validate(x,expected,register,policy))
    x=copy.deepcopy(strict);x['exact_relaxed_vector'][F0]=str(Q(x['exact_relaxed_vector'][F0])+1);attack('branch_DC_constraint_violation',lambda:validate(x,expected,register,policy))
    x=copy.deepcopy(strict);v=x['exact_relaxed_vector'];v[:24*G]=v[G:24*G]+v[:G];attack('hour_index_shift',lambda:validate(x,expected,register,policy))
    x=copy.deepcopy(eq);x['input']['e0']=str(Q(x['input']['e0'])+1);attack('wrong_parameter_state_certificate',lambda:validate(x,expected,register,policy))
    x=copy.deepcopy(strict);x['exact_relaxed_vector'][0]=float(Q(x['exact_relaxed_vector'][0]));attack('floating_substitution_for_exact_coordinate',lambda:validate(x,expected,register,policy))
    x=copy.deepcopy(strict);x['exact_reference_candidate'][0]=str(Q(x['exact_reference_candidate'][0])+1);attack('retained_z_changed_by_reconstruction',lambda:validate(x,expected,register,policy))
    x=copy.deepcopy(eq);x['input']['e0']='-1000';attack('empty_parameter_domain_identity',lambda:validate(x,expected,register,policy))
    x=copy.deepcopy(eq);x.pop('exact_relaxed_vector');attack('EQ_without_nonempty_exact_point',lambda:validate(x,expected,register,policy))
    x=copy.deepcopy(policy);x['source_ramp']='99';attack('incorrect_network_extension_ramp_bound',lambda:policy_check(x))
    # Canonical source coefficients prevent flipping the SOC power-row sign.
    taper_row=next(r for r in register[eq['input']['case_id']].values() if r['family']=='CHARGE_SOC_END');co=json.loads(taper_row['coefficients_json']);assert Q(co['energy_0'])==Q(1,3)
    badrow=dict(taper_row,coefficients_json=json.dumps(dict(co,energy_0='-1/3')));attack('SOC_power_row_sign',lambda:taper_coefficient(badrow))
    x=copy.deepcopy(eq);reg=copy.deepcopy(register);extra=dict(taper_row,row_id='minimum_throughput',family='MIN_THROUGHPUT',coefficients_json=json.dumps({'charge_0':'-1','discharge_0':'-1'}),rhs='-1')
    reg[x['input']['case_id']]['minimum_throughput']=extra;x['declared_native_rows']+=1;x['guards'].append(dict(row='minimum_throughput',family='MIN_THROUGHPUT',reason='forgedautomaticguard'))
    attack('arbitrary_lossless_minimum_throughput_guard',lambda:validate(x,expected,reg,policy))
    result=dict(status='PASS',case_records=rows,distinct_network_parameter_states=len({(x['case_id'],x['e0']) for x in rows}),policy_check='EXACT_FULL24H_BOX_PASS',old_economic_exact_recovery_checks=4,independent_full_physical_native_equations=True,independent_cvc5_fresh_models=8,negative_tests=rejected,wall_seconds=time.perf_counter()-start,external_host_review=False,scope='No new objective-exactness or theorem;all-chargeUNSATdiagnosticisnotglobalEQproof')
    (D/'05_INDEPENDENT_CHECKS/NETWORK_INDEPENDENT_QA.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
