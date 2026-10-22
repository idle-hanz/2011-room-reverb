"""Offline prototype: source radiation in the 2011 Room Reverb early field + FDN inject.

Room 6 x 3 x 8 m (W x H x L), SR 48 kHz. Uses the LIVE engine/early_field.py
(copied read-only) for image geometry + per-hit allpass + air; inserts the
source-radiation stage FIRST in each image's serial cascade (before surfaces/
peaking/air), direct path per capsule (air-free, as live), and the FDN inject
through the per-source power-averaged (diffuse) filter.

FDN here is a STAND-IN with the same topology as the live one (32 lines,
unscaled +-1 Hadamard (fwht), per-line inject = tap level, line i <-> tap i),
used only to show relative energy / invariance; it is not the engine's tuned FDN.
Peaking (wall) stages are skipped in this prototype (LTI; order-independent,
irrelevant to the null and relative tests). Labels: all numbers are box runs.
"""
from __future__ import annotations
import json, math, os, sys
import numpy as np
from scipy.signal import lfilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "live_code"))
sys.path.insert(0, HERE)
from engine import early_field as ef  # noqa
import radiation as R  # noqa
import numba as nb

FS = 48000
ROOM = (6.0, 3.0, 8.0)
SRC = (3.0, 1.5, 2.5)
MIC_C = (3.0, 1.5, 5.5)
SPACE = 0.3
N_SAMP = int(1.6 * FS)
HUM = 0.5
PRESETS = os.path.join(ROOT, "source_fitter", "presets")
OUT = os.path.join(HERE, "out")


def load_preset(pid):
    return json.load(open(os.path.join(PRESETS, pid + ".json")))


def build_taps(hn=32):
    stand = ef.MicStand(cx=MIC_C[0], cy=MIC_C[1], cz=MIC_C[2], space=SPACE, car_omni=1.0,
                        mlalr=math.pi, mralr=math.pi, mcalr=math.pi)  # capsules face the source (-z)
    taps = ef.compute_taps(ROOM, SRC, stand, hadamard_n=hn)
    ml, mr = ef.mic_positions(stand)
    return taps, {"l": ml, "r": mr}


def src_stage(buf, preset, n, img_pos, rx, basis, stats=None):
    if preset is None:
        return buf
    e = R.emission_dir(n, img_pos, rx)
    c = R.coef_for_dir(preset["params"], R.local_dir(e, basis), FS)
    if stats is not None:
        stats.append(c.bypass)
    return R.src_process_fast(buf, c)


def render_early(taps, rx, preset, yaw, pitch=0.0, bus="l"):
    """Per tap: Dirac -> allpass -> SOURCE -> (surfaces/peaking skipped) -> air; direct excluded."""
    basis = R.facing_basis(yaw, pitch)
    out = np.zeros(N_SAMP)
    for t in taps:
        if t.n == (0, 0, 0):
            continue
        d = getattr(t, "distance_" + bus); lv = getattr(t, "level_" + bus)
        ds = int(round(d / ef.SPEED_OF_SOUND_M_S * FS))
        buf = np.zeros(N_SAMP)
        ef.apply_allpass_to_dirac(buf, ds, lv, t.allpass_stages, FS)
        buf = src_stage(buf, preset, t.n, t.position, rx[bus], basis)
        buf = ef.apply_air_absorption(buf, d, FS, HUM)
        out += buf
    return out


def render_direct(taps, rx, preset, yaw, pitch=0.0, bus="l"):
    """Direct: direction source->capsule, air-free (lock)."""
    basis = R.facing_basis(yaw, pitch)
    t = [t for t in taps if t.n == (0, 0, 0)][0]
    d = getattr(t, "distance_" + bus); lv = getattr(t, "level_" + bus)
    buf = np.zeros(N_SAMP); buf[int(round(d / ef.SPEED_OF_SOUND_M_S * FS))] = lv
    return src_stage(buf, preset, t.n, t.position, rx[bus], basis)


@nb.njit(cache=True)
def _fdn(inj_x, inj_gain, delays, att, n_out):
    N = delays.shape[0]
    L = delays.max() + 1
    ring = np.zeros((N, L)); w = 0
    y = np.zeros(n_out); v = np.zeros(N)
    for s in range(n_out):
        for i in range(N):
            v[i] = ring[i, (w - delays[i]) % L] * att[i]
        acc = 0.0
        for i in range(N):
            acc += v[i]
        y[s] = acc
        # unscaled fwht in place
        h = 1
        while h < N:
            for i in range(0, N, 2 * h):
                for j in range(i, i + h):
                    a = v[j]; b = v[j + h]; v[j] = a + b; v[j + h] = a - b
            h *= 2
        xs = inj_x[s] if s < inj_x.shape[0] else 0.0
        for i in range(N):
            ring[i, w] = v[i] / math.sqrt(N) + xs * inj_gain[i]
        w = (w + 1) % L
    return y


def render_tail(taps, preset, yaw, bus="l", alpha=0.0, rx=None, rt60=1.1):
    """FDN stand-in. inject line i = tap i level; input x = Dirac through the per-source
    DIFFUSE filter (power-averaged directivity). alpha>0 blends per-image broadband gain."""
    lines = [t for t in taps][:32]
    delays = np.array([max(int(round(getattr(t, "distance_" + bus) / 340.0 * FS)), 64) for t in lines], np.int64)
    att = 10 ** (-3.0 * delays / (FS * rt60))
    g = np.array([getattr(t, "level_" + bus) for t in lines])
    x = np.zeros(N_SAMP); x[0] = 1.0
    if preset is not None:
        c = R.diffuse_coef(preset, FS)
        x = R.src_process_fast(x, c)
        if alpha > 0.0:
            basis = R.facing_basis(yaw, 0.0)
            for i, t in enumerate(lines):
                e = R.emission_dir(t.n, t.position, rx[bus])
                cc = R.coef_for_dir(preset["params"], R.local_dir(e, basis), FS)
                # broadband image gain at 1 kHz relative to diffuse at 1 kHz
                from scipy.signal import freqz
                imp = np.zeros(2048); imp[0] = 1
                hi = np.abs(np.fft.rfft(R.src_process_fast(imp, cc)))[43]
                hd = np.abs(np.fft.rfft(R.src_process_fast(imp, R.diffuse_coef(preset, FS))))[43]
                g[i] *= (1 - alpha) + alpha * hi / max(hd, 1e-9)
    return _fdn(x, g, delays, att, N_SAMP)


def third_oct_db(x, fmin=63, fmax=16000):
    X = np.abs(np.fft.rfft(x, 1 << 17)) ** 2
    f = np.fft.rfftfreq(1 << 17, 1 / FS)
    fc = 1000 * 2 ** (np.arange(-12, 13) / 3)
    fc = fc[(fc >= fmin) & (fc <= fmax)]
    out = []
    for c in fc:
        m = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))
        out.append(10 * np.log10(X[m].mean() + 1e-20))
    return fc, np.array(out)


def energy_db(x):
    return 10 * np.log10(np.sum(x ** 2) + 1e-30)


def main():
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(OUT, exist_ok=True)
    taps, rx = build_taps()
    rep = {"room": ROOM, "source": SRC, "mic_centre": MIC_C, "fs": FS, "n_taps": len(taps)}
    face_yaw = R.yaw_to_face(SRC, MIC_C)
    # ---------------- 1. omni null test
    omni = load_preset("omni")
    null = {}
    for bus in ("l", "r"):
        e0 = render_early(taps, rx, None, 0, bus=bus); e1 = render_early(taps, rx, omni, 37.0, bus=bus)
        d0 = render_direct(taps, rx, None, 0, bus=bus); d1 = render_direct(taps, rx, omni, 37.0, bus=bus)
        t0 = render_tail(taps, None, 0, bus=bus); t1 = render_tail(taps, omni, 37.0, bus=bus)
        null[bus] = {"early_maxdiff": float(np.max(np.abs(e0 - e1))), "direct_maxdiff": float(np.max(np.abs(d0 - d1))),
                     "tail_maxdiff": float(np.max(np.abs(t0 - t1)))}
    rep["omni_null"] = null
    # on-axis exactness for a directional preset: an image straight ahead must be bypass
    tp = load_preset("trumpet")
    c_ax = R.coef_for_dir(tp["params"], np.array([1.0, 0, 0]) if tp["params"]["aim_az"] == 0 and tp["params"]["aim_el"] == 0 else R.SM.axis_frame(tp["params"]["aim_az"], tp["params"]["aim_el"])[0], FS)
    rep["trumpet_on_axis_bypass"] = bool(c_ax.bypass or (abs(c_ax.gain - 1) < 1e-12))
    # ---------------- 2. spectra facing vs away, echograms, energy table
    table = []
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2))
    figE, axE = plt.subplots(3, 1, figsize=(11, 10))
    base_e = render_early(taps, rx, None, 0); base_d = render_direct(taps, rx, None, 0); base_t = render_tail(taps, None, 0)
    for k, pid in enumerate(["talking_head", "trumpet", "combo_1x12"]):
        pr = load_preset(pid)
        for yaw_rel, ls in ((0, "-"), (90, "--"), (180, ":")):
            yaw = face_yaw + yaw_rel
            e = render_early(taps, rx, pr, yaw); d = render_direct(taps, rx, pr, yaw)
            t0 = render_tail(taps, pr, yaw, alpha=0.0); t5 = render_tail(taps, pr, yaw, alpha=0.5, rx=rx)
            fc, s = third_oct_db((d + e)[: int(0.08 * FS)])
            axs[k].semilogx(fc, s, ls, label=f"yaw {yaw_rel:+d}° rel. facing mic")
            imp = np.zeros(4096); imp[0] = 1.0
            Hd = np.abs(np.fft.rfft(R.src_process_fast(imp, R.diffuse_coef(pr, FS))))
            mk = -20 * np.log10(Hd[int(round(1000 / FS * 4096))])
            table.append({"preset": pid, "yaw_rel_deg": yaw_rel, "power_match_makeup_dB_1k": float(mk),
                          "direct_dB_rel_omni": energy_db(d) - energy_db(base_d),
                          "early_dB_rel_omni": energy_db(e) - energy_db(base_e),
                          "tail_alpha0_dB_rel_omni": energy_db(t0) - energy_db(base_t),
                          "tail_alpha0.5_dB_rel_omni": energy_db(t5) - energy_db(base_t),
                          "early_hf_4k_dB": float(s[np.argmin(abs(fc - 4000))]), "early_lf_250_dB": float(s[np.argmin(abs(fc - 250))])})
            if yaw_rel in (0, 180):
                full = np.concatenate([d, np.zeros(0)]) + e + 0.3 * t0
                bins = int(0.001 * FS); nb_ = N_SAMP // bins
                eg = 10 * np.log10(np.add.reduceat(full ** 2, np.arange(0, nb_ * bins, bins)) + 1e-20)
                axE[k].plot(np.arange(nb_), eg[:nb_], label=f"{pid} yaw {yaw_rel:+d}°", lw=0.9)
        fc, s = third_oct_db((base_d + base_e)[: int(0.08 * FS)])
        axs[k].semilogx(fc, s, color="k", lw=0.8, alpha=0.5, label="omni (current engine)")
        axs[k].set_title(f"{pid}: direct+early (0-80 ms), mic L"); axs[k].set_xlabel("Hz"); axs[k].set_ylabel("dB (1/3 oct)")
        axs[k].grid(True, which="both", alpha=0.3); axs[k].legend(fontsize=7)
        full0 = base_d + base_e + 0.3 * base_t
        bins = int(0.001 * FS); nb_ = N_SAMP // bins
        eg0 = 10 * np.log10(np.add.reduceat(full0 ** 2, np.arange(0, nb_ * bins, bins)) + 1e-20)
        axE[k].plot(np.arange(nb_), eg0[:nb_], color="k", lw=0.6, alpha=0.6, label="omni (before)")
        axE[k].set_xlim(0, 400); axE[k].set_ylim(eg0.max() - 70, eg0.max() + 3); axE[k].legend(fontsize=7)
        axE[k].set_ylabel("dB / 1 ms"); axE[k].grid(alpha=0.3)
    axE[-1].set_xlabel("ms")
    fig.suptitle("PROTOTYPE (box run): 6x3x8 m, source faces mic at yaw_rel 0"); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "spectra_facing_vs_away.png"), dpi=110)
    figE.suptitle("Echogram before (omni) / after (preset facing vs away); tail = FDN stand-in x0.3"); figE.tight_layout()
    figE.savefig(os.path.join(OUT, "echogram_before_after.png"), dpi=110)
    rep["energy_table"] = table
    json.dump(rep, open(os.path.join(OUT, "proto_report.json"), "w"), indent=1)
    lines = ["| preset | yaw rel. | direct dB | early dB | tail α=0 dB | tail α=0.5 dB | early 250 Hz | early 4 kHz | power-match make-up @1k |", "|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        lines.append(f"| {r['preset']} | {r['yaw_rel_deg']} | {r['direct_dB_rel_omni']:+.1f} | {r['early_dB_rel_omni']:+.1f} | {r['tail_alpha0_dB_rel_omni']:+.2f} | {r['tail_alpha0.5_dB_rel_omni']:+.2f} | {r['early_lf_250_dB']:.1f} | {r['early_hf_4k_dB']:.1f} | {r['power_match_makeup_dB_1k']:+.1f} |")
    open(os.path.join(OUT, "energy_table.md"), "w").write("\n".join(lines) + "\n")
    print(json.dumps(null, indent=1)); print("\n".join(lines))


if __name__ == "__main__":
    main()
