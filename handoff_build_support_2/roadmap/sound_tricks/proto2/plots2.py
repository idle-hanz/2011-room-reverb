import json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
r = json.load(open("a2_results.json")); OUT = "/workspace/build_support_2/roadmap/sound_tricks/"
OCT = [125, 250, 500, 1000, 2000, 4000, 8000]
def fcol(f, lo=125.0):   # red (lowest band shown) -> violet (8 kHz), log frequency
    h = np.clip(np.log(f / lo) / np.log(8000 / lo), 0, 1) * 0.78
    return plt.cm.hsv(h)
def fx(ax, lo=40, hi=10000):
    ax.set_xscale("log"); ax.set_xticks([63, 125, 250, 500, 1000, 2000, 4000, 8000]); ax.set_xticklabels(["63", "125", "250", "500", "1k", "2k", "4k", "8k"])
    ax.set_xticks([], minor=True); ax.set_xlim(lo, hi); ax.grid(alpha=0.3)
# ---------- Figure 1: how the pieces come together + auto-treat result
fig = plt.figure(figsize=(15, 6.2))
ax = fig.add_axes([0.01, 0.04, 0.47, 0.86]); ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
def box(x, y, w, h, t, c):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", fc=c, ec="0.25", lw=1))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8.2)
def arr(x0, y0, x1, y1): ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="->", lw=1.2, color="0.2"))
# column 1: inputs; column 2: physics; column 3: engine
box(0.1, 8.0, 2.9, 1.6, "SURFACES table\nmaterial per face (alpha by band)\n+ broadband porous panels\n(depth, air gap, coverage)", "#f3efe2")
box(0.1, 5.7, 2.9, 1.7, "Detected resonances\n(EQ_PLAN, Render IR, <= 4)\n+ room modes, Schroeder f\n-> AUTO-TREAT suggests\nmembrane / Helmholtz panels", "#e6f0e6")
box(0.1, 3.4, 2.9, 1.7, "Target (Makivirta, EQ_PLAN)\nflat mid T, +0.2 s below 300 Hz\nEBU 3276 / BS.1116 tolerance\n(used to size the panels)", "#e6f0e6")
box(0.1, 1.1, 2.9, 1.7, "Face EQ (tone)\nper face, before the FDN\ncuts also count as loss\n(no boosts in the loop)", "#e8eef8")
box(3.6, 8.0, 2.9, 1.6, "alpha(f) per face\nbase + porous + panels\n(area-weighted), random\n-> specular conversion", "#f3efe2")
box(3.6, 5.7, 2.9, 1.7, "Room T(f) from physics\nEyring / Arau blend by\nscattering + ISO 9613 air\n(shown in 'Room result')", "#f8e8e8")
box(3.6, 3.4, 2.9, 1.7, "Per-line decay rates\nfaces each line's image path\nhits (directional), scattered\nshare >= 0.5 room average", "#f8e8e8")
box(3.6, 1.1, 2.9, 1.7, "One Render calibration\nmeasure T20 per octave,\nscale rates, redesign\n(engine vs model only)", "#f8e8e8")
box(7.1, 5.4, 2.8, 2.6, "Attenuation filter\nper FDN line, 3 biquads\n(shelf + 2 peaks), fits\nrate x delay, folds the\naxis cuts, stability guard", "#efe6f6")
box(7.1, 1.1, 2.8, 2.9, "FDN loop (3 x 32 lines)\nHadamard mix\n-> tail decay per band\n(plot on the right)\n+ mic / source directivity", "#eeeeee")
arr(3.0, 8.8, 3.6, 8.8)        # surfaces -> alpha
arr(3.0, 6.55, 3.6, 8.3)       # auto-treat panels -> alpha
arr(1.55, 5.1, 1.55, 5.7)      # target -> auto-treat
arr(5.05, 8.0, 5.05, 7.4)      # alpha -> room T
arr(5.05, 5.7, 5.05, 5.1)      # room T -> per-line
arr(3.0, 1.95, 3.6, 3.9)       # face EQ -> per-line (loss)
arr(6.5, 4.25, 7.1, 5.9)       # per-line -> attenuation filter
arr(8.5, 5.4, 8.5, 4.0)        # filter -> loop
arr(7.1, 2.0, 6.5, 2.0)        # loop -> calibration
arr(5.05, 2.8, 5.05, 3.4)      # calibration -> per-line
ax.text(5, 9.95, "How the pieces come together (Render prototype; Play uses the same filters)", ha="center", fontsize=10, weight="bold")
ax2 = fig.add_axes([0.55, 0.12, 0.43, 0.76])
tg = None
import sys; sys.path.insert(0, "."); sys.path.insert(0, "/workspace/st_work/proto")
TH = 1000.0 * 2.0 ** (np.arange(-13, 10) / 3.0)
for nm, lab, ls in (("g5_untreated_cal", "untreated (plaster + parquet)", ":"), ("g5_broadband_cal", "broadband panels only", "--"), ("g5_treated_cal", "auto-treated (broadband + 4 tuned panels)", "-")):
    if nm not in r: continue
    y = np.array(r[nm]["T20_third"], float)
    ax2.plot(TH, y, ls=ls, color="0.2", lw=1.3, label=lab)
    ax2.scatter(TH, y, c=[fcol(f, 50.0) for f in TH], s=28, edgecolor="k", lw=0.4, zorder=3)
tgt = json.load(open("target_treated.json"))
ft, t = np.array(tgt["f"]), np.array(tgt["T"])
ax2.fill_between(ft, t * 0.9, t * 1.1, color="0.6", alpha=0.25, label="Makivirta target +/-10 %")
ax2.plot(ft, t, color="0.4", lw=1.5, ls="-.")
for f0 in [p["f0"] for p in tgt["plan"] if p.get("kind") in ("membrane", "helmholtz")]:
    ax2.axvline(f0, color="0.5", lw=0.8, ls=(0, (2, 3))); ax2.text(f0, 7.3, f"{f0:.0f}", fontsize=7, ha="center", rotation=90, va="bottom", bbox=dict(fc="white", ec="none", pad=0.5))
ax2.set_yscale("log"); ax2.set_ylim(0.3, 9); ax2.set_yticks([], minor=True); ax2.set_yticks([0.4, 0.6, 0.8, 1, 1.5, 2, 3, 5, 8]); ax2.set_yticklabels(["0.4", "0.6", "0.8", "1", "1.5", "2", "3", "5", "8"])
fx(ax2, 45, 9500); from matplotlib.ticker import NullLocator, NullFormatter; ax2.yaxis.set_minor_locator(NullLocator()); ax2.yaxis.set_minor_formatter(NullFormatter()); ax2.set_xlabel("1/3-octave band (Hz)"); ax2.set_ylabel("decay time T20 (s), rendered")
ax2.set_title("Decay per band: untreated vs auto-treated (6 x 3 x 8 m)\ndot colour = band, red low to violet high; dotted lines = panel tunings (Hz)", fontsize=9.5)
ax2.legend(fontsize=8, loc="lower left")
fig.savefig(OUT + "surfaces_in_loop_overview.png", dpi=110); plt.close(fig)
# ---------- Figure 2: material contrast + CR2
fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))
for a, room, title in ((axs[0], "studio", "Carpeted, panelled studio room"), (axs[1], "brick", "Bare brick / plaster room")):
    tg = r[f"g4_{room}_avg"]["target"]
    a.plot(OCT, tg, color="0.4", lw=2, ls="--", label="target from Surfaces")
    for nm, lab, ls in ((f"g4_{room}_flat", "Flat (2011)", ":"), (f"g4_{room}_avg_cal", "room average", "-"), (f"g4_{room}_dir_cal", "directional", "-.")):
        if nm not in r: continue
        y = r[nm]["T20"]; a.plot(OCT, y, color="0.15", lw=1, ls=ls, label=lab)
        a.scatter(OCT, y, c=[fcol(f) for f in OCT], s=40, edgecolor="k", lw=0.4, zorder=3)
    fx(a, 90, 11000); a.set_title(title, fontsize=10); a.set_xlabel("octave band (Hz)"); a.legend(fontsize=7.5)
axs[0].set_ylabel("T20 (s), rendered")
a = axs[2]; meas = [1.34, 1.72, 2.00, 1.94, 1.74, 1.54, 1.11]
a.plot(OCT, meas, color="k", lw=2.2, label="BRAS CR2 measured T20")
a.plot(OCT, r["cr2_avg"]["target"], color="0.45", lw=1.6, ls="--", label="model target (BRAS materials)")
for nm, lab, ls in (("cr2_flat", "Flat (2011)", ":"), ("cr2_avg_cal", "room average", "-"), ("cr2_dir_cal", "directional", "-.")):
    if nm not in r: continue
    y = r[nm]["T20"]; a.plot(OCT, y, color="0.2", lw=1, ls=ls, label=lab)
    a.scatter(OCT, y, c=[fcol(f) for f in OCT], s=40, edgecolor="k", lw=0.4, zorder=3)
fx(a, 90, 11000); a.set_title("Accuracy vs a measured room (BRAS CR2, CC BY-SA 4.0)", fontsize=10); a.set_xlabel("octave band (Hz)"); a.legend(fontsize=7.5)
fig.suptitle("Surfaces in the loop: changing materials changes the decay per band. Dot colour = band, red low to violet high", fontsize=10)
fig.tight_layout(); fig.savefig(OUT + "surfaces_in_loop_rooms.png", dpi=110)
