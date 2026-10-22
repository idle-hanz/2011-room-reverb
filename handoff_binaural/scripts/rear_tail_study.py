"""Study for the 2026-09-30 locked decisions: rear images (item 5) and diffuse IC tail (item 1).

Read-only use of the p5 engine (compute_taps, FDN, render helpers). Writes:
  reports/rear_images.json, reports/tail_ic.json,
  presets/binaural/image_sets/binaural_rear32.json, presets/binaural/tail_ic/<id>.json,
  plots/binaural/rear_images_top.png, plots/binaural/tail_ic_SADIE2_KU100.png
"""
import json, math, sys, time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
P5 = Path('/workspace/build_support_2/work/p5/software')
sys.path.insert(0, str(P5)); sys.path.insert(0, str(P5 / 'engine'))
from engine import early_field as ef  # noqa: E402
import render_pipeline as rp  # noqa: E402
from engine.fdn import FDN, fdn_delays_from_taps, build_inject_from_taps  # noqa: E402

from binaural_fitter.rear_images import BINAURAL_REAR32, LIVE_32_P5, REAR  # noqa: E402
from binaural_fitter.grid import grid_nodes, mirror_map, nearest_node, engine_head_relative  # noqa: E402
from binaural_fitter.reference import load_preset, load_table, image_to_ears, record_sos  # noqa: E402
from binaural_fitter.sosfit import sos_db  # noqa: E402
from binaural_fitter import tail_ic as T  # noqa: E402

REP = ROOT / "reports"; PL = ROOT / "plots" / "binaural"; PR = ROOT / "presets" / "binaural"
PRESETS = ["SADIE2_KU100", "SADIE2_KEMAR", "THK_KU100_FF"]
NS_PER_BIQUAD = 3.1  # VERIFIED reports/bench_sos_box.log (3.09-3.12 ns at K=6)
SCENES = {
    'default_A': dict(room=(6.0, 3.0, 8.0), src=(2.6, 1.2, 4.75), head=(3.0, 1.5, 1.5)),
    'default_B': dict(room=(6.0, 3.0, 8.0), src=(3.4, 1.2, 4.75), head=(3.0, 1.5, 1.5)),
    'small_A': dict(room=(4.0, 2.5, 5.0), src=(1.5, 1.2, 3.5), head=(2.0, 1.2, 1.2)),
    'hall_A': dict(room=(20.0, 10.0, 30.0), src=(8.0, 1.5, 15.0), head=(10.0, 1.5, 5.0)),
    'centre_A': dict(room=(6.0, 3.0, 8.0), src=(2.6, 1.2, 6.0), head=(3.0, 1.5, 4.0)),
}


def stand(head, space=0.18):
    return ef.MicStand(cx=head[0], cy=head[1], cz=head[2], space=space, car_omni=0.0,
                       mlalr=math.radians(-90), mralr=math.radians(90),
                       pattern_l='omni', pattern_r='omni', pattern_c='omni')


def taps_for(sc, imgs):
    return ef.compute_taps(sc['room'], sc['src'], stand(sc['head']), indices=list(imgs))


def dirs(sc, imgs, yaw=0.0):
    out = []
    for t in taps_for(sc, imgs):
        az, el, r = engine_head_relative(sc['head'], t.position, yaw)
        out.append(dict(n=list(t.n), az=float(az), el=float(el), r=float(r)))
    return out


def counts(dlist, nodes, mm):
    nn, _ = nearest_node(nodes, [d['az'] for d in dlist], [d['el'] for d in dlist])
    s = set(int(i) for i in nn)
    rec = s | set(int(mm[i]) for i in s)
    return s, rec


def entry_study():
    nodes = grid_nodes("G60"); mm = mirror_map(nodes)
    res = {}
    for set_name, imgs in (("LIVE_32", LIVE_32_P5), ("BINAURAL_REAR32", BINAURAL_REAR32)):
        r = {}
        for yaw in (0.0, 90.0, 180.0):
            for k, sc in SCENES.items():
                d = dirs(sc, imgs, yaw)
                s, rec = counts(d, nodes, mm)
                r[f"{k}@yaw{int(yaw)}"] = {
                    "filters_per_ear": len(s), "records_symmetric_shared": len(rec),
                    "rear_arrivals_abs_az_gt_90": int(sum(abs(x['az']) > 90 for x in d)),
                    "cpu_pct_48k_K6_both_ears": round(100 * 2 * len(s) * 6 * NS_PER_BIQUAD * 1e-9 * 48000, 2)}
            dA, dB = dirs(SCENES['default_A'], imgs, yaw), dirs(SCENES['default_B'], imgs, yaw)
            sA, _ = counts(dA, nodes, mm); sB, _ = counts(dB, nodes, mm)
            both = sA | sB
            recAB = both | set(int(mm[i]) for i in both)
            r[f"default_A+B@yaw{int(yaw)}"] = {"filters_per_ear": len(both), "records_symmetric_shared": len(recAB),
                                              "cpu_pct_48k_K6_both_ears": round(100 * 2 * len(both) * 6 * NS_PER_BIQUAD * 1e-9 * 48000, 2)}
        res[set_name] = r
    res["worst_case_fixed_bank"] = len(nodes)
    res["max_irs"] = 64
    return res


def front_back_study():
    """Rear image colour vs its front mirror (same lateral angle): fitted K6 records, 48 kHz."""
    out = {}
    band = np.geomspace(2000, 12000, 60)
    for pid in PRESETS:
        t = load_table(pid, 48000); nodes = t["nodes"]
        diffs = []
        for i, (az, el) in enumerate(nodes):
            if abs(el) > 1e-6 or abs(az) <= 90 or abs(abs(az) - 180) < 1e-6 and False:
                continue
            faz = math.copysign(180 - abs(az), az)
            j = int(nearest_node(nodes, [faz], [el])[0][0])
            d = sos_db(record_sos(t, i), band, 48000) - sos_db(record_sos(t, j), band, 48000)
            diffs.append(dict(rear_az=az, front_az=nodes[j][0], rms_db=float(np.sqrt(np.mean(d ** 2))),
                              mean_db=float(np.mean(d))))
        # rear image taps in the default scene
        p = load_preset(pid)
        sc = SCENES['default_A']
        taps = []
        for tp in taps_for(sc, BINAURAL_REAR32):
            if tp.n[2] >= 0:
                continue
            L, R = image_to_ears(p, t, sc['head'], 0.0, tp.position)
            fl = sos_db(record_sos(t, L.record), [4000.0], 48000)[0]
            fr = sos_db(record_sos(t, R.record), [4000.0], 48000)[0]
            bb = np.geomspace(1000, 8000, 40)
            ild_bb = float(np.mean(sos_db(record_sos(t, L.record), bb, 48000) - sos_db(record_sos(t, R.record), bb, 48000)))
            faz = math.copysign(180 - abs(L.az), L.az)
            jf = int(nearest_node(nodes, [faz], [L.el])[0][0])
            dd = sos_db(record_sos(t, L.record), band, 48000) - sos_db(record_sos(t, jf), band, 48000)
            taps.append(dict(n=list(tp.n), az=L.az, el=L.el, node=L.node, node_az_el=nodes[L.node],
                             front_mirror_node=jf, itd_us=1e3 * (R.delay_ms - L.delay_ms),
                             ild_4k_db=float(fl - fr), ild_1_8k_mean_db=ild_bb, rear_vs_front_rms_2_12k_db=float(np.sqrt(np.mean(dd ** 2)))))
        out[pid] = {"horizontal_rear_vs_front_mirror": diffs,
                    "horizontal_rms_db_median": float(np.median([x['rms_db'] for x in diffs])),
                    "horizontal_rms_db_min": float(np.min([x['rms_db'] for x in diffs])),
                    "default_scene_rear_taps": taps}
    return out


def mixer_design_study():
    out = {}
    fe = np.geomspace(100, 16000, 200)
    for pid in PRESETS:
        f, ic = T.target_ic(pid)
        tgt = np.interp(np.log(fe), np.log(f), ic)
        out[pid] = {}
        for fs in (44100, 48000):
            for N in (129, 257, 513, 1025):
                hp, hm, hc, hs = T.design_mixer(f, ic, fs, N)
                icd, gdb = T.designed_ic(hc, hs, fs, fe)
                err = icd - tgt
                m125 = fe >= 125
                out[pid][f"{fs}_N{N}"] = {"max_abs_ic_err_125_16k": float(np.max(np.abs(err[m125]))),
                                          "max_abs_ic_err_200_16k": float(np.max(np.abs(err[fe >= 200]))),
                                          "rms_ic_err_125_16k": float(np.sqrt(np.mean(err[m125] ** 2))),
                                          "power_dev_db_max": float(np.max(np.abs(gdb[m125]))),
                                          "latency_ms": 1e3 * (N // 2) / fs}
    return out


def fdn_polys(sc, imgs, sr=48000, length_s=1.0, g=0.999):
    taps = taps_for(sc, imgs)
    n = 32; ns = int(sr * length_s) + 1
    diffusion = rp.diffusion_scale_from_room(sc['room'])
    dff = [rp.tap_dff(t.n, None, master=rp.DIFFUSION_MASTER_LIVE) for t in taps]
    polys = {}
    for ch in ('l', 'r'):
        dly = fdn_delays_from_taps(taps, sr=sr, c=340.0, n=n, channel=ch)
        inj = build_inject_from_taps(taps, ns, sr, 340.0, n, channel=ch)
        dffs = rp.dffs_from_taps(taps, dff, diffusion, n=n, channel=ch)
        f = FDN(dly, g=g, room=sc['room'], sr=sr, c=340.0, depth_per_axis=rp.DEFAULT_DEPTH, peaking=True, n=n, dffs=dffs)
        polys[ch] = f.process_block_poly(inj)
    return polys


def engine_tail_study(N=513, length_s=4.0):
    out = {}
    pid = "SADIE2_KU100"
    f_t, ic_t = T.target_ic(pid)
    tgt_b = np.interp(np.log(T.THIRD_OCT), np.log(f_t), ic_t)
    curves = {}
    for scn in ("default_A", "small_A"):
        for set_name, imgs in (("BINAURAL_REAR32", BINAURAL_REAR32),):
            sr = 48000
            t0 = time.time()
            P = fdn_polys(SCENES[scn], imgs, sr, length_s=length_s)
            a0 = int(0.1 * sr)
            Lraw, Rraw = P['l'].sum(1), P['r'].sum(1)
            A, B = T.split_even_odd(P['l'], P['r'])
            hp, hm, _, _ = T.design_mixer(f_t, ic_t, sr, N)
            L, R = T.apply_mixer(A, B, hp, hm)
            d = N // 2
            res = {}
            for name, (x, y) in {"raw_L_R_loops": (Lraw, Rraw), "A_even_L_vs_B_odd_R": (A, B),
                                 "mixed_output": (L[a0 + d:], R[a0 + d:])}.items():
                if name != "mixed_output":
                    x, y = x[a0:], y[a0:]
                f, c = T.measure_ic(x, y, sr)
                b = T.band_ic(f, c, T.THIRD_OCT)
                res[name] = {"band_hz": T.THIRD_OCT.tolist(), "ic": b.tolist(),
                             "max_abs_err_vs_target": float(np.nanmax(np.abs(b - tgt_b))),
                             "rms_err_vs_target": float(np.sqrt(np.nanmean((b - tgt_b) ** 2)))}
                curves[(scn, name)] = (f, c)
            res["power_ratio_A_over_Lraw"] = float(np.mean(A[a0:] ** 2) / np.mean(Lraw[a0:] ** 2))
            res["power_ratio_mixedL_over_Lraw"] = float(np.mean(L[a0 + d:] ** 2) / np.mean(Lraw[a0:] ** 2))
            res["seconds"] = round(time.time() - t0, 1)
            out[f"{scn}/{set_name}"] = res
    # synthetic check: 20 s independent white noise, same mixer
    rng = np.random.default_rng(20260930)
    A, B = rng.standard_normal(20 * 48000), rng.standard_normal(20 * 48000)
    hp, hm, _, _ = T.design_mixer(f_t, ic_t, 48000, N)
    L, R = T.apply_mixer(A, B, hp, hm)
    f, c = T.measure_ic(L[N:], R[N:], 48000, nperseg=8192)
    b = T.band_ic(f, c, T.THIRD_OCT)
    out["synthetic_white_noise_20s"] = {"ic": b.tolist(), "max_abs_err_vs_target": float(np.max(np.abs(b - tgt_b)))}
    nf = []
    for s_ in range(30):
        a_, b_ = rng.standard_normal(int((length_s - 0.1) * 48000)), rng.standard_normal(int((length_s - 0.1) * 48000))
        f_, c_ = T.measure_ic(a_, b_, 48000)
        nf.append(float(np.nanmax(np.abs(T.band_ic(f_, c_, T.THIRD_OCT)))))
    out["estimator_noise_floor_max_abs_ic_independent_noise"] = {"length_s": length_s - 0.1, "median": float(np.median(nf)), "p95": float(np.percentile(nf, 95))}
    out["target_band_ic"] = tgt_b.tolist()
    out["render_length_s"] = length_s
    out["ntaps"] = N
    return out, curves


def plot_rear(entries):
    sc = SCENES['default_A']
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.5), subplot_kw={"projection": "polar"})
    for ax, (nm, imgs) in zip(axs, (("p5 LIVE_32 (current)", LIVE_32_P5), ("BINAURAL_REAR32 (locked)", BINAURAL_REAR32))):
        d = dirs(sc, imgs)
        for x in d:
            col = "C3" if x['n'][2] < 0 else ("k" if x['n'] == [0, 0, 0] else "C0")
            ax.plot(math.radians(x['az']), 1.0 / max(x['r'], 0.5), "o", color=col, ms=6, alpha=0.8)
        ax.set_theta_zero_location("N"); ax.set_theta_direction(1)  # az + = left (CCW), front up
        ax.set_title(f"{nm}\nimage arrivals, default scene A, head yaw 0\n(radius = 1/r, red = rear n_z<0, black = direct)", fontsize=9)
        ax.set_rticks([])
    k0 = entries["BINAURAL_REAR32"]
    fig.suptitle("Head-top view (front up, left to the left). Filters/ear default A: "
                 f"LIVE_32 {entries['LIVE_32']['default_A@yaw0']['filters_per_ear']}, REAR32 {k0['default_A@yaw0']['filters_per_ear']}", fontsize=10)
    fig.tight_layout()
    p = PL / "rear_images_top.png"; fig.savefig(p, dpi=110); plt.close(fig)
    return p


def plot_tail(eng, curves, design):
    pid = "SADIE2_KU100"
    f_t, ic_t = T.target_ic(pid)
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    ax = axs[0]
    ax.semilogx(f_t, ic_t, "k", lw=2.2, label="target: SADIE2_KU100 diffuse-field IC (MEASURED)")
    for (scn, name), (f, c) in curves.items():
        if scn != "default_A":
            continue
        st = {"raw_L_R_loops": ("C3", "raw L/R loop sums (today)"), "A_even_L_vs_B_odd_R": ("C1", "A = even lines L, B = odd lines R"),
              "mixed_output": ("C0", "after IC mixer (N=513)")}[name]
        b = T.band_ic(f, c, T.THIRD_OCT)
        ax.semilogx(T.THIRD_OCT, b, "o-", color=st[0], label=st[1], ms=4)
    ax.axhline(0, color="0.6", lw=0.8); ax.set_xlim(100, 16000); ax.set_ylim(-0.4, 1.05)
    ax.set_xlabel("Hz"); ax.set_ylabel("Re{IC}, 1/3-oct bands"); ax.grid(alpha=0.3, which="both")
    ax.set_title("p5 FDN tail (100 ms-4 s), default scene A, BINAURAL_REAR32, 48 kHz", fontsize=10); ax.legend(fontsize=8)
    ax = axs[1]
    Ns = [129, 257, 513, 1025]
    for fs, mk in ((48000, "o-"), (44100, "s--")):
        ax.plot(Ns, [design[pid][f"{fs}_N{N}"]["max_abs_ic_err_125_16k"] for N in Ns], mk, label=f"max |IC err| 125 Hz-16 kHz, {fs}")
        ax.plot(Ns, [design[pid][f"{fs}_N{N}"]["max_abs_ic_err_200_16k"] for N in Ns], mk, alpha=0.5, label=f"max |IC err| 200 Hz-16 kHz, {fs}")
    ax.set_xscale("log", base=2); ax.set_xlabel("FIR taps (latency (N-1)/2)"); ax.set_ylabel("designed IC error")
    ax.grid(alpha=0.3); ax.legend(fontsize=8); ax.set_title("Mixer FIR length trade-off (design, SADIE2_KU100)", fontsize=10)
    fig.tight_layout()
    p = PL / f"tail_ic_{pid}.png"; fig.savefig(p, dpi=110); plt.close(fig)
    return p


def export(design_N):
    (PR / "image_sets").mkdir(parents=True, exist_ok=True)
    (PR / "image_sets" / "binaural_rear32.json").write_text(json.dumps({
        "schema": "mic_fitter.binaural_image_set.v1", "id": "binaural_rear32",
        "status": "LOCKED 2026-09-30 (Idle): rear images in binaural mode; selection rule ASSUMED (design)",
        "derived_from": "p5 engine.early_field.LIVE_32 (order kept; 7 slots replaced)",
        "indices": [list(n) for n in BINAURAL_REAR32], "rear_indices": [list(n) for n in REAR],
        "replaced_slots": {"7": "(0,1,1) duplicate -> (0,-1,1)", "9": "(0,0,1) duplicate -> (0,0,-1)",
                           "24": "(-1,-2,0) duplicate -> (-1,-1,0)", "10": "(1,2,1) -> (1,0,-1)",
                           "25": "(-1,2,1) -> (-1,0,-1)", "14": "(1,-2,1) -> (0,1,-1)", "29": "(-1,-2,1) -> (0,-1,-1)"},
        "direct_index": 2}, indent=1))
    (PR / "tail_ic").mkdir(parents=True, exist_ok=True)
    for pid in PRESETS:
        f, ic = T.target_ic(pid)
        d = {"schema": "mic_fitter.binaural_tail_ic.v1", "preset_id": pid,
             "provenance": "MEASURED: area-weighted diffuse-field interaural coherence Re{IC} of the preset's SOFA HRIRs",
             "target": {"f_hz": f.tolist(), "ic_real": ic.tolist()},
             "method": "A = sqrt2*sum(even lines, L loop), B = sqrt2*sum(odd lines, R loop); M=A+B, S=A-B; "
                       "L=(hp*M+hm*S)/2, R=(hp*M-hm*S)/2; hp=hc+hs, hm=hc-hs, hc=cos(phi), hs=sin(phi), sin(2phi)=IC",
             "ntaps": design_N, "latency_samples": design_N // 2, "window": "hann", "linear_phase": True, "fir": {}}
        for fs in (44100, 48000):
            hp, hm, _, _ = T.design_mixer(f, ic, fs, design_N)
            d["fir"][str(fs)] = {"hp": [float(x) for x in hp], "hm": [float(x) for x in hm]}
        (PR / "tail_ic" / f"{pid}.json").write_text(json.dumps(d))


if __name__ == "__main__":
    N_SHIP = int(sys.argv[1]) if len(sys.argv) > 1 else 513
    ent = entry_study()
    fb = front_back_study()
    des = mixer_design_study()
    eng, curves = engine_tail_study(N_SHIP)
    (REP / "rear_images.json").write_text(json.dumps({"entries": ent, "front_back": fb,
                                                       "image_set": [list(n) for n in BINAURAL_REAR32]}, indent=1))
    (REP / "tail_ic.json").write_text(json.dumps({"design": des, "engine_check": eng}, indent=1))
    export(N_SHIP)
    print(plot_rear(ent), plot_tail(eng, curves, des))
    for k in ("LIVE_32", "BINAURAL_REAR32"):
        for s, v in ent[k].items():
            print(k, s, v)
    for pid, v in fb.items():
        print(pid, "rear-vs-front-mirror horizontal RMS 2-12k median %.2f min %.2f" % (v["horizontal_rms_db_median"], v["horizontal_rms_db_min"]))
        for x in v["default_scene_rear_taps"]:
            print("   ", x["n"], "az %.1f el %.1f itd %.0f us ild4k %.1f ild1-8k %.1f dB rear-vs-front %.1f dB" % (x["az"], x["el"], x["itd_us"], x["ild_4k_db"], x["ild_1_8k_mean_db"], x["rear_vs_front_rms_2_12k_db"]))
    for pid in PRESETS:
        print(pid, {k: (round(v["max_abs_ic_err_125_16k"], 3), round(v["max_abs_ic_err_200_16k"], 3), round(v["power_dev_db_max"], 3)) for k, v in des[pid].items()})
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: (vv["max_abs_err_vs_target"] if isinstance(vv, dict) else vv) for kk, vv in v.items()}) for k, v in eng.items() if k not in ("target_band_ic",)}, indent=1))
