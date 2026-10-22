"""SURFACES IN THE LOOP A/B WAVs: 24-bit 48 kHz, equal RMS within a group, one shared gain to -1 dBFS peak."""
import sys, json, math, numpy as np
sys.path.insert(0, "/workspace/st_work/proto")
import struct
SR = 48000
def write24(path, x):   # same 24-bit PCM writer as proto/make_wavs.py (copied: importing that script re-renders Task-1 WAVs)
    x = np.clip(x, -1.0, 1.0 - 2 ** -23)
    q = np.round(x * 2 ** 23).astype(np.int32)
    b = (q.reshape(-1).astype("<i4").view(np.uint8).reshape(-1, 4)[:, :3]).tobytes()
    nch = x.shape[1]
    hdr = b"RIFF" + struct.pack("<I", 36 + len(b)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, nch, SR, SR * nch * 3, nch * 3, 24) + b"data" + struct.pack("<I", len(b))
    open(path, "wb").write(hdr + b)
from scipy import signal
from scipy.io import wavfile
OUT = "/workspace/build_support_2/roadmap/sound_tricks/surfaces_ab"
import os; os.makedirs(OUT, exist_ok=True)
g = np.load("/workspace/build_support_2/roadmap/robotic_1240/w/guitar.npy").astype(float)
if g.ndim > 1: g = g.mean(1)
sr, s = wavfile.read("/workspace/early-field/phone_dry_snare.wav"); s = s.astype(float) / 32768.0
if s.ndim > 1: s = s.mean(1)
s = signal.resample_poly(s, 160, 147)
sn = np.zeros(int(8.0 * SR))
for t in (0.1, 4.0): sn[int(t * SR):int(t * SR) + len(s)] += s
SRC = {"guitar": g, "snare": sn}
A0 = np.load("/workspace/st_work/proto/ir_ortf_noC.npy")
ld = lambda n: np.load(f"/workspace/st_work/proto2/ir_{n}.npy")
G = {
 "3_surfaces_default_room": {"A_flat_2011": A0, "B_room_average": ld("g3_avg_cal"), "C_directional": ld("g3_dir_cal"), "D_directional_with_room_shell": ld("g3_dir_shell_cal")},
 "4_material_contrast": {"studio_flat": ld("g4_studio_flat"), "studio_room_average": ld("g4_studio_avg_cal"), "studio_directional": ld("g4_studio_dir_cal"),
                         "brick_flat": ld("g4_brick_flat"), "brick_room_average": ld("g4_brick_avg_cal"), "brick_directional": ld("g4_brick_dir_cal")},
 "5_auto_treat": {"A_untreated": ld("g5_untreated_cal"), "B_broadband_only": ld("g5_broadband_cal"), "C_auto_treated_panels": ld("g5_treated_cal")},
}
meta = {}
for gname, irs in G.items():
    meta[gname] = {}
    for sname, x in SRC.items():
        ys = {k: signal.fftconvolve(x[:, None], v, axes=0) for k, v in irs.items()}
        n = max(len(y) for y in ys.values())
        ys = {k: np.pad(y, ((0, n - len(y)), (0, 0))) for k, y in ys.items()}
        rms = {k: math.sqrt(float(np.mean(y ** 2))) for k, y in ys.items()}
        ref = min(rms.values()); ys = {k: y * ref / rms[k] for k, y in ys.items()}
        pk = max(float(np.max(np.abs(y))) for y in ys.values()); gg = 10 ** (-1 / 20) / pk
        for k, y in ys.items():
            write24(f"{OUT}/{gname}__{sname}__{k}.wav", y * gg)
        meta[gname][sname] = dict(shared_gain_db=round(20 * math.log10(gg), 2), rms_trim_db={k: round(20 * math.log10(ref / rms[k]), 2) for k in ys})
json.dump(meta, open(f"{OUT}/ab_levels.json", "w"), indent=1)
print(json.dumps(meta, indent=1))
