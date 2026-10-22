# Round-3 mic-pre prototypes: linear path = measured 8192-tap kernel; nonlinear branch = emphasis -> shaper (+ transformer flux term, + bias memory) -> de-emphasis -> output filter.
import numpy as np, json, sys
sys.path.insert(0, '/workspace/uad2/scripts')
import volterra as V
from io2 import rec as rec2
from scipy.signal import fftconvolve, butter, sosfiltfilt, sosfilt
from numba import njit
SR = 48000; PRE = V.PRE
J3 = {j['id']: j for j in json.load(open('/workspace/uad3/jobs_r3.json'))}
def rec3(id_):
    j = J3[id_]; y = np.load('/workspace/uad3/r3out/%s.npz' % id_)['y'][0].astype(float)
    x = np.load('/workspace/uad3/r3in/%s' % j['input']).astype(np.float32)
    if 'gain_db' in j: x = (x * np.float32(10 ** (j['gain_db'] / 20.0))).astype(np.float32)
    return x.astype(float), y, j.get('keep')
_K = {}
def klin(p, M=8192):
    if (p, M) not in _K:
        x, y = rec2('pess_%s_-30' % p); _K[(p, M)] = V.fit_hammerstein([(x, y)], N=1, M=M)[0]
    return _K[(p, M)]
def lin(x, k): return fftconvolve(x, k)[PRE:PRE + len(x)]
def gain1k(k):
    K = np.fft.rfft(np.roll(np.pad(k, (0, 65536 - len(k))), -PRE)); fr = np.fft.rfftfreq(65536, 1 / SR)
    return float(np.abs(K[np.argmin(np.abs(fr - 1000))]))
@njit(cache=True)
def shelf_lp(x, a, g):
    """emphasis: y = x + (g-1)*LP1(x)  (low-shelf boost by g below fc, a = exp(-2 pi fc/SR))"""
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s = a * s + (1 - a) * x[i]; y[i] = x[i] + (g - 1.0) * s
    return y
@njit(cache=True)
def shelf_lp_inv(x, a, g):
    """exact inverse of shelf_lp"""
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        # x = y + (g-1)*(a*s + (1-a)*y)  -> y = (x - (g-1)*a*s)/(1 + (g-1)*(1-a))
        yi = (x[i] - (g - 1.0) * a * s) / (1.0 + (g - 1.0) * (1 - a)); s = a * s + (1 - a) * yi; y[i] = yi
    return y
@njit(cache=True)
def shaper(u, fam, p0, p1, p2, p3, mem_m, mem_a):
    """returns S(u)-u (distortion part), unity small-signal slope.
    fam 0: poly  p0*u^2 + p1*u^3 + p2*u^4 + p3*u^5
    fam 1: biased tanh  (tanh(u+b)-tanh(b))/sech^2(b) - u, b=p0 (+ bias memory b += mem_m*LP(|u|)) ; plus p1*u^2 extra
    fam 2: soft-clip poly: u - u^3/3 for |u|<1 limited, with asym p0*u^2 """
    n = len(u); d = np.empty(n); m = 0.0
    for i in range(n):
        v = u[i]
        if fam == 0:
            d[i] = p0 * v * v + p1 * v * v * v + p2 * v ** 4 + p3 * v ** 5
        elif fam == 1:
            m = mem_a * m + (1 - mem_a) * abs(v); b = p0 + mem_m * m
            t0 = np.tanh(b); s2 = 1 - t0 * t0
            d[i] = (np.tanh(v + b) - t0) / s2 - v + p1 * v * v
        elif fam == 2:
            w = min(max(v, -1.0), 1.0); d[i] = (w - w * w * w / 3.0) * 1.5 - v + p0 * v * v
        else:
            # fam 3: n-th order smooth hard clip, asymmetric knee: s = 1+p1 (v>0) / 1-p1 (v<0); n = p0; extra even term p2*v^2; bias memory on p1
            m = mem_a * m + (1 - mem_a) * v; a = p1 + mem_m * m
            sc = 1.0 + a if v > 0 else 1.0 - a
            w = v / sc
            d[i] = sc * w / (1.0 + abs(w) ** p0) ** (1.0 / p0) - v + p2 * v * v
    return d
@njit(cache=True)
def flux_term(v, a, Vphi, c):
    """transformer core: phi = LP1(v) (integrator above fc); distortion = c*Vphi*inverseLP((phi/Vphi)^3)."""
    n = len(v); d = np.empty(n); s = 0.0; ep = 0.0
    for i in range(n):
        s = a * s + (1 - a) * v[i]; e = (s / Vphi) ** 3
        d[i] = c * Vphi * (e - a * ep) / (1 - a); ep = e
    return d
BP = butter(6, [20.0, 19000.0], 'bandpass', fs=SR, output='sos')
def bl(y): return sosfiltfilt(BP, y)
class Pre:
    def __init__(self, p, cfg):
        self.p = p; self.k = klin(p); self.G = gain1k(self.k); self.kn = self.k / self.G; self.cfg = cfg
    def nl(self, x, th):
        c = self.cfg; v = x * self.G; Vc = 10 ** (th['vc_db'] / 20)
        if c.get('emph'):
            a = np.exp(-2 * np.pi * th['emph_fc'] / SR); g = 10 ** (th['emph_db'] / 20); ue = shelf_lp(v, a, g)
        else: ue = v
        u = ue / Vc
        d = Vc * shaper(u, c['fam'], th.get('p0', 0.0), th.get('p1', 0.0), th.get('p2', 0.0), th.get('p3', 0.0),
                        th.get('mem_m', 0.0), np.exp(-1.0 / (max(th.get('mem_tau', 0.01), 1e-4) * SR)))
        if c.get('emph') and c.get('deemph', True): d = shelf_lp_inv(d, a, g)
        if c.get('flux'):
            af = np.exp(-2 * np.pi * th['phi_fc'] / SR); d = d + flux_term(v, af, 10 ** (th['phi_db'] / 20), th['phi_c'])
        return d
    def run(self, x, th):
        return lin(x, self.k) + lin(self.nl(x, th), self.kn)
