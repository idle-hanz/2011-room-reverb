# Run our preset models on exactly the same burst-depth signals and compare timing metrics with UAD.
import numpy as np, csv, sys, json
sys.path.insert(0, '/workspace/uad2/scripts')
import io2, models as Mo, siglib2
SR = 48000; FIT = json.load(open('/workspace/uad2/an/static_fit.json'))
def env(v, w=48, dec=12):
    c = np.concatenate([[0.0], np.cumsum(v.astype(np.float64) ** 2)]); m = (c[w:] - c[:-w]) / w
    e = np.sqrt(2 * np.maximum(m, 0)); pad = w // 2
    return np.concatenate([np.full(pad, e[0]), e, np.full(len(v) - len(e) - pad, e[-1])])[::dec]
def metrics(ei, eo, sp, dec=12):
    fs = SR / dec; gr = -20 * np.log10(np.maximum(eo, 1e-12) / np.maximum(ei, 1e-12))
    i_on = int(round(sp['pre_s'] * fs)); i_off = i_on + int(round(sp['burst_s'] * fs))
    gr = gr - np.median(gr[int(i_on - 0.2 * fs):i_on - 8])
    gend = gr[i_off - 1]; a = gr[i_on:i_off]; ta = np.arange(len(a)) / fs * 1000
    first = lambda fr: float(ta[np.nonzero(a >= fr * gend)[0][0]]) if (a >= fr * gend).any() else np.nan
    r = gr[i_off:]; tr = np.arange(len(r)) / fs * 1000
    rel = lambda fr: float(tr[np.nonzero(r <= fr * gend)[0][0]]) if (r <= fr * gend).any() else np.nan
    within = lambda d: float(tr[np.nonzero(np.abs(r) <= d)[0][0]]) if (np.abs(r) <= d).any() else np.nan
    return dict(gr_end=round(float(gend), 2), att63=round(first(0.63), 2), att90=round(first(0.9), 2),
                rel63=round(rel(0.37), 1), rel90=round(rel(0.1), 1), rel_1db=round(within(1.0), 1)), gr
