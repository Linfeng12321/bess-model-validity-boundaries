from pathlib import Path
import sys,os,json,hashlib,time,ctypes,csv
O=Path(__file__).resolve().parents[1]; ROOT=O.parent
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'RESEARCH/round2/dependencies'),str(ROOT/'RESEARCH/round2/z3_dependencies')]
def now():
    from datetime import datetime,timezone
    return datetime.now(timezone.utc).isoformat()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def atomic(p,v,replace=False):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    text=v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)
    tmp=p.with_name(p.name+'.tmp.'+str(os.getpid()))
    with tmp.open('x',encoding='utf-8',newline='') as f:f.write(text);f.flush();os.fsync(f.fileno())
    if replace:os.replace(tmp,p)
    else:os.rename(tmp,p) # Windows rename fails if destination exists; immutable results.
def csvwrite(p,rows,fields=None):
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
def memory():
    class M(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('available',ctypes.c_ulonglong),('totalpage',ctypes.c_ulonglong),('availpage',ctypes.c_ulonglong),('totalvirtual',ctypes.c_ulonglong),('availvirtual',ctypes.c_ulonglong),('extended',ctypes.c_ulonglong)]
    m=M();m.length=ctypes.sizeof(M);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return dict(total_bytes=m.total,available_bytes=m.available,load_percent=m.load)
def peak_memory():
    class P(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
    p=P();p.cb=ctypes.sizeof(P)
    h=ctypes.windll.kernel32.GetCurrentProcess
    h.restype=ctypes.c_void_p
    ok=ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(h()),ctypes.byref(p),p.cb)
    return p.PeakWorkingSetSize if ok else None
def impl_hash():
    return digest({p.name:sha(p) for p in sorted((O/'implementation_v1_0').glob('*.py'))})
def verify_freeze():
    q=read(O/'00_PROTOCOL/FREEZE_MANIFEST.json')
    for name,expected in q['files'].items():
        if sha(O/name)!=expected:raise RuntimeError('FROZEN_HASH_CONFLICT:'+name)
    return q
