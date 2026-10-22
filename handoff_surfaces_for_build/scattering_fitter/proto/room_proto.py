#!/usr/bin/env python3
"""Offline prototype of per-hit scattering on the audited early field (6x3x8 m, user settings).

Input taps: the REAL live params the current software produces for the user's settings
(p_user_colour.json, generated read-only by the current render_pipeline.live_fdn_params):
  per line i: delay_ms, signed inject amplitude (includes 1/r, mic gain, broadband reflect gain).
Image indices / order / hit list: engine.early_field.build_image_indices(32) + surface_colour.surfaces_hit_by_n (copied).

Outputs: plots/proto_*.png, reports/proto_results.json
"""
import json, os, sys, math
import numpy as np
from scipy.signal import lfilter
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
from scattering_fitter.model import specular_fraction, velvet_cluster, fit_gain_shelf, biquad_mag
from scattering_fitter.sources import BANDS7

SR = 48000
PARAMS = os.environ.get("PUSER", "/workspace/scratch_er_dropout/tree2/software/p_user_colour.json")
# == engine.early_field.build_image_indices(32) (read from the audited copy, 26 Sep)
IDX = [(0, 2, 0), (0, 1, 0), (0, 0, 0), (0, -1, 0), (0, -2, 0), (0, 2, 1), (0, 1, 1), (0, 1, 1), (0, 0, 1), (0, 0, 1),
       (1, 2, 1), (1, 1, 1), (1, 0, 1), (1, -1, 1), (1, -2, 1), (1, 2, 0), (1, 1, 0), (1, 0, 0), (1, -1, 0), (1, -2, 0),
       (-1, 2, 0), (-1, 1, 0), (-1, 0, 0), (-1, -2, 0), (-1, -2, 0), (-1, 2, 1), (-1, 1, 1), (-1, 0, 1), (-1, -1, 1),
       (-1, -2, 1), (0, 1, 2), (0, 0, 2)]


def surfaces_hit_by_n(n):  # verbatim logic of surface_colour.surfaces_hit_by_n
    nx, ny, nz = n; hit = []
    if nx: hit.append("A" if nx < 0 else "C"); (abs(nx) >= 2) and hit.append("C" if nx < 0 else "A")
    if ny: hit.append("E" if ny < 0 else "F"); (abs(ny) >= 2) and hit.append("F" if ny < 0 else "E")
    if nz: hit.append("D" if nz < 0 else "B"); (abs(nz) >= 2) and hit.append("B" if nz < 0 else "D")
    return hit


def load_preset(pid):
    return json.load(open(os.path.join(ROOT, "presets", pid + ".json")))["scatter"]


SCENES = {
    # face letter -> preset id (ASSUMED demo assignment; A/C side walls x, E floor, F ceiling, B/D front/back z)
    "demo_mixed": dict(A="brick_unglazed", C="brick_unglazed", E="wood_parquet", F="acoustic_ceiling_tile",
                       B="plywood_panel", D="plaster_smooth"),
    "qrd_back_wall": dict(A="plaster_smooth", C="plaster_smooth", E="wood_parquet", F="plaster_smooth",
                          B="diffuser_qrd_n7", D="plaster_smooth"),
}


def band_energy(x, sr=SR):
    X = np.abs(np.fft.rfft(x, 1 << 16)) ** 2; f = np.fft.rfftfreq(1 << 16, 1 / sr)
    return np.array([X[(f >= fc / math.sqrt(2)) & (f < fc * math.sqrt(2))].sum() for fc in BANDS7])


def build(taps, scene, amount=1.0, n_pulses=16, length_ms=200.0, mute=()):
    n = int(SR * length_ms / 1000)
    before = np.zeros(n); spec = np.zeros(n); scat = np.zeros(n)
    per_tap = []
    for i, (d_ms, amp) in enumerate(taps):
        nidx = IDX[i]; hits = [h for h in surfaces_hit_by_n(nidx) if h not in mute]
        t0 = d_ms * 1e-3 * SR; i0 = int(math.floor(t0)); fr = t0 - i0
        imp = np.zeros(n)
        if i0 + 1 < n: imp[i0] += amp * (1 - fr); imp[i0 + 1] += amp * fr
        before += imp
        if not hits or amount <= 0:
            spec += imp; per_tap.append(dict(line=i, order=0 if not hits else len(hits), hits=hits, scatter_mean=0.0)); continue
        s_hits = [amount * np.asarray(load_preset(scene[h])) for h in hits]
        Sfr = specular_fraction(s_hits)                     # per band, prod(1-s)
        bs, as_, err_s, ps = fit_gain_shelf(np.sqrt(Sfr), BANDS7, SR)
        # scatter target from the *realised* specular magnitude so |Hs|^2+|Hd|^2 ≈ 1 per band
        realised = biquad_mag(bs, as_, BANDS7, SR)
        tgt_d = np.sqrt(np.clip(1.0 - realised ** 2, 0.0, 1.0))
        bd, ad, err_d, pd = fit_gain_shelf(tgt_d, BANDS7, SR)
        spec += lfilter(bs, as_, imp)
        off, a, w_ms = velvet_cluster(d_ms, SR, n_pulses=n_pulses, seed=1000 + i)
        cl = np.zeros(n)
        for o, aa in zip(off, a):
            j = i0 + o
            if j + 1 < n: cl[j] += amp * aa * (1 - fr); cl[j + 1] += amp * aa * fr
        scat += lfilter(bd, ad, cl)
        per_tap.append(dict(line=i, order=len(hits), hits=hits, t_ms=round(d_ms, 2), width_ms=round(w_ms, 2),
                            spec_frac=[round(float(v), 4) for v in Sfr], shelf_err_db=[round(err_s, 3), round(err_d, 3)],
                            energy_sum_per_band=[round(float(v), 4) for v in (realised ** 2 + biquad_mag(bd, ad, BANDS7, SR) ** 2)]))
    return before, spec, scat, per_tap


def echogram(x, ms=1.0):
    k = int(SR * ms / 1000); m = len(x) // k
    e = (x[:m * k] ** 2).reshape(m, k).sum(1)
    return np.arange(m) * ms, 10 * np.log10(e + 1e-14)


def main():
    P = json.load(open(PARAMS)); b = P["buses"]["l"]
    taps = list(zip(b["delay_ms"], b["inject"]))
    out = {"params_file": PARAMS, "room": "W6 H3 L8 (user)", "sr": SR, "n_lines": len(taps)}
    os.makedirs(os.path.join(ROOT, "plots"), exist_ok=True)
    for name, scene in SCENES.items():
        before, spec, scat, per_tap = build(taps, scene)
        after = spec + scat
        eb, ea = band_energy(before), band_energy(after)
        es, ed = band_energy(spec), band_energy(scat)
        # reflected-only share (exclude the direct line, which has no hits)
        dimp = np.zeros(len(before))
        for i, (d_ms, amp) in enumerate(taps):
            if not surfaces_hit_by_n(IDX[i]):
                t0 = d_ms * 1e-3 * SR; i0 = int(math.floor(t0)); fr = t0 - i0; dimp[i0] += amp * (1 - fr); dimp[i0 + 1] += amp * fr
        es_r = band_energy(spec - dimp)
        res = dict(scene=scene,
                   scattered_share_of_reflected=[round(float(d / (s + d)), 4) for s, d in zip(es_r, ed)],
                   per_tap_filter_energy_err_db_maxabs=round(float(max(abs(10 * np.log10(v)) for tp in per_tap if tp.get("energy_sum_per_band") for v in tp["energy_sum_per_band"])), 3),
                   band_energy_ratio_db=[round(float(10 * np.log10(a / bb)), 3) for a, bb in zip(ea, eb)],
                   spec_plus_scat_vs_before_db=[round(float(10 * np.log10((s + d) / bb)), 3) for s, d, bb in zip(es, ed, eb)],
                   scattered_share=[round(float(d / (s + d)), 4) for s, d in zip(es, ed)],
                   broadband_energy_ratio_db=round(float(10 * np.log10((after ** 2).sum() / (before ** 2).sum())), 3),
                   peak_before=float(np.abs(before).max()), peak_after=float(np.abs(after).max()),
                   finite=bool(np.isfinite(after).all()), taps=per_tap)
        # amount sweep: continuity / no level jump
        sweep = []
        for am in np.linspace(0, 1, 11):
            bb, ss, dd, _ = build(taps, scene, amount=am)
            sweep.append(dict(amount=round(float(am), 2),
                              energy_db=round(float(10 * np.log10(((ss + dd) ** 2).sum() / (bb ** 2).sum())), 3),
                              null_vs_before=float(np.abs(ss + dd - bb).max()) if am == 0 else None))
        res["amount_sweep"] = sweep
        # muted-face check: mute the scattering-heaviest face -> that face contributes no scattering
        mf = "B"; bm, sm, dm, ptm = build(taps, scene, mute=(mf,))
        res["mute_check"] = dict(muted=mf, any_tap_lists_muted_face=any(mf in t["hits"] for t in ptm),
                                 scattered_share_with_mute=[round(float(v), 4) for v in (band_energy(dm) / (band_energy(sm) + band_energy(dm)))])
        out[name] = res
        # plots
        t = np.arange(len(before)) / SR * 1e3
        fig, ax = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
        ax[0].plot(t, before, lw=0.7); ax[0].set_title(f"{name}: BEFORE (specular taps only, live inject amps)")
        ax[1].plot(t, spec, lw=0.7, label="specular (sqrt(prod(1-s)) shelf)"); ax[1].plot(t, scat, lw=0.7, alpha=0.8, label="scattered clusters (Lambert velvet)")
        ax[1].legend(fontsize=8); ax[1].set_title("AFTER — components")
        te, eb_ = echogram(before); _, ea_ = echogram(after)
        ax[2].plot(te, eb_, label="before"); ax[2].plot(te, ea_, label="after"); ax[2].set_ylim(max(eb_.max(), ea_.max()) - 60, max(eb_.max(), ea_.max()) + 3)
        ax[2].set_title("Echogram (1 ms bins, dB)"); ax[2].legend(); ax[2].set_xlabel("ms")
        fig.tight_layout(); fig.savefig(os.path.join(ROOT, "plots", f"proto_{name}_ir_echogram.png"), dpi=110); plt.close(fig)
        fig, ax = plt.subplots(1, 2, figsize=(11, 4))
        ax[0].semilogx(BANDS7, res["band_energy_ratio_db"], "o-"); ax[0].axhline(0, color="k", lw=0.5)
        ax[0].set_ylim(-1.5, 1.5); ax[0].set_title("after/before energy per octave (dB)"); ax[0].grid(True, which="both", alpha=0.3)
        ax[1].plot([s["amount"] for s in sweep], [s["energy_db"] for s in sweep], "o-"); ax[1].set_ylim(-1.5, 1.5)
        ax[1].set_title("scatter amount sweep: broadband energy vs before (dB)"); ax[1].grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(os.path.join(ROOT, "plots", f"proto_{name}_energy.png"), dpi=110); plt.close(fig)
    # cluster envelope plot
    from scattering_fitter.model import lambert_energy_cdf
    x = np.linspace(1, 2.5, 300)
    fig, ax = plt.subplots(figsize=(6, 3.5)); ax.plot(x, 4 * x ** -5, label="density ∝ x^-5"); ax.plot(x, lambert_energy_cdf(x), label="CDF 1-x^-4")
    ax.axvline(10 ** 0.25, ls="--", color="gray"); ax.set_xlabel("t / t_spec"); ax.legend(); ax.set_title("DERIVED Lambert first-order envelope")
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "plots", "proto_lambert_envelope.png"), dpi=110); plt.close(fig)
    json.dump(out, open(os.path.join(ROOT, "reports", "proto_results.json"), "w"), indent=1)
    for name in SCENES:
        r = out[name]
        print(name, "band dB", r["band_energy_ratio_db"], "spec+scat dB", r["spec_plus_scat_vs_before_db"], "share", r["scattered_share"], "share_refl", r["scattered_share_of_reflected"], "tapErr", r["per_tap_filter_energy_err_db_maxabs"],
              "bb", r["broadband_energy_ratio_db"], "peak", round(r["peak_before"], 4), round(r["peak_after"], 4))
        print("  sweep", [(s["amount"], s["energy_db"]) for s in r["amount_sweep"]], "null@0", r["amount_sweep"][0]["null_vs_before"])
        print("  mute", r["mute_check"])
        w = [t.get("width_ms") for t in r["taps"] if t.get("width_ms")]; print("  cluster widths ms min/max", min(w), max(w))


if __name__ == "__main__":
    main()
