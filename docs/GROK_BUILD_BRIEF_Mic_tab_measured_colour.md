# GROK BUILD BRIEF — Mic tab architecture + measured polar colour
### Comprehensive handoff for Grok Build (Idle Hanz — paste entire file)
### **v2.6** — Capsule angle is the 3D angle between aim and the incoming ray (2026-09-23)

| Field | Value |
|-------|--------|
| **Revision** | **v2.6** (2026-09-23) |
| **Canonical tree** | `C:\Users\IdleHanz\Desktop\2011 Room Reverb\` |
| **Canonical brief** | `...\docs\GROK_BUILD_BRIEF_Mic_tab_measured_colour.md` |
| **Mirror** | `...\mic_fitter\GROK_BUILD_BRIEF_Mic_tab_measured_colour.md` (**must stay byte-identical**) |
| **Review archive (v1→v2)** | `...\docs\GROK_BUILD_REVIEW_Mic_tab_2026-09-23.md` |
| **Review archive (v2.1→v2.2)** | `...\docs\GROK_BUILD_REVIEW_Mic_tab_v2.1_2026-09-23.md` |
| **Live software** | `...\software\` |
| **Mic data** | `...\mic_fitter\` (v3) |
| **Owner** | Idle Hanz |
| **Architecture / locks** | Reaktor Reverb Bot |
| **Implementer** | Grok Build |
| **Out of scope** | SE 2200A (no data — do not stub MEASURED) |

**Idle’s bar:** Clean, section-contained architecture. Prefer boring boundaries. Do not spend years fault-finding.

**Revision:** v2 folded the first read-only review. **v2.1** adds REPLACE (fitter model replaces the program shelf). **v2.2** locks SM57, boot ORTF ±55°, Render-only A/B vs ASSUMED_TOYS, L8, early-toy gate, SciPy-safe import, moving-path helper. **v2.3** puts the mic on arrival, leaves Air Abs on the adder input, and keeps wall cards early-only until a later switch. **v2.4** corrects the hooks against the code: filter L/C/R direct spikes **before** the fold; colour inside the three builders; gate early toys in `render_early_ir`; default SM57 when the page sends nothing; one filter design rebuilt at the live sample rate. **v2.5** retires the Structure microphone one-pole for good (the measured fit replaces it, including that fit’s own soft pole). The Structure **air** one-pole (`fc = Wet/Dis`) is also retired, but only in Phase 6, after Play matches Render. Mic phases must leave that air lowpass exactly as it is. **v2.6:** the capsule angle is the 3D angle between where the mic is aimed and the incoming ray (dot product). It is not the floor-plan angle. Same-height arrivals match the old horizontal angle, so the ORTF direct check does not move.

---

## LOCKED decisions (do not reopen without Idle)

### L0. REPLACE lock (Idle 2026-09-23) — highest priority
The **current** off-axis colour in the listened program is **replaced** by the mic_fitter model:

- **Retire from the default / Measured path:** `offaxis_shelf_gain_linear` (`MIC_OFFAXIS_SHELF_DB = -6.0`, baked into levels inside `compute_taps`) and any companion “toy” pole/HP/beaming that was standing in for mic colour.
- **Install instead:** fitter `dual_shelf_plus_soft_one_pole` via `relative_db` / `angle_weight` (high shelf + low shelf + relative soft pole, 20 Hz–16 kHz, degrees + fold inside the model). `MODEL_NAME = "dual_shelf_plus_soft_one_pole"`.
- **Not a permanent dual stack:** do not leave the −6 dB shelf under Measured shelves.
- **Migration safety (v2.2 LOCKED):**
  - **Boot scene = stock ORTF ±55°** (today’s desk). Mix Direct is **uncoloured today**; filtering Direct at ~55° **will** change the listened file vs today — that is expected under REPLACE, not a bug.
  - **“On-axis level ≈ today” is a fixture**, not the boot scene. Use a dedicated on-axis check (e.g. force θ≈0° / on-axis layout) to prove loudness parity; do **not** treat stock ORTF as that check.
  - When the old shelf is removed from inject scalars, **recompute makeup from the new pre-colour scalars** so FDN loudness does not jump (see L8).
  - Phase 1 exit must **report stock ORTF Render Direct+FDN vs today** (timbre will dull; call it out, do not “fix” by restoring the shelf).
- **Default Measured preset id = SM57** (LOCKED). Not an ASSUMED cardioid proxy. Thread the same id to all three capsule preset slots at first.
- **Preset load may set `family_*` / `polar_*` only.** Pattern map must **not** rewrite yaw / space / `mic_setup` on preset load (boot ORTF ±55° stays).
- **Structure microphone one-pole is retired (v2.5).** Do not add a `STRUCTURE_ONE_POLE` mode. Do not call `mic_one_pole_coeff` on the audio path. Do not set `apply_mic=True` or fill `mic_g` / `line.micG`. The functions stay in `early_field.py` because `selfcheck.py` tests the old law. The measured fit’s **soft one-pole is part of `relative_db`** and stays. It is not that Structure pole.

### L1. Where the mic filter sits (v2.4 LOCKED — arrival, not the loop)

The room changes the sound while it travels. The capsule changes it when that sound arrives. A linear filter inside the feedback loop is applied every trip; the same filter on the way out is applied once. Those are different sounds. Mic colour is the second one.

Checked against the program and against HANDOVER’s wet path (`In → Air Abs → + → Diffuser Delay`, microphone tapped off the delay, feedback returning to the `+` without the mic):

- **Where the code lives (v2.4).** Colour goes **inside** `render_listen_direct_ir`, `render_early_ir`, and `render_fdn_ir`. The still render, the moving hop, and two-sources all call those. A helper that only wraps `combined_ir` misses two-sources.
- **Mix Direct.** `render_listen_direct_ir` writes three spikes (`Ld`, `Cd`, `Rd`), folds them (`apply_capsule_weights`), then × 0.55. Filter **each spike at that capsule’s direct-tap θ before the fold**. The spike amplitude stays **1**. Do **not** multiply Mix Direct by `pattern_gain` (that level already lives on the early taps and the FDN inject only). Do not filter the stereo pair that comes back. The 0.55 gain can sit either side of the filter. Direct never enters the Hadamard. Today the spikes are uncoloured, so stock ORTF ±55° dulls L and R. Centre looks at the source, so its spike stays nearer 0 dB. Accepted under L0.
- **Early images.** Left and right only. There is **no centre early buffer**; centre colour is the Direct spike and the FDN centre bus. After that tap’s air dose and its surface-card EQ, filter `bl` / `br` at `theta_l` / `theta_r`, then sum. Do not write the coloured tap into the FDN. Gate `gradient_hp_hz` and `beaming_lp_hz` **in `render_early_ir`** (that is where they run). The shelf-skip flag is the only `early_field.py` edit. Default `early_wet: 0`, so this layer is silent until the Early fader is up.
- **FDN tail.** Three buses already (`l`, `c`, `r`). Filter each line of that bus on the way out: L lines use `theta_l`, C uses `theta_c`, R uses `theta_r` of the seed image. Read `process_block_poly` with `apply_mic=False`, filter those lines, **then** sum. The delay memory already holds unfiltered `y`. Do **not** colour `inject` / `xin` (`x = mixed + inject` would circulate the colour). With a 0 dB filter, the sum must match today’s `process_block_sum` (null test), so the path change itself does not retune the tail.
- **Do not** put one mic filter on the finished stereo bus after makeup, after the L/C/R fold, or on `combined_ir` as a whole.
- The old Structure microphone one-pole is **not** a later phase. Nothing may turn it on. `apply_mic` stays False. `mic_g` stays unset. Do not reuse that slot’s coefficient for the fitter. The fitter is its own filter on the same speaker tap.
- After the first Hadamard trip a line is no longer a pure image. The θ on that line is the seed image’s angle. That is the tail’s label. Do not invent a second angle.
- Phase 1 ships this on Render (Direct + FDN speaker tap). Early is coloured too. A/B is heard on Direct+FDN (`direct_wet: 1`, `fdn_wet: 1`).

### L2. θ contract (v2.6 — aim · incoming ray)

The angle that drives pattern level and mic colour is the angle between the capsule’s aim and the direction the sound is arriving from. A dot product is that angle. The long floor-plan arctangent is the same answer only when the ray is level with the mic.

- Aim is horizontal. Yaw 0 looks toward +Z: `look = (−sin yaw, 0, cos yaw)`. The stand does not tilt up or down. Height is in the ray, not in a second mic angle.
- `û` is the unit vector from the capsule to the image (the incoming path).
- `cosθ = clamp(look · û, −1, 1)`. `θ = acos(cosθ)`, so θ runs from 0 (straight ahead) to π (straight behind).
- Pattern uses `cosθ` directly. Fig-8 is `cosθ`. Cardioid is `½(1+cosθ)`. Do not run that through `direction_angles()[0]`.
- Mic colour converts θ to degrees inside MicColour. The fitter’s fold stays inside `angle_weight`.
- If the image sits on the capsule, treat it as on-axis (`cosθ = 1`).
- Do not use `arrival_cos_xz`. That helper drops height on purpose. Do not pass the discarded elevation return (`direction_angles`’s second value) in as θ. That is the angle above the floor, not the angle off the mic’s axis.
- Same-height source and mic: this θ matches today’s horizontal angle. Floor and ceiling images move off-axis and their pattern level changes. That is expected. Do not “correct” it back to the floor plan. Structure’s XZ arctan stays in the findings as what the patch did. The product uses this ray angle.

### L3. MicColour return / import graph
- Returns `H_db(θ,f)` and optional HPF dB only.
- Callers own `pattern_gain` (signed for audio, abs for drawings).
- Package: `software/mic_colour/`. Imports **neither** `early_field` nor DOM.
- `early_field` does **not** import MicColour — only gains a flag to **skip** `offaxis_shelf_gain_linear` once hooks own colour.
- Hooks owned by `render_pipeline.py` + `live_fdn_params` (document in `software/mic_colour/HOOKS.md`).
- **SciPy-safe import (v2.2 LOCKED):** do **not** import `mic_fitter` through the package `__init__` (it pulls SciPy). Port golden vectors into `software/` tests, **or** load `model.py` alone. Importable paths: outer folder on path → `mic_fitter.model`; repo root → `mic_fitter.mic_fitter.model` (package lives at `mic_fitter/mic_fitter/`).

### L4. How audio realises H (v2.4 — one design, rebuilt per sample rate)
- Use fitter `relative_db` (import `mic_fitter.model` alone, or golden-port — see L3 SciPy note).
- **One design:** `relative_db` → one causal minimum-phase filter at a stated sample rate. Not `rbj_highshelf`, not `mic_one_pole_coeff`, and not a second “close enough” biquad invented in Phase 3.
- Phase 1 builds that design at the **render file rate**. Phase 3 builds the **same design** at the **AudioContext rate**. Do not copy 44.1 kHz coefficients into a 48 kHz worklet. `HOOKS.md` records the design.
- **Play live keeps today’s −6 dB shelf until Phase 3.** Phase 1 A/B is **Render only**.

### L5. State shape
- **Three preset ids** (L / C / R), even if UI dropdown writes all three at first.
- **Default all three = SM57** after Phase 1 replacement (L0).
- **Missing fields default on the server (v2.4).** Today’s page sends no preset id and no ColourMode. `params_from_body` must treat those absences as SM57 × 3 and `MEASURED_SHELF`. If it waits for the page, Phase 1 changes nothing.
- Loading a preset sets that capsule’s `family_*` / `polar_*` via an explicit ASSUMED map (`fig8_ribbon`→fig8, `hypercardioid`→super, etc.). **Must not write yaw / space / mic_setup.**
- Omni→super morph slider is **not live under MEASURED**.

### L6. Modes + HPF
```
MEASURED_SHELF = default (fitter dual shelf + the fit’s own soft pole); preset SM57
BYPASS         = pattern gain only; shelf OFF; fitter OFF (not the Phase 1 A/B reference)
ASSUMED_TOYS   = LEGACY / Phase 1 A/B reference — today’s −6 dB level shelf + early gradient/beaming.
                 Not the product default. Do not newly wire dead apply_capsule_colour.
```
There is **no** Structure-pole mode. Do not add one.
- One enum. `BYPASS` is that enum value. Do **not** add a second bypass checkbox beside it.
- **Phase 1 A/B reference mode = ASSUMED_TOYS** (today’s FDN shelf), **not** BYPASS. BYPASS = pattern-only, shelf off, fitter off.
- Manufacturer HPF is **orthogonal**, default off, disabled when `hpf_hz` is null; stacks on every mode. Not the unwired panel `mic_hp_*`.
- **Early toys gate (v2.4):** gate `gradient_hp_hz` and `beaming_lp_hz` **off** unless mode is `ASSUMED_TOYS`. They run in `render_early_ir`, not in `early_field.py`.

### L7. Loader
- Resolve **repo root** containing both `software/` and `mic_fitter/` (not `Path(__file__).parents[1]` from inside `mic_colour/`).
- Read `mic_fitter/presets/index.json` (`mic_fitter.preset_index.v3`) and `presets/assumed/index.json` (v2).
- Accept v3; v2 only if nine params + `dual_shelf_plus_soft_one_pole` present.
- Do not scan `pending_se2200a` or `presets_assumed_backup/`. User saves outside `mic_fitter/presets/`.

### L8. Shelf vs makeup (v2.2 LOCKED — full mode list)
- **Every mode except `ASSUMED_TOYS`:** build inject **scalars without** `offaxis_shelf_gain_linear`; compute makeup from those pre-colour scalars **before** the frequency filter.
- **`ASSUMED_TOYS` alone** restores the old −6 dB level shelf and must **NOT** leave the fitter on the Direct spike.
- Do **not** scale the inject scalar by `10^(H/20)`.
- The fitter is **not** on the inject. Stripping the old shelf changes inject **level**. The frequency filter happens later, on the speaker tap, and must not be folded back into those scalars.

### L9. Air (v2.5 — placement stays; the lowpass goes in Phase 6 only)

Real air is a small high-frequency loss that grows with distance (ISO 9613-1). The Structure one-pole `fc = Wet/Dis` is a much darker stand-in for that same idea (a 10 m path can put the knee near 40 Hz). It is **not** part of the physics model. Idle retired it. The ISO shelf from `air_fitter` replaces the **assumed** shelf (`−0.15 dB/m`), not the lowpass. Doing both at once would leave the room muffled and hide the ISO curve.

**Mic phases 1–5 must not touch air.** Leave `air_lp` at 0.25, leave `fc = Wet/Dis`, leave the assumed shelf. Do not set `air_lp` to 0 “while you’re there.” A mic A/B that also brightens the tail cannot be judged.

**Phase 6, and only after Phase 3** (Play and Render already share the mic filter):

- Remove the air one-pole from Render and from the worklet. Do not leave a coefficient someone can turn back to 0.25. Do not delete `one_pole_lp_process` if something else calls it; just stop calling it from air.
- Replace `humidity_shelf` with the studio preset `air_fitter/presets/studio_20C_50RH.json` (`dual_high_shelf`). `A_db(f, d) = d · H1(f)`, then `10^(A_db/20)`. Load `model.py` alone (the package `__init__` pulls SciPy). Do not refit.
- Humidity **0** still bypasses air colour. Humidity **above 0** selects that ISO colour. It no longer sets `Wet`. `air_shelf` remains the mix of that colour (default 1). `air_lp` is ignored and must not be wired back to a lowpass.
- Other climate presets can wait. Default is studio 20 °C / 50 % RH.
- **Placement does not change.** Once on each early image, from that path length, before the mic filter. Once on each FDN inject, from that line’s distance. Not on Mix Direct. Not on the feedback return (adder 473). Not on every loop trip — that would add a full dose per circulation and darken far past the ISO path.
- Geometric **`1/r²` stays.** Axial peaking stays. This phase does not move the mic filter.

Expect a **brighter tail** than today. That is the point of removing the lowpass. Do not “fix” it by putting the pole back.

### L10. Wall-tone switch (v2.3 DOCUMENTED — later phase, default = today)

Panel-card EQ is an ASSUMED upgrade, not Structure. The program today is the default. The other two positions are listens for a later session. Do not build the switch in Phase 1, and do not change axial peaking as part of it.

Axial peaking (`peaking_stages_for_tap`, on inside `process_block_poly` every trip, and on each early tap) stays where it is. It is not the surface-card EQ.

| `wall_tone` | What you hear | Written back into the FDN? |
|-------------|---------------|----------------------------|
| `early_only` **(default, current program)** | Card EQ on early-image buffers only (`apply_surface_to_buffer` after air). FDN inject is scaled once by broadband `tap_reflect_gain`. No card EQ in the loop. | No |
| `per_trip` | Same early path, and the hit cards’ tone also runs **inside** the loop once per circulation. The tail darkens a bit more every trip. This stands in for “another bounce,” because a mixed line no longer knows which panel it hit. | Yes |
| `on_exit` | Card tone once on each FDN line’s **speaker tap**, using that line’s delay length (longer line, more tone), after the loop. Early path unchanged. | No |

Default remains `early_only` until Idle flips the switch and listens. Phase 5 only.

---

## Ambiguities resolved (v2.2 — Idle locks from second Build review)

| Topic | Locked side |
|-------|-------------|
| Default Measured preset | **SM57**; three ids all = SM57 at first |
| Preset load side-effects | `family_*` / `polar_*` only — **no** yaw / space / `mic_setup` rewrite |
| Boot vs on-axis check | Boot = **ORTF ±55°**; “on-axis ≈ today” = **fixture**, not boot |
| Mix Direct today | Uncoloured; filtering Direct at ~55° changes the file (expected under REPLACE) |
| Phase 1 A/B path | **Render only**; Play keeps −6 dB shelf until Phase 3 |
| Phase 1 A/B reference | **ASSUMED_TOYS** (today’s FDN shelf), not BYPASS |
| BYPASS meaning | Pattern-only; shelf off; fitter off |
| L8 modes | All except ASSUMED_TOYS strip shelf; ASSUMED_TOYS restores shelf, no fitter on Direct |
| Early toys | `gradient_hp_hz` / `beaming_lp_hz` off unless ASSUMED_TOYS |
| SciPy | No package `__init__` import; goldens port or `model.py` alone |
| Moving path | Calls the same three builders as the still render. Not a second helper on `combined_ir` only |
| Mic vs the loop | Speaker tap off the delay output. **Not** on FDN inject. Not written back. Not one EQ on the finished mix |
| Air Abs | Same door (adder input, once). Mic phases: leave the lowpass and the assumed shelf untouched. Phase 6: ISO shelf instead, lowpass gone |
| Wall cards | Switch later. Default `early_only` = current program. Tries: `per_trip`, `on_exit`. Axial peaking stays put |
| Direct fold | Filter `Ld`/`Cd`/`Rd` **before** `apply_capsule_weights`. Never the returned stereo pair |
| Builders | Colour inside `render_listen_direct_ir`, `render_early_ir`, `render_fdn_ir` — not only `combined_ir` |
| Page sends nothing | Server defaults SM57 × 3 and `MEASURED_SHELF` |
| Filter design | One minimum-phase design from `relative_db`, rebuilt at the sample rate in use. No second biquad |
| Early centre | No centre early buffer. Centre colour is Direct + FDN centre bus |
| Structure mic pole | Retired. No mode, no `apply_mic`, no `mic_g`. Functions stay for selfcheck. The fit’s soft pole stays inside `relative_db` |
| Air lowpass | Stays in the code through mic phases. Phase 6 removes it and swaps the assumed shelf for the ISO studio preset. Not before Phase 3 |
| Phase 3 live taps | Direct delay, early delay, and FDN `y` — three places, each before its sum |

---

## A. Mission

Replace Mic tab ASSUMED flat cardioids + toy colour chrome with a contained **MicColour** subsystem that:

1. Loads mic_fitter v3 presets (MEASURED + ASSUMED proxies).
2. Drives Polar solids from the **same** model as audio.
3. Applies **relative** off-axis colour per arrival, per L/C/R.
4. Leaves Mix laws, Hadamard, Air Abs `1/r²`, Surfaces, Two-sources gains alone except documented hooks.
5. Makes colour modes exclusive (no Measured + Structure + toys mush).

Success: Idle loads SM57 / U87 cardioid / Royer, sees an honest solid, Plays/Renders, and hears musical shelf-led dulling — **not** the old −6 dB linear shelf and **not** a phone filter.

---

## B. Non-goals

- Do not retune Two-sources, Direct 0.55 fold constant (`LIVE_DIRECT_FOLD = 0.55`), FDN makeup **formula**, or listened wet defaults except as required by L0/L8 (pre-colour scalars).
- Do not change Air Abs `1/r²`, unscaled ±1 Hadamard, Decay lock.
- Do not uniquify delays; do not invent A–F / OCR Hadamard into audio.
- Do not rebuild Floor / Lattice / Paths / Surfaces in this pass.
- Do not add a second FDN.
- Do not claim SE2200A.
- Do not put Mix / Hadamard chrome on the Mic tab.
- Do not drive MEASURED from Proximity / Capsule mm / Mic response Hz.
- Do not use Play live as the Phase 1 A/B (Render only until Phase 3).
- Do not move Air Abs onto the feedback return, and do not change `1/r²`.
- Do not remove or bypass the air one-pole during mic phases. That is Phase 6, after Phase 3.
- Do not wire the Structure microphone one-pole. Do not delete its functions (`selfcheck` still calls them).
- Do not build the wall-tone switch in the mic phases (L10, Phase 5). Do not pull axial peaking out of the loop.

---

## C. Current state (VERIFIED 2026-09-23 against Desktop)

| Piece | Where | Honesty | Role after L0 |
|-------|--------|---------|----------------|
| Defaults | `static/js/app.js` | VERIFIED | `early_wet:0`, `fdn_wet:1`, `direct_wet:1` — A/B on Direct+FDN |
| Direct | `render_listen_direct_ir`: spikes, then `apply_capsule_weights`, then ×0.55 | VERIFIED | **No air.** Filter `Ld`/`Cd`/`Rd` **before** the fold. Uncoloured today |
| FDN mic tap | `fdn.py` `process_block_poly`: buffer stores `y`, then `mic_g` (if on) filters each line before the fold. Worklet adds `xin` into the loop and does **not** filter `y` | VERIFIED | Measured colour uses this **speaker tap**. `apply_mic` stays False. Do not colour `inject` |
| Air on the FDN | `build_inject_from_taps`; worklet air on `xin` before the add. One-pole `fc=Wet/Dis` plus assumed shelf | VERIFIED current code | **Mic phases: leave both.** Phase 6 removes the one-pole and replaces the shelf with ISO. Still one dose, not on the feedback return |
| Wall cards | `apply_surface_to_buffer` on early taps only; `tap_reflect_gain` scales FDN inject | VERIFIED current | Default `early_only`. Switch is Phase 5 |
| Axial peaking | Inside `process_block_poly` every trip, and on early taps | VERIFIED current | Not the card EQ. Do not move it for L10 |
| `apply_capsule_colour` | `early_field.py` | VERIFIED dead (0 callers) | Do **not** newly wire as the replacement |
| Early gradient/beaming | `gradient_hp_hz` / `beaming_lp_hz` inside `render_early_ir` | ASSUMED | Silent at `early_wet=0`. Gate **there**, off unless ASSUMED_TOYS. Not an `early_field.py` edit |
| Structure mic one-pole | `mic_one_pole_coeff`; `apply_mic=False`; worklet ignores `line.micG` | Law real; audio path off | **Retired.** Do not wire it. Keep the functions for selfcheck. Measured soft pole stays inside `relative_db` |
| Fitter model | `mic_fitter/mic_fitter/model.py` `relative_db`, `angle_weight` (degrees) | VERIFIED | **Replacement colour**; load `model.py` alone (no SciPy `__init__`) |
| Presets | `presets/index.json` v3 (17 measured); `presets/assumed/` v2 | VERIFIED | Read-only data; default id **SM57** |
| Polar | `POST /api/polar` assumed LF→omni morph | ASSUMED | Replace radius in Measured mode |
| Name clash | `POST /api/colour` = IR spectrum | VERIFIED | New mic routes must not reuse `/api/colour` |
| Worklet | `WORKLET_VER = 12` in `live_fdn.js` | VERIFIED | Bump on worklet change |

**Audible-bus warning (VERIFIED):** a hook only in early IR is inaudible at default wets. Phase 1 must colour **Direct + the FDN speaker tap** (per line, not fed back). Colouring the inject would circulate inside the loop and is the wrong door.

---

## D. Architecture (contained)

```
UI Mic desk ──► MicColour (software/mic_colour/) ──► Polar adapter
                              │
                              ├── render_pipeline hooks (Direct, early after air/cards, FDN speaker tap)
                              └── live_fdn_params / worklet (Phase 3)

UNTOUCHED cores: Hadamard, Air Abs, Mix wet laws, Two-sources gains, Surfaces
```

### D.1 Package
- `software/mic_colour/model.py` — equations match fitter `relative_db`
- `software/mic_colour/preset_store.py` — repo-root resolver
- `software/mic_colour/modes.py` — ColourMode matrix + L0 replace semantics
- `software/mic_colour/hpf.py` — optional manufacturer HPF
- `software/mic_colour/HOOKS.md` — four call sites
- `software/tests/test_mic_colour_relative.py` — golden vectors from fitter (ported; no SciPy `__init__`)
- Optional thin `static/js/mic_colour.js` **or** mesh API (prefer one pattern math)

### D.2 Mode matrix

| Mode | pattern_gain | fitter (shelves + its soft pole) | Old −6 dB shelf / early toys |
|------|--------------|-----------------------------------|-------------------------------|
| MEASURED_SHELF | ON | ON | OFF |
| BYPASS | ON | OFF | OFF |
| ASSUMED_TOYS | ON | OFF | ON (legacy / Phase 1 A/B ref) |

### D.3 Split gains
1. θ = angle between capsule aim and the incoming ray (L2). Not the floor-plan angle.
2. `g_pat = pattern_gain(θ, pattern)` — broadband, where it already is (early levels and FDN inject). Not on Mix Direct.
3. Colour = mode filter (Measured = fitter H).
4. Room distance / Air Abs / surface EQ stay outside MicColour.

### D.4 Polar
- Radius = `abs(pattern_gain(θ)) * 10^(H_db(θ,f)/20)`.
- In MEASURED: **drop** LF→omni morph.
- Rings: 20 / 63 / 125 / 250 / 1k / 4k / 8k / 16k.
- Mic desk + `POST /api/polar` share this. No fifth pattern function.

### D.5 API
- `GET /api/mic_presets`, `GET /api/mic_presets/{id}`
- Optional `POST /api/mic_colour/mesh`
- **Do not** reuse `/api/colour` (`POST /api/colour` = IR spectrum)

### D.6 UI (Phase 2+)
Mic tab owns: placement desk, capsule model + honesty badge, ColourMode (the enum **is** the bypass), HPF, polar hero, designer knobs (Advanced). No extra bypass checkbox.
Does not own: Mix / FDN / Surfaces / Lattice.

### D.9 Call sites (all four)
The helper lives **inside** the three builders. `combined_ir`, the moving hop, and the two-source branch pick it up by calling them. Phase 3’s `live_fdn_params` / worklet mirrors the same three taps. The helper colours:

- `Ld`, `Cd`, `Rd` in `render_listen_direct_ir`, each at its own direct θ, **before** the fold
- each early `bl` / `br` **after** air and card EQ (`theta_l` / `theta_r` only — no centre early buffer)
- each FDN line from `process_block_poly` (`apply_mic=False`) **before** the per-bus sum: L bus `theta_l`, C bus `theta_c`, R bus `theta_r`. Not the inject

Source B colours B’s early and B’s direct. The single FDN stays on A’s image times and A’s seed angles. Causal minimum-phase from `relative_db`, designed at the rate of that render. Phase 3 redesigns at the live rate (L4). Makeup = L8. Bump `WORKLET_VER` when the worklet changes. Null test: 0 dB filters, poly-sum matches today’s `process_block_sum`. Worklet Phase 3 colours three places, and does not write them back: the per-bus direct delay (before × 0.55), the early-delay read, and FDN `y` before `fdnOut +=`. Air on `xin` stays (L9).

---

## E. File touch list

| Area | Files | Action |
|------|--------|--------|
| NEW | `software/mic_colour/*` | Core + HOOKS.md + tests |
| Engine | `early_field.py` | Aim·ray angle for pattern and colour (L2). Skip-shelf flag. Do not leave `compute_taps` on the floor-plan angle |
| Render | `render_pipeline.py` | Colour inside the three builders. Gate early toys in `render_early_ir`. Direct spikes before the fold. Poly lines before the sum. Do not enable `apply_mic` |
| Live | `fdn_worklet.js`, `live_fdn.js` | Phase 3: direct delay, early delay, and FDN `y`. Play keeps the old shelf until then |
| Polar | `polar_field.py`, `polar_field.js` | Measured radius |
| Mic UI | `mic_desk.js`, `index.html`, CSS | Phase 2 |
| API | `app_server.py` | Preset routes |
| Data | `mic_fitter/presets/*` | Read-only |

**Do not edit:** Hadamard core, `LIVE_DIRECT_FOLD` constant, Air Abs `1/r²`, Two-sources gain laws. Do not set `apply_mic=True`. Do not newly call `apply_capsule_colour` as the product path. Do not import `mic_fitter` or `air_fitter` via package `__init__`. Do not strip the soft pole out of `relative_db`.

---

## F. Phases (one per Build session)

### Phase 1 — Ray angle and measured colour together (no Mic UI redesign)

The 3D angle is part of this session. Colour and pattern use that same angle in one pass. Do not render twice and do not stop between them. A second render was only a way to separate the two effects by ear. The math does not need it.

- Replace the floor-plan θ in `compute_taps` with L2 (`acos(look · û)`). Pattern level on early taps and FDN inject uses `cosθ`. Mix Direct spikes stay amplitude 1.
- Add `mic_colour` + golden tests vs fitter `relative_db` (SM57 @ 0°/90°/180°, 1 kHz & 8 kHz). Port goldens or load `model.py` alone — **no SciPy package `__init__` import**.
- Repo-root preset loader (v3 + qualified v2).
- Server defaults: missing preset ids → SM57 × 3; missing mode → `MEASURED_SHELF`.
- Wire MEASURED_SHELF inside the three builders: `Ld`/`Cd`/`Rd` **before** the direct fold; FDN poly lines **before** the per-bus sum (`apply_mic=False`, bus θ as in L1); early `bl`/`br` **after** air and card EQ.
- Do **not** colour FDN inject. Do **not** filter the already-folded direct stereo. Do **not** multiply those spikes by `pattern_gain`. Do **not** change air (leave the one-pole and the assumed shelf). Do **not** add `wall_tone`. Do **not** set `apply_mic=True`. Do **not** call `mic_one_pole_coeff`.
- Remove old shelf from inject **scalars** per L8 (every mode except ASSUMED_TOYS). Makeup uses those scalars. The fitter is not one of them.
- **Gate early** `gradient_hp_hz` / `beaming_lp_hz` in **`render_early_ir`**, off unless ASSUMED_TOYS.
- Preset load may set `family_*` / `polar_*` only — must not write yaw / space / `mic_setup`.
- Null test: 0 dB filters, FDN sum matches today’s `process_block_sum`.
- **A/B = Render only** vs **ASSUMED_TOYS** (today’s FDN shelf). BYPASS stays available as pattern-only. **Play keeps today’s −6 dB shelf until Phase 3** — do not use Play as the A/B.
- Moving hop uses the **same colour helper** as `combined_ir`.
- **Exit:** one stock ORTF Render against today. Same-height direct dulling is the mic (L/R about 55°, centre nearer unchanged). Floor and ceiling level changes are the new angle, not a broken fit: in front and above gets quieter, behind and above gets a little less rejected. Makeup may barely move. L/R entrances lose the −6 dB shelf, so their lows rise a little, then the fitter darkens their highs. On-axis loudness is a fixture, not the boot scene. Off-axis follows the fitter, not the −6 dB law. Two-source and moving call the same three builders. `selfcheck` runs the new tests. No Mic tab chrome. Structure mic pole stays uncalled. Air lowpass stays in the path.

### Phase 2 — Mic tab UI
Preset dropdown + badges, ColourMode, HPF, multi-f 2D + hero solid, demote toys.

### Phase 3 — Live parity
Same design as Render, rebuilt at the AudioContext rate (L4). Three worklet taps: per-bus direct delay before × 0.55, early-delay read, and FDN `y` before `fdnOut +=`. Do not write those filters back. Do not colour `xin`. Bump `WORKLET_VER`. **Only then** does Play match Render. Until then Play keeps the old shelf.

### Phase 4 — Designer knobs + pattern variant chips

### Phase 5 — Wall-tone switch only (after a mic listen)
- Add `wall_tone`: `early_only` (default, today’s program) / `per_trip` / `on_exit` (L10).
- Do not change the air lowpass or the air shelf. Do not move axial peaking. Do not retune the mic filter.
- **Exit:** Idle can flip the switch on a Render and hear the two tries against `early_only`.

### Phase 6 — Air physics (only after Phase 3 has been listened to)
- Render and Play already share the mic filter. This session changes air on **both**, or on neither.
- Remove the air one-pole (`fc = Wet/Dis`) from Render and the worklet.
- Replace the assumed −0.15 dB/m shelf with `studio_20C_50RH` (`dual_high_shelf`). Humidity 0 bypasses. Humidity above 0 uses that curve. `air_shelf` is the mix (default 1). `air_lp` is not a lowpass anymore.
- Same doors as now: early path and FDN inject, once, from distance. Not Direct. Not the feedback return. `1/r²` unchanged. Mic filter unchanged. Axial peaking unchanged.
- **Exit:** tail is brighter than the one-pole days. ISO shelf is the only air tone. Do not put the lowpass back.

**Build prompt:** paste this brief + “Execute Phase N only.”

---

## G. Acceptance tests

1. Default preset id = **SM57** (all three slots); colour is fitter `relative_db` (**not** −6 dB shelf) on the Direct spike and on each FDN **speaker-tap** line. The inject that enters the Hadamard is uncoloured by the fitter.
2. Phase 1 A/B: **Render** MEASURED_SHELF vs **ASSUMED_TOYS** (not BYPASS; not Play). On-axis level matched within agreed tolerance via **fixture**.
3. θ=0 → ~0 dB relative (HPF off).
4. SM57 @ 90° = this shelf model including relative pole; **fail** if loss is `mic_one_pole_coeff` or a single LP.
5. No audio path calls `mic_one_pole_coeff` or sets `apply_mic`. Selfcheck of that old law still passes. The measured soft pole is still inside `relative_db` (test 4).
6. Royer: fig-8 after preset map; rear may be dark (angle law monotonic); map does not rewrite yaw/space/mic_setup.
7. U87 Omni vs Cardioid distinct.
8. HPF test on U87/C414 only (SM57 `hpf_hz` null); test 3 with HPF off.
9. ORTF / Floor unaffected placement-wise; stock ORTF Render Direct+FDN timbre **may dull vs today** (accepted); Two-sources smoke; Hadamard/Air Abs smoke; moving path same helper.
10. No SE2200A. `/api/colour` still IR spectrum. No SciPy pulled via `mic_fitter` package `__init__`.

---

## H. Idle suggestions (in scope)

1. Mic tab = desk; hero = frequency-stacked polar solid.  
2. Preset gallery + honesty badges.  
3. BYPASS is a ColourMode, for A/B against Measured. Not a second checkbox.  
4. Designer knobs + Reset.  
5. Pattern packs via existing preset ids.  
6. ~~SE2200A~~ excluded.  
7. Leave Mix/Hadamard alone.  
8. Review each phase against this brief.

---

## I. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Stock ORTF Direct dulls vs today (Direct uncoloured today; ~55° filter) | **High — accepted phase risk** | Call out in Phase 1 exit; do not “fix” by restoring shelf. Idle must not treat as broken hook. |
| Play ≠ Render until Phase 3 (Play keeps −6 dB shelf) | **High — accepted phase risk** | Phase 1 A/B = Render only; document so Idle does not treat as broken hook. |
| Inaudible Phase 1 (early-only hook) | High | Colour Direct + FDN speaker tap (L1) |
| Mic colour fed into the loop via inject | High | L1: filter line output only; buffer write stays uncoloured |
| Air moved onto the feedback return | High | L9: leave adder-input air. Not a mic-phase edit |
| Wall switch slipped into Phase 1 | Med | L10 / Phase 5. Default stays `early_only` |
| Mix jump when removing −6 dB shelf | High | L8 makeup from pre-colour scalars |
| Structure mic pole wired “for authenticity” | High | No such mode (L0). `apply_mic` stays False |
| Air lowpass removed during a mic phase | High | Phase 6 only, after Phase 3. Mic phases leave `air_lp` alone |
| ISO shelf stacked on the air lowpass | High | Phase 6 removes the lowpass in the same session as the shelf swap |
| Early toys still on under MEASURED | Med | Gate `gradient_hp_hz` / `beaming_lp_hz` unless ASSUMED_TOYS |
| SciPy pulled via `mic_fitter` `__init__` | Med | Port goldens or load `model.py` alone |
| Moving hop misses colour helper | Med | Same helper as `combined_ir` (D.9) |
| `mic_g` filled with the fitter, or the old pole turned on | High | Fitter is its own filter. `apply_mic` stays False. `mic_g` stays empty |
| Filtering the folded direct stereo | High | Filter `Ld`/`Cd`/`Rd` before the fold (L1) |
| Helper only on `combined_ir` | High | Colour inside the three builders |
| Toys gated in `early_field.py` | High | Gate them in `render_early_ir` |
| 44.1 kHz coeffs used at 48 kHz, or a Phase 3 biquad | High | One design, rebuilt at the rate in use (L4) |
| Page never sends SM57, so Phase 1 is silent | High | Server defaults when fields are absent |
| Degrees vs radians, or floor-plan θ instead of aim·ray | High | L2. `acos(look·û)`. Do not use `arrival_cos_xz` or the discarded elevation |
| Polar morph lie | High | D.4 |
| Path/`parents[1]` bug | High | L7 |
| Quota | — | One phase per session |

---

## J. Reference paths

- Software: `C:\Users\IdleHanz\Desktop\2011 Room Reverb\software\`
- Mic fitter: `C:\Users\IdleHanz\Desktop\2011 Room Reverb\mic_fitter\`
- Air fitter (Phase 6 only): `C:\Users\IdleHanz\Desktop\2011 Room Reverb\air_fitter\` — preset `studio_20C_50RH.json`
- Launch: `CLICK ME - Open Tweak App.bat` → http://127.0.0.1:7860
- Review archive (first): `docs\GROK_BUILD_REVIEW_Mic_tab_2026-09-23.md`
- Review archive (second, v2.1): `docs\GROK_BUILD_REVIEW_Mic_tab_v2.1_2026-09-23.md`

---

## K. Suggested Build prompts

**Phase 1:**  
`Read docs/GROK_BUILD_BRIEF_Mic_tab_measured_colour.md (v2.6). Execute Phase 1 only. One pass: aim·ray angle (L2) and measured colour together. Do not render twice. Do not use the floor-plan angle or arrival_cos_xz. Server defaults missing preset/mode to SM57 ×3 and MEASURED_SHELF. Colour inside render_listen_direct_ir (Ld/Cd/Rd before the fold), render_early_ir (bl/br after air and card EQ; gate gradient/beaming there unless ASSUMED_TOYS), and render_fdn_ir (process_block_poly lines before the sum, apply_mic=False, per-bus theta). Do not colour FDN inject. Do not filter the folded direct stereo. Do not multiply Mix Direct spikes by pattern_gain. Do not set apply_mic=True. Do not call mic_one_pole_coeff. Do not add a Structure-pole mode. Do not change the air one-pole or the air shelf (that is Phase 6, after Phase 3). Do not add the wall-tone switch. Keep the soft pole inside relative_db. One minimum-phase design from relative_db at the render sample rate — Phase 3 rebuilds it at the live rate, no second biquad. Null test: 0 dB filters match today's process_block_sum. No SciPy via mic_fitter __init__. No Mic tab UI. No Hadamard / 1/r² / Two-sources gain edits. Stop with files changed, test results, and the stock ORTF Render note (L/R direct dulls, centre nearer unchanged, makeup may barely move, L/R lows up a little then highs darken).`

**Phase 2–6:** same brief, “Phase N only.” Phase 6 only after Phase 3 has been listened to.

---

**END OF BRIEF v2.6**
