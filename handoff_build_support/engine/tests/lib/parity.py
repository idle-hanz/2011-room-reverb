"""Play-vs-Render IR comparison metrics. Import or run:
python parity.py <play_prefix> <render_prefix>   (expects <p>_full.f32 optional, _early.f32, _direct.f32)"""
import sys, json, numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from analyze import *
SR = 48000
OCT = [125, 250, 500, 1000, 2000, 4000, 8000, 16000]

def peaks(x, n=12, t_max=0.08, min_sep=0.0005):
    y = np.abs(x[: int(t_max * SR)])
    idx = []
    for i in np.argsort(-y):
        if y[i] <= 0: break
        if all(abs(i - j) > min_sep * SR for j in idx): idx.append(i)
        if len(idx) >= n: break
    return sorted((int(i), float(x[i])) for i in idx)

def edb(x):
    return 10 * np.log10(max(float(np.sum(np.asarray(x) ** 2)), 1e-300))

def direct_metrics(P, R):
    out = {}
    for ch, nm in ((0, 'L'), (1, 'R')):
        ip, ir = int(np.argmax(np.abs(P[:, ch]))), int(np.argmax(np.abs(R[:, ch])))
        out[nm] = {'play_sample': ip, 'render_sample': ir, 'dt_samples': ip - ir,
                   'play_peak': float(P[ip, ch]), 'render_peak': float(R[ir, ch]),
                   'level_diff_db': 20 * np.log10(abs(P[ip, ch]) / max(abs(R[ir, ch]), 1e-12)),
                   'energy_diff_db': edb(P[:, ch]) - edb(R[:, ch])}
    return out

def early_metrics(P, R, t_max=0.08):
    out = {}
    for ch, nm in ((0, 'L'), (1, 'R')):
        pp, rp = peaks(P[:, ch], 12, t_max), peaks(R[:, ch], 12, t_max)
        matches = []
        for (ti, vi) in rp:
            j = min(pp, key=lambda q: abs(q[0] - ti)) if pp else None
            if j is None: continue
            matches.append({'render_ms': ti / SR * 1e3, 'play_ms': j[0] / SR * 1e3, 'dt_ms': (j[0] - ti) / SR * 1e3,
                            'dlevel_db': 20 * np.log10(max(abs(j[1]), 1e-12) / max(abs(vi), 1e-12)), 'sign_match': bool(np.sign(j[1]) == np.sign(vi))})
        n = int(t_max * SR)
        out[nm] = {'energy_diff_db_0_80ms': edb(P[:n, ch]) - edb(R[:n, ch]),
                   'max_abs_dt_ms': max(abs(m['dt_ms']) for m in matches) if matches else None,
                   'median_abs_dlevel_db': float(np.median([abs(m['dlevel_db']) for m in matches])) if matches else None,
                   'sign_mismatch': sum(not m['sign_match'] for m in matches), 'matches': matches}
    return out

def octave_balance(x, t0=0.0, t1=1.0):
    seg = x[int(t0 * SR): int(t1 * SR)]
    return {fc: edb(band(seg, SR, fc)) for fc in OCT if fc * 2 ** 0.5 < 0.45 * SR or fc == 16000}

def full_metrics(P, R):
    res = {'broadband_energy_diff_db': {nm: edb(P[:, c]) - edb(R[:, c]) for c, nm in ((0, 'L'), (1, 'R'))}}
    tp, tr = t60_bands(P[:, 0], SR, bands=[250, 500, 1000, 2000, 4000, 8000]), t60_bands(R[:, 0], SR, bands=[250, 500, 1000, 2000, 4000, 8000])
    res['t30_play'] = {str(k): round(v, 2) for k, v in tp.items()}
    res['t30_render'] = {str(k): round(v, 2) for k, v in tr.items()}
    bp, br = octave_balance(P[:, 0], 0.08, 1.0), octave_balance(R[:, 0], 0.08, 1.0)
    off = edb(P[int(0.08 * SR):SR, 0]) - edb(R[int(0.08 * SR):SR, 0])
    res['tail_octave_balance_diff_db_(norm)'] = {str(k): round(bp[k] - br[k] - off, 1) for k in bp}
    res['tail_level_diff_db_80ms_1s'] = off
    for nm, (a, b) in (('early_0_80ms', (0, 0.08)), ('tail_80ms_1s', (0.08, 1.0))):
        s = slice(int(a * SR), int(b * SR))
        def corr(X):
            l, r = X[s, 0], X[s, 1]
            return float(np.dot(l, r) / np.sqrt(max(np.dot(l, l) * np.dot(r, r), 1e-300)))
        def lr(X):
            return edb(X[s, 0]) - edb(X[s, 1])
        res['stereo_' + nm] = {'corr_play': corr(P), 'corr_render': corr(R), 'LminusR_db_play': lr(P), 'LminusR_db_render': lr(R)}
    return res

def load(p):
    return np.fromfile(p, np.float32).reshape(-1, 2).astype(np.float64)

if __name__ == '__main__':
    pp, rp = sys.argv[1], sys.argv[2]
    out = {}
    import os
    if os.path.exists(pp + '_direct.f32'): out['direct'] = direct_metrics(load(pp + '_direct.f32'), load(rp + '_direct.f32'))
    if os.path.exists(pp + '_early.f32'): out['early'] = early_metrics(load(pp + '_early.f32'), load(rp + '_early.f32'))
    for tag in ('byp', 'col'):
        if os.path.exists(pp + f'_{tag}.f32'): out['full_' + tag] = full_metrics(load(pp + f'_{tag}.f32'), load(rp + f'_{tag}.f32'))
    print(json.dumps(out, indent=1, default=float))
