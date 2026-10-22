# Structure screenshots batch 10 — shots 466–475 (2026-09-20 ~08:00)

PNGs in Pictures. Not copied into the repo. Idle Hanz: Diffuser Delay will not open because it is a built-in.

---

## 466–467 — Microphone Gain leaf (Power X vs Y)

Path: `Instrument > Sound Processing > Microphone > Macro`

**466** Power selected. Info **VERIFIED**: *“Power Function. The output delivers the result of X to the power of Y.”*

**467** module after **Dir** selected. Info **VERIFIED**: *“The output is the absolute value of the input signal…”* — **|x| / rectifier**, not Sine/Cosine (old LIKELY was wrong).

Graph **VERIFIED**:

1. **Dir** → **|x|**
2. **× Const 2**
3. **Power** `X^Y`
4. **Const 1 −** that → **Gain**

Pin order **LIKELY / treat as VERIFIED from layout (466):** Mul out (2·|Dir|) → Power **X** (base); **C/O** InPort → Power **Y** (exponent).

`Gain = 1 − (2·|Dir|)^C/O`

Do **not** wire into the renderer. This still drives the 1-pole **cutoff** with Log(Res) (410), not early-tap polar. Sound Processing **HF** feeds Microphone **C/O**; panel **C/O** feeds Microphone **Res** (410 / 460) — names do not match.

467 |Dir| debug ~0.002…0.17 (32 voices).

---

## 468–471 — Fr.V is a voice picker, not a delay **VERIFIED**

Path: `Instrument > Sound Processing > Feedback Delay Network`

**Fr.V** Info **VERIFIED** (468–471): *“One voice is selected from the polyphonic input signal by the value of the (V) input. Only the signal of the selected voice is transmitted to the monophonic output. The signals of the other voices are discarded.”*

Hadamard sits in a poly→mono→poly sandwich. Delay is **not** here.

---

## 472–476 — Diffuser Delay is a built-in **VERIFIED**

Path: `Instrument > Sound Processing`. Top column selected.

**472** Diffuser Delay selected. Info **VERIFIED**:

*“Diffuser delay, containing a feedback delay. This is an allpass filter as used for constructing reverb effects. When Dly=0 this is a 1-pole allpass as used for building phaser effects.”*

NI Primary **Diffuser Delay** (R5/R6 Delay / Diffuse): cannot open. Pins:

| Pin | Meaning | Tag |
|-----|---------|-----|
| **Dly** | delay time, milliseconds (image Distances; 460 = TL) | VERIFIED |
| **Dffs** | diffusion / internal allpass feedback, nominally −1…1. **0 = pure delay** | module spec; live Dffs scale from absorb macro still LIKELY |
| **In** | audio in | VERIFIED |
| **Out** | audio out → Microphone and Feedback Delay In | VERIFIED |

Internal feedback (Dffs) is **inside** the built-in, plus the Hadamard loop on the outside.

**473** the `+` on Diffuser Delay **In**: Info *“Adder for multiple signals.”* **Two** cyan summands with the adder selected: Air Abs Out (upper in) and **Feedback Delay Out** (lower in). Adder out → Diffuser Delay In. Loop **VERIFIED**. C/R copies **LIKELY** the same (same `+` under each column; L opened).

**474** Feedback Delay selected; debug on its Out (near-zero at this instant).

**475** debug on the adder / In path (near-zero).

Loop **VERIFIED** (473): Air Abs + Feedback Delay Out → **+** → Diffuser Delay In. 472: Diffuser Delay Out → Feedback Delay In and Microphone In.

**476** Function / Properties on the same L Diffuser Delay **VERIFIED**:

| Field | Value |
|-------|-------|
| Max Delay (ms) | **1000** (raised from NI default 200) |
| Quality | **High Quality Interpolation** |
| Mono / Mute | off |

Live image Dly tops out ~736 ms (413 / 433 / 460), so 1000 ms covers the list. 1000 ms × 340 m/s = 340 m max path. C and R copies **LIKELY** the same (same built-in, not opened).

---

## Engine

Engine now uses image-ms Diffuser Delay lengths, t=0 inject, L/C/R loops. Dffs allpass still not wired.

## Do not reshoot

Hadamard Voice 1–32, Fr.V, Diffuser Delay interior, and **Max Delay 1000 ms** (476) are done.
