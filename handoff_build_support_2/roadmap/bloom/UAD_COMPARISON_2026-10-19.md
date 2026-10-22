# UAD plug-ins as a second opinion on the Bloom compressor research

*Written 19 Oct 2026, about 13:00 (UK time, BST). Measured on Idle's PC (WINDOWS-TUCGHE6) in a separate venv, `C:\Users\IdleHanz\uad_measure\.venv`, using pedalboard 0.9.26 with Python 3.14.7. No file under `software\`, the harness or the tests was touched. The research files `COMPRESSOR_RESEARCH.md` and `compressor_presets.json` were not edited; the proposed edits are listed in §9.*

Data, plots and scripts are in `roadmap\bloom\uad\`. The mic-pre half of this work is in `roadmap\mic_character\UAD_PRE_COMPARISON_2026-10-19.md`.

## 0. The short version

- **The plug-ins worked headlessly.** All 20 UADx plug-ins loaded, processed audio and gave the same output on both channels. None was muted or silent and none showed a demo mute. The only problem was a path one: pedalboard can't open the `.vst3` *bundle folder*, but it does open the binary inside it (`...\X.vst3\Contents\x86_64-win\X.vst3`). Licensing was not touched. UA Connect was already running and the plug-ins authorised themselves normally.
- **Our circuit and SPICE timing is confirmed where it mattered most.** Treat UAD as a second model, not as the hardware.
  - **Fairchild positions 1–4**: τ matches within 1–4%.
  - **SSL G Auto release**: the program-dependent shape matches our SPICE almost exactly. The slow share after 0.05/0.3/1/3/8 s of compression is 0.12/0.37/0.69/0.85/0.87 in UAD, against 0.11/0.36/0.69/0.86/0.88 in our SPICE.
  - **1176 release range**: UAD gives 56 ms–1.19 s, against our 59 ms–1.16 s from the circuit.
- **Where UAD disagrees with us:**
  1. **LA-2A memory.** UAD's LA-2A Silver and Gray have almost **no long release memory**. The release τ is about 0.11 s whether the burst lasted 1 s or 20 s. Our model, fitted to one measured cell, gives 0.57 s after 1 s and 1.51 s after 5 s. The older UAD LA-2 has only mild memory (0.35 → 0.53 s).
  2. **Static curves are stiffer than our laws.** The Fairchild's local ratio reaches 4–9:1 at 10–18 dB of gain reduction (GR). Our 6386 law in a feedback loop can't go past about 3:1. The LA-2A sits at 4–5:1 against our device model's 2.7:1. The SSL is the other way round: it is *softer* than our "hard knee, 4 + 0.115·GR" and reaches 4:1 only at about 20 dB GR. The *slope* of ratio against GR still matches ours (+0.12 per dB).
  3. **Fairchild positions 5 and 6 recover faster than our SPICE after short and medium bursts.** After 50 ms at position 5 it takes 1.85 s to get within 1 dB, against 3.35 s in our SPICE. After long bursts the two agree (7.2–7.7 s against 7.4 s).
  4. **Manley Variable Mu.** UAD does **not** cap GR at 10 dB. It reached 13.6 dB in Limit and 19.7 dB at hot settings.
- **Distressor (new, never modelled before):**
  - The release range is much shorter than the manual's 0.05–3.5 s: t63 runs 30 ms → 0.94 s, and the knob stops changing above 9.
  - The Nuke release is a clear two-stage, log-like shape: about 40–130 ms fast plus about 0.5 s slow. Our estimates (0.15 s / 1.0 s) are about 2× too slow.
  - Attack is about 1.5–2× slower than our taper between knobs 3.5 and 6.

## 1. Method

**Loading.** `pedalboard.load_plugin()` on the inner VST3 binary. pedalboard handled the plug-in latency itself: the reported latency was 86–87 samples (31 on the dbx 160 and LA-3A), and the measured cross-correlation lag of a −50 dBFS noise burst through each unit was **0 samples**, so no further shift was needed. Every render had 1 s of silence in front of it, which I cut off afterwards. That lets each parameter settle first. Both channels got the same signal and matched to within 2×10⁻⁵ (Manley VM; the rest were exact). Rendering ran as one process, one plug-in at a time, and was 10–30× faster than real time. CPU load stayed modest.

**Signals (48 kHz, 1 kHz sine unless stated; levels are dBFS *peak*):**
- **Static curve.** A level staircase from −40 to +10 dBFS in 2 dB steps, 1 s per step (2–4 s for slow units). I took the median gain over the last 0.3 s of each step. The 1176 runs went down to −60 dBFS.
- **Attack and release.** A probe tone below threshold, then a burst 20 dB higher, then the probe again. The burst level was set from the staircase so that GR was about 10 dB. Release is measured on the probe after the burst, and attack on the burst itself.
- **Program dependence.** The same test with bursts of 10/50 ms, 0.3 s, 1, 3, 5, 8, 10 and 20 s.
- **Gain reduction** is the output envelope divided by the input envelope, minus the small-signal gain. The envelope is a one-cycle (1 ms) RMS, centred, so **anything faster than about 1 ms can't be resolved**. That limits only the sub-millisecond FET and Fairchild attacks.

**Fits.** I fitted the same model forms the research uses:
- one, two or three exponentials on the GR release (dB domain);
- for the Fairchild, also in "detector volts", after inverting our law GR = 18.1·ln(1 + V/8.06);
- for the opto units, also in the conductance domain, u = 10^(GR/20) − 1, which is the domain where our τ_rel is defined.

The exact parameter values set and read back for every run are in each row's `params` column in the CSVs. The per-run JSONs on the PC (`C:\Users\IdleHanz\uad_measure\out\`) also record every knob's read-back string.

**The settings used, as UAD knob values (no presets):**

| Unit | Settings |
|---|---|
| Fairchild 670 | Input 0 dB, Threshold 5.0, DC Thr 8.6 (default), Time Const 1–6, both channels the same. Burst −9 dBFS, probe −29. |
| SSL G Bus | Threshold 0 dB, Make-up 0, Ratio 4:1 (2:1, 10:1 for statics), Attack 10 ms (30 ms also tried), Release 0.1/0.3/0.6/1.2 s/Auto, SC filter Off, Headroom 16 dB. Burst −11, probe −31. |
| LA-2A Silver / Gray | Peak Reduction 50, Gain 30, Comp (Limit for one static), Emphasis 0. Burst −12 (Silver), −17 (Gray). |
| LA-2 | Peak Reduction 50, Gain 30. Burst −7. |
| LA-3A | Peak Reduction 5.0, Gain 5.0, Comp. Burst −9. |
| 1176LN Rev E / Rev A | Input −40 dB, Output −20 dB, Ratio 4:1 (20:1 static), Attack 4.00, Release 1–7. Burst −7, probe −27. 1176 (FET) ALL: Input −20, burst −30. |
| Distressor | Input 5.0, Output 5.0, Detector Norm, Audio Norm, Headroom 16 dB. Ratio 2:1…Nuke. Attack 0–10, Release 0–10.5. Burst −6 (6:1), −10 (Nuke and 10:1). |
| dbx 160 | Threshold −30 dB, Compress 4.0:1, Gain 0. |
| Manley Variable Mu | Dual Input 5, Threshold 5, Recovery Fast…Slo, Attack 0/5/10, Comp (Limit for statics; one "hot" static at Input 10 / Threshold 10). Burst 0 dBFS, probe −20. |

## 2. Fairchild 670

| Quantity | Ours (SPICE / circuit) | UAD | Difference |
|---|---|---|---|
| Pos 1–4 release τ | 0.10 / 0.30 / 0.88 / 1.76 s | 0.102 / 0.293 / 0.859 / 1.69 s | +2 / −2 / −2 / −4 % |
| Pos 1–4, 10 dB → 1 dB | 0.26 / 0.76 / 2.23 / 4.45 s | 0.23 / 0.68 / 2.01 / 3.95 s | −10 to −11 % |
| Pos 5 τ (volts domain, our law inverted) | 0.22 s + 3.2 s | 0.26–0.32 s + 3.74–3.85 s | fast +20–45 %, slow +17–20 % |
| Pos 5 τ (dB domain) | n/a | 0.30 s + 4.0 s (both constant across bursts) | n/a |
| Pos 5 slow share (volts) | not quoted | 13 / 19 / 33 / 51 / 59 % after 0.05 / 0.3 / 1 / 3 / 10 s | n/a |
| Pos 5 → 1 dB after 10 ms / 0.3 / 1 / 3 / 10 s | 3.35 / 5.20 / 6.69 / 7.40 / 7.46 s | 1.36* / 3.46 / 5.61 / 7.25 / 7.74 s (50 ms: 1.85 s) | short bursts −45 to −60 %, long ≈ equal |
| Pos 6 τ (volts) | 0.077 / 1.12 / 8.2 s | 0.093–0.105 / 1.7–2.4 / 10.1 s | +20–35 % / +50–110 % / +23 % |
| Pos 6 → 1 dB after 10 ms / 0.3 / 1 / 3 / 10 s | 0.29 / 6.64 / 13.2 / 17.4 / 18.9 s | 0.30 / 1.53 / 7.1 / 13.9 / 18.4 s | ends match; the middle is much faster in UAD |
| Pos 6 → 0.5 dB after ≥ 10 s | 24.6 s (manual "25 s") | 25.6–26.4 s | +4–7 % |
| Static law | GR = 18.1·ln(1 + V/8.06), ratio grows with level | local ratio 1.6 (2 dB GR) → 2.4 → 3.3 → 4.4 (10 dB) → 5.4 → 6.4 → 9+ (18 dB) | see below |

\*The 10 ms burst reached only 7.6 dB of GR, because the attack didn't finish.

**What it means.**
- **Positions 1–4 confirm our reading of the timing network** and the "panel time ≈ 2.3τ" rule.
- **Positions 5 and 6 confirm** the number of stages, the very-long-burst end points and the manual's 25 s.
- **But UAD shares the charge between the stages differently.** Short and medium bursts leave much less in the slow capacitor, so the "swell" after a single hit lets go about twice as fast as in our SPICE.
- **Static shape: this is a real contradiction.**
  - Our law, put inside a feedback loop with a rectified-output detector, gives a ratio that can never go past about 3.1:1. At high GR, d(GR)/d(out dB) → 18.1·ln10/20 = 2.08, so the ratio → 3.08.
  - UAD's local ratio passes 4:1 at 10 dB GR and 6:1 at 15 dB.
  - The best fit of our law plus a threshold to UAD's curve misses by 2.2 dB RMS, and by 4.6 dB at worst.
  - So either the plug-in's sidechain gain isn't linear, or its tube law is steeper at high bias than the DAFx-12 black-box fit. The manual's "2:1 rising to 20:1/30:1" sides with UAD.
  - For Swell, this only matters if we model the curve rather than the timing. Swell is capped at 10 dB anyway.

Plot: `uad\fairchild_release_pos5_pos6.png`.

## 3. SSL G bus compressor

| Quantity | Ours | UAD | Difference |
|---|---|---|---|
| Auto fast τ | 42.8 ms (91 k ∥ 0.47 µF) | 37–41 ms | −4 to −14 % |
| Auto slow τ | 5.1 s (750 k ∥ 6.8 µF) | 3.6–4.1 s | −20 to −29 % |
| Slow share after 0.05 / 0.3 / 1 / 3 / 8 s | SPICE 0.11 / 0.36 / 0.69 / 0.86 / 0.88; formula d/(d+0.62), cap 0.89: 0.075 / 0.33 / 0.62 / 0.83 / 0.89 | 0.12 / 0.37 / 0.69 / 0.85 / 0.87 | ≤ 0.02 against SPICE; the formula is low at short d |
| After 50 ms: half / to 1 dB | 35 ms / 0.12 s | 35 ms / 0.26 s | half time equal |
| After ≥ 3 s: half / to 1 dB | 2.8 s / 9.6 s | 2.2 s / 9.2 s | −21 % / −4 % |
| Fixed 0.1 / 0.3 / 0.6 / 1.2 s τ | 85 / 127 / 263 / 564 ms | 80 / 117 / 225 / 413 ms | −6 / −8 / −14 / −27 % |
| Fixed, 10 dB → 1 dB | 0.17 / 0.26 / 0.55 / 1.18 s | 0.18 / 0.27 / 0.54 / 1.01 s | 1.2 s position −14 % |
| Attack "10 ms", t63 at about 4 / 8 / 13 dB GR | 26.7 / 14.5 / 9.4 ms | 15.0 / 9.2 / 6.0 ms (3.6 / 7.8 / 13.2 dB) | UAD 35–45 % faster; same trend |
| Attack "30 ms", t63 | n/a | 31 / 21 / 14 ms (2.5 / 5.9 / 10.7 dB) | n/a |
| Knee / ratio at 4:1 | hard onset, ratio ≈ 4 + 0.115·GR | local ratio 1.9 (2 dB) → 2.9 (8) → 3.2 (11) → 3.8 (17) → 4.4 (23); ≈ 1.65 + 0.12·GR | **soft, not hard**; same slope, offset −2.3 |
| 10:1 / 2:1 | n/a | 4.1 → 7.3 / 1.4 → 2.2 | n/a |
| Lower ratio → lower threshold | yes (manual) | onset −36 / −28 / −24 dBFS at 2 / 4 / 10:1 | agrees |

**What it means.**
- **The Auto release *structure* is confirmed beautifully.** Two sections in series, with the slow share growing as d/(d + about 0.6 s). See `uad\ssl_auto_release.png`, where UAD and SPICE sit on top of each other.
- **UAD's slow section is shorter** (about 4 s, against 5.1 s). That still falls within resistor and capacitor tolerance plus the loop effect.
- **The closed-form share formula** should be replaced by the SPICE share values, or by simulating the two sections directly (§4B already recommends that). The formula is the only piece that was "approximately right".
- **The knee is where UAD disagrees.** UAD's 4:1 behaves like a broad soft knee that needs about 20 dB of GR to reach 4:1. At Glue's 1–4 dB target, UAD's effective ratio is only about 2–2.5:1, against our 4.1–4.5:1. That makes "Glue" noticeably gentler in UAD's opinion.

## 4. Teletronix LA-2A (Silver and Gray), LA-2, LA-3A

| Quantity | Ours | UAD Silver | UAD Gray | UAD LA-2 |
|---|---|---|---|---|
| Release τ (conductance) after 0.3 / 1 / 5 s | model 0.14 / 0.57 / 1.51 s (Stroe cell 0.09 / 0.58 / 1.56) | 0.090 / 0.112 / 0.113 s | 0.096 / 0.113 / 0.113 s | 0.35 / 0.43 / 0.53 s |
| After 20 s burst | (memory saturated) about 1.6 s | 0.113 s | 0.113 s | 0.53 s |
| Release, after 5 s: to 1 dB / 0.5 dB | 3.9 / 4.8 s | 1.13 / 1.95 s | 0.84 / 1.33 s | 4.7 / 7.0 s |
| GR half-time | "60 ms to 50 %" (UA) | 0.03–0.10 s | 0.05–0.09 s | 0.13–0.53 s |
| Attack | model: 88 % τ 0.104 s + 12 % τ 1.25 s (open-loop cell); SPICE closed loop t63 about 20 ms; UA spec 10 ms | t63 about 2 ms, t90 22–38 ms; fit 80–87 % τ ≈ 2 ms + 13–20 % τ 0.13–0.16 s | t63 2–3 ms, t90 14–34 ms; 80–84 % + 16–20 % τ 0.10–0.14 s | t63 2–5 ms, t90 0.10–0.13 s; 58–68 % + 32–42 % τ 0.12–0.16 s |
| Static ratio (Comp) | device model 1.1 → 2.7:1 (asymptote 2.8); UA "about 4:1" | 3.4 (3 dB GR) → 4.8 (8) → 5.3 (13) → 3.7 (27) | 2.4 → 5.3 → 3.1 | over-compresses above about 10 dB GR (ratio < 0) |
| Static ratio (Limit) | ∞ | 3.8 → 6.9 → 13.6 → ∞ at about 20 dB GR | n/a | n/a |
| Equivalent γ·n (u ∝ out^(γn)) | 1.8 (γ 0.6, n 3) | ≈ 5.2 | ≈ 4.8 | n/a |

LA-3A, no prior claims: t63 0.05–0.12 s, mild memory, but a long last half-dB after 5 s or more (4.6–5 s to 0.5 dB). Ratio 3.5–4.9:1.

**What it means.**
- **This is the biggest disagreement.** UAD's LA-2A has the classic fast-then-slow shape, but **no multi-second history effect**. After any burst of 1 s or more it releases the same way: about 0.1 s τ, within 1 dB in about 1 s, and within 0.5 dB in about 2 s.
- **Our "Natural" preset is built around the memory.** It blooms more after long loud passages. That memory came from **one** cell measured open-loop (Stroe), checked against the "0.5–5 s depending on previous reduction" spec text.
- Six real units measured by Moore 2025 settled in 449–1670 ms, which sits between the two. **I would not throw away the memory on UAD's word.** It is a modelling choice that UA evidently did not make for the Silver and Gray. The LA-2 has a gentle version of it.
- **Two ways forward:**
  - Keep the memory (truer to the cell physics and the spec text).
  - Halve its range, e.g. τ = 0.06 + 0.6·M₂ s, so it sits between UAD and the cell.
- **This one should be decided by listening, not by me.**
- **UAD's attack is much faster** than both our closed-loop SPICE (about 20 ms) and UA's own spec (10 ms). The *split* is similar to ours, about 85 % fast and 15 % slow, but the slow stage is about 8× shorter.
- **On the static curve UAD agrees with UA's "about 4:1"** and says our device model (γn = 1.8) is too soft. γn ≈ 4.5–5 reproduces UAD.

Plot: `uad\la2a_release_memory.png`.

## 5. 1176 (LN Rev E, Rev A, and the 1176 FET with All-buttons)

| Quantity | Ours | UAD LN Rev E | UAD Rev A |
|---|---|---|---|
| Release 63 % range (knob 7 → 1) | 59 ms – 1.16 s (circuit) | 56 ms – 1.19 s | 94 ms – 1.27 s |
| Per knob 1 … 7 (t63, s) | n/a | 1.19 / 1.10 / 0.83 / 0.55 / 0.30 / 0.077 / 0.056 | 1.27 / 1.19 / 0.95 / 0.69 / 0.42 / 0.13 / 0.094 |
| Release shape | single τ | fast knobs: 90 % τ 50–67 ms + 10 % τ 0.84 s; knob 4: 59 % 0.36 s + 41 % 1.06 s | knobs 6–7: 60–65 % 53–69 ms + 35–40 % 0.32 s (knob 5: 92 % τ 0.46 s) |
| Program dependence (knob 4) | none | t63 0.45 / 0.55 / 0.77 s after 0.05 / 0.5 / 3 s | 0.67 / 0.69 / 0.70 s (none) |
| Static curve (4:1) | **unknown** (our SPICE wasn't usable); knee estimated at 5 dB | local ratio 2.3 (1 dB GR) → 3.7 (4) → 4.7 (7) → 5.6 (10–20 dB) | 2.7 → 3.6 → 4.4 → 5.1 → 5.9 |
| Attack (knob 4) | 20–800 µs start, settles over up to 5.5 ms | t63 ≤ 3 ms (1 ms resolution), t90 39 ms | t63 ≤ 2 ms, t90 0.12 s |
| All-buttons onset lag | 1–3 ms (estimate) | 1176 FET ALL: t10 0.8–2.5 ms (normal ratios < 0.5 ms) | n/a |
| All-buttons release | "drops off severe and sudden" | t63 3–40 ms (10–30× faster than 4:1); attack tail t90 0.2–0.28 s; static ratio 13–45:1 | n/a |

**What it means.**
- **Our circuit-derived release range is confirmed** to within 5 % on the LN.
- **UAD gives the static curve we couldn't get.** It is a soft knee about 8–10 dB wide, after which "4:1" actually runs at about 5.5–6:1. Our knee estimate of 5 dB is too narrow. The 20:1 setting is close to a hard knee.
- **The All-buttons lag** in UAD sits right inside our 1–3 ms estimate.

Plot: `uad\u1176_release_knob.png`.

## 6. Distressor (new: not modelled before)

| Quantity | Our estimate / manual | UAD |
|---|---|---|
| Attack knob 0 / 1 / 2 / 3 / 3.5 / 4 / 5 / 6 / 7 / 8 / 9 / 10, t63 | 0.05 ms @0; 0.8 @3.5; 1.06 @4; 1.85 @5; 3.2 @6; 30 @10 ms (manual-anchored taper) | < 0.25 / 0.5 / 0.8 / 1.3 / 1.8 / 2.2 / 3.0 / 4.0 / 6.0 / 10.3 / 16.8 / 23.8 ms (t90 0.8 → 70 ms) |
| Release knob 0 / 2 / 3 / 5 / 6 / 7 / 8 / 9–10.5, t63 | estimate 0.05·70^(k/10) s: 0.05 / 0.12 / 0.18 / 0.42 / 0.64 / 0.98 / 1.5 / 3.5 s; manual 0.05–3.5 s | 0.030 / 0.073 / 0.095 / 0.165 / 0.31 / 0.57 / 0.79 / 0.94 s (to 1 dB: 0.33 … 1.88 s) |
| Release shape | n/a | not a single exponential (0.25–0.38 dB fit error); fast fall, then a slow last dB |
| Nuke release ("logarithmic") | two-stage estimate: 0.15 s fast + 1.0 s slow | release 2 / 3 / 5: fast 36 / 48 / 91 ms + slow 0.54–0.57 s; slow share 6–11 % after 50 ms, 31–32 % after 1 s |
| Nuke ratio | "within 1 dB", ∞ | local 20–36:1 up to about 20 dB GR |
| 10:1 Opto, to 1 dB after 0.05 / 0.5 / 3 / 10 s | "up to 20 s", program-dependent | 0.21 / 0.73 / 3.3 / 8.4 s (0.5 dB: 0.37 / 1.3 / 8.8 / 14 s) |
| Ratio at about 10 dB GR, 2 / 3 / 4 / 6 / 10 / 20 :1 | long parabolic knees on 2:1 and 3:1 | 3.9 / 5.1 / 5.0 / 6.7 / about 12 / about 24 (2:1 and 3:1 keep rising over 15–20 dB) |

At Input 5 the ratio falls back above about 18–20 dB of GR. That's probably the modelled input stage running out of headroom.

**What it means for Bloom's Nuke preset.**
- The documented room setting (attack 4–5, release 2–3) corresponds in UAD to:
  - attack t63 of about 2–3 ms;
  - release of about 50–70 ms fast plus about 0.5 s slow, with the slow share growing with how long it has been compressing.
- That is about **2× faster on both release stages** than our estimate.
- The attack taper should move up by about 1.5–2× between knobs 3.5 and 6.
- The release taper estimate is **wrong at the top end**. UAD's knob tops out at about 1 s τ (about 1.9 s to 1 dB), not 3.5 s.

Plot: `uad\distressor_tapers.png`.

## 7. dbx 160 and Manley Variable Mu (cheap extras)

| Quantity | Ours (published) | UAD | Difference |
|---|---|---|---|
| dbx 160 release | constant 120 dB/s (160A: 125) | constant 87–93 dB/s | −25 % (constant-rate shape confirmed) |
| dbx 160 attack, 10 / 20 / 30 dB over threshold | 15 / 5 / 3 ms | t63 20 / 7.3 / 3.0 ms | same trend |
| dbx 160 ratio, knee | 4:1 hard | 4.1–4.8:1 local, hard onset | agrees |
| Manley recovery Fast … Slo | 0.2 / 0.4 / 0.6 / 4 / 8 s | τ 0.18 / 0.38 / 0.79 / 1.72 / 3.28 s; to 1 dB from 5 dB 0.28 / 0.60 / 1.27 / 2.74 / 4.94 s | Fast and Med Fast match; Med Slo and Slo about 2.3× shorter |
| Manley attack | 25 ms (fast) – 70 ms (slow) | knob 0 and 5: t63 about 19 ms; knob 10: 1.8 ms | doesn't follow the published span |
| Manley max GR | "never more than −10 dB" | Comp 8.1 dB at +10 dBFS (still rising); Limit 13.6 dB; hot (input 10, threshold 10) 19.7 dB | **cap not reproduced** |
| Manley ratios | Comp 1.5:1; Limit 4:1 → 20:1 past 12 dB | Comp 1.2–1.6; Limit 1.7–2.4 (hot: 4–5.6) | Comp agrees; Limit much softer |

**What it means for Swell.** Swell takes its 10 dB cap and its 25 ms attack from the Manley. The cap is still a sensible safety choice for Bloom. It just shouldn't be called "hardware-matching" on the strength of UA's text, because UA's own plug-in doesn't enforce it.

## 8. How far to trust this

- **UAD is a model.** It agrees with our circuit work wherever both rest on component values (Fairchild 1–4, SSL release network, 1176 release pot). Where they disagree, either side could be wrong:
  - LA-2A memory is a modelling choice.
  - Static curves depend on the sidechain gain and gain-element laws, which neither we nor UA publish in full.
- **These are steady 1 kHz tones at about 10 dB GR, one setting each.** Real music and other GR depths will shift the numbers, especially the opto units.
- **Attack below about 1 ms isn't resolved** (one-cycle envelope).
- **dBFS-to-dBu calibration inside UAD isn't known,** so thresholds are only relative.
- **No version string** is embedded in the UADx binaries. These are the copies installed on 19 Oct 2026.

## 9. Proposed edits to the research files (not made)

**To `COMPRESSOR_RESEARCH.md`:**
1. **§4A.4 (Fairchild):**
   - Add "UAD cross-check: pos 1–4 τ within 4 %; pos 5/6 end points match; short- and medium-burst recovery is about 2× faster in UAD."
   - Add a note under the 6386 law that, in a feedback loop, it caps the ratio at about 3:1. UAD (and the manual's 20–30:1) are stiffer, so the law is good for timing but not for the static curve.
2. **§4A.3 (SSL):**
   - Mark the Auto structure as "UAD-confirmed".
   - Note the slow τ of about 4 s in UAD against 5.1 s from the drawings.
   - Replace "w_slow ≈ d/(d + 0.62 s)" with the SPICE share table, or with direct simulation of the two sections.
   - Change "hard onset" to "hard onset in our SPICE; UAD shows a soft knee with ratio ≈ 1.65 + 0.12·GR at the 4:1 setting".
   - Note that the attack is 35–45 % faster in UAD.
3. **§4A.1 (LA-2A):**
   - Add "UAD Silver and Gray show no multi-second memory (τ ≈ 0.11 s after any burst ≥ 1 s); the UAD LA-2 shows mild memory (0.35 → 0.53 s)."
   - Raise the open question of whether Natural keeps the full memory range.
   - Note UAD's attack (t63 about 2 ms) and its static ratio of about 4–5:1 (γn ≈ 5).
4. **§4A.2 (1176):**
   - Replace "Not used … knee width stays an estimate (5 dB)" with the UAD static curve: soft knee about 8–10 dB, "4:1" settling at about 5.5–6:1.
   - Mark the release range as UAD-confirmed.
   - Add the mild program dependence on the LN (0.45 → 0.77 s at knob 4).
5. **§4A.5 / §4.8 (Distressor):**
   - Add the measured attack and release tapers (§6 above).
   - Retire the 0.05·70^(k/10) release estimate.
   - Record the Nuke release as fast ≈ 40–90 ms plus slow ≈ 0.55 s, with a duration-dependent share.
6. **§4.9 (Manley):** add "UAD plug-in exceeds 10 dB GR; recovery Med Slo/Slo ≈ 1.7/3.3 s τ".
7. **§4.5 (dbx):** add "UAD: about 90 dB/s release".
8. **§4B trust table:** add a "UAD cross-check" column: Fairchild timing ✓, SSL release ✓, 1176 release ✓, LA-2A memory ✗, static curves ✗ (UAD stiffer except SSL).

**To `compressor_presets.json`:**
1. **Nuke:** release fast 0.15 → about 0.06 s, slow 1.0 → about 0.55 s; attack about 2–3 ms at knob 4–5. Status "UAD-measured".
2. **Glue:** either keep the hard knee as circuit-derived, or add an option `knee_db ≈ 10–12` reflecting UAD. Flag it for a listening choice.
3. **Room Crush:** knee 5 → about 9 dB; effective ratio at 4:1 ≈ 5.5. The release range stays.
4. **Natural:** no change until Idle has listened. Possibly add a `memory_scale` (1.0 = cell fit, about 0.1 = UAD-like).
5. **Swell:** keep the timing. Note that UAD recovers faster after short peaks, and that the 10 dB cap is a Bloom safety choice rather than a hardware match.
