import sys, json, numpy as np
sys.path.insert(0, '/workspace/uad3'); import targets as T, dyn3
from scipy.optimize import minimize
p = sys.argv[1]
SPEC = {  # free params: (lo, hi, log?)
 'glue': {'T': (-34, -24, 0), 'R': (2.5, 8, 1), 'W': (0, 12, 0), 'ta': (0.002, 0.02, 1), 't1': (0.01, 0.2, 1), 't2': (1.0, 10.0, 1)},
 'natural': {'T': (-30, -22, 0), 'a1': (0.0002, 0.003, 1), 'wf': (0.5, 0.97, 0), 'tf0': (0.01, 0.2, 1), 'tfm': (0.0, 0.3, 0), 'w0': (0.0, 0.6, 0), 'wm': (0.0, 0.6, 0),
             'ts': (0.3, 3.0, 1), 'tm': (0.05, 3.0, 1), 'tmd': (0.05, 3.0, 1), 'heavy_db': (8, 18, 0), 'kh': (0.0, 0.6, 0)},
 'room_crush': {'T': (-45, -30, 0), 'R': (2, 30, 1), 'W': (0, 15, 0), 'ta1': (0.0002, 0.003, 1), 'ta2': (0.001, 0.02, 1), 'wa': (0.2, 0.95, 0), 'tr': (0.01, 0.06, 1), 'beta': (0.0, 1.5, 0)},
 'nuke': {'T': (-30, -18, 0), 'ta': (0.0003, 0.003, 1), 'trf': (0.03, 0.3, 1), 'trs': (0.2, 2.0, 1), 'ws0': (0.0, 0.8, 0), 'wsg': (0.0, 0.6, 0), 'tg': (0.05, 3.0, 1)},
 'swell': {'T': (-32, -16, 0), 'R': (1.2, 6, 1), 'W': (0, 16, 0), 'R2': (1.2, 30, 1), 'K2': (2, 25, 0), 'ta': (0.001, 0.01, 1), 'RT': (2e4, 1e6, 1), 'RU': (2e4, 1e6, 1), 'CU': (1e-6, 4e-5, 1)},
}[p]
TGT_T63 = {'glue': 7.875, 'natural': 0.812, 'room_crush': 1.583, 'nuke': 0.896, 'swell': 3.417}[p]
LVM = {'glue': (-45, 12), 'natural': (-45, 12), 'room_crush': (-36, 6), 'nuke': (-45, 12), 'swell': (-30, 12)}[p]
keys = list(SPEC); base = dict(dyn3.DEF[p]); base['T'] = T.FIT[p]['T']
import os
if os.path.exists('/workspace/uad3/fit_%s.json' % p): base.update(json.load(open('/workspace/uad3/fit_%s.json' % p))['params'])
def tov(P): return np.array([(np.log(P[k]) if SPEC[k][2] else P[k]) for k in keys])
def fromv(v):
    P = dict(base)
    for k, z in zip(keys, v):
        lo, hi, lg = SPEC[k]; P[k] = float(np.clip(np.exp(z) if lg else z, lo, hi))
    return P
def lr(a, b): return np.log(max(a, 1e-3) / max(b, 1e-3)) if np.isfinite(a) and np.isfinite(b) else (0.0 if not np.isfinite(b) else 2.0)
LVs = np.array(T.LV); msk = (LVs >= LVM[0]) & (LVs <= LVM[1])
def cost(v, verbose=False):
    P = fromv(v); s = T.static(p, P); e = (s - T.UAD_STATIC[p])[msk]; c = np.mean(e ** 2) / 0.25 ** 2 * 0.5
    a = T.attack(p, P); c += (40 if p == 'glue' else 4) * lr(a['t63_ms'], TGT_T63) ** 2 / 0.1 ** 2 * 0.05
    if p == 'nuke': c += 0.2 * lr(a['t90_ms'], 1.667) ** 2 / 0.1 ** 2
    rows = T.bursts(p, P)
    for dep, bs, mu, m in rows:
        if p == 'room_crush': continue
        c += lr(m['rel63'], mu['rel63']) ** 2 / 0.15 ** 2
        if p in ('natural', 'nuke'): c += 0.5 * lr(m['rel90'], mu['rel90']) ** 2 / 0.15 ** 2
    if p == 'room_crush':
        for dep, bs, mu, m in rows: c += 2 * lr(m['rel63'], mu['rel63']) ** 2 / 0.25 ** 2
    if verbose: return P, s, a, rows, c
    return c
v0 = tov(base); best = (cost(v0), v0)
rng = np.random.default_rng(1)
for rs in range(4):
    st = best[1] if rs == 0 else best[1] + rng.normal(0, 0.15, len(v0))
    r = minimize(cost, st, method='Nelder-Mead', options=dict(maxiter=500 if p != 'swell' else 350, xatol=1e-3, fatol=1e-3, adaptive=True))
    if r.fun < best[0]: best = (r.fun, r.x)
    print(p, 'restart', rs, 'cost', round(float(r.fun), 3), 'best', round(float(best[0]), 3), flush=True)
P, s, a, rows, c = cost(best[1], True)
e = s - T.UAD_STATIC[p]
out = dict(preset=p, params=P, cost=c, static_rms=float(np.sqrt(np.mean(e[msk] ** 2))), static_max=float(np.abs(e[msk]).max()), gr_ours=[round(float(z), 2) for z in s],
           t63=a['t63_ms'], t90=a['t90_ms'], bursts=[dict(dep=d, burst_s=b, uad=mu, ours=m) for d, b, mu, m in rows])
json.dump(out, open('/workspace/uad3/fit_%s.json' % p, 'w'), indent=1, default=float)
print(json.dumps({k: out[k] for k in ('params', 'static_rms', 'static_max', 't63', 't90')}, default=float))
for d, b, mu, m in rows: print(d, b, 'rel63 %s/%s rel90 %s/%s att90 %s/%s' % (mu['rel63'], m['rel63'], mu['rel90'], m['rel90'], mu['att90'], m['att90']))
