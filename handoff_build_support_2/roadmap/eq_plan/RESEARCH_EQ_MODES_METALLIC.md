# Research: room tone and modes, and metallic ringing

For 2011 Room Reverb (image-source early reflections, then a 32-line Hadamard FDN with Dffs allpass diffusers and an S5 SURF per-line feed-forward cascade on the inject).
Written 2026-10-04, around 07:00 BST, by the research worker. This is research only, with no engine changes. EQ_PLAN.md (another worker) is the plan. This file is the evidence behind it.

How to read the tags: **[read]** means I opened the source and read the relevant part. **[abstract]** means I only saw the abstract, the publisher page, or a search summary. **[unverified]** means I could not confirm the URL or the detail, so treat it as a lead. Every URL below came from a live search or fetch on 2026-10-04. None are guessed.

---

## 0. Six things that change the plan

1. **A filter on the FDN inject cannot build up over passes.** The FDN is linear and time-invariant, so a filter placed before it (like S5's SURF cascade, which `live_stereo.c` states "is outside the loop") does exactly what the same filter after the FDN would do. It cuts the whole tail by the same dB at every moment. Idle's "shallow cut that gets deeper with every pass" only happens in two places:
   - **Inside the loop**, applied on every trip round a line. The engine already has this: three in-loop peaking biquads, one per axis (`i % 3`), normalised to unity at DC (`read_peaked`, `pb2 = 1 + a1 + a2 − b0 − b1`). That looks like the 2011 "resonator" idea.
   - **In the image-source wall filters**, where an order-k image picks up the wall cut k times.
2. **Make in-loop cuts proportional to delay length** (Jot and Chaigne's "homogeneous" loss). If each line's cut in dB scales with its own delay, every mode near that frequency decays at the same rate. If all lines share one biquad, as the per-axis peaking does now, a short line loses more per second than a long one. Schlecht and Habets show this makes neighbouring modes decay at very different rates (§1.6), and Heldmann and Schlecht say homogeneous decay is what "prevents single modes from ringing past the overall decay" (§2.3).
3. **The per-pass cut is small, and it can be calculated.** Δ dB per pass = 60 · d · (1/T_target − 1/T_now), with d the line delay in seconds. For a peak ringing at 2.4 s that should match 1.8 s: 0.17 dB per pass on a 20 ms line, 0.33 dB on a 40 ms line. Over time that adds up to only 0.8 dB at 100 ms, but 4.2 dB at 0.5 s and 8.3 dB at 1 s. That is exactly the "transients through, long-term cut" behaviour Idle described (§1.3).
4. **The FDN's modes are not the box's modes.** In an FDN the mode frequencies are spread almost evenly, whereas a real room's mode density grows with f². Most of the energy sits in a minority of modes (§1.6). So in Idle's engine the "box tone" really lives in the image-source early part, and any tones in the tail are FDN artefacts. That means detection has to measure the engine's output, not just predict modes from the dimensions.
5. **Metallic ringing is a separate problem with a separate fix.** Literature starting points for modulation (all §2):
   - **Delay modulation:** about 6 samples at 44.1 kHz (0.14 ms) peak depth, 0.5–2 Hz, sinusoids with phases offset 45–90° between lines, first-order allpass interpolation, and only some of the lines modulated (Frenette 2000, measured by listening).
   - **Dattorro's figure:** about 8 samples at 29.8 kHz (0.27 ms) at about 1 Hz.
   - **Matrix modulation:** a lower-pitch-artefact option for a Hadamard, rotating 2–15 % of π at 0.1–1 Hz (Coppola, DAFx26).
6. **The engine's FDN read uses linear interpolation** (`read_lane`). With a fixed fraction it is a fixed lowpass per pass: −2.0 dB at 10 kHz per pass when the fraction is 0.5 at 48 kHz. Once the delay is modulated, that loss changes over time, so HF would "breathe". Frenette found linear interpolation audibly dull in a modulated FDN, which is why he used allpass interpolation. **Any modulation item must change the interpolator on the modulated lines.** Separately, it's worth checking whether today's static fractional delays already add an uneven HF loss per line. I have not measured that.

---

## TOPIC 1 — Room tone, modes, detection, correction

### 1.1 How box rooms build up tone

- **Room-mode formula and the Schroeder frequency.** Rigid rectangular-room modes are f(l,m,n) = (c/2)·√((l/Lx)² + (m/Ly)² + (n/Lz)²). They are classed as axial, tangential or oblique, and axial modes carry the most energy. Below f_S ≈ 2000·√(T/V) the modes are separate. Above it they overlap and the room is better treated statistically.
  Source: https://en.wikipedia.org/wiki/Room_modes **[read]** (cites Kuttruff, *Room Acoustics*, and Schroeder 1962, JASA 34(12)). The factor 2000 corresponds to about 3 modal overlaps, and Schroeder's original stricter value was 4000: Skålevik, https://www.akutek.info/Papers/MS_Schroeder_Revisited.pdf **[abstract]**.
  - *What it means for Idle:* below f_S, a box can genuinely have audible tones, so predicted modes are a valid starting candidate list for the early part. Worked examples (c = 343 m/s):

    | Room (m) | T (s) | V (m³) | f_S | Mean free path | 1st axial modes (Hz) |
    |---|---|---|---|---|---|
    | 5 × 4 × 3 | 0.8 | 60 | ≈ 231 Hz | 2.55 m = 7.4 ms | 34.3, 42.9, 57.2 |
    | 10 × 8 × 5 | 1.8 | 400 | ≈ 134 Hz | 4.71 m = 13.7 ms | 17.1, 21.4, 34.3 |
    | 5.7 × 3.42 × 9.7 (if "57 × 34.2 × 97" is in dm) | 1.8 | 189 | ≈ 195 Hz | 3.50 m = 10.2 ms | 30.1, 50.1, 17.7 |

    Mean free path = 4V/S. That is the average time between wall hits, which sets how often an image-source wall filter is applied.

- **The image-source method in a rigid box is the time-domain form of the modal sum.** Allen and Berkley (1979), "Image method for efficiently simulating small-room acoustics," JASA 65(4):943–950: https://pubs.aip.org/asa/jasa/article/65/4/943/765693/Image-method-for-efficiently-simulating-small-room **[abstract]**.
  - *What it means for Idle:* the early bus, with its box geometry, carries the box's modal tone, but only for as long as the image set runs. The FDN tail does not inherit it.

- **Real rooms are slightly time-varying.** Small changes in the speed of sound, from temperature and air movement, decorrelate repeated RIRs, increasingly later in the response and at high frequencies. Prawda, Schlecht and Välimäki, "Time Variance in Measured Room Impulse Responses," Forum Acusticum 2023: https://aaltodoc.aalto.fi/items/358dddba-a8e0-44cf-bbaa-71e84dd2fdab **[abstract]**.
  - *What it means for Idle:* this is the physical case for a small amount of modulation (Topic 2), and the reason it should stay tiny.

### 1.2 Detecting resonances automatically

1. **Mode identification by decay fitting** (Mäkivirta, Antsalo, Karjalainen and Välimäki). They take an STFT of the IR and, for every bin, fit an "exponential decay plus noise floor" model by nonlinear least squares. A candidate is a bin whose level is above the 500 Hz–2 kHz average and whose decay is slow. They refine the frequency by fitting a parabola to the three bins around the peak, and turn T60 into a pole radius with r = 10^(−3 / (T60·fs)). They reject candidates with too little SNR or no decay at all, because those are hum or noise, not modes. A 5 % error in pole radius or angle "greatly reduces control."
   - Conference version (AES 111, 2001): https://assets.ctfassets.net/4zjnzn055a4v/1PmYuXIBmuySLxSGG1iViz/bd768fcbeb5a5b2a4655793186a1973d/Low-Frequency_Modal_Equalization_Of_Loudspeaker-Room_Responses.pdf **[read]**
   - Journal version: "Modal Equalization of Loudspeaker-Room Responses at Low Frequencies," JAES 51(5):324–343, 2003: https://research.aalto.fi/en/publications/modal-equalization-of-loudspeaker-room-responses-at-low-frequenci/ **[abstract]**
   - *What it means for Idle:* this is the right detector for the Room colour analyser: per-bin EDR, then a decay-plus-noise fit, then flag bins whose T60 is above the local median.
2. **Frequency-zooming ARMA** resolves closely spaced modes and dense clusters. Karjalainen, Esquef, Antsalo, Mäkivirta and Välimäki, JAES 50(12):1012–1029, 2002: https://research.aalto.fi/en/publications/frequency-zooming-arma-modeling-of-resonant-and-reverberant-syste/ **[abstract]**, PDF https://assets.ctfassets.net/4zjnzn055a4v/5cl6UREWpVkLlTB7bnY5cZ/58ed6a3243a261297d8d91ac267e357a/Frequency-Zooming_ARMA_Modeling_of_Resonant_and_Reverberant_Systems.pdf **[not read]**.
   - *What it means for Idle:* use it only as a second pass on a flagged cluster below about 300 Hz. It's overkill for the whole band.
3. **Comparison of the two modal-EQ design methods** (the "AMK" decay-fit and the ARMA pole-zero fit), with a small listening test that found a "possible marginal improvement" over plain magnitude EQ. Antsalo et al., "Comparison of Modal Equalizer Design Methods": https://assets.ctfassets.net/4zjnzn055a4v/7qJhV0iWZveIUTXiqL1kWA/422a1777445a1ebbcca6e2e1a1f242c8/Comparison_of_Modal_Equalizer_Design_Methods.pdf **[abstract]**.
   - *What it means for Idle:* the iterative method fits his request well: fix the longest-ringing mode first, then repeat until every mode is within its target.
4. **Exact modal decomposition of an FDN** gives every pole (frequency and decay) and residue (energy). It uses an Ehrlich–Aberth iteration on the matrix polynomial, works up to about 10⁶ poles, and also handles attenuation filters in the delay lines.
   - Schlecht and Habets, "Modal Decomposition of Feedback Delay Networks," IEEE Trans. Signal Process. 67(20):5340–5351, 2019: https://ar5iv.labs.arxiv.org/html/1901.08865 **[read]**; sound examples at https://www.audiolabs-erlangen.de/resources/2018-IEEE-Modal
   - MATLAB code in FDNTB: https://github.com/SebastianJiroSchlecht/fdnToolbox **[abstract]**
   - *What it means for Idle:* system order = sum of the 32 delay lengths, a few tens of thousands of poles, which is fine offline. It's the most precise way to find the FDN's own ringing frequencies. It doesn't cover the diffuser and filter details exactly unless they're modelled as polynomial or filter matrices.
5. **The FDN pole bound with attenuation filters**: each pole radius lies between min and max over lines of α_i(e^{jω})^{1/m_i}. Same paper, eq. 35 **[read]**.
   - *What it means for Idle:* this gives a closed-form check of what an in-loop cut does to every mode near ω, with no rendering needed.

### 1.3 Correction: in the loop or per reflection, versus post EQ

- **Mäkivirta "Type I" modal EQ** puts a pole-zero filter in series with the source. Its zeros cancel the room's mode poles, and new poles at the same frequency with a smaller radius replace them. That shortens the decay, not just the level. The magnitude response is a notch. After modal EQ the peak was still about 15 dB above baseline in their 1-mode example (it was about 30 dB before), and the decay matched the target T60. **[read]**
  - *What it means for Idle:* this is the literature closest to his intuition, but note how it works. A pre-filter can shorten a decay only by cancelling the exact pole. That's practical for a few isolated low-frequency room modes in a real room, not for the thousands of closely spaced FDN poles. In this engine the faithful equivalent is the cut inside the loop.
- **Target decay curve** (same paper): use the mean T60 at 500 Hz–2 kHz, and let the target rise linearly on a log-frequency scale by 0.2 s from 300 Hz down to 50 Hz. Broadcast recommendations allow up to +0.3 s by 63 Hz and at most a 25 % rise between adjacent third-octaves. **[read]**
  - *What it means for Idle:* this is a ready-made default "auto" target for the resonator detector, with a slight low-end bloom allowed instead of a dead flat T60.
- **Jot and Chaigne 1991**: delay-proportional absorption filters inside the loop (homogeneous decay), plus a separate "tonal correction" filter E(z) outside the loop, which equalises mode energy independently of T60. AES 90, preprint 3030: https://aes2.org/publications/elibrary-page/?id=5663 **[abstract]**; Smith's summary: https://ccrma.stanford.edu/~jos/pasp/History_FDNs_Artificial_Reverberation.html **[read]**
  - *What it means for Idle:* this is exactly the split to adopt. In-loop proportional cuts handle "this frequency rings too long". The S5 SURF or an outside-loop EQ handles "this frequency is too loud everywhere". They are two different knobs.
- **Accurate reverberation-time control.** Errors in the attenuation filter propagate nonlinearly into T60, and they recommend a constrained nonlinear least-squares fit on T60 itself, not on the magnitude response. Schlecht and Habets, DAFx-17: http://www.dafx17.eca.ed.ac.uk/papers/DAFx17_paper_11.pdf **[abstract]**.
  - Note: this paper is by Schlecht and Habets, not "Välimäki and Liski". Liski and Välimäki's "The Quest for the Best Graphic Equalizer" is also at DAFx-17 (program: http://www.dafx17.eca.ed.ac.uk/Program.html). Their "accurate cascade graphic equalizer" IEEE SPL paper is **[unverified]**, because I did not find its URL.
- **Improved T60 control**: an octave cascade GEQ plus a high shelf in each line, using a weighting that accounts for error propagation. It notes that "a 5 % error in T60 can be audible." Prawda, Schlecht and Välimäki, DAFx-19: https://www.dafx.de/paper-archive/2019/DAFx2019_paper_46.pdf **[abstract]**
  - Follow-up: "Two-Stage Attenuation Filter" (a low-order pre-filter plus a third-octave GEQ), IEEE SPL 31:391–395, 2024: https://research.aalto.fi/en/publications/two-stage-attenuation-filter-for-artificial-reverberation/ , code https://github.com/KPrawda/Two_stage_filter **[abstract]**
  - *What it means for Idle:* use about 5 % T60 as the JND. Only treat a peak whose T60 exceeds the local target by more than roughly 5–10 %.
- **Proportional parametric equalisers**: first- and second-order IIR sections whose dB response scales with one gain parameter. These are designed for exactly the "cut ∝ delay length" job inside reverb loops. Jot, AES 139 (2015), paper 9358. Author site: https://sites.google.com/site/jmmjot **[abstract; AES e-library URL unverified]**
  - *What it means for Idle:* each line i gets the same peaking shape with gain_dB_i = m_i · γ_dB. The engine's RBJ peaking can approximate this. Proportionality is exact only if the dB response scales cleanly with gain, which is true for Regalia–Mitra-style sections and only approximately true for a plain RBJ peak.
- **Per-reflection, material-like filters.** Scattering Delay Networks put wall-node filters with material absorption at every reflection, so an order-k path gets k filters. De Sena, Hacıhabiboğlu, Cvetković and Smith, IEEE/ACM TASLP 23(9):1478–1492, 2015: https://arxiv.org/abs/1502.05751 **[abstract]**
  - *What it means for Idle:* a Helmholtz or membrane "absorber" on a face is a narrow dip in that face's reflection filter. Per bounce the cut is −10·log10(1 − α(f)) dB, so α = 0.1 gives 0.46 dB and α = 0.2 gives 0.97 dB. Images that hit that face more often get more of it, which is physically right and builds up the same way. The α values here are illustrative, not sourced.
- **Modal reverb** synthesises the late field as a parallel bank of resonant mode filters, each with its own frequency, damping and gain, so per-mode T60 is directly editable. Abel, Coffin and Spratt, AES 137 (2014), paper 9208: https://secure.aes.org/forum/pubs/conventions/?elib=17531 **[abstract]**. Heldmann and Schlecht cite it as EUSIPCO 2014, so the venue has a small discrepancy.
  - *What it means for Idle:* a possible future "LF modal layer" below f_S that would give the tail a true box tone. It's a separate, larger item, not part of the resonator cuts.

**Worked per-pass depths.** Δ dB per pass = 60·d·(1/T_target − 1/T_now). The cumulative extra cut after t seconds is 60·t·(1/T_target − 1/T_now), whatever the line length.

| T_now → T_target | d = 10 ms | 20 ms | 40 ms | 80 ms | Extra cut at 0.1 s / 0.5 s / 1 s |
|---|---|---|---|---|---|
| 2.0 → 1.8 s | 0.03 dB | 0.07 | 0.13 | 0.27 | 0.3 / 1.7 / 3.3 dB |
| 2.4 → 1.8 s | 0.08 | 0.17 | 0.33 | 0.67 | 0.8 / 4.2 / 8.3 dB |
| 3.0 → 1.8 s | 0.13 | 0.27 | 0.53 | 1.07 | 1.3 / 6.7 / 13.3 dB |
| 1.0 → 0.8 s | 0.15 | 0.30 | 0.60 | 1.20 | 1.5 / 7.5 / 15.0 dB |

*Recommendation:* the peaking gain at the centre frequency should be about −0.05 to −1 dB per pass, set by line delay. Only the bandwidth (Q) is shared across lines. Keep the cut ≤ 0 dB everywhere and normalise to unity at DC, as the engine already does, so the loop stays passive.

### 1.4 Audibility: what is worth cutting

- **Modal decay detection thresholds** (Fazenda, Stephenson and Goldberg, JASA 137(3):1088–1098, 2015): https://eprints.hud.ac.uk/id/eprint/24317/ **[abstract; numbers from the search summary, PDF not opened]**. For unmasked test tones, the threshold falls from about 0.9 s at 32 Hz to about 0.17 s at 200 Hz, with a knee near 63 Hz. With music masking it is about 0.51 s at 63 Hz and 0.12 s at 250 Hz.
  - *What it means for Idle:* below about 63 Hz, long modal decays are hard to hear, so the detector can be lenient there.
- **Resonance audibility** (Toole and Olive 1988; Olive et al., JAES 45(3), 1997, as summarised in the Mäkivirta paper **[read]**): detectability drops about 3 dB for each doubling of Q. Low-Q resonances are more audible with continuous broadband signals, high-Q ones with transient signals. At high Q, notches are much less audible than peaks.
  - *What it means for Idle:* (a) broad, shallow cuts matter more than narrow ones; (b) a narrow cut slightly off-frequency is fairly harmless, so the detector's errors fail gracefully; (c) check the cuts with both pad and percussive material.

### 1.5 How this maps to Idle's controls

- **Detect** with the engine's own render, using fine-band EDR and a decay-plus-noise fit per bin (§1.2-1). List peaks where T60 exceeds the Mäkivirta target by more than 5–10 %. Rank them by Fazenda audibility (frequency and decay) and by level above the neighbouring median.
- **Predict** box modes below f_S only as labels: "this early peak is the 1-0-0 axial mode of the 9.7 m dimension." Don't use them as the cut list for the FDN.
- **Correct**:
  - The **ring-time part** goes in the loop, proportional to delay, with depth from the formula above (the automatic starting point), plus Idle's amount knob and bypass.
  - The **level part** goes on the inject (SURF) or the output.
  - The **early part** goes into the face filters, as α-dips per bounce.

### 1.6 FDN modes are not room modes (why tones in the tail need measuring)

From the modal decomposition paper **[read]**:
- **Mode frequencies of random lossless FDNs are spread almost evenly.** Over 66 % of 2π/𝔑 intervals hold exactly one mode, versus 37 % for uniform random, "in stark contrast" to rooms, where mode density rises quadratically with frequency.
- **Residue magnitudes are roughly log-Rayleigh, so a few modes carry much of the energy.** "Audible modal density is considerably lower than theoretic modal density." This is offered as the explanation for "why some FDNs have an unpleasant metallic ringing despite a sufficiently high modal density."
- **Inhomogeneous attenuation**, meaning the same filter on every line instead of one proportional to delay, "the decay time of the neighboring modes are largely different."
- *What it means for Idle:* the per-axis peaking biquads that are shared across lines of different lengths are exactly that inhomogeneous case. Switch them to proportional.

---

## TOPIC 2 — Metallic ringing

### 2.1 Why FDNs sound metallic

- **Too few modes.** Schroeder and Logan suggest about 0.15 modes/Hz for T60 = 1 s, scaling with T60, so the total delay M ≥ 0.15·T60·fs. "Insufficient mode density can be heard as ringing tones or an uneven amplitude modulation." Smith, PASP: https://ccrma.stanford.edu/~jos/pasp/Mode_Density_Requirement.html and https://ccrma.stanford.edu/~jos/pasp/Choice_Delay_Lengths.html **[read]**
  - *What it means for Idle:* for T60 = 1.8 s at 48 kHz, M ≥ 12,960 samples, which is about 8.4 ms average per line over 32 lines. Default rooms probably clear this easily, but very small rooms or a short "Decay" with short lines may not. This is a cheap check to add to the analyser.
- **Uneven modal excitation**, even with enough modes and equal decay. A perceptual study (11 listeners, MUSHRA-style) found that coloration rises with the spread of the modal-excitation distribution. Among N = 8 FDNs, Hadamard and Householder were rated "certainly colored", random-orthogonal "fairly colored/colorless", and the homogeneous allpass FDN "rather colorless". With equal excitation, 1000 modes sounded "certainly colored" and about 10,000–20,000 sounded close to noise. Heldmann and Schlecht, "The Role of Modal Excitation in Colorless Reverberation," DAFx20in21: https://dafx2020.mdw.ac.at/proceedings/papers/DAFx20in21_paper_17.pdf **[read]**
  - *What it means for Idle:* a plain Hadamard is the most colour-prone of the dense matrices tested, though Idle's has 32 lines and in-loop allpass diffusers, which both help. The fix with no time-variance is to shape b, c, the delays and the diffusers for flat modal excitation, not to EQ.
- **Low early echo density and periodicity** (commensurate delays). The usual remedy is co-prime delays and diffusion. Abel and Huang's echo-density profile (fraction of samples outside ±1σ in a sliding window, divided by erfc(1/√2) ≈ 0.3173) is a level- and EQ-independent texture metric that correlates with perceived texture. AES 121 (2006), paper 6985: https://aes.org/publications/elibrary-page/?id=13819 **[abstract]**
- **Overview**: Välimäki, Parker, Savioja, Smith and Abel, "Fifty Years of Artificial Reverberation," IEEE TASLP 20(5):1421–1448, 2012: https://ieeexplore.ieee.org/document/6161610 **[abstract]**

### 2.2 Remedy A: delay-line modulation

- **Frenette (2000), master's thesis, Univ. of Miami** (supervised by Pirkle), "Reducing artificial reverberation requirements using time-variant FDNs." I read Chapter 5 on a Japanese-translation mirror, so the numbers are as translated: http://mcpu.s12.xrea.com/dsp/jf/chapter_5/chapter_5.html **[read]**; abstract http://mcpu.s12.xrea.com/dsp/jf/abstract.html
  - **Depth.** "8 samples or more" gave perceptible pitch change on sustained sax and piano. "4 samples" didn't break up the ringing. They chose **6 samples at 44.1 kHz (0.136 ms peak)**.
  - **Rate.** Below **0.5 Hz** gave almost no improvement. Above **2 Hz** was easily heard on some line and signal combinations. They used 2 Hz in the final design.
  - **Phase.** With all modulators in phase, pitch change was clearly audible even at moderate settings. With **45° or 90° phase offsets** between lines, it became hard to notice, even at 6 samples.
  - **Shape.** Sinusoids were preferred to filtered random, because random modulators sometimes all move the same way, which makes audible pitch shifts, or all go quiet, which makes the modulation less effective.
  - **Interpolation.** Linear and 2nd-order Lagrange have "too noticeable" HF roll-off. Lagrange needs 4th order or more to sound flat. A **first-order allpass** sounded about as good as 4th-order Lagrange at about 55 % of its cost.
  - **Coefficient update rate.** Every ≤ 25 samples was inaudible, every 50 added very slight noise, and every ≥ 75 was audible.
  - **Partial modulation.** 4 of 8 lines modulated, with 7k words of memory, matched or beat 12 unmodulated lines. In ABX tests 30–60 % of listeners could tell the two apart, and most preferred the modulated one on vocals and sax for a "smoother decay." One listener out of 20 heard slight pitch error.
- **Dattorro (1997), "Effect Design, Part 1," JAES 45(9):660–684.** Tank allpass taps are modulated with linear or, better, allpass interpolation. EXCURSION = 16 (the maximum excursion), and the footnote gives a **peak excursion of about 8 samples at about 29.8 kHz (about 0.27 ms) at about 1 Hz**. It "breaks up some pretty audible modes" on drums. "Without the modulation… enclosed by a picket fence." It also notes there is "no analogue… in a real room (unless the walls are moving)."
  - https://ccrma.stanford.edu/~dattorro/EffectDesignPart1.pdf **[read]**, AES https://aes.org/publications/elibrary-page/?id=10160
- **Griesinger (1991), "Improving Room Acoustics Through Time-Variant Synthetic Reverberation,"** AES 90, preprint 3014. Time-variant reverberators are used for stable, uncoloured enhancement (the Lexicon/LARES lineage). https://tile.loc.gov/storage-services/master/mbrs/recording_preservation/manuals/REPORT--Improving%20Room%20Acoustics%20Through%20Time-Variant%20Synthetic%20Reverb%20(AES,%201991)%20(Griesinger).pdf **[abstract; PDF not opened, so modulation parameters unverified]**
- **Practitioner view** (Costello, Valhalla DSP): heavy modulation in old units (EMT 250, Lexicon "chorus") masks periodic artefacts from small delay memory but "goes far beyond what can be heard in any real-world acoustic space." https://valhalladsp.com/2009/07/30/modulation-in-reverbs-reality-and-unreality/ **[read]**. ValhallaVintageVerb separates "random" modulation (to cut metallic ring) from "chorus" modulation: https://valhalladsp.com/2023/02/10/valhallavintageverb-the-modes/ **[abstract]**

**Pitch cost (my derivation, not from the sources).** Sinusoidal delay modulation with peak depth D seconds at rate f_m gives a peak frequency deviation of Δf/f = 2π·f_m·D per pass:

| Peak depth | 0.3 Hz | 0.5 Hz | 1 Hz | 2 Hz |
|---|---|---|---|---|
| 0.05 ms (2.4 samples at 48 kHz) | 0.16 cents | 0.27 | 0.54 | 1.09 |
| 0.10 ms (4.8 samples) | 0.33 | 0.54 | 1.09 | 2.17 |
| 0.14 ms (6.5 samples, Frenette) | 0.46 | 0.76 | 1.52 | 3.04 |
| 0.27 ms (13 samples, Dattorro) | 0.88 | 1.47 | 2.93 | 5.86 |

For the hearing threshold: at slow rates (around 2 Hz), FM detection relies on phase locking up to about 4 kHz (Moore and Sek, JASA 100(4):2320, 1996: http://dbao.leo-varnet.fr/wp-content/uploads/2020/10/Moore-Sek-1996-Journal-of-the-Acoustical-Society-of-America-id704.pdf **[abstract]**). A 2019 study at a 1 kHz carrier and 2 Hz rate (https://journals.sagepub.com/doi/10.1177/2331216519853963) reports a young normal-hearing FM threshold of "2.3". Search summaries disagree on whether that is Hz or %, and the page timed out, so it is **[unverified]**. If it is 2.3 Hz (0.23 %, about 4 cents), then Frenette's 6 samples at 2 Hz (about 3 cents per pass, phase-spread across lines) sits just below threshold, which matches his listening result. A sound in the tail passes through several modulated lines, so the deviations partly average out, but the frequency smear also builds up over time. That build-up is the intended spreading.

**Starting ranges for Idle (48 kHz, 32 lines). These are inferences from the above and need listening.**

| Parameter | Start | Range to audition | Basis |
|---|---|---|---|
| Peak depth | 0.10 ms (about 5 samples) | 0.05–0.15 ms (2.5–7 samples) | Frenette: 4 too little, 6 chosen, ≥ 8 audible (at 44.1 kHz) |
| Rate | 0.7 Hz centre, each line × 0.6–1.4, not commensurate | 0.3–1.5 Hz | Frenette: < 0.5 Hz weak, > 2 Hz audible; Dattorro about 1 Hz |
| Shape and phase | Sinusoid, phases spread evenly (≥ 45° apart) | — | Frenette |
| Lines modulated | 16 of 32 (alternate lengths) | 8–32 | Frenette: half gives most of the benefit |
| Interpolator (modulated lines) | 1st-order allpass, or cubic Lagrange or Hermite | — | Frenette, Dattorro; linear is audibly dull |
| Coefficient update | Every sample, or every ≤ 16–25 samples | — | Frenette: ≤ 25 inaudible |
| Off in | reaktor_parity, flat cards, mirror and null test modes | — | Determinism (§2.5) |

### 2.3 Remedy B: feedback-matrix modulation (fits a Hadamard best)

- **Schlecht and Habets, "Time-varying feedback matrices in FDNs…," JASA 138(3):1389–1398, 2015.** Continuous unitary modulation of the matrix stays stable, moves the poles, improves "liveliness," and reduces artefacts in a listening test.
  - https://pubs.aip.org/asa/jasa/article/138/3/1389/680169/Time-varying-feedback-matrices-in-feedback-delay **[abstract]**
  - Practical real-valued implementation, comparing orthogonal modulation with interpolating matrix entries: AES 138 (2015), paper 9255: https://secure.aes.org/forum/pubs/conventions/?elib=17679 **[abstract]**
  - Plugin: https://github.com/JanisHeldmann/TVFDN-plugin **[abstract]**
- **Coppola (Arturia), "Fast Parametric Matrices for Lossless FDNs," DAFx26 (Sept 2026):** https://dafx26.mit.edu/assets/papers/DAFx26_paper_04.pdf **[read]**
  - A Hadamard of order 2^M is the Kronecker product of M copies of Ref(π/4), and it can be computed in place in O(N log N), like the FWHT.
  - Modulating one kernel angle keeps the matrix exactly orthogonal. The pole histogram σ fell from 71.0 to 24.8 in their example.
  - Settings used: **2–15 % of π amplitude, 0.1–1.0 Hz**.
  - "Unlike delay line modulation, which introduces chorus-like artifacts, feedback matrix modulation… [introduces] less pitch variation." That's the author's claim, with no formal listening test.
  - *What it means for Idle:* FWHT32 already uses this butterfly structure. Replacing one of its 5 stages with a rotation by π/4 + ε·sin(2π f t) costs a few multiplies per sample, needs no interpolator, and has no HF loss. This is a strong candidate as the first anti-metallic option to try.

### 2.4 Remedies with no time-variance (they keep bit-exact Play/Render and mirror)

- **Delay-length choice:** co-prime, not close to commensurate, and total M ≥ 0.15·T60·fs (Smith, above).
- **Optimise b and c (input and output gains) for flat modal excitation.** This is linear least squares once the poles are known (Schlecht and Habets 2019, §IV-B3 **[read]**), or done with a differentiable FDN using spectral-flatness and temporal-density losses.
  - Dal Santo, Prawda, Schlecht and Välimäki, DAFx23: https://www.dafx.de/paper-archive/2023/DAFx23_paper_32.pdf , code https://github.com/gdalsanto/diff-fdn-colorless **[abstract]**
  - Follow-up, "Efficient optimization of FDNs for smooth reverberation" (2024): https://arxiv.org/abs/2402.11216 **[abstract]**
  - *What it means for Idle:* an offline optimisation of the 32 inject and output weights (and the Dffs coefficients) per room preset could lower ringing at zero CPU.
- **Velvet-noise input and output filters (VFDN):** a 16-line VFDN matches a 32-line FDN's echo density with 35–52 % fewer operations. Fagerström, Alary, Schlecht and Välimäki, DAFx2020: https://dafx2020.mdw.ac.at/proceedings/papers/DAFx2020_paper_23.pdf **[abstract]**. Dark velvet noise for frequency-dependent decay, DAFx 2022: https://www.dafx.de/paper-archive/2022/papers/DAFx20in22_paper_31.pdf **[abstract]**
- **Scattering FDN, or a filter feedback matrix** (including the cheap "velvet" matrix) for a dense IR. Schlecht and Habets, IEEE/ACM TASLP 28:1915–1924, 2020: https://arxiv.org/pdf/1912.08888v2.pdf **[abstract]**
  - *What it means for Idle:* this is the "scatter" phase already on the roadmap (SCATTER blob section 4). It's the principled no-modulation fix for density.
- **Allpass or homogeneous FDN** for colourless design: Heldmann and Schlecht (above) **[read]**.

### 2.5 Trade-offs and how they affect Idle's test regime

- **Chorus and pitch.** This is the main risk on sustained sources such as guitar, sax and piano. Keep depth and rate in the table above, spread the phases, and audition sustained notes, not just clicks.
- **Interpolation HF loss.** It applies on every pass, so it compounds. The engine's linear `read_lane` gives −1.4 dB (fraction 0.25) to −2.0 dB (fraction 0.5) at 10 kHz per pass at 48 kHz. Under modulation that loss changes over time. Use allpass or cubic interpolation on modulated lines. Note that a first-order allpass is itself an IIR filter, so it produces a transient when the coefficient changes (Frenette found this acceptable).
- **Determinism.** Modulation can be fully deterministic: seeded phases, LFO phase indexed by absolute sample, the same code in Play and Render. The existing gates still change:
  - **Null tests against today's goldens** will fail by design. They need new goldens plus statistical gates: third-octave tail match, EDR or T30 per band, echo density, and a spectral-flatness or "peakiness" figure.
  - **Peakiness** is the standard deviation of the fine-bin dB magnitude in a late window, compared against about 5.57 dB, the textbook value for a Rayleigh-distributed (diffuse) response (Schroeder; Kuttruff). This is a textbook figure that I did not fetch.
  - **Mirror test:** give LFO phases and rates to lines by a mirror-symmetric key, as with D-MIX-J, so a mirrored scene gets mirrored modulation.
  - **Play vs Render parity:** keep it sample-exact by starting both at the same t = 0 phase.
  - **reaktor_parity and flat cards:** modulation off.
- **Interaction with the resonator cuts.** Modulation spreads narrow peaks, so the room-tone detector should run on the modulated tail, and narrow in-loop cuts become less precise. Do metallic first (the structure), then room tone (the EQ), then re-detect.
- **Not physical in large amounts.** Real-room time variance exists but is tiny (Prawda et al. 2023; Costello). Keep modulation at the "just breaks the ring" level by default.

---

## 3. Decisions to bring to Idle

1. **Where the "build up over passes" cuts live.**
   - (a) In the loop, proportional to delay. This replaces or generalises the 3 shared per-axis peaking biquads. *Recommended.*
   - (b) Keep the shared per-axis biquads (inhomogeneous).
   - Both also get matching face α-dips for the early part.
2. **Auto target.** Mäkivirta curve (mid T60, +0.2 s from 300 down to 50 Hz) with a 5–10 % tolerance, *recommended*, or a flat T60.
3. **Which anti-metallic option to try first.**
   - (a) Hadamard kernel-angle modulation: cheap, no interpolation. *Recommended first.*
   - (b) Delay modulation at about 0.1 ms and 0.3–1.5 Hz, which needs the interpolator change.
   - (c) Static b/c and Dffs optimisation: bit-exact friendly.
4. **How the gates handle modulation:** new goldens plus statistical gates, with modulation off in parity, flat and mirror-test modes.

## 4. What I could not verify
- The full text of the Mäkivirta 2003 JAES paper. I read the 2001 AES conference version, which has the same method.
- The Jot 2015 AES paper's e-library URL.
- The URL for Liski and Välimäki's "accurate cascade GEQ" IEEE SPL paper.
- Griesinger 1991 modulation parameters.
- The units in the 2019 FM-threshold paper (Hz or %).
- Fazenda et al. numbers: these come from the search summary only.
- The 5.57 dB Rayleigh figure: textbook value, not fetched.
- Whether the engine's FDN delays are non-integer today, and so whether linear interpolation already adds uneven HF loss per line. This needs a quick measurement.
- Frenette was read through a translated mirror, not the original English PDF.
