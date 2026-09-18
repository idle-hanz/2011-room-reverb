#!/usr/bin/env python3
"""Generate print-friendly PNGs for HOW_IT_WORKS_ILLUSTRATED (2011 Room Reverb, FastAPI edition)."""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch, Arc, Wedge
import numpy as np

OUT = Path(__file__).resolve().parent / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

C = {
    "bg": "#FFFFFF", "ink": "#1A1A1A", "muted": "#555555",
    "room": "#E8EEF4", "room_edge": "#2C4A6E",
    "source": "#C0392B", "mic": "#1F7A4C", "mic_l": "#1A6B9A", "mic_r": "#8B5A00", "mic_c": "#1F7A4C",
    "prepare": "#D6EAF8", "reflect": "#D5F5E3", "dist": "#FCF3CF",
    "absorb": "#FADBD8", "sound": "#E8DAEF", "fdn": "#F5CBA7", "mix": "#D5DBDB",
    "dry": "#AEB6BF", "image": "#7D3C98", "arrow": "#2C3E50",
    "verified": "#196F3D", "assumed": "#B9770E", "ui": "#5B2C6F",
    "grid": "#B0BEC5",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "figure.facecolor": C["bg"], "axes.facecolor": C["bg"],
    "savefig.dpi": 160, "savefig.bbox": "tight", "savefig.facecolor": C["bg"],
})


def save(fig, name: str):
    fig.savefig(OUT / name, dpi=160, bbox_inches="tight", facecolor=C["bg"])
    plt.close(fig)
    print("wrote", name)


def box(ax, xy, w, h, text, fc, fs=9):
    x, y = xy
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                linewidth=1.4, edgecolor=C["ink"], facecolor=fc))
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs, fontweight="bold",
            color=C["ink"], multialignment="center")


def arrow(ax, a, b):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=C["arrow"], lw=1.6, mutation_scale=14))


def diagram_signal_flow():
    fig, ax = plt.subplots(figsize=(13, 4.2))
    ax.set_xlim(0, 15); ax.set_ylim(0, 4.5); ax.axis("off")
    ax.set_title("Signal flow — FastAPI tweak app (early field + unscaled Hadamard FDN)", fontweight="bold")
    steps = [
        (0.3, "Dry\nWAV", C["dry"]),
        (2.2, "Geometry\nPrepare", C["prepare"]),
        (4.3, "Image\nsources", C["reflect"]),
        (6.4, "Mic\npatterns", C["sound"]),
        (8.5, "Surfaces\nA–F", C["absorb"]),
        (10.5, "Hadamard\nFDN", C["fdn"]),
        (12.6, "Mix +\nFFT conv", C["mix"]),
    ]
    for x, t, fc in steps:
        box(ax, (x, 1.5), 1.7, 1.5, t, fc, 8)
    for i in range(len(steps)-1):
        arrow(ax, (steps[i][0]+1.7, 2.25), (steps[i+1][0], 2.25))
    ax.text(7.5, 0.55, "Early wet ──► mixer   ·   Early taps also excite FDN   ·   Hadamard N scales images + FDN lines",
            ha="center", fontsize=9, color=C["muted"])
    ax.text(8.5, 3.55, "ASSUMED", color=C["assumed"], fontsize=8, fontweight="bold")
    ax.text(10.5, 3.55, "unscaled ±1", color=C["verified"], fontsize=8, fontweight="bold")
    save(fig, "01_signal_flow.png")


def diagram_room_floor_side():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    # Floor
    ax = axes[0]
    ax.set_xlim(0, 6); ax.set_ylim(0, 8); ax.set_aspect("equal")
    ax.add_patch(Rectangle((0,0), 6, 8, facecolor=C["room"], edgecolor=C["room_edge"], lw=2))
    ax.plot(3.0, 4.8, "o", color=C["source"], ms=12); ax.text(3.15, 5.05, "Src", color=C["source"], fontweight="bold")
    ax.plot(3.0, 1.5, "s", color=C["mic"], ms=10); ax.text(3.2, 1.2, "Mic", color=C["mic"], fontweight="bold")
    ax.plot([2.7, 3.3], [1.5, 1.5], "-", color=C["mic_l"], lw=3)
    ax.set_xlabel("X (W)"); ax.set_ylabel("Z (L)"); ax.set_title("Floor — drag Src / Mic (metres)")
    ax.grid(True, alpha=0.3)
    # Side
    ax = axes[1]
    ax.set_xlim(0, 8); ax.set_ylim(0, 3.2); ax.set_aspect("equal")
    ax.add_patch(Rectangle((0,0), 8, 3, facecolor=C["room"], edgecolor=C["room_edge"], lw=2))
    ax.plot(4.8, 2.1, "o", color=C["source"], ms=12); ax.text(5.0, 2.3, "sy (Src H)", color=C["source"], fontsize=9)
    ax.plot(1.5, 1.5, "s", color=C["mic"], ms=10); ax.text(1.7, 1.7, "my (Mic H)", color=C["mic"], fontsize=9)
    ax.annotate("", xy=(4.8, 2.1), xytext=(4.8, 0), arrowprops=dict(arrowstyle="<->", color=C["source"]))
    ax.annotate("", xy=(1.5, 1.5), xytext=(1.5, 0), arrowprops=dict(arrowstyle="<->", color=C["mic"]))
    ax.set_xlabel("Z (L)"); ax.set_ylabel("Y (H)"); ax.set_title("Side — sy independent of my")
    ax.grid(True, alpha=0.3)
    fig.suptitle("Placement: Floor XZ + Side heights (Link heights optional)", fontweight="bold")
    save(fig, "07_floor_side_heights.png")


def diagram_image_mirrors():
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.set_xlim(-6, 12); ax.set_ylim(-6, 12); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Image-source mirrors (plan sketch)", fontweight="bold")
    for i in range(-1, 2):
        for j in range(-1, 2):
            x0, z0 = i*6, j*8
            ax.add_patch(Rectangle((x0, z0), 6, 8, fill=False, edgecolor="#B0BEC5", lw=1, ls="--"))
    ax.add_patch(Rectangle((0, 0), 6, 8, facecolor=C["room"], edgecolor=C["room_edge"], lw=2))
    ax.plot(3, 5, "o", color=C["source"], ms=10)
    for i in range(-1, 2):
        for j in range(-1, 2):
            if i == 0 and j == 0: continue
            sx = (2*i*6 + 3) if i % 2 == 0 else (2*i*6 + (6-3))
            # simpler mirror dots
            ax.plot(3 + 2*i*6, 5 + 2*j*8, "o", color=C["image"], ms=7, alpha=0.7)
    ax.plot(3, 1.5, "s", color=C["mic"], ms=9)
    ax.text(3, -1.2, "Purple = image sources · Green = mic · Red = real source", ha="center", color=C["muted"], fontsize=9)
    save(fig, "03_image_mirrors.png")


def diagram_prepare_mcz():
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis("off")
    ax.set_title("Prepare lock — MCZ = L − MZ (VERIFIED)", fontweight="bold")
    ax.add_patch(Rectangle((1, 0.8), 7, 2.2, facecolor=C["room"], edgecolor=C["room_edge"], lw=2))
    ax.annotate("", xy=(8, 0.8), xytext=(1, 0.8), arrowprops=dict(arrowstyle="<->", color=C["ink"]))
    ax.text(4.5, 0.45, "L (depth)", ha="center")
    ax.plot(2.2, 1.5, "s", color=C["mic"], ms=12)
    ax.plot(6.5, 2.2, "o", color=C["source"], ms=12)
    ax.text(2.2, 2.55, "Mic near front\nMZ from front wall", ha="center", fontsize=8, color=C["mic"])
    ax.text(7.3, 3.2, "MCZ = L − MZ", fontsize=11, fontweight="bold", color=C["verified"])
    ax.text(7.3, 2.75, "c = 340 m/s", fontsize=10, color=C["verified"])
    save(fig, "04_prepare_algebra.png")


def diagram_fdn():
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.set_xlim(0, 12); ax.set_ylim(0, 5); ax.axis("off")
    ax.set_title("Unscaled Hadamard FDN — N lines, ±1 matrix, ×g (no 1/√N)", fontweight="bold")
    for i in range(6):
        y = 4.2 - i*0.55
        ax.plot([1, 4], [y, y], color=C["ink"], lw=2)
        ax.plot(1, y, "o", color=C["reflect"], ms=8)
        ax.text(0.35, y, f"d{i+1}", va="center", fontsize=8)
    box(ax, (4.5, 1.5), 2.4, 2.2, "Hadamard\n±1\nunscaled", C["fdn"], 9)
    box(ax, (7.4, 1.8), 1.6, 1.6, "× g", C["dist"], 12)
    box(ax, (9.5, 1.8), 1.8, 1.6, "to\nmix", C["mix"], 10)
    arrow(ax, (4.0, 2.6), (4.5, 2.6)); arrow(ax, (6.9, 2.6), (7.4, 2.6)); arrow(ax, (9.0, 2.6), (9.5, 2.6))
    ax.text(6, 0.6, "Early image taps inject into lines · N (8–128) matches image lattice size", ha="center", color=C["muted"])
    save(fig, "05_fdn_schematic.png")


def diagram_mic_desk():
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    # top
    ax = axes[0]; ax.set_aspect("equal"); ax.set_xlim(-0.3, 0.3); ax.set_ylim(-0.3, 0.3)
    ax.set_title("Mic desk — top")
    ax.add_patch(Circle((0,0), 0.04, color=C["mic_c"]))
    ax.add_patch(Circle((-0.12, 0.02), 0.035, color=C["mic_l"]))
    ax.add_patch(Circle((0.12, 0.02), 0.035, color=C["mic_r"]))
    for ang, col, lab in [(-25, C["mic_l"], "L"), (0, C["mic_c"], "C"), (25, C["mic_r"], "R")]:
        rad = np.radians(ang)
        ax.arrow(0, 0, 0.18*np.sin(rad), 0.18*np.cos(rad), head_width=0.03, color=col, length_includes_head=True)
        ax.text(0.22*np.sin(rad), 0.22*np.cos(rad), lab, color=col, fontweight="bold")
    ax.set_xticks([]); ax.set_yticks([])
    # polars
    for ax, title, col, width in [
        (axes[1], "Cardioid (side)", C["mic_l"], 1.0),
        (axes[2], "Omni (MS mid)", C["mic_c"], 0.0),
    ]:
        theta = np.linspace(0, 2*np.pi, 200)
        if width < 0.1:
            r = np.ones_like(theta)
        else:
            r = 0.5 * (1 + np.cos(theta))
        ax.plot(r*np.cos(theta), r*np.sin(theta), color=col, lw=2)
        ax.set_aspect("equal"); ax.set_title(title); ax.set_xlim(-1.2, 1.2); ax.set_ylim(-1.2, 1.2)
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(True, alpha=0.25)
    fig.suptitle("Mic desk: stand close-up + per-capsule pattern / yaw (presets: AB XY ORTF NOS DIN MS…)", fontweight="bold")
    save(fig, "08_mic_desk_polars.png")


def diagram_lattice_paths():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    ax = axes[0]
    ax.set_title("Lattice — image grid (concept)")
    xs = ys = zs = []
    pts = []
    for i in range(-1, 2):
        for j in range(0, 2):
            for k in range(-1, 2):
                pts.append((i, j, k))
    # 2D projection
    for x,y,z in pts:
        ax.plot(x+0.4*z, y+0.3*z, "o", color=C["image"], ms=8, alpha=0.8)
    ax.plot(0, 0.5, "o", color=C["source"], ms=12)
    ax.plot(0, 0, "s", color=C["mic"], ms=10)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
    ax = axes[1]
    ax.set_title("Paths — in-room vs last legs")
    ax.add_patch(Rectangle((0,0), 4, 3, fill=False, edgecolor=C["room_edge"], lw=2))
    ax.plot([1, 0, 3.5], [1.5, 3, 0.8], "-", color=C["image"], lw=2, label="folded path")
    ax.plot([3.5, 2.2], [0.8, 0.5], "-", color=C["mic"], lw=3, label="last leg")
    ax.plot(1, 1.5, "o", color=C["source"], ms=10)
    ax.plot(2.2, 0.5, "s", color=C["mic"], ms=10)
    ax.legend(fontsize=8, loc="upper right")
    ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Lattice & Paths tabs", fontweight="bold")
    save(fig, "09_lattice_paths.png")


def diagram_colour_surfaces():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    f = np.array([50,100,200,400,800,1600,3200,6400,12800])
    db = -3*np.log2(f/100) + 2*np.sin(np.log(f))
    ax.semilogx(f, db, color=C["room_edge"], lw=2)
    ax.set_title("Colour — 1/3-octave IR (ASSUMED surfaces)")
    ax.set_xlabel("Hz"); ax.set_ylabel("dB"); ax.grid(True, which="both", alpha=0.3)
    ax = axes[1]
    ax.set_title("Surfaces A–F (ASSUMED cards)")
    ax.axis("off")
    for i, letter in enumerate("ABCDEF"):
        y = 5.2 - i*0.85
        box(ax, (0.5, y), 8, 0.7, f"{letter}   absorb · EQ · diffusion", C["absorb"] if i%2==0 else C["dist"], 9)
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.2)
    fig.suptitle("Colour & Surfaces — tagged ASSUMED (mask writers exist; wall dict not invented)", fontweight="bold")
    save(fig, "10_colour_surfaces.png")


def diagram_polar_field():
    fig = plt.figure(figsize=(8, 5))
    ax = fig.add_subplot(111, projection="3d")
    # simple solid of revolution-ish
    az = np.linspace(0, 2*np.pi, 60)
    fr = np.linspace(0, 1, 20)
    AZ, FR = np.meshgrid(az, fr)
    # cardioid grows with FR
    R = (0.3 + 0.7*FR) * (0.55 + 0.45*np.cos(AZ))
    X = R * np.cos(AZ); Y = R * np.sin(AZ); Z = FR * 2
    ax.plot_surface(X, Y, Z, color="#5DADE2", alpha=0.7, linewidth=0)
    ax.set_title("Polar 3D — pattern × frequency (ASSUMED)")
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("freq→")
    save(fig, "11_polar_field.png")


def diagram_track_fx():
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_xlim(0, 12); ax.set_ylim(0, 5); ax.axis("off")
    ax.set_title("Intended Studio One shape — linked track-FX in one shared room", fontweight="bold")
    box(ax, (0.4, 2.8), 3.2, 1.5, "Shared room editor\n(Desktop / host)", C["prepare"], 9)
    for i, label in enumerate(["Guitar FX", "Vocal FX", "Drum FX"]):
        x = 5 + i*2.3
        box(ax, (x, 2.9), 2.0, 1.3, label + "\ninstance", C["fdn"], 8)
        arrow(ax, (3.6, 3.5), (x, 3.5))
    box(ax, (5.5, 0.6), 5, 1.2, "One room: mics · W/H/L · surfaces\nEach instance = source position", C["mix"], 9)
    ax.text(6, 4.6, "Not shipped as VST yet — architecture target", color=C["ui"], fontsize=9, fontweight="bold")
    save(fig, "12_track_fx_instances.png")


def diagram_direct_vs_image():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_xlim(0, 8); ax.set_ylim(0, 4); ax.set_aspect("equal")
    ax.add_patch(Rectangle((1,0.5), 5, 3, facecolor=C["room"], edgecolor=C["room_edge"], lw=2))
    ax.plot(2, 2, "o", color=C["source"], ms=12)
    ax.plot(5, 1.2, "s", color=C["mic"], ms=10)
    ax.plot([2, 5], [2, 1.2], "--", color=C["muted"], lw=1.5, label="Direct (may be 2D XZ readout)")
    ax.plot([2, 1, 5], [2, 3.5, 1.2], "-", color=C["image"], lw=2, label="Image path (3D delay)")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Direct readout vs image delay paths (VERIFIED distinction)")
    ax.set_xticks([]); ax.set_yticks([])
    save(fig, "06_direct_vs_image_distance.png")


def diagram_room_geometry():
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_xlim(-0.5, 6.5); ax.set_ylim(-0.5, 8.5); ax.set_aspect("equal")
    ax.add_patch(Rectangle((0,0), 6, 8, facecolor=C["room"], edgecolor=C["room_edge"], lw=2))
    ax.plot(3, 4.5, "o", color=C["source"], ms=12, label="Source")
    ax.plot(2.7, 1.5, "s", color=C["mic_l"], ms=9, label="L")
    ax.plot(3.0, 1.5, "s", color=C["mic_c"], ms=9, label="C")
    ax.plot(3.3, 1.5, "s", color=C["mic_r"], ms=9, label="R")
    ax.set_xlabel("X = W"); ax.set_ylabel("Z = L")
    ax.set_title("Room geometry XZ (corner origin)")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    save(fig, "02_room_geometry_xz.png")


def main():
    diagram_signal_flow()
    diagram_room_geometry()
    diagram_image_mirrors()
    diagram_prepare_mcz()
    diagram_fdn()
    diagram_direct_vs_image()
    diagram_room_floor_side()
    diagram_mic_desk()
    diagram_lattice_paths()
    diagram_colour_surfaces()
    diagram_polar_field()
    diagram_track_fx()
    print("done →", OUT)


if __name__ == "__main__":
    main()
