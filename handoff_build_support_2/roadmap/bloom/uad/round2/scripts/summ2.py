import csv, collections, numpy as np
A = '/workspace/uad2/an/'
C = list(csv.DictReader(open(A + 'comp_colour_vs_gr.csv')))
I = list(csv.DictReader(open(A + 'comp_imd_steps.csv')))
G = [0, 3, 6, 10, 15]
out = []
byS = collections.OrderedDict()
for r in C: byS.setdefault(r['setting'], {}).setdefault(int(r['freq']), {})[int(r['gr_target'])] = r
imd = collections.defaultdict(list)
for r in I:
    if r['gr_db'] == '': continue
    imd[(r['setting'], r['test'])].append(r)
def imd_at(s, test, g):
    v = imd.get((s, test));
    if not v: return ''
    gr = np.array([float(r['gr_db']) for r in v]); i = int(np.argmin(np.abs(gr - g)))
    if abs(gr[i] - g) > max(1.5, 0.25 * g): return ''
    r = v[i]
    return ('%.3g' % float(r['imd_pct'])) if test == 'smpte' else (r['d2_dbc'] + '/' + r['d3_dbc'])
for s, F in byS.items():
    row = {'setting': s}
    for f in (100, 1000, 5000):
        for g in G:
            r = F.get(f, {}).get(g)
            row['thd%%_%d_gr%d' % (f, g)] = '' if r is None else '%.3g' % float(r['thd_pct'])
            if f == 1000:
                row['twin_thd%%_1k_gr%d' % g] = '' if r is None or r['twin_thd_pct'] == '' else '%.3g' % float(r['twin_thd_pct'])
                row['h2_1k_gr%d' % g] = '' if r is None else r['h2_dbc']; row['h3_1k_gr%d' % g] = '' if r is None else r['h3_dbc']
    for g in G:
        row['smpte%%_gr%d' % g] = imd_at(s, 'smpte', g); row['ccif_d2/d3_gr%d' % g] = imd_at(s, 'ccif', g)
    out.append(row)
keys = list(out[0]); [keys.append(k) for r in out for k in r if k not in keys]
with open(A + 'comp_colour_summary.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)
for r in out:
    print(r['setting'].ljust(16), '1k THD%', [r.get('thd%%_1000_gr%d' % g, '') for g in G], 'twin', [r.get('twin_thd%%_1k_gr%d' % g, '') for g in G],
          '| H2', [r.get('h2_1k_gr%d' % g) for g in G], 'H3', [r.get('h3_1k_gr%d' % g) for g in G])
    print(' ' * 16, '100 THD%', [r.get('thd%%_100_gr%d' % g, '') for g in G], '5k THD%', [r.get('thd%%_5000_gr%d' % g, '') for g in G], 'SMPTE%', [r['smpte%%_gr%d' % g][:6] for g in G], 'CCIF', [r['ccif_d2/d3_gr%d' % g] for g in G])
