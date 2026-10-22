#!/usr/bin/env python3
"""Fit all source presets. Usage: python run_fit.py [--quick] [--only id1 id2]"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from source_fitter import data_io as io, fit as F, model as M, plot as P  # noqa: E402

OUT_P = os.path.join(HERE, "presets")
OUT_PL = os.path.join(HERE, "plots")
B = io.DATA + "/byu/"

BYU_SPEECH = ("Average Speech Directivity", "S. D. Bellows, C. M. Pincock, J. K. Whiting, T. W. Leishman, 'Average Speech Directivity', BYU ScholarsArchive Directivity 1 (2019); T. W. Leishman et al., JASA 149(3) 1507-1523 (2021) doi:10.1121/10.0003363",
              "https://scholarsarchive.byu.edu/directivity/1/")
BYU_AMPS = ("Guitar Amplifier Directivity", "R. C. Edelman, B. E. Anderson, S. D. Bellows, T. W. Leishman, 'Guitar Amplifier Directivity', BYU ScholarsArchive (2026)",
            "https://scholarsarchive.byu.edu/directivity/19/")
BYU_TPT = ("Trumpet Directivity", "S. D. Bellows, K. J. Bodon, T. W. Leishman, 'Trumpet Directivity', BYU ScholarsArchive Directivity 13 (2020)",
           "https://scholarsarchive.byu.edu/directivity/13/")
BYU_VLN = ("Violin Directivity", "S. D. Bellows, K. J. Bodon, T. W. Leishman, 'Violin Directivity', BYU ScholarsArchive Directivity 15 (2020)",
           "https://scholarsarchive.byu.edu/directivity/15/")

# id, label, category, loader-spec, fixed params
CATALOG = [
    ("talking_head", "Talking head (average speech, 6 talkers)", "voice",
     ("byu", B + "SpeechDirectivity.csv", BYU_SPEECH, {"note": "median-plane symmetrised by authors (VERIFIED); seated talker incl. chair/torso"}), {"aim_az": 0.0, "b_lr": 0.0}),
    ("singer_soprano", "Singer (soprano, TU Berlin)", "voice", ("tu", "Soprano_m"), {}),
    ("acoustic_guitar", "Acoustic guitar (steel/modern, TU Berlin)", "strings", ("tu", "Acoustic_guitar_modern"), {}),
    ("trumpet", "Trumpet (Bach 239, TU Berlin)", "brass", ("tu", "Trumpet_modern"), {}),
    ("trumpet_byu", "Trumpet (BYU, 160-3150 Hz)", "brass", ("byu", B + "Trumpet.csv", BYU_TPT, {}), {}),
    ("violin", "Violin (modern, TU Berlin)", "strings", ("tu", "Violin_modern"), {}),
    ("violin_byu", "Violin (BYU, 200-2500 Hz)", "strings", ("byu", B + "Violin.csv", BYU_VLN, {}), {}),
    ("cello", "Cello (modern, TU Berlin)", "strings", ("tu", "Cello_modern"), {}),
    ("combo_1x12", "Guitar combo 1x12 open-back (Fender Deluxe Reverb)", "guitar_amp",
     ("byu", B + "amps/Fender Deluxe Reveb.csv", BYU_AMPS, {"speaker_complement": "1x12 open-back (manufacturer spec; ASSUMED, not in dataset)"}), {}),
    ("combo_1x12_bluesjr", "Guitar combo 1x12 (Fender Blues Junior)", "guitar_amp",
     ("byu", B + "amps/Fender Blues Junior.csv", BYU_AMPS, {"speaker_complement": "1x12 open-back (ASSUMED)"}), {}),
    ("combo_1x12_bluesdlx", "Guitar combo 1x12 (Fender Blues Deluxe)", "guitar_amp",
     ("byu", B + "amps/Fender Blues Deluxe.csv", BYU_AMPS, {"speaker_complement": "1x12 open-back (ASSUMED)"}), {}),
    ("combo_1x10", "Guitar combo 1x10 (Fender Princeton Reverb)", "guitar_amp",
     ("byu", B + "amps/Fender Princeton Reverb.csv", BYU_AMPS, {"speaker_complement": "1x10 open-back (ASSUMED)"}), {}),
    ("combo_2x12", "Guitar combo 2x12 (Fender Twin Reverb)", "guitar_amp",
     ("byu", B + "amps/Fender Twin Reverb.csv", BYU_AMPS, {"speaker_complement": "2x12 open-back (ASSUMED)"}), {}),
    ("combo_2x12_ac30", "Guitar combo 2x12 (Vox AC30)", "guitar_amp",
     ("byu", B + "amps/Vox AC30.csv", BYU_AMPS, {"speaker_complement": "2x12 open-back (ASSUMED)"}), {}),
]
# the rest of TU Berlin instruments as a library (tu_<name>)
for n in sorted(io.TU_FORWARD_MIC):
    if n in ("Soprano_m", "Acoustic_guitar_modern", "Trumpet_modern", "Violin_modern", "Cello_modern"):
        continue
    CATALOG.append(("tu_" + n.lower(), n.replace("_", " ") + " (TU Berlin)", "library_tu", ("tu", n), {}))


def load(spec):
    if spec[0] == "tu":
        return io.load_tu(spec[1])
    _, path, (title, cite, url), extra = spec
    return io.load_byu(path, os.path.basename(path), io.byu_prov(title, cite, url, extra), stride=2)


def a_eq(f0):
    return 340.0 / (2 * math.pi * f0)


def job(item, maxiter):
    pid, label, cat, spec, fixed = item
    t = time.time()
    ds = load(spec)
    best = None
    for order in (1, 2):   # discrete choice: soft beaming LP order (fit both, keep lower train RMSE)
        fx = dict(fixed); fx["lp_order"] = float(order)
        r = F.fit_dataset(ds, maxiter=maxiter, fixed=fx)
        if best is None or r["rmse_train_db"] < best["rmse_train_db"]:
            best = r
    res = best
    p = res["params"]
    diff = F.fit_diffuse_filter(p)
    preset = make_preset(pid, label, cat, p, res, diff, ds.provenance, "MEASURED-FIT")
    json.dump(preset, open(os.path.join(OUT_P, pid + ".json"), "w"), indent=2)
    if cat != "library_tu" or pid in ("tu_alto_saxophone_modern", "tu_french_horn_modern", "tu_tenor_trombone_modern", "tu_transverse_flute_modern"):
        P.polar(pid, p, ds, os.path.join(OUT_PL, "polars", pid + ".png"), label)
        P.balloon(pid, p, os.path.join(OUT_PL, "balloons", pid + ".png"), title=label)
        P.di_plot(pid, p, res, diff, os.path.join(OUT_PL, "di", pid + ".png"))
    return pid, res["rmse_train_db"], res["rmse_holdout_db"], time.time() - t


def make_preset(pid, label, cat, p, res, diff, prov, tag):
    f = np.array([125, 250, 500, 1000, 2000, 4000, 8000, 16000], float)
    di = M.directivity_index_db(p, f)
    return {
        "schema": M.PRESET_SCHEMA, "id": pid, "label": label, "category": cat, "tag": tag,
        "model": M.MODEL_NAME, "level_reference": "on_axis (0 dB when facing the receiver; omni = exact null)",
        "frame": {"x": "facing (radiation reference axis of the dataset)", "y": "source left", "z": "up",
                  "facing_definition": prov.get("front_axis") or prov.get("forward_axis", "")},
        "params": {k: round(float(v), 5) for k, v in p.items()},
        "size": {"a_eq_m": round(a_eq(p["f0"]), 4), "beaming_onset_hz": round(p["f0"], 1),
                 "rule": "a_eq = c/(2*pi*f0), c=340 m/s as engine (piston ka=1); UI size slider sets size_scale = a_user/a_eq -> f0, lp_hz divided by size_scale"},
        "di_db": {f"{fi:g}": round(float(v), 2) for fi, v in zip(f, di)},
        "diffuse_inject": diff,
        "fit": {k: v for k, v in res.items() if k not in ("params",)},
        "dsp": {"stages": ["broadband_gain(k_lo*lo_db)", "rbj_high_shelf(f0, k*hi_db, shelf_s)", "soft_beaming_lp(lp_hz/k_hi, lp_mix, lp_order 1|2 cascaded one-poles)"],
                "fs_ref_hz": 48000, "k": "k_hi = A*u^p*(1-q*u^8); k_lo = A*((1-dip)*u^p_lo*(1-q*u^8) + dip*4u(1-u)); both 0 on axis",
                "slot": "FIRST stage of each image's serial cascade (before surfaces/air/mic)"},
        "provenance": prov,
        "tags": {"params": "VERIFIED fit output (this code) of MEASURED data" if tag.startswith("MEASURED") else "ASSUMED design values",
                 "model_form": "ASSUMED (engineering model, mirrors mic_fitter v3)",
                 "size_rule": "VERIFIED physics (piston ka=1) applied as ASSUMED mapping"},
    }


def assumed_presets(maxiter):
    """omni (exact null) + ASSUMED derived presets. Never tagged MEASURED."""
    out = []
    om = M.omni_params()
    diff = F.fit_diffuse_filter(om)
    pr = make_preset("omni", "Omni (current engine sound — null)", "reference", om,
                     {"note": "analytic; relative response identically 0 dB"}, diff,
                     {"dataset": "none (analytic)", "measurement": "n/a"}, "ASSUMED-EXACT")
    pr["tags"]["params"] = "VERIFIED analytic null (k*0 = 0 dB everywhere)"
    json.dump(pr, open(os.path.join(OUT_P, "omni.json"), "w"), indent=2)
    out.append(("omni", 0.0, 0.0))
    base_path = os.path.join(OUT_P, "combo_1x12.json")
    if os.path.exists(base_path):
        base = json.load(open(base_path))["params"]
        # closed-back 1x12: kill rear dipole lobe (q=0), LF near-omni (lo_db >= -1): ASSUMED
        c1 = dict(base); c1["q"] = 0.0; c1["lo_db"] = max(base["lo_db"], -1.0)
        # 4x12 closed: 2x2 array of 12" -> effective radius ~2x -> f0/2, lp_hz/2 (ASSUMED array rule)
        c4 = dict(c1); c4["f0"] = base["f0"] / 2.0; c4["lp_hz"] = max(150.0, base["lp_hz"] / 2.0)
        for pid, lab, p, why in (
            ("cab_1x12_closed", "Guitar cab 1x12 closed-back (ASSUMED, derived)", c1,
             "derived from combo_1x12 MEASURED fit: q->0 (no open-back rear lobe), lo_db>=-1 (closed box ~omni at LF)"),
            ("cab_4x12_closed", "Guitar cab 4x12 closed-back (ASSUMED, derived)", c4,
             "derived from cab_1x12_closed: 2x2 array of 12in drivers -> effective radius ~2x -> f0, lp_hz halved (piston/array scaling)")):
            d = F.fit_diffuse_filter(p)
            pr = make_preset(pid, lab, "guitar_amp", p, {"note": "no measured data found for this cabinet type"}, d,
                             {"dataset": "none — derived", "derived_from": "combo_1x12 (BYU Fender Deluxe Reverb fit)", "rule": why,
                              "measurement": "ASSUMED (no open 4x12 / closed 1x12 spherical dataset found; DirPat cab data rejected, see report)"},
                             "ASSUMED")
            json.dump(pr, open(os.path.join(OUT_P, pid + ".json"), "w"), indent=2)
            P.polar(pid, p, None, os.path.join(OUT_PL, "polars", pid + ".png"), lab + " — no data dots (ASSUMED)")
            P.balloon(pid, p, os.path.join(OUT_PL, "balloons", pid + ".png"), title="ASSUMED")
            P.di_plot(pid, p, None, d, os.path.join(OUT_PL, "di", pid + ".png"))
            out.append((pid, float("nan"), float("nan")))
    # piano: no open spherical dataset found -> ASSUMED placeholder (qualitative: lid-open grand radiates up/out the lid side)
    pp = dict(M.omni_params()); pp.update(lo_db=-1.5, hi_db=-9.0, f0=900.0, shelf_s=0.5, p=1.0, aim_el=25.0, b_ud=0.0,
                                         aim_az=-20.0, lp_hz=24000.0, lp_mix=0.0)
    d = F.fit_diffuse_filter(pp)
    pr = make_preset("piano_grand_lid_open", "Grand piano, lid open (ASSUMED placeholder)", "keys", pp,
                     {"note": "no open measured spherical piano directivity found"}, d,
                     {"dataset": "none", "basis": "qualitative only: lid-open grand radiates mainly upward/out of the open lid side (Meyer, Acoustics and the Performance of Music, Springer 2009, doi:10.1007/978-0-387-09517-2) — NO numbers taken",
                      "measurement": "ASSUMED"}, "ASSUMED")
    json.dump(pr, open(os.path.join(OUT_P, "piano_grand_lid_open.json"), "w"), indent=2)
    P.polar("piano_grand_lid_open", pp, None, os.path.join(OUT_PL, "polars", "piano_grand_lid_open.png"), "ASSUMED placeholder")
    P.balloon("piano_grand_lid_open", pp, os.path.join(OUT_PL, "balloons", "piano_grand_lid_open.png"), title="ASSUMED")
    out.append(("piano_grand_lid_open", float("nan"), float("nan")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--assumed-only", action="store_true", help="only rebuild omni + ASSUMED presets and the index")
    a = ap.parse_args()
    for d in (OUT_P, OUT_PL + "/polars", OUT_PL + "/balloons", OUT_PL + "/di"):
        os.makedirs(d, exist_ok=True)
    maxiter = 40 if a.quick else 110
    items = [c for c in CATALOG if not a.only or c[0] in a.only]
    if a.assumed_only:
        rows = []
    else:
        with Pool(a.procs) as pool:
            rows = pool.starmap(job, [(it, maxiter) for it in items])
    rows = [(r[0], r[1], r[2]) for r in rows] + assumed_presets(maxiter)
    idx = []
    for f in sorted(os.listdir(OUT_P)):
        if f.endswith(".json") and f != "index.json":
            j = json.load(open(os.path.join(OUT_P, f)))
            idx.append({"id": j["id"], "label": j["label"], "category": j["category"], "tag": j["tag"],
                        "rmse_train_db": j["fit"].get("rmse_train_db"), "rmse_holdout_db": j["fit"].get("rmse_holdout_db"),
                        "fit_bands_hz": j["fit"].get("fit_bands_hz"), "a_eq_m": j["size"]["a_eq_m"],
                        "di_1k_db": j["di_db"]["1000"], "di_4k_db": j["di_db"]["4000"],
                        "dataset": j["provenance"].get("dataset", "")})
    json.dump({"schema": "source_fitter.index.v1", "presets": idx}, open(os.path.join(OUT_P, "index.json"), "w"), indent=2)
    for r in rows:
        print("%-40s train %.2f  hold %.2f" % r)


if __name__ == "__main__":
    main()
