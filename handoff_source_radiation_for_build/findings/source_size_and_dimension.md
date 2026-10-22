# Source size and "dimension": what makes a source sound big or small

Tags: VERIFIED = from the cited source (see `source_radiation_research.md`) or computed; ASSUMED = design choice.

## 1. The four cues and what our engine can do with each

| Cue | Physics / perception | Engine lever | Cost |
|---|---|---|---|
| **Beaming onset** | A radiator of radius *a* is ~omni while ka < 1. Above that it narrows; the −3 dB half-angle shrinks roughly as 1/(ka) (piston-in-baffle, Kinsler et al.). The onset is f₁ ≈ c/(2πa). VERIFIED (standard theory). | `size` rescales the preset's `f0` and `lp_hz` by a_preset/a_user, so a bigger source beams from a lower frequency. The preset stores `size.a_eq_m = c/(2π f0)` as its equivalent radius. | Free: coefficients only. |
| **Directivity to diffuse ratio** | The facing cue in rooms is the direct/early spectrum relative to the tail (Imbery 2019; Kato 2010 level + tilt). A big directional source has a large DI at HF, which darkens the tail relative to the direct sound when facing. VERIFIED (cited). | FDN inject goes through the power-averaged `diffuse_inject` filter. | 1 biquad per source per bus. |
| **Extent / decorrelation (ASW)** | Several decorrelated emission points spread over the source extent widen the apparent source width (Potard & Burnett 2004). Early lateral energy raises ASW (Barron & Marshall 1981). VERIFIED (cited). | (a) **per-image emission jitter**: each image leaves a different random point of the source ball, i.e. a path-length and small direction change of up to *a*. (b) **multi-point emission**: M points, each with its own image set. | (a) Free at runtime: it changes delays only (coefficients/delays at geometry update). (b) M× early taps. |
| **Near-field / parallax** | Near a large source (distance ≲ its size) the level gradient across it and the angular extent are audible. Point-source 1/r overstates the level at very small r. VERIFIED principle (Blauert, Spatial Hearing). | Optional near-field clamp: effective distance r_eff = √(r² + a²) for level only (ASSUMED). **Default off**, because the 1/r² geometric lock stays as the reference. | Free. |

## 2. Size numbers (VERIFIED arithmetic, c = 340 m/s as in the engine)

| Source | a (ASSUMED typical) | f₁ = c/(2πa) |
|---|---|---|
| Mouth (talking head) | 0.01–0.02 m (mouth), head ~0.09 m | mouth 2.7–5.4 kHz; head shadow from ~600 Hz |
| Trumpet bell (Ø 12 cm) | 0.06 m | ~900 Hz |
| Violin body | ~0.1 m | ~540 Hz |
| 10" speaker | ~0.11 m effective | ~490 Hz |
| 12" speaker | ~0.13 m | ~420 Hz |
| 2x12 baffle (horizontal) | ~0.3 m | ~180 Hz |
| 4x12 baffle (0.75 m square) | ~0.37 m | ~150 Hz (vertical and horizontal) |
| Grand piano soundboard / lid | ~0.7–1 m | 55–80 Hz |

The fitted `f0` gives an equivalent radius per preset (`size.a_eq_m` in each JSON). It is an **effective** radius of the fitted shelf, not a physical dimension.

## 3. Recommended implementation (ASSUMED, phased)

1. **Phase 1: size as beaming only.** The UI "Size" slider (a in cm, shown as a circle on the source dot) scales `f0` and `lp_hz`. Default = the preset's own `a_eq`, so there is no change.
2. **Phase 2: size jitter (cheap dimension).** Per image, draw a fixed pseudo-random point p_i in the ball of radius *a* (seeded, so Render and Play match). This gives:
   - a delay offset −p_i·e_i/c (sub-ms for a ≤ 0.5 m);
   - an optional emission-direction perturbation (for strongly directional presets, bright/dark varies image to image).
   It decorrelates the early images slightly without extra taps. **Kept separate from the surfaces' own diffusion jitter**, because the two diffusion layers must stay separate. Distance scaling: the jitter is absolute metres, so its angular size shrinks with distance automatically.
3. **Phase 3: multi-point emission (Advanced).** M ∈ {1, 2, 3, 4} emission points spread along the source's left–right axis (e.g. a 4x12 or a piano). Each point has its own image set (M× early taps). Levels are 1/M (power) so the total energy is invariant. The FDN inject is unchanged: diffuse, once per source. Cost scales linearly (see `source_radiation_c_offload.md`).
   - In Play, M > 1 is only feasible on reduced image counts, or by sharing the image set and adding only the M−1 **first-order** images and the direct sound per extra point (a recommended cheap variant: the order-0/1 arrivals carry most ASW, Barron & Marshall). ASSUMED.
4. **Not recommended:** randomised per-block modulation (it creates chorus-like artefacts); decorrelation all-pass filters on the direct sound (they smear transients; the engine already has per-hit allpass on images).

## 4. What "dimension" means for Idle's use-cases (ASSUMED listening guidance)
- **Guitar cab**: a big DI at HF, so facing the mic gives a bright, present direct sound and turning away makes it dark and roomy. A 4x12 is 'big' because the HF narrows early (f₁ ~150–400 Hz), plus two to four points in Phase 3.
- **Vocal**: small; directivity matters above ~1 kHz only. Turning away mostly dulls the consonants.
- **Piano**: large. Multi-point emission is where most of its dimension comes from; the directivity itself is ASSUMED (lid).
