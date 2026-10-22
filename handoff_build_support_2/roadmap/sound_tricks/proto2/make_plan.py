"""Writes target_treated.json: auto-treat plan for the real default room, Makivirta target, model before/after."""
import sys, json, numpy as np
sys.path.insert(0, "/workspace/st_work/proto2"); sys.path.insert(0, "/workspace/st_work/proto")
from harness import *
import treatment as TR, rooms as R, surfdecay as SD
b = body(); p0 = A.params_from_body(dict(b)); W, H, L = p0["W"], p0["H"], p0["L"]; hum = float(p0["humidity"])
base = R.surfaces_for("real_default", p0["surfaces"])
s, plan, bef, aft, tgt = TR.auto_treat(W, H, L, base, hum, 0.8)
V = W * H * L
cov = {k: round(sum(t["coverage"] for t in s[k]["treatment"]), 3) for k in s}
band = lambda lo, hi: (TR.THIRD >= lo) & (TR.THIRD <= hi)
inb = int(np.sum(np.abs(aft / tgt - 1) <= 0.10))
out = dict(room=dict(W=W, H=H, L=L, V=V), f=TR.THIRD.tolist(), T=tgt.tolist(), before=bef.tolist(), after_model=aft.tolist(),
           plan=plan, coverage=cov, within10_of_24=inb, ebu_Tm=TR.ebu_tm(V),
           schroeder_before=TR.schroeder_hz(float(np.mean(bef[band(500, 2000)])), V), schroeder_after=TR.schroeder_hz(0.8, V),
           axial=[(round(m[0], 1), m[1]) for m in TR.modes(W, H, L, 300) if m[2] == "axial"])
json.dump(out, open("target_treated.json", "w"), indent=1, default=str)
for r in plan: print(r)
print("coverage", cov, "within10", inb, "/24", "EBU Tm", round(TR.ebu_tm(V), 3))
print("after/target", np.round(aft / tgt, 2))
