from core import *
from fractions import Fraction as F
from mapping import build,row
from verifier_v1_1 import exact
import sys
job=read(sys.argv[1]);p=job['parameters'];model=build(p,job['e0'])
assert p['family']=='BOX' and p['terminal']=='fixed_floor'
model['rows'].append(row('terminal_floor','TERMINAL_LOWER',p['T']-1,{3*p['T']-1:-1},-F(p['terminal_floor'])))
result=exact(model);result.update(case_id=job['id'],input_hash=digest(job),model_hash=digest(model),completed_utc=now(),code_hashes={str(Path(__file__).parent/n):sha(Path(__file__).parent/n) for n in ['worker_terminal_v1_1.py','mapping.py','verifier_v1_1.py','core.py']})
out=Path(sys.argv[2]);assert out.resolve().is_relative_to(B)
with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.flush();os.fsync(f.fileno())
