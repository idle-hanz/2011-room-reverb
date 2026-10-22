import numpy as np, json
from scipy.linalg import hadamard
H=hadamard(32)
def tau(i):
    b=[(i>>k)&1 for k in range(5)]; b[0],b[4]=b[4],b[0]; b[1],b[3]=b[3],b[1]
    return sum(v<<k for k,v in enumerate(b))
orb=[];seen=set()
for i in range(32):
    if i in seen: continue
    o={i,tau(i)}; seen|=o; orb.append(sorted(o))
print('orbits',len(orb))
best=None
import itertools
for bits in range(1<<len(orb)):
    s=np.ones(32)
    for k,o in enumerate(orb):
        if (bits>>k)&1:
            for i in o: s[i]=-1
    if s[0]<0: continue
    m=np.max(np.abs(H@s)); 
    if best is None or m<best[0] or (m==best[0] and np.sum(np.abs(H@s)==m)<best[2]): best=(m,s.copy(),int(np.sum(np.abs(H@s)==m)))
print('best max |H s|',best[0],'count',best[2]); print([int(v) for v in best[1]])
assert all(best[1][i]==best[1][tau(i)] for i in range(32))
json.dump({'s':[int(v) for v in best[1]],'max_walsh':int(best[0]),'tau':'(b0 b4)(b1 b3) invariant'},open('out_signs.json','w'))
