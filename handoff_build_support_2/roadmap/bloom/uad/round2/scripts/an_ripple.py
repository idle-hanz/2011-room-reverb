# How much of the 'colour while compressing' is gain-ripple (reproducible by a correct gain computer) vs circuit colour?
# Our preset models (pure gain, no waveshaping) on the same 100 Hz / 1 kHz / 5 kHz staircases as UAD.
import numpy as np, csv, sys, json
sys.path.insert(0, '/workspace/uad2/scripts')
import io2, models as Mo, units as U, anlib as AL
SR = 48000; LV = list(range(-45, 13, 3)); FIT = json.load(open('/workspace/uad2/an/static_fit.json'))
rows = []
for p, u in Mo.PRESET_UNIT.items():
    if u == 'dis_nuke_room': u = 'dis_nuke'      # staircases exist for dis_nuke (detector Norm); HP detector irrelevant at 1k/5k but NOT at 100 Hz
    st = U.COMP[u][2]; s = str(st).replace('.', 'p'); n = int(st * SR); K = SR // 2
    for f in (100, 1000, 5000):
        idu = 'c%s_%s' % ('1k' if f == 1000 else str(f), u)
        if idu not in io2._J: continue
        _, yu = io2.rec(idu)
        x = np.load(io2.I + 'st_%d_%s.npy' % (f, s)).astype(float)
        ym, gr = Mo.run_preset(p, np.concatenate([np.zeros(SR), x]), FIT[p]['T']); ym = ym[SR:]
        for i, L in enumerate(LV):
            su = yu[i * K:(i + 1) * K]; sm = ym[(i + 1) * n - K:(i + 1) * n]
            hu = AL.harm(su, f); hm = AL.harm(sm, f)
            gru = None
            rows.append(dict(preset=p, unit=u, freq=f, in_dbfs=L, uad_out_dbfs=round(float(AL.db(hu['fund'])), 2), ours_out_dbfs=round(float(AL.db(hm['fund'])), 2),
                             uad_thd_pct=round(hu['thd_pct'], 4), ours_thd_pct=round(hm['thd_pct'], 4),
                             uad_h2=round(hu['h_dbc'][0], 1), ours_h2=round(hm['h_dbc'][0], 1), uad_h3=round(hu['h_dbc'][1], 1), ours_h3=round(hm['h_dbc'][1], 1)))
# add GR columns relative to the -45 step
import collections
g = collections.defaultdict(list)
for r in rows: g[(r['preset'], r['freq'])].append(r)
for k, v in g.items():
    u0 = v[0]['uad_out_dbfs'] - v[0]['in_dbfs']; m0 = v[0]['ours_out_dbfs'] - v[0]['in_dbfs']
    for r in v:
        r['uad_gr'] = round(u0 - (r['uad_out_dbfs'] - r['in_dbfs']), 2); r['ours_gr'] = round(m0 - (r['ours_out_dbfs'] - r['in_dbfs']), 2)
with open('/workspace/uad2/an/ripple_vs_uad.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for k, v in g.items():
    print(k, ' | '.join('%d: GR %.1f/%.1f THD %.3g/%.3g' % (r['in_dbfs'], r['uad_gr'], r['ours_gr'], r['uad_thd_pct'], r['ours_thd_pct']) for r in v if r['in_dbfs'] % 6 == 3 or r['in_dbfs'] in (-45,)))
