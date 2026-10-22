import json, os, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
from ism2d import room, tree, backtrace
BG, PANEL, PANEL2, BORDER, TEXT, MUTED, FAINT = "#0b0c10", "#13151b", "#191c25", "#2a2f3d", "#e9ecf3", "#8b93a8", "#5c6478"
ACC, SRC, MIC, DANGER, VIOLET = "#2dd4bf", "#fbbf24", "#60a5fa", "#f472b6", "#a78bfa"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": TEXT, "axes.labelcolor": TEXT, "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": BORDER, "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG})
OUT = os.path.join(os.path.dirname(__file__), "..", "diagrams")
POLY = [(-2, 0), (2, 0), (3, 6), (-3, 6)]
NAMES = ["Front", "Right", "Rear", "Left"]
S = np.array((-1.2, 0.8)); M = np.array((0.0, 3.2))
W = room(POLY)

# ---------- 1. branch tree ----------
def fig_tree():
    nodes = tree(S, W, 3)
    aud = {}
    for i in range(len(nodes)):
        aud[i] = True if i == 0 else (not nodes[i]["pruned"] and backtrace(nodes, i, M, W)[0])
    kids = {i: [j for j in range(len(nodes)) if nodes[j]["parent"] == i] for i in range(len(nodes))}
    fig, ax = plt.subplots(figsize=(15, 7.6)); ax.set_facecolor(BG); ax.axis("off")
    ax.set_xlim(-2.2, 12.5); ax.set_ylim(-0.75, 6.6)
    ys = {0: 5.6, 1: 3.7, 2: 1.6}
    order1 = kids[0]; xs = {0: 6.0}
    for a, n1 in enumerate(order1):
        xs[n1] = 1.5 + a * 3.0
        for b, n2 in enumerate(kids[n1]):
            xs[n2] = xs[n1] - 1.0 + b * 1.0
    def style(i):
        n = nodes[i]
        if n["pruned"]: return DANGER, (0, (3, 2)), "pruned"
        return (ACC, "-", "audible") if aud[i] else (MUTED, "-", "hidden")
    def box(i):
        n = nodes[i]; lvl = len(n["seq"]); x, y = xs[i], ys[lvl]
        col, ls, kind = style(i)
        w = 2.0 if lvl < 2 else 0.86; h = 0.62 if lvl < 2 else 0.95
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=PANEL2 if kind != "audible" else "#0f2a2a", ec=col, lw=1.8, ls=ls))
        if lvl == 0: label = "S (source)"
        elif lvl == 1: label = NAMES[n["seq"][0]]
        else: label = "\n".join(NAMES[g] for g in n["seq"])
        ax.text(x, y, label, ha="center", va="center", fontsize=10.5 if lvl < 2 else 8.6, color=TEXT, linespacing=1.15)
        if lvl == 2:
            # order-3 summary under each order-2 node
            k3 = kids[i]; na = sum(aud[j] for j in k3)
            if n["pruned"]:
                t, c = "3 skipped", DANGER
            else:
                t, c = f"3 kids\n{na} audible", (ACC if na else MUTED)
            ax.text(x, y - 0.95, t, ha="center", va="top", fontsize=7.6, color=c, linespacing=1.1)
            ax.plot([x, x], [y - h / 2, y - 0.86], color=FAINT, lw=0.9)
    for i in range(len(nodes)):
        if len(nodes[i]["seq"]) > 2: continue
        for j in kids[i]:
            if len(nodes[j]["seq"]) > 2: continue
            lvl = len(nodes[i]["seq"])
            h0 = 0.62 if lvl < 2 else 0.95; h1 = 0.62 if lvl + 1 < 2 else 0.95
            ax.plot([xs[i], xs[j]], [ys[lvl] - h0 / 2, ys[lvl + 1] + h1 / 2], color=BORDER, lw=1.3, zorder=0)
    for i in range(len(nodes)):
        if len(nodes[i]["seq"]) <= 2: box(i)
    # side labels
    for lvl, txt in [(0, "order 0\n1 image"), (1, "order 1\nN = 4"), (2, "order 2\nN(N-1) = 12")]:
        ax.text(-2.1, ys[lvl], txt, ha="left", va="center", fontsize=10, color=MUTED)
    ax.text(-2.1, 0.45, "order 3\nN(N-1)² = 36", ha="left", va="center", fontsize=10, color=MUTED)
    ax.text(5.15, 6.45, "Image-source tree, one branch per face (2D splayed control room, 4 walls, mic at the mix position)", ha="center", fontsize=13.5, color=TEXT, weight="bold")
    ax.text(5.15, 6.08, "A face never reflects twice in a row, so each node has N-1 children: order k has N(N-1)^(k-1) candidates, total 1 + sum over k", ha="center", fontsize=10.5, color=MUTED)
    ly = -0.45
    for lx, col, ls, t in [(-2.0, ACC, "-", "audible at this mic\n(passes the backward check)"), (2.4, MUTED, "-", "hidden at this mic: keep it,\nits children may still be audible"), (7.4, DANGER, (0, (3, 2)), "pruned: parent is behind the face,\nthe whole branch can never be real")]:
        ax.add_patch(FancyBboxPatch((lx, ly - 0.13), 0.42, 0.26, boxstyle="round,pad=0.01,rounding_size=0.06", fc=PANEL2, ec=col, lw=1.6, ls=ls))
        ax.text(lx + 0.6, ly, t, va="center", fontsize=9.5, color=TEXT, linespacing=1.15)
    fig.savefig(os.path.join(OUT, "D1_branch_tree.png"), dpi=130, bbox_inches="tight", pad_inches=0.25); plt.close(fig)

# ---------- 2. backward validity check ----------
def draw_room(ax):
    ax.add_patch(Polygon(POLY, closed=True, fc=PANEL2, ec="none", zorder=0))
    for w, nm in zip(W, NAMES):
        ax.plot(*zip(w.a, w.b), color=TEXT, lw=2.4, zorder=2, solid_capstyle="round")
        # dotted extension of each wall line
        t = (w.b - w.a) / np.linalg.norm(w.b - w.a)
        for p, sgn in [(w.a, -1), (w.b, 1)]:
            ax.plot(*zip(p, p + sgn * t * 3.2), color=FAINT, lw=1.0, ls=(0, (2, 3)), zorder=1)
    lab = {"Front": (0.9, -0.38), "Right": (2.95, 2.0), "Rear": (0, 6.35), "Left": (-2.95, 2.0)}
    for nm, (x, y) in lab.items():
        ax.text(x, y, nm + " wall", ha="center", va="center", fontsize=9.5, color=MUTED, rotation={"Right": 80.5, "Left": -80.5}.get(nm, 0), zorder=3, bbox=dict(fc=PANEL, ec="none", pad=1.0))
    ax.plot(*S, marker="s", ms=11, color=SRC, zorder=6); ax.text(S[0] - 0.25, S[1] + 0.28, "S", color=SRC, fontsize=12, weight="bold", ha="right", zorder=6)
    ax.plot(*M, marker="o", ms=11, color=MIC, zorder=6); ax.text(M[0] + 0.28, M[1] + 0.12, "Mic", color=MIC, fontsize=12, weight="bold", zorder=6)

def fig_backtrace():
    nodes = tree(S, W, 2)
    find = lambda seq: next(i for i, n in enumerate(nodes) if tuple(NAMES[g] for g in n["seq"]) == seq)
    iv, ix = find(("Front", "Right")), find(("Front", "Left"))
    fig, axs = plt.subplots(1, 2, figsize=(15, 8.4))
    XL, YL = (-4.2, 6.6), (-3.5, 7.7)
    for ax in axs:
        ax.set_aspect("equal"); ax.set_facecolor(PANEL); ax.set_xticks([]); ax.set_yticks([])
        ax.set_xlim(*XL); ax.set_ylim(*YL)
        for sp in ax.spines.values(): sp.set_color(BORDER)
        draw_room(ax)
    box = lambda ec: dict(boxstyle="round,pad=0.35", fc=BG, ec=ec, lw=1.0)
    # valid
    ax = axs[0]
    ok, pts, _ = backtrace(nodes, iv, M, W); assert ok
    I1 = nodes[nodes[iv]["parent"]]["pos"]; I2 = nodes[iv]["pos"]
    ax.plot(*zip(M, I2), color=ACC, lw=1.2, ls=(0, (5, 4)), alpha=0.8, zorder=3)
    ax.plot(*zip(pts[1], I1), color=ACC, lw=1.2, ls=(0, (5, 4)), alpha=0.8, zorder=3)
    for a_, b_ in zip(pts[:-1], pts[1:]):
        ax.annotate("", xy=b_, xytext=a_, arrowprops=dict(arrowstyle="-|>", color=ACC, lw=2.4, mutation_scale=16), zorder=5)
    for q in pts[1:-1]:
        ax.plot(*q, marker="o", ms=7, color=ACC, zorder=7)
    ax.plot(*I1, marker="s", ms=10, mfc="none", mec=SRC, mew=1.8, zorder=6)
    ax.text(I1[0] - 0.2, I1[1] - 0.4, "image I1\n(S mirrored in Front)", color=SRC, fontsize=9, ha="center", va="top")
    ax.plot(*I2, marker="s", ms=10, mfc="none", mec=SRC, mew=1.8, zorder=6)
    ax.text(I2[0], I2[1] - 0.4, "image I2\n(I1 mirrored in Right)", color=SRC, fontsize=9, ha="center", va="top")
    ax.annotate("1  line Mic to I2 crosses the Right\n    wall inside its outline", xy=pts[1], xytext=(3.55, 3.9), color=TEXT, fontsize=9.5, ha="left", va="center", bbox=box(ACC), arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9), zorder=8)
    ax.annotate("2  from that point, the line to I1\n    crosses the Front wall inside", xy=pts[2], xytext=(0.2, -2.75), color=TEXT, fontsize=9.5, ha="left", va="center", bbox=box(ACC), arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9), zorder=8)
    ax.text(XL[0] + 0.2, 7.5, "VALID: Front then Right (2nd order)", color=ACC, fontsize=13, weight="bold", va="top")
    ax.text(XL[0] + 0.2, 7.0, "3  from the Front-wall point to S is clear, so the path is real", color=MUTED, fontsize=10, va="top")
    # occluded
    ax = axs[1]
    ok, pts, fail = backtrace(nodes, ix, M, W); assert not ok and fail[0] == "outline"
    I1 = nodes[nodes[ix]["parent"]]["pos"]; I2 = nodes[ix]["pos"]; q = fail[2]
    ax.plot(*zip(M, I2), color=DANGER, lw=1.2, ls=(0, (5, 4)), alpha=0.9, zorder=3)
    ax.annotate("", xy=q, xytext=M, arrowprops=dict(arrowstyle="-", color=DANGER, lw=2.4), zorder=5)
    ax.plot(*q, marker="x", ms=14, mew=3, color=DANGER, zorder=7)
    ax.plot(*I1, marker="s", ms=10, mfc="none", mec=SRC, mew=1.8, zorder=6)
    ax.text(I1[0] + 0.35, I1[1] - 0.05, "image I1 (S mirrored in Front)", color=SRC, fontsize=9, ha="left", va="center")
    ax.plot(*I2, marker="s", ms=10, mfc="none", mec=SRC, mew=1.8, zorder=6)
    ax.text(I2[0] - 0.1, I2[1] - 0.4, "image I2\n(I1 mirrored in Left)", color=SRC, fontsize=9, ha="center", va="top")
    ax.annotate("1  line Mic to I2 meets the Left wall's line\n    BEYOND the corner, on its dotted extension:\n    there is no wall there, so the path is blocked", xy=q, xytext=(-0.4, -2.75), color=TEXT, fontsize=9.5, ha="left", va="center", bbox=box(DANGER), arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9), zorder=8)
    ax.text(XL[0] + 0.2, 7.5, "OCCLUDED: Front then Left (2nd order)", color=DANGER, fontsize=13, weight="bold", va="top")
    ax.text(XL[0] + 0.2, 7.0, "stop at the first miss; this reflection is not heard at this mic", color=MUTED, fontsize=10, va="top")
    fig.suptitle("Backward validity check (Borish 1984): Mic to deepest image, through each face outline in turn, back to S", color=TEXT, fontsize=13.5, weight="bold", y=0.985)
    fig.text(0.5, 0.02, "Top view of a splayed control room (front 4 m, rear 6 m, 6 m deep). Dashed = construction line to an image; solid = the real sound path; arrows follow the check (Mic first).\nSame rule in 3D with face polygons; non-convex rooms add a blocking test on every segment.", ha="center", color=MUTED, fontsize=10)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.93, bottom=0.08, wspace=0.04)
    fig.savefig(os.path.join(OUT, "D2_backward_check.png"), dpi=130, pad_inches=0.25); plt.close(fig)

# ---------- 3. counts chart ----------
def fig_counts():
    res = json.load(open(os.path.join(os.path.dirname(__file__), "results.json")))
    short = {"Box 6 x 4.5 x 3 m": "Box\n(6 faces)", "Hexagon booth (R 1.6 m, 2.7 m)": "Hexagon\nbooth (8)", "Splayed control room (4->6 m, sloped ceiling)": "Splayed\nctrl room (6)", "LEDE-style (splayed front)": "LEDE-style\n(8)", "Gable-ceiling vocal booth": "Gable vocal\nbooth (7)", "L-shaped live room (non-convex)": "L-shaped\nlive room (8)"}
    names = list(res.keys())
    fig, axs = plt.subplots(2, 2, figsize=(15, 9.4))
    for k, ax in zip(range(1, 5), axs.flat):
        x = np.arange(len(names)); wdt = 0.27
        c = [res[n]["candidates"][k] for n in names]; v = [res[n]["after_validity"][k] for n in names]; a = [res[n]["audible"][k] for n in names]
        ax.bar(x - wdt, c, wdt, color=PANEL2, edgecolor=MUTED, lw=1.2, label="candidates N(N-1)^(k-1)")
        ax.bar(x, v, wdt, color=VIOLET, alpha=0.75, label="left after the parent-side prune")
        ax.bar(x + wdt, a, wdt, color=ACC, label="audible at the mic (valid)")
        ax.set_yscale("log"); ax.set_ylim(0.8, 12000)
        for xi, ci, ai in zip(x, c, a):
            ax.text(xi + wdt, ai * 1.25, f"{ai:.0f}\n{100 * ai / ci:.0f}%", ha="center", va="bottom", fontsize=8.3, color=TEXT, linespacing=1.0)
            ax.text(xi - wdt, ci * 1.12, f"{ci}", ha="center", va="bottom", fontsize=8, color=MUTED)
        ax.set_xticks(x); ax.set_xticklabels([short[n] for n in names], fontsize=8.6, color=TEXT)
        ax.set_title(f"order {k}", color=TEXT, fontsize=12, loc="left")
        ax.grid(axis="y", color=BORDER, lw=0.6, which="major"); ax.set_axisbelow(True)
        for sp in ax.spines.values(): sp.set_color(BORDER)
        ax.tick_params(axis="x", length=0)
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=3, frameon=False, fontsize=10.5, bbox_to_anchor=(0.5, 0.945), labelcolor=TEXT)
    fig.suptitle("Image-source candidates vs valid images (mean of 30 random source/mic pairs per room; log scale; label = valid count and % of candidates)", color=TEXT, fontsize=12.5, weight="bold", y=0.985)
    fig.text(0.5, 0.01, "Box check: valid = 6, 18, 38, 66 = 4k²+2, the exact shoebox count. Prototype: roadmap/nonrect/proto/ism_proto.py", ha="center", color=MUTED, fontsize=9.5)
    fig.tight_layout(rect=(0, 0.025, 1, 0.92))
    fig.savefig(os.path.join(OUT, "D3_counts.png"), dpi=130, pad_inches=0.25); plt.close(fig)

if __name__ == "__main__":
    fig_tree(); fig_backtrace(); fig_counts(); print("done")
