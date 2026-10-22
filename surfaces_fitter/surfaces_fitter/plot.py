"""Plots: α bars; R_db ISO-target vs model; gallery index."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .fit import FitResult
from .materials import OCTAVE_HZ
from .model import SurfaceAbsModel, alpha_at_freqs, fit_freqs, target_r_db


def plot_alpha_bars(out_path: Path, result: FitResult) -> Path:
    """Bar chart of textbook α at octave centres (+ model α markers)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    hz = np.asarray(result.absorb_hz, dtype=float)
    alpha = np.asarray(result.absorb, dtype=float)
    model = SurfaceAbsModel(model=result.model, **result.params)
    model_a = model.model_alpha(hz)

    labels = [f"{int(h)}" if h < 1000 else f"{int(h/1000)}k" for h in hz]
    x = np.arange(len(hz))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(x - 0.18, alpha, width=0.36, color="#64748b", label="textbook α (ASSUMED)")
    ax.bar(x + 0.18, model_a, width=0.36, color="#f59e0b", alpha=0.85, label="model α")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("α (energy absorb)")
    ax.set_xlabel("Hz")
    ax.set_title(f"{result.display_name} — absorb bands\nroles={result.roles} · {result.honesty}")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def plot_r_db_fit(out_path: Path, result: FitResult) -> Path:
    """Target R_db (from √(1−α)) vs fitted model on log-frequency."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    freqs = fit_freqs(256)
    target = target_r_db(freqs, OCTAVE_HZ, result.alpha_octave)
    model = SurfaceAbsModel(model=result.model, **result.params)
    pred = model.r_db(freqs)

    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ax.semilogx(freqs, target, "k-", lw=2.0, label="target R_db = 20·log10√(1−α)")
    ax.semilogx(freqs, pred, "C1--", lw=2.0, label=f"model ({result.model})")
    # Mark octave centres
    oct_f = np.asarray(result.absorb_hz, dtype=float)
    oct_t = target_r_db(oct_f, OCTAVE_HZ, result.alpha_octave)
    ax.scatter(oct_f, oct_t, c="k", s=28, zorder=5, label="octave centres")
    ax.set_xlim(freqs[0], freqs[-1])
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("R (dB)  amplitude reflection")
    ax.set_title(
        f"{result.display_name} — fit RMSE={result.rmse_r_db:.3f} dB · "
        f"absorb L1={result.absorb_l1:.4f}"
    )
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def plot_gallery_index(out_path: Path, results: Sequence[FitResult]) -> Path:
    """One gallery: small multiples of R_db target vs model for all materials."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(results)
    cols = 3
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(4.6 * cols, 3.2 * rows), squeeze=False)
    fig.suptitle(
        "surfaces_fitter gallery — target R_db vs model (ASSUMED_TEXTBOOK)",
        fontsize=12,
    )
    freqs = fit_freqs(128)
    for i, r in enumerate(results):
        ax = axes[i // cols][i % cols]
        target = target_r_db(freqs, OCTAVE_HZ, r.alpha_octave)
        model = SurfaceAbsModel(model=r.model, **r.params)
        pred = model.r_db(freqs)
        ax.semilogx(freqs, target, "k-", lw=1.4)
        ax.semilogx(freqs, pred, "C1--", lw=1.4)
        ax.set_title(f"{r.material_id}\nRMSE={r.rmse_r_db:.2f} dB · {r.model}", fontsize=8)
        ax.grid(True, which="both", alpha=0.25)
        ax.tick_params(labelsize=7)
    for j in range(n, rows * cols):
        axes[j // cols][j % cols].axis("off")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_role_matrix(out_path: Path, results: Sequence[FitResult]) -> Path:
    """Heat-ish role × material legality matrix."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    roles = ["floor", "wall", "ceiling"]
    ids = [r.material_id for r in results]
    mat = np.zeros((len(roles), len(ids)))
    for j, r in enumerate(results):
        for i, role in enumerate(roles):
            mat[i, j] = 1.0 if role in r.roles else 0.0

    fig, ax = plt.subplots(figsize=(max(8.0, 0.7 * len(ids)), 3.2))
    im = ax.imshow(mat, aspect="auto", cmap="Greens", vmin=0, vmax=1)
    ax.set_yticks(range(len(roles)))
    ax.set_yticklabels(roles)
    ax.set_xticks(range(len(ids)))
    ax.set_xticklabels(ids, rotation=45, ha="right", fontsize=8)
    ax.set_title("Role legality (green = allowed)")
    for i in range(len(roles)):
        for j in range(len(ids)):
            ax.text(
                j, i, "OK" if mat[i, j] > 0.5 else "—",
                ha="center", va="center", fontsize=7,
                color="#064e3b" if mat[i, j] > 0.5 else "#94a3b8",
            )
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, ticks=[0, 1])
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path
