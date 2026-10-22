# GROK BUILD BRIEF — Surfaces panel Solo / Mute
### Comprehensive handoff for Grok Build (Idle Hanz — paste entire file)
### **v1.0** — Panel Solo / Mute on the Surfaces desk (2026-09-24)

| Field | Value |
|-------|--------|
| **Revision** | **v1.0** (2026-09-24) |
| **Canonical tree** | `C:\Users\IdleHanz\Desktop\2011 Room Reverb\` |
| **Canonical brief** | `...\docs\GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md` |
| **Box mirror** | `/workspace/surfaces_solo_mute_brief/GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md` (**must stay byte-identical**) |
| **Related findings** | `...\findings\surfaces-multi-bounce-diffusion-solo.md`, `...\findings\surfaces-crazy-kit-purge.md`, `...\findings\diffusion-two-layers.md` |
| **Style reference** | `...\docs\GROK_BUILD_BRIEF_Mic_tab_measured_colour.md` (locks / VERIFIED vs ASSUMED / phases / A/B) |
| **Live software** | `...\software\` (READ for mining; implement only the Surfaces Solo/Mute scope below) |
| **Material pack** | `...\surfaces_fitter\` — **context only; do not rewrite the fitter** |
| **Owner** | Idle Hanz |
| **Architecture / locks** | Reaktor Reverb Bot |
| **Implementer** | Grok Build |

**Idle’s bar:** Clean, section-contained architecture. Prefer boring boundaries. Do not spend years fault-finding. Solo/Mute must ship as one clear product behaviour — **no ambiguous “or” left for Build to invent.**

**Revision:** v1.0 locks Mute = α=1-style full absorb (no reflection colour), exclusive Solo that forces non-soloed faces to the same Mute behaviour, Play+Render parity in Phase 1, Direct untouched, FDN inject ᾱ using effective (solo/mute-aware) cards, and no unification of Surfaces Δd with Structure Dffs.

---

## LOCKED decisions (do not reopen without Idle)

### L0. Product gap this brief fills
**VERIFIED:** There is **no panel Solo / Mute today** (`findings/surfaces-multi-bounce-diffusion-solo.md`; `static/js/colour_surfaces.js` has edit-select only; Mix-desk Solo/Mute in `app.js` is bus Solo, not Surfaces).

This brief adds **Surfaces-tab-only** audition controls: exclusive **Solo face A–F** and multi **Mute face A–F**.

### L1. Mute face = α=1-style full absorb (LOCKED)

**Mute** on face X means face X contributes **no reflection colour** while geometry and image timing stay intact.

For every audio path that already consults that card:

| Path | Mute behaviour | Honesty |
|------|----------------|---------|
| Early cascade `apply_surface_to_buffer` / `surface_filter_stages` | Skip absorb peaking **and** EQ stages for letter X (identity for that hit) | VERIFIED call sites in `surface_colour.py` / `render_pipeline.py` |
| FDN inject `tap_reflect_gain` | That hit multiplies gain by **0** (full absorb — do **not** rely on the normal-card `min(0.95, ᾱ)` clamp, which would still pass ~√0.05) | VERIFIED `tap_reflect_gain` clamp at `render_pipeline.py` |
| Surfaces Δd `jittered_distance` | That letter’s `diffusion` term = **0** | VERIFIED `jittered_distance` reads per-card `diffusion` |
| Structure Dffs via `tap_dff` | That letter adds **0** to the Dif sum | VERIFIED `tap_dff` |

**Do not** delete the image tap. **Do not** remove the letter from `surfaces_hit_by_n`. Geometry stays; the panel acoustically disappears.

**Multiple mutes allowed.** Mute is independent of edit-selection.

### L2. Solo face = exclusive radio; non-soloed faces use Mute behaviour (LOCKED)

When **Solo X** is active:

1. Face X keeps its **normal** absorb / EQ / diffusion (unless X is also muted — see L3).
2. Every other face A–F behaves exactly as **Mute** (L1).
3. **Direct** (`n=(0,0,0)`, Mix Direct spikes) is **unaffected** by Surfaces Solo/Mute. **VERIFIED:** Direct has no surface hits (`surfaces_hit_by_n((0,0,0))` → `[]`).
4. **Do not** filter the early tap list to “hits containing X only.” That alternative was floated in the findings memo and is **REJECTED** here. Keep all taps; colour them with effective cards. Timing / 1/r² / air stay.

Clearing Solo restores each face to its own Mute state (mutes persist).

### L3. Solo + Mute interaction (LOCKED)

- **Solo on a muted face clears Mute on that face** and engages Solo (DAW-like: Solo wins for audition).
- Engaging Mute on the currently soloed face **clears Solo** and leaves that face Muted (and other faces return to their mute flags — no auto-solo of another face).
- Illegal / error-toast states are **not** used. One click always yields a legal state.

### L4. FDN inject ᾱ under Solo/Mute (LOCKED — musically honest)

**VERIFIED today:** FDN inject uses the product of `√(1−ᾱ)` per geometric hit (`tap_reflect_gain`); card EQ is `early_only` on early buffers only (`apply_surface_to_buffer`). Mic brief L10 documents `wall_tone`; default stays `early_only`.

**Lock:** Solo/Mute builds **one effective surfaces dict** (or equivalent per-letter gate) shared by:

- `tap_reflect_gain` (Play `live_fdn_params` **and** Render)
- `tap_dff`
- `jittered_distance` / early cascade

Non-soloed / muted faces contribute **full absorb (×0 reflection)** to the inject product — **not** the pre-solo room mean. Early and FDN therefore agree on which panels still colour the room. Do **not** mute the entire FDN inject when Solo is active (that findings alternative is **REJECTED** — it would silence the tail instead of soloing a panel’s colour).

**Do not** retune the unscaled Hadamard matrix. **Do not** invent `wall_tone` / `per_trip` in this brief.

### L5. Diffusion layers stay two (LOCKED)

**VERIFIED:** Surfaces `D` → seeded `Δd` path jitter ≠ Structure `Dffs` from `tap_dff` (`findings/diffusion-two-layers.md`). Solo/Mute may zero a muted face’s contribution to **both** layers independently; it must **not** unify Δd with Dffs or rename `D` to scattering.

### L6. Play and Render both honour Solo/Mute in Phase 1 (LOCKED)

Unlike Mic Phase 1 (Render-only), Surfaces Solo/Mute is an audition control that must match ears on **Play and Render** from Phase 1:

- **VERIFIED:** `live_fdn_params` already applies `tap_reflect_gain` and `tap_dff` from `parse_surfaces` — Play FDN inject/Dffs see effective cards once Solo/Mute is folded into that parse (or a single `effective_surfaces()` helper called from both Render and live params).
- **VERIFIED:** Render early cascade uses `apply_surface_to_buffer` after hits — must see the same effective cards.
- **ASSUMED / gap:** Play live may not run the early absorb×EQ biquad cascade today (card EQ is Render `render_early_ir`). Phase 1 does **not** invent Play early card EQ. It only applies Solo/Mute wherever Surfaces already affect audio. Document the gap in the Phase 1 exit note.

### L7. UI ownership (LOCKED)

- Controls live on the **Surfaces** desk only (`#surfacesPanel` / surface cards / room net).
- **Do not** put Surfaces Solo/Mute on Floor, Mic, Mix bus strips, or Lattice.
- Mix-desk bus Solo/Mute (`solo_direct` / `mute_fdn` etc. in `app.js`) stays unrelated.
- Edit-select (which card’s sliders you paint) stays as today; Solo/Mute is audition state, not a replacement for selection.

### L8. State / persistence (LOCKED)

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| `surfaces_solo` | `null` or one of `A`–`F` | `null` | Exclusive. Missing → null. |
| `surfaces_mute` | object `{A:bool,…F:bool}` **or** list of muted letters | all false / `[]` | Multi. Missing → none muted. |

- Stored beside `state.surfaces` in the client; POSTed on Render and `/api/live_params` like other params.
- **Server:** `params_from_body` / `parse_surfaces` path must accept the new keys; absent keys = defaults (no solo, no mutes). Do not require the page to send them for “no audition” behaviour.
- **Material chip / Shift-paint-all:** updates absorb/EQ/diffusion only — **does not** clear Solo/Mute.
- **Room / surfaces reset to defaults:** clears Solo and all Mutes.
- Per-card JSON may optionally carry `mute: bool` for display sync; canonical audition state remains the top-level keys above so Solo stays exclusive without six competing flags.

### L9. Early cascade family stays serial (LOCKED)

**VERIFIED:** Early colour is a serial cascade of per-hit filters (`surface_filter_stages` loops hit letters). Correct for specular paths. Solo/Mute only changes **which** hit letters contribute filters (muted → skip); it does **not** switch to last-hit-only or average-EQ.

### L10. Do-not-touch (LOCKED)

Do **not** in this brief’s implementation scope:

- Change unscaled ±1 Hadamard / FDN matrix
- Change geometric `1/r²` air amplitude law
- Edit mic colour package / Mic Phase hooks / `mic_colour/*`
- Edit air absorption engine files toward ISO / retire Structure air one-pole (Mic L9 / Phase 6)
- Unify Surfaces Δd with Structure Dffs
- Wire `engine/absorb_masks.py` A–F bits into audio
- Invent MEASURED absorption or rewrite `surfaces_fitter/`
- Add scattering `s` / new image paths
- Build Mic L10 `wall_tone` switch
- Claim Structure-locked Surface EQ dictionary

---

## Ambiguities resolved (v1.0 — Idle product locks)

| Topic | Locked side |
|-------|-------------|
| Mute meaning | α=1-style **no reflection colour**; geometry kept; EQ skipped; D=0 for that face on Δd and Dffs |
| Solo non-soloed faces | Same as Mute (not “bypass identity with full reflection”) |
| Solo tap filtering | **Rejected** — do not drop taps lacking X |
| FDN under Solo | Effective ᾱ / ×0 on muted hits — **not** mute-entire-FDN; **not** keep pre-solo room mean |
| Solo + Mute | Solo clears Mute on that face; Mute on soloed face clears Solo |
| Direct | Unaffected |
| Play vs Render | **Both** honour in Phase 1 (Surfaces paths that already exist) |
| Diffusion layers | Stay two; Solo/Mute zeros muted contributions only |
| UI home | Surfaces tab only |
| Materials library | Not a Phase 1 dependency; works with current chips |
| `tap_reflect_gain` 0.95 clamp | Normal cards keep clamp; muted hits short-circuit to ×0 |

---

## A. Mission

Give Idle a Surfaces-desk **Solo face** and **Mute face** so each of A–F can be auditioned or silenced for colour without redesigning the room engine.

Success: Idle solos Floor (E), hears early+FDN colour that still carries E and treats other faces as full absorb; mutes Curtain-painted walls; Direct stays put; Hadamard / 1/r² / mic / air untouched; Play matches Render on inject/Dffs (and Render early cascade).

---

## B. Non-goals

- Do not ship the full `surfaces_fitter` material library or crazy-kit purge as a prerequisite (reference roles only).
- Do not rewrite absorb→dB mapping or invent MEASURED α tables.
- Do not change Mix bus Solo/Mute semantics.
- Do not add “Solo All” as a seventh radio that means something other than clearing Solo (a **Solo Off / All** control that sets `surfaces_solo=null` is fine).
- Do not silently change listened wet defaults (`early_wet` / `fdn_wet` / `direct_wet`).
- Do not touch Mic or Air implementation files in this pass.

---

## C. Current behaviour (mined 2026-09-24 against Desktop)

| Piece | Where | Honesty | Role after this brief |
|-------|--------|---------|------------------------|
| Cards A–F | `surface_colour.py` `SURFACE_LETTERS`, `default_surface`; UI `colour_surfaces.js` | VERIFIED desk (ASSUMED α/EQ values) | Unchanged fields + audition gates |
| Hit letters | `surfaces_hit_by_n` | ASSUMED geometric; B/D/E/F names VERIFIED | Unchanged |
| Early colour | `apply_surface_to_buffer` ← `surface_filter_stages` serial | VERIFIED cascade | Skip stages for muted/effective-muted letters |
| Absorb→dB | `_absorb_to_db`: \|R\|=√(1−α) | ASSUMED mapping | Keep; Mute short-circuits instead of fighting clamp |
| FDN inject | `tap_reflect_gain` product √(1−ᾱ); `live_fdn_params` + Render | VERIFIED | Use effective cards; muted hit ×0 |
| Card EQ on FDN | early_only today | VERIFIED | Unchanged |
| Δd jitter | `jittered_distance` / per-card `diffusion` | ASSUMED roughness | Muted letter D=0 |
| Dffs | `tap_dff` sum of hit Dif × master | VERIFIED Structure-ish path | Muted letter adds 0 |
| Panel Solo | — | VERIFIED absent | **Add** |
| Material chips | Plaster/Wood/Concrete/Curtain/Carpet in UI | ASSUMED | Paint ignores Solo/Mute state |
| Mix Solo/Mute | `app.js` bus solos | VERIFIED unrelated | Do not reuse for Surfaces |

---

## D. Architecture (contained)

```
UI Surfaces desk (Solo radio + Mute toggles)
        │
        ▼
state.surfaces_solo / state.surfaces_mute  ──► POST body (Render + /api/live_params)
        │
        ▼
effective_surfaces(raw_surfaces, solo, mute)   # single helper — boring boundary
        │
        ├── surface_filter_stages / apply_surface_to_buffer   (Render early)
        ├── tap_reflect_gain                                 (Render + Play inject)
        ├── tap_dff                                          (Render + Play Dffs)
        └── jittered_distance                                (where already called)

UNTOUCHED: Hadamard, 1/r², mic_colour, air engine, absorb_masks→audio, surfaces_fitter
```

### D.1 Helper contract

```text
effective_surfaces(surfaces, solo: Optional[str], mute: Set[str]) -> Dict[str, card]

For each letter L in A–F:
  if L in mute or (solo is not None and L != solo):
      card' = copy with absorb=[1]*7, eq gains 0, diffusion=0, muted=True
  else:
      card' = card as authored
```

`tap_reflect_gain`: if `card.get("muted")` or explicit gate → multiply by `0.0` for that hit (before/instead of √(1−ᾱ)).

`surface_filter_stages`: if muted → `continue` (no peaking, no EQ).

### D.2 UI spec (Phase 1)

Per surface card (and optionally mirrored on room-net face buttons):

- **Mute** toggle (`aria-pressed`) — multi.
- **Solo** toggle — exclusive; turning on Solo X turns off Solo on others.
- **Solo Off** control (panel header or “All”) sets `surfaces_solo=null`.
- Visual: soloed card **highlighted**; muted card **dimmed** (`is-solo` / `is-muted` classes). When Solo is active, non-soloed cards show muted styling even if their mute flag is false (effective mute).
- Hint line: `Solo E · others α=1` / `Mute A,C` — short, Surfaces panel only.
- Do not clutter Floor/Mic.

### D.3 API / schema

- Extend POST bodies already carrying `surfaces` with `surfaces_solo` and `surfaces_mute`.
- `GET /api/surfaces` may document defaults (`solo: null`, `mute: {}`); no new route required in Phase 1.
- `parse_surfaces` stays responsible for absorb/EQ/D; add `parse_surfaces_audit(solo, mute)` or fold into `params_from_body` then call `effective_surfaces` once before Render / live_fdn_params.

---

## E. File touch list

| Area | Files | Action |
|------|--------|--------|
| Helper | `software/surface_colour.py` (preferred) **or** thin helper used by `render_pipeline.py` | `effective_surfaces` + mute short-circuit docs |
| Reflect / Dff | `software/render_pipeline.py` | `tap_reflect_gain` / `tap_dff` / early path use effective cards; `live_fdn_params` same |
| UI | `software/static/js/colour_surfaces.js`, `static/index.html`, `static/css/app.css` | Solo/Mute controls + classes |
| State | `software/static/js/app.js` | defaults, reset, POST fields |
| API | `software/app_server.py` | parse new keys in `params_from_body` |
| Tests | `software/tests/` (new small test) | muted hit → reflect gain 0; solo E → only E stages; Direct gain 1 |

**Do not edit:** `engine/fdn.py` Hadamard core, `mic_colour/*`, air fitter integration, `surfaces_fitter/*`, `engine/absorb_masks.py` audio wiring.

---

## F. Phases

### Phase 1 — Minimal shippable Solo + Mute (this session)

1. Add `surfaces_solo` / `surfaces_mute` state + POST parse (defaults = off).
2. Implement `effective_surfaces` + mute ×0 in `tap_reflect_gain`; skip muted stages in cascade; D=0 for muted in `tap_dff` / jitter.
3. Wire helper into Render early + FDN inject paths **and** `live_fdn_params` (Play).
4. Surfaces UI: six Mute + exclusive Solo + Solo Off; highlight/dim.
5. Reset-to-defaults clears audit state; material paint does not.
6. Unit tests for L1/L2/L4.
7. **A/B listen** (below). Both Play and Render.

**Exit:** Idle can solo one face and mute others; Direct unchanged; no Hadamard/mic/air edits; Phase 1 exit note mentions Play early card-EQ gap if still present.

### Phase 2 — Polish (later)

- Room-net Solo/Mute chrome parity; keyboard; persistence in saved scenes if/when scene IO exists.
- Optional sparkline that shows **effective** cumulative path under Solo.
- Align with materials role-filter brief when that ships (paint still must not clear Solo/Mute).

### Phase 3 — Out of scope here

- Scattering `s`, wall_tone switch, MEASURED α from fitter, absorb_masks→audio.

---

## G. A/B listen checklist

Use a bright transient (click / snare) and a sustained source. Stock room ORTF OK.

| # | Action | Expect |
|---|--------|--------|
| 1 | All Solo Off, no Mutes — Render vs today’s file | Null / near-null (no audition state) |
| 2 | Mute all six A–F | Early surface colour gone; FDN inject reflect→0 on all hit lines; Direct intact; room much drier/darker in wet |
| 3 | Solo **E** (Floor) only | Colour of floor card audible on paths that hit E; other faces silent for colour; Direct intact; FDN still present but only E’s absorb in the product for E hits (other hits ×0) |
| 4 | Solo **A** then Solo **C** | Exclusive: only one Solo lit; timbre flips with Left vs Right ASSUMED split |
| 5 | Mute **E**, then Solo **E** | Mute clears on E; Solo engages; E audible again |
| 6 | Solo **E**, then Mute **E** | Solo clears; E muted; no face auto-soloed |
| 7 | Paint Curtain on A while Solo E | Paint does not clear Solo; A still effective-muted under Solo E |
| 8 | Play vs Render with Solo E | Inject/Dffs agree; call out if Play early EQ still missing |
| 9 | Mix bus Solo FDN with Surfaces Solo E | Independent; both may apply |

---

## H. Out of scope / hand to Reaktor Reverb Bot

- Whether Structure ever had panel solo (research) — product lock above stands regardless.
- Wall-tone `per_trip` / `on_exit` (Mic brief L10).
- Unifying Δd with Dffs.
- Shipping surfaces_fitter MEASURED library / crazy-kit purge enforcement (separate brief; Solo must not wait).
- Any Hadamard / OCR A–F bit audio claim.

---

## I. Acceptance criteria

- [ ] Brief locks have **no unresolved “or”** for Mute vs bypass, FDN ᾱ, or Solo+Mute.
- [ ] `effective_surfaces` (or equivalent) is the single gate for cascade, reflect gain, Dffs, Δd.
- [ ] Muted hit → inject reflect contribution **0** (not √(1−0.95)).
- [ ] Solo exclusive; Mute multi; L3 interaction.
- [ ] Direct unaffected (fixture).
- [ ] Play + Render both use effective cards on existing Surfaces hooks.
- [ ] UI on Surfaces tab only; visual solo highlight / mute dim.
- [ ] Defaults: no solo, no mutes; reset clears; paint does not clear.
- [ ] No edits to Hadamard, 1/r² law, mic_colour, air engine retirement, surfaces_fitter rewrite, absorb_masks→audio.
- [ ] A/B checklist items 1–6 pass by ear; 7–9 noted.

---

## J. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Using α=1 through 0.95 clamp → mute still leaks | **High** | L1 short-circuit ×0 |
| Dropping taps under Solo → timing holes | High | L2 keep taps |
| Mute entire FDN on Solo → “solo” is just dry early | High | L4 effective ᾱ |
| Play≠Render because only Render early cascade updated | Med | L6 wire `live_fdn_params`; document early-EQ gap |
| Solo UI on Mix desk confuses bus Solo | Med | L7 Surfaces only |
| Paint-all clears Solo mid-listen | Med | L8 paint ignores audit |
| Touching mic/air “while here” | High | L10 |

---

## K. Reference paths

- Software: `C:\Users\IdleHanz\Desktop\2011 Room Reverb\software\`
- Surfaces colour: `software\surface_colour.py`
- Pipeline: `software\render_pipeline.py` (`tap_reflect_gain`, `tap_dff`, `apply_surface_to_buffer`, `live_fdn_params`)
- UI: `software\static\js\color_surfaces.js`, `software\static\index.html`
- Findings: `findings\surfaces-multi-bounce-diffusion-solo.md`
- Mic style brief: `docs\GROK_BUILD_BRIEF_Mic_tab_measured_colour.md`
- Launch: `CLICK ME - Open Tweak App.bat` → http://127.0.0.1:7860

---

## L. Suggested Build prompt

**Phase 1:**  
`Read docs/GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md (v1.0). Execute Phase 1 only. Add surfaces_solo (null|A–F) and surfaces_mute; implement effective_surfaces; Mute = no reflection colour (skip EQ/absorb stages; tap_reflect_gain ×0 for muted hits; D=0 on Δd and tap_dff). Solo X = exclusive; non-soloed faces use Mute behaviour; keep all taps; Direct unaffected; FDN inject uses effective cards (not room-mean, not mute-entire-FDN). Wire Render early + live_fdn_params. Surfaces-tab UI only. Do not touch Hadamard, 1/r², mic_colour, air engine, surfaces_fitter, absorb_masks→audio, or unify Δd with Dffs. Stop with files changed, tests, and A/B notes.`

---

**END OF BRIEF v1.0**
