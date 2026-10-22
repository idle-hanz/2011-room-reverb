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
