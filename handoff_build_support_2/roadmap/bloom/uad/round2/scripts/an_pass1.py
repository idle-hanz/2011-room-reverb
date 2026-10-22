import json, os, sys, csv, glob, numpy as np
import anlib as A, pass1 as P1, units as U, siglib as S
SR = 48000; OUT = A.OUT; AN = "/workspace/uad2/an"; os.makedirs(AN, exist_ok=True)
I = None
def steps_of(job_id, f0, levels, channel=0):
    m, y = A.load(job_id)
    segs = A.stair_segments(y, m["keep"])
    rows = []
    for L, s in zip(levels, segs):
        h = A.harm(s[channel], f0)
        rows.append((L, h))
    return m, rows

def comp_stairs():
    out = []
    for name, (pl, pr, st, role) in U.COMP.items():
        for f in (1000, 100, 5000):
            jid = ("c1k_%s" % name) if f == 1000 else ("c%d_%s" % (f, name))
            if not os.path.exists(os.path.join(OUT, jid + ".json")): continue
            m, rows = steps_of(jid, float(f), P1.LV)
            g = [A.db(h["fund"]) - L for L, h in rows]
            g0 = float(np.median(g[:3]))
            for (L, h), gg in zip(rows, g):
                hd = h["h_dbc"] + [np.nan] * (9 - len(h["h_dbc"]))
                out.append({"setting": name, "role": role, "freq": f, "in_dbfs": L, "out_dbfs": round(A.db(h["fund"]), 3),
                            "small_sig_gain_db": round(g0, 3), "gr_db": round(g0 - gg, 3), "thd_pct": h["thd_pct"], "thdn_pct": h["thdn_pct"],
                            **{"h%d_dbc" % (k + 2): (round(v, 2) if v == v else "") for k, v in enumerate(hd)}, "params": json.dumps(pr)})
    return out

def comp_imd():
    out = []
    for name, (pl, pr, st, role) in U.COMP.items():
        for k in ("smpte", "ccif"):
            jid = "c%s_%s" % (k, name)
            if not os.path.exists(os.path.join(OUT, jid + ".json")): continue
            m, y = A.load(jid); segs = A.stair_segments(y, m["keep"])
            res = [(L, (A.imd_smpte if k == "smpte" else A.imd_ccif)(s[0])) for L, s in zip(P1.LV, segs)]
            ref = "a60" if k == "smpte" else "a19"
            a1 = 0.8 if k == "smpte" else 0.5
            g = [A.db(r[ref] / (S.db2a(L) * a1)) for L, r in res]; g0 = float(np.median(g[:3]))
            for (L, r), gg in zip(res, g):
                row = {"setting": name, "role": role, "test": k, "in_peak_dbfs": L, "gr_db": round(g0 - gg, 3), "imd_pct": r["imd_pct"]}
                row.update({kk: round(vv, 2) for kk, vv in r.items() if kk.endswith("dbc")})
                out.append(row)
    return out

def comp_fr():
    """FR at GR from (tone+sweep) - (tone) difference, deconvolved."""
    sw, _ = S.ess(1.0, 20.0, 20000.0, 0.005)
    t = np.arange(len(sw)) / SR; L = 1.0 / np.log(1000.0)
    inv = sw[::-1] * np.exp(-t / L)
    X = np.fft.rfft(sw, 4 * len(sw)); IV = np.fft.rfft(inv, 4 * len(sw)); fr = np.fft.rfftfreq(4 * len(sw), 1 / SR)
    kk = 1 / np.median(np.abs(X * IV)[(fr > 200) & (fr < 10000)]); inv *= kk
    bands = [20, 31.5, 50, 100, 200, 500, 2000, 5000, 10000, 15000, 18000, 20000]
    out = []
    for name, (pl, pr, st, role) in U.COMP.items():
        if role != "P": continue
        a = "cfrsw_" + name; b = "cfrtone_" + name
        if not (os.path.exists(os.path.join(OUT, a + ".json")) and os.path.exists(os.path.join(OUT, b + ".json"))): continue
        ma, ya = A.load(a); mb, yb = A.load(b)
        sa = A.stair_segments(ya, ma["keep"]); sb = A.stair_segments(yb, mb["keep"])
        base = None
        for Lv, s1, s2 in zip(P1.LVF, sa, sb):
            d = (s1[0] - s2[0]) / S.db2a(Lv - 30.0)
            ir = A.deconv(d, inv)
            i0 = len(sw) - 1; h = ir[i0 - 256:i0 + 4096] * np.r_[np.hanning(512)[:256], np.ones(4096 - 512 + 256), np.hanning(512)[256:]]
            H = np.fft.rfft(h, 1 << 15); f = np.fft.rfftfreq(1 << 15, 1 / SR)
            mag = A.db(H)
            # tone level-based GR (tone-only run)
            h1 = A.harm(s2[0][-int(0.3 * SR) // 100 * 100:], 1000.0)
            row = {"setting": name, "in_dbfs": Lv, "out_tone_dbfs": round(A.db(h1["fund"]), 2)}
            ref = np.mean(mag[(f > 300) & (f < 600)] ) * 0.5 + np.mean(mag[(f > 1800) & (f < 3000)]) * 0.5
            for bb in bands:
                sel = (f > bb / 2 ** (1 / 6)) & (f < bb * 2 ** (1 / 6))
                row["fr_%g" % bb] = round(float(np.mean(mag[sel]) - ref), 2)
            row["near1k_dip_db"] = round(float(np.min(mag[(f > 700) & (f < 1400)]) - ref), 2)
            out.append(row)
    return out

def wcsv(path, rows):
    if not rows: return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, keys); w.writeheader(); [w.writerow(r) for r in rows]

if __name__ == "__main__":
    what = sys.argv[1:] or ["stairs", "imd", "fr"]
    if "stairs" in what: wcsv(AN + "/comp_colour_steps.csv", comp_stairs())
    if "imd" in what: wcsv(AN + "/comp_imd_steps.csv", comp_imd())
    if "fr" in what: wcsv(AN + "/comp_fr_vs_gr.csv", comp_fr())
    print("done")
