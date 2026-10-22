# Round-3 program nulls: UAD vs BLOOM current / current+UAD FR / proto dyn / proto dyn+colour / shippable proto (dyn+colour+fitted EQ).
# Works on box (synthetic prog_*) and on the PC (real rprog_*): set env UADROOT to the folder holding uad2/ and uad3/.
import os, sys, json, csv, numpy as np
ROOT = os.environ.get('UADROOT', '/workspace'); sys.path.insert(0, ROOT + '/uad2/scripts'); sys.path.insert(0, ROOT + '/uad3')
import io2, models as Mo, an_prog_lib as AP, comp_proto as CP, dyn3
from scipy.signal import sosfilt
SR = 48000
EQ = json.load(open(ROOT + '/uad3/eq_fit.json')); FIT = json.load(open(ROOT + '/uad2/an/static_fit.json'))
def colour_of(p):
    f = ROOT + '/uad3/colour_choice.json'
    return json.load(open(f)).get(p) if os.path.exists(f) else None
def eq(p, y):
    sos = np.array([list(q['b']) + list(q['a']) for q in EQ[p]['biquads']]); return sosfilt(sos, y)
def frac_delay(k):
    K = np.fft.rfft(np.roll(np.pad(k, (0, 16384 - len(k))), -AP.V.PRE)); fr = np.fft.rfftfreq(16384, 1 / SR)
    m = (fr > 300) & (fr < 3000); ph = np.unwrap(np.angle(K)); return -np.polyfit(2 * np.pi * fr[m], ph[m], 1)[0] * SR
def shift(y, D):
    n = len(y); N = 1 << int(np.ceil(np.log2(n + 4096))); Y = np.fft.rfft(y, N); f = np.fft.rfftfreq(N)
    return np.fft.irfft(Y * np.exp(-2j * np.pi * f * D), N)[:n]
def proto(p, x, colour=True):
    P = CP.dyn_params(p); C = colour_of(p) if colour else None
    if C is None: gr = dyn3.gr_of(p, x, P); return 10 ** (-gr / 20) * x, gr
    gr = dyn3.gr_of(p, x, P); g = 10 ** (-gr / 20); side = C.get('side', CP.SIDE[p])
    if side == 'in': return g * CP.colour(x, np.zeros_like(gr), C), gr
    return CP.colour(g * x, gr, C), gr
def compare(p, unit, x, y, tag):
    k = AP.h1(unit); gs = AP.g_ss(unit); D = frac_delay(k)
    out = dict(preset=p, unit=unit, prog=tag)
    yc, grc = Mo.run_preset(p, x, FIT[p]['T'])
    out['null_current'] = AP.null_db(y, shift(yc, D))[0]
    out['null_current_uadFR'] = AP.null_db(y, AP.lin(yc, k))[0]
    yd, grd = proto(p, x, False); out['null_protodyn_uadFR'] = AP.null_db(y, AP.lin(yd, k))[0]
    yp, grp = proto(p, x, True); out['null_proto_uadFR'] = AP.null_db(y, AP.lin(yp, k))[0]
    out['null_proto_EQ'] = AP.null_db(y, shift(eq(p, yp), D))[0]
    out['null_current_EQ'] = AP.null_db(y, shift(eq(p, yc), D))[0]
    # GR error vs UAD (r2 method)
    hx = AP.lin(x, k); gu, ex = AP.block_gain(hx, y); rho = AP.block_gain.rho.copy()
    GRu = -20 * np.log10(np.maximum(np.abs(gu), 1e-6))
    act = (ex > max(-60.0, ex.max() - 40)) & (rho > 0.95)
    for nm, gr in (('current', grc), ('proto', grp)):
        GRm = np.asarray(gr)[AP.B // 2::AP.B][:len(GRu)]; n = len(GRm)
        d = (GRm - GRu[:n])[act[:n]]; d = d - np.median(d)   # offset-free GR shape error (makeup not modelled)
        out['grerr_rms_' + nm] = float(np.sqrt(np.mean(d ** 2))); out['grerr_p99_' + nm] = float(np.percentile(np.abs(d), 99))
    return {a: (round(b, 2) if isinstance(b, float) else b) for a, b in out.items()}, dict(yc=yc, yp=yp, ype=shift(eq(p, yp), D), yce=shift(eq(p, yc), D))
