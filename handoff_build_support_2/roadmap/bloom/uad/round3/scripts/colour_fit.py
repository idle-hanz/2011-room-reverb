# Fit static colour shaper (+depth law, + optional memory LP on distortion) to UAD complex H2/H3 stairs.
import sys, os, json, csv, time, numpy as np
sys.path.insert(0, '/workspace/uad2/scripts'); sys.path.insert(0, '/workspace/uad3')
import io2, harmlib as H, comp_proto as CP, dyn3
from scipy.optimize import minimize
from scipy.signal import lfilter
SR = 48000; LV = list(range(-45, 13, 3))
UNIT = {'natural': ['la2as_pr50', 'la2as_nocomp'], 'room_crush': ['fet_all'], 'nuke': ['dis_nuke'],
        'swell': ['fc_t5', 'fc_nocomp'], 'glue': ['ssl_4_auto']}
T = {}
for r in csv.DictReader(open('/workspace/uad3/harm_phase_uad.csv')): T[(r['src'], int(r['freq']), int(float(r['in_dbfs'])))] = r
def ids(p):
    out = []
    for u in UNIT[p]:
        for f in (100, 1000, 5000):
            i = ('c1k_%s' % u) if f == 1000 else ('c%d_%s' % (f, u))
            if i in io2._J and (u, f, -45) in T: out.append((i, u, f))
    return out
X = {}
def get(i):
    if i not in X:
        j = io2.job(i); k = j['keep']; k = json.loads(k) if isinstance(k, str) else k; X[i] = (io2.xin(i), k)
    return X[i]
GR = {}
def model_rows(p, C, P, os_=1, adaa=False):
    res = {}
    for i, u, f in ids(p):
        x, keep = get(i)
        if i not in GR:
            GR[i] = np.zeros_like(x) if 'nocomp' in u else dyn3.gr_of(p, x, P)
        gr = GR[i]; side = C.get('side', CP.SIDE[p]); vr = 10 ** (C['vr_db'] / 20)
        for L, (a0, b0) in zip(LV, keep):
            # colour is static given the precomputed GR, so only the kept step (with its first half as warm-up) is processed
            xs = x[a0:b0]; grs = gr[a0:b0]; g = 10 ** (-grs / 20)
            v = xs if side == 'in' else g * xs
            dd = CP.depth(grs if side != 'in' else np.zeros_like(grs), C)
            o = CP.shape(v, dd, C['fam'], vr, C.get('a2', 0.), C.get('a3', 0.), C.get('b', 0.))
            if C.get('fc', 0) > 0:
                al = np.exp(-2 * np.pi * C['fc'] / SR); o = lfilter([1 - al], [1, -al], o)
            o = CP.dcblock(o, np.exp(-2 * np.pi * 5 / SR)); y = v + o
            if side == 'in': y = g * y
            s = y[(b0 - a0) // 2:]
            d, th = H.rel_phase(s, f, 3); res[(u, f, L)] = (d[1], th[1], d[2], th[2])
    return res
def cost(p, C, P, detail=False):
    R = model_rows(p, C, P); e = []; rows = []
    for k, (m2, t2, m3, t3) in R.items():
        r = T[k]
        for mu, tu, mm, tm in ((float(r['h2_dbc']), float(r['th2_deg']), m2, t2), (float(r['h3_dbc']), float(r['th3_deg']), m3, t3)):
            if mu < -100 and mm < -100: continue
            de = (max(mm, -110) - max(mu, -110)) / 6.0
            ph = abs(((tm - tu + 180) % 360) - 180) / 90.0 if mu > -95 else 0.0
            w = 1.0 if mu > -80 else 0.4
            e.append(w * (min(abs(de), 4) ** 2 + ph ** 2))
        rows.append((k, r['h2_dbc'], round(m2, 1), r['th2_deg'], round(t2), r['h3_dbc'], round(m3, 1), r['th3_deg'], round(t3)))
    c = float(np.mean(e)) if e else 99
    return (c, rows) if detail else c
FAM = {  # name: (fam, param names, x0, lo, hi)
 'poly':      (0, ['a2', 'a3', 'd0', 'Gs'], [0.0, 0.0, 1.0, 10.0], [-1, -1, 0, 0.5], [1, 1, 1, 30]),
 'poly_mem':  (0, ['a2', 'a3', 'd0', 'Gs', 'lfc'], [0.0, 0.0, 1.0, 10.0, 3.5], [-1, -1, 0, 0.5, 2.3], [1, 1, 1, 30, 4.38]),
 'polyv':     (0, ['vr_db', 'a2', 'a3', 'd0', 'Gs'], [-12.0, 0.0, 0.0, 1.0, 10.0], [-36, -1, -1, 0, 0.5], [6, 1, 1, 1, 30]),
 'btanh':     (1, ['vr_db', 'b', 'd0', 'Gs'], [6.0, 0.05, 1.0, 10.0], [-30, -1.5, 0, 0.5], [30, 1.5, 1, 30]),
 'btanh_mem': (1, ['vr_db', 'b', 'd0', 'Gs', 'lfc'], [6.0, 0.05, 1.0, 10.0, 3.5], [-30, -1.5, 0, 0.5], [30, 1.5, 1, 30, 4.38]),
}
def mkC(fam, names, v, side):
    C = {'fam': FAM[fam][0], 'vr_db': 0.0, 'law': 'gr'}
    for n, x in zip(names, v):
        if n == 'lfc': C['fc'] = 10 ** x
        else: C[n] = float(x)
    if side: C['side'] = side
    return C
if __name__ == '__main__':
    p = sys.argv[1]; fams = sys.argv[2].split(','); side = sys.argv[3] if len(sys.argv) > 3 else None
    P = CP.dyn_params(p); out = {}
    c0 = cost(p, {'off': 1, 'fam': 0, 'vr_db': 0, 'a2': 0, 'a3': 0, 'd0': 0, 'Gs': 1}, P)
    print(p, 'no-colour cost', round(c0, 3), flush=True)
    for fam in fams:
        f, names, x0, lo, hi = FAM[fam]; lo = np.array(lo + [2.3] * (len(names) - len(lo))); hi = np.array(hi + [4.38] * (len(names) - len(hi)))
        def J(z):
            v = np.clip(z, lo, hi); pen = np.sum((z - v) ** 2) * 10
            return cost(p, mkC(fam, names, v, side), P) + pen
        best = None; t0 = time.time()
        starts = [x0] + [list(lo + (hi - lo) * np.random.default_rng(s).random(len(lo))) for s in range(2)]
        if fam == 'poly':
            starts += [[0.05, -0.05] + x0[2:], [-0.05, 0.05] + x0[2:]]
        if fam == 'polyv':
            starts += [[-12, 0.3, -0.3, 1.0, 10.0], [-20, -0.3, 0.3, 0.5, 10.0]]
        for s in starts:
            r = minimize(J, np.array(s, float), method='Nelder-Mead', options=dict(maxiter=300, xatol=1e-4, fatol=1e-4))
            if best is None or r.fun < best.fun: best = r
        v = np.clip(best.x, lo, hi); C = mkC(fam, names, v, side); c, rows = cost(p, C, P, True)
        out[fam] = dict(C=C, cost=c, nocolour=c0, rows=[list(map(str, r)) for r in rows])
        print('%-10s cost %.3f (none %.3f) %s  %ds' % (fam, c, c0, json.dumps(C), time.time() - t0), flush=True)
        json.dump(out, open('/workspace/uad3/colfit_%s%s%s.json' % (p, '_' + side if side else '', os.environ.get('CFTAG', '')), 'w'), indent=1)
