# Surfaces extras: angle-dependent absorption, thickness/backing, FDN wall-tone

Written 27 Sep 2026 (BST). This is research only. Nothing in `software\` was changed.

Tags: **VERIFIED** = read in code or data on the box, or in the cited source. **MODEL** = computed by the prototypes here (not measurements). **ASSUMED** = my judgement or a typical parameter.

Prototypes (cheap, reproducible):
- `proto/angle_absorption.py`: Miki porous model, local vs extended reaction, Paris integral, panel resonances, and image-hit angles. Outputs `plots/angle_absorption_and_panels.png` and `proto/angle_absorption_results.json`.
- `proto/wall_tone.py`: Sabine, Eyring and Fitzroy per octave from the `surfaces_fitter` presets. Outputs `plots/wall_tone_t60.png` and `proto/wall_tone_results.json`.

Run both with `/workspace/scratch_er_dropout/venv/bin/python proto/<name>.py`.

## Summary

| Option | Verdict | One-line reason |
|---|---|---|
| **1. Angle-dependent absorption** (oblique vs random incidence, local/extended reaction) | **LATER** | It is only audible on porous absorbers at grazing angles: +1 to +4 dB louder reflection at 1–8 kHz beyond 60°. That covers about 20% of hits in a 6×3×8 room. Doing it honestly needs impedance data (flow resistivity, thickness) that the textbook presets do not have. |
| **2a. Porous thickness + air gap** | **YES, offline, as preset variants** | An air gap roughly doubles α at 125–250 Hz (MODEL). That is a clear LF tail difference, and it costs nothing at runtime (it is just another α table). Use measured tables where they exist, and tag model-derived ones MODELLED. |
| **2b. Membrane / panel resonances** (plasterboard on studs, wood panels) | **LATER** (mostly already covered) | Plasterboard f0 ≈ 60–75 Hz, which is below the 125 Hz band. The existing `gypsum_painted` and `plywood_panel` presets already carry the LF panel absorption in their 125 Hz value. A dedicated resonance stage only pays off for thin panels on deep gaps (f0 100–150 Hz), and it needs +1 biquad per hit. |
| **3. FDN wall-tone** (per-band tail T60 from the Surfaces materials) | **YES, decay-lock path only** | In decay lock, the dial sets the 1 kHz T60, and Eyring on the material α sets the shape across bands (MODEL: LF/1k ratio 1.8–3.1 in the example rooms). It costs 2 shelves per line (about 64 biquads per sample, **ASSUMED** ≈ 0.05–0.1 ms/block). The 2011 unlocked mode is left untouched. |

---

## 1. Angle-dependent absorption

**Physics (sources below).** A locally reacting surface with normal impedance Zs reflects at angle θ with R(θ) = (Zs cosθ − ρc)/(Zs cosθ + ρc) and α(θ) = 1 − |R|². Random-incidence ("statistical") absorption is the Paris integral, α_ran = ∫ α(θ) sin 2θ dθ over 0–90°. Porous layers can be modelled with Delany–Bazley (1970) or Miki (1990) from flow resistivity σ and thickness. An extended-reacting layer (sound also travels along the layer) changes α(θ), mostly at oblique angles. Jeong (2011) finds that the local-reaction assumption **always underestimates** random-incidence α for rigidly backed porous absorbers. It is within 10% only if the layer is thick (≥ 120 mm at σ = 5 kPa·s/m², with about 25 mm less needed per doubling of σ), or, with an air gap, if the material is at least about 40% of the cavity depth. Mondet et al. (2020) show how to go from absorption coefficients back to a complex impedance. The problem is non-unique and needs prior material information.

**What the prototype shows (MODEL, 50 mm porous, σ = 15 kPa·s/m² ASSUMED typical, rigid backing):**

| Octave (Hz) | 125 | 250 | 500 | 1k | 2k | 4k | 8k |
|---|---|---|---|---|---|---|---|
| α at 0° (local) | 0.08 | 0.23 | 0.57 | 0.93 | 0.97 | 0.98 | 1.00 |
| α at 45° (local) | 0.10 | 0.29 | 0.62 | 0.90 | 1.00 | 0.96 | 0.98 |
| α at 75° (local) | 0.21 | 0.38 | 0.50 | 0.60 | 0.79 | 0.65 | 0.69 |
| α at 75° (extended) | 0.27 | 0.49 | 0.62 | 0.69 | 0.77 | 0.83 | 0.83 |
| α Paris (local) | 0.12 | 0.30 | 0.58 | 0.84 | 0.95 | 0.90 | 0.92 |
| α Paris (extended) | 0.14 | 0.35 | 0.64 | 0.87 | 0.95 | 0.95 | 0.96 |
| preset `absorber_panel_2in` (textbook, reverberation-room style) | 0.28 | 0.70 | 0.88 | 0.92 | 0.94 | 0.92 | 0.95 |

- **Per-bounce effect** (plot, lower left). At the median image-hit angle of about 40°, α(θ) is within about 0.05 of the random-incidence value, which means < 0.4 dB of reflection level. At 75°, a 1 kHz reflection off the absorber is about **4 dB louder** than the random-incidence card makes it (|R|² 0.40 vs 0.16), and 125–250 Hz is slightly *more* absorbed. On hard surfaces (α < 0.1) the change is < 0.5 dB at any angle, which is inaudible.
- **How often grazing hits occur** (6×3×8 m, source and mic on the long axis, ASSUMED positions): first order has 0% of hits > 60°. Second order has 22% > 60° and 0% > 75°. Third order has 18% > 60° and 5% > 75°. The median is 40° at every order.
- **Model vs textbook preset:** the modelled Paris values are well **below** the textbook table at 125–500 Hz (0.12 vs 0.28 at 125 Hz). Textbook and ISO 354 values come from reverberation-room tests on finite samples, which include edge diffraction and can exceed the Paris-integral prediction. **So you cannot derive α(θ) by fitting a model to the preset tables without real material data. It would be invention.** This is the main reason for LATER.

**Audible:** absorptive walls would sound slightly "brighter" at glancing angles (wide rooms, sources near a wall). This is subtle next to the per-hit EQ that already exists.

**Cost:** Render: negligible (one angle per hit, and geometry already gives cosθ). Play: after P4.1 there is one early tap per line with a per-line cascade (roadmap P4.1, VERIFIED design), so an angle correction is a **packer-side** change (different coefficients per line) with **zero per-sample cost**. It fits the "serial per-hit cascade per image" lock, because it modifies the existing hit stage and adds no new stage.

**Recommendation: LATER.** Revisit if Idle adds porous presets with a known construction (σ, thickness, gap). Then use extended reaction for thin, rigid-backed layers (Jeong 2011), and apply only the *ratio* α(θ)/α_Paris to the measured random-incidence card, so the measured data stays the anchor.

## 2. Panel thickness / backing

**2a. Porous thickness + air gap (MODEL, same σ):**

| Octave (Hz) | 125 | 250 | 500 | 1k |
|---|---|---|---|---|
| 50 mm on rigid, α Paris (local) | 0.12 | 0.30 | 0.58 | 0.84 |
| 50 mm + 50 mm gap, α Paris (local) | 0.30 | 0.62 | 0.88 | 0.95 |
| 50 mm + 50 mm gap, α Paris (extended) | 0.22 | 0.51 | 0.81 | 0.92 |

- **Audible:** yes. The gap moves absorption about an octave lower, so the LF part of the tail shortens and the early field loses LF weight. This is the most common real-world difference between "panel on wall" and "panel on standoffs".
- **Cost:** zero at runtime. It is another α table, fitted by the existing `surfaces_fitter` (dual shelf, per-bounce R(f)).
- **Locks:** real materials only. Prefer measured tables for each construction (manufacturer data sheets for 25/50/100 mm mineral wool, with and without a gap). Where only a model is available, tag the preset `honesty: MODELLED (Miki+Paris, σ=…)`, never MEASURED. **Recommendation: YES** as preset variants (e.g. `absorber_panel_2in_gap2in`), roles `wall`/`ceiling` only (lock: no curtains or absorbers on the floor).

**2b. Membrane / panel absorbers.** Mass–air–spring resonance f0 ≈ 60/√(m·d) (m in kg/m², d = cavity depth in m), or about 50/√(m·d) with porous fill. This is the standard rule of thumb. Typical values (ASSUMED surface masses):

| Construction | f0 empty | f0 filled |
|---|---|---|
| 12.5 mm plasterboard (~9 kg/m²) on 75 mm studs | 73 Hz | 61 Hz |
| 2×12.5 mm (~18 kg/m²), 75 mm | 52 Hz | 43 Hz |
| 6 mm plywood (~3.5 kg/m²), 50 mm gap | 143 Hz | 120 Hz |
| 18 mm ply/MDF (~11 kg/m²), 25 mm battens | 114 Hz | 95 Hz |

- The existing presets already encode this at octave resolution. `gypsum_painted` α125 = 0.10 ("panel LF dip") and `plywood_panel` α125 = 0.28 ("LF panel absorb"). Both are fitted with low+high shelves (rmse 0.004 and 0.026 dB in R).
- A resonance peak at 100–150 Hz can't be represented by the shelf models (it needs a peaking stage, +1 biquad per hit). The roadmap's 7 octave bands start at 125 Hz, so plasterboard (≈ 60–75 Hz) falls outside the bands the fitter uses anyway.
- **Recommendation: LATER.** Only add a `PK` material stage if a thin-panel preset is added and its measured table shows a clear bump that the shelves miss by more than 1 dB.

## 3. FDN wall-tone (tail per-band decay from the materials)

**Formulas:**
- Sabine: T = 0.161 V / A.
- Eyring: T = 0.161 V / (−S ln(1 − ᾱ)).
- Fitzroy (1959): an area-weighted sum over the three axis pairs of Eyring-type terms, meant for non-uniform absorption.

Prawda, Schlecht & Välimäki (2022) show that errors in the assumed absorption dominate over the formula's own error, and that calibrated α gives ±10% for Sabine and Eyring whatever the absorption distribution.

**Prototype (MODEL, 6×3×8 m, presets = ASSUMED_TEXTBOOK α, no air term):**

| Room | ᾱ @1k | Sabine @125/1k | Eyring @125/1k | Fitzroy @125/1k | Eyring shape re 1 kHz (125…8k) |
|---|---|---|---|---|---|
| plaster walls/ceiling, parquet | 0.045 | 5.08 / 2.84 s | 5.02 / 2.78 s | 5.23 / 2.81 s | 1.81 1.81 1.12 1.00 0.86 0.82 0.78 |
| same + tile ceiling | 0.25 | 0.92 / 0.52 s | 0.85 / 0.45 s | 3.22 / 1.60 s | 1.89 1.56 1.15 1.00 0.98 1.03 0.98 |
| studio (absorber sides, carpet, tile ceiling) | 0.57 | 0.54 / 0.23 s | 0.47 / 0.15 s | 0.48 / 0.48 s | 3.11 1.77 1.29 1.00 0.83 0.84 0.78 |

- **Audible:** yes, and it matters a lot. The shape of the tail across frequency (LF 1.8–3× longer than 1 kHz in these rooms) is what makes "a plaster room" sound different from "a treated room". Today the tail tone comes from the dial plus the in-loop peaking, not from the chosen materials.
- **Which formula:** **Eyring** as the default. Sabine runs long once ᾱ > 0.2 (studio: 0.23 vs 0.15 s at 1 kHz). **Fitzroy** is a strong outlier when one axis is absorptive (tile ceiling: 1.6 s vs 0.45 s, with a non-monotonic curve in the studio case). Offer it as an option only, and do not make it the default.
- **Air:** the 4mV Sabine term is shown in the prototype for reference only. **Lock: no air on the FDN return**, so leave it out of the target.
- **Where it plugs in:** Jot & Chaigne (1991) per-line absorptive filters. Line i gets a gain per band of 10^(−3·d_i / (fs·T60(f))). This is the frequency-dependent generalisation of F2 (per-line broadband loss). Prawda, Välimäki & Schlecht (2019) use a full octave graphic EQ per line (≈ 10 biquads, too heavy for 32 lines in Play). The recommended cheap form is a low shelf + high shelf per line, fitted to the 7-band target, which reaches the T60 shape to about 5–10% (ASSUMED; verify with the acceptance test in the brief). A 5% T60 error is quoted as possibly audible (Prawda 2019).
- **Locks:** the unscaled ±1 Hadamard is untouched (the filters are per line, outside the matrix). No air on the return ✓. Early images still excite the FDN ✓. The two diffusion layers are untouched ✓.
- **2011 authenticity:** in unlocked (GainF) mode the tail should stay the 2011 mechanism (GainF + in-loop Dffs). Wall-tone is a **decay-lock feature**, which is also where F2 lives. It does not affect decision (a).
- **Cost:** 32 lines × 2 biquads ≈ 64 biquads/sample, **ASSUMED** 0.05–0.1 ms/block in WASM (from the flop count, not benchmarked). The coefficients are recomputed on scene or material change only.

**Recommendation: YES (decay-lock only).** Brief: `GROK_BUILD_BRIEF_Surfaces_extras.md`.

## Sources (checked 27 Sep 2026 by web lookup, except where noted)

- Delany, M. E. & Bazley, E. N. (1970). Acoustical properties of fibrous absorbent materials. *Applied Acoustics* 3(2), 105–116.
- Miki, Y. (1990). Acoustical properties of porous materials: modifications of Delany–Bazley models. *J. Acoust. Soc. Jpn. (E)* 11(1), 19–24.
- Paris, E. T. (1928). On the coefficient of sound-absorption measured by the reverberation method. *Philosophical Magazine* (series 7), vol. 5. Source of the random-incidence integral. Journal and year checked; page numbers not re-checked.
- Jeong, C.-H. (2011). Guideline for adopting the local reaction assumption for porous absorbers in terms of random incidence absorption coefficients. *Acta Acustica united with Acustica* 97(5), 779–790. doi:10.3813/AAA.918458.
- Jeong, C.-H. (2012). Absorption and impedance boundary conditions for phased geometrical-acoustics methods. *JASA* 132(4), 2347–2358. doi:10.1121/1.4740494.
- Mondet, B., Brunskog, J., Jeong, C.-H. & Rindel, J. H. (2020). From absorption to impedance: enhancing boundary conditions in room acoustic simulations. *Applied Acoustics* 157, 106884. doi:10.1016/j.apacoust.2019.04.034.
- Fitzroy, D. (1959). Reverberation formula which seems to be more accurate with nonuniform distribution of absorption. *JASA* 31(7), 893–897.
- Prawda, K., Schlecht, S. J. & Välimäki, V. (2022). Calibrating the Sabine and Eyring formulas. *JASA* 152(2), 1158–1169. doi:10.1121/10.0013575.
- Jot, J.-M. & Chaigne, A. (1991). Digital delay networks for designing artificial reverberators. *AES 90th Convention*, preprint 3030.
- Prawda, K., Välimäki, V. & Schlecht, S. J. (2019). Improved reverberation time control for feedback delay networks. *Proc. DAFx-19*, 299–306.
- Schlecht, S. J. & Habets, E. A. P. (2017). Accurate reverberation time control in feedback delay networks. *Proc. DAFx-17*, 337–344.

The panel rule f0 ≈ 60/√(m·d) is the standard mass–air–mass rule of thumb found in room-acoustics handbooks. It is used here only for orders of magnitude.
