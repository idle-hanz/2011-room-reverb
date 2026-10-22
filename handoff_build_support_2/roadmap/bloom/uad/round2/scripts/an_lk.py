import numpy as np, csv, sys
sys.path.insert(0, '/workspace/uad2/scripts')
import io2
SR = 48000
def amp(seg, f):
    t = np.arange(len(seg)) / SR; w = np.hanning(len(seg)); return np.abs(np.sum(seg * w * np.exp(-2j * np.pi * f * t)) / np.sum(w) * 2)
rows = []
for id_ in sorted(k for k in io2._J if k.startswith('lk_')):
    sp = io2.job(id_)['spec']; x, y = io2.rec(id_, both=True)
    n0 = int(sp['off_s'] * SR); n1 = int(sp['on_s'] * SR)
    pre = slice(n0 - SR // 2, n0 - 1000); on = slice(n0 + n1 - SR // 2, n0 + n1 - 100)
    gL = 20 * np.log10(amp(y[0][on], 1000) / amp(x[0][on], 1000))
    gR_pre = 20 * np.log10(amp(y[1][pre], 3000) / amp(x[1][pre], 3000)); gR_on = 20 * np.log10(amp(y[1][on], 3000) / amp(x[1][on], 3000))
    # L's small-signal gain is not directly measured here; use R's pre-burst gain (identical channels) as the reference
    leak = 20 * np.log10(amp(y[1][on], 1000) / amp(x[0][on], 1000) + 1e-12)
    rows.append(dict(test=id_[3:], L_gr_db=round(gR_pre - gL, 2), R_gr_while_L_compresses_db=round(gR_pre - gR_on, 2),
                     L_to_R_1k_leak_db=round(leak, 1)))
    print(rows[-1])
with open('/workspace/uad2/an/comp_link.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
