"""3D stacked polar-field solids (room Polar view style).

Height = frequency (log10), radial distance = linear polar magnitude.
Uses the same frequency_dependent_polar_db construction as polar.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — registers 3d projection

from .model import MicShelfModel
from .polar import frequency_dependent_polar_db

# Dense log layers for the solid (~40–60)
DEFAULT_F_LO = 20.0
DEFAULT_F_HI = 16000.0
DEFAULT_N_LAYERS = 48

# Discrete rings (classic room-software style)
RING_FREQS = (20.0, 63.0, 125.0, 250.0, 1000.0, 4000.0, 8000.0, 16000.0)


def _db_to_radius(pol_db: np.ndarray, floor_db: float = -40.0) -> np.ndarray:
    """Convert normalised polar dB (peak=0) to linear radius in [0, 1].

    Uses pressure magnitude 10**(dB/20), clipped at floor_db, then
    normalised so 0 dB → 1.0.
    """
    clipped = np.maximum(pol_db, floor_db)
    r = 10.0 ** (clipped / 20.0)
    r0 = 10.0 ** (0.0 / 20.0)  # = 1
    return np.clip(r / r0, 0.0, 1.0)


def _freq_to_z(freqs: np.ndarray) -> np.ndarray:
    return np.log10(np.asarray(freqs, dtype=float))


def plot_polar_solid(
    out_path: Path,
    title: str,
    model: MicShelfModel,
    family: str,
    honesty: str,
    f_lo: float = DEFAULT_F_LO,
    f_hi: float = DEFAULT_F_HI,
    n_layers: int = DEFAULT_N_LAYERS,
    n_theta: int = 181,
    pattern_null_db: float = -18.0,
    colormap: str = "plasma",
    color_by: str = "freq",
    dpi: int = 140,
) -> Path:
    """
    Render a 3D polar solid: θ around, radius = linear magnitude, z = log10(f).

    Low frequency at the base, high at the top. Matches room Polar stacking.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    freqs = np.logspace(np.log10(f_lo), np.log10(f_hi), n_layers)
    theta, fr, pol = frequency_dependent_polar_db(
        model, freqs, family, n_theta=n_theta, pattern_null_db=pattern_null_db
    )
    # Close the circle for a seamless surface
    if abs(theta[0] - (theta[-1] % 360.0)) > 1e-6 and abs(theta[-1] - 360.0) > 1e-6:
        theta = np.concatenate([theta, [360.0]])
        pol = np.concatenate([pol, pol[:, :1]], axis=1)
    elif abs(theta[-1] - 360.0) < 1e-6 or abs(theta[-1] - theta[0]) < 1e-6:
        pass
    else:
        theta = np.concatenate([theta, [theta[0] + 360.0]])
        pol = np.concatenate([pol, pol[:, :1]], axis=1)

    r = _db_to_radius(pol)  # (n_freq, n_theta)
    th_rad = np.deg2rad(theta)
    z = _freq_to_z(fr)

    TH, ZZ = np.meshgrid(th_rad, z)
    RR = r
    X = RR * np.sin(TH)  # 0° → +Y (front), matching N-up polar convention
    Y = RR * np.cos(TH)
    Z = ZZ

    fig = plt.figure(figsize=(9.5, 7.5))
    ax = fig.add_subplot(111, projection="3d")

    if color_by == "radius":
        facecolors = plt.colormaps[colormap](RR)
    else:
        # colour by height / frequency (normalised across layers)
        zn = (Z - Z.min()) / max(Z.max() - Z.min(), 1e-12)
        facecolors = plt.colormaps[colormap](zn)

    surf = ax.plot_surface(
        X,
        Y,
        Z,
        facecolors=facecolors,
        linewidth=0.05,
        antialiased=True,
        shade=False,
        rstride=1,
        cstride=1,
        alpha=0.92,
    )
    # subtle wireframe overlay for structure
    ax.plot_wireframe(
        X, Y, Z, rstride=max(n_layers // 8, 1), cstride=max(n_theta // 12, 1),
        color="k", linewidth=0.15, alpha=0.25,
    )

    ax.set_xlabel("X (sin θ · radius)")
    ax.set_ylabel("Y (cos θ · radius) — 0° front")
    ax.set_zlabel("log₁₀ frequency")

    # Frequency tick labels on Z
    z_ticks_hz = np.array([20, 63, 125, 250, 1000, 4000, 16000], dtype=float)
    z_ticks_hz = z_ticks_hz[(z_ticks_hz >= f_lo) & (z_ticks_hz <= f_hi)]
    ax.set_zticks(_freq_to_z(z_ticks_hz))
    ax.set_zticklabels([f"{int(h)}" if h < 1000 else f"{h/1000:g}k" for h in z_ticks_hz])

    lim = 1.05
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_zlim(_freq_to_z(np.array([f_lo]))[0], _freq_to_z(np.array([f_hi]))[0])

    ax.view_init(elev=22, azim=-60)
    ax.set_title(
        f"{title}\n[{honesty}] 3D polar solid — height=freq (log), radius=|H| "
        f"({f_lo:g}–{f_hi/1000:g} kHz)",
        fontsize=11,
        pad=12,
    )

    # colourbar for frequency
    sm = cm.ScalarMappable(
        cmap=plt.colormaps[colormap],
        norm=plt.Normalize(vmin=np.log10(f_lo), vmax=np.log10(f_hi)),
    )
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.55, pad=0.08, aspect=18)
    cbar.set_label("Frequency (Hz)")
    cbar_ticks = _freq_to_z(z_ticks_hz)
    cbar.set_ticks(cbar_ticks)
    cbar.set_ticklabels([f"{int(h)}" if h < 1000 else f"{h/1000:g}k" for h in z_ticks_hz])

    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def plot_polar_rings(
    out_path: Path,
    title: str,
    model: MicShelfModel,
    family: str,
    honesty: str,
    ring_freqs: Sequence[float] = RING_FREQS,
    n_theta: int = 361,
    pattern_null_db: float = -18.0,
    dpi: int = 140,
) -> Path:
    """Wireframe stacked rings at discrete frequencies (63…16k)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    freqs = np.asarray(ring_freqs, dtype=float)
    theta, fr, pol = frequency_dependent_polar_db(
        model, freqs, family, n_theta=n_theta, pattern_null_db=pattern_null_db
    )
    r = _db_to_radius(pol)
    th_rad = np.deg2rad(theta)
    z = _freq_to_z(fr)

    fig = plt.figure(figsize=(9.5, 7.5))
    ax = fig.add_subplot(111, projection="3d")
    cmap = plt.colormaps["plasma"]
    colors = cmap(np.linspace(0.1, 0.95, len(fr)))

    for i, (f, row, zi, col) in enumerate(zip(fr, r, z, colors)):
        x = row * np.sin(th_rad)
        y = row * np.cos(th_rad)
        zz = np.full_like(x, zi)
        ax.plot(x, y, zz, color=col, lw=2.0, label=_freq_label(f))
        # light fill spokes at 0/90/180/270 for orientation
        if i == len(fr) - 1 or i == 0:
            for ang in (0, 90, 180, 270):
                j = int(round(ang / 360.0 * (len(theta) - 1)))
                ax.plot([0, x[j]], [0, y[j]], [zi, zi], color=col, lw=0.6, alpha=0.5)

    ax.set_xlabel("X (sin θ · radius)")
    ax.set_ylabel("Y (cos θ · radius) — 0° front")
    ax.set_zlabel("log₁₀ frequency")
    z_ticks_hz = np.asarray(ring_freqs, dtype=float)
    ax.set_zticks(_freq_to_z(z_ticks_hz))
    ax.set_zticklabels([_freq_label(h) for h in z_ticks_hz])
    lim = 1.05
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.view_init(elev=22, azim=-60)
    ax.set_title(
        f"{title}\n[{honesty}] stacked polar rings (0 dB peak / freq)",
        fontsize=11,
        pad=12,
    )
    ax.legend(loc="upper left", fontsize=8, title="freq", framealpha=0.85)
    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def _freq_label(f: float) -> str:
    if f >= 1000:
        return f"{f / 1000:g} kHz"
    return f"{f:g} Hz"
