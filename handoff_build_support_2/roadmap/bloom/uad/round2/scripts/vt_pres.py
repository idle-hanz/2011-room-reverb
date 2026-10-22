import numpy as np, json, csv, sys, time
sys.path.insert(0, '.')
import volterra as V
from io2 import rec
O = '/workspace/uad2/out/'; I = '/workspace/uad2/inputs/'
CLIP = {"neve": -36, "u610a": -57, "u610b": -54, "api": -36, "sslE": -24, "manley": -24}
def _old_rec(job):
    j = json.load(open(O + job + '.json')); y = np.load(O + job + '.npz')['y'][0].astype(float)
    x = np.load(I + j['input']).astype(float) * 10 ** (j.get('gain_db', 0) / 20); n = min(len(x), len(y))
    return x[:n], y[:n]
rows = []
pres = sys.argv[1:] or list(CLIP)
for p in pres:
    t0 = time.time()
    ess = {r: rec('pess_%s_%+d' % (p, r)) for r in (-30, -20, -10, -3)}
    nz = {r: rec('pnz_%s_%+d' % (p, r)) for r in (-20, -12, -6)}
    prg = {(k, r): rec('pprog_%s_%s_%+d' % (p, k, r)) for k in ('mix', 'vocal', 'drums', 'wetmix') for r in (-6, 0)}
    k_lin = V.fit_hammerstein([ess[-30]], N=1)
    train = [ess[r] for r in (-30, -20, -10, -3)] + [nz[-20], nz[-12]]
    K = {N: V.fit_hammerstein(train, N=N) for N in (3, 5, 7)}
    b5 = lambda x: V.apply_hammerstein(x, K[5])
    c = V.fit_volterra_resid([nz[-20], nz[-12]] + [ess[-10], ess[-3]], b5)
    np.savez('/workspace/uad2/an/hk_%s.npz' % p, k5=K[5], k7=K[7], k3=K[3], klin=k_lin, volt=c)
    tests = {('noise', -6): nz[-6], ('noise', -12): nz[-12], ('ess', -3): ess[-3]}
    tests.update({k: v for k, v in prg.items()})
    for (nm, r), (x, y) in tests.items():
        sl = slice(4096, len(x) - 4096)
        ylin = V.apply_hammerstein(x, k_lin)
        e_lin = V.nmse_db(y, ylin, sl)
        row = {"pre": p, "signal": nm, "rel_clip_db": r, "held_out": not (nm == 'ess' or (nm == 'noise' and r == -12)),
               "lin_err_db": round(e_lin, 1)}
        for N in (3, 5, 7):
            row["ham%d_err_db" % N] = round(V.nmse_db(y, V.apply_hammerstein(x, K[N]), sl), 1)
        row["ham5+volt_err_db"] = round(V.nmse_db(y, V.apply_volterra_resid(x, b5, c), sl), 1)
        rows.append(row); print(row, flush=True)
    print(p, 'done %.0fs' % (time.time() - t0), flush=True)
with open('/workspace/uad2/an/vt_pres%s.csv' % ('' if not sys.argv[1:] else '_' + '_'.join(pres)), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
