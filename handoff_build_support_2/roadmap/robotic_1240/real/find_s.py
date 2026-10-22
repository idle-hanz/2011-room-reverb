import numpy as np, json
from scipy.linalg import hadamard
H=hadamard(32)
rng=np.random.default_rng(1); best=None
for it in range(200000):
    s=rng.choice([-1,1],32)
    m=np.max(np.abs(H@s))
    if best is None or m<best[0]: best=(m,s.copy())
    if m<=8: break
print('max |H s|',best[0],'of 32; funnel max energy share',(best[0]/32)**2*1.0)
print(best[1].tolist())
json.dump({'s':best[1].tolist(),'max_walsh':int(best[0])},open('out_signs.json','w'))
