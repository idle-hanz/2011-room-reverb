# Compressor dynamics research for Bloom

**Project:** 2011 Room Reverb, D-BLOOM (Mix window: Amount, Threshold, Attack, Release, Predelay, Sustain)
**Compiled:** 18 Oct 2026 (Europe/London)
**Scope:** This covers only the *timing and level behaviour* of classic compressors: how fast they react, how they let go, and how hard they squash. We need that to make the reverb tail duck and bloom like a familiar unit. It does **not** cover their tone (transformer, tube or FET colour).

**How to read the numbers.** Every figure carries a source tag like **[S6]**. The full list is at the end. Labels:
- **Published** means printed in a manufacturer manual or spec sheet.
- **Derived** means I calculated it from published numbers, and the working is shown.
- **Estimate** means no published figure exists. It's my engineering guess, chosen so the preset feels right, and it must be tuned by ear.

Where two official sources disagree, both are shown.

---

## 1. Plain-language primer (jargon defined once)

- **Compressor:** an automatic volume rider. When the signal gets louder than a set level, it turns the signal down.
- **Threshold:** the level where the turning-down starts.
- **Ratio:** how hard it turns down above the threshold. At 4:1, a 4 dB rise in input gives only a 1 dB rise in output. At ∞:1 (a **limiter**, or "brick wall"), the output doesn't rise at all.
- **Gain reduction (GR):** how many dB it is currently turning down.
- **Knee:** the shape of the corner at the threshold. With a **hard knee**, the full ratio applies the instant the threshold is crossed. With a **soft knee**, the ratio fades in over a range of levels, the **knee width** in dB.
- **Attack:** how quickly gain reduction arrives once the signal goes over the threshold.
- **Release (recovery):** how quickly gain reduction goes away once the signal drops.
- **Program-dependent:** attack and/or release change with the music itself. Short peaks get a fast release, and long loud passages get a slow one. **Auto release** and **two-stage release** are the common forms.
- **Detector (side-chain):** the part that measures the level and decides the GR. A **peak** detector follows the waveform's highest points. An **RMS** detector follows average energy, which is closer to loudness. An **opto** (optical) detector has a light shining on a light-dependent resistor, and the resistor's own sluggish chemistry sets the timing.
- **Feedforward:** the detector listens to the signal *before* the gain change. **Feedback:** it listens to the signal *after* the gain change, so it is correcting its own result. Feedback units feel softer and can't make a perfect ∞:1 limiter [S28, Eq. 18–19].
- **Side-chain filter:** an EQ placed only in the detector. The common one is a high-pass filter (**HPF**), so bass doesn't make the compressor pump.
- **Stereo link:** both channels get the same GR, so the image doesn't wander.
- **Time constant (τ, "tau"):** for a simple smoothing circuit, the time to cover 63% of a change. Manufacturers often quote other definitions instead, such as "time to 50%", "time to complete release" or "dB per second". Section 2.4 converts them.
- **Makeup gain:** the gain added back after compression. **This is the key to the room-mic trick:** when you play, the room is turned down. Between notes, the GR lets go and the makeup gain lifts the quiet tail. Bloom's **Amount** is essentially this makeup gain.

---

## 2. The generic digital compressor (the engine every preset plugs into)

The standard reference is Giannoulis, Massberg and Reiss, *Digital Dynamic Range Compressor Design: A Tutorial and Analysis*, JAES 60(6), 2012 **[S28]**. Their recommended design is feedforward, with smoothing done in decibels after the gain computer, using a "smooth decoupled" peak detector (their §5 Conclusion).

### 2.1 Gain computer (the static curve) [S28, Eq. 3–4]

Work in dB. With the input level x_G = 20·log10|x|, threshold T, ratio R and knee width W:

```
y_G = x_G                                         if 2(x_G - T) < -W
y_G = x_G + (1/R - 1)(x_G - T + W/2)^2 / (2W)     if 2|x_G - T| <= W
y_G = T + (x_G - T)/R                             if 2(x_G - T) > W
```

The target gain change is x_L = x_G − y_G, which is ≥ 0, in dB of reduction.

**Extension for curves whose ratio grows with level.** The Manley Limit mode goes from 4:1 to 20:1 [S25]. The Distressor 4:1 and 6:1 curves are "steeper knees … gradually move towards hard limiting" [S24]. Fairchild and LA-2A curves end in limiting [S6, S10]. All of these can be modelled as a soft knee followed by a second, higher-ratio segment. A 2-segment piecewise curve with a soft corner at each joint is enough.

### 2.2 Level detection and smoothing [S28, Eq. 5–7, 14–17, 23]

One-pole coefficient: **α = exp(−1/(τ·fs))** [S28, Eq. 7].

Recommended form: smooth the gain-reduction signal itself, in dB [S28, Eq. 23], with a **smooth decoupled** detector [S28, Eq. 17]:

```
y1[n] = max( x_L[n],  αR·y1[n-1] + (1-αR)·x_L[n] )   // instant-attack peak hold, releases toward the input
y_L[n] = αA·y_L[n-1] + (1-αA)·y1[n]                 // attack smoothing
GR_dB[n] = -y_L[n]
```

Alternative is the **smooth branching** detector [S28, Eq. 16]. It gives exact, easy-to-reason-about time constants, but the slope has a kink where it switches between attack and release:

```
y_L[n] = αA·y_L[n-1] + (1-αA)·x_L[n]   if x_L[n] > y_L[n-1]
y_L[n] = αR·y_L[n-1] + (1-αR)·x_L[n]   otherwise
```

Notes from [S28] that matter for presets:
- In the decoupled detector, the real release time is about τR + τA (p. 402). When copying a unit's published release, subtract the attack, or use the branching form.
- A detector working in the linear domain, before the dB conversion, releases at a constant number of **dB per second** (p. 404). That is exactly what the dbx 160 does by design: 120 dB/s [S17]. So the dbx preset should use a constant-rate release, not an exponential one.
- **RMS detection** is a one-pole low-pass on x², then a square root [S28, §2.3.1]. It behaves like the peak forms apart from a scaling of the time constant.

### 2.3 Program-dependent (auto / two-stage) release

The two-stage circuit is described by Hugh Robjohns **[S16]**. Two time-constant capacitors are stacked. "The loudest two-thirds (or thereabouts)" of the control voltage discharge fast ("typically 30 ms"), and the "last 4 dB or so" release slowly ("maybe … 700 ms"). [S28] (p. 402) names the SSL bus compressor as using "two release networks stacked on top of each other", and says Fairchild-era tube units used similar designs.

A digital model (my construction, following [S16]/[S28]): run two smoothing branches on the same target x_L.

```
fast:  y_f  = branching detector with (τA,       τR_fast)
slow:  y_s  = branching detector with (τ_charge, τR_slow)   // τ_charge >> τA, so it only fills on sustained GR
GR_dB = -max(y_f, y_s)              // "max" variant (also used by an open Fairchild model [S12-adj, see §4.3])
or     GR_dB = -(w·y_f + (1-w)·y_s) // "weighted" variant, w ≈ 2/3 per [S16]
```

A short peak only fills the fast branch, so it recovers quickly. A long loud passage also fills the slow branch, so recovery ends slowly. That is the "gain platform" described in the Neve manuals [S23].

### 2.4 Converting published times into τ

| Published definition | Conversion to one-pole τ | Used by |
|---|---|---|
| "for 63% recovery" | τ = stated time | 1176LN release [S2] |
| "x ms for 50% release" | τ = t / ln 2 ≈ 1.443·t | LA-2A first stage [S6, S7] |
| "complete release in t" | τ ≈ t / 3 (≈95%). **Estimate:** "complete" is undefined | LA-2A second stage [S6] |
| "dB per second" | linear-in-dB ramp, not exponential | dbx 160 [S17, S18] |
| bare "attack/release time" (SSL, API, Neve, Manley, CL1B, Distressor) | definition not published. **Treat as τ (estimate)**, then tune by ear | most units |
| "release time from 10 dB of limiting" | **SPICE-derived (§4A): ≈ time to recover to ~0.5–1 dB ≈ 2.3–3 τ.** Not τ | Fairchild 670 [S10]; SSL fixed steps behave the same |

### 2.5 Feedback vs feedforward in Bloom

Bloom's detector listens to the **dry** input, and the gain lands on the **reverb tail**. That is a keyed (external side-chain) setup, like a ducker. In this arrangement a true feedback loop doesn't exist. Feedback character is approximated by (a) a softer knee, (b) a lower effective ratio (a feedback design can't reach ∞:1 [S28, Eq. 18]), and (c) a slightly slower, smoother attack. Section 5 adds an optional "self-keyed" mode, where the detector hears dry plus tail. That is closer to a real room mic going into a compressor.

---

## 3. Mapping the compressor onto Bloom

The room-mic trick, in compressor terms: the room mic goes through a compressor with heavy GR and makeup gain. While you play, GR is large and the room sits roughly where it was. When you stop, GR releases and the makeup gain lifts the decaying room. Andy Johns put it this way: running room mics through 1176s "brings up the decay time of the room when your guy hits the bass drum or the snare … at medium or half-time tempo" **[S1, "Drums" section]**. The Distressor notes say slower releases let "room ambience … 'swell up' on the tom and snare rings later" **[S24]**.

The Bloom signal law (proposed):

```
det    = detector( dry input  [ or dry + wet in "self-keyed" mode ] )
GR_dB  = generic model (§2) applied to det                      (<= 0)
wet_gain_dB = clamp( Amount_dB + GR_dB,  -MaxDuck_dB,  +Amount_dB )
tail_out = tail * dB2lin(wet_gain_dB)          // direct + early reflections untouched, tank untouched
```

- **Amount** is the makeup gain: the most the tail can be lifted when nothing is playing.
- **Threshold** is where the ducking starts.
- **Attack and Release** are the detector times, or a preset's model.
- **Predelay** is a delay on the tank input, as in D-BLOOM.

**Why it stays clean** (derived): the tail is only lifted when the dry level is low, which is exactly when there's headroom. During loud playing, GR pulls the lift back. If Amount ≤ the GR reached on typical loud playing, the tail's peak level never goes above the un-Bloomed peak. A simple safe default is **auto-Amount ≈ GR measured on steady loud playing**, the same idea as the API 2500's auto make-up [S20]. Bloom sits before the limiter, so the limiter is a backstop, not the mechanism.

**Why it sounds like a longer decay** (derived): a free tail falls at 60/T60 dB per second. That's 33 dB/s for the 1.8 s lock. While GR is releasing, the tail is lifted at the release rate. Releasing 10 dB with τ = 300 ms starts at about 33 dB/s, so the tail almost **plateaus** for a moment, then falls again. That is the "bloom". Fast releases give a pumping swell. Slow releases (opto, vari-mu) give a gentle lengthening.

**Attack matters less on a tail than on a close mic** (derived): the tail already builds up gradually and Predelay holds it back further. So attacks under about 1 ms (1176, Fairchild, API 30 µs) aren't audibly different from 1 ms when ducking a reverb tail. I suggest clamping Bloom's Attack to ≥ 0.1 ms. The detector should still run per sample, not per block: it costs a few multiplies per sample, and block-rate GR would step audibly at a 1–3 ms block size.

---

## 4. Unit-by-unit findings

### 4.1 Teletronix LA-2A (opto, T4 cell)
- **Detector:** opto. An electro-luminescent panel driven by the audio shines on a photoconductive cell. "Rectification and filtering … are not necessary" and speed is "limited only by the response of the … photo cell" **[S6]**.
- **Topology:** feedback. The side-chain is taken after the T4 divider (GroupDIY and UA plug-in manual, via search summary; medium confidence).
- **Static curve:** compression starts at the breakaway point, "gradually increases over the first 10 dB of input level rise", then becomes horizontal (limiting). The manual's Figure 1 shows the breakaway at −30 dB input, flat from −20 dB **[S6]**. In generic-model terms that is a soft knee about 10 dB wide (derived), ending in ∞:1. The UA 2-LA-2 manual says Compress is "approximately 4:1, program-dependent" and Limit is "up to Infinity:1" **[S9]**. The T4 is "program and frequency dependent" **[S8]**.
- **Attack:** UA spec 10 ms **[S7, S8]**. Note: the 1966 original manual's spec line reads "essentially instantaneous (10 µsec)" **[S6]**. Sources disagree. Use 10 ms, which matches every modern UA document.
- **Release:** two-stage, history-dependent. About 60 ms to 50% release, then gradual. The original spec says "0.5 to 5 seconds for complete release depending upon amount of previous reduction". The original text and UA history say "1 to 15 seconds" **[S6, S7, S8]**. Heavy or long compression leads to slower release **[S8]**.
- **Side-chain EQ:** there is a "gain reduction frequency response control", a rear HF-emphasis adjustment, so the detector can be made more sensitive to highs **[S6]**.
- **Link:** the 2-LA-2 has a Link/Dual switch **[S9]**. T4 cells vary unit to unit **[S9]**.
- **DSP model:** Najnudel et al. (DAFx-23) model a vactrol, an LED plus photoresistor of the LA-2A family, physically. Attack ranges from tens of µs to release in hundreds of ms, and "the attack time decreases with the received light" **[S29]**. For Bloom, use the cheaper behavioural model below.
  - **Opto model (superseded by the fitted model in §4A.1; kept for history; estimate, built on [S6–S8, S29]):** let light L follow the detector with τA = 10 ms. Let the "memory" M (0…1) charge from sustained GR with τ_mem ≈ 1–2 s. The release is the weighted two-stage form from §2.3, with w = 0.5 (because "50% release"). τR_fast = 60 ms / ln 2 ≈ 87 ms (derived). τR_slow = 0.3 s + M·2.7 s (estimate, scaled from "0.5–5 s complete").

### 4.2 UREI / UA 1176LN (FET)
- **Detector and topology:** peak-type. Feedback: the side-chain is taken from the output (Moore, *ARP Journal* 2012, via search summary **[S5]**; UA's API manual also groups the 1176 with feedback designs **[S20]**).
- **Attack:** 20–800 µs **[S1, S3]**. The catalog says "less than 20 µs" **[S2]**. The UA plug-in manual notes actual attack "varies slightly based on the selected ratio … lower ratios … fastest" **[S1-plugin]**.
- **Release:** 50 ms–1.1 s **[S1, S3]**, defined "for 63% recovery", so it is τ directly **[S2]**.
- **Ratios:** 4:1, 8:1, 12:1, 20:1. Higher ratios also raise the threshold. Soft knee **[S1]**. Knee width is not published. Estimate 4–6 dB.
- **All-buttons ("British") mode:** "distortion increases radically due to a lag time on the attack of initial transients and there are constant changes in the attack and release times, as well as a change in the bias points" **[S1]**. Pulsar describes the ratio as "between 12:1 and 20:1" and "a slight delay on the attack, and the release drops off in a severe and sudden way" **[S4]**, a secondary source. UA: engineers "typically use 'All-button' mode on drums or on ambience or room mics" **[S1]**.
- **Room/ambience settings from the UA manual [S1]:** Andy Johns ran room mics through 1176s "just so that they are nudging a bit", working at medium or half-time tempos. Jay Newland put a single room mic through an 1176 at "a healthy 3–5 dB". Allen Sides used overhead mults through 1176s in all-button mode.
- **Bloom mapping:** ratio 20 (or 16 with ±4 drift for all-buttons). τA 0.2–0.8 ms. For the all-buttons feel, add an estimated 1–3 ms onset lag before the GR starts. τR 50–1100 ms, about 300 ms for medium tempos (estimate). Knee 5 dB (estimate).

### 4.3 Fairchild 660 / 670 (vari-mu tube)
- **Gain element and topology:** variable-mu tube (gain changes with grid bias). **Feedback:** "the 670 circuit is a feedback design as the 'sidechain' amplifier monitors the output" **[S12]**. The 660 is the mono version with the same six-position timing switch **[S33]**.
- **Ratio and knee:** the spec is "variable from 1:1 to 1:20 above a predetermined level" (factory +2 dBm) **[S10]**. The brochure text describes a 2:1 compressor up to a "30 to 1" peak limiter **[S10]**. The AC and DC threshold controls "jointly control the threshold, ratio and knee shape" **[S12]**, so the curve is a gradual soft knee whose ratio grows with level.
- **Time constants (original manual [S10]; release "from 10 dB of limiting"):**

| Pos | Attack | Release |
|---|---|---|
| 1 | 0.2 ms | 0.3 s |
| 2 | 0.2 ms | 0.8 s |
| 3 | 0.4 ms | 2 s |
| 4 | 0.4 ms | 5 s |
| 5 | 0.4 ms | program: 2 s for individual peaks, 10 s for multiple peaks |
| 6 | 0.2 ms | program: 0.3 s individual peaks, 10 s multiple peaks, 25 s consistently high level |

  UA's table differs on attack: pos 4 is 800 µs, pos 5 is 200 µs, pos 6 is 400 µs. UA also notes "actual measured times are a bit different, but the overall trend is the same" **[S11]**. The manual recommends position 3 as general purpose, 1–2 for pop and speech, and 4 for classical. Positions 5–6 "combine fast release with slow release" and are "least audible" **[S10]**.
- **DSP models:** Raffensperger, DAFx-12, a wave-digital-filter plus black-box model of the whole 670 **[S12]**, open source as "wavechild670". It's too heavy for us, and Bloom doesn't need the tone. An open-source plug-in (phu-fair-kid-67) models positions 5–6 as two parallel release branches combined with **max()**. It states its fast and slow values are *estimates*.
- **Bloom mapping (superseded 18 Oct 19:15, see §4A.4: these are recovery times, the real τ are 0.22 s + 3.2 s):** a two-stage release from §2.3. Pos 5: fast 2 s, slow 10 s. Pos 6: three stages, 0.3 / 10 / 25 s, or two stages, 0.3 / 10 s. Knee wide (estimate 10–15 dB), ratio rising from about 2:1 toward 20:1.

### 4.4 SSL G-series stereo bus compressor (VCA)
- **Ratios:** 2:1, 4:1, 10:1. Ratio interacts with threshold: "as Ratio is decreased, the effective threshold is lowered" **[S13]**.
- **Attack:** 0.1, 0.3, 1, 3, 10, 30 ms **[S13, S14, S15]**.
- **Release:** 0.1, 0.3, 0.6, 1.2 s, or Auto. Auto is "program-dependent, multi-stage" **[S13]**, and "dependent upon the duration of the program peak" **[S14]**. [S28] names it as the classic two-stacked-release-network design. **No official time constants for Auto are published.** Forum circuit readings exist but are unverified, so I haven't used them.
- **Link:** always fully linked; "the control set always adjusts both … simultaneously" **[S13]**. Threshold ±15 dB, make-up −5 to +15 dB **[S14, S15]**.
- **Side-chain:** the Waves plug-in adds a side-chain HPF of 21–500 Hz **[S14]**. I found no source showing one on the original console module, so treat it as optional.
- **Topology note:** [S28] says the SSL derives its side-chain from a "slave VCA that mirrors the main VCA's action" (p. 404). In practice that behaves like a feedback design (my reading).
- **Typical use:** 1–2 dB average GR on the mix bus **[S13]**. The common recipe is 2:1 or 4:1, 10–30 ms attack, Auto release, 1–3 dB GR (Access Analog, citing Robjohns). Drum bus: 4:1, 10 ms, 0.1–0.3 s, 4–6 dB (Waves blog).
- **Bloom mapping (superseded 18 Oct 19:15, see §4A.3: Auto is τ 42.8 ms + 5.1 s in series):** ratio 4, hard-ish knee (estimate 2 dB), τA 10 or 30 ms, release Auto as the §2.3 two-stage with fast ≈ 0.1 s and slow ≈ 1.2 s (estimate, bracketed by the fixed steps), linked.

### 4.5 dbx 160 (VCA, true-RMS)
- **Detector:** true RMS (Blackmer). Attack and release automatically track the program **[S17]**.
- **Topology:** feedforward (Mixonline "Birth of a Classic", via search summary **[S19]**; medium confidence).
- **Attack:** "15 ms for 10 dB level change above threshold; 5 ms for 20 dB; 3 ms for 30 dB" **[S17, S18]**. Derived fit: t_A ≈ 438·Δ^(−1.465) ms, where Δ is the dB over threshold. This reproduces 15 / 5.4 / 3 ms.
- **Release:** a constant **120 dB/s** on the original 160 **[S17]**. The 160A says "8 ms for 1 dB, 80 ms for 10 dB, 400 ms for 50 dB; 125 dB/sec rate" **[S18]**.
- **Ratio:** 1:1 to ∞ (120:1) on the 160. The 160A goes past ∞ to −1:1 ("negative compression") **[S17, S18]**. Knee: hard on the 160. The 160A offers OverEasy (soft) or hard **[S18]**.
- **Link:** the 160A uses "true RMS power summing" for stereo **[S18]**.
- **Bloom mapping:** RMS detector (estimate τ_rms ≈ 5–10 ms), attack from the fit above, release as a linear 120 dB/s ramp in dB. Punchy and even. It's a good "tight" preset but not needed in the core set.

### 4.6 API 2500 (VCA, RMS, switchable topology)
- **Attack:** 0.03, 0.1, 0.3, 1, 3, 10, 30 ms. **Release:** 0.05, 0.1, 0.2, 0.5, 1, 2 s, or variable 50 ms–3 s **[S20, S21]**.
- **Ratios:** 1.5, 2, 3, 4, 6, 10, ∞:1 **[S20]**. Threshold +10 to −20 dB **[S20]**.
- **Knee:** Hard, Med or Soft (Soft is "similar to an 'over-easy' type knee") **[S21]**. **No widths are published.** Estimate 0 / 6 / 12 dB.
- **Type:** New is feedforward, "harder … more transparent". Old is feedback, "smoother … more character", and in Old the make-up gain sits inside the loop **[S20]**.
- **Thrust:** a filter in front of the **RMS** detector with a 10 dB/decade slope, "the inverse of the pink noise energy curve". In LOUD it is −15 dB at 20 Hz and +15 dB at 20 kHz **[S20, S21]**. This is a neat, documented side-chain tilt we could reuse as a Bloom detector option.
- **Link:** 0 (independent), 50–100% in steps, with Shape filters on the link signal **[S20]**. On the 50th Anniversary unit the link has peak (fast) or RMS (slow) control-voltage filtering **[S21]**.

### 4.7 Neve 33609 and 2254 (diode bridge)
**33609/N (AMS Neve current manual) [S22]:**
- **Compressor:** ratios 1.5:1 to 6:1 (1.5, 2, 3, 4, 6). "Soft and progressive, so the true ratio is only attained > 5 dB above the threshold". That's a knee about 10 dB wide (derived, W/2 = 5 dB). Attack fast 3 ms ±1. Slow is 6 ms ±1 "with 100 Hz first order high-pass filter" in the detector. Recovery 100–1500 ms (manual steps 100, 400, 800, 1500 ms). **a1 = 100 ms / 2000 ms, a2 = 50 ms / 5000 ms** (two-stage auto). These are the only published fast/slow auto pairs in this survey, so they're very useful.
- **Limiter:** attack fast 2 ms ±1, slow 4 ms ±1. Recovery 50–800 ms, with the same a1/a2. Ratio: "change in output level < 0.1 dB with 10 dBu to 20 dBu step input", effectively > 100:1 (derived).
- **Link:** stereo mode links the side-chains so both channels get the same GR.

**2254/R (AMS Neve current manual) [S23]:**
- One gain element, two independent side-chains (limiter and compressor), "each … operates in a closed loop", i.e. feedback. The compressor side-chain samples before the output amp, and the limiter side-chain samples after it.
- **Limiter:** ratio > 100:1. Attack 5 ms (slow), or 100 µs–2 ms (Fast Attack). Recovery 100 / 200 / 800 ms or Auto.
- **Compressor:** ratios 1.5–6:1, "true ratio being reached within the first 5 to 10 dB above the Threshold". Attack 5 ms. Recovery: **the manual contradicts itself.** The control description says 100 / 200 / 800 ms / Auto. The spec table says 400 / 800 / 1500 ms / Auto.
- **Auto:** "rapid for isolated peaks, while remaining slow for persistently high levels … the programme rides on a slowly moving 'gain platform'". No 2254 numbers are published; the 33609 a1/a2 values are the nearest documented ones.

### 4.8 Empirical Labs Distressor (EL8) [S24]
- **Ratios:** 1:1 (colour only), 2:1 and 3:1 (parabolic knee; "2:1 knee can be as long as 30 dB"; elsewhere "+15 dB knee"), 4:1 and 6:1 (steeper knees that move toward limiting), 10:1 "Opto" (separate detector emulating EL opto behaviour), 20:1 and **Nuke** ("brick wall limiting, keeping any normal signal within 1 dB or so").
- **Attack:** 50 µs–30 ms. Faster still at 0 on 2:1–4:1.
- **Release:** 0.05–3.5 s (the operation notes also say "50 ms to 3 seconds"). In 10:1 Opto, release "can extend up to 20 seconds" (program-dependent). **Nuke release is "logarithmic, meaning it lets off quickly at first and then slows"**, so a two-stage model fits.
- **Detector options:** HPF 100 Hz at 6 dB/oct, band emphasis around 6 kHz, stereo link.
- **Room mics (the use case):** "The 'Nuke' ratio was originally developed for room mics". Settings: "20:1 or 'Nuke', [10, 6, 2.5, 6]" (input, attack, release, output) or "attack on 5 and release on 3" (elsewhere "attack on 4 and release on 2"). "Fifteen to twenty dB of compression … the John Bonham thing". "Release should be quick (< 3) for the largest sound, but slower releases … room ambience can be made to 'swell up' on the tom and snare rings later". Also: "20 dB of compression can bring the noise floor up by 20 dB". Bloom avoids that, because it lifts a noiseless tail.
- **Knob-to-time taper is not published.** (Attack taper revised in §4A.5 from manual anchors.) Assuming a logarithmic taper (estimate): attack(k) = 0.05·600^(k/10) ms, release(k) = 0.05·70^(k/10) s. That gives attack 5 ≈ 1.2 ms, attack 6 ≈ 2.3 ms, release 2.5 ≈ 0.15 s, release 3 ≈ 0.18 s.

### 4.9 Manley Variable Mu (vari-mu tube) [S25]
- **Attack:** continuously 25 ms (Fast) to 70 ms (Slow).
- **Recovery:** 0.2, 0.4, 0.6, 4, 8 s (5-position switch).
- **Compress:** 1.5:1 with a soft knee. **Limit:** 4:1, rising to 20:1 once limiting exceeds 12 dB; the knee "actually softens as more limiting is used".
- **Maximum GR:** "can never achieve greater than −10 dB of gain reduction" (stated by UA as matching the hardware). That is a useful built-in safety cap for a Bloom preset.
- **Side-chain HPF:** −3 dB at 100 Hz, 6 dB/oct. **Link:** side-chain link switch. M/S mode is available.
- Remote-cutoff (vari-mu) gain element, continuously re-biased by the side-chain. Topology isn't stated in the UA manual.

### 4.10 Tube-Tech CL 1B (opto) [S26, S27]
- **Gain element:** optical. Tube-Tech calls it the "CL 1B Opto Compressor" [S27]. The side-chain is solid-state (JFET op-amps) [S26].
- **Ratio:** continuously 2:1–10:1. **Threshold:** +20 to −40 dBu.
- **Attack:** 0.5–300 ms. **Release:** 0.05–10 s (Manual mode).
- **Fixed mode:** attack 1 ms, release 50 ms.
- **Fix/Man mode:** fast attack (1 ms) and "a fast release when the peak disappears, then superseded shortly thereafter by the release time selected by the release control". The **attack knob becomes the delay** before the slow release takes over. This applies only when the peak is shorter than the attack setting. It's a documented, controllable two-stage release, and a good pattern for Bloom's Release control.
- **Manufacturer suggestions:** Final mix: Fix/Man, 3–4 dB. Standard instruments: Manual, 4–5 dB. Heavy: Manual, 10 dB. Knob positions are given in o'clock only.
- **Link:** up to ten units via side-chain sockets.

### 4.11 "Room-mic crush" practice and the SSL Listen Mic Compressor
- **History:** on the SSL 4000 the Listen Mic (talkback) circuit had "a huge great compressor on it … so that if somebody was talking quietly in the corner you'd still hear them". Hugh Padgham opened it while Phil Collins played and "out came the most unbelievable sound". It was then re-routed to a channel, and the channel gate added the cut-off: "when you compress a sound in a live room it brings up all the background noise and the echo in a room … going from all to nothing in milliseconds" **[S30]**.
- **Numbers:** SSL describes its LMC+ as having "fixed attack and release curves" **[S32]**. **SSL does not publish the times.** Korneff's model offers up to 100:1 **[S31]**. That is a modelled value, not an SSL spec.
- **Other documented crush recipes:** 1176 all-buttons on rooms and overheads **[S1]**; Distressor Nuke at 15–20 dB GR **[S24]**; Andy Johns' 1176 "nudging" for medium tempos **[S1]**.
- **Takeaway for Bloom:** the room-mic effect comes from (1) heavy GR with fast-to-medium release, and (2) makeup gain lifting the room between hits. Bloom does both on the tail alone, with no noise floor coming up and no tone change. An optional gate after Bloom would give the gated-room sound. That is a separate feature and out of scope here.

---

## 4A. Circuit and modelling evidence (per unit)

*Added 18 Oct 2026, 19:15 (UK time).* Idle asked for more than the manuals. This section uses three other kinds of evidence:

- **Circuit drawings.** Original schematics, where the actual resistor and capacitor values can be read off.
- **Published circuit models.** DAFx/AES papers, theses, and plug-in or DIY designers' write-ups.
- **My own SPICE simulations of those circuits.** These are in `spice/`, and §4B explains what they are and how far to trust them.

**New words used here:**
- **RC time constant.** A resistor R draining a capacitor C makes the voltage fall to 37% in R×C seconds. That is the "τ" from §1.
- **Gain element.** The part that actually turns the audio down: a light-dependent resistor, a FET, a VCA chip or a tube.
- **Control law.** How many dB of turn-down you get per volt of control signal.
- **Rectifier.** Turns the audio wave into a one-sided "how loud" voltage. *Full-wave* uses both halves of the wave.
- **Peak-hold vs average.** A diode in front of the capacitor lets it charge but not discharge back through the source, so it holds peaks. Without that diode, the capacitor follows the *average* level.
- **Dead zone.** A stretch of control voltage that produces no gain change at all. The control has to cross it before anything happens, which shows up as a lag.
- **Sum of exponentials.** A release made of two or three simple decays added together, each with its own τ. That gives a fast-then-slow ("multi-slope") release.

Confidence labels used below:
- **published:** from the manufacturer.
- **circuit-derived:** worked out from component values on a schematic.
- **measured (third party):** someone measured real hardware.
- **SPICE-derived:** my simulation of schematic parts. The device-model source is noted.
- **behavioural fit:** a model whose numbers were fitted to measurements.
- **estimate:** my guess.

### A key cross-unit finding: what "release time" on a panel means
On the Fairchild and SSL, the release number printed by the switch is **not** the RC time constant τ. It is about the time to recover from roughly 10 dB of gain reduction to within about 1 dB, which works out to **2.1–2.5 × τ**. Two pieces of evidence:
- The SSL 0.3/0.6/1.2 s switch positions have τ = 127/263/564 ms. In SPICE they reach 1 dB after 0.26/0.55/1.18 s.
- Fairchild positions 1–4 have τ = 0.10/0.30/0.88/1.76 s. In SPICE they reach 1 dB after 0.26/0.76/2.23/4.45 s. The manual says 0.3/0.8/2/5 s.

This also explains the "manual values look shifted" puzzle raised on GroupDIY [S47]. **The 1176 is the exception:** it explicitly specifies "63% recovery", which is τ. That checks out against its circuit: (270 k + 0…5 MΩ) × 220 nF = 59 ms…1.16 s [S39].

### 4A.1 Teletronix LA-2A (T4 optical cell)
**Curve shapes and components**
- **Gain element.** Two CdS (cadmium sulphide) light-dependent resistors form a shunt attenuator. Their resistance falls as light rises, roughly R ∝ light^(−γ). For audio-type CdS cells the slope γ is 0.6–0.85, and the PDV-P8001 datasheet gives 0.6 [S38].
  - The light comes from an **electroluminescent (EL) panel** in the original T4 [S6].
  - Moore's 2025 JAES paper describes it as a "tungsten lamp" [S37]. That's a disagreement between sources. The original 1966 manual says electro-luminescent. UA's own reissue T4B also uses an EL panel (Stroe's Table 2.1 [S36]).
- **Detector.** There is no rectifier and no RC network. The panel plus the LDR *are* the detector [S6]. The topology is feedback [S37].
- **Knee from the device.** Steady-state gain is 1/(1 + Rs·G), where G is the LDR conductance (1/R) and grows as light^γ. That gives a soft knee by itself:
  - At low levels the attenuation is tiny.
  - At high levels the local ratio levels off at about **1 + γ·n**, where n is how steeply the panel's light rises with drive voltage.
  - In my behavioural model (γ = 0.6, n = 3, an estimate) the ratio rises smoothly from 1.1:1 to about 2.7:1. UA quotes "about 4:1" [S9], so n·γ ≈ 3 is the value to tune toward.
- **Attack has two stages** (measured on optical cells [S36]): the first 63% of the gain reduction comes quickly, and the last 37% creeps in slowly. On Stroe's cell closest to a T4 ("CdS + old-modelled panel"), the first stage took 128 ms and reaching full gain reduction took another 1.0 s. That was measured open-loop, with the cell outside a compressor.
  - In a feedback loop it gets much faster. My SPICE closed loop with the fitted cell reaches 63% in about **20 ms**.
  - Measurements on six real LA-2As [S37] took 33–81 ms to *settle* (a stricter measure). UA quotes 10 ms [S7].
- **Release has two stages plus "memory"** [S36]. Measured release time to 63% on the same cell:
  - 90 ms after a 0.3 s burst.
  - 580 ms after a 1 s burst.
  - 1560 ms after a 5 s burst.
- **Physics behind this** [S36, S38, S44]:
  - Photo-cells have a "light history" effect: after a long, bright exposure they recover more slowly.
  - Lawrence (1964, via [S36]) says the cell stays faster at re-attacking if it compressed within the last 20–30 s.
  - PerkinElmer describes the resistance "tripling in a couple of milliseconds and then increasing linearly with time" [S36].
  - Eichas & Zölzer measured a VTL5C2 opto: below 1 kΩ within 5 ms of switching on, but about 500 ms to get back above 1 MΩ after switching off, roughly 100× slower [S44].
- **Fitted Bloom model (behavioural fit to [S36]; SPICE-checked).** The release τ applies to the LDR conductance:
  - **τ_rel = 0.06 s + 1.53 s × M₂.** M₂ is a "memory" level from 0 to 1. It charges through two cascaded lags of 0.84 s each while light is on, and drains over about 20 s (estimate) when dark.
  - The 0.06 s floor matches UA's "60 ms to 50%" [S7]. The fit hits 0.14/0.57/1.51 s against the measured 0.09/0.58/1.56 s.
  - Converting conductance to dB, GR = 20·log10(1 + Rs·G), gives the opto shape: dB falls almost in a straight line at first, then eases into a slow tail.
  - After a 5 s burst, the SPICE model recovers to 0.5 dB in 4.8 s, inside the spec's "0.5–5 s complete" [S6].
- **Spread between units is large.** On six real units, release took 449–1670 ms to settle and attack 33–81 ms [S37]. So any LA-2A preset is "one good unit", not "the" LA-2A.

### 4A.2 UREI 1176LN (FET)
**Curve shapes and components**
- **Gain element.** A JFET used as a voltage-controlled resistor shunting the signal. Early units used the 2N3819; the 2N5457 is a common substitute. Its channel resistance follows roughly Rds ≈ Ron/(1 − Vgs/Vp), where Vgs is the gate voltage and Vp the pinch-off voltage at which the FET stops conducting.
  - With vendor SPICE models [S40]: Ron = 273 Ω (2N5457, Motorola model) and 130 Ω (2N3819, Vishay model).
  - The usable range is about 30 dB of gain reduction. That figure comes from Haible's PSpice study of the 1176 [S41]; I set my series resistor to reproduce it, so it's an assumption in my model.
  - Half the drain signal is fed back to the gate (the 1 M/1 M network). That reduces distortion and doesn't change the timing.
- **Detector.** A full-wave peak rectifier charges C27 (220 nF) through the attack network (25 k pot plus a small source resistance) and discharges it through 270 k + a 5 M pot [S39]. The **ratio buttons change both the rectifier bias and the feedback gain** [S41]. That's why higher ratios also raise the threshold, and why the knee gets harder at 12:1 and 20:1 [S5].
- **Attack and release depend on level, by design of the circuit.** This is a feedback loop around a FET whose dB-per-volt slope changes along its curve, so the loop gain and therefore the time constants move as gain reduction builds up [S41].
  - SPICE-derived, 2N5457, fastest attack: 63% of GR in 0.16 ms at 8 dB of gain reduction, and 0.09 ms at 16 dB.
  - Slowest attack: 1.2 ms and 0.7 ms.
  - A third party measured a Klark Teknik clone at about 0.5 ms to the 37% point but about 5 ms to full gain reduction [S39].
  - So the manual's "20–800 µs" describes the *start* of the gain change. The tail of the attack settles over roughly the RC time (up to 5.5 ms). I've added a new `attack_settle_ms` field for that.
- **All-buttons mechanism** [S41]. Pressing several buttons shorts part of the shared bias divider. That pushes the FET past pinch-off, so the control voltage first has to cross a **dead zone** before any gain reduction happens, which is the "lag on the attack". The loop then flips between open and closed, which is why "attack and release constantly change".
  - My SPICE run with 0.6 V of extra bias shows the threshold rising and only tens of µs of extra lag at the fastest attack.
  - The lag should grow with slower attack settings and lighter drive. **The 1–3 ms onset lag remains an estimate.**
- **Not used.** My 1176 static-curve SPICE run gave an implausible curve: compression started at the lowest test level and the ratio fell with level. The rectifier gains and bias I assumed weren't calibrated to a real 1176, so I'm not quoting a 1176 ratio curve from it. The knee width stays an estimate (5 dB).
- **Published model.** Gerat, Eichas & Zölzer (AES 143, 2017) built a gray-box 1176LN model from measurements of a clone [S45]. I only read the abstract, which is behind a paywall, so I took no numbers from it.

### 4A.3 SSL 4000 G bus compressor (VCA)
**Curve shapes and components** (read from SSL drawings 82E26/82E27 [S34])
- **Gain element.** A dbx 202C VCA, the predecessor of the THAT 2180 [S35]. Its gain in dB is proportional to its control voltage (an "exponential" VCA). So gain reduction in dB tracks the timing-capacitor voltage directly.
  - The volts-to-dB scale between the capacitor and the VCA isn't readable from the drawings. I **assumed** 20 dB/V. That affects only absolute levels, not the timing.
- **Topology.** A second "sidechain" VCA copies the main one, so the detector hears the *output*. That makes it effectively a feedback design [S28, S35].
- **Detector.**
  - A full-wave rectifier (TL074/741 stages) feeds a diode, then the attack resistor, then the release capacitor, then a buffer. That is a **linear-volts peak detector**: not RMS and not logarithmic [S34, S35].
  - The ~0.6 V diode sets the real threshold [S35].
  - Attack resistors: 820 Ω, 2.7 k, 8.2 k, 27 k, 82 k and 270 k into 0.47 µF, for the 0.1/0.3/1/3/10/30 ms positions.
  - Fixed release resistors: 180 k, 270 k, 560 k and 1.2 M across 0.47 µF [S34].
- **Attack depends on level and ratio** (circuit-derived, SPICE-confirmed).
  - The bare RC is about 4× the label. For example, 82 k × 0.47 µF = 38.5 ms for the "10 ms" position.
  - The feedback loop divides it by roughly the local ratio. At 4:1, SPICE gives 63% in 26.7/14.5/9.4 ms at 4/8/13 dB of gain reduction.
  - So the panel labels hold at heavy compression (about 12 dB). The real attack is slower at light compression and faster at 10:1.
- **Auto release is two RC sections in series** [S34], confirmed on an original 1979 card by GroupDIY members [S47b]. It replaces my old estimate.
  - Fast section: 91 k ∥ 0.47 µF, **τ = 42.8 ms**. Slow section: 750 k ∥ 6.8 µF, **τ = 5.1 s**.
  - The charging current flows through both sections. A short peak mostly charges the small capacitor, so it releases quickly. Sustained compression transfers charge to the big one, ending at 750/(91+750) = 89%.
  - SPICE confirms the release is *exactly* a sum of two exponentials (fit error 0.035 dB). The slow share is 0.11/0.36/0.69/0.86/0.88 after 0.05/0.3/1/3/8 s of compression, closely following **w_slow ≈ d/(d + 0.62 s)**, where d is how long it had been compressing.
  - Measured on the release: after a 50 ms burst, gain reduction halves in 35 ms and is within 1 dB by 0.12 s. After 3 s or more, it takes 2.8 s to halve and 9.6 s to reach 1 dB.
- **Disagreement.** The popular gyraf/GSSL clone swaps the two resistors, giving 0.35 s and 0.62 s, which is far less program-dependent. Its "2.4 s Auto" spec isn't a time constant [S35, S47b]. The original values are the ones above.
- **Ratio changes with level** (circuit-derived law, SPICE-checked). In a feedback loop with a linear detector and a dB-linear VCA, the local ratio is about **R₀ + 0.115 × GR(dB)**: each extra dB of gain reduction adds about 0.12 to the ratio.
  - SPICE at 4:1: 3.9 → 4.4 over 4–13 dB of gain reduction. That is less than the ideal law predicts, because of ripple and peak-hold losses.
  - The knee is a **hard onset** at the diode threshold. The softness comes from this rising ratio, not from a designed knee. The ratio switch also shifts the threshold [S35].

### 4A.4 Fairchild 660/670 (vari-mu, 6386 tube)
**Curve shapes and components** (Raffensperger, DAFx-12 [S12])
- **Gain element.** A 6386 remote-cutoff triode. Its gain (transconductance, gm) fades gradually as the grid is driven more negative. Raffensperger's black-box tube equation, fitted to the GE datasheet, gives this gain-reduction law against sidechain voltage V (anode at 250 V, bias −7.2 V):
  - **GR ≈ 18.1·ln(1 + V/8.06) dB** (max error 1.3 dB over 0–30 V).
  - That's about 1.9 dB/V at the start, falling to about 0.4 dB/V at 30 V. The full table is in `spice/raw/fairchild_fit.json`.
  - This concave law, where each extra volt buys less gain reduction, is where the 670's ever-softening knee and gentle "ratio grows with level" come from.
- **Detector.** A push-pull sidechain amplifier whose class-B first stage has deliberate crossover distortion set by the DC-threshold pot. That's the knee control: below the crossover the stage barely conducts. It feeds a bridge rectifier, then the timing network. Feedback topology [S12].
- **Timing network** (Fig. 8 / Table 3 of [S12]): CT ∥ RT ∥ (RU + CU) ∥ (RV + CV).
  - My SPICE runs used this network with an assumed 100 Ω source, which reproduces the manual's 0.2 ms attack.
  - Pos 1–4 are single exponentials: τ = 0.10/0.30/0.88/1.76 s.
  - **Pos 5** has two time constants, τ = 0.22 s and 3.2 s. From 10 dB it reaches 1 dB 3.3 s after a 10 ms peak and 7.5 s after 3 s or more of limiting. The manual says "2 s / 10 s".
  - **Pos 6** has three, τ = 0.077, 1.12 and 8.2 s. From 10 dB it reaches 1 dB 0.29 s after a peak, 13 s after 1 s, and 18.9 s (25 s to 0.5 dB) after 10 s or more. The manual says "0.3 / 10 / 25 s". It matches.
- **Change to the preset.** The old Swell preset used 2 s and 10 s as τ. Those are recovery-to-about-1-dB times, so the old preset was **about 3× too slow** compared with the hardware.
- **Disagreements.**
  - A GroupDIY member read different component values and concluded the manual looked shifted by one position [S47]. That is resolved by the 2.3τ reading above.
  - The open-source phu-fair-kid-67 plug-in claims other parts ("100 k × 8 µF = 0.8 s") and uses 0.5/10 s and 1/25 s branches. Its own source marks these as estimates [S47].
  - The DAFx-12 table is the traced circuit, so I used it.

### 4A.5 Empirical Labs Distressor
- **No published schematic, so no SPICE model.** I'm not inventing one. What the manual does say [S42]:
  - The gain element is a VCA, and each ratio sets its own threshold and curve.
  - 2:1 and 3:1 have "parabolic" knees, up to 30 dB long on 2:1 ("+15 dB" elsewhere: a conflict inside the manual).
  - 4:1 and 6:1 are knees whose ratio keeps rising toward limiting.
  - 2:1, 10:1 and Nuke use "special detector circuitry".
  - The Nuke release is "logarithmic … lets off quickly at first and then slows".
- **Attack-knob taper**, from the manual's own emulation notes:
  - The 1176's attack range sits "below 3" and is emulated at "Att 0 – 3.5".
  - The spec gives 50 µs at 0 and 30 ms at 10.
  - That supports a two-piece logarithmic taper: **knob 3.5 ≈ 0.8 ms**, 4 ≈ 1.06 ms, 5 ≈ 1.85 ms, 6 ≈ 3.2 ms. The old single-log estimate gave 1.2 ms at knob 5.
- **Release taper is still an estimate.** The manual's "1176: rel 1–10.5" doesn't fit the stated 0.05–3.5 s range (the 1176 tops out at 1.1 s), so it can't be used as an anchor.
- **Topology** is described only as "based on the oldest compressor topology". That isn't stated explicitly as feedback or feedforward, so it is unknown.

### 4A.6 SSL Listen Mic Compressor (talkback, 82E33)
**Curve shapes and components** (read from the hand-drawn SSL sheet [S43])
- **Gain element.** A 2N5486 JFET shunt (T7) after roughly 22 k of series resistance, with the 1 M/1 M gate linearisation. A 10 k trimmer sets the FET bias, as in an 1176 [S43].
  - Maximum gain reduction is set by the FET's on-resistance against that 22 k: about 50 dB (SPICE-derived with the Siliconix model [S40]).
- **Detector.**
  - A precision full-wave rectifier (TDA + 741 with 4k7 resistors) feeds **1 k → C14**. I read C14 as "15 µF / 25 V", but the scan is unclear, so treat it with caution.
  - There's **no isolating diode**, so the capacitor charges *and* discharges through the same 1 k. That makes it an **average (mean-absolute) detector with symmetric τ ≈ 15 ms**, circuit-derived.
  - This replaces my old estimates of 1 ms attack / 100 ms release.
- **SPICE** (loop gain and bias assumed):
  - Attack reaches 63% in 4.3 ms at 11 dB of gain reduction and 2.3 ms at 25 dB.
  - The capacitor releases with τ = 15.0 ms. But the gain reduction is gone about 5 ms after the signal stops, because the capacitor rests well below the FET's pinch-off, in a dead zone. The next hit must cross that dead zone again.
  - Fast symmetric average-following plus that dead-zone snap is a plausible mechanism for its famous pumping. It isn't verified against a real console.

### 4A.7 Other published models (context, not used for numbers)
- Wright & Välimäki, *Grey-Box Modelling of Dynamic Range Compression*, DAFx-20in22 [S46]. A trainable compressor structure fitted to LA-2A data; useful later if we capture our own measurements.
- Najnudel et al., DAFx-23 vactrol model [S29]. A physical LED/LDR model; too heavy for us, but it confirms that "attack time decreases with the received light".
- Simionato & Fasciani, JAES 2025: state-space models of optical compressors (cited in [S37]; not read).

---

## 4B. How the SPICE models work and how far to trust them

**What SPICE is.** SPICE is a circuit simulator. You give it a list of parts and their connections (a *netlist*), and it works out every voltage and current over time. Plug-in developers use it to predict how a circuit's parts shape the sound before writing DSP. I used **ngspice 44.2** on the box.

Everything is in `spice/`:
- `netlists/*.cir`: the circuits.
- `models/devices.lib`: the transistor and diode models.
- `scripts/*.py`: the drivers, sweeps and curve fits.
- `raw/`: outputs. The `*_summary.json` files and CSVs are small; the full waveforms are in `raw_full.tar.xz`.
- `plots/*.png`: the figures.

**What is real and what is assumed, unit by unit:**

| Unit | Real (from schematic/datasheet) | Device model | Assumed | Trust |
|---|---|---|---|---|
| Fairchild 670 timing | CT/RT/RU/CU/RV/CV per switch position [S12] | 6386 black-box law (DAFx-12, fitted to GE datasheet) | 100 Ω source; 250 V anode; bias −7.2 V | **High** for release shape and times; medium for dB scale |
| SSL G bus | attack R's, release R/C, auto network [S34] | generic small-signal silicon diode for the 1S44 | VCA dB-per-volt scale (20 dB/V), rectifier offset per ratio | **High** for release; medium for attack-vs-level; trend-only for ratio-vs-level |
| 1176 | C27 220 nF, attack/release pots [S39] | 2N5457 (Motorola), 2N3819 (Vishay) | series R for a 30 dB range, rectifier gain/bias | Medium for timing trends; **static curve not usable** |
| LA-2A T4 | none (no SPICE model exists for a T4) | *behavioural* EL + LDR equations | γ = 0.6, EL exponent n = 3, memory decay 20 s; fitted to one measured cell [S36] | Medium: matches spec and measurements, but cells vary a lot |
| Listen Mic | 1 k / 15 µF timing, 2N5486, 22 k [S43] | 2N5486 (Siliconix) | loop gain, rest voltage −0.6 V; capacitor value read from a poor scan | Medium-low |
| Distressor | none | none | n/a | **Not modelled**: no schematic |

**How far to trust them, in plain words:**
- **Resistors and capacitors don't lie.** When the schematic gives the timing parts, SPICE reproduces the manual's release numbers closely (Fairchild and SSL above). Those results are solid.
- **Gain-element curves are only as good as the device model.** The JFET models are generic vendor ones, and real FETs vary by ±50% in pinch-off voltage. Treat FET-law numbers as shape, not gospel.
- **Where I had to guess a gain or a scale**, I say so, and I only quote *trends*: attack speeding up with level, ratio rising with gain reduction. I don't quote exact dB values.
- **Bloom doesn't need the tone parts.** I left out transformers, tube distortion and the FET's distortion. Bloom only steers the reverb tail's level.

**How to use this in the Bloom code:**
- For Glue and Swell, implement the **actual RC network** as two or three coupled one-pole states in "detector volts". Then map volts to dB with the unit's gain law.
  - SSL: dB = k·V.
  - Fairchild: dB = 18.1·ln(1 + V/8.06).
  - That costs a handful of multiplies per sample and reproduces the program-dependent release *exactly*. It is better than inventing two-stage weights.
- For Natural, run the opto state equations (`spice/scripts/la2a_t4.py`, function `net`) at control rate. They're cheap.


## 5. Recommended Bloom presets (core set of 5, plus 1 optional)

What makes compression bloom an ambience is the **release behaviour**, not the attack (§3). So the set spans the documented release families: opto memory, auto two-stage, fixed-fast FET, logarithmic brick wall, and very slow vari-mu.

| Preset | Emulates | Ratio / knee | Attack τ | Release model | Detector / SC | GR target | Confidence |
|---|---|---|---|---|---|---|---|
| **Natural** (default) | LA-2A, CL 1B Fix/Man | device soft knee (LDR γ 0.6 × EL n ≈ 3–5) → ≈3–4:1, limit ∞ | 10 ms [S7] (two-stage: 88% fast / 12% slow) | opto memory: τ = 0.06 s + 1.53 s·M₂, M₂ two lags of 0.84 s (behavioural fit [S36]) | light-domain (no rectifier) | 3–6 dB | medium |
| **Glue** | SSL G bus | 4:1 hard onset, ratio ≈ 4 + 0.115·GR | 10 ms label (RC 38.5 ms ÷ loop gain) [S13, S34] | Auto = series sections τ 42.8 ms + 5.1 s, slow share ≈ d/(d+0.62 s) (circuit-derived [S34]) | linear peak, linked | 1–4 dB [S13] | medium-high |
| **Room Crush** | 1176 all-buttons / Andy Johns | 16:1 ±4 drift, knee 5 dB (est.), max GR ≈ 30 dB [S41] | 0.4 ms [S1] start + ≈3 ms settle [S39] + 2 ms lag (est.) | branching, τR 300 ms (59–1160 ms circuit-derived [S39]) | peak, feedback | 5–10 dB ("nudging" 3–5 [S1]) | medium |
| **Nuke** | Distressor Nuke on rooms | ∞:1 (within 1 dB [S24]), knee 0 | ≈1.1–1.9 ms (knob 4–5, manual-anchored taper [S42]) | log release as two-stage: fast 0.15 s, slow 1.0 s (est.) | HPF 100 Hz 6 dB/oct [S24] | 15–20 dB [S24], Amount capped | medium (release estimated) |
| **Swell** | Fairchild pos 5 / Manley Vari-Mu | 6386 law GR = 18.1·ln(1+V/8.06) → ratio rises with level; GR capped 10 dB [S25] | 25 ms [S25] (Fairchild 0.2–0.4 ms [S10]) | real pos-5 RC network: τ 0.22 s + 3.2 s (circuit-derived [S12]); manual "2 s / 10 s" = recovery-to-1 dB | HPF 100 Hz 6 dB/oct [S25] | 3–6 dB | high (timing) |
| *Talkback* (optional) | SSL Listen Mic | limiter, FET range ≈ 50 dB (SPICE [S43]) | ≈2–4 ms effective (RC 15 ms in feedback) | symmetric τ 15 ms, average detector, dead-zone snap ≈ 5 ms (circuit-derived [S43]) | average, HPF 150 Hz (est.) | 20+ dB | medium-low |

Why these five:
- **Natural** is the safest default. Its release memory makes the tail bloom more after long loud passages and stay modest after single hits, the way people already expect an LA-2A to behave.
- **Glue** is gentle and tempo-friendly, for mixes where Bloom should be felt rather than heard.
- **Room Crush** is the classic documented ambience trick, with the medium-tempo pump [S1].
- **Nuke** is the extreme "John Bonham" room [S24]. Amount must be capped (I suggest ≤ 12 dB) so the tail can't jump past headroom between hits.
- **Swell** has the best-documented program-dependent times [S10] and gives a slow, cinematic lengthening for pads and ballads.
- The dbx, API and Neve units are documented (§4) and can become extra presets later. Two things from them are worth reusing now as global options: API's documented **Thrust** detector tilt and Neve's published **a1/a2** auto pairs (100 ms/2 s, 50 ms/5 s).

**Mapping onto the D-BLOOM controls:**
- **Amount:** makeup in dB, 0–12 dB, with auto-Amount ≈ median GR on loud playing.
- **Threshold:** in dBFS on the dry detector.
- **Attack:** sets τA, clamped to ≥ 0.1 ms.
- **Release:** for two-stage presets, scales both stages together, the way the CL 1B pairs fast and slow.
- **Predelay:** the tank input delay.
- **Sustain** (the transient T60 boost) is separate. It can be driven by the same GR signal. Suggestion: boost ∝ (Amount + GR)/Amount, hard-capped below the decay lock's stability limit.

At Amount 0 Bloom is bit-identical to off, as D-BLOOM requires.

---

## 6. Solid vs estimated: summary

**Solid** (published, multiple sources agree):
- 1176 attack and release ranges and ratios, plus its all-buttons description.
- Fairchild six time-constant positions (original manual).
- SSL G attack, release and ratio steps.
- dbx 160 attack-vs-level and dB/s release.
- API 2500 steps, Thrust slope and Type.
- Neve 33609 times, including a1/a2 auto pairs and knee "true ratio > 5 dB above threshold".
- 2254/R limiter times.
- Distressor ranges, ratios, detector filters and room-mic recipe.
- Manley attack, recovery steps, ratio law, 10 dB cap and SC HPF.
- CL 1B ranges and Fix/Man behaviour.
- LA-2A 10 ms attack and 60 ms to 50% release.

**Conflicts flagged:**
- LA-2A attack: 10 ms (UA) vs "10 µsec" (1966 manual).
- LA-2A complete release: 0.5–5 s (spec) vs 1–15 s (text).
- Fairchild attack per position: original manual vs UA table.
- 2254/R compressor recovery: control text vs spec table.
- Distressor max release: 3.5 s vs 3 s.

**Firmed up by circuits / SPICE (18 Oct 2026, 19:15):** SSL Auto (τ 42.8 ms + 5.1 s, series sections), SSL fixed release τ and attack-vs-level, Fairchild pos 1–6 eigen time constants and what the manual's numbers mean, LA-2A memory law (fitted to measured cells), Distressor attack taper (manual-anchored), Listen Mic timing (1 k/15 µF, average detector), 1176 timing RC and two-stage attack. See §4A.

**New conflicts flagged:** LA-2A light source (EL panel [S6, S36] vs "tungsten lamp" [S37]); SSL Auto original vs GSSL clone values [S35, S47b]; Fairchild component readings (DAFx-12 vs GroupDIY vs phu-fair-kid-67) [S12, S47]; Distressor 2:1 knee "30 dB" vs "+15 dB" [S42]; 1176 attack spec vs RC (spec = start of the gain change) [S39].

**Still estimated (old list, items now resolved are struck):**
- ~~SSL Auto release constants~~ (now circuit-derived).
- API and 1176 knee widths.
- Distressor knob tapers (attack now manual-anchored; release still estimated).
- LA-2A slow-stage law and memory constant (now a behavioural fit to measured cells; memory decay 20 s and EL exponent still estimated).
- 1176 all-buttons onset lag.
- SSL Listen Mic: times now read from schematic (C14 value from a poor scan); loop gain and HPF still estimated.
- Whether bare "attack/release" figures are τ or something else: for Fairchild and SSL they are ≈ 2.1–2.5 τ (SPICE); for the 1176 they are τ (63%); others still unknown.
- SSL VCA dB-per-volt scale; 1176 static curve (my SPICE run was not usable); Distressor anything circuit-level (no schematic).

---

## 7. Sources
- **[S1]** Universal Audio, *1176LN Classic Limiting Amplifier manual* (v3), https://media.uaudio.com/assetlibrary/1/1/1176ln_manual.pdf. **[S1-plugin]** UA, *1176 Classic FET Compressor Manual*, https://help.uaudio.com/hc/en-us/articles/34530260482324
- **[S2]** UREI, *1176LN Limiting Amplifier catalog*, https://www.steampoweredradio.com/pdf/urei/catalogs/UREI%20%201176LN%20Limiting%20Amplifier%20Catalog.pdf
- **[S3]** UREI, *1176LN owner's manual*, https://archive.org/stream/Urei_1176LN_owners_manual/Urei_1176LN_owners_manual_djvu.txt
- **[S4]** Pulsar Audio, *The History of All-buttons-in Mode* (2023), https://pulsar.audio/blog/the-history-of-all-buttons-in-mode/ (secondary)
- **[S5]** A. Moore, *All Buttons In: an investigation into the use of the 1176 FET compressor*, Journal on the Art of Record Production (2012), https://www.arpjournal.com/asarpwp/all-buttons-in-an-investigation-into-the-use-of-the-1176-fet-compressor-in-popular-music-production/ (seen via search summary only)
- **[S6]** Teletronix, *Model LA-2A Leveling Amplifier manual* (3-66), Library of Congress, https://tile.loc.gov/storage-services/master/mbrs/recording_preservation/manuals/Teletronix%20Model%20LA-2A%20Leveling%20Amplifier.pdf
- **[S7]** UA, *Teletronix LA-2A Classic Leveling Amplifier* specs, https://help.uaudio.com/hc/en-us/articles/206356233
- **[S8]** UA, *A History of the Teletronix LA-2A*, https://help.uaudio.com/hc/en-us/articles/215779663
- **[S9]** UA, *2-LA-2 manual*, https://media.uaudio.com/assetlibrary/2/-/2-la-2-manual.pdf
- **[S10]** Fairchild, *Model 670 Stereo Limiter manual*, https://fairchildusa.com/wp-content/uploads/2023/12/Fairchild-Model-670-Manual.pdf
- **[S11]** UA, *Fairchild Tube Limiter Collection Manual*, https://help.uaudio.com/hc/en-us/articles/13293388042900
- **[S12]** P. Raffensperger, *Toward a Wave Digital Filter Model of the Fairchild 670 Limiter*, DAFx-12, https://www.dafx.de/paper-archive/2012/papers/dafx12_submission_9.pdf. [S12-adj] github.com/huberp/phu-fair-kid-67 docs/fairchild670-spec-traceability.md (open-source model; values marked as estimates by its author)
- **[S13]** UA, *SSL 4000 G Bus Compressor Manual*, https://help.uaudio.com/hc/en-us/articles/30847649785748
- **[S14]** Waves, *SSL G-Master Buss Compressor manual*, https://assets.wavescdn.com/pdf/plugins/ssl-g-master-buss-compressor.pdf
- **[S15]** Sound On Sound, *SSL XLogic G-series Compressor* review, https://www.soundonsound.com/reviews/ssl-xlogic-g-series-compressor
- **[S16]** H. Robjohns, *Q. What does a compressor's auto-release control do?*, Sound On Sound, Sept 2014, https://www.soundonsound.com/sound-advice/q-what-does-compressors-auto-release-control-do
- **[S17]** dbx, *160/161 manual*, https://www.technicalaudio.com/pdf/dbx/dbx_160.pdf (spec table also transcribed at easymanua.ls/dbx/160/manual)
- **[S18]** dbx, *160A specifications*, https://dbxpro.com/en-US/products/160a/specifications.html, and 160A cut sheet
- **[S19]** Mix, *Birth of a Classic: The dbx 160 Compressor*, https://www.mixonline.com/technology/birth-of-a-classic-the-dbx-160-compressor (via search summary)
- **[S20]** UA, *API 2500 Bus Compressor Manual*, https://help.uaudio.com/hc/en-us/articles/4419505673620
- **[S21]** API, *50th Anniversary 2500 user manual* (2019), https://www.apiaudio.com/docs/manuals/2500-50th_user_2019-07-18.pdf
- **[S22]** AMS Neve, *33609/N user manual* issue 2.1, https://www.ams-neve.com/wp-content/uploads/2026/09/33609N1-User-Manual-Issue-2.1.pdf
- **[S23]** AMS Neve, *2254/R user manual* issue 2.4, https://www.ams-neve.com/wp-content/uploads/2023/01/2254R_User_Manual_Iss2_4-1.pdf
- **[S24]** UA, *Empirical Labs EL8 Distressor Manual*, including "Operation Notes From Empirical Labs" by Dave Derr, https://help.uaudio.com/hc/en-us/articles/18741515014676
- **[S25]** UA, *Manley Variable Mu Manual*, https://help.uaudio.com/hc/en-us/articles/18737967080340
- **[S26]** Tube-Tech, *CL 1B manual*, https://fast-images.static-thomann.de/pics/atg/atgdata/document/manual/manual_cl_1b_101115w.pdf
- **[S27]** Tube-Tech, *CL 1B Opto Compressor* product page, https://www.tube-tech.com/cl-1b-opto-compressor/
- **[S28]** D. Giannoulis, M. Massberg, J. D. Reiss, *Digital Dynamic Range Compressor Design: A Tutorial and Analysis*, JAES 60(6), 399–408, 2012, https://joshreiss.github.io/documents/2012/GiannoulisMassbergReiss-dynamicrangecompression-JAES2012.pdf
- **[S29]** J. Najnudel, R. Müller, T. Hélie, D. Roze, *Power-Balanced Dynamic Modeling of Vactrols: Application to a VTL5C3/2*, DAFx-23, https://www.dafx.de/paper-archive/2023/DAFx23_paper_50.pdf
- **[S30]** MusicRadar, *How Genesis's Peter Gabriel and Phil Collins stumbled upon the '80s gated-reverb drum sound* (Hugh Padgham interview, 2020), https://www.musicradar.com/features/how-genesis-peter-gabriel-and-phil-collins-stumbled-upon-the-80s-gated-reverb-drum-sound
- **[S31]** Sound On Sound news, *Talkback Limiter from Korneff Audio* (2020), https://www.soundonsound.com/news/talkback-limiter-korneff-audio
- **[S32]** SSL, *LMC+* product page, https://store.solidstatelogic.com/plug-ins/ssl-lmc
- **[S33]** Fairchild 660/670 information sheet, https://www.barryrudolph.com/recall/manuals/660-670info.pdf

- **[S34]** SSL drawings CF82E27 (compressor time constants) and 82E26 (mix amps, VCA, compressor sidechain), via gyraf.dk: https://gyraf.dk/gy_pd/ssl/ssl_82e27.gif, https://gyraf.dk/gy_pd/ssl/ssl_82e26.gif (copies in src/)
- **[S35]** J. Erland (gyraf), *The SSL Mixbus Compressor Clone*, https://gyraf.dk/wp-content/uploads/2018/05/The-SSL-Mixbus-Compressor-Clone.pdf
- **[S36]** O. Stroe, *Complete Overview and Analysis of an Electro-Luminescent Based Optical Cell*, MSc thesis, Univ. of Huddersfield, 2018, https://eprints.hud.ac.uk/id/eprint/34532/ (Table 6.6)
- **[S37]** A. Moore, *Objective Analysis and Perceptual Evaluation of LA-2A Compressors and Vocal Recordings*, JAES (accepted manuscript), https://pure.hud.ac.uk/ws/portalfiles/portal/140787498/AAM.pdf, doi 10.17743/jaes.2022.0240 (Table 3)
- **[S38]** Advanced Photonix, *PDV-P8001 CdS photocell* datasheet, https://advancedphotonix.com/wp-content/uploads/2015/07/DS-PDV-P8001.pdf; PerkinElmer, *Photoconductive Cells* intro, https://cdn-learn.adafruit.com/assets/assets/000/010/129/original/APP_PhotocellIntroduction.pdf
- **[S39]** GroupDIY, *1176: attack time wrong on the manual?* (2022, KT clone measurement), https://groupdiy.com/threads/1176-attack-time-wrong-on-the-manual.82136/; *Some more 1176 Qs* (pot/cap values), https://groupdiy.com/threads/some-more-1176-qs-ideas-attack-confusion-plus-ratios-nuke-content.62264/
- **[S40]** JFET SPICE models: 2N5457 Motorola (via https://www.diyaudio.com/community/threads/pspice-for-2n5457.230743/); 2N3819 Vishay and 2N5486 Siliconix from the LTspice standard library (https://github.com/evenator/LTSpice-Libraries/blob/master/cmp/standard.jft)
- **[S41]** J. Haible, *JH. Compressor: Discussing the Urei 1176* (PSpice study), https://www.jhaible.info/compressor/jh_compress.html
- **[S42]** Empirical Labs, *Distressor EL8 manual*, https://www.empiricallabs.com/wp-content/uploads/distressor_manual.pdf
- **[S43]** SSL CF82B33 *Talkback (Listen) Amplifiers and Compressor* drawing, https://gyraf.dk/schematics/SSL_82E33_Talkback.GIF; GroupDIY thread https://groupdiy.com/threads/ssl-talkback-listen-compressor.30888/
- **[S44]** F. Eichas, U. Zölzer, *Modeling of an optocoupler-based audio dynamic range control circuit*, Proc. SPIE 9948 (2016), https://www.hsu-hh.de/ant/wp-content/uploads/sites/699/2017/10/Eichas-Modeling-of-an-optocoupler-based-audio-dynamic-range-control-circuit-99480W.pdf
- **[S45]** E. Gerat, F. Eichas, U. Zölzer, *Virtual Analog Modeling of a UREI 1176LN Dynamic Range Control System*, AES Conv. 143 (2017), paper 9852, https://aes.org/e-lib/browse.cfm?elib=19249 (abstract only)
- **[S46]** A. Wright, V. Välimäki, *Grey-Box Modelling of Dynamic Range Compression*, DAFx-20in22, https://www.dafx.de/paper-archive/2022/papers/DAFx20in22_paper_35.pdf
- **[S47]** GroupDIY, *Problem with Fairchild 660/670 original manual data?*, https://groupdiy.com/threads/problem-with-fairchild-660-670-original-manual-data.40623/; huberp, phu-fair-kid-67 TimingNetwork.cpp, https://github.com/huberp/phu-fair-kid-67/blob/344b16ab/src/DSP/Models/Sidechain/TimingNetwork.cpp
- **[S47b]** GroupDIY, *(G)SSL - learning about Release variations* (original 1979 card measured), https://groupdiy.com/threads/g-ssl-learning-about-release-variations.63477/; *Understanding the gssl auto circuit*, https://groupdiy.com/threads/understanding-the-gssl-auto-circuit.81070/
