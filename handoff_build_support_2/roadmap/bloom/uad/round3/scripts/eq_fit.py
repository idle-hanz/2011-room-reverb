# Fixed EQ for each comp hybrid: fit HP2 + high-shelf + 2x LP2 (RBJ) to UAD small-signal FR (lowest-level row).
import csv, json, numpy as np
from scipy.signal import freqz
from scipy.optimize import least_squares
SR = 48000; F = [20, 31.5, 50, 100, 200, 500, 2000, 5000, 10000, 15000]  # 18k/20k excluded: identical brickwall on every UADx unit (plugin decimator), not unit EQ
U = {'natural': 'la2as_pr50', 'room_crush': 'fet_all', 'nuke': 'dis_nuke', 'swell': 'fc_t2', 'glue': 'ssl_4_auto'}
rows = list(csv.DictReader(open('/workspace/uad2/an/comp_fr_vs_gr.csv')))
def rbj(kind, f0, Q, g=0.0):
    A = 10 ** (g / 40); w = 2 * np.pi * f0 / SR; c, s = np.cos(w), np.sin(w); al = s / (2 * Q)
    if kind == 'hp': b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]; a = [1 + al, -2 * c, 1 - al]
    elif kind == 'lp': b = [(1 - c) / 2, 1 - c, (1 - c) / 2]; a = [1 + al, -2 * c, 1 - al]
    else:  # high shelf
        sq = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
        a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
    return np.array(b) / a[0], np.array(a) / a[0]
def resp(z, nlp):
    hf, hq, sf, sg = z[:4]; secs = [rbj('hp', hf, hq), rbj('hs', sf, 0.707, sg)]
    for k in range(nlp): secs.append(rbj('lp', z[4 + 2 * k], z[5 + 2 * k]))
    H = np.ones(len(F), complex)
    for b, a in secs: H *= freqz(b, a, worN=np.array(F), fs=SR)[1]
    return 20 * np.log10(np.abs(H)), secs
if __name__ == '__main__':
    out = {}
    for p, u in U.items():
        r = [x for x in rows if x['setting'] == u][0]; tgt = np.array([float(r['fr_%s' % (f if f != 31.5 else '31.5')]) for f in F])
        best = None
        for nlp in (0,):
            z0 = [15, 0.6, 12000, 0.0] + [21000, 0.7] * nlp; lo = [3, 0.3, 3000, -6] + [12000, 0.3] * nlp; hi = [60, 1.5, 22000, 6] + [23500, 4] * nlp
            f = lambda z: resp(z, nlp)[0] - tgt
            s = least_squares(f, z0, bounds=(lo, hi)); e = np.max(np.abs(s.fun))
            if best is None or e < best[0] - 0.05: best = (e, nlp, s.x)
        e, nlp, z = best; m, secs = resp(z, nlp)
        out[p] = dict(unit=u, nlp=nlp, params=list(map(float, z)), max_err_db=float(e), target=list(tgt), model=list(np.round(m, 2)),
                      biquads=[dict(b=list(map(float, b)), a=list(map(float, a))) for b, a in secs])
        print(p, u, 'nLP', nlp, 'max err %.2f dB' % e, np.round(z, 3)); print('  tgt', tgt); print('  mdl', np.round(m, 2))
    json.dump(out, open('/workspace/uad3/eq_fit.json', 'w'), indent=1)
