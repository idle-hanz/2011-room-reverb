import numpy as np, csv, sys, json
sys.path.insert(0, '/workspace/uad2/scripts')
import io2, volterra as V
SR = 48000
STEPS = json.load(open('/workspace/uad2/an/static_fit.json'))
rows = []
H1C = {}
def h1mag(unit, f):
    if unit not in H1C:
        x, y = io2.rec('cess_%s_-30' % unit)
        k = V.fit_hammerstein([(x, y)], N=1, M=4096)[0]
        nf = 1 << 16; K = np.fft.rfft(np.roll(np.pad(k, (0, nf - len(k))), -V.PRE)); fr = np.fft.rfftfreq(nf, 1 / SR)
        H1C[unit] = (fr, np.abs(K))
    fr, K = H1C[unit]; return np.interp(f, fr, K)
def amp(seg, f):
    t = np.arange(len(seg)) / SR; w = np.hanning(len(seg))
    c = np.sum(seg * w * np.exp(-2j * np.pi * f * t)) / np.sum(w) * 2; return np.abs(c)
for id_ in sorted(k for k in io2._J if k.startswith('sc_')):
    j = io2.job(id_); sp = j['spec']; F = sp['freqs']; n = int(round(sp['step_s'] * SR))
    x, y = io2.rec(id_); unit = id_[3:].rsplit('_', 1)[0]
    # unit name is the setting key: strip the tag
    for u in ('ssl_4_auto', 'dis_6', 'fc_t2', 'la2as_pr50', 'la3a_pr5', 'ln_4', 'mvm_lim', 'dbx_4'):
        if id_.startswith('sc_' + u): unit = u; tag = id_[len('sc_' + u) + 1:]
    gr = []
    for i, f in enumerate(F):
        seg_y = y[(i + 1) * n - SR // 2:(i + 1) * n]; seg_x = x[(i + 1) * n - SR // 2:(i + 1) * n]
        g = amp(seg_y, f) / amp(seg_x, f) / h1mag(unit, f)
        # settle check: GR over the 2nd-to-last vs last quarter second
        s1 = y[(i + 1) * n - SR // 2:(i + 1) * n - SR // 4]; s2 = y[(i + 1) * n - SR // 4:(i + 1) * n]
        drift = 20 * np.log10(amp(s2, f) / amp(s1, f))
        gr.append((round(float(-20 * np.log10(g)), 2), round(float(drift), 2)))
    r = dict(setting=unit, variant=tag, level_dbfs=sp['level_db'])
    for f, (g, d) in zip(F, gr): r['gr_%d' % f] = g
    r['max_settle_drift_db'] = max(abs(d) for g, d in gr)
    rows.append(r); print(unit, tag, ' '.join('%d:%.1f' % (f, g) for f, (g, d) in zip(F, gr)), 'drift', r['max_settle_drift_db'])
with open('/workspace/uad2/an/comp_sidechain.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
