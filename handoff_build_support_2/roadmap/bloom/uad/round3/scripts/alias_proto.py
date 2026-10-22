# Prototype aliasing at 1x / ADAA1 / 2x / 4x, M1+M2 tone methods + sweep, same inputs/levels as the UAD r3 jobs.
import sys, os, json, ast, csv, numpy as np
sys.path.insert(0, '/workspace/uad2/scripts'); sys.path.insert(0, '/workspace/uad3')
import alias as AL, comp_proto as CP, dyn3, prelib
from scipy.signal import resample_poly
SR = 48000; J = {j['id']: j for j in json.load(open('/workspace/uad3/jobs_r3.json'))}
UNIT = {'natural': 'la2as_pr50', 'room_crush': 'fet_all', 'nuke': 'dis_nuke_room', 'swell': 'fc_t5', 'glue': 'ssl_4_auto'}
def xin(i):
    j = J[i]; x = np.load('/workspace/uad3/r3in/' + j['input']).astype(np.float32)
    if x.ndim == 2: x = x[0]
    return (x * np.float32(10 ** (j.get('gain_db', 0) / 20))).astype(float)
def best_colour(p):
    try: d = json.load(open('/workspace/uad3/colour_choice.json'))[p]
    except Exception: return None
    return d
def comp_y(p, x, mode):
    C = best_colour(p); P = CP.dyn_params(p)
    if mode == 'adaa' and (C is None or C['fam'] != 0): return None
    os_ = {'1x': 1, 'adaa': 1, '2x': 2, '4x': 4}[mode]
    y, gr = run_c(p, x, P, C, os_, mode == 'adaa'); return y
def run_c(p, x, P, C, os_, adaa):
    gr = dyn3.gr_of(p, x, P); g = 10 ** (-gr / 20)
    if C is None: return g * x, gr
    side = C.get('side', CP.SIDE[p])
    if side == 'in': return g * CP.colour(x, np.zeros_like(gr), C, os_, adaa), gr
    return CP.colour(g * x, gr, C, os_, adaa), gr
def pre_y(p, x, mode):
    ch = json.load(open('/workspace/uad3/pre_choice.json'))[p]; cfg, th = ch['cfg'], ch['th']
    m = prelib.Pre(p, cfg); os_ = {'1x': 1, '2x': 2, '4x': 4, '8x': 8, '16x': 16}.get(mode)
    if os_ is None: return None
    if os_ == 1: d = m.nl(x, th)
    else:
        prelib.SR = SR * os_
        try: d = resample_poly(m.nl(resample_poly(x, os_, 1), th), 1, os_)[:len(x)]
        finally: prelib.SR = SR
    return prelib.lin(x, m.k) + prelib.lin(d, m.kn)
if __name__ == '__main__':
    rows = []; out = open('/workspace/uad3/alias_proto%s.txt' % os.environ.get('ATAG', ''), 'w')
    targets = [(p, UNIT[p], comp_y) for p in UNIT] + [(p, p, pre_y) for p in ('neve', 'u610a')]
    import os
    sel = os.environ.get('PRESETS'); targets = [t for t in targets if not sel or t[0] in sel.split(',')]
    for p, u, fn in targets:
        for f in (7000, 9000, 13000, 17000):
            for L in (['-24', '-12', '-6', '+0'] if fn is comp_y else ['-12', '-6', '+0', '+6']):
                i = 'al_%s_%d_%s' % (u, f, L)
                if i not in J: continue
                x = xin(i)
                for mode in os.environ.get('MODES', '1x,adaa,2x,4x').split(','):
                    y = fn(p, x, mode)
                    if y is None: continue
                    a = AL.tone_alias(y, f); a.update(preset=p, unit=u, f=f, L=L, mode=mode); rows.append(a)
                    s = '%s %s %d %s %-4s | M1 %.1f dBFS (k%d@%d) | M2<16k %.1f @%d | M2 peak %.1f @%d' % (p, u, f, L, mode, a['m1_worst_alias_dbfs'], a['m1_worst_k'], a['m1_worst_f'], a['m2_peak_below16k_dbfs'], a['m2_peak_below16k_f'], a['m2_peak_resid_dbfs'], a['m2_peak_f'])
                    print(s, flush=True); out.write(s + '\n'); out.flush()
        # sweep (third method)
        i = 'alsw_%s' % u
        cand = [k for k in J if k.startswith('alsw_%s' % u)]
        for i in cand:
            x = xin(i)
            yu = np.load('/workspace/uad3/r3out/%s.npz' % i)['y'].astype(float); yu = yu[0] if yu.ndim == 2 else yu
            su = AL.sweep_alias(yu); hu = su[su[:, 0] > 5000]; s = '%s SWEEP %s UAD  | worst non-harmonic (f>5k) %.1f dBFS' % (p, i, hu[:, 1].max()); print(s); out.write(s + '\n')
            rows.append(dict(preset=p, unit=u, f='sweep', L=i, mode='UAD', sweep_worst_dbfs=hu[:, 1].max()))
            for mode in os.environ.get('MODES', '1x,adaa,2x,4x').split(','):
                y = fn(p, x, mode)
                if y is None: continue
                s_ = AL.sweep_alias(y); hi = s_[s_[:, 0] > 5000]
                s = '%s SWEEP %s %-4s | worst non-harmonic (f>5k) %.1f dBFS' % (p, i, mode, hi[:, 1].max()); print(s, flush=True); out.write(s + '\n')
                rows.append(dict(preset=p, unit=u, f='sweep', L=i, mode=mode, sweep_worst_dbfs=hi[:, 1].max()))
        w = csv.DictWriter(open('/workspace/uad3/alias_proto%s.csv' % os.environ.get('ATAG', ''), 'w', newline=''), sorted({k for r in rows for k in r})); w.writeheader(); w.writerows(rows)
