# Surfaces: multi-bounce EQ, diffusion, solo, materials

**Date:** 2026-09-24  
**Audience:** Idle + Grok Build  
**Tag:** ASSUMED vs VERIFIED  
**Status:** research proposal — not implemented.

## Where we are (Desktop truth)

- **VERIFIED:** Six cards A–F: `absorb[7]` bands 125…8k, EQ (low shelf/peak/high shelf), diffusion `D`.
- **VERIFIED:** Hit names are A Left, B Ahead, C Right, D Behind, E Floor, F Ceiling.
- **ASSUMED:** The geometric surface split is A Left, C Right for Sides; B Ahead; D Behind; E Floor; F Ceiling.
- **VERIFIED:** Early colour is a serial cascade: `apply_surface_to_buffer` runs for **every** hit letter, not last-hit-only.
- **VERIFIED:** FDN inject currently uses the product of `sqrt(1−ᾱ)` only; card EQ is `early_only` today.
- **VERIFIED:** Diffusion has three distinct layers:
  1. Surfaces `D` → seeded `Δd` path jitter.
  2. NI Diffuser Delay `Dffs` from `tap_dff`.
  3. Geometric allpass by order.
- **LOCK:** Do **not** unify `Δd` with `Dffs`.
- **ASSUMED:** Current material chips are Plaster, Wood, Concrete, Curtain, Carpet.
- **VERIFIED:** There is no panel solo today.
- **LOCK:** Hadamard unscaled, `1/r²`, inject air once, mic colour door, and no A–F bit masks into audio.

## Multi-bounce EQ — recommendation

For a specular image path, the amplitude reflection is approximately `sqrt(1−α(f))` per hit. For a hit sequence, the total path response is therefore:

`H(f) = product of per-hit filters along the hit sequence`

Today's serial cascade is the right family for this model. **Keep the cascade.**

Clarify the UI: the colour sparkline represents the **cumulative path**, not one panel. A path that hits A, then E, then A again should visibly accumulate all three applications in order.

Defer Phase-5 modes `early_only | per_trip | on_exit` unless Idle specifically wants an FDN wall tone next. Default remains `early_only` for card EQ.

The mapping from band absorb values to peaking stages remains **ASSUMED** as a musical fit to the α bands. Later, the stages can be driven from a material-table α value without changing the same `sqrt(1−α) → dB` mapping.

## Diffusion — recommendation

Keep the two practical layers separate:

1. **Surfaces `D` = micro timing (`Δd`) — keep.** It must remain seeded and bit-identical.
2. **Structure `Dffs` = late smear — keep.** Do not drive it from `Δd`.

True scattering `s` in the ISO 17497 sense is not in the engine. A later proposal (do not code now) can define per-material `s ∈ [0,1]`:

- Specular early amplitude is multiplied by `sqrt(1−s)` (or specular energy by `1−s`).
- Fraction `s` contributes to inject/`Dffs` weight.
- This still creates no new image paths.

An image-source model cannot produce a full diffuse field; the FDN is already the diffuse stand-in. Do not rename `D` to “scattering” until a real `s` parameter exists.

## Panel solo — recommendation

Add **Surfaces Solo A–F**, plus **All** and **Mute face** controls.

- **Solo face X:** Early keeps only taps whose hit list contains X. Direct may optionally be muted while soloing. For FDN, either mute the inject or keep it broadband according to Idle's listening preference; default to **mute FDN when Surfaces solo is active** so the early panel is clear.
- **Mute face X:** Treat that card as `α=1` (total absorption) for the early cascade, or exclude taps that hit X. Prefer `α=1`: geometry stays intact while the panel acoustically “disappears.”
- Selecting a face for editing stays as it is today; solo/mute is an audition state, not an edit-selection replacement.

## Material library — sane set

The following is **ASSUMED** from published octave-table conventions (Sengpiel-style bands 125–4k). Extend the internal 8k value by clamping or gentle extrapolation, not by inventing a sharp jump. These are role-tagged material choices, not a claim that a chip is a lab-tested product.

### Keep / add

- Plaster smooth (wall/ceiling) — low α. **Role:** wall, ceiling.
- Painted plaster / gypsum board. **Role:** wall, ceiling.
- Brick unglazed (wall). **Role:** wall.
- Concrete / painted concrete. **Role:** floor, wall, ceiling.
- Wood parquet / wood on joists. **Role:** floor.
- Plywood panel 3/8 in (bassier absorb). **Role:** wall.
- Carpet on concrete. **Role:** floor only.
- Carpet on foam. **Role:** floor only.
- Glass window. **Role:** wall only.
- Acoustic ceiling tile. **Role:** ceiling.
- Absorber panel / fiberglass 2 in (studio tool). **Role:** wall.
- Heavy curtain / drape. **Role:** wall only; not floor or ceiling.

### Remove / ban

- Curtain as a paint kit for Floor (E) or Ceiling (F).
- Carpet for walls/ceiling unless Idle explicitly asks for it.
- Any “curtains on floor/ceiling” UI path.

### Indicative absorption table

These values are **ASSUMED textbook indicators**, not an ISO 354 product test. They are representative octave-band α values for 125, 250, 500, 1k, 2k, and 4k Hz. Actual values vary with construction, mounting, air gap, angle, and finish.

| Material | 125 | 250 | 500 | 1k | 2k | 4k |
|---|---:|---:|---:|---:|---:|---:|
| Plaster (smooth) | 0.10 | 0.06 | 0.04 | 0.03 | 0.02 | 0.02 |
| Brick (unglazed) | 0.03 | 0.03 | 0.04 | 0.05 | 0.07 | 0.08 |
| Concrete | 0.01 | 0.01 | 0.02 | 0.02 | 0.03 | 0.03 |
| Parquet | 0.15 | 0.11 | 0.07 | 0.06 | 0.07 | 0.07 |
| Carpet on concrete | 0.08 | 0.20 | 0.35 | 0.45 | 0.50 | 0.55 |
| Plywood panel 3/8 in | 0.30 | 0.15 | 0.10 | 0.07 | 0.06 | 0.06 |
| Glass window | 0.20 | 0.10 | 0.04 | 0.03 | 0.02 | 0.02 |
| Heavy curtain / drape | 0.07 | 0.10 | 0.20 | 0.35 | 0.45 | 0.50 |
| Acoustic ceiling tile | 0.20 | 0.30 | 0.55 | 0.70 | 0.75 | 0.80 |

The UI should filter material chips by selected-face role: **E** gets floor kits, **F** gets ceiling kits, and **A–D** get wall kits. Shift-paint-all applies only materials legal for each face; it must not bypass role legality.

## Out of scope / locks

- Do not touch Hadamard, `1/r²`, air inject, or mic colour while Build owns mic/air.
- Do not wire `absorb_masks` A–F bits into audio.
- Do not add new image paths for diffusion.
- Do not implement the proposal in this memo yet.

## Suggested Build phases (docs only)

- **P0:** Trim materials; add role filtering; remove curtain on E/F.
- **P1:** Add Surfaces Solo/Mute.
- **P2:** Let material α tables drive `absorb[7]`; keep EQ shelves as an optional override.
- **P3:** Optional scattering `s` → specular loss + `Dffs` weight (brief later).

Status: proposal for Idle — await go before Build.

---

## Build brief (appended 2026-09-24)

**LOCKED product brief:** [../docs/GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md](../docs/GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md) (v1.0) — panel Solo/Mute semantics; Mute=α=1-style; exclusive Solo; Play+Render; do not implement from this memo alone.
