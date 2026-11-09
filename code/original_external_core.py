from pathlib import Path
from datetime import datetime, timezone
import json,hashlib,os,csv,uuid,shutil,time
B=Path(__file__).resolve().parents[1]
R=B.parent
A=R/'ECM_STAGE2_EXTERNAL_EVIDENCE_v1_0'
S1=R/'ECM_STAGE1_LONG_HORIZON_BRIDGE_v1_0'
def now(): return datetime.now(timezone.utc).isoformat()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4194304),b''): h.update(b)
    return h.hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def target(n):
    p=(B/n).resolve(); assert p.is_relative_to(B)
    p.parent.mkdir(parents=True,exist_ok=True)
    return p
def put(n,x):
    p=target(n)
    with p.open('x',encoding='utf-8',newline='') as f:
        f.write(x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False));f.flush();os.fsync(f.fileno())
def table(n,rs,fields=None):
    p=target(n)
    with p.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rs[0]));w.writeheader();w.writerows(rs);f.flush();os.fsync(f.fileno())
def append(n,x):
    p=target(n);exists=p.exists()
    with p.open('a',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(x))
        if not exists:w.writeheader()
        w.writerow(x);f.flush();os.fsync(f.fileno())
def snapshot(n,x):
    p=target(n);t=target('tmp/'+uuid.uuid4().hex+'.json')
    with t.open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
    for i in range(3):
        try:os.replace(t,p);return True
        except PermissionError:
            if i==2:append('logs/MONITORING_ERRORS.csv',dict(time=now(),status='MONITORING_DEGRADED',path=str(p)));return False
            time.sleep(.2)
def state(phase,next_action,**kw):
    p=B/'STAGE2B_STATE.json';s=read(p) if p.exists() else dict(started_utc=now(),stage2b_complete=False)
    s.update(timestamp=now(),current_phase=phase,next_action=next_action,**kw);snapshot('STAGE2B_STATE.json',s)
    elapsed=(datetime.now(timezone.utc)-datetime.fromisoformat(s['started_utc'])).total_seconds()
    h=dict(timestamp=now(),last_completed_case=kw.get('last_completed_case',''),current_phase=phase,current_horizon=kw.get('current_horizon',''),completed_cells=kw.get('completed_cells',0),expected_cells=kw.get('expected_cells',0),**{k:kw.get(k,0) for k in ['EQ','STRICT','EMPTY','UNKNOWN','TIMEOUT','BUDGET_EXCEEDED','NOT_APPLICABLE','ERROR']},elapsed_wall_time=elapsed,latest_checkpoint=kw.get('latest_checkpoint',''),free_disk_space=shutil.disk_usage(B).free)
    append('RUN_HEARTBEAT_APPEND_ONLY.csv',h);snapshot('RUN_HEARTBEAT.json',h)
