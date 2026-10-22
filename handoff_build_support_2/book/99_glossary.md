# Glossary

> **Status: DONE (draft 2026-10-05)** for every term used in Chapters 1–8. It grows with the book.

**How to use it.** Each entry gives an everyday sentence first, then a *Precise* note for engineers (and for Ben), then the chapter where the term matters most. Tags (VERIFIED / ASSUMED / LOCKED / PLANNED) live in the chapters, and the glossary follows them. Definitions marked *(general acoustics)* are standard textbook meanings, not project-specific facts.

---

## Numbers and symbols

- **1/r²** — Further away is quieter: twice the distance gives a quarter of the level. *Precise:* the locked geometric level law for each image in this engine ("Air Abs geometry is 1/r² VERIFIED"). An older public doc says 1/r and is out of date. (Ch. 1, 5)
- **2011 / Flat (2011)** — The original sound of Idle's Reaktor reverb, kept forever as a mode. *Precise:* the decay mode where every FDN line loses the same dB per second at every frequency; it will be protected by a frozen parity suite (D-SL10). (Ch. 1, 2, 8)
- **477 fold** — The rule for mixing three mics to two speakers: left + half the centre, right + half the centre. *Precise:* `L + 0.5·C`, `R + 0.5·C`; "477" is the Structure reference cited for it (that reading of the number is ASSUMED). (Ch. 1, 7)
- **z⁻¹** — "One sample later." *Precise:* unit delay; "z⁻¹ in both" means Play and Render both apply the Hadamard feedback on the next sample (S7). (Ch. 3, 5)
- **α (alpha), absorption coefficient** — How much of the sound a surface swallows per bounce, from 0 (mirror) to 1 (open window). *Precise:* random-incidence absorption per octave on a material card; converted to per-bounce α with 1 − e^(−α) in Surfaces mode. (Ch. 6)
- **κ (kappa)** — A scale factor in the Surfaces design. *Precise:* normalises the directional part of each line's rate so the delay-weighted mean equals the room target. (Ch. 6)

## A

- **A–F faces** — The six room surfaces. *Precise:* A Left (−X), B Front (+Z), C Right (+X), D Back (−Z), E Floor (−Y), F Ceiling (+Y); orientation ASSUMED from the older doc, D = back VERIFIED. (Ch. 6)
- **A/B** — Listening to two versions back to back to choose. *Precise:* level-matched render pairs with a checklist; every sound change is decided this way. (Ch. 4)
- **AB (mic setup)** — Two mics spaced apart. *Precise:* `ab_omni` / `ab_card` setups. (Ch. 7)
- **ABBA** — A fair way to time old against new. *Precise:* paired runs in the order old/new/new/old, 12 rounds, median of per-round differences; the PC result is the gate. (Ch. 3, 8)
- **Air absorption** — Air soaks up treble over distance. *Precise:* ISO 9613-1 by path length on early images and the FDN inject; the direct sound is air-free; never on the FDN return today. (Ch. 2, 5)
- **Allpass (diffuser)** — A filter that smears a click in time without changing its tone. *Precise:* a Schroeder allpass around each delay line with coefficient d = Dffs; |T| = 1 when lossless. (Ch. 5)
- **Arau-Puchades** — A reverb-time formula for rooms that are deader in one direction. *Precise:* area-weighted geometric mean of per-axis Eyring times; blended with Eyring by scattering in Surfaces (blend ASSUMED). (Ch. 6)
- **Array / Room (mic)** — On the stand, or moved off as a room mic. *Precise:* Array = capsule stays on the stand; Room = placed at the room-mic spot (one shared spot today; one per strip from T7/T8). (Ch. 7)
- **ASSUMED** — "This is a judgement, or not re-checked." *Precise:* tag for any claim not measured or read in a cited file. (all)
- **AudioWorklet** — The browser's slot for running live audio code. *Precise:* hosts `live_stereo.wasm`, called once per 128-sample block. (Ch. 2, 3)
- **Auto-treat** — A helper that suggests panels to hit a target decay. *Precise:* PLANNED (SL6, D-SL5): broadband porous by bisection, then up to 4 tuned panels at the worst 40–500 Hz excess vs the Mäkivirta target; suggestions only. (Ch. 6)
- **Axial mode** — The lowest note a room "hums" along one dimension. *Precise:* f = c/(2·length); default room ≈ 21.3 / 28.3 / 56.7 Hz at c = 340 (computed in the book). (Ch. 5, 6)

## B

- **Binaural** — Recording with a dummy head so headphones sound 3-D. *Precise:* SADIE II KU100 default, ears 0.18 m, K = 6 biquads per ear, `BINAURAL_REAR32`, IC-matched tail, centre mic muted. (Ch. 7)
- **Biquad** — One standard EQ building block. *Precise:* a second-order IIR section (two poles, two zeros); S1P2 uses three per line. (Ch. 6)
- **Bisection** — Finding a value by halving the range each time, like "higher / lower". *Precise:* auto-treat uses 30 halvings for coverage and 25 for panel area, fixed counts not tolerances. (Ch. 6)
- **Bit-exact** — Not one sample different. *Precise:* max-abs difference 0; required for any feature when switched off and for the main golden in NO sessions. (Ch. 8)
- **Block / block budget** — The small slice of audio Play must deliver on time. *Precise:* 128 samples at 48 kHz = 2.667 ms (`BUDGET_MS`). (Ch. 3)
- **The box** — The research computer. *Precise:* Linux machine that works on copies, prototypes, measures and writes prompts; never touches `software\` on the PC. (Ch. 1)
- **BRAS CR2** — A real, published, measured room used as a check. *Precise:* T20 125 Hz–8 kHz 1.34 / 1.72 / 2.00 / 1.94 / 1.74 / 1.54 / 1.11 s. (Ch. 6)
- **Build session** — One scoped job that changes the real program. *Precise:* one prompt per new Build window; ends with tests green and the golden hash recorded. (Ch. 1, 4)
- **Bus** — A group channel on the desk. *Precise:* Direct, Early, FDN, Host dry; with solo, mute and fader. (Ch. 7)

## C

- **c** — The speed of sound. *Precise:* locked at 340 m/s in the engine; the Surfaces prebuild uses 343 m/s (OPEN mismatch). (Ch. 5, 6)
- **Calibration (Surfaces)** — Render once, measure, nudge once. *Precise:* D-SL4: T20 per octave, scale factor clamped 0.6–1.6, redesign once; Play uses the Render-designed coefficients. (Ch. 6)
- **Capsule** — The sensing part of a microphone. (Ch. 7)
- **Cardioid** — A mic that mainly hears what is in front. *Precise:* heart-shaped polar pattern. (Ch. 7)
- **C migration (J2)** — Moving Play and Render onto one C engine. *Precise:* PLANNED; makes drift impossible; prerequisite for the plug-in. (Ch. 3)
- **Colour (mic)** — How a real mic changes tone, including with direction. *Precise:* measured minimum-phase FIR (Play, 80 ms) from SOS tables; modes Measured / User defined / Bypass. (Ch. 7)
- **Comb (filtering)** — A hollow, "flanged" colouring from regularly spaced peaks and dips. *Precise:* removed in the default room by the S4b H·D column signs. (Ch. 5)
- **Convolution** — Applying a room's echo fingerprint to a recording. *Precise:* Render's `fft_convolve` of the dry file with the IR; only possible for time-invariant processing. (Ch. 2, 3)
- **Cut line** — In a session prompt, the line above which work is essential. (Ch. 4)

## D

- **dB (decibel)** — The unit for loudness differences; −6 dB is about half the amplitude, −60 dB is a thousandth. *(general acoustics)* (all)
- **Decay dial / T60** — How long the tail rings. *Precise:* the dialled time for a 60 dB fall; with Decay lock on, it sets each line's loss `lg`. (Ch. 2, 5)
- **Decay lock** — The desktop default where the dial directly sets the decay. *Precise:* g = 1/√N plus per-line loss lg = 10^(−3·dᵢ/(sr·T)); off = the 2011 law g = Gain/N. (Ch. 5)
- **Decay mode** — How each line loses energy per trip. *Precise:* Flat (2011) shipped; Natural (air) LOCKED for SL7a; Surfaces LOCKED for SL1–SL6. (Ch. 2)
- **Denormal** — An extremely tiny number some processors handle very slowly. *Precise:* flushed below about 1e-20, plus a tiny DC offset in the loop. (Ch. 5)
- **DESIGNED** — Worked out and prototyped on the box, not in the program. (Ch. 6)
- **Desk** — The mixer page. *Precise:* three mic strips (L, C, R) and four buses; no EQ. (Ch. 7)
- **Dffs** — The strength of each line's smearing filter. *Precise:* allpass coefficient per line = surface diffusion sum × Diffusion Master, clipped to ±1; Smooth caps |Dffs| at 0.7 (LOCKED, T4). (Ch. 5)
- **Diffusion Master** — One knob scaling all the smearing. *Precise:* default −0.25, clamped [−0.5, 0]. (Ch. 5)
- **Direct sound** — The sound that travels straight from source to mic. *Precise:* image (0,0,0), voice 3, line index 2; filtered per capsule then × 0.55. (Ch. 2, 7)
- **Directional lines** — Letting each tail corridor follow its own walls. *Precise:* D-SL2, rate = air + s′·room + (1 − s′)·κ·own faces, s′ ≥ 0.5. (Ch. 6)
- **Double slope** — A decay that sounds like two fades one after the other. *Precise:* seen with raw directional rates (s′ = 0.15) and in the SL4 untreated-plaster finding. (Ch. 6)

## E

- **Early reflections / early field** — The first distinct echoes. *Precise:* the 32 image taps (`LIVE_32`) in Play; the full image set in Render. (Ch. 2, 5)
- **EBU Tech 3276** — A broadcast standard for control-room decay. *Precise:* D-SL9 preset, Tm = 0.25·(V/100)^(1/3) s with per-band tolerances. (Ch. 6)
- **EDT** — Early decay time: how fast the first part of the fade goes. *(general acoustics: from 0 to −10 dB, scaled to 60 dB)* (Ch. 6)
- **Eyring** — The classic formula linking room size and absorption to reverb time. *Precise:* T = 0.161·V / (−S·ln(1 − ᾱ) + 4mV). (Ch. 6)

## F

- **Face EQ** — A per-wall tone control. *Precise:* low shelf, peak, high shelf; in Surfaces only cuts count in the loop. (Ch. 6)
- **FDN (feedback delay network)** — The recirculating "corridors" that make the tail. *Precise:* 32 delay lines (per L/C/R bus), unscaled ±1 Hadamard H·D, one-sample feedback, per-line allpass and loss. (Ch. 2, 5)
- **FDN-first** — The default mix: tail up, direct and early down. *Precise:* K4. (Ch. 2)
- **Figure-8 (bidirectional)** — A mic that hears front and back but not the sides. (Ch. 7)
- **FIR** — A filter made from a short fingerprint of samples. *Precise:* finite impulse response. (Ch. 7)
- **Fitter** — The routine that sets each line's tone control. *Precise:* bounded least squares, 56 log-spaced points, at most 600 evaluations, stability penalty; convergence not checked (OPEN). (Ch. 6)

## G–H

- **Gate** — A pass/fail condition a session must meet. *Precise:* with a stop rule: ship the safe variant or revert, never half-merge. (Ch. 4, 8)
- **Golden** — A stored reference recording that must not change by accident. *Precise:* four Play goldens + `render_std_unlocked_byp.f32`. (Ch. 8)
- **GOLDEN_META** — The file that records golden fingerprints and why they changed. (Ch. 8)
- **Guard** — A safety check on each line filter. *Precise:* reject if loop gain implies T > 3× the longest target or octave error > 50 %; refit with S1, else broadband. (Ch. 6)
- **H·D (column signs)** — The shuffle pattern with some columns flipped. *Precise:* Hadamard times a fixed mirror-safe sign diagonal (S4b); `reaktor_parity` keeps plain H. (Ch. 5)
- **Hadamard matrix** — A fixed pattern of +1 and −1 that blends every line into every other. *Precise:* unscaled ±1 Sylvester construction (ASSUMED), applied by `fwht32`. (Ch. 5)
- **HANDOVER** — The project's read-first notes file, kept with the code. (Ch. 1)
- **Harness** — The 19 automatic engine checks (`run_all.py`, t01–t19). (Ch. 8)
- **Helmholtz panel** — A perforated board over a cavity that soaks up one bass band, like blowing over a bottle. *Precise:* f0 = (c/2π)·√(ε/(t′·d)); Q 3 ASSUMED (physics suggests 1–2, open). (Ch. 6)
- **H-1** — The locked mic-height compromise. *Precise:* direct, early and inject follow capsule heights; FDN lines stay at stand height (tail change ≤ 0.42 dB). (Ch. 7)
- **HRTF** — How your head and ears filter sound from each direction. *Precise:* head-related transfer function; SADIE II data in this program. (Ch. 7)

## I–L

- **IC (interaural coherence)** — How similar the two ears' signals are. *Precise:* the binaural tail is matched to the head's IC. (Ch. 7)
- **Image source** — A mirror copy of the source behind a wall, standing for one echo. *Precise:* 2011 mirror macros, full-R; delay d/340 s, level 1/r². (Ch. 5)
- **Impulse response (IR)** — A room's echo fingerprint: what you'd record after one click. (Ch. 2, 3)
- **Inject** — Where the echoes enter the tail. *Precise:* all 32 images inject into the FDN; filters here change tone and level, not decay. (Ch. 2, 5)
- **Jitter (Δd)** — Tiny random changes in echo path length so the pattern sounds less rigid. *Precise:* seeded, mirror-invariant since D-MIX-J; separate from Dffs. (Ch. 5)
- **K1 / YAW_X_SIGN** — The one rule for left and right. *Precise:* `YAW_X_SIGN = +1` in Python and JS; source left ⇒ L louder and earlier. (Ch. 7)
- **Least squares** — Making the total of squared errors as small as possible. (Ch. 6)
- **LFO** — A slow wobble generator. *Precise:* Movement uses sines at 0.7 Hz × 0.6–1.4 per line. (Ch. 5)
- **lg / line_t60** — Each corridor's loss per trip. *Precise:* lg = 10^(−3·dᵢ/(sr·T)), i.e. −60·τᵢ/T dB per pass. (Ch. 5)
- **Limiter** — A safety stop against clipping. *Precise:* one shared soft limiter in Play and Render (S-AUDIT). (Ch. 2)
- **LIVE_32** — The fixed list of 32 images. *Precise:* orders 0–4 as 1/6/11/10/4; `engine/early_field.py`. (Ch. 5)
- **LOCKED** — Approved by Idle, not yet in the program. (all)
- **Loop gain (g)** — How much the mixer passes back each trip. *Precise:* g = Gain/N (2011) or 1/√N (Decay lock). (Ch. 5)
- **LTI** — A process that treats every moment the same and just adds signals. *Precise:* linear time-invariant; any LTI chain can be replaced by one fixed filter, so it can live in an IR. (Ch. 2, 3)

## M

- **Mäkivirta target** — The decay shape studios aim for. *Precise:* flat at T_mid (500 Hz–2 kHz mean), +0.2 s on log f from 300 Hz down to 50 Hz, air alone above 2 kHz; the auto-treat yardstick. (Ch. 6)
- **Material card** — A wall's absorption per octave. *Precise:* 12 real materials with role bans plus porous presets; the default card is not a real material (ASSUMED plaster-ish). (Ch. 6)
- **Median** — The middle value of a sorted list; used for CPU gates. (Ch. 3, 8)
- **Membrane panel** — A board over an air gap that vibrates like a drum skin and soaks up one bass band. *Precise:* f0 ≈ 60/√(m·d), ≈ 50/√(m·d) with wool; Q 2, αmax 0.6 ASSUMED. (Ch. 6)
- **Mic tap** — Where a mic listens. *Precise:* off the diffuser output, in parallel with feedback; never written back. (Ch. 2, 7)
- **Minimum-phase** — A filter built to add as little delay as possible. (Ch. 7)
- **Mirror (two sources)** — Putting the second source at the mirror spot across the room. *Precise:* B at (W − sx, sy, sz); `test_mirror_exact` ≤ −120 dB. (Ch. 2, 8)
- **Mirror / Linked / Split** — How the right mic follows the left. *Precise:* D-UI37, LOCKED for T7/T8. (Ch. 7)
- **Movement** — A gentle wobble of corridor lengths that stops metallic rings. *Precise:* LOCKED (T11): 16 of 32 lines, 0.10–0.15 ms peak, allpass reads, default 0; Render runs the loop when > 0. (Ch. 5)
- **MS** — Mid plus Side: a forward mic and a sideways figure-8 decoded to stereo. *Precise:* side route s = (+a, −a); D18/D19 fixes LOCKED for T3b. (Ch. 7)

## N–O

- **Natural (air) decay** — Treble dies a bit faster, as in real air. *Precise:* LOCKED (SL7a, ST-1/ST-2): per-line air loss for the line's delay, per-axis cut loss folded in. (Ch. 2)
- **Null / null test** — Flip one version upside down, add it to the other, measure what's left. *Precise:* reported in dB; t18 −71.8 dB. (Ch. 3, 8)
- **Nyquist** — The highest pitch a sample rate can carry: half the rate. *(general)* (Ch. 6)
- **Octave / third-octave** — A band whose top is twice its bottom / a third of that width. *(general acoustics)* (Ch. 6)
- **Omni** — A mic that hears all directions equally. (Ch. 7)
- **OPEN** — Undecided or unknown. (all)
- **ORTF** — Two cardioids slightly apart and angled out; the default setup. *Precise:* ±55° outward; today includes C at 0 dB; C off by default from T4b (D20). (Ch. 7)

## P

- **Pan law** — How level is shared as you pan. *Precise:* the 2011 linear law, pan = (a(1 − t), a·t). (Ch. 7)
- **Parity** — Two versions sounding identical. *Precise:* Play vs Render, or today vs 2011 (`reaktor_parity`). (Ch. 3, 8)
- **Peakiness** — How spiky the fine detail of the tail's spectrum is; a measure of metallic ringing. *Precise:* std of fine-bin dB over 0.3–1.3 s; engine 7.20 dB vs noise 5.53. (Ch. 5)
- **Peaking cut (per-axis)** — A small fixed dip inside the loop. *Precise:* one RBJ cut per line at the first axial mode of X, Y or Z (line i % 3), −1.5 dB per pass, Q 1.5. (Ch. 5)
- **Phase (invert)** — Flipping a signal upside down. *Precise:* `phase_l/c/r` = ±1. (Ch. 7)
- **Play** — The live engine in the browser. *Precise:* `live_stereo` C compiled to wasm in an AudioWorklet. (Ch. 2, 3)
- **PLANNED** — An idea or later design, not decided in detail. (all)
- **Polar pattern** — Which directions a mic hears. (Ch. 7)
- **Porous absorber** — A soft panel (mineral wool, foam) that soaks up mids and treble. *Precise:* library presets 1″+1″ gap, 2″, 2″+2″, 4″+4″. (Ch. 6)
- **Prebuild** — Code pre-written and tested on the box, ready for a Build session. (Ch. 6, 8)

## Q–R

- **Q** — How narrow a filter or resonance is; higher = narrower. (Ch. 5, 6)
- **reaktor_parity ("Hall")** — The switch that recreates the 2011 behaviour. *Precise:* g = Gain/N, plain H, `LIVE_32_REAKTOR`; Smooth and Movement forced off. (Ch. 1, 5)
- **Reflection order** — How many bounces an echo has made. (Ch. 5)
- **Render** — The offline engine that writes a file. *Precise:* `render_pipeline.py`, IR + FFT convolution; 24-bit WAV. (Ch. 2, 3)
- **Room result** — A planned panel showing predicted vs rendered decay per band. *Precise:* DESIGNED (SL1), mock-up only. (Ch. 6)
- **Room shell** — An allowance for doors, windows and stud walls. *Precise:* D-SL6: 90 Hz membrane, Q 1, 30 % of each wall, αmax 0.35 (ASSUMED values). (Ch. 6)
- **Route** — Where a mic strip goes. *Precise:* centre, both, l, r, s, pan. (Ch. 7)

## S

- **S1P2** — The three-stage line filter. *Precise:* one biquad packing a first-order low and high shelf, plus two peaks (D-SL7). (Ch. 6)
- **Sample / sample rate** — One measurement of the waveform / how many per second (44,100 or 48,000). (Ch. 3)
- **Scattering** — How much a surface spreads sound in all directions instead of mirroring it. *Precise:* sets the Eyring/Arau blend and s′ = max(mean scattering, 0.5). (Ch. 6)
- **Schroeder curve** — A smoothed decay curve used to measure reverb time. *(general acoustics: backward integration of the IR)* (Ch. 6)
- **SHA1** — A 40-character fingerprint of a file. (Ch. 8)
- **Shared tail** — One tail for all mics in Play to save CPU. *Precise:* off by default; 24.7 % saving. (Ch. 2)
- **Shelf filter** — A tone control that tilts everything above or below a pitch. (Ch. 6)
- **Smooth** — A cap on the smearing filters to reduce metallic ringing. *Precise:* LOCKED (T4): |Dffs| ≤ 0.7, default ON, decay-corrected; off = bit-exact. (Ch. 5)
- **Solo / Mute (face)** — Hear only, or drop, the echoes touching one wall. *Precise:* early field only; the inject is unaffected. (Ch. 5)
- **SOS** — Second-order sections: a chain of small filter stages. (Ch. 7)
- **Source** — The instrument or voice in the room. *Precise:* position, height, yaw, radiation pattern. (Ch. 2)
- **Structure mining** — Reading Idle's 2011 Reaktor patch screen by screen to recover the exact design. (Ch. 1)
- **Surfaces mode** — Walls and panels decide how long each pitch rings. *Precise:* LOCKED (D-SL1–9), DESIGNED, not merged; per-line S1P2 filters inside the loop. (Ch. 2, 6)

## T–Z

- **T20 / T30 / T60** — Ways of stating decay time. *Precise:* T60 = time for a 60 dB fall; T20 and T30 estimate it from the −5 to −25 dB and −5 to −35 dB parts of the Schroeder curve. (Ch. 5, 6, 8)
- **Tail** — The smooth fading wash after the early echoes; made by the FDN. (Ch. 2)
- **Trim** — Input level on a strip. (Ch. 7)
- **Tuned panel** — A panel that absorbs one narrow bass band (membrane or Helmholtz). (Ch. 6)
- **U87 Ai / SM57** — Two real microphones: a Neumann studio condenser and a Shure dynamic. *Precise:* SM57 × 3 default today; U87 Ai Cardioid planned default in SL7b (D-UI30/38). (Ch. 7)
- **VERIFIED** — Read in a cited file or measured. (all)
- **Voice** — One of 32 parallel copies of the processing, one per image. (Ch. 5)
- **wasm (WebAssembly)** — Compiled code that runs fast inside a browser. (Ch. 2, 3)
- **Width** — How wide the side signal is spread in MS. *Precise:* replaces trim on route s. (Ch. 7)
- **WORKLET_VER** — The version number of the live engine (51 in build 51). (Ch. 1)
- **XFAIL** — "Expected to fail": a test waiting for a feature that is not built yet. (Ch. 8)
- **XY** — Two directional mics at one point, angled apart. *Precise:* `xy_90`, `xy_120`. (Ch. 7)
