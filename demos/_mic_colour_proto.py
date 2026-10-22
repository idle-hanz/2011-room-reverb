import math, json
from pathlib import Path
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    HAS_MPL = False

SR = 48000.0
RES = 10000.0  # dynamic Mic Response
CO = 1.0
OUT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb\demos\mic_colour_models")
OUT.mkdir(parents=True, exist_ok=True)

def f_to_p(f):
    return 69.0 + 12.0 * math.log(max(f, 1e-6) / 440.0, 2.0)

def p_to_f(p):
    return 440.0 * (2.0 ** ((p - 69.0) / 12.0))

def mic_power_gain(dir_val, co=1.0):
    ad = abs(float(dir_val))
    if ad < 1e-15:
        return 1.0
    try:
        g = 1.0 - (2.0 * ad) ** float(co)
    except OverflowError:
        g = 0.0
    return 0.0 if g < 0.0 else (1.0 if g > 1.0 else g)

def mic_cutoff_hz(res_hz, gain):
    g = max(0.0, min(1.0, float(gain)))
    if g <= 0.0:
        return p_to_f(0.0)
    if g >= 1.0:
        return float(res_hz)
    return p_to_f(f_to_p(res_hz) * g)

def one_pole_H(f, fc, sr=SR):
    # H(z) = g / (1 - (1-g) z^-1), z=e^{j w}; DC-normalized already
    if fc <= 0:
        return np.ones_like(f, dtype=np.complex128)
    g = 1.0 - math.exp(-2.0 * math.pi * min(fc, 0.49 * sr) / sr)
    w = 2.0 * math.pi * f / sr
    zinv = np.exp(-1j * w)
    return g / (1.0 - (1.0 - g) * zinv)

def rbj_highshelf_H(f, f0, gain_db, sr=SR, slope=1.0):
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = (sinw / 2.0) * math.sqrt(max((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0, 0.0))
    two = 2.0 * math.sqrt(A) * alpha
    b0 = A * ((A + 1.0) + (A - 1.0) * cosw + two)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cosw)
    b2 = A * ((A + 1.0) + (A - 1.0) * cosw - two)
    a0 = (A + 1.0) - (A - 1.0) * cosw + two
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cosw)
    a2 = (A + 1.0) - (A - 1.0) * cosw - two
    w = 2.0 * math.pi * f / sr
    z = np.exp(1j * w)
    z2 = z * z
    num = b0 + b1 / z + b2 / z2
    den = a0 + a1 / z + a2 / z2
    return num / den

def model_A_structure_radians(theta_rad):
    """Current engine: pass |theta| radians into Structure Gain law."""
    g = mic_power_gain(theta_rad, CO)
    return mic_cutoff_hz(RES, g)

def model_B_dir_normalized(theta_rad):
    """LIKELY fix: map angle to Structure-like Dir in ~0..0.5 via |sin(theta/2)| or |theta|/pi."""
    # Use |theta|/pi so 180deg -> 0.5 -> gain 0; 90deg -> 0.25 -> gain 0.5
    d = abs(theta_rad) / math.pi
    g = mic_power_gain(d, CO)
    return mic_cutoff_hz(RES, g)

def model_C_shelf_db(theta_rad):
    """ASSUMED: high-shelf depth vs angle, corner ~3.5 kHz."""
    # 0 deg: 0 dB; 90: -6; 180: -12 (smooth with 1-cos)
    t = 0.5 * (1.0 - math.cos(min(abs(theta_rad), math.pi)))  # 0..1
    return -12.0 * t

def model_D_combo(theta_rad):
    """Recommended: mild high-shelf + 1-pole with fc floor (never phone-like)."""
    t = 0.5 * (1.0 - math.cos(min(abs(theta_rad), math.pi)))
    shelf_db = -8.0 * t
    # softer LP: use normalized Dir, then floor fc at ~2.5 kHz * (1-0.5*t)
    d = abs(theta_rad) / math.pi
    g = mic_power_gain(d, CO)
    fc = mic_cutoff_hz(RES, g)
    fc_floor = 2500.0 + 5500.0 * (1.0 - t)  # on-axis ~8k effective floor blend
    # Blend Structure pitch-law toward a gentle floor so off-axis never tanks
    fc_soft = max(fc, 1800.0 + 2200.0 * (1.0 - t))
    return shelf_db, fc_soft

angles_deg = [0, 30, 60, 90, 120, 150, 180]
freqs = np.logspace(np.log10(50), np.log10(20000), 512)

rows = []
for deg in angles_deg:
    th = math.radians(deg)
    fc_A = model_A_structure_radians(th)
    fc_B = model_B_dir_normalized(th)
    sh_C = model_C_shelf_db(th)
    sh_D, fc_D = model_D_combo(th)
    rows.append({
        "deg": deg,
        "fc_A_structure_rad": round(fc_A, 1),
        "fc_B_dir_norm": round(fc_B, 1),
        "shelf_C_db": round(sh_C, 2),
        "shelf_D_db": round(sh_D, 2),
        "fc_D_soft": round(fc_D, 1),
        "gain_A": round(mic_power_gain(th, CO), 4),
        "gain_B": round(mic_power_gain(th / math.pi, CO), 4),
    })

(OUT / "mic_colour_table.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

# Markdown summary
md = ["# Mic off-axis colour models (prototype)", "",
      "Res = 10 kHz (dynamic). C/O = 1. Not a Structure OCR of shelf — ASSUMED comparisons.", "",
      "| Angle | A: Structure law on **radians** fc | B: same law on **θ/π** fc | C: high-shelf dB | D: shelf + soft LP fc |",
      "|------:|-----------------------------------:|---------------------------:|-----------------:|---------------------:|"]
for r in rows:
    md.append(f"| {r['deg']}° | {r['fc_A_structure_rad']} Hz | {r['fc_B_dir_norm']} Hz | {r['shelf_C_db']} dB | {r['shelf_D_db']} dB / {r['fc_D_soft']} Hz |")
md += ["",
"## Takeaways", "",
"1. **Model A** (current engine if θ is radians): by 90° Gain hits 0 → fc ≈ 8 Hz. That is the phone-filter feeling.",
"2. Structure dump Dir was **0.002–0.17**, not 0–π. So either Dir is a small look-error, or we must **normalize** angle before the Power law.",
"3. **High-shelf alone** keeps lows and mids, tilts HF — closer to real off-axis plots (DPA etc.).",
"4. **Combo D**: shelf does the audible HF dulling; soft LP with a floor adds a little air loss without muting the tap.",
"5. Keep Structure 1-pole path as an option (Mic Response), but default colour should be **shelf-led**.", ""]
(OUT / "README.md").write_text("\n".join(md), encoding="utf-8")

if HAS_MPL:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True)
    plot_angles = [0, 60, 90, 135]
    for ax, deg in zip(axes.flat, plot_angles):
        th = math.radians(deg)
        # A
        Ha = one_pole_H(freqs, model_A_structure_radians(th))
        # B
        Hb = one_pole_H(freqs, model_B_dir_normalized(th))
        # C
        Hc = rbj_highshelf_H(freqs, 3500.0, model_C_shelf_db(th))
        # D
        sh, fc = model_D_combo(th)
        Hd = rbj_highshelf_H(freqs, 3500.0, sh) * one_pole_H(freqs, fc)
        for H, lab, col in [
            (Ha, "A LP rad", "#c44"),
            (Hb, "B LP θ/π", "#e83"),
            (Hc, "C shelf", "#2a6"),
            (Hd, "D shelf+softLP", "#26a"),
        ]:
            mag = 20.0 * np.log10(np.maximum(np.abs(H), 1e-12))
            ax.semilogx(freqs, mag, label=lab, color=col, lw=1.8)
        ax.set_title(f"Incidence {deg}°")
        ax.set_ylim(-40, 6)
        ax.set_xlim(50, 20000)
        ax.grid(True, which="both", alpha=0.3)
        ax.axhline(0, color="#888", lw=0.8)
    axes[0,0].legend(loc="lower left", fontsize=8)
    axes[1,0].set_xlabel("Hz")
    axes[1,1].set_xlabel("Hz")
    axes[0,0].set_ylabel("dB")
    axes[1,0].set_ylabel("dB")
    fig.suptitle("Off-axis mic colour — 1-pole vs shelf vs combo (Res=10 kHz)", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "mic_colour_models.png", dpi=140)
    plt.close()
    print("PLOT", OUT / "mic_colour_models.png")
else:
    print("NO_MPL")

# Short noise demos at 90deg for A vs C vs D
rng = np.random.default_rng(0)
n = int(SR * 1.2)
x = rng.standard_normal(n).astype(np.float64) * 0.15
# pink-ish
b = np.array([0.049922035, -0.095993537, 0.050612699, -0.004408786])
a = np.array([1, -2.494956002, 2.017265875, -0.522189400])
# simple filter via lfilter if scipy else skip wav nuance

def apply_one_pole(x, fc):
    if fc <= 0: return x.copy()
    g = 1.0 - math.exp(-2.0 * math.pi * min(fc, 0.49*SR) / SR)
    y = np.empty_like(x); s = 0.0
    for i, xi in enumerate(x):
        s += g * (xi - s); y[i] = s
    return y

def biquad(x, f0, gdb):
    # highshelf process
    A = 10.0 ** (gdb / 40.0)
    w0 = 2.0 * math.pi * f0 / SR
    cosw = math.cos(w0); sinw = math.sin(w0)
    alpha = (sinw / 2.0) * math.sqrt(max((A + 1.0/A)*(1.0/1.0 - 1.0) + 2.0, 0.0))
    two = 2.0 * math.sqrt(A) * alpha
    b0 = A * ((A + 1.0) + (A - 1.0) * cosw + two)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cosw)
    b2 = A * ((A + 1.0) + (A - 1.0) * cosw - two)
    a0 = (A + 1.0) - (A - 1.0) * cosw + two
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cosw)
    a2 = (A + 1.0) - (A - 1.0) * cosw - two
    b0,b1,b2,a1,a2 = b0/a0,b1/a0,b2/a0,a1/a0,a2/a0
    y = np.empty_like(x); x1=x2=y1=y2=0.0
    for i,xi in enumerate(x):
        yi = b0*xi + b1*x1 + b2*x2 - a1*y1 - a2*y2
        x2,x1 = x1,xi; y2,y1 = y1,yi; y[i]=yi
    return y

def write_wav(path, mono):
    import wave, struct
    m = np.clip(mono, -1, 1)
    pcm = (m * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(SR))
        w.writeframes(pcm.tobytes())

th = math.radians(90)
write_wav(OUT / "A_structure_rad_90deg.wav", apply_one_pole(x, model_A_structure_radians(th)))
write_wav(OUT / "B_dir_norm_90deg.wav", apply_one_pole(x, model_B_dir_normalized(th)))
write_wav(OUT / "C_shelf_90deg.wav", biquad(x, 3500.0, model_C_shelf_db(th)))
sh, fc = model_D_combo(th)
write_wav(OUT / "D_combo_90deg.wav", apply_one_pole(biquad(x, 3500.0, sh), fc))
write_wav(OUT / "dry_noise.wav", x)
print("WAVS", OUT)
print(json.dumps(rows, indent=2))
