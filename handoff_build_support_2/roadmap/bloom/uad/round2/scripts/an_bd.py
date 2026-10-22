import numpy as np, csv, sys, re
sys.path.insert(0, '/workspace/uad2/scripts')
import io2
SR = 48000
rows = []
ids = sorted(k for k in io2._J if k.startswith('bd_'))
def cross(t, g, frac, start, sign):
    # first time g crosses frac*target after start
    for i in range(start, len(g)):
        if sign * g[i] >= sign * frac: return t[i]
    return np.nan
for id_ in ids:
    j = io2.job(id_); sp = j['spec']; ei, eo, dec = io2.env_rec(id_)
    fs = SR / dec; t = np.arange(len(ei)) / fs
    eo = eo.mean(axis=0) if eo.shape[0] == 1 else eo[0]
    gr = -20 * np.log10(np.maximum(eo, 1e-12) / np.maximum(ei, 1e-12))
    i_on = int(round(sp['pre_s'] * fs)); i_off = i_on + int(round(sp['burst_s'] * fs)); n = len(gr)
    g0 = np.median(gr[int(i_on - 0.2 * fs):i_on - int(0.002 * fs)])
    gr = gr - g0
    gss = np.median(gr[i_off - max(2, int(min(0.01, sp['burst_s'] / 5) * fs)):i_off - 1])
    gend = gr[i_off - 1]
    # attack times (dB-domain fraction of the end-of-burst GR); envelope window 1 ms => +/-0.5 ms resolution
    a = gr[i_on:i_off]; ta = (np.arange(len(a)) / fs) * 1000
    def first(fr):
        k = np.nonzero(a >= fr * gss)[0]; return float(ta[k[0]]) if len(k) else np.nan
    ovs = float(a.max() - gss)
    r = gr[i_off:]; tr = np.arange(len(r)) / fs * 1000
    def rel(fr):  # time for GR to fall to fr*gend
        k = np.nonzero(r <= fr * gend)[0]; return float(tr[k[0]]) if len(k) else np.nan
    def within(db):
        k = np.nonzero(np.abs(r) <= db)[0]; return float(tr[k[0]]) if len(k) else np.nan
    m = re.match(r'bd_(.+)_(\d+)_([\dp]+)$', id_)
    rows.append(dict(setting=m.group(1), target_gr=int(m.group(2)), burst_s=sp['burst_s'], gr_end_db=round(gend, 2), gr_ss_db=round(gss, 2),
                     overshoot_db=round(ovs, 2), att_t10_ms=round(first(0.1), 2), att_t63_ms=round(first(0.63), 2), att_t90_ms=round(first(0.9), 2),
                     rel_t63_ms=round(rel(0.37), 1), rel_t90_ms=round(rel(0.1), 1), rel_to_1db_ms=round(within(1.0), 1), rel_to_0p1db_ms=round(within(0.1), 1),
                     resid_gr_at_end_db=round(float(np.median(r[-int(0.2 * fs):])), 3), tail_s=sp['tail_s']))
with open('/workspace/uad2/an/comp_burst_depth.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows: print(*[r[k] for k in ('setting','target_gr','burst_s','gr_end_db','overshoot_db','att_t10_ms','att_t63_ms','att_t90_ms','rel_t63_ms','rel_t90_ms','rel_to_1db_ms','rel_to_0p1db_ms','resid_gr_at_end_db')])
