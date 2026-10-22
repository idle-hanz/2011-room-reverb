"""Analysis for SURFACES IN THE LOOP renders: octave T30/EDT, 1/3-octave T30 (treated rooms), L/R tail tone."""
import sys, json, glob, math, numpy as np
sys.path.insert(0, "/workspace/st_work/proto")
import ana
from scipy import signal
SR = 48000
THIRD = 1000.0 * 2.0 ** (np.arange(-13, 10) / 3.0)   # 50 Hz .. 8 kHz
def third(x, fc):
    sos = signal.butter(3, [fc / 2 ** (1 / 6), min(fc * 2 ** (1 / 6), 0.45 * SR)], btype="band", fs=SR, output="sos")
    return signal.sosfiltfilt(sos, x)
def t30_third(m):
    n0 = ana.onset(m); out = []
    for fc in THIRD:
        e = ana.edc_db(third(m, fc)[n0:]); out.append(ana.t_fit(e, -5, -25))   # T20 (BRAS / EBU practice for short rooms)
    return out
def lr_tone(ir, t0=0.08, t1=0.5):
    a, b = int(t0 * SR), int(t1 * SR); out = []
    for fc in ana.OCT:
        l = ana.octave(ir[:, 0], fc)[a:b]; r = ana.octave(ir[:, 1], fc)[a:b]
        out.append(10 * math.log10(np.sum(l ** 2) / max(np.sum(r ** 2), 1e-30)))
    return out
res = {}
names = sys.argv[1:] or [f[3:-4] for f in sorted(glob.glob("ir_*.npy"))]
for nm in names:
    ir = np.load(f"ir_{nm}.npy") if nm != "A_default_flat" else np.load("/workspace/st_work/proto/ir_ortf_noC.npy")
    m = ir.sum(1); pr = ana.params(m)
    meta = {}
    try: meta = json.load(open(f"meta_{nm}.json"))
    except Exception: pass
    d = dict(T30=[pr[f]["T30"] for f in ana.OCT], T20=[pr[f]["T20"] for f in ana.OCT], EDT=[pr[f]["EDT"] for f in ana.OCT],
             C50_1k=pr[1000]["C50"], target=meta.get("target_T_oct"), lr_tail_db=lr_tone(ir), len_s=len(ir) / SR,
             peak=float(np.max(np.abs(ir))), finite=bool(np.all(np.isfinite(ir))))
    d["curv_EDT_over_T30"] = [e / t if t and t == t else None for e, t in zip(d["EDT"], d["T30"])]
    if meta.get("target_T_oct"):
        d["err_pct"] = [100 * (a / b - 1) for a, b in zip(d["T30"], meta["target_T_oct"])]
    if nm.startswith("g5") or nm.startswith("cr2"):
        d["T20_third"] = t30_third(m)
    res[nm] = d
    print(nm, "T30", np.round(d["T30"], 2), "err%", np.round(d.get("err_pct", []), 1), "EDT/T30", np.round([x or 0 for x in d["curv_EDT_over_T30"]], 2), "L-R", np.round(d["lr_tail_db"], 1))
json.dump(res, open("a2_results.json", "w"), indent=1, default=float)
