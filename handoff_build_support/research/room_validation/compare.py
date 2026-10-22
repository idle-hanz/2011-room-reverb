"""Compare measured BRAS CR2 RIRs with the 2011 Room Reverb Render variants and the ISM baseline.
Writes results/*.json, results/*.md tables and plots/*.png.  Run after render_all.py."""
import json, os, sys, warnings
import numpy as np
from scipy import signal
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bras_cr2 as B, analysis as A, scene as S, ism_baseline as I
from render_all import VARIANTS, OUT
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.ticker

SR = B.SR
PAIRS = [(ls, mp) for ls in B.SOURCES for mp in B.RECEIVERS]
RES = os.path.join(HERE, "results"); PLOTS = os.path.join(HERE, "plots")
os.makedirs(RES, exist_ok=True); os.makedirs(PLOTS, exist_ok=True)
KEYS = ["EDT", "T20", "T30", "C50", "C80", "D50"]


PRE_ZERO = 32  # model IRs carry a non-physical sample block at t=0 (FDN diffuser allpass feed-forward -g*x,
               # engine/fdn.py process_block_poly: y = -gi*x + v). It is reported separately and zeroed for analysis.


def load_model(v, ls, mp, raw=False):
    x = np.fromfile(os.path.join(OUT, f"{v}_LS{ls}_MP{mp}.f32"), np.float32).reshape(-1, 2)[:, 0].astype(float)
    if not raw:
        x = x.copy(); x[:PRE_ZERO] = 0.0
    return x


def band_energy_ratio(x, i0, bands=A.OCT):
    """Late (>=50 ms after onset) band energy relative to the direct window (onset-0.5 ms .. +2.5 ms), dB."""
    out = {}
    for f in bands:
        y = A.bandpass(x, f, SR, 1)
        d = (y[max(0, i0 - int(0.0005 * SR)): i0 + int(0.0025 * SR)] ** 2).sum()
        late = (y[i0 + int(0.05 * SR):] ** 2).sum()
        out[int(f)] = 10 * np.log10(late / d)
    return out


def mf_env(x, i0, band=(500, 4000)):
    tpl = x[max(0, i0 - 20): i0 + 70] * np.hanning(len(x[max(0, i0 - 20): i0 + 70]))
    y = signal.correlate(x, tpl, mode="full", method="fft")[len(tpl) - 1 - 20:]   # lag 0 aligned, shifted by 20
    y = y[:len(x)]
    sos = signal.butter(4, band, btype="band", fs=SR, output="sos")
    env = np.abs(signal.hilbert(signal.sosfiltfilt(sos, y)))
    return env / env[max(0, i0 - 10): i0 + 30].max()


WALLS = {"A x=0 (BRAS x0)": (0, "lo"), "C x=W (BRAS x1)": (0, "hi"), "E floor": (1, "lo"), "F ceiling": (1, "hi"),
         "D z=0 (back, no -Z image in LIVE_32)": (2, "lo"), "B z=L (front)": (2, "hi")}
ALPHA1K = {"A x=0 (BRAS x0)": "A", "C x=W (BRAS x1)": "C", "E floor": "E", "F ceiling": "F",
           "D z=0 (back, no -Z image in LIVE_32)": "D", "B z=L (front)": "B"}


def first_order(ls, mp):
    m = S.to_model(ls, mp); src = np.array([m["sx"], m["sy"], m["sz"]]); rec = np.array([m["mcx"], m["my"], m["mcz"]])
    dims = [S.W, S.H, S.L]; dd = np.linalg.norm(src - rec); out = {}
    surf = S.surfaces(m["flip"])
    for name, (ax, side) in WALLS.items():
        img = src.copy(); img[ax] = -src[ax] if side == "lo" else 2 * dims[ax] - src[ax]
        di = np.linalg.norm(img - rec)
        a = surf[ALPHA1K[name]]["absorb"][3]
        out[name] = dict(d_img=di, d_dir=dd, dt_phys_ms=(di - dd) / B.C_AIR * 1e3, dt_model_ms=(di - dd) / 340.0 * 1e3,
                         L_phys_db=20 * np.log10(dd / di * np.sqrt(1 - a)), L_model_law_db=20 * np.log10((dd / di) ** 2 * np.sqrt(1 - a)))
    return out


def main():
    meas = {p: B.load_rir(*p) for p in PAIRS}
    ref = B.reference_params()
    # ---------- parameters
    table = {"measured": {}, "ism": {}}
    for v in VARIANTS: table[v] = {}
    spec = {k: {} for k in table}
    for p in PAIRS:
        x = meas[p]; i0 = A.onset(x)
        table["measured"][p] = A.all_params(x, SR, noise_comp=True)
        spec["measured"][p] = band_energy_ratio(x, i0)
        for v in VARIANTS:
            h = load_model(v, *p); j0 = A.onset(h)
            table[v][p] = A.all_params(h, SR, noise_comp=False)
            spec[v][p] = band_energy_ratio(h, j0)
        en = I.ism_energy(*p)
        m = S.to_model(*p); dd = np.linalg.norm([m["sx"] - m["mcx"], m["sy"] - m["my"], m["sz"] - m["mcz"]])
        table["ism"][p] = {b: I.params_from_energy(e, dd / B.C_AIR) for b, e in en.items()}
        # ISM "late/direct" ratio: energy >= 50 ms vs direct bin
        i0b = int(dd / B.C_AIR / I.BIN)
        spec["ism"][p] = {b: 10 * np.log10(e[i0b + int(0.05 / I.BIN):].sum() / e[i0b:i0b + 6].sum()) for b, e in en.items()}
    summ = {}
    for k, t in table.items():
        summ[k] = {}
        for f in A.OCT.astype(int):
            summ[k][int(f)] = {q: float(np.nanmean([t[p][f][q] for p in PAIRS])) for q in KEYS}
            summ[k][int(f)].update({q + "_sd": float(np.nanstd([t[p][f][q] for p in PAIRS])) for q in KEYS})
            summ[k][int(f)]["late_over_direct_db"] = float(np.mean([spec[k][p][int(f)] for p in PAIRS]))
    json.dump(summ, open(os.path.join(RES, "cr2_octave_summary.json"), "w"), indent=1)
    # JND-based verdicts (ISO 3382-1 Annex A: EDT/T 5 %, C80/C50 1 dB, D50 0.05)
    lines = ["| model | f (Hz) | EDT s | T20 s | T30 s | C50 dB | C80 dB | late/direct dB |", "|---|---|---|---|---|---|---|---|"]
    for k in ["measured", "ism"] + list(VARIANTS):
        for f in A.OCT.astype(int):
            s = summ[k][f]
            lines.append(f"| {k} | {f} | {s['EDT']:.2f} | {s['T20']:.2f} | {s['T30']:.2f} | {s['C50']:.1f} | {s['C80']:.1f} | {s['late_over_direct_db']:.1f} |")
    open(os.path.join(RES, "cr2_octave_table.md"), "w").write("\n".join(lines) + "\n")
    # error table vs measured (in JNDs)
    elines = ["| model | metric | 125 | 250 | 500 | 1k | 2k | 4k | 8k | mean abs err (JND) |", "|---|---|---|---|---|---|---|---|---|---|"]
    jnd = {"EDT": ("rel", 0.05), "T20": ("rel", 0.05), "T30": ("rel", 0.05), "C50": ("abs", 1.0), "C80": ("abs", 1.0)}
    errs = {}
    for k in ["ism"] + list(VARIANTS):
        errs[k] = {}
        for q, (mode, j) in jnd.items():
            row = []
            for f in A.OCT.astype(int):
                mv, me = summ[k][f][q], summ["measured"][f][q]
                e = (mv / me - 1) / j if mode == "rel" else (mv - me) / j
                row.append(e)
            errs[k][q] = row
            elines.append(f"| {k} | {q} | " + " | ".join(f"{e:+.1f}" for e in row) + f" | {np.mean(np.abs(row)):.1f} |")
    open(os.path.join(RES, "cr2_error_jnd.md"), "w").write("\n".join(elines) + "\n")
    json.dump(errs, open(os.path.join(RES, "cr2_error_jnd.json"), "w"), indent=1)
    # ---------- early reflections
    er = []
    for p in PAIRS:
        x = meas[p]; i0 = A.onset(x); env_m = mf_env(x, i0)
        envs = {}
        for v in ("snap_oracle", "fix_oracle"):
            h = load_model(v, *p); j0 = A.onset(h); envs[v] = (j0, mf_env(h, j0))
        for name, fo in first_order(*p).items():
            km = i0 + int(round(fo["dt_phys_ms"] * 1e-3 * SR)); kh = int(round(fo["dt_model_ms"] * 1e-3 * SR))
            w = int(0.0003 * SR)
            lm = 20 * np.log10(env_m[km - w: km + w + 1].max() + 1e-12)
            lh = {v: float(20 * np.log10(e[j0 + kh - w: j0 + kh + w + 1].max() + 1e-12)) for v, (j0, e) in envs.items()}
            # measured peak time offset within +-0.6 ms of prediction
            ww = int(0.0006 * SR); seg = env_m[km - ww: km + ww + 1]; off = (np.argmax(seg) - ww) / SR * 1e3
            er.append(dict(pair=f"LS{p[0]}MP{p[1]}", wall=name, dt_phys_ms=round(fo["dt_phys_ms"], 2),
                           dt_model_ms=round(fo["dt_model_ms"], 2), meas_peak_offset_ms=round(off, 2),
                           L_meas_db=round(lm, 1), L_model_db=round(lh["fix_oracle"], 1), L_snap_db=round(lh["snap_oracle"], 1), L_phys_1r_db=round(fo["L_phys_db"], 1),
                           L_1r2_law_db=round(fo["L_model_law_db"], 1)))
    json.dump(er, open(os.path.join(RES, "cr2_first_order.json"), "w"), indent=1)
    # aggregate per wall
    agg = ["| wall | dt model-phys (ms, mean) | L meas (dB) | L model snap_oracle (dB) | L model fix_oracle (dB) | 1/r expectation (dB) | 1/r^2 law (dB) |", "|---|---|---|---|---|---|---|"]
    for name in WALLS:
        rows = [r for r in er if r["wall"] == name]
        agg.append(f"| {name} | {np.mean([r['dt_model_ms'] - r['dt_phys_ms'] for r in rows]):+.2f} | {np.mean([r['L_meas_db'] for r in rows]):.1f} | {np.mean([r['L_snap_db'] for r in rows]):.1f} | "
                   f"{np.mean([r['L_model_db'] for r in rows]):.1f} | {np.mean([r['L_phys_1r_db'] for r in rows]):.1f} | {np.mean([r['L_1r2_law_db'] for r in rows]):.1f} |")
    open(os.path.join(RES, "cr2_first_order_by_wall.md"), "w").write("\n".join(agg) + "\n")
    # ---------- plots
    f = A.OCT
    fig, axs = plt.subplots(2, 3, figsize=(15, 8))
    style = {"measured": ("k", "-", "o"), "ism": ("tab:gray", "--", "s"), "snap_default": ("tab:red", ":", "x"),
             "snap_eyring": ("tab:orange", ":", "^"), "snap_oracle": ("tab:red", "-", "^"), "fix_eyring": ("tab:cyan", "-", "v"),
             "fix_oracle": ("tab:blue", "-", "v")}
    for ax, q in zip(axs.flat, ["EDT", "T20", "T30", "C50", "C80", "late_over_direct_db"]):
        for k, (c, ls_, mk) in style.items():
            y = [summ[k][int(b)][q] for b in f]
            ax.semilogx(f, y, color=c, ls=ls_, marker=mk, label=k)
            if k == "measured" and q in KEYS:
                sd = [summ[k][int(b)][q + "_sd"] for b in f]
                ax.fill_between(f, np.array(y) - sd, np.array(y) + sd, color="k", alpha=0.12)
        if q == "T20":
            ax.semilogx(ref["T20"][0], ref["T20"][1], "k.", ms=4, label="BRAS file T20 (1/3 oct)")
        if q == "EDT":
            ax.semilogx(ref["EDT"][0], ref["EDT"][1], "k.", ms=4, label="BRAS file EDT (1/3 oct)")
        if q == "C80":
            ax.semilogx(ref["C80"][0], ref["C80"][1], "k.", ms=4, label="BRAS file C80 (1/3 oct)")
        ax.set_title(q.replace("_", " ") + (" (s)" if q[0] in "ET" else " (dB)")); ax.set_xticks(f); ax.set_xticklabels([str(int(b)) for b in f]); ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator()); ax.grid(alpha=0.3)
    axs[0, 0].legend(fontsize=7)
    fig.suptitle("BRAS CR2 seminar room: measured (10 dodecahedron RIRs, mean ±1 sd) vs 2011 Room Reverb Render variants vs ISM")
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "cr2_params_octave.png"), dpi=110); plt.close(fig)
    # EDC plot
    p = (1, 1)
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, fb in zip(axs, (250, 1000, 4000)):
        x = meas[p]; i0 = A.onset(x); y = A.bandpass(x, fb, SR)[i0:]; e = A.edc_db(y, SR)
        ax.plot(np.arange(len(e)) / SR, e, "k", label="measured")
        for k in ["snap_default", "snap_oracle", "fix_oracle", "fix_eyring"]:
            h = load_model(k, *p); j0 = A.onset(h); y = A.bandpass(h, fb, SR)[j0:]; e = A.edc_db(y, SR, noise_comp=False)
            c, ls_, _ = style[k]; ax.plot(np.arange(len(e)) / SR, e, color=c, ls=ls_, label=k)
        e = table["ism"][p][fb]["edc"]; ax.plot(np.arange(len(e)) * I.BIN, e, color="tab:gray", ls="--", label="ISM")
        ax.set_ylim(-60, 2); ax.set_xlim(0, 2.5); ax.set_title(f"EDC {fb} Hz, LS1 MP1"); ax.set_xlabel("s"); ax.grid(alpha=0.3)
    axs[0].legend(fontsize=7); fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "cr2_edc_LS1_MP1.png"), dpi=110); plt.close(fig)
    # early plot
    for p in [(1, 1), (2, 4)]:
        x = meas[p]; i0 = A.onset(x); em = mf_env(x, i0)
        h = load_model("fix_oracle", *p); j0 = A.onset(h); eh = mf_env(h, j0)
        t = (np.arange(int(0.06 * SR)) - int(0.002 * SR)) / SR * 1e3
        fig, ax = plt.subplots(figsize=(13, 4.5))
        ax.plot(t, 20 * np.log10(em[i0 - int(0.002 * SR): i0 - int(0.002 * SR) + len(t)] + 1e-9), "k", lw=0.8, label="measured (matched-filter env, 0.5-4 kHz)")
        ax.plot(t, 20 * np.log10(eh[j0 - int(0.002 * SR): j0 - int(0.002 * SR) + len(t)] + 1e-9), "tab:blue", lw=0.8, alpha=0.8, label="model fix_oracle (same processing)")
        for name, fo in first_order(*p).items():
            ax.axvline(fo["dt_phys_ms"], color="g", ls="--", lw=0.8); ax.text(fo["dt_phys_ms"], 2, name.split(" ")[0], color="g", fontsize=8)
            ax.axvline(fo["dt_model_ms"], color="tab:blue", ls=":", lw=0.8)
        ax.set_ylim(-40, 5); ax.set_xlabel("ms after direct"); ax.set_ylabel("dB re direct"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
        ax.set_title(f"Early field LS{p[0]} MP{p[1]}: green dashed = first-order image times (physical, c=343.1), blue dotted = model (c=340)")
        fig.tight_layout(); fig.savefig(os.path.join(PLOTS, f"cr2_early_LS{p[0]}_MP{p[1]}.png"), dpi=110); plt.close(fig)
    # first-order level scatter
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter([r["L_phys_1r_db"] for r in er], [r["L_meas_db"] for r in er], s=14, c="k", label="measured")
    ax.scatter([r["L_phys_1r_db"] for r in er], [r["L_model_db"] for r in er], s=14, c="tab:blue", marker="v", label="model fix_oracle")
    ax.plot([-25, 0], [-25, 0], "g--", lw=0.8, label="1/r·|R| expectation")
    ax.set_xlabel("physical expectation (dB re direct)"); ax.set_ylabel("observed (dB re direct)"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    ax.set_title("First-order reflection levels (60 = 10 pairs × 6 walls)"); fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "cr2_first_order_levels.png"), dpi=110); plt.close(fig)
    print(open(os.path.join(RES, "cr2_error_jnd.md")).read()); print(open(os.path.join(RES, "cr2_first_order_by_wall.md")).read())


if __name__ == "__main__":
    main()
