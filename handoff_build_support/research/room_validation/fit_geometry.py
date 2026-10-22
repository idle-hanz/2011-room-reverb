"""Fit shoebox wall planes for BRAS CR2 from measured first-order reflection arrivals.
Each wall's image depends on one plane coordinate only, so each wall is a 1-D scan:
score(plane) = mean over the 10 LS/MP pairs of the peak (1-8 kHz Hilbert envelope, normalised to the
direct peak) within +-0.2 ms of the predicted image delay relative to the measured direct onset.
Output: fitted planes + the geometry actually used by run_validation.py (written to geometry_fit.json)."""
import json, sys, os
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bras_cr2 as B, analysis as A
import warnings; warnings.filterwarnings("ignore")

sr, c = B.SR, B.C_AIR
BAND = tuple(float(v) for v in os.environ.get("FIT_BAND", "1000,8000").split(","))
sos = signal.butter(4, list(BAND), btype="band", fs=sr, output="sos")
data = {}
for ls in B.SOURCES:
    for mp in B.RECEIVERS:
        x = B.load_rir(ls, mp)
        i0 = A.onset(x)
        if os.environ.get("FIT_MF", "1") == "1":
            # matched filter with the measured direct sound (sharpens the dodecahedron's smeared pulse)
            tpl = x[i0 - 20:i0 + 70] * np.hanning(90)
            y = signal.correlate(x, tpl, mode="same", method="fft")
            y = np.roll(y, -(len(tpl) // 2 - 20 - 0))  # keep the direct near its onset index
            env = np.abs(signal.hilbert(signal.sosfiltfilt(sos, y)))
        else:
            env = np.abs(signal.hilbert(signal.sosfiltfilt(sos, x)))
        pk = env[max(0, i0 - 20): i0 + 40].max()
        data[(ls, mp)] = [env / pk, i0 + int(np.argmax(env[max(0, i0 - 20): i0 + 40])) - 20]
# Absolute timing: one global latency (median of measured direct peak minus geometric direct time),
# because per-IR onsets scatter by up to +-0.7 ms (dodecahedron driver nearest the mic arrives early).
lat = np.median([v[1] - np.linalg.norm(np.subtract(B.SOURCES[k[0]], B.RECEIVERS[k[1]])) / c * sr for k, v in data.items()])
ONSET_SCATTER = {f"LS{k[0]}_MP{k[1]}": round(float(v[1] - lat - np.linalg.norm(np.subtract(B.SOURCES[k[0]], B.RECEIVERS[k[1]])) / c * sr), 1) for k, v in data.items()}
for k, v in data.items():
    v[1] = lat + np.linalg.norm(np.subtract(B.SOURCES[k[0]], B.RECEIVERS[k[1]])) / c * sr

def image(s, axis, plane):
    p = list(s); p[axis] = 2 * plane - p[axis]; return p

def score(axis, plane, win_ms=0.2):
    w = int(win_ms * 1e-3 * sr); vals = []
    for (ls, mp), (env, i0) in data.items():
        s, r = B.SOURCES[ls], B.RECEIVERS[mp]
        dd = np.linalg.norm(np.subtract(s, r)); di = np.linalg.norm(np.subtract(image(s, axis, plane), r))
        k = int(round(i0 + (di - dd) / c * sr))
        vals.append(env[k - w:k + w + 1].max() if k + w < len(env) else 0)
    return np.mean(vals), vals

scans = {"x0": (0, np.arange(-3.6, -1.9, 0.005)), "x1": (0, np.arange(2.3, 3.8, 0.005)),
         "y0": (1, np.arange(-4.8, -3.2, 0.005)), "y1": (1, np.arange(3.2, 4.9, 0.005)),
         "z0": (2, np.arange(-0.3, 0.3, 0.005)), "z1": (2, np.arange(2.5, 3.4, 0.005))}
res = {}
if __name__ == "__main__":
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 3, figsize=(13, 6))
    for ax, (k, (axis, grid)) in zip(axs.flat, scans.items()):
        s = np.array([score(axis, g)[0] for g in grid])
        best = float(grid[np.argmax(s)])
        res[k] = dict(best=round(best, 3), score=round(float(s.max()), 3),
                      per_pair=[round(float(v), 3) for v in score(axis, best)[1]])
        ax.plot(grid, s); ax.axvline(best, color="r"); ax.set_title(f"{k}: best {best:.3f} m (score {s.max():.2f})")
        ax.set_xlabel("plane coordinate (m, BRAS frame)"); ax.set_ylabel("mean env. at predicted time")
    fig.tight_layout(); fig.savefig(os.path.join(os.path.dirname(__file__), "plots", "geometry_fit_scans.png"), dpi=110)
    W = res["x1"]["best"] - res["x0"]["best"]; Lz = res["y1"]["best"] - res["y0"]["best"]; H = res["z1"]["best"] - res["z0"]["best"]
    res["latency_samples"] = round(float(lat), 1); res["direct_peak_scatter_samples"] = ONSET_SCATTER
    res["box"] = dict(W_x=round(W, 3), L_y=round(Lz, 3), H_z=round(H, 3), volume=round(W * Lz * H, 1), bras_volume=B.VOLUME_M3)
    json.dump(res, open(os.path.join(os.path.dirname(__file__), "geometry_fit.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))
