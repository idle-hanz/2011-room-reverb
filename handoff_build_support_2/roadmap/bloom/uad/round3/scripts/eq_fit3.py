# Fixed EQ v3: richer IIR (HP2 + 2 peaking + LS + HS) complex fit to UAD ESS kernel, 12 Hz-17 kHz, 240 log points. Keeps v2 where v3 is not better.
import sys, json, numpy as np
sys.path.insert(0, '/workspace/uad3'); import an_prog_lib as AP, prog3 as P, eq_fit2 as E2, eq_fit as E
from scipy.signal import sosfreqz
from scipy.optimize import least_squares
SR = 48000; fq = np.geomspace(12, 17000, 240)
def pk(f0, g, Q):
    A = 10 ** (g / 40); w = 2 * np.pi * f0 / SR; c, s = np.cos(w), np.sin(w); al = s / (2 * Q)
    b = [1 + al * A, -2 * c, 1 - al * A]; a = [1 + al / A, -2 * c, 1 - al / A]; return np.array(b) / a[0], np.array(a) / a[0]
def secs(z): return [E.rbj('hp', z[0], z[1]), pk(z[2], z[3], z[4]), pk(z[5], z[6], z[7]), E2.ls(z[8], z[9], 0.707), E.rbj('hs', z[10], 0.707, z[11])]
def H(z): return sosfreqz(np.array([list(b) + list(a) for b, a in secs(z)]), worN=fq, fs=SR)[1]
old = json.load(open('/workspace/uad3/eq_fit.json')); out = dict(old)
for p in sys.argv[1:]:
    u = old[p]['unit']; k = AP.h1(u); N = 1 << 16; K = np.fft.rfft(np.roll(np.pad(k, (0, N - len(k))), -AP.V.PRE)); fr = np.fft.rfftfreq(N, 1 / SR)
    D = P.frac_delay(k); K = K * np.exp(2j * np.pi * fr * D / SR); K = np.interp(fq, fr, K.real) + 1j * np.interp(fq, fr, K.imag); K = K / np.abs(K[np.argmin(abs(fq - 1000))])
    f = lambda z: np.concatenate([(np.log(np.abs(H(z) / K))) * 8.686 / 0.25, np.angle(H(z) / K) * 57.3 / 3.0])
    best = None
    for z0 in ([8, 0.6, 40, 0, 1, 3000, 0, 1, 100, 0, 10000, 0], [15, 0.8, 25, 1, 0.7, 8000, -0.5, 0.7, 200, -0.5, 12000, -0.3]):
        s = least_squares(f, z0, bounds=([2, 0.3, 15, -8, 0.2, 500, -6, 0.2, 20, -6, 3000, -4], [40, 2, 400, 8, 4, 16000, 6, 4, 1000, 6, 20000, 4]))
        if best is None or s.cost < best.cost: best = s
    z = best.x; h = H(z); md = np.abs(20 * np.log10(np.abs(h / K)))[fq >= 20].max(); pdg = np.abs(np.degrees(np.angle(h / K)))[fq >= 20].max()
    # time-domain check on a program
    import io2
    x, _ = io2.rec('prog_%s_tail_a' % u); ref = AP.lin(x, k)
    sos_new = np.array([list(b) + list(a) for b, a in secs(z)])
    from scipy.signal import sosfilt
    n_new = AP.null_db(ref, P.shift(sosfilt(sos_new, x), D))[0]; n_old = AP.null_db(ref, P.shift(P.eq(p, x), D))[0]
    print(p, 'v3 mag %.2f dB phase %.1f deg, tail_a null %.1f (v2 %.1f)' % (md, pdg, n_new, n_old), np.round(z, 2))
    if n_new < n_old - 0.5:
        out[p] = dict(unit=u, src='h1 cess_%s_-30 (v3: HP2+2PK+LS+HS)' % u, params=list(map(float, z)), max_mag_err_db=float(md), max_phase_err_deg=float(pdg),
                      biquads=[dict(b=list(map(float, b)), a=list(map(float, a))) for b, a in secs(z)])
json.dump(out, open('/workspace/uad3/eq_fit.json', 'w'), indent=1)
