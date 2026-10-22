"""Plots: ISO vs model path loss, α(f) vs H1, ASSUMED shelf comparison."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .iso9613 import Climate, alpha_db_per_m, path_loss_db
from .model import AirAbsModel, assumed_shelf_h1_db


def plot_fit_distances(
    out_path: Path,
    title: str,
    freqs: np.ndarray,
    distances: Sequence[float],
    climate: Climate,
    model: AirAbsModel,
    assumed_humidities: Sequence[float] = (0.5, 1.0),
) -> Path:
    """ISO vs model path loss A_db(f,d) at several distances (+ ASSUMED overlay)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(distances)
    cols = 2
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(5.2 * cols, 3.6 * rows), squeeze=False)
    fig.suptitle(
        f"{title}\nISO 9613-1 vs fitted model — path loss A_db(f,d) ≤ 0",
        fontsize=11,
    )
    for i, d in enumerate(distances):
        ax = axes[i // cols][i % cols]
        iso = path_loss_db(freqs, d, climate)
        pred = model.path_loss_db(freqs, d)
        ax.semilogx(freqs, iso, "k-", lw=1.8, label="ISO 9613-1")
        ax.semilogx(freqs, pred, "C1--", lw=1.8, label=f"model ({model.model})")
        for j, hum in enumerate(assumed_humidities):
            h1 = assumed_shelf_h1_db(freqs, humidity=hum)
            ax.semilogx(
                freqs,
                float(d) * h1,
                ls=":",
                color=f"C{j + 2}",
                lw=1.3,
                label=f"ASSUMED hum={hum:g}",
            )
        ax.set_xlim(freqs[0], freqs[-1])
        ax.set_xlabel("Hz")
        ax.set_ylabel("A (dB)")
        ax.set_title(f"d = {d:g} m")
        ax.grid(True, which="both", alpha=0.3)
        if i == 0:
            ax.legend(fontsize=7, loc="lower left")
    for j in range(n, rows * cols):
        axes[j // cols][j % cols].axis("off")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def plot_shape_h1(
    out_path: Path,
    title: str,
    freqs: np.ndarray,
    climate: Climate,
    model: AirAbsModel,
) -> Path:
    """α ISO (as −α) vs H1(f) in dB/m."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    alpha = alpha_db_per_m(freqs, climate)
    h1 = model.h1_db_per_m(freqs)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.semilogx(freqs, -alpha, "k-", lw=2.0, label="−α_ISO (dB/m)")
    ax.semilogx(freqs, h1, "C1--", lw=2.0, label=f"H1 model ({model.model})")
    for hum, ls in ((0.5, ":"), (1.0, "-.")):
        ax.semilogx(
            freqs,
            assumed_shelf_h1_db(freqs, humidity=hum),
            ls=ls,
            color="C2" if hum == 0.5 else "C3",
            lw=1.4,
            label=f"ASSUMED −0.15·hum={hum:g}",
        )
    ax.set_xlim(freqs[0], freqs[-1])
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("dB / metre")
    ax.set_title(f"{title} — shape H1(f)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def plot_hall_long_path(
    out_path: Path,
    freqs: np.ndarray,
    climate: Climate,
    model: AirAbsModel,
    distances: Sequence[float] = (40.0, 60.0, 80.0),
) -> Path:
    """Optional note plot: studio coeffs at long hall distances (no extra fit)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    cmap = plt.cm.plasma(np.linspace(0.2, 0.85, len(distances)))
    for i, d in enumerate(distances):
        iso = path_loss_db(freqs, d, climate)
        pred = model.path_loss_db(freqs, d)
        ax.semilogx(freqs, iso, color=cmap[i], lw=1.8, label=f"ISO {d:g} m")
        ax.semilogx(freqs, pred, color=cmap[i], lw=1.6, ls="--", alpha=0.9)
    ax.set_xlim(freqs[0], freqs[-1])
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("A (dB)")
    ax.set_title(
        "hall_long_path note — studio coeffs at 40–80 m (solid=ISO, dashed=model)"
    )
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path
