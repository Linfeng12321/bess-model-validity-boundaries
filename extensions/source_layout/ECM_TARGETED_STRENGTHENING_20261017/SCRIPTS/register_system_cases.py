from pathlib import Path
from fractions import Fraction as F
import json,csv,hashlib,datetime
W=Path(__file__).resolve().parents[1];P=W/'03_SYSTEM_CASE/PUBLIC_SOURCE_REVIEW'
with (P/'ac-dc-meshed_loads-p_set.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
assert list(rows[0])[1]=='London';values=[F(r['London']) for r in rows];profile=[str(100*v/max(values)) for v in values[:4]]
cases=[]
for profile_name,load in [('PUBLIC_FIRST_FOUR',profile),('SOURCE_FLAT_100',['100']*4)]:
    for device in ['BOX','TAPER']:
        for frac in [F(1,5),F(1,2),F(4,5)]:
            cases.append(dict(case_id=f'{profile_name}_{device}_E{frac.numerator}of{frac.denominator}',stage='PILOT' if profile_name=='PUBLIC_FIRST_FOUR' else 'CONTEXT_EXTENSION',profile=profile_name,T=4,load=load,device=device,eta_c='9/10',eta_d='19/20',rho='99/100',e0=str(6*frac),battery_bus='Bus1',power_MW='1',energy_MWh='6',battery_enabled=True,source_class='Public synthetic source network/profile; study specified battery and combination'))
cases.insert(6,dict(case_id='PUBLIC_FIRST_FOUR_BOX_LOSSLESS',stage='PILOT',profile='PUBLIC_FIRST_FOUR',T=4,load=profile,device='BOX',eta_c='1',eta_d='1',rho='99/100',e0='3',battery_bus='Bus1',power_MW='1',energy_MWh='6',battery_enabled=True,source_class='Lossless mathematical control; not a device-efficiency claim'))
obj=dict(registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),public_commit='23e243654c5657d8da3689d6baf5a03f3f3b455e',profile_source_sha256=hashlib.sha256((P/'ac-dc-meshed_loads-p_set.csv').read_bytes()).hexdigest(),network_notebook_sha256=hashlib.sha256((P/'PyPSA_docs_examples_negative-prices-kvl-baker.ipynb').read_bytes()).hexdigest(),cases=cases,stopping='Context extension requires a certified pilotcost/service gap or optimizedrequestfailure; generalcounterquery alone does not trigger expansion.')
(W/'03_SYSTEM_CASE/REGISTERED_SYSTEM_CASES.json').write_text(json.dumps(obj,indent=2),encoding='utf-8');print({'registered_cases':len(cases),'pilot':7,'conditional_context':6,'loads_exact':profile,'loads_display':list(map(float,map(F,profile)))})
