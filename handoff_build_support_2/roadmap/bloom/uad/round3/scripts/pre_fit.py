import sys, json, numpy as np, time
sys.path.insert(0, '/workspace/uad3'); sys.path.insert(0, '/workspace/uad2/scripts')
import prelib as P, io2
from scipy.optimize import least_squares
p = sys.argv[1]; fams = sys.argv[2].split(',') if len(sys.argv) > 2 else None
VC0 = {'neve': 14.0, 'u610a': -12.0}[p]; DRV = {'neve': -36.0, 'u610a': -57.0}[p]
PLV = list(range(-90, 1, 3))
def stair_rec2(id_):
    x = io2.xin(id_); y = np.load(io2.O + id_ + '.npz')['y'][0].astype(float); return x, y, io2.job(id_)['keep']
TRAIN = []
for f in (20, 30, 50, 200): TRAIN.append(('st', 'p%d_%s' % (f, p)) + stair_rec2('p%d_%s' % (f, p)))
for f in (40, 100, 1000, 5000): TRAIN.append(('st', 'pst3_%s_%d' % (p, f)) + P.rec3('pst3_%s_%d' % (p, f)))
for r in (-30, -20, -10, -3): TRAIN.append(('full', 'pess_%s_%+d' % (p, r)) + P.rec2('pess_%s_%+d' % (p, r)) + (None,))
for r in (-20, -12): TRAIN.append(('full', 'pnz_%s_%+d' % (p, r)) + P.rec2('pnz_%s_%+d' % (p, r)) + (None,))
HOLD = [('pnz_%s_-6' % p)] + ['pprog_%s_%s_%+d' % (p, k, r) for k in ('vocal', 'mix', 'wetmix', 'drums') for r in (0, -6)]
pre = P.Pre(p, {})
def segs(v, keep, kept_only):
    if keep is None: return [v[4096:-4096]]
    if kept_only: return P_split(v, keep)
    return [v[a:b] for a, b in keep]
def P_split(v, keep):
    out = []; q = 0
    for a, b in keep: out.append(v[q:q + b - a]); q += b - a
    return out
PREP = []
for kind, id_, x, y, keep in TRAIN:
    t = y - (P.lin(x, pre.k) if keep is None else np.concatenate([s for s in segs(P.lin(x, pre.k), keep, False)]))
    tb = P.bl(t) if keep is None else t
    ys = segs(y, keep, True); ts = segs(tb, keep, True)
    # only stair steps above the noise: output >= -60 dBFS and below hard saturation irrelevance
    rm = [max(np.sqrt(np.mean(t_ ** 2)), 1e-3 * np.sqrt(np.mean(s ** 2))) + 1e-12 for s, t_ in zip(ys, ts)]
    ry = [np.sqrt(np.mean(s ** 2)) for s in ys]
    if keep is not None:
        lv = P.J3[id_]['levels'] if id_ in P.J3 else PLV
        rm = [(r if (DRV - 30 <= L <= DRV + 6 and yy > 10 ** (-70 / 20)) else 0.0) for r, L, yy in zip(rm, lv, ry)]
    PREP.append((kind, id_, x, keep, ts, rm))
FAM = {
 'poly3': (dict(fam=0), {'p0': (0.0, -1, 1), 'p1': (0.0, -1, 1)}),
 'poly5': (dict(fam=0), {'p0': (0.0, -1, 1), 'p1': (0.0, -1, 1), 'p2': (0.0, -1, 1), 'p3': (0.0, -1, 1)}),
 'btanh': (dict(fam=1), {'vc_db': (VC0, VC0 - 20, VC0 + 20), 'p0': (0.0, -1.5, 1.5), 'p1': (0.0, -0.5, 0.5)}),
 'btanh_emph': (dict(fam=1, emph=True), {'vc_db': (VC0, VC0 - 20, VC0 + 20), 'p0': (0.0, -1.5, 1.5), 'p1': (0.0, -0.5, 0.5), 'emph_fc': (150.0, 20, 2000), 'emph_db': (3.0, -12, 20)}),
 'btanh_flux': (dict(fam=1, flux=True), {'vc_db': (VC0, VC0 - 20, VC0 + 20), 'p0': (0.0, -1.5, 1.5), 'p1': (0.0, -0.5, 0.5), 'phi_fc': (20.0, 2, 200), 'phi_db': (VC0, VC0 - 40, VC0 + 20), 'phi_c': (-0.01, -1, 1)}),
 'btanh_emph_flux': (dict(fam=1, emph=True, flux=True), {'vc_db': (VC0, VC0 - 20, VC0 + 20), 'p0': (0.0, -1.5, 1.5), 'p1': (0.0, -0.5, 0.5), 'emph_fc': (150.0, 20, 2000), 'emph_db': (3.0, -12, 20), 'phi_fc': (20.0, 2, 200), 'phi_db': (VC0, VC0 - 40, VC0 + 20), 'phi_c': (-0.01, -1, 1)}),
 'btanh_emph_flux_mem': (dict(fam=1, emph=True, flux=True), {'vc_db': (VC0, VC0 - 20, VC0 + 20), 'p0': (0.0, -1.5, 1.5), 'p1': (0.0, -0.5, 0.5), 'emph_fc': (150.0, 20, 2000), 'emph_db': (3.0, -12, 20), 'phi_fc': (20.0, 2, 200), 'phi_db': (VC0, VC0 - 40, VC0 + 20), 'phi_c': (-0.01, -1, 1), 'mem_m': (0.0, -1, 1), 'mem_tau': (0.02, 0.001, 0.3)}),
 'poly3_flux': (dict(fam=0, flux=True), {'p0': (0.0, -1, 1), 'p1': (0.0, -1, 1), 'phi_fc': (20.0, 2, 200), 'phi_db': (VC0, VC0 - 40, VC0 + 20), 'phi_c': (-0.01, -1, 1)}),
 'nclip': (dict(fam=3), {'vc_db': (VC0, VC0 - 20, VC0 + 20), 'p0': (4.0, 1.0, 30.0), 'p1': (0.0, -0.6, 0.6), 'p2': (0.0, -0.5, 0.5)}),
 'nclip_emph': (dict(fam=3, emph=True), {'vc_db': (VC0, VC0 - 20, VC0 + 20), 'p0': (4.0, 1.0, 30.0), 'p1': (0.0, -0.6, 0.6), 'p2': (0.0, -0.5, 0.5), 'emph_fc': (150.0, 20, 2000), 'emph_db': (3.0, -12, 20)}),
 'nclip_flux': (dict(fam=3, flux=True), {'vc_db': (VC0, VC0 - 20, VC0 + 20), 'p0': (4.0, 1.0, 30.0), 'p1': (0.0, -0.6, 0.6), 'p2': (0.0, -0.5, 0.5), 'phi_fc': (20.0, 2, 200), 'phi_db': (VC0, VC0 - 40, VC0 + 20), 'phi_c': (-0.01, -1, 1)}),
 'nclip_emph_flux': (dict(fam=3, emph=True, flux=True), {'vc_db': (VC0, VC0 - 20, VC0 + 20), 'p0': (4.0, 1.0, 30.0), 'p1': (0.0, -0.6, 0.6), 'p2': (0.0, -0.5, 0.5), 'emph_fc': (150.0, 20, 2000), 'emph_db': (3.0, -12, 20), 'phi_fc': (20.0, 2, 200), 'phi_db': (VC0, VC0 - 40, VC0 + 20), 'phi_c': (-0.01, -1, 1)}),
 'nclip_emph_flux_mem': (dict(fam=3, emph=True, flux=True), {'vc_db': (VC0, VC0 - 20, VC0 + 20), 'p0': (4.0, 1.0, 30.0), 'p1': (0.0, -0.6, 0.6), 'p2': (0.0, -0.5, 0.5), 'emph_fc': (150.0, 20, 2000), 'emph_db': (3.0, -12, 20), 'phi_fc': (20.0, 2, 200), 'phi_db': (VC0, VC0 - 40, VC0 + 20), 'phi_c': (-0.01, -1, 1), 'mem_m': (0.0, -2, 2), 'mem_tau': (0.02, 0.001, 0.3)}),
 'softclip': (dict(fam=2), {'vc_db': (VC0, VC0 - 20, VC0 + 20), 'p0': (0.0, -1, 1)}),
}
def make_th(keys, v, fixed):
    th = dict(fixed); th.update({k: float(z) for k, z in zip(keys, v)}); return th
DEC = 4
def resid(v, keys, cfg, fixed):
    pre.cfg = cfg; th = make_th(keys, v, fixed); out = []
    for kind, id_, x, keep, ts, rms in PREP:
        d = P.lin(pre.nl(x, th), pre.kn)
        if keep is None: d = P.bl(d); ds = [d[4096:-4096]]
        else: ds = [d[a:b] for a, b in keep]
        for di, ti, ri in zip(ds, ts, rms):
            if ri <= 0: continue
            out.append(((ti - di) / ri)[::DEC] / np.sqrt(len(ti) / DEC))
    r = np.concatenate(out)
    return np.nan_to_num(r, nan=10.0, posinf=10.0, neginf=-10.0)
def evaluate(cfg, th):
    pre.cfg = cfg; res = {}
    for id_ in HOLD:
        x, y = P.rec2(id_); sl = slice(4096, len(x) - 4096)
        yl = P.lin(x, pre.k); ym = yl + P.lin(pre.nl(x, th), pre.kn)
        e = lambda a: float(10 * np.log10(np.sum((P.bl(y)[sl] - P.bl(a)[sl]) ** 2) / np.sum(P.bl(y)[sl] ** 2)))
        res[id_] = (round(e(yl), 2), round(e(ym), 2))
    return res
results = {}
for name in (fams or list(FAM)):
    cfg, spec = FAM[name]; keys = list(spec); t0 = time.time()
    fixed = {'vc_db': VC0} if 'vc_db' not in spec else {}
    v0 = np.array([spec[k][0] for k in keys]); lo = np.array([spec[k][1] for k in keys]); hi = np.array([spec[k][2] for k in keys])
    best = None
    for st in range(3):
        vs = v0 if st == 0 else np.clip(v0 + np.random.default_rng(st).normal(0, 0.3, len(v0)) * (hi - lo) * 0.2, lo, hi)
        try:
            r = least_squares(resid, vs, bounds=(lo, hi), args=(keys, cfg, fixed), x_scale='jac', max_nfev=120, diff_step=1e-3)
        except Exception as e:
            print(name, 'fail', e); continue
        if best is None or r.cost < best.cost: best = r
    th = make_th(keys, best.x, fixed); ev = evaluate(cfg, th)
    r0 = resid(np.zeros(0), [], dict(fam=0), {'vc_db': VC0, 'p0': 0, 'p1': 0})
    results[name] = dict(cfg=cfg, th=th, train_cost=float(best.cost), train_cost_linear=float(0.5 * np.sum(r0 ** 2)), hold=ev)
    hv = np.array([v[1] - v[0] for v in ev.values()])
    print('%-22s train %.4f (lin %.4f) | held-out gain vs linear: median %+.2f dB, worst %+.2f | %.0fs' % (name, best.cost, results[name]['train_cost_linear'], np.median(hv), hv.max(), time.time() - t0), flush=True)
    print('   ', {k: round(v, 4) for k, v in th.items()}, flush=True)
    print('   ', ev, flush=True)
    json.dump(results, open('/workspace/uad3/prefit_%s%s.json' % (p, '' if not fams else '_' + '_'.join(fams)), 'w'), indent=1, default=float)
