from core import *
from fractions import Fraction as F
from collections import Counter
from bisect import bisect_right
from datetime import datetime,timedelta
source=A/'04_WP3_REAL_SOURCE_TRAJECTORY/fallback_source/Elspotprices_DK1_2025_01.json'
data=json.loads(source.read_text(),parse_float=str)['records'];index={r['HourDK']:r for r in data};cal=sorted(F(r['SpotPriceEUR']) for r in data[:168]);out=[];windows=[]
p=dict(read(B/'03_EXTERNAL_DOMAIN_MAPS/ANCHOR_PARAMETERS_BATCH01_FROZEN.json')['anchors'][0]);p['T']=4;p['id']='POZO_SOURCE_COVERAGE_T4'
for label,start in [('EARLIEST','2025-01-08'),('MIDDLE','2025-01-16'),('LATEST','2025-01-25')]:
    e=F(55);energies=[]
    for i in range(169):
        t=datetime.fromisoformat(start)+timedelta(hours=i);endpoint=i==168;raw=index.get(t.isoformat());price=F(raw['SpotPriceEUR']) if raw and not endpoint else None
        target_e=F(30)+30*F(bisect_right(cal,price),len(cal)) if price is not None else e
        c=min(F(20),max(F(0),(target_e-e)/F(9,10)));d=min(F(20),max(F(0),(e-target_e)*F(19,20)));en=e+F(9,10)*c-d/F(19,20)
        assert c*d==0 and 30<=e<=60 and 30<=en<=60
        out.append(dict(window=label,index=i,timestamp_local=t.isoformat(),energy_kWh=str(e),SOC_fraction=str(e/60),charge_kW=str(c),discharge_kW=str(d),net_power_kW=str(d-c),next_energy_kWh=str(en),target_energy_kWh=str(target_e),price_EUR_MWh=str(price) if price is not None else '',endpoint=endpoint,source_sha256=sha(source),label='COVERAGE_ORIENTED_REAL_SOURCE_DRIVEN_SIMULATION_NOT_TELEMETRY',first_action_native_feasible=True))
        energies.append(e);e=en
    freq=Counter(energies);windows.append(dict(window=label,timestamps=len(energies),unique_energy=len(freq),engineering_bin_kWh='.06',unique_engineering_bins=len(set(e//F(3,50) for e in energies)),Emin=str(min(energies)),Emax=str(max(energies)),fraction_declared_domain=str((max(energies)-min(energies))/30),largest_exact_state_fraction=max(freq.values())/len(energies),at_lower=sum(e==30 for e in energies),at_upper=sum(e==60 for e in energies)))
table('08_REAL_SOURCE_COVERAGE/COVERAGE_TRAJECTORY_FROZEN.csv',out)
put('08_REAL_SOURCE_COVERAGE/COVERAGE_POLICY_FREEZE.json',dict(time=now(),source=str(source),source_sha256=sha(source),policy='preregistered bounded tracking of right-continuous empirical CDF of first168price observations; upward target with price as specified, no economic optimality claim',evaluation_excludes_calibration=True,source_parameters=p,windows=windows,trajectory_sha256=sha(B/'08_REAL_SOURCE_COVERAGE/COVERAGE_TRAJECTORY_FROZEN.csv')))
unique=sorted(set(F(r['energy_kWh']) for r in out));jobs=[dict(id=f'COVERAGE_UNIQUE_{i:04d}',parameters=p,e0=str(e),role='SOURCE_COVERAGE_UNIQUE_STATE') for i,e in enumerate(unique)]
table('08_REAL_SOURCE_COVERAGE/UNIQUE_STATE_LOOKUP.csv',[dict(case_id=j['id'],energy_kWh=j['e0']) for j in jobs])
code={str(B/'00_GOVERNANCE'/n):sha(B/'00_GOVERNANCE'/n) for n in ['worker_v1_1.py','mapping.py','verifier_v1_1.py','core.py','runtime_v1_2.py']}
put('08_REAL_SOURCE_COVERAGE/COVERAGE_MANIFEST.json',dict(phase='REAL_SOURCE_COVERAGE',output='08_REAL_SOURCE_COVERAGE/campaign',worker=str(B/'00_GOVERNANCE/worker_v1_1.py'),jobs=jobs,code_hashes=code,worker_wall_guard_seconds=345,smt_budget_seconds=300))
print('FROZEN',len(out),'timestamps',len(unique),'unique states',json.dumps(windows))
