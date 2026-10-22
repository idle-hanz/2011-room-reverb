# Static 1 kHz curve: UAD vs our preset models; fit our threshold T to the UAD curve.
import numpy as np, json, sys
sys.path.insert(0, '/workspace/uad2/scripts')
import io2, models as Mo
SR = 48000; LV = list(range(-45, 13, 3)); ST = 72000; KEEP = 24000
def uad_curve(setting):
    x, y = io2.rec('c1k_' + setting)
    seg = y.reshape(len(LV), KEEP)
    out = 20 * np.log10(np.sqrt(2 * np.mean(seg ** 2, axis=1)))
    g = out - np.array(LV); return g[0] - g      # GR re the -45 dBFS gain
def ours_curve(preset, T):
    x = np.load(io2.I + 'st_1000_1p5.npy').astype(float)
    y, gr = Mo.run_preset(preset, x, T)
    seg = np.stack([y[(i + 1) * ST - KEEP:(i + 1) * ST] for i in range(len(LV))])
    out = 20 * np.log10(np.sqrt(2 * np.mean(seg ** 2, axis=1)))
    g = out - np.array(LV); return g[0] - g
res = {}
for p, u in Mo.PRESET_UNIT.items():
    gu = uad_curve(u)
    best = None
    for T in np.arange(-50, 10.01, 0.5):
        go = ours_curve(p, T); m = (gu > 0.2) | (go > 0.2)
        if not m.any(): continue
        e = np.sqrt(np.mean((go[m] - gu[m]) ** 2))
        if best is None or e < best[0]: best = (e, T, go)
    e, T, go = best
    for T2 in np.arange(T - 0.5, T + 0.51, 0.1):
        g2 = ours_curve(p, T2); m = (gu > 0.2) | (g2 > 0.2); e2 = np.sqrt(np.mean((g2[m] - gu[m]) ** 2))
        if e2 < e: e, T, go = e2, T2, g2
    res[p] = dict(unit=u, T=round(float(T), 2), rms_err_db=round(float(e), 2), max_err_db=round(float(np.max(np.abs(go - gu))), 2),
                  levels=LV, gr_uad=[round(float(v), 2) for v in gu], gr_ours=[round(float(v), 2) for v in go])
    print(p, u, 'T', round(T, 2), 'rms', round(e, 2), 'max', res[p]['max_err_db'])
    print('  uad ', ' '.join('%5.1f' % v for v in gu)); print('  ours', ' '.join('%5.1f' % v for v in go))
json.dump(res, open('/workspace/uad2/an/static_fit.json', 'w'), indent=1)
