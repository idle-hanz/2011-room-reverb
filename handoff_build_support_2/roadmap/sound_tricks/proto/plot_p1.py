import json, numpy as np, matplotlib, matplotlib.ticker
matplotlib.use("Agg"); import matplotlib.pyplot as plt
r = json.load(open("p1_results.json")); B = [125, 250, 500, 1000, 2000, 4000, 8000]
cols = plt.cm.rainbow_r(np.linspace(0.0, 1.0, 7))   # rainbow_r: index 0 = red (low) ... 1 = violet (high)
cols = [plt.cm.hsv(h) for h in np.linspace(0.0, 0.78, 7)]  # hue 0 red -> 0.78 violet
fig, ax = plt.subplots(1, 3, figsize=(13, 4.4), sharey=True)
names = [("A_today", "A  today (flat, broadband only)"), ("B1_air", "B1  air in the loop"), ("B2_air_materials", "B2  air + surface cards (bass capped 1.25x)")]
for a, (k, title) in zip(ax, names):
    d = r[k]
    a.plot(B, d["target"], color="0.35", lw=2, ls="--", label="target (Eyring + ISO 9613 air)")
    a.plot(B, d["T30"], color="0.15", lw=1, label="measured T30 (Render)")
    for i, fc in enumerate(B):
        a.scatter([fc], [d["T30"][i]], s=70, color=cols[i], edgecolor="k", zorder=3)
        a.annotate(f"{d['err_pct'][i]:+.0f}%", (fc, d["T30"][i]), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=8)
    a.set_xscale("log"); a.xaxis.set_minor_locator(matplotlib.ticker.NullLocator()); a.set_xticks(B); a.set_xticklabels(["125", "250", "500", "1k", "2k", "4k", "8k"]); a.set_xticks([], minor=True)
    a.set_title(title, fontsize=10); a.set_xlabel("octave band (Hz)"); a.grid(alpha=0.3); a.set_ylim(0, 2.6)
ax[0].set_ylabel("decay time T30 (s)"); ax[0].legend(fontsize=8, loc="lower left")
fig.suptitle("Natural decay prototype: default 6x3x8 m room, dial 1.8 s, ORTF (C off). Dot colour = band, red low to violet high. Labels = error vs target.", fontsize=10)
fig.tight_layout(); fig.savefig("/workspace/build_support_2/roadmap/sound_tricks/natural_decay_T30.png", dpi=110)
