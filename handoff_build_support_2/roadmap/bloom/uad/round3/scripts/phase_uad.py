import sys, json, numpy as np, csv
sys.path.insert(0, '/workspace/uad2/scripts'); sys.path.insert(0, '/workspace/uad3')
import io2, anlib as A, harmlib as H
rows = []
LV = list(range(-45, 13, 3))
for u in ['la2as_pr50', 'la2as_nocomp', 'ssl_4_auto', 'fet_all', 'dis_nuke', 'dis_1_norm', 'fc_t2', 'fc_nocomp', 'fc_t5', 'ln_4', 'mvm_lim']:
    for f in (100, 1000, 5000):
        id_ = ('c1k_%s' % u) if f == 1000 else ('c%d_%s' % (f, u))
        try: m, y = A.load(id_)
        except Exception: continue
        segs = A.stair_segments(y, m['keep'])
        for L, s in zip(LV, segs):
            d, th = H.rel_phase(s[0], f, 5)
            rows.append(dict(src=u, freq=f, in_dbfs=L, out_dbfs=round(float(A.db(H.hfit(s[0], f, 1)[0][0])), 2), h2_dbc=round(d[1], 1), h3_dbc=round(d[2], 1), th2_deg=round(th[1], 1), th3_deg=round(th[2], 1)))
PLV = list(range(-90, 1, 3))
for p in ['neve', 'u610a', 'u610b', 'api', 'sslE', 'manley']:
    for f in (20, 30, 50, 200):
        m, y = A.load('p%d_%s' % (f, p)); segs = A.stair_segments(y, m['keep'])
        for L, s in zip(PLV, segs):
            d, th = H.rel_phase(s[0], f, 5)
            rows.append(dict(src='pre_' + p, freq=f, in_dbfs=L, out_dbfs=round(float(A.db(H.hfit(s[0], f, 1)[0][0])), 2), h2_dbc=round(d[1], 1), h3_dbc=round(d[2], 1), th2_deg=round(th[1], 1), th3_deg=round(th[2], 1)))
w = csv.DictWriter(open('/workspace/uad3/harm_phase_uad.csv', 'w', newline=''), list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows:
    if (r['h2_dbc'] > -85 or r['h3_dbc'] > -85) and r['in_dbfs'] % 6 == 0: print(*r.values())
