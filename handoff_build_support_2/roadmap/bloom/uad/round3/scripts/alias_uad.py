import sys, json, numpy as np, csv
sys.path.insert(0, '/workspace/uad3'); import alias as AL
J = {j['id']: j for j in json.load(open('/workspace/uad3/jobs_r3.json'))}
rows = []
for id_, j in J.items():
    if not id_.startswith('al_'): continue
    y = np.load('/workspace/uad3/r3out/%s.npz' % id_)['y'][0].astype(float)
    m = json.load(open('/workspace/uad3/r3out/%s.json' % id_))
    _, u, f, L = id_.split('_', 3) if id_.count('_') == 3 else (None, '_'.join(id_.split('_')[1:-2]), id_.split('_')[-2], id_.split('_')[-1])
    r = AL.tone_alias(y, float(f)); rows.append(dict(unit=u, f=int(f), in_db=L, latency=m['reported_latency'], **{k: (round(float(v), 1) if isinstance(v, (float, np.floating)) else v) for k, v in r.items()}))
w = csv.DictWriter(open('/workspace/uad3/alias_uad_tones.csv', 'w', newline=''), list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows: print(r['unit'], r['f'], r['in_db'], 'fund %.1f | M1 alias %.1f dBFS (k%d @%d) | M2 peak %.1f @%d, <16k %.1f @%d, tot %.1f dBc' % (r['fund_dbfs'], r['m1_worst_alias_dbfs'], r['m1_worst_k'], r['m1_worst_f'], r['m2_peak_resid_dbfs'], r['m2_peak_f'], r['m2_peak_below16k_dbfs'], r['m2_peak_below16k_f'], r['m2_resid_total_dbc']))
