# SMPTE (60 Hz + 7 kHz 4:1) and CCIF (19+20 kHz) IMD stairs: UAD vs BLOOM current vs prototype (dyn+colour, 1x and 2x).
# SMPTE sidebands are also the gain-path modulation test (60 Hz drives the detector; 7 kHz is the HF probe).
import sys, json, csv, numpy as np
sys.path.insert(0, '/workspace/uad2/scripts'); sys.path.insert(0, '/workspace/uad3')
import io2, anlib as A, models as Mo, alias_proto as AP3, comp_proto as CP
FIT = json.load(open('/workspace/uad2/an/static_fit.json'))
U = {'natural': 'la2as_pr50', 'room_crush': 'fet_all', 'nuke': 'dis_nuke', 'swell': 'fc_t2', 'glue': 'ssl_4_auto'}
rows = []
for p, u in U.items():
    for test in ('smpte', 'ccif'):
        i = 'c%s_%s' % (test, u); m, y = A.load(i); x = io2.xin(i); keep = json.loads(m['keep']) if isinstance(m['keep'], str) else m['keep']
        segu = A.stair_segments(y[0] if y.ndim == 2 else y, keep)
        yc, _ = Mo.run_preset(p, x, FIT[p]['T']); P = CP.dyn_params(p); C = AP3.best_colour(p)
        y1, _ = AP3.run_c(p, x, P, C, 1, False); y2, _ = AP3.run_c(p, x, P, C, 2, False)
        fn = A.imd_smpte if test == 'smpte' else A.imd_ccif
        for k, (a0, b0) in enumerate(keep):
            r = dict(preset=p, unit=u, test=test, step=k)
            for nm, yy in (('uad', segu[k]), ('current', yc[a0:b0]), ('proto1x', y1[a0:b0]), ('proto2x', y2[a0:b0])):
                s = yy[len(yy) // 2:]; d = fn(s); r[nm + '_imd_pct'] = round(d['imd_pct'], 4)
                if test == 'smpte': r[nm + '_sb1_dbc'] = round(d['sb1_dbc'], 1)
                else: r[nm + '_d2_dbc'] = round(d['d2_dbc'], 1); r[nm + '_d3_dbc'] = round(d['d3_dbc'], 1)
            rows.append(r); print(*r.values(), flush=True)
w = csv.DictWriter(open('/workspace/uad3/imd_proto.csv', 'w', newline=''), list(dict.fromkeys(k for r in rows for k in r))); w.writeheader(); w.writerows(rows)
