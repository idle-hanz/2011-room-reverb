"""Render one SURFACES-IN-LOOP variant. usage: run2.py <variant>"""
import sys, json, time, copy, math, os
sys.path.insert(0, "/workspace/st_work/proto2"); sys.path.insert(0, "/workspace/st_work/proto")
import numpy as np
from harness import *
import fdn as F, attfilt as AF, surfdecay as SD, rooms as R, treatment as TR
sys.path.insert(0, "/workspace/build_support/research/room_validation")
NOC = {"mic_gain_c": 0.0, "mic_gain_l": 1.0, "mic_gain_r": 1.0}
v = sys.argv[1]
CAL = v.endswith("_cal")
if CAL:
    v0 = v[:-4]
vb = v[:-4] if CAL else v
RAW = vb.endswith("_raw")          # directional with the raw scattering share (no S_MIN floor)
if RAW:
    vb = vb[:-4]; SD.S_MIN = 0.0
b = body(**NOC); p0 = A.params_from_body(dict(b))
W, H, L = p0["W"], p0["H"], p0["L"]; hum = float(p0["humidity"])

def cards_for_body(surf):
    out = {}
    for k, c in surf.items():
        cc = {kk: vv for kk, vv in c.items() if kk not in ("treatment", "absorb_fn", "material")}
        if c.get("treatment"):
            cc["absorb"] = [round(float(x), 4) for x in TR.alpha_fn(c)(np.asarray(c["absorb_hz"], float))]
        out[k] = cc
    return out

def fn_cards(surf):
    return {k: dict(c, absorb_fn=TR.alpha_fn(c)) if c.get("treatment") else c for k, c in surf.items()}

spec = dict(
  g3_avg=("real_default", "avg", 1.8), g3_dir=("real_default", "dir", 1.8),
  g4_studio_flat=("studio_panelled", "flat", None), g4_studio_avg=("studio_panelled", "avg", None), g4_studio_dir=("studio_panelled", "dir", None),
  g4_brick_flat=("bare_brick_plaster", "flat", None), g4_brick_avg=("bare_brick_plaster", "avg", None), g4_brick_dir=("bare_brick_plaster", "dir", None),
  g5_untreated=("real_default", "dir", None), g5_broadband=("treat_bb", "dir", None), g5_treated=("treat_full", "dir", None),
  g3_dir_shell=("real_shell", "dir", 1.8),
  cr2_avg=("cr2", "avg", None), cr2_dir=("cr2", "dir", None), cr2_flat=("cr2", "flat", None),
)[vb]
setname, mode, anchor = spec
peaks = "fold"
if setname == "cr2":
    import scene as SCN
    b = SCN.body(1, 1, 1.8); W, H, L = SCN.W, SCN.H, SCN.L
    surf = SCN.surfaces(False)
    for k in surf: surf[k]["absorb_hz"] = list(SD.BANDS)
    import bras_cr2 as BR
    hum_rh = BR.HUMIDITY_PCT
    b["surfaces"] = {k: dict(c) for k, c in surf.items()}
    hum = float(b.get("humidity", 0.35))
    fsurf = surf
elif setname == "real_shell":
    # ASSUMED 'room shell': doors, windows and lightweight wall areas (30 % of each wall) act as a broad
    # membrane near 90 Hz. Real rooms always have some; textbook solid plaster alone gives no LF loss.
    s = R.surfaces_for("real_default", p0["surfaces"])
    for k in "ABCD":
        s[k]["treatment"] = [dict(type="membrane", f0=90.0, q=1.0, amax=0.35, coverage=0.3, build="room shell (doors, glazing, stud walls)")]
    fsurf = fn_cards(s); b["surfaces"] = cards_for_body(s)
elif setname.startswith("treat"):
    base = R.surfaces_for("real_default", p0["surfaces"])
    s, plan, bef, aft, tgt = TR.auto_treat(W, H, L, base, hum, 0.8)
    if setname == "treat_bb":
        for k in s: s[k]["treatment"] = [t for t in s[k].get("treatment", []) if t["type"] == "porous"]
    fsurf = fn_cards(s); b["surfaces"] = cards_for_body(s); peaks = "replace"
    json.dump(plan, open(f"plan_{v}.json", "w"), indent=1, default=str)
else:
    s = R.surfaces_for(setname, p0["surfaces"]); fsurf = s; b["surfaces"] = cards_for_body(s)
    if setname == "real_default" and v.startswith("g5"): peaks = "replace"
fm = np.array([500.0, 1000.0])
Tmid = float(np.mean(SD.room_target(W, H, L, fsurf, hum, fm)))
b["decay_lock"] = True; b["decay_s"] = float(anchor or Tmid)
corr = np.ones(len(AF.OCT))
if CAL:
    # one Render-side calibration pass (like EQ_PLAN detection): measure T per octave on the first render,
    # scale each band's loss by T20_measured / T_target (T20: the -5..-25 dB slope EBU/BS.1116 practice uses), redesign. Only the overall T(f) moves; the
    # per-line (directional) spread is kept.
    import ana
    m0 = json.load(open(f"meta_{v0}.json")); ir0 = np.load(f"ir_{v0}.npy").sum(1); pr = ana.params(ir0)
    corr = np.clip(np.array([pr[f]["T20"] for f in ana.OCT]) / np.array(m0["target_T_oct"]), 0.6, 1.6)
cfn = lambda ff: np.interp(np.log(ff), np.log(AF.OCT), corr)
if mode != "flat":
    F.SURF_LOOP = {"struct": "S1P2", "peaks": peaks, "report": [],
                   "rates_for": lambda d, sr: SD.line_rates(d, sr, W, H, L, fsurf, hum, AF.FIT_F, mode == "dir", t_anchor=anchor)[0] * cfn(AF.FIT_F)[None, :]}
t = time.time(); ir, info, _ = render_ir(b); np.save(f"ir_{v}.npy", ir)
Tt = SD.room_target(W, H, L, fsurf, hum, AF.OCT)
if anchor: Tt = Tt * anchor / Tmid
meta = dict(variant=v, set=setname, mode=mode, decay_s=b["decay_s"], target_T_oct=Tt.round(3).tolist(),
            secs=round(time.time() - t, 1), report=(F.SURF_LOOP or {}).get("report", []), guard=(F.SURF_LOOP or {}).get("guard", []), stab=(F.SURF_LOOP or {}).get("stab", []), peaks=peaks, calib=corr.round(3).tolist())
json.dump(meta, open(f"meta_{v}.json", "w"), indent=1)
print(json.dumps(meta)[:900], flush=True)
