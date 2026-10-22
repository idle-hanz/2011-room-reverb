"""Plots: multi-frequency polars (horizontal + vertical plane), 3D balloons, DI vs frequency."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import model as M
from .fit import FLOOR_DB

PF = [250, 500, 1000, 2000, 4000, 8000]
COLS = plt.cm.viridis(np.linspace(0, 0.95, len(PF)))


def _plane_dirs(plane, n=361):
    a = np.deg2rad(np.linspace(0, 360, n))
    if plane == "h":   # azimuth: x fwd, y left
        return a, np.stack([np.cos(a), np.sin(a), 0 * a], -1)
    return a, np.stack([np.cos(a), 0 * a, np.sin(a)], -1)  # vertical median: x fwd, z up


def _nearest_band(freqs, f):
    j = int(np.argmin(np.abs(np.log(freqs / f))))
    return j if abs(np.log2(freqs[j] / f)) < 0.2 else None


def polar(pid, params, ds, out, title=""):
    fig, axs = plt.subplots(1, 2, subplot_kw={"projection": "polar"}, figsize=(11, 5.4))
    for ax, plane, name in zip(axs, ("h", "v"), ("Horizontal (top view, 0°=facing, 90°=left)",
                                                  "Vertical median (side view, 0°=facing, 90°=up)")):
        a, d = _plane_dirs(plane)
        for f, col in zip(PF, COLS):
            r = M.relative_db(params, d, np.array([f], float))[:, 0]
            ax.plot(a, np.maximum(r, -30), color=col, lw=1.8, label=f"{f if f < 1000 else str(f // 1000) + 'k'} Hz model")
            if ds is not None:
                j = _nearest_band(ds.freqs, f)
                if j is not None and ds.band_ok[j]:
                    other = ds.dirs[:, 2] if plane == "h" else ds.dirs[:, 1]
                    tol = 0.09 if len(ds.dirs) > 200 else 0.3
                    m = np.abs(other) < tol
                    if m.any():
                        fr = int(np.argmax(ds.dirs[:, 0]))
                        L = ds.mag_db[:, j] - ds.mag_db[fr, j]
                        ang = (np.arctan2(ds.dirs[m, 1], ds.dirs[m, 0]) if plane == "h"
                               else np.arctan2(ds.dirs[m, 2], ds.dirs[m, 0]))
                        ax.scatter(ang, np.clip(L[m], -30, 12), s=9, color=col, alpha=0.7)
        ax.set_ylim(-30, 8)
        ax.set_yticks([-24, -18, -12, -6, 0, 6])
        ax.set_title(name, fontsize=9)
        ax.set_theta_zero_location("N")
    axs[0].legend(loc="lower left", bbox_to_anchor=(-0.25, -0.18), fontsize=7, ncol=3)
    fig.suptitle(f"{pid}: {title}\nlines = fitted model (dB re on-axis), dots = data (dB re data front axis)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def balloon(pid, params, out, freqs=(500, 2000, 8000), title=""):
    th = np.linspace(0, np.pi, 46)
    ph = np.linspace(0, 2 * np.pi, 91)
    TH, PH = np.meshgrid(th, ph)
    d = np.stack([np.sin(TH) * np.cos(PH), np.sin(TH) * np.sin(PH), np.cos(TH)], -1).reshape(-1, 3)
    fig = plt.figure(figsize=(12, 4.4))
    for i, f in enumerate(freqs):
        r = M.relative_db(params, d, np.array([f], float))[:, 0]
        rr = np.clip((r + 30) / 30, 0.02, None).reshape(TH.shape)
        X, Y, Z = (rr * np.sin(TH) * np.cos(PH), rr * np.sin(TH) * np.sin(PH), rr * np.cos(TH))
        ax = fig.add_subplot(1, len(freqs), i + 1, projection="3d")
        ax.plot_surface(X, Y, Z, facecolors=plt.cm.magma(np.clip(rr, 0, 1.2) / 1.2), rstride=1, cstride=1,
                        linewidth=0, antialiased=False, shade=False)
        ax.quiver(0, 0, 0, 1.4, 0, 0, color="cyan", lw=2)
        ax.set_box_aspect((1, 1, 1))
        lim = 1.1
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
        ax.set_xlabel("fwd"); ax.set_ylabel("left"); ax.set_zlabel("up")
        ax.set_title(f"{f} Hz (radius = dB+30)", fontsize=9)
        ax.view_init(elev=20, azim=-60)
    fig.suptitle(f"{pid}: model radiation balloons — cyan arrow = facing  {title}", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=100)
    plt.close(fig)


def di_plot(pid, params, fitres, diffuse, out):
    f = np.geomspace(50, 16000, 80)
    di = M.directivity_index_db(params, f)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.semilogx(f, di, label="model DI (dB)", lw=2)
    if fitres and fitres.get("di_data_db"):
        fd = np.array([float(k) for k in fitres["di_data_db"]])
        ax.semilogx(fd, list(fitres["di_data_db"].values()), "o", ms=4, label="data DI at data front axis")
    g = diffuse["gain_db"] + M.biquad_mag_db(M.rbj_high_shelf(diffuse["shelf_f0"], diffuse["shelf_gain_db"], 0.7), f)
    ax.semilogx(f, -g, "--", label="−(FDN inject filter) fitted gain+shelf")
    ax.set_xlabel("Hz"); ax.set_ylabel("dB"); ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    ax.set_title(f"{pid}: directivity index & power-averaged FDN inject weighting", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)
