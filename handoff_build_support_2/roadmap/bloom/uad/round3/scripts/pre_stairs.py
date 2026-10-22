import sys, numpy as np, csv
sys.path.insert(0, '/workspace/uad3'); import prelib as P, harmlib as H
rows = []
for p in ('neve', 'u610a'):
    for f in (40, 100, 1000, 5000):
        x, y, keep = P.rec3('pst3_%s_%d' % (p, f)); lv = P.J3['pst3_%s_%d' % (p, f)]['levels']; q = 0
        for (a, b), L in zip(keep, lv):
            s = y[q:q + b - a]; q += b - a
            amp, ph = H.hfit(s, f, 5); d, th = H.rel_phase(s, f, 5)
            thd = 100 * np.sqrt(np.sum(amp[1:] ** 2)) / amp[0]
            rows.append(dict(pre=p, freq=f, in_dbfs=L, rel_drive_db=L - {'neve': -36, 'u610a': -57}[p], out_dbfs=round(20 * np.log10(amp[0]), 2), thd_pct=round(thd, 4),
                             h2_dbc=round(d[1], 1), h3_dbc=round(d[2], 1), h4_dbc=round(d[3], 1), h5_dbc=round(d[4], 1), th2_deg=round(th[1], 1), th3_deg=round(th[2], 1)))
w = csv.DictWriter(open('/workspace/uad3/pre_stairs_r3.csv', 'w', newline=''), list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows:
    if r['rel_drive_db'] % 4 == 0 and r['rel_drive_db'] >= -18: print(*r.values())
