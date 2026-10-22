"""Fit MEASURED binaural presets. Usage: python run_binaural_fit.py [--grid G50] [--kship 5]

Stage 1 (cached): per dataset x rate x grid node, fit K = 3..6 biquads to the
symmetrised, diffuse-field-equalised, 1/6-oct smoothed left-ear magnitude.
Stage 2: metrics (node fit, hold-out incl. grid quantisation, symmetrisation), ITD, ILD.
Stage 3: export presets/binaural/*.json + sos_tables + reports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from binaural_fitter.core import FGRID, EVAL_MASK, HrtfSet, load_sofa, nearest_index
from binaural_fitter.datasets import DATASETS
from binaural_fitter.grid import GRIDS, grid_nodes, lateral_angle, mirror_map, nearest_node
from binaural_fitter.itd import correction_s, fit_woodworth, geometric_itd, measured_itd, woodworth
from binaural_fitter.sosfit import LAYOUTS, errors_db, fit_ear, params_to_sos, sos_db, stability

ROOT = Path(__file__).resolve().parent
REP = ROOT / "reports"
OUT = ROOT / "presets" / "binaural"
RATES = (44100, 48000)
KS = (3, 4, 5, 6)
C_ENGINE = 340.0  # engine SPEED_OF_SOUND_M_S (p5 early_field.py, VERIFIED)
C_MEAS = 343.0    # for reporting a_eff only

_H = {}


def hset(did, fs):
    key = (did, fs)
    if key not in _H:
        files = DATASETS[did]["files"]
        path = files.get(fs) or files[48000]
        _H[key] = HrtfSet(load_sofa(path))
    return _H[key]


def sym_targets(h: HrtfSet, nodes):
    az = [n[0] for n in nodes]
    el = [n[1] for n in nodes]
    idx, ang = nearest_index(h.sofa, az, el)
    raw = h.mag_db(idx)  # (G, 2, F)
    mm = mirror_map(nodes)
    pl = 10 ** (raw[:, 0] / 10)
    pr_m = 10 ** (raw[mm, 1] / 10)
    TL = 10 * np.log10(0.5 * (pl + pr_m))
    TR = TL[mm]
    asym = raw[:, 0] - raw[mm, 1]
    return idx, ang, raw, TL, TR, mm, asym


def _fit_task(args):
    did, fs, gid, n, tgt = args
    r = fit_ear(np.asarray(tgt), fs, Kmax=max(KS), Kmin=min(KS))
    return (did, fs, gid, n, {K: r[K][0].tolist() for K in r})


def stage1(gid, datasets):
    cache = REP / f"fits_{gid}.json"
    have = json.loads(cache.read_text()) if cache.exists() else {}
    tasks = []
    nodes = grid_nodes(gid)
    for did in datasets:
        for fs in RATES:
            key = f"{did}|{fs}"
            if key in have and len(have[key]) == len(nodes):
                continue
            h = hset(did, fs)
            _, _, _, TL, _, _, _ = sym_targets(h, nodes)
            for n in range(len(nodes)):
                tasks.append((did, fs, gid, n, TL[n].tolist()))
    if tasks:
        t0 = time.time()
        with Pool(8) as p:
            for did, fs, g, n, res in p.imap_unordered(_fit_task, tasks, chunksize=2):
                have.setdefault(f"{did}|{fs}", {})[str(n)] = res
        print(f"stage1: {len(tasks)} fits in {time.time() - t0:.0f} s")
        cache.write_text(json.dumps(have))
    return have


def holdout_dirs(h: HrtfSet, nodes, step=5.0):
    az, el = [], []
    for e in (-60, -45, -30, -15, 0, 15, 30, 45, 60):
        for a in np.arange(-180 + step, 180.01, step):
            az.append(a)
            el.append(e)
    idx, ang = nearest_index(h.sofa, az, el)
    idx = np.unique(idx)
    nn, nang = nearest_node(nodes, h.sofa.az[idx], h.sofa.el[idx])
    keep = nang > 2.5  # exclude directions sitting on a node
    return idx[keep], nn[keep], nang[keep]


def stats(a):
    a = np.asarray(a)
    return {"median": float(np.median(a)), "p95": float(np.percentile(a, 95)), "max": float(np.max(a)), "mean": float(np.mean(a))}


def band_levels(db, bands=(500, 1000, 2000, 4000, 8000)):
    out = []
    for fc in bands:
        m = (FGRID >= fc / 2 ** 0.5) & (FGRID < fc * 2 ** 0.5)
        out.append(10 * np.log10(np.mean(10 ** (db[..., m] / 10), axis=-1)))
    return np.stack(out, axis=-1)


def stage2(gid, fits, datasets):
    nodes = grid_nodes(gid)
    res = {}
    for did in datasets:
        res[did] = {}
        for fs in RATES:
            h = hset(did, fs)
            idx, ang, raw, TL, TR, mm, asym = sym_targets(h, nodes)
            F = fits[f"{did}|{fs}"]
            per_k = {}
            for K in KS:
                layout = LAYOUTS[K]
                sosL = [params_to_sos(np.array(F[str(n)][str(K)] if str(K) in F[str(n)] else F[str(n)][K]), layout, fs) for n in range(len(nodes))]
                curvesL = np.array([sos_db(s, FGRID, fs) for s in sosL])
                curvesR = curvesL[mm]
                e_node = []
                e_raw = []
                for n in range(len(nodes)):
                    for ear, cur, tgt in ((0, curvesL[n], TL[n]), (1, curvesR[n], TR[n])):
                        d = (cur - tgt)[EVAL_MASK]
                        e_node.append((float(np.max(np.abs(d))), float(np.sqrt(np.mean(d ** 2)))))
                        d2 = (cur - raw[n, ear])[EVAL_MASK]
                        e_raw.append((float(np.max(np.abs(d2))), float(np.sqrt(np.mean(d2 ** 2)))))
                e_node = np.array(e_node)
                e_raw = np.array(e_raw)
                # hold-out: measured direction vs SOS of nearest node (total), and target-of-node (quantisation only)
                hi, hn, hang = holdout_dirs(h, nodes)
                meas = h.mag_db(hi)
                tot, quant = [], []
                for j in range(len(hi)):
                    n = hn[j]
                    for ear, cur, tgt in ((0, curvesL[n], TL[n]), (1, curvesR[n], TR[n])):
                        d = (cur - meas[j, ear])[EVAL_MASK]
                        tot.append((np.max(np.abs(d)), np.sqrt(np.mean(d ** 2))))
                        dq = (tgt - meas[j, ear])[EVAL_MASK]
                        quant.append((np.max(np.abs(dq)), np.sqrt(np.mean(dq ** 2))))
                tot, quant = np.array(tot), np.array(quant)
                stab = [stability(s) for s in sosL]
                # ILD at nodes (el 0 ring), measured vs fitted
                per_k[K] = {
                    "node_fit_max_db": stats(e_node[:, 0]), "node_fit_rms_db": stats(e_node[:, 1]),
                    "vs_unsymmetrised_max_db": stats(e_raw[:, 0]), "vs_unsymmetrised_rms_db": stats(e_raw[:, 1]),
                    "holdout_total_max_db": stats(tot[:, 0]), "holdout_total_rms_db": stats(tot[:, 1]),
                    "holdout_quantisation_only_rms_db": stats(quant[:, 1]),
                    "n_holdout_dirs": int(len(hi)),
                    "max_pole_radius": float(max(s[0] for s in stab)),
                    "max_zero_radius": float(max(s[1] for s in stab)),
                    "per_node_max_db_L": e_node[0::2, 0].tolist(), "per_node_rms_db_L": e_node[0::2, 1].tolist(),
                    "per_node_max_db_R": e_node[1::2, 0].tolist(), "per_node_rms_db_R": e_node[1::2, 1].tolist(),
                }
            res[did][str(fs)] = {
                "sofa": str(DATASETS[did]["files"].get(fs) or DATASETS[did]["files"][48000]),
                "native_rate": fs in DATASETS[did]["files"],
                "node_measured_index": idx.tolist(), "node_offset_deg": ang.tolist(),
                "asymmetry_rms_db": stats(np.sqrt(np.mean(asym[:, EVAL_MASK] ** 2, axis=1))),
                "per_k": per_k,
            }
    return res


def itd_analysis(did):
    h = hset(did, 48000)
    s = h.sofa
    sel = np.where(np.abs(s.el) <= 60)[0]
    itx = measured_itd(s.ir[sel], s.fs, "xcorr")
    ito = measured_itd(s.ir[sel], s.fs, "onset")
    k = fit_woodworth(s.az[sel], s.el[sel], itx)
    th = lateral_angle(s.az[sel], s.el[sel])
    sp = s.ear_spacing_m
    g_meas = geometric_itd(s.az[sel], s.el[sel], sp, s.r[sel], C_ENGINE)
    g_far = (sp / C_ENGINE) * np.sin(th)
    ww = woodworth(th, k)
    corr = correction_s(th, k, sp, C_ENGINE)
    # tabulated alternative: median measured ITD per 5-degree lateral bin
    bins = np.arange(-90, 91, 5)
    lat = np.degrees(th)
    tab = []
    for b in bins:
        m = np.abs(lat - b) <= 2.5
        tab.append(float(np.median(itx[m])) if m.any() else float("nan"))
    tab = np.array(tab)
    tab_pred = np.interp(lat, bins, tab)
    rms = lambda x: float(np.sqrt(np.mean(x ** 2)) * 1e6)
    h0 = np.where(np.abs(s.el[sel]) < 1.0)[0]
    return {
        "method": "LF cross-correlation (4th-order LP 1.5 kHz, x8 upsampled, +-1 ms); onset = -20 dB threshold, reported for comparison",
        "n_dirs": int(len(sel)),
        "ear_spacing_m_from_sofa": sp,
        "woodworth_k_us": k * 1e6,
        "woodworth_a_eff_m_at_c343": k * C_MEAS,
        "measured_max_itd_us_xcorr": float(np.max(np.abs(itx)) * 1e6),
        "measured_max_itd_us_onset": float(np.max(np.abs(ito)) * 1e6),
        "geometric_max_itd_us_at_spacing": float(np.max(np.abs(g_meas)) * 1e6),
        "rms_err_us_geometry_only": rms(g_meas - itx),
        "rms_err_us_geometry_plus_woodworth_correction": rms(g_far + corr - itx),
        "rms_err_us_tabulated_5deg": rms(tab_pred - itx),
        "max_err_us_geometry_only": float(np.max(np.abs(g_meas - itx)) * 1e6),
        "max_err_us_geometry_plus_woodworth_correction": float(np.max(np.abs(g_far + corr - itx)) * 1e6),
        "max_err_us_tabulated_5deg": float(np.max(np.abs(tab_pred - itx)) * 1e6),
        "p95_err_us_woodworth": float(np.percentile(np.abs(g_far + corr - itx), 95) * 1e6),
        "p95_err_us_tabulated_5deg": float(np.percentile(np.abs(tab_pred - itx), 95) * 1e6),
        "max_correction_us": float(np.max(np.abs(corr)) * 1e6),
        "sign_check_left_source_positive": bool(itx[np.argmin(np.abs(s.az[sel] - 90) + np.abs(s.el[sel]))] > 0),
        "table_lateral_deg": bins.tolist(), "table_itd_us": (tab * 1e6).tolist(),
        "_plot": {"az_h": s.az[sel][h0].tolist(), "itx_h": (itx[h0] * 1e6).tolist(), "ito_h": (ito[h0] * 1e6).tolist(),
                  "geo_h": (g_meas[h0] * 1e6).tolist(), "ww_h": (ww[h0] * 1e6).tolist(), "tab_h": (tab_pred[h0] * 1e6).tolist()},
    }


def grid_study(did, gids=("G26", "G50", "G60", "G86")):
    """Quantisation-only error (no fitting): measured at hold-out dir vs measured at nearest node."""
    h = hset(did, 48000)
    out = {}
    for gid in gids:
        nodes = grid_nodes(gid)
        idx, _ = nearest_index(h.sofa, [n[0] for n in nodes], [n[1] for n in nodes])
        T = h.mag_db(idx)
        hi, hn, hang = holdout_dirs(h, nodes)
        M = h.mag_db(hi)
        d = (T[hn] - M)[:, :, EVAL_MASK]
        rms = np.sqrt(np.mean(d ** 2, axis=2)).reshape(-1)
        ild_m = band_levels(M)[:, 0] - band_levels(M)[:, 1]
        ild_t = band_levels(T[hn])[:, 0] - band_levels(T[hn])[:, 1]
        out[gid] = {"n_nodes": len(nodes), "records_symmetric": len(nodes), "records_per_ear_unsymmetric": 2 * len(nodes),
                    "quant_rms_db": stats(rms), "angle_to_node_deg": stats(hang),
                    "ild_err_db_abs_per_band_500_1k_2k_4k_8k_p95": np.percentile(np.abs(ild_t - ild_m), 95, axis=0).tolist()}
    return out


def entry_counts(gid):
    d = json.loads((REP / "engine_directions.json").read_text())
    nodes = grid_nodes(gid)
    mm = mirror_map(nodes)
    out = {}
    def nodes_for(dirs):
        nn, _ = nearest_node(nodes, [x["az"] for x in dirs], [x["el"] for x in dirs])
        return nn
    for scene, dirs in d.items():
        nn = nodes_for(dirs)
        L = set(nn.tolist())
        R = set(mm[i] for i in nn.tolist())  # right ear of node n uses left record of mirror(n)
        out[scene] = {"image_taps": len(dirs), "L_nodes": len(L), "R_nodes": len(set(nn.tolist())),
                      "records_symmetric_shared": len(L | R), "records_unsymmetric": 2 * len(set(nn.tolist())),
                      "play_filter_instances_per_ear": len(set(nn.tolist()))}
    # two sources apart (A + B) in the default room
    nnA, nnB = nodes_for(d["default_A"]), nodes_for(d["default_B"])
    allN = set(nnA.tolist()) | set(nnB.tolist())
    out["default_A+B"] = {"records_symmetric_shared": len(allN | set(mm[i] for i in allN)), "records_unsymmetric": 2 * len(allN)}
    out["worst_case_fixed_bank_symmetric"] = len(nodes)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", default="G60")
    ap.add_argument("--datasets", nargs="*", default=list(DATASETS))
    args = ap.parse_args()
    REP.mkdir(exist_ok=True)
    fits = stage1(args.grid, args.datasets)
    t0 = time.time()
    res = stage2(args.grid, fits, args.datasets)
    itd = {did: itd_analysis(did) for did in args.datasets}
    gs = {did: grid_study(did) for did in args.datasets}
    ec = entry_counts(args.grid)
    (REP / f"metrics_{args.grid}.json").write_text(json.dumps({"grid": args.grid, "fit": res, "itd": itd, "grid_study": gs, "entry_counts": ec}, indent=1))
    print(f"stage2 {time.time() - t0:.0f} s")
    for did in args.datasets:
        for fs in RATES:
            for K in KS:
                m = res[did][str(fs)]["per_k"][K]
                print(f"{did:14s} {fs} K{K}: node max med/p95/max {m['node_fit_max_db']['median']:.2f}/{m['node_fit_max_db']['p95']:.2f}/{m['node_fit_max_db']['max']:.2f}"
                      f"  node rms med/max {m['node_fit_rms_db']['median']:.2f}/{m['node_fit_rms_db']['max']:.2f}"
                      f"  holdout rms med/p95 {m['holdout_total_rms_db']['median']:.2f}/{m['holdout_total_rms_db']['p95']:.2f}"
                      f"  quant-only rms med {m['holdout_quantisation_only_rms_db']['median']:.2f}  pole {m['max_pole_radius']:.4f}")
    print(json.dumps({d: {k: v for k, v in itd[d].items() if not k.startswith('_') and not k.startswith('table')} for d in itd}, indent=1))
    print(json.dumps(gs, indent=1))
    print(json.dumps(ec, indent=1))


if __name__ == "__main__":
    main()
