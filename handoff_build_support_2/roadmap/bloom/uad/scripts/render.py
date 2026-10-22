# UAD measurement renderer. Runs on Idle's PC in C:\Users\IdleHanz\uad_measure\.venv
# Usage: python render.py jobs.json outdir
# Each job: {"id","plugin","params":{k:v},"sig":{...}}. One process, sequential, modest CPU.
import sys, os, json, time, numpy as np
from pedalboard import load_plugin
SR = 48000
ROOT = r"C:\Program Files\Common Files\VST3"
PRE = 1.0  # silence preroll seconds (parameter smoothing / settle), removed from output

def plug(name):
    return load_plugin(os.path.join(ROOT, name + ".vst3", "Contents", "x86_64-win", name + ".vst3"))

def db2a(d): return 10 ** (d / 20.0)

def tone_seg(level_db, dur, f=1000.0, t0=0):
    n = int(round(dur * SR)); t = (np.arange(n) + t0) / SR
    return db2a(level_db) * np.sin(2 * np.pi * f * t)  # peak amplitude = level (dBFS peak)

def build(sig):
    k = sig["kind"]; f = sig.get("f", 1000.0)
    if k in ("stair", "tonestair"):
        segs = []; tt = 0
        for L in sig["levels"]:
            segs.append(tone_seg(L, sig["step_s"], f, tt)); tt += len(segs[-1])
        return np.concatenate(segs)
    if k == "burst":  # probe -> burst -> probe; continuous phase
        parts = [(sig["probe_db"], sig["pre_s"]), (sig["burst_db"], sig["burst_s"]), (sig["probe_db"], sig["tail_s"])]
        segs = []; tt = 0
        for L, d in parts:
            segs.append(tone_seg(L, d, f, tt)); tt += len(segs[-1])
        return np.concatenate(segs)
    if k == "multiburst":  # repeated bursts then tail
        segs = []; tt = 0
        seq = [(sig["probe_db"], sig["pre_s"])]
        for i in range(sig["n"]):
            seq += [(sig["burst_db"], sig["burst_s"]), (sig["probe_db"], sig["gap_s"])]
        seq[-1] = (sig["probe_db"], sig["tail_s"])
        for L, d in seq:
            segs.append(tone_seg(L, d, f, tt)); tt += len(segs[-1])
        return np.concatenate(segs)
    if k == "tone":
        return tone_seg(sig["level_db"], sig["dur_s"], f)
    if k == "noise":
        rng = np.random.default_rng(1); n = int(sig["dur_s"] * SR)
        x = rng.standard_normal(n); x *= db2a(sig["level_db"]) / np.sqrt(np.mean(x ** 2)); return x
    if k == "ess":
        T = sig["dur_s"]; f1, f2 = 10.0, 23000.0; n = int(T * SR); t = np.arange(n) / SR
        Lr = T / np.log(f2 / f1)
        x = np.sin(2 * np.pi * f1 * Lr * (np.exp(t / Lr) - 1))
        fade = int(0.02 * SR); w = np.ones(n); w[:fade] = 0.5 - 0.5 * np.cos(np.pi * np.arange(fade) / fade); w[-fade:] = w[:fade][::-1]
        x = x * w * db2a(sig["level_db"])
        return np.concatenate([x, np.zeros(int(sig.get("pad_s", 1.0) * SR))])
    raise ValueError(k)

def env(y):  # one-cycle (48-sample at 1 kHz) RMS -> peak amplitude, centred
    w = int(round(SR / 1000.0))
    c = np.concatenate([[0.0], np.cumsum(y.astype(np.float64) ** 2)])
    m = (c[w:] - c[:-w]) / w
    e = np.sqrt(2 * np.maximum(m, 0)); pad = w // 2
    return np.concatenate([np.full(pad, e[0]), e, np.full(len(y) - len(e) - pad, e[-1])])

def harmonics(y, f0, nh=10):
    n = SR  # 1 s window, integer cycles for f0 in {20,50,100,1000,...}
    seg = y[-n:] * np.hanning(n)
    sp = np.abs(np.fft.rfft(seg)) * 2 / np.sum(np.hanning(n))
    bins = [int(round(f0 * h)) for h in range(1, nh + 1) if f0 * h < SR / 2 - 100]
    amps = [float(np.max(sp[max(b - 2, 0):b + 3])) for b in bins]
    fund = amps[0]
    tot = np.sqrt(np.sum(sp ** 2)); 
    # THD+N: everything except +-5 bins around fundamental and below 15 Hz
    mask = np.ones_like(sp, bool); b0 = bins[0]; mask[max(b0 - 5, 0):b0 + 6] = False; mask[:15] = False
    thdn = float(np.sqrt(np.sum(sp[mask] ** 2) / 1.5) / fund)  # /1.5 hann noise power correction approx
    return {"fund_db": 20 * np.log10(fund + 1e-30), "h_db_rel": [20 * np.log10(a / fund + 1e-30) for a in amps[1:]],
            "thd_pct": float(100 * np.sqrt(np.sum(np.array(amps[1:]) ** 2)) / fund), "thdn_pct": 100 * thdn}

def run(job, outdir):
    t0 = time.time()
    pl = plug(job["plugin"])
    applied = {}
    for k, v in job.get("params", {}).items():
        setattr(pl, k, v)
    for k in pl.parameters:
        p = pl.parameters[k]
        try: applied[k] = p.string_value
        except Exception: applied[k] = str(getattr(pl, k))
    lat = int(pl.reported_latency_samples)
    x = build(job["sig"]).astype(np.float32)
    npre = int(PRE * SR)
    xx = np.concatenate([np.zeros(npre, np.float32), x])
    X = np.stack([xx, xx])
    Y = pl.process(X, SR, reset=True)
    y = Y[0, npre:]; yR = Y[1, npre:]
    meta = {"id": job["id"], "plugin": job["plugin"], "plugin_name": pl.name, "set": job.get("params", {}), "applied": applied,
            "reported_latency": lat, "sig": job["sig"], "render_s": round(time.time() - t0, 2),
            "out_peak": float(np.abs(y).max()), "lr_maxdiff": float(np.abs(y - yR).max())}
    kind = job["sig"]["kind"]
    res = {}
    if kind in ("stair", "burst", "multiburst", "tone_env"):
        ei = env(x); eo = env(y)
        dec = 12
        res["env_in"] = ei[::dec].astype(np.float32); res["env_out"] = eo[::dec].astype(np.float32); res["dec"] = dec
    if kind == "tonestair":
        st = int(round(job["sig"]["step_s"] * SR)); f0 = job["sig"].get("f", 1000.0); steps = []
        for k_, L in enumerate(job["sig"]["levels"]):
            seg = y[k_ * st:(k_ + 1) * st]
            h = harmonics(seg, f0); h["in_db"] = L; h["out_peak"] = float(np.abs(seg[-SR:]).max()); steps.append(h)
        meta["steps"] = steps
    if kind == "tone":
        meta["harm"] = harmonics(y, job["sig"].get("f", 1000.0)); meta["in_db"] = job["sig"]["level_db"]
    if kind in ("noise", "ess"):
        res["y"] = y.astype(np.float32)
    if kind == "noise" or job["sig"].get("xcorr"):
        n = min(len(x), 4 * SR); a = x[:n].astype(np.float64); b = y[:n].astype(np.float64)
        F = np.fft.rfft(a, 2 * n); G = np.fft.rfft(b, 2 * n); cc = np.fft.irfft(np.conj(F) * G)
        lag = int(np.argmax(np.abs(cc[:2000]))); meta["xcorr_lag"] = lag
        meta["noise_gain_db"] = float(20 * np.log10(np.sqrt(np.mean(b ** 2)) / np.sqrt(np.mean(a ** 2))))
    np.savez_compressed(os.path.join(outdir, job["id"] + ".npz"), **res)
    json.dump(meta, open(os.path.join(outdir, job["id"] + ".json"), "w"), indent=1)
    return meta

if __name__ == "__main__":
    jobs = json.load(open(sys.argv[1])); outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    skip = "--force" not in sys.argv
    for j in jobs:
        if skip and os.path.exists(os.path.join(outdir, j["id"] + ".json")): continue
        try:
            m = run(j, outdir)
            extra = (" harm thd=%.4f%% fund=%.1f" % (m["harm"]["thd_pct"], m["harm"]["fund_db"])) if "harm" in m else ""
            print("OK", j["id"], m["render_s"], "s peak %.3f" % m["out_peak"], ("lag %s" % m.get("xcorr_lag")) if "xcorr_lag" in m else "", extra, flush=True)
        except Exception as e:
            print("ERR", j["id"], repr(e)[:300], flush=True)
