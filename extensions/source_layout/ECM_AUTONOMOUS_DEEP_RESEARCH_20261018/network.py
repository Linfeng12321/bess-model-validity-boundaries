"""Exact connected DC network completion; no optimization outcomes are assumed."""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,time
import sympy as sp
from model import D,data
CACHE=D/'03_RTS_EXACT_NETWORK/NETWORK_COMPLETION_MAP.json'
def fraction(q):return F(int(q.p),int(q.q))
def compute():
    src=data();B=len(src['buses']);index={b['id']:i for i,b in enumerate(src['buses'])};M=[[F(0) for _ in range(B-1)] for _ in range(B-1)]
    for l in src['lines']:
        i=index[l['from_bus']];j=index[l['to_bus']];beta=F(l['susceptance'])
        if i:M[i-1][i-1]+=beta
        if j:M[j-1][j-1]+=beta
        if i and j:M[i-1][j-1]-=beta;M[j-1][i-1]-=beta
    return M,index
def load_map():
    obj=json.loads(CACHE.read_text());return [[F(v) for v in row] for row in obj['inverse']]
def main():
    start=time.perf_counter();M,index=compute();A=sp.Matrix([[sp.Rational(v.numerator,v.denominator) for v in r] for r in M]);inverse=A.inv(method='DM');inv=[[fraction(inverse[i,j]) for j in range(len(M))] for i in range(len(M))]
    # Machine-verified inverse with sparse physical rows, no floating residual.
    for i,row in enumerate(M):
        nz=[(k,a) for k,a in enumerate(row) if a]
        for j in range(len(M)):assert sum((a*inv[k][j] for k,a in nz),F(0))==int(i==j)
    obj=dict(status='PASS',method='rational reduced Laplacian inverse with exact sparse identity replay',bus_order=list(index),reference_bus=next(iter(index)),inverse=[[str(v) for v in r] for r in inv],dimension=len(M),wall_seconds=time.perf_counter()-start,maximum_denominator_bits=max(v.denominator.bit_length() for r in inv for v in r))
    CACHE.write_text(json.dumps(obj,indent=2));print(json.dumps({k:v for k,v in obj.items() if k not in ('inverse','bus_order')},indent=2))
def complete(src,g,c,d,inv):
    B=len(src['buses']);L=len(src['lines']);G=len(src['generators']);index={b['id']:i for i,b in enumerate(src['buses'])};angles=[];flows=[]
    for t in range(24):
        injection=[-F(b['load'][t]) for b in src['buses']]
        for j,gen in enumerate(src['generators']):injection[index[gen['bus']]]+=g[t*G+j]
        injection[index[313]]+=d[t]-c[t]
        assert sum(injection,F(0))==0,('total_balance',t)
        a=[F(0)]+[sum((v*b for v,b in zip(row,injection[1:])),F(0)) for row in inv]
        angles.extend(a);flows.extend(F(l['susceptance'])*(a[index[l['from_bus']]]-a[index[l['to_bus']]]) for l in src['lines'])
    return g+flows+angles
if __name__=='__main__':main()
