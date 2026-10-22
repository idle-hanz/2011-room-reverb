"""Export MEASURED binaural presets + per-rate SOS grid tables from the stage-1 cache.

Writes (new files only):
  presets/binaural/<id>.json                      mic_fitter.binaural_preset.v1 (both rates embedded)
  presets/binaural/sos_tables/<rate>/<id>.json    colour_sos_grid.v1, K = --kship (default 6)
  presets/binaural/sos_tables/<rate>/<id>.K3.json same, K = 3 (drop-in with today's 3-section budget)
  presets/binaural/index.json                     mic_fitter.binaural_index.v1
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from binaural_fitter.core import FGRID, EVAL_MASK
from binaural_fitter.datasets import DATASETS
from binaural_fitter.grid import GRIDS, grid_nodes, mirror_map
from binaural_fitter.sosfit import LAYOUTS, params_to_sos, sos_db, stability
from run_binaural_fit import C_ENGINE, RATES, hset, sym_targets

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "presets" / "binaural"
REP = ROOT / "reports"
COORDS = ("head-relative, SOFA convention: azimuth deg counter-clockwise from front (+90 = LEFT), "
          "elevation deg up (+90 = top). Engine mapping: see BINAURAL_MODE_BRIEF.md section 3.")


def f32_check(sos, tgt, fs):
    s32 = np.asarray(sos, dtype=np.float32).astype(np.float64)
    d = (sos_db(s32, FGRID, fs) - sos_db(sos, FGRID, fs))[EVAL_MASK]
    e = (sos_db(s32, FGRID, fs) - tgt)[EVAL_MASK]
    return float(np.max(np.abs(d))), float(np.max(np.abs(e))), stability(s32)[0]


def table(did, fs, gid, K, fits):
    nodes = grid_nodes(gid)
    mm = mirror_map(nodes)
    h = hset(did, fs)
    _, _, _, TL, TR, _, _ = sym_targets(h, nodes)
    F = fits[f"{did}|{fs}"]
    PL = [F[str(n)][str(K)] for n in range(len(nodes))]
    sosL = [params_to_sos(np.array(p), LAYOUTS[K], fs) for p in PL]
    worst = {"f32_vs_f64_max_db": 0.0, "f32_fit_max_db": 0.0, "f32_max_pole_radius": 0.0}
    for n, s in enumerate(sosL):
        a, b, c = f32_check(s, TL[n], fs)
        worst["f32_vs_f64_max_db"] = max(worst["f32_vs_f64_max_db"], a)
        worst["f32_fit_max_db"] = max(worst["f32_fit_max_db"], b)
        worst["f32_max_pole_radius"] = max(worst["f32_max_pole_radius"], c)
    return {
        "nodes": [[float(a), float(e)] for a, e in nodes],
        "mirror": mm,
        "params": {"L": PL, "R": [PL[mm[n]] for n in range(len(nodes))]},
        "sos": {"L": [s.tolist() for s in sosL], "R": [sosL[mm[n]].tolist() for n in range(len(nodes))]},
        "record_of": {"L": list(range(len(nodes))), "R": mm},
        "f32": worst,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", default="G60")
    ap.add_argument("--kship", type=int, default=6)
    args = ap.parse_args()
    gid, K = args.grid, args.kship
    fits = json.loads((REP / f"fits_{gid}.json").read_text())
    met = json.loads((REP / f"metrics_{gid}.json").read_text())
    (OUT / "sos_tables" / "44100").mkdir(parents=True, exist_ok=True)
    (OUT / "sos_tables" / "48000").mkdir(parents=True, exist_ok=True)
    index = {"schema": "mic_fitter.binaural_index.v1",
             "note": ("MEASURED dummy-head HRTF colour presets (separate from the 20 mic presets in ../index.json, "
                      "which are untouched). Per-ear min-phase RBJ SOS per head-relative grid node; ITD handled as "
                      "delay (geometry + Woodworth correction). Licences differ per preset: see licence fields."),
             "grid": gid, "K": K, "presets": []}
    for did, ds in DATASETS.items():
        itd = met["itd"][did]
        spacing = round(float(itd["ear_spacing_m_from_sofa"]), 4)
        lat = np.array(itd["table_lateral_deg"], dtype=float)
        tab = np.array(itd["table_itd_us"], dtype=float)
        tab = 0.5 * (tab - tab[::-1])  # antisymmetric: ITD(0) = 0, ITD(-t) = -ITD(t)
        itd_tab_us = [round(float(x), 2) for x in tab]
        corr_us = [round(float(x), 2) for x in tab - 1e6 * (spacing / C_ENGINE) * np.sin(np.radians(lat))]
        per_rate = {}
        for fs in RATES:
            tK = table(did, fs, gid, K, fits)
            t3 = table(did, fs, gid, 3, fits)
            m = met["fit"][did][str(fs)]
            for kk, tt, suffix in ((K, tK, ""), (3, t3, ".K3")):
                sos_file = {
                    "schema": "colour_sos_grid.v1",
                    "preset_id": did, "honesty": "MEASURED", "fit_fs": fs, "K": kk, "layout": LAYOUTS[kk],
                    "param_order": "per section: log2(f_hz), gain_db, log2(Q)  (RBJ, same as colour_sos_wtable.v1)",
                    "sos_row": "b0 b1 b2 a1 a2 (a0 = 1), TDF-II as live_stereo.c run_sos",
                    "coords": COORDS, "grid_id": gid, "lookup": "nearest node by great-circle angle (no interpolation)",
                    "mirror_symmetric": True,
                    "record_note": "R ear at node n uses the L record of node mirror[n]; a fixed bank of len(nodes) records serves both ears.",
                    "eq": "diffuse_field", "ear_spacing_m": spacing,
                    "nodes": tt["nodes"], "mirror": tt["mirror"], "params": tt["params"], "sos": tt["sos"],
                    "licence": ds["licence"], "source_doi": ds["doi"],
                    "float32_check": tt["f32"],
                }
                blob = json.dumps(sos_file, separators=(",", ":"))
                sos_file["table_hash"] = hashlib.sha1(blob.encode()).hexdigest()[:16]
                (OUT / "sos_tables" / str(fs) / f"{did}{suffix}.json").write_text(json.dumps(sos_file, separators=(",", ":")))
            per_rate[str(fs)] = {
                "sofa_file": Path(m["sofa"]).name, "native_rate": m["native_rate"],
                "sos_table": f"sos_tables/{fs}/{did}.json", "sos_table_K3": f"sos_tables/{fs}/{did}.K3.json",
                "params_L": tK["params"]["L"], "sos_L": tK["sos"]["L"],
                "metrics": {f"K{k}": {kk: v for kk, v in m["per_k"][str(k)].items() if not kk.startswith("per_node")}
                            for k in (3, 4, 5, 6)},
                "per_node_error_K": {"K": K, **{kk: v for kk, v in m["per_k"][str(K)].items() if kk.startswith("per_node")}},
                "asymmetry_rms_db_before_symmetrising": m["asymmetry_rms_db"],
                "float32_check": tK["f32"],
            }
        preset = {
            "schema": "mic_fitter.binaural_preset.v1",
            "preset_id": did, "display_name": ds["display_name"], "honesty": "MEASURED", "kind": "binaural_head",
            "head": ds["head"],
            "source": {k: ds.get(k) for k in ("dataset", "doi", "url", "paper_doi", "paper") if ds.get(k)},
            "licence": {"id": ds["licence"], "share_alike": ds["share_alike"], "notice": ds["notice"],
                        "note": ds.get("licence_note", ""), "file": ds["licence_file"],
                        "changes": ("Derived by the 2011 Room Reverb project: diffuse-field equalised, 1/6-octave smoothed, "
                                    "left/right mirror-averaged magnitude at grid nodes, fitted to RBJ biquads; ITD modelled "
                                    "(Woodworth fit). No raw HRIRs redistributed.")},
            "measurement": {"distance_m": float(np.unique(hset(did, 48000).sofa.r)[0]),
                            "n_directions": int(len(hset(did, 48000).sofa.az)),
                            "native_rates_hz": sorted(int(r) for r in ds["files"]),
                            "taps": int(hset(did, 48000).sofa.ir.shape[-1]),
                            "sofa_history": hset(did, 48000).sofa.attrs.get("History", ""),
                            "sofa_comment": hset(did, 48000).sofa.attrs.get("Comment", "")},
            "ear_spacing_m": spacing,
            "ear_spacing_source": "SOFA ReceiverPosition (|L - R|), VERIFIED from file",
            "coords": COORDS,
            "processing": {"eq": "diffuse_field (power average over the measured sphere, area-weighted, 1/3-oct smoothed, both ears)",
                           "smoothing": "1/6-octave power", "symmetrised": "L(n) := power mean of L(n) and R(mirror n); R(n) := L(mirror n)",
                           "fit_band_hz": [40, 20000], "metric_band_hz": [100, 16000],
                           "fit_weights": "1.0 in 100 Hz-16 kHz, 0.3 outside"},
            "grid": {"id": gid, "rings_el_azstep": GRIDS[gid], "n_nodes": len(grid_nodes(gid)),
                     "lookup": "nearest node by great-circle angle"},
            "colour": {"K": K, "layout": LAYOUTS[K], "rates": per_rate},
            "itd": {"model": "tabulated_lateral (default); woodworth_lateral (fallback)",
                    "lateral_angle": "theta_lat = asin(cos(el) * sin(az)), + = left (interaural-polar)",
                    "table_lateral_deg": itd["table_lateral_deg"],
                    "table_itd_us": itd_tab_us, "table_note": "median measured LF ITD per 5-degree lateral bin (|el| <= 60), antisymmetrised",
                    "correction_us": corr_us,
                    "correction_note": "D(theta) = table_itd - (ear_spacing_m / c_engine) * sin(theta) in us; linear interpolation in theta",
                    "k_us": itd["woodworth_k_us"], "a_eff_m_at_c343": itd["woodworth_a_eff_m_at_c343"],
                    "woodworth_formula": "ITD_target = k * (theta_lat + sin theta_lat)",
                    "engine_rule": ("per image, per tap build: D = correction(theta_lat); t_R += max(D, 0); t_L += max(-D, 0) "
                                    "(on top of each ear's own geometric path delay; contralateral ear only, so causal)"),
                    "c_engine_m_s": C_ENGINE,
                    **{k: v for k, v in itd.items() if not k.startswith(("_", "table")) and k not in ("woodworth_k_us", "woodworth_a_eff_m_at_c343")}},
            "ild": "carried by the per-ear magnitude tables (no separate ILD gain)",
            "notes": ("Binaural mode only. The capsule pattern gain is replaced by this colour (omni gain). "
                      "Not a capsule preset: do not list in the per-capsule mic preset dropdown."),
        }
        (OUT / f"{did}.json").write_text(json.dumps(preset, indent=1))
        k6 = per_rate["48000"]["metrics"][f"K{K}"]
        index["presets"].append({
            "preset_id": did, "display_name": ds["display_name"], "honesty": "MEASURED", "file": f"{did}.json",
            "licence": ds["licence"], "share_alike": ds["share_alike"], "ear_spacing_m": spacing,
            "node_fit_rms_db_median_48k": k6["node_fit_rms_db"]["median"], "node_fit_max_db_p95_48k": k6["node_fit_max_db"]["p95"],
            "holdout_rms_db_median_48k": k6["holdout_total_rms_db"]["median"],
        })
        print(did, "f32", per_rate["44100"]["float32_check"], per_rate["48000"]["float32_check"])
    index["default_preset"] = "SADIE2_KU100"
    (OUT / "index.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
