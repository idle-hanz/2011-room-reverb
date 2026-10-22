"""Classic polar-pattern plots at several frequencies + off-axis colour helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .model import MicShelfModel, angle_weight


def cardioid_level(theta_deg: np.ndarray, pattern: str = "cardioid") -> np.ndarray:
    """Broadband geometric polar (linear pressure), independent of colour model."""
    th = np.deg2rad(np.asarray(theta_deg, dtype=float))
    c = np.cos(th)
    if pattern in ("cardioid", "dynamic_cardioid", "sdc_cardioid", "ldc_cardioid"):
        return 0.5 * (1.0 + c)
    if pattern in ("fig8", "fig8_ribbon", "bidirectional"):
        return np.abs(c)
    if pattern in ("supercardioid",):
        return 0.37 + 0.63 * c
    if pattern in ("omni", "omnidirectional"):
        return np.ones_like(c)
    return 0.5 * (1.0 + c)


def frequency_dependent_polar_db(
    model: MicShelfModel,
    freqs: Sequence[float],
    family: str,
    n_theta: int = 361,
    pattern_null_db: float = -18.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Combine geometric polar + colour model into dB polar vs angle at each freq.

    Returns theta_deg (n,), freqs (m,), pol_db (m, n) normalised so max at each
    freq is 0 dB (classic polar presentation).
    """
    theta = np.linspace(0.0, 360.0, n_theta)
    freqs = np.asarray(freqs, dtype=float)
    geom = cardioid_level(theta, family)
    geom_db = 20.0 * np.log10(np.maximum(geom, 1e-4))

    # colour relative to on-axis from tiny model
    colour = model.relative_db(freqs, theta)  # (n_theta, n_freq) -> transpose
    # model returns (n_theta, n_freq)
    colour = colour.T  # (n_freq, n_theta)

    # mild pattern-HF blend (same spirit as synthetic generator)
    w = angle_weight(theta, max(model.p * 0.85, 0.5))
    f_blend = 1.0 / (1.0 + np.exp(-3.0 * np.log10(freqs / 1500.0)))
    pattern = (pattern_null_db * w[None, :]) * f_blend[:, None]

    if family in ("fig8_ribbon", "fig8", "bidirectional"):
        side = np.sin(np.deg2rad(theta)) ** 2
        pattern = pattern * 0.35 + (-18.0 * side[None, :]) * f_blend[:, None]

    pol = geom_db[None, :] + colour + pattern
    # normalise per frequency to 0 dB peak
    pol = pol - np.max(pol, axis=1, keepdims=True)
    return theta, freqs, pol


def plot_polar_gallery(
    out_path: Path,
    title: str,
    model: MicShelfModel,
    family: str,
    honesty: str,
    freqs: Sequence[float] = (63.0, 125.0, 250.0, 1000.0, 4000.0, 8000.0),
    pattern_null_db: float = -18.0,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    theta, fr, pol = frequency_dependent_polar_db(
        model, freqs, family, pattern_null_db=pattern_null_db
    )
    th_rad = np.deg2rad(theta)

    n = len(fr)
    fig, axes = plt.subplots(1, n, subplot_kw={"projection": "polar"}, figsize=(3.1 * n, 3.4))
    if n == 1:
        axes = [axes]
    fig.suptitle(f"{title}\n[{honesty}] polar field (0 dB = peak at each freq)", fontsize=11)

    for ax, f, row in zip(axes, fr, pol):
        # dB → linear radius for display (map -40..0 → 0..1)
        r = np.clip((row + 40.0) / 40.0, 0.0, 1.0)
        ax.plot(th_rad, r, "C0-", lw=1.8)
        ax.fill(th_rad, r, alpha=0.15)
        ax.set_title(f"{f/1000 if f >= 1000 else f:g}{'k' if f >= 1000 else ''}Hz", va="bottom")
        ax.set_ylim(0, 1.05)
        ax.set_rticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels([])
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)

    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def plot_colour_curves(
    out_path: Path,
    title: str,
    freqs: np.ndarray,
    angles: Sequence[float],
    target_db: np.ndarray,
    model: MicShelfModel,
    honesty: str,
) -> Path:
    """Off-axis colour curves (same as overlay, under plots/colour/)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pred = model.relative_db(freqs, np.asarray(angles, dtype=float))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    cmap = plt.cm.plasma(np.linspace(0.1, 0.9, len(angles)))
    for i, ang in enumerate(angles):
        ax.semilogx(freqs, target_db[i], color=cmap[i], lw=1.5, label=f"{ang:g}°")
        ax.semilogx(freqs, pred[i], color=cmap[i], lw=1.3, ls="--", alpha=0.85)
    ax.axhline(0, color="k", lw=0.6, alpha=0.4)
    ax.set_xlim(freqs[0], freqs[-1])
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Relative level vs 0° (dB)")
    ax.set_title(f"{title} [{honesty}] colour — solid=target dashed=model")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8, ncol=2, title="angle")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def plot_measured_polar_gallery(
    out_path: Path,
    title: str,
    freqs_plot: Sequence[float],
    angles_deg: np.ndarray,
    freqs_full: np.ndarray,
    db_rel: np.ndarray,
    honesty: str,
    family: str = "cardioid",
) -> Path:
    """
    Polar from measured relative dB + geometric pattern, at selected freqs.
    db_rel: (n_angle, n_freq_full) relative to 0°.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # densify angles by reflecting if we only have 0..180
    ang = np.asarray(angles_deg, dtype=float)
    # interpolate relative colour onto a full circle
    theta = np.linspace(0.0, 360.0, 361)
    # fold to [0,180] for lookup
    fold = np.abs(((theta + 180.0) % 360.0) - 180.0)
    # sort unique measured
    order = np.argsort(ang)
    ang_s = ang[order]
    db_s = db_rel[order]

    n = len(freqs_plot)
    fig, axes = plt.subplots(1, n, subplot_kw={"projection": "polar"}, figsize=(3.1 * n, 3.4))
    if n == 1:
        axes = [axes]
    fig.suptitle(
        f"{title}\n[{honesty}] measured+geom polar (0 dB = peak)",
        fontsize=11,
    )

    geom = cardioid_level(theta, family)
    geom_db = 20.0 * np.log10(np.maximum(geom, 1e-4))

    for ax, f in zip(axes, freqs_plot):
        # interpolate colour at this freq across measured angles
        col_at_ang = np.array(
            [np.interp(f, freqs_full, db_s[i]) for i in range(len(ang_s))]
        )
        col = np.interp(fold, ang_s, col_at_ang)
        pol = geom_db + col
        pol = pol - np.max(pol)
        r = np.clip((pol + 40.0) / 40.0, 0.0, 1.0)
        ax.plot(np.deg2rad(theta), r, "C2-", lw=1.8)
        ax.fill(np.deg2rad(theta), r, alpha=0.15, color="C2")
        label = f"{f/1000:g}kHz" if f >= 1000 else f"{f:g}Hz"
        ax.set_title(label, va="bottom")
        ax.set_ylim(0, 1.05)
        ax.set_rticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels([])
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)

    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path
