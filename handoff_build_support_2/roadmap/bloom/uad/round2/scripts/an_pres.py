import json, os, csv, numpy as np
import anlib as A, pass1 as P1, units as U, siglib as S
from scipy.signal import butter, sosfilt, bilinear, lfilter
SR = 48000; AN = "/workspace/uad2/an"
GAIN = {"neve": 47.4, "u610a": 43.5, "u610b": 35.9, "api": 41.0, "sslE": 28.8, "manley": 34.6}
def wcsv(path, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    w = csv.DictWriter(open(path, "w", newline=""), keys); w.writeheader(); [w.writerow(r) for r in rows]
def lf_stairs():
    rows = []
    for name in U.PRES:
        for f in (20, 30, 50, 200):
            m, y = A.load("p%d_%s" % (f, name)); segs = A.stair_segments(y, m["keep"])
            for L, s in zip(P1.PLV, segs):
                h = A.harm(s[0], float(f))
                rows.append({"pre": name, "freq": f, "in_dbfs": L, "out_dbfs": round(A.db(h["fund"]), 2), "thd_pct": h["thd_pct"],
                             "h2_dbc": round(h["h_dbc"][0], 1), "h3_dbc": round(h["h_dbc"][1], 1)})
    wcsv(AN + "/pre_lf_steps.csv", rows); return rows
def imd():
    rows = []
    for name in U.PRES:
        for k in ("smpte", "ccif"):
            m, y = A.load("p%s_%s" % (k, name)); segs = A.stair_segments(y, m["keep"])
            for L, s in zip(P1.PLV, segs):
                r = (A.imd_smpte if k == "smpte" else A.imd_ccif)(s[0])
                ref = r["a60"] if k == "smpte" else r["a19"]
                rows.append({"pre": name, "test": k, "in_peak_dbfs": L, "out_ref_tone_dbfs": round(A.db(ref), 2),
                             "imd_pct": r["imd_pct"], **{kk: round(v, 1) for kk, v in r.items() if kk.endswith("dbc")}})
    wcsv(AN + "/pre_imd_steps.csv", rows); return rows
def aweight():
    f1, f2, f3, f4 = 20.598997, 107.65265, 737.86223, 12194.217
    NUM = [(2 * np.pi * f4) ** 2 * (10 ** (1.9997 / 20)), 0, 0, 0, 0]
    DEN = np.polymul([1, 4 * np.pi * f4, (2 * np.pi * f4) ** 2], [1, 4 * np.pi * f1, (2 * np.pi * f1) ** 2])
    DEN = np.polymul(np.polymul(DEN, [1, 2 * np.pi * f3]), [1, 2 * np.pi * f2])
    return bilinear(NUM, DEN, SR)
def noise():
    rows = []; b, a = aweight()
    for name, (pl, pr, r1, gains) in U.PRES.items():
        for gname, gp in gains:
            jid = "pnoise_%s_%s" % (name, gname.replace(' ', '').replace('+', 'p').replace('-', 'm'))
            m, y = A.load(jid); s = y[:, SR:]
            bp = sosfilt(butter(4, [20, 20000], 'bp', fs=SR, output='sos'), s, axis=-1)
            rms = np.sqrt(np.mean(bp ** 2)); aw = lfilter(b, a, s, axis=-1); rmsA = np.sqrt(np.mean(aw[:, SR // 2:] ** 2))
            sp = np.abs(np.fft.rfft(s[0] * np.hanning(s.shape[1]))) ** 2; fr = np.fft.rfftfreq(s.shape[1], 1 / SR)
            def band(lo, hi): return 10 * np.log10(np.mean(sp[(fr > lo) & (fr < hi)]) + 1e-40)
            hum = 10 * np.log10(max(sp[np.argmin(abs(fr - 50))], sp[np.argmin(abs(fr - 60))]) + 1e-40) - band(40, 70)
            corr = float(np.corrcoef(s[0], s[1])[0, 1]) if s.shape[0] == 2 and np.std(s[1]) > 0 else None
            rows.append({"pre": name, "gain": gname, "rms_dbfs_20_20k": round(A.db(rms), 1), "rms_dbfsA": round(A.db(rmsA), 1),
                         "slope_100_vs_10k_db": round(band(80, 125) - band(8000, 12500), 1), "hum_peak_over_band_db": round(hum, 1),
                         "lr_corr": None if corr is None else round(corr, 3), "peak_dbfs": round(A.db(np.abs(s).max()), 1)})
    wcsv(AN + "/pre_noise.csv", rows); return rows
def brec():
    rows = []
    for name in U.PRES:
        for k in ("1k", "40"):
            m, y = A.load("pbrec_%s_%s" % (k, name)); s = y[0]
            # windows of 50 ms on the 1 kHz probe; ref = 0.4-0.9 s; after burst ends at 1.5 s
            def win(t0, t1=None):
                a = int(t0 * SR); b = a + int(0.05 * SR) if t1 is None else int(t1 * SR); return A.harm(s[a:b], 1000.0, 6)
            ref = win(0.4, 0.9)
            for dt in (0.005, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 3.5):
                h = win(1.5 + dt)
                rows.append({"pre": name, "burst": k, "t_after_s": dt, "gain_dev_db": round(A.db(h["fund"] / ref["fund"]), 3),
                             "thd_pct": round(h["thd_pct"], 4), "thd_ref_pct": round(ref["thd_pct"], 4),
                             "h2_dbc": round(h["h_dbc"][0], 1), "h3_dbc": round(h["h_dbc"][1], 1)})
    wcsv(AN + "/pre_burst_recovery.csv", rows); return rows
def phase():
    rows = []
    x, inv, L = A.inv_ess(P1.ESS_T)
    for name in U.PRES:
        m, y = A.load("pess_%s_-30" % name)
        sc = S.db2a(P1.CLIP_IN[name] - 30)
        ir = A.deconv(y[0] / sc, inv); i0 = int(0.2 * SR) + len(x) - 1
        h = ir[i0 - 512:i0 + 8192].copy(); h[:256] *= np.hanning(512)[:256]
        H = np.fft.rfft(h, 1 << 16); f = np.fft.rfftfreq(1 << 16, 1 / SR)
        ph = np.unwrap(np.angle(H))
        # remove the 512-sample offset and any bulk delay (fit 1-5 kHz)
        sel = (f > 1000) & (f < 5000); slope = np.polyfit(2 * np.pi * f[sel], ph[sel], 1)[0]
        ex = ph - slope * 2 * np.pi * f; gd = -np.gradient(ph, 2 * np.pi * f) - 512 / SR
        r = {"pre": name, "bulk_delay_samples": round(-slope * SR - 512, 2)}
        for fb in (20, 30, 50, 100, 1000, 10000, 15000, 20000):
            i = np.argmin(abs(f - fb))
            r["mag_db_%d" % fb] = round(A.db(abs(H[i])) - A.db(abs(H[np.argmin(abs(f - 1000))])), 2)
            r["phase_deg_%d" % fb] = round(float(np.degrees(ex[i] - ex[np.argmin(abs(f - 1000))])), 1)
            r["gd_ms_%d" % fb] = round(float(np.median(gd[max(i - 3, 0):i + 4]) * 1000), 3)
        rows.append(r)
    wcsv(AN + "/pre_phase_gd.csv", rows); return rows
if __name__ == "__main__":
    for fn in (lf_stairs, imd, noise, brec, phase): fn(); print(fn.__name__, "ok")
