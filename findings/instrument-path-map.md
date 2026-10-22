# Instrument signal path (2011 vs Desktop) — 2026-09-20

Fundamentals of `2011-room-reverb.ens`. Upgrades stay tagged ASSUMED. Mixer: shot **477**.

Audio vs event: yellow = event/control; white = audio. Do not treat Controls / Mic Stand display as Prepare audio.

---

## 0. Instrument spine **VERIFIED** (459, batch-3)

Left → right:

`Switch` (Surf/Floor/Seal/Wall) → `Controller` → `Absorb Diffus Code` + `Surface Absor+Diffu`  
`Controls` (Diffusion Matrix, Room Dim, Source, Mic Stand — mostly **GUI**)  
`Prepare` → `Reflection Code` → `Distances and Delays` → `Sound Processing` → `Mixer` → stereo **L / R**

Host dry does **not** enter Mixer. 2011 Out is the wet bus. Desktop `dry_gain` is an **ASSUMED** upgrade.

---

## 1. Prepare **VERIFIED**

Room `W,H,L`. `MCZ = L − MZ`. Parity `MCX = W×0.5` (Desktop free `mcx` is an upgrade).  
`MLX/MRX = MCX ∓ Space/2`. `MLALR/MRALR = Diverg×0.5 ∓ 0.25` (Add, 403).  
`SX = W×SoX`, `SY = MY` historically, `SZ = MCZ+(L−MCZ)×SoZ`. Direct Field `DD` = 2D XZ.

---

## 2. Reflection Code **VERIFIED** (leaves)

Per-voice image coords from named macros (`2W−X`, `−2W+X` = `X−(2·W)`, `4L−Z`, …). Corner origin, full `R`. To V 17–52 is the image index bus (not FDN V1–32).

---

## 3. Distances and Delays **VERIFIED**

`d = √(Δx²+Δy²+Δz²)`. `TL/TC/TR = (d/340)×1000` ms. Distances `1/x` is `1/340`, not a gain. Geometric amp is Air Abs `1/r²`.  
`DL/DC/DR` → Microphone **Dir**. Angle chain is ΔX/ΔZ ArcTan (long form of XZ `cos θ`).

**459 cyan is Distances selected**, not a delay into Mixer. Distances does **not** feed Mixer (477 has only audio L/C/R). Batch-9 “TL → Mixer early field” is **REJECTED**.

---

## 4. Sound Processing — this is the reverb **VERIFIED** / **LIKELY**

Three parallel columns **L / C / R**.

```
In ──► Air Absorption ──► + ──► Diffuser Delay ──► Microphone ──► L/C/R
                              ▲         │  Dly = DtL/DtC/DtR (image ms)
                              │         │  Dffs from absorb macro
                              │         └──► Feedback Delay Network
                              │                    Fr.V (voice picker)
                              │                    Hadamard ±1
                              │                    × (1/32) × Gain
                              └────────────── Out ──────────────┘
```

| Block | Role | Tag |
|-------|------|-----|
| **Diffuser Delay** | Built-in allpass delay. **The** delay. `Dly` ms = image times. Max **1000 ms**, High Quality Interpolation (476). `Dffs = Dis × Dff × (1/Diffusion)` (462–465). | delay **VERIFIED**; Dffs formula **VERIFIED** |
| **Feedback Delay / Hadamard** | Mix / unique inversions per voice. **Fr.V** picks one poly voice to mono. **Not** a delay. | VERIFIED |
| **Adder** on Delay In | Air Abs Out + Feedback Delay Out → Diffuser Delay In | **VERIFIED** (473, both cyan) |
| **Microphone** | 1-pole after delay. `P = FtoP(Res)×(1-(2·\|Dir\|)^C/O)`. Res = Mic Response **10 kHz**. | **VERIFIED** (410, 214, 399); C/O=1 LIKELY |
| Air Abs | Amp `1/Dis²` × 1-pole LP, `fc=Wet/Dis`. One shared `Dis` into L/C/R. | amp **VERIFIED** (256); 1-pole graph **VERIFIED**; Wet **100–700 default 400** VERIFIED (486); `fc=Wet/Dis` LIKELY |

Poly 32: same input copied to every voice; each voice has its own `Dly`. First read at `d_i` **is** that image. Recirculation is the tail. There is no second delay table.

---

## 5. Mixer **VERIFIED** (477)

Path: `Instrument > Mixer`. **No Delay module.**

```
L ─────────────┐
               ├ Add ─► … ─► L out
C ─× 0.5 ──┬───┤
           └───┤
R ─────────────┴ Add ─► … ─► R out
```

`L_out` path = **L + 0.5·C**. `R_out` path = **R + 0.5·C**. Const **0.5** on C **VERIFIED**.

After the Adds: **Audio Voice Combiner** (poly → mono, 479) then **× Receive RMS Volume** (478). Automatic loudness — not a user trim. See `mixer-agc.md`.

2011 wet is **one** bus: Sound Processing L/C/R → this fold. Not “early FIR + FDN mix.”

---

## 6. What the Desktop still did wrong (until this pass)

| 2011 | Old Desktop |
|------|-------------|
| One delay: Diffuser Delay, image ms, 1000 ms cap | Early FIR **plus** a second FDN |
| Hadamard on delayed voices, feedback into the same delay | Inject images **at their delay times** through a Hadamard **column** (PROPOSAL) |
| Three loops L/C/R, then Mixer `+ 0.5·C` | One stereo FDN, even/odd split, mean L/R delay |
| Mixer has no delay | `early_wet` + `fdn_wet` as two IRs |

---

## 7. Fundamentals vs upgrades

**Fundamentals (must match):** image delays are the FDN lines; Hadamard is feedback mix only; `g` maps to `(Gain/32)` on unscaled H; 32 voices; no `1/√N`; Mixer is LCR fold, not a delay.

**Upgrades (ASSUMED, keep tagged):** free `mcx`, modern toe/ORTF, Surfaces absorb/EQ, seeded Δd jitter, Colour, 3D, `dry_gain`, parallel early FIR overlay if `early_wet > 0` (2011 Mixer does not have that overlay).

**Now wired (later passes):** Mic Power cutoff 1-pole on delay out; Air Abs humidity 1-pole + independent `air_lp` / `air_shelf`; Mixer leftover = Voice Combiner (479). Play live AudioWorklet. Do not treat this section as “still to do.”

---

## 8. Engine patch (this pass)

- `fdn_delays_from_taps`: L / C / R; cap **1000 ms**; **no uniquify**.
- Inject at **t = 0** with that line’s tap level.
- Three FDN runs; Mixer fold `L+0.5·C`, `R+0.5·C`.
- Defaults: `early_wet=0`, `fdn_wet=1`, `ir_length_ms=1500`.
- Early FIR overlay only if `early_wet > 0` (ASSUMED).
- **Play live:** `/api/live_params` + `fdn_worklet.js` (3×32, Mixer fold). Drag updates delays. Render still writes a WAV.
- UI Feedback = Structure Gain; `g = Gain/N`. Humidity Wet 100–700 (486).
