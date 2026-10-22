import sys, numpy as np; sys.path.insert(0, '/workspace/uad3'); import an_prog_lib as AP, prelib, models as Mo
d = {}
for u in Mo.PRESET_UNIT.values(): d['h1_' + u] = AP.h1(u); d['gss_' + u] = np.array(AP.g_ss(u))
for p in ('neve', 'u610a'): d['klin_' + p] = prelib.klin(p)
np.savez('/workspace/uad3/kernels.npz', **d); print(list(d))
