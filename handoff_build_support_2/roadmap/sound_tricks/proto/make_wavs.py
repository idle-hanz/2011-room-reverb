"""sound_tricks A/B WAVs: 24-bit 48 kHz stereo, equal RMS within each group, one shared gain to -1 dBFS peak."""
import numpy as np, json, struct, math
from scipy import signal
from scipy.io import wavfile
SR = 48000; OUT = "/workspace/build_support_2/roadmap/sound_tricks/ab"

def write24(path, x):
    x = np.clip(x, -1.0, 1.0 - 2 ** -23)
    q = np.round(x * 2 ** 23).astype(np.int32)
    b = (q.reshape(-1).astype("<i4").view(np.uint8).reshape(-1, 4)[:, :3]).tobytes()
    nch = x.shape[1]
    hdr = b"RIFF" + struct.pack("<I", 36 + len(b)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, nch, SR, SR * nch * 3, nch * 3, 24) + b"data" + struct.pack("<I", len(b))
    open(path, "wb").write(hdr + b)

def dry_sources():
    g = np.load("/workspace/build_support_2/roadmap/robotic_1240/w/guitar.npy").astype(float)
    if g.ndim > 1: g = g.mean(1)
    sr, s = wavfile.read("/workspace/early-field/phone_dry_snare.wav")
    s = s.astype(float) / 32768.0
    if s.ndim > 1: s = s.mean(1)
    s = signal.resample_poly(s, 160, 147)
    hits = np.zeros(int(4.0 * SR))
    for t in (0.1, 1.6):                     # two hits, 1.5 s apart, so the full decay is audible
        hits[int(t * SR):int(t * SR) + len(s)] += s
    return {"guitar": g, "snare": hits}

def direct_scaled(ir, gain_db):
    """Scale the first arrival only (window -0.3..+1.2 ms round the onset); its loop feed is untouched."""
    out = ir.copy()
    for ch in range(ir.shape[1]):
        a = np.abs(ir[:, ch]); n0 = int(np.argmax(a >= 0.1 * a.max()))
        i0, i1 = n0 - int(0.0003 * SR), n0 + int(0.0012 * SR)
        w = np.ones(i1 - i0); r = int(0.0002 * SR)
        w[:r] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, r)); w[-r:] = w[:r][::-1]
        g = 10 ** (gain_db / 20)
        out[i0:i1, ch] = ir[i0:i1, ch] * (1 - w + w * g)
    return out

N0 = None
def drr_db(ir):
    m = ir[:, 0]; n0 = N0
    E = m ** 2; d = E[n0 - 15:n0 + 58].sum()
    return 10 * math.log10(d / (E.sum() - d))

ir_A = np.load("ir_ortf_noC.npy")
_a = np.abs(ir_A[:, 0]); N0 = int(np.argmax(_a >= 0.1 * _a.max()))
groups = {
  "1_natural_decay": {"A_today_flat": ir_A, "B1_air_in_loop": np.load("ir_p1_air.npy"), "B2_air_plus_surfaces": np.load("ir_p1_airmatc.npy")},
  "2_direct_level": {"A_today": ir_A, "B_direct_minus9dB": direct_scaled(ir_A, -9.0), "C_direct_minus18dB_physical": direct_scaled(ir_A, -18.0)},
}
src = dry_sources(); meta = {}
for gname, irs in groups.items():
    meta[gname] = {k: {"DRR_dB_L": round(drr_db(v), 1)} for k, v in irs.items()}
    for sname, x in src.items():
        ys = {k: signal.fftconvolve(x[:, None], v, axes=0) for k, v in irs.items()}
        rms = {k: math.sqrt(float(np.mean(y ** 2))) for k, y in ys.items()}
        ref = min(rms.values())
        ys = {k: y * ref / rms[k] for k, y in ys.items()}
        pk = max(float(np.max(np.abs(y))) for y in ys.values())
        g = 10 ** (-1 / 20) / pk
        for k, y in ys.items():
            write24(f"{OUT}/{gname}__{sname}__{k}.wav", y * g)
        meta[gname][f"shared_gain_{sname}_dB"] = round(20 * math.log10(g), 2)
json.dump(meta, open(f"{OUT}/ab_levels.json", "w"), indent=1)
print(json.dumps(meta, indent=1))
