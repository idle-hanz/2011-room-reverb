"""Plots for the binaural pack -> plots/binaural/. Reads caches + presets; no refitting."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from binaural_fitter.core import FGRID, EVAL_MASK, complex_spectra, nearest_index  # noqa: E402
from binaural_fitter.datasets import DATASETS  # noqa: E402
from binaural_fitter.grid import grid_nodes, mirror_map, nearest_node  # noqa: E402
from binaural_fitter.sosfit import LAYOUTS, params_to_sos, sos_db  # noqa: E402
from run_binaural_fit import band_levels, hset, sym_targets  # noqa: E402

GID = "G60"
PL = ROOT / "plots" / "binaural"
PL.mkdir(parents=True, exist_ok=True)
REP = ROOT / "reports"
FITS = json.loads((REP / f"fits_{GID}.json").read_text())
MET = json.loads((REP / f"metrics_{GID}.json").read_text())
NODES = grid_nodes(GID)
MM = mirror_map(NODES)
FS = 48000
KSHIP = 6


def curves(did, fs, K):
    F = FITS[f"{did}|{fs}"]
    cl = np.array([sos_db(params_to_sos(np.array(F[str(n)][str(K)]), LAYOUTS[K], fs), FGRID, fs) for n in range(len(NODES))])
    return cl, cl[MM]


def node_of(az, el):
    i, _ = nearest_node(NODES, [az], [el])
    return int(i[0])


def plot_hrtf_vs_fit(did):
    h = hset(did, FS)
    idx, _, raw, TL, TR, _, _ = sym_targets(h, NODES)
    c6L, c6R = curves(did, FS, KSHIP)
    c3L, _ = curves(did, FS, 3)
    dirs = [(0, 0), (40, 0), (80, 0), (140, 0), (180, 0), (-100, 0), (30, 30), (0, -30)]
    fig, axs = plt.subplots(2, 4, figsize=(17, 8), sharex=True)
    for ax, (az, el) in zip(axs.flat, dirs):
        n = node_of(az, el)
        rawidx = idx[n]
        rr = h.raw_mag_db([rawidx])[0]
        ax.semilogx(FGRID, rr[0], color="C0", alpha=0.25, lw=0.8)
        ax.semilogx(FGRID, rr[1], color="C3", alpha=0.25, lw=0.8)
        ax.semilogx(FGRID, TL[n], color="C0", lw=2, label="L measured (DFE, 1/6-oct, sym)")
        ax.semilogx(FGRID, TR[n], color="C3", lw=2, label="R measured")
        ax.semilogx(FGRID, c6L[n], "k--", lw=1.3, label=f"L fit K={KSHIP}")
        ax.semilogx(FGRID, c6R[n], "--", color="0.4", lw=1.3, label=f"R fit K={KSHIP}")
        ax.semilogx(FGRID, c3L[n], ":", color="C2", lw=1.3, label="L fit K=3")
        eL = np.abs(c6L[n] - TL[n])[EVAL_MASK].max()
        eR = np.abs(c6R[n] - TR[n])[EVAL_MASK].max()
        ax.set_title(f"az {NODES[n][0]:+.0f} el {NODES[n][1]:+.0f}  (max err K{KSHIP}: L {eL:.1f} / R {eR:.1f} dB)", fontsize=9)
        ax.axvspan(20, 100, color="0.9"); ax.axvspan(16000, 20000, color="0.9")
        ax.set_xlim(40, 20000); ax.set_ylim(-45, 20); ax.grid(True, which="both", alpha=0.3)
    axs[0, 0].legend(fontsize=7, loc="lower left")
    for ax in axs[1]:
        ax.set_xlabel("Hz")
    for ax in axs[:, 0]:
        ax.set_ylabel("dB (diffuse-field EQ)")
    fig.suptitle(f"{DATASETS[did]['display_name']}: measured HRTF vs min-phase SOS fit ({FS} Hz; faint = unsmoothed; grey = outside 100 Hz-16 kHz metric band)  [MEASURED, {DATASETS[did]['licence']}]", fontsize=10)
    fig.tight_layout()
    p = PL / f"{did}_hrtf_vs_fit.png"
    fig.savefig(p, dpi=110); plt.close(fig)
    return p


def horizontal(did):
    h = hset(did, FS)
    s = h.sofa
    sel = np.where(np.abs(s.el) < 0.6)[0]
    order = np.argsort(s.az[sel])
    sel = sel[order]
    # de-duplicate azimuths (SADIE has repeated az on the el=0 ring from multiple configurations)
    _, u = np.unique(np.round(s.az[sel], 1), return_index=True)
    sel = sel[u]
    return h, sel


def plot_ild_itd(did):
    h, sel = horizontal(did)
    s = h.sofa
    M = h.mag_db(sel)
    bl = band_levels(M)  # (n, 2, 5)
    ild_m = bl[:, 0] - bl[:, 1]
    c6L, c6R = curves(did, FS, KSHIP)
    nn, _ = nearest_node(NODES, s.az[sel], s.el[sel])
    blf = band_levels(np.stack([c6L[nn], c6R[nn]], axis=1))
    ild_f = blf[:, 0] - blf[:, 1]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 5.5))
    for j, fc in enumerate((500, 1000, 2000, 4000, 8000)):
        a1.plot(s.az[sel], ild_m[:, j], color=f"C{j}", lw=1.5, label=f"{fc} Hz measured")
        a1.plot(s.az[sel], ild_f[:, j], color=f"C{j}", lw=1, ls="--")
    a1.set_xlabel("azimuth deg (+ = left), el 0"); a1.set_ylabel("ILD = L - R, octave band dB")
    a1.set_title(f"ILD: measured (solid) vs K={KSHIP} fit at nearest {GID} node (dashed)", fontsize=10)
    a1.grid(alpha=0.3); a1.legend(fontsize=8); a1.set_xlim(-180, 180)
    it = MET["itd"][did]["_plot"]
    az = np.array(it["az_h"]); o = np.argsort(az)
    a2.plot(az[o], np.array(it["itx_h"])[o], lw=2, label="measured, LF x-corr (<1.5 kHz)")
    a2.plot(az[o], np.array(it["ito_h"])[o], lw=1, alpha=0.7, label="measured, onset -20 dB")
    a2.plot(az[o], np.array(it["geo_h"])[o], "k:", lw=1.5, label=f"engine geometry only, spacing {MET['itd'][did]['ear_spacing_m_from_sofa']:.3f} m, c 340")
    a2.plot(az[o], np.array(it["ww_h"])[o], "r--", lw=1.5, label=f"geometry + Woodworth correction (a_eff {MET['itd'][did]['woodworth_a_eff_m_at_c343']*100:.1f} cm)")
    a2.plot(az[o], np.array(it["tab_h"])[o], "g-", lw=1.2, label="geometry + tabulated correction (5 deg lateral bins, SHIPPED)")
    a2.set_xlabel("azimuth deg (+ = left), el 0"); a2.set_ylabel("ITD = t_R - t_L (us); + = left ear leads")
    a2.set_title("ITD vs azimuth", fontsize=10); a2.grid(alpha=0.3); a2.legend(fontsize=8); a2.set_xlim(-180, 180)
    fig.suptitle(f"{DATASETS[did]['display_name']}  [MEASURED]", fontsize=11)
    fig.tight_layout()
    p = PL / f"{did}_ild_itd.png"
    fig.savefig(p, dpi=110); plt.close(fig)
    return p


def plot_polar_top(did):
    h, sel = horizontal(did)
    s = h.sofa
    M = h.mag_db(sel)
    bl = band_levels(M, bands=(500, 2000, 4000, 8000))
    c6L, c6R = curves(did, FS, KSHIP)
    nn, _ = nearest_node(NODES, s.az[sel], s.el[sel])
    blf = band_levels(np.stack([c6L[nn], c6R[nn]], axis=1), bands=(500, 2000, 4000, 8000))
    th = np.radians(s.az[sel])
    fig, axs = plt.subplots(1, 4, figsize=(20, 5.6), subplot_kw={"projection": "polar"})
    for j, (ax, fc) in enumerate(zip(axs, (500, 2000, 4000, 8000))):
        ax.set_theta_zero_location("N"); ax.set_theta_direction(1)  # az +90 (left) drawn on the left
        rmin = -30
        for e, col, nm in ((0, "C0", "L ear"), (1, "C3", "R ear")):
            ax.plot(np.r_[th, th[:1]], np.clip(np.r_[bl[:, e, j], bl[:1, e, j]], rmin, None), color=col, lw=2, label=f"{nm} measured")
            ax.plot(np.r_[th, th[:1]], np.clip(np.r_[blf[:, e, j], blf[:1, e, j]], rmin, None), color=col, lw=1, ls="--", label=f"{nm} fit K{KSHIP}")
        ax.set_rlim(rmin, 15); ax.set_rticks([-30, -20, -10, 0, 10]); ax.tick_params(labelsize=7)
        # head (radius in r-units ~ small circle near centre drawn in axes coords)
        hx = ax.inset_axes([0.42, 0.42, 0.16, 0.16]); hx.set_aspect("equal"); hx.axis("off")
        hx.add_patch(plt.Circle((0, 0), 1, fill=False, lw=1.5))
        hx.plot([-.25, 0, .25], [0.95, 1.3, 0.95], "k-", lw=1.2)  # nose (front = up)
        hx.add_patch(plt.Rectangle((-1.2, -0.25), 0.2, 0.5, color="C0")); hx.add_patch(plt.Rectangle((1.0, -0.25), 0.2, 0.5, color="C3"))
        hx.text(-1.5, -0.9, "L", color="C0", fontsize=8); hx.text(1.2, -0.9, "R", color="C3", fontsize=8)
        hx.set_xlim(-1.6, 1.6); hx.set_ylim(-1.3, 1.5)
        ax.set_title(f"{fc} Hz octave band (dB, DF-EQ)", fontsize=10)
    hd, lb = axs[0].get_legend_handles_labels()
    fig.legend(hd, lb, fontsize=8, loc="lower center", ncol=4)
    fig.suptitle(f"Head-top polar view (front = up, left = left), el 0: {DATASETS[did]['display_name']}  [MEASURED]", fontsize=11)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    p = PL / f"{did}_polar_top.png"
    fig.savefig(p, dpi=110); plt.close(fig)
    return p


def plot_error_map(did):
    m = MET["fit"][did][str(FS)]["per_k"][str(KSHIP)]
    d = json.loads((REP / "engine_directions.json").read_text())
    az = np.array([n[0] for n in NODES]); el = np.array([n[1] for n in NODES])
    fig, axs = plt.subplots(1, 2, figsize=(15, 5))
    for ax, ear in zip(axs, ("L", "R")):
        sc = ax.scatter(az, el, c=m[f"per_node_max_db_{ear}"], s=160, cmap="viridis", vmin=0, vmax=5, edgecolor="k")
        for scene, mk in (("default_A", "x"), ("small_A", "+")):
            ax.scatter([x["az"] for x in d[scene]], [x["el"] for x in d[scene]], marker=mk, color="r", s=30, label=f"engine image dirs ({scene})")
        ax.set_xlim(185, -185); ax.set_ylim(-95, 95); ax.grid(alpha=0.3)
        ax.set_xlabel("azimuth deg (+ = left; plotted left = left)"); ax.set_ylabel("elevation deg")
        ax.set_title(f"{ear} ear: per-node max |error| dB, K={KSHIP}, 100 Hz-16 kHz", fontsize=10)
        plt.colorbar(sc, ax=ax)
    axs[0].legend(fontsize=7, loc="lower left")
    fig.suptitle(f"{GID} grid ({len(NODES)} nodes, mirror-symmetric = {len(NODES)} shared records <= MAX_IRS 64): {DATASETS[did]['display_name']}", fontsize=11)
    fig.tight_layout()
    p = PL / f"{did}_grid_error_map.png"
    fig.savefig(p, dpi=110); plt.close(fig)
    return p


def plot_k_tradeoff():
    bench = {}
    for line in (REP / "bench_sos_box.log").read_text().splitlines():
        if line.startswith("filters=34"):
            k = int(line.split("K=")[1].split(":")[0]); bench[k] = float(line.split("%")[0].split(",")[-1].split()[0])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 5.5))
    Ks = [3, 4, 5, 6]
    for i, did in enumerate(DATASETS):
        for fs, ls in ((44100, ":"), (48000, "-")):
            pk = MET["fit"][did][str(fs)]["per_k"]
            a1.plot(Ks, [pk[str(k)]["node_fit_max_db"]["p95"] for k in Ks], ls=ls, marker="o", color=f"C{i}", label=f"{did} {fs} node max p95" if fs == 48000 else None)
            a1.plot(Ks, [pk[str(k)]["node_fit_rms_db"]["median"] for k in Ks], ls=ls, marker="s", color=f"C{i}", alpha=0.6, label=f"{did} node rms median" if fs == 48000 else None)
            a1.plot(Ks, [pk[str(k)]["holdout_total_rms_db"]["median"] for k in Ks], ls=ls, marker="^", color=f"C{i}", alpha=0.35, label=f"{did} hold-out rms median (incl. grid)" if fs == 48000 else None)
    a1.set_xlabel("biquads per ear entry (K)"); a1.set_ylabel("dB (100 Hz-16 kHz)"); a1.grid(alpha=0.3)
    a1.set_xticks(Ks); a1.legend(fontsize=7); a1.set_title("Fit error vs K (solid 48 kHz, dotted 44.1 kHz)", fontsize=10)
    ax2 = a1.twinx(); ax2.bar(Ks, [bench.get(k, np.nan) for k in Ks], alpha=0.12, color="k", width=0.5)
    ax2.set_ylabel("Play colour CPU, % of one box core @48k (34 filters)")
    gs = MET["grid_study"]
    for i, did in enumerate(DATASETS):
        g = gs[did]; ks = list(g)
        a2.plot([g[k]["n_nodes"] for k in ks], [g[k]["quant_rms_db"]["median"] for k in ks], "o-", color=f"C{i}", label=f"{did} median")
        a2.plot([g[k]["n_nodes"] for k in ks], [g[k]["quant_rms_db"]["p95"] for k in ks], "o--", color=f"C{i}", alpha=0.6, label=f"{did} p95")
    a2.axvline(64, color="r", lw=1); a2.text(65, 3.9, "MAX_IRS 64", color="r", fontsize=8)
    a2.set_xlabel("grid nodes (= records, mirror-symmetric)"); a2.set_ylabel("grid quantisation RMS dB (measured, no fit)")
    a2.set_title("Grid quantisation error at hold-out directions (G26 / G50 / G60 / G86)", fontsize=10)
    a2.grid(alpha=0.3); a2.legend(fontsize=7)
    fig.tight_layout()
    p = PL / "k_tradeoff_and_grid.png"
    fig.savefig(p, dpi=110); plt.close(fig)
    return p


def plot_coherence():
    fig, ax = plt.subplots(figsize=(9, 5))
    out = {}
    f_out = np.geomspace(50, 16000, 120)
    for i, did in enumerate(DATASETS):
        h = hset(did, FS)
        f, H = complex_spectra(h.sofa.ir, h.sofa.fs, nfft=1024)
        w = h.w
        num = np.einsum("m,mf->f", w, H[:, 0] * np.conj(H[:, 1]))
        den = np.sqrt(np.einsum("m,mf->f", w, np.abs(H[:, 0]) ** 2) * np.einsum("m,mf->f", w, np.abs(H[:, 1]) ** 2))
        ic = np.real(num) / den
        ax.semilogx(f[1:], ic[1:], color=f"C{i}", lw=1.8, label=f"{did} (MEASURED, diffuse-field)")
        out[did] = {"f_hz": f_out.tolist(), "ic_real": np.interp(f_out, f, ic).tolist()}
    fx = np.geomspace(50, 16000, 400)
    s = 0.18
    ax.semilogx(fx, np.sinc(2 * fx * s / 340.0), "k:", label="two free-field omnis 0.18 m (sinc)")
    ax.axhline(0, color="0.5", lw=0.8)
    ax.set_xlabel("Hz"); ax.set_ylabel("interaural coherence Re{IC}")
    ax.set_title("Diffuse-field interaural coherence (area-weighted over the measured sphere)", fontsize=10)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8); ax.set_xlim(50, 16000)
    fig.tight_layout()
    p = PL / "diffuse_field_coherence.png"
    fig.savefig(p, dpi=110); plt.close(fig)
    (REP / "diffuse_field_coherence.json").write_text(json.dumps(out))
    return p


if __name__ == "__main__":
    paths = []
    for did in DATASETS:
        paths += [plot_hrtf_vs_fit(did), plot_ild_itd(did), plot_polar_top(did), plot_error_map(did)]
    paths += [plot_k_tradeoff(), plot_coherence()]
    for p in paths:
        print(p)
