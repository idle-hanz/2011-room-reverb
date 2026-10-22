# UAD round-2 renderer. Runs on Idle's PC in C:\Users\IdleHanz\uad_measure\.venv (read-only for the product).
# Usage: python render2.py jobs.json inputs_dir out_dir
# Job: {"id","plugin","params":{..},"input":"name.npy","keep":[[a,b],...] (input-sample ranges, optional),
#       "pre_s":1.0 (silence pre-roll, default 1), "chunk":0 (process in chunks of N samples, 0 = whole)}
# Input .npy: float32, shape (N,) mono (copied to both channels) or (2,N).
# Output: out_dir/id.npz with y (channels, kept samples; one channel if L==R exactly) and id.json meta.
import sys, os, json, time, ctypes, numpy as np
from pedalboard import load_plugin
try:
    k32 = ctypes.windll.kernel32
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    PRIO_OK = bool(k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00004000))  # BELOW_NORMAL
except Exception:
    PRIO_OK = False
SR = 48000
ROOT = r"C:\Program Files\Common Files\VST3"
_cache = {}
def plug(name):
    return load_plugin(os.path.join(ROOT, name + ".vst3", "Contents", "x86_64-win", name + ".vst3"))

def run(job, indir, outdir):
    t0 = time.time()
    pl = plug(job["plugin"])
    for k, v in job.get("params", {}).items():
        if isinstance(v, str) and v.startswith("~"):   # nearest valid string value (numeric match)
            import re
            want = float(v[1:]); best = None
            for s_ in pl.parameters[k].valid_values:
                m_ = re.match(r"\s*([-+]?[0-9.]+)\s*(k?)", str(s_))
                if not m_: continue
                val = float(m_.group(1)) * (1000.0 if m_.group(2) == "k" else 1.0)
                if best is None or abs(val - want) < abs(best[0] - want): best = (val, s_)
            v = best[1]
        setattr(pl, k, v)
    applied = {}
    for k in pl.parameters:
        p = pl.parameters[k]
        try: applied[k] = p.string_value
        except Exception: applied[k] = str(getattr(pl, k))
    if "spec" in job:
        import siglib2
        x = siglib2.make(job["spec"]).astype(np.float32)
    else:
        x = np.load(os.path.join(indir, job["input"])).astype(np.float32)
    if x.ndim == 1: x = np.stack([x, x])
    if "gain_db" in job: x = (x * np.float32(10 ** (job["gain_db"] / 20.0))).astype(np.float32)
    npre = int(job.get("pre_s", 1.0) * SR)
    X = np.concatenate([np.zeros((2, npre), np.float32), x], axis=1)
    ch = int(job.get("chunk", 0))
    if ch > 0:
        outs = []
        for i in range(0, X.shape[1], ch):
            outs.append(pl.process(X[:, i:i + ch], SR, reset=(i == 0)))
        Y = np.concatenate(outs, axis=1)
    else:
        Y = pl.process(X, SR, reset=True)
    Y = Y[:, npre:]
    same = bool(np.array_equal(Y[0], Y[1]))
    if "keep" in job:
        Yk = np.concatenate([Y[:, a:b] for a, b in job["keep"]], axis=1)
    else:
        Yk = Y
    if same: Yk = Yk[:1]
    if job.get("store") == "env":
        w = int(job.get("env_win", 48)); dec = int(job.get("env_dec", 12))
        def env(v):
            c = np.concatenate([[0.0], np.cumsum(v.astype(np.float64) ** 2)]); m = (c[w:] - c[:-w]) / w
            e = np.sqrt(2 * np.maximum(m, 0)); pad = w // 2
            return np.concatenate([np.full(pad, e[0]), e, np.full(len(v) - len(e) - pad, e[-1])])[::dec]
        E = np.stack([env(Yk[c]) for c in range(Yk.shape[0])]).astype(np.float32)
        Ei = env(x[0])[None, :].astype(np.float32)
        np.savez_compressed(os.path.join(outdir, job["id"] + ".npz"), env=E, env_in=Ei, dec=dec, win=w)
    else:
        np.savez_compressed(os.path.join(outdir, job["id"] + ".npz"), y=Yk.astype(np.float32))
    meta = {"id": job["id"], "plugin": job["plugin"], "plugin_name": pl.name, "set": job.get("params", {}),
            "applied": applied, "reported_latency": int(pl.reported_latency_samples), "input": job.get("input"), "spec": job.get("spec"),
            "keep": job.get("keep"), "lr_identical": same, "render_s": round(time.time() - t0, 2),
            "out_peak": float(np.abs(Y).max()), "n": int(Y.shape[1])}
    json.dump(meta, open(os.path.join(outdir, job["id"] + ".json"), "w"), indent=1)
    return meta

if __name__ == "__main__":
    jobs = json.load(open(sys.argv[1])); indir = sys.argv[2]; outdir = sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    T = time.time(); n = 0
    print("priority_below_normal", PRIO_OK, flush=True)
    for j in jobs:
        if os.path.exists(os.path.join(outdir, j["id"] + ".json")): continue
        try:
            m = run(j, indir, outdir); n += 1
            print("OK", j["id"], m["render_s"], "s peak %.3f" % m["out_peak"], "LR" if not m["lr_identical"] else "", flush=True)
        except Exception as e:
            print("ERR", j["id"], repr(e)[:300], flush=True)
    print("DONE", n, "jobs", round(time.time() - T, 1), "s", flush=True)
