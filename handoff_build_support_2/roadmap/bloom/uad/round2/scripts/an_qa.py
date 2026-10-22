# Sub-ms attack from a 5 kHz sin/cos quadrature pair: g(t) = sqrt(ys^2 + yc^2) / A(t), sample-accurate.
import numpy as np, csv, sys, json, re
sys.path.insert(0, '/workspace/uad2/scripts')
import io2, models as Mo, siglib2
SR = 48000; FIT = json.load(open('/workspace/uad2/an/static_fit.json'))
def gr_trace(ys, yc, sp):
    i0 = int(round(sp['t_step'] * SR)); i1 = i0 + int(round(sp['t_hi'] * SR))
    A = np.full(len(ys), 10 ** (sp['lo_db'] / 20)); A[i0:i1] = 10 ** (sp['hi_db'] / 20)
    g = np.sqrt(ys ** 2 + yc ** 2) / A
    g0 = np.median(g[i0 - 2400:i0 - 10])
    return -20 * np.log10(np.maximum(g, 1e-9) / g0), i0, i1
def met(gr, i0, i1):
    a = gr[i0:i1]; t = np.arange(len(a)) / SR * 1000; gend = np.median(a[-480:])
    f = lambda fr: float(t[np.nonzero(a >= fr * gend)[0][0]]) if (a >= fr * gend).any() else np.nan
    ab = lambda d: float(t[np.nonzero(a >= d)[0][0]]) if (a >= d).any() else np.nan
    g20 = float(a[int(0.020 * SR)]) if len(a) > 960 else np.nan
    # level overshoot: how far the output envelope exceeds its final value in the first 2 ms (dB re final), = GR deficit
    return dict(gr_end_db=round(float(gend), 2), gr_at_0p1ms=round(float(a[5]), 2), gr_at_0p5ms=round(float(a[24]), 2), gr_at_1ms=round(float(a[48]), 2),
                gr_at_5ms=round(float(a[240]), 2), gr_at_20ms=round(g20, 2), t10_ms=round(f(0.1), 3), t63_ms=round(f(0.63), 3), t90_ms=round(f(0.9), 3),
                t_3db_ms=round(ab(3.0), 3), t_6db_ms=round(ab(6.0), 3))
rows = []
ids = sorted(k[:-2] for k in io2._J if k.startswith('qa_') and k.endswith('_s'))
OURS = {"qa_fet_all_att4.0": "room_crush", "qa_dis_nuke_att4.5": "nuke", "qa_la2as_pr50_def": "natural", "qa_ssl_4_auto_att10.0": "glue", "qa_fc_t2_l_t5.0_r_t5.0": "swell"}
for base in ids:
    sp = io2.job(base + '_s')['spec']
    _, ys = io2.rec(base + '_s'); _, yc = io2.rec(base + '_c')
    gr, i0, i1 = gr_trace(ys, yc, sp); m = met(gr, i0, i1)
    row = dict(test=base[3:], source='UAD', lo_db=sp['lo_db'], hi_db=sp['hi_db'], **m); rows.append(row)
    print(row['test'], 'UAD', ' '.join('%s=%s' % (k, v) for k, v in m.items()))
    if base in OURS:
        p = OURS[base]; out = []
        for nm in ('s', 'c'):
            x = siglib2.make(io2.job(base + '_' + nm)['spec']); x = np.concatenate([np.zeros(SR), x])
            y, _ = Mo.run_preset(p, x, FIT[p]['T']); out.append(y[SR:])
        gr2, _, _ = gr_trace(out[0], out[1], sp); m2 = met(gr2, i0, i1)
        rows.append(dict(test=base[3:], source='ours:' + p, lo_db=sp['lo_db'], hi_db=sp['hi_db'], **m2))
        print(row['test'], 'ours:' + p, ' '.join('%s=%s' % (k, v) for k, v in m2.items()))
        np.savez_compressed('/workspace/uad2/an/qa_trace_%s.npz' % p, uad=gr[i0 - 480:i0 + 4800].astype(np.float32), ours=gr2[i0 - 480:i0 + 4800].astype(np.float32))
with open('/workspace/uad2/an/comp_subms_attack.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
