# Chosen pre models vs UAD on the r3 stairs (40/100/1k/5k Hz, drive -30..+12): THD, H2/H3 magnitude and phase.
import sys, json, csv, numpy as np
sys.path.insert(0, '/workspace/uad3'); import prelib as P, harmlib as H
CH = json.load(open(sys.argv[1] if len(sys.argv) > 1 else '/workspace/uad3/pre_choice.json'))
rows = []
for p in ('neve', 'u610a'):
    m = P.Pre(p, CH[p]['cfg']); th = CH[p]['th']
    for f in (40, 100, 1000, 5000):
        i = 'pst3_%s_%d' % (p, f); x, y, keep = P.rec3(i); lv = P.J3[i]['levels']; ym = m.run(x, th); q = 0
        for (a, b), L in zip(keep, lv):
            su = y[q:q + b - a]; q += b - a; sm = ym[a:b]
            r = dict(pre=p, freq=f, rel_drive_db=L - {'neve': -36, 'u610a': -57}[p])
            for nm, s in (('uad', su), ('model', sm)):
                amp, _ = H.hfit(s, f, 5); d, t = H.rel_phase(s, f, 5)
                r[nm + '_thd_pct'] = round(100 * np.sqrt(np.sum(amp[1:] ** 2)) / amp[0], 4); r[nm + '_h2'] = round(d[1], 1); r[nm + '_h3'] = round(d[2], 1)
                r[nm + '_th2'] = round(t[1], 1); r[nm + '_th3'] = round(t[2], 1)
            rows.append(r)
w = csv.DictWriter(open('/workspace/uad3/pre_harm_check.csv', 'w', newline=''), list(rows[0])); w.writeheader(); w.writerows(rows)
for p in ('neve', 'u610a'):
    for f in (40, 100, 1000, 5000):
        rr = [r for r in rows if r['pre'] == p and r['freq'] == f and -30 <= r['rel_drive_db'] <= 6]
        dthd = [20 * np.log10(max(r['model_thd_pct'], 1e-6) / max(r['uad_thd_pct'], 1e-6)) for r in rr if r['uad_thd_pct'] > 0.01]
        h2 = [abs(r['model_h2'] - r['uad_h2']) for r in rr if r['uad_h2'] > -80]; h3 = [abs(r['model_h3'] - r['uad_h3']) for r in rr if r['uad_h3'] > -80]
        t2 = [abs((r['model_th2'] - r['uad_th2'] + 180) % 360 - 180) for r in rr if r['uad_h2'] > -70]; t3 = [abs((r['model_th3'] - r['uad_th3'] + 180) % 360 - 180) for r in rr if r['uad_h3'] > -70]
        md = lambda a: '%.1f(n%d)' % (np.median(a), len(a)) if a else '-'
        print(p, f, 'THD err dB med', md(list(np.abs(dthd))), 'bias', '%.1f' % np.median(dthd) if dthd else '-', '| |dH2|', md(h2), '|dH3|', md(h3), '| |dth2|', md(t2), '|dth3|', md(t3))
        for r in rr:
            if r['rel_drive_db'] in (-12, -6, 0, 4): print('   d%+d THD uad %.3f%% model %.3f%% | H2 %.0f/%.0f H3 %.0f/%.0f | th2 %.0f/%.0f th3 %.0f/%.0f' % (r['rel_drive_db'], r['uad_thd_pct'], r['model_thd_pct'], r['uad_h2'], r['model_h2'], r['uad_h3'], r['model_h3'], r['uad_th2'], r['model_th2'], r['uad_th3'], r['model_th3']))
