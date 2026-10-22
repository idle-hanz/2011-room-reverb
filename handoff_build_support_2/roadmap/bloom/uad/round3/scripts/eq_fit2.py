# Fixed EQ v2: complex fit (mag+phase) to the UAD ESS linear kernel h1 (r2 cess_<unit>_-30), 15 Hz-17 kHz, log-spaced.
# Sections: HP1 (bilinear), low shelf (RBJ), high shelf (RBJ). Delay removed (fractional, 300-3k phase slope); 1 kHz normalised.
import sys, json, numpy as np
sys.path.insert(0, '/workspace/uad3'); import an_prog_lib as AP, prog3 as P, eq_fit as E
from scipy.signal import sosfreqz
from scipy.optimize import least_squares
SR = 48000; U = {'natural': 'la2as_pr50', 'room_crush': 'fet_all', 'nuke': 'dis_nuke_room', 'swell': 'fc_t5', 'glue': 'ssl_4_auto'}
fq = np.geomspace(15, 17000, 120)
def hp1(fc):
    k = np.tan(np.pi * fc / SR); return np.array([1, -1, 0]) / (1 + k), np.array([1, (k - 1) / (k + 1), 0])
def ls(f0, g, Q=0.707):
    A = 10 ** (g / 40); w = 2 * np.pi * f0 / SR; c, s = np.cos(w), np.sin(w); al = s / (2 * Q); sq = 2 * np.sqrt(A) * al
    b = [A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq)]
    a = [(A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq]
    return np.array(b) / a[0], np.array(a) / a[0]
def secs(z):
    s = [hp1(z[0]), ls(z[1], z[2], z[3]), E.rbj('hs', z[4], 0.707, z[5])]
    return s
def H(z):
    sos = np.array([list(b) + list(a) for b, a in secs(z)]); return sosfreqz(sos, worN=fq, fs=SR)[1]
if __name__ == '__main__':
    out = {}
    for p, u in U.items():
        k = AP.h1(u); N = 1 << 16; K = np.fft.rfft(np.roll(np.pad(k, (0, N - len(k))), -AP.V.PRE)); fr = np.fft.rfftfreq(N, 1 / SR)
        D = P.frac_delay(k); K = K * np.exp(2j * np.pi * fr * D / SR); K = np.interp(fq, fr, K.real) + 1j * np.interp(fq, fr, K.imag)
        K = K / np.abs(K[np.argmin(abs(fq - 1000))])
        def f(z):
            h = H(z); e = np.log(h / K); return np.concatenate([e.real * 8.686 / 0.5, np.angle(h / K) * 57.3 / 5.0])
        best = None
        for z0 in ([5, 60, 0, 0.7, 8000, 0], [12, 150, -1, 0.7, 12000, 0.5], [2, 40, 1, 1.0, 5000, -0.5]):
            s = least_squares(f, z0, bounds=([1, 20, -6, 0.3, 2000, -4], [40, 1000, 6, 2.0, 20000, 4]))
            if best is None or s.cost < best.cost: best = s
        z = best.x; h = H(z); md = 20 * np.log10(np.abs(h / K)); pd = np.degrees(np.angle(h / K))
        sel = fq >= 20
        out[p] = dict(unit=u, src='h1 cess_%s_-30' % u, hp1_fc=z[0], ls_f=z[1], ls_db=z[2], ls_q=z[3], hs_f=z[4], hs_db=z[5],
                      max_mag_err_db=float(np.max(np.abs(md[sel]))), max_phase_err_deg=float(np.max(np.abs(pd[sel]))),
                      uad_db_at={str(ff): round(float(20 * np.log10(abs(K[np.argmin(abs(fq - ff))]))), 2) for ff in (20, 31.5, 50, 100, 10000, 15000)},
                      biquads=[dict(b=list(map(float, b)), a=list(map(float, a))) for b, a in secs(z)])
        print(p, np.round(z, 3), 'mag err %.2f dB phase err %.1f deg' % (out[p]['max_mag_err_db'], out[p]['max_phase_err_deg']), out[p]['uad_db_at'])
    json.dump(out, open('/workspace/uad3/eq_fit.json', 'w'), indent=1)
