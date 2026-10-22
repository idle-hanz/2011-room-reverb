"""Comparison plots: measured/ASSUMED target vs model for train & holdout angles."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .model import MicShelfModel


def plot_comparison(
    out_path: Path,
    title: str,
    freqs: np.ndarray,
    angles: Sequence[float],
    target_db: np.ndarray,
    model: MicShelfModel,
    honesty: str,
    split_label: str,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pred = model.relative_db(freqs, np.asarray(angles, dtype=float))
    n = len(angles)
    cols = min(3, max(n, 1))
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 3.2 * rows), squeeze=False)
    fig.suptitle(f"{title}\n[{honesty}] {split_label} — relative H(θ)/H(0°) dB", fontsize=11)

    for i, ang in enumerate(angles):
        ax = axes[i // cols][i % cols]
        ax.semilogx(freqs, target_db[i], "k-", lw=1.6, label="target")
        ax.semilogx(freqs, pred[i], "C1--", lw=1.6, label="model")
        ax.set_xlim(freqs[0], freqs[-1])
        ax.set_xlabel("Hz")
        ax.set_ylabel("dB rel")
        ax.set_title(f"θ = {ang:g}°")
        ax.grid(True, which="both", alpha=0.3)
        if i == 0:
            ax.legend(fontsize=8)

    for j in range(n, rows * cols):
        axes[j // cols][j % cols].axis("off")

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_overlay_all(
    out_path: Path,
    title: str,
    freqs: np.ndarray,
    angles: Sequence[float],
    target_db: np.ndarray,
    model: MicShelfModel,
    honesty: str,
) -> Path:
    """Single-axis overlay of several angles (target solid, model dashed)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pred = model.relative_db(freqs, np.asarray(angles, dtype=float))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    cmap = plt.cm.viridis(np.linspace(0.15, 0.9, len(angles)))
    for i, ang in enumerate(angles):
        ax.semilogx(freqs, target_db[i], color=cmap[i], lw=1.4, label=f"{ang:g}° tgt")
        ax.semilogx(freqs, pred[i], color=cmap[i], lw=1.4, ls="--", alpha=0.85)
    ax.set_xlim(freqs[0], freqs[-1])
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Relative level (dB)")
    ax.set_title(f"{title} [{honesty}] solid=target dashed=model")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=7, ncol=2, loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path
