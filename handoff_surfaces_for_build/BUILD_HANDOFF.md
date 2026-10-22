# BUILD HANDOFF — Surfaces (materials + Solo/Mute)

**Date:** 2026-09-24 (Europe/London)  
**Owner:** Idle Hanz  
**Implementer:** Grok Build  
**Handoff root (Desktop):** `C:\Users\IdleHanz\Desktop\2011 Room Reverb\handoff_surfaces_for_build\`  
**Box mirror:** `/workspace/handoff_surfaces_for_build/`  
**Live software (implement only when Idle says go):** `C:\Users\IdleHanz\Desktop\2011 Room Reverb\software\`

This is the **single entry doc**. Read it fully before either brief.

---

## 1. Read order

1. **This file** (`BUILD_HANDOFF.md`)
2. **`briefs/GROK_BUILD_BRIEF_Surfaces_materials_and_purge.md`** (Track A)
3. **`briefs/GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md`** (Track B)
4. **`findings/surfaces-crazy-kit-purge.md`** (+ pack `surfaces_fitter/PURGE_LIST.md`, same policy)
5. **`findings/surfaces-multi-bounce-diffusion-solo.md`** (architecture; Solo semantics are **locked in the Solo brief**, not the memo alone)
6. **`surfaces_fitter/presets/index.json`** then individual `presets/<id>.json`; skim `MORNING_REPORT.md` / `plots/gallery_index.png` / `role_matrix.png` for context

---

## 2. Product locks (apply to ALL Surfaces work)

Do **not** reopen without Idle:

| Lock | Rule |
|------|------|
| Hadamard | Keep **unscaled** FDN / matrix as today |
| Distance law | Geometric **1/r²** air amplitude unchanged |
| Early colour | **Serial cascade** of per-hit filters — not last-hit-only |
| Diffusion | Surfaces **Δd** (from card `D`) **≠** Structure **Dffs** — do not unify |
| Mic / air | **No collision** — do not rewrite mic colour or air absorption in Surfaces tracks |
| Mix | Do **not** casually retune listened mix defaults (Direct/Early/FDN wet, stock ORTF, …) |
| Bits | Do **not** wire `absorb_masks` A–F into audio |
| Honesty | Material α tables are **ASSUMED_TEXTBOOK**, not Structure VERIFIED |
| Cards | Keep Floor **E** / Ceiling **F** — purge kits, not cards |
| Research vs implement | No live `software/` edits during research-only; implement from briefs when Idle says go |

---

## 3. Two tracks (sequential OK)

### Track A — Material library + role purge

**Brief:** `briefs/GROK_BUILD_BRIEF_Surfaces_materials_and_purge.md` (v1.0 — **written for this handoff**)

**Do:**

- Load **12** presets from `surfaces_fitter/presets/` (`index.json` + `absorb[7]`)
- Role-filter chips: A–D = wall, E = floor, F = ceiling
- Enforce crazy-kit purge (Idle pick #11): Curtain **never** on E/F; Carpet **never** on A–D/F (default); paint-all **skips** illegal roles
- Replace / restrict unrestricted soft paint-all chips

**Do not (Track A):** implement Solo/Mute; touch Hadamard/mic/air; rewrite the fitter.

### Track B — Panel Solo / Mute

**Brief:** `briefs/GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md` (v1.0)

**Do:**

- Surfaces-tab Solo (exclusive A–F) + Mute (multi)
- Mute = α=1-style **no reflection colour**; keep geometry/taps
- Solo X → non-soloed faces use Mute behaviour; Direct unaffected
- Single `effective_surfaces` gate for cascade, `tap_reflect_gain`, `tap_dff`, Δd
- Play **and** Render honour Solo/Mute on existing Surfaces hooks (Phase 1)

**Do not (Track B):** implement materials library (unless already done in A); unify Δd/Dffs; mute-entire-FDN; drop taps that lack solo letter.

**Recommended order:** A then B. Paint must not clear Solo/Mute once B exists.

---

## 4. ASSUMED vs VERIFIED (summary)

| Item | Tag |
|------|-----|
| Cards A–F; absorb[7]; EQ; diffusion D; hit names | **VERIFIED** |
| Early cascade per hit; FDN inject √(1−ᾱ) product; EQ early_only | **VERIFIED** |
| Δd ≠ Dffs; no panel solo today | **VERIFIED** |
| 12 material α + fitter params | **ASSUMED_TEXTBOOK** |
| Role bans / crazy-kit purge | **ASSUMED** product policy (Idle) |
| Geometric side split A Left / C Right | **ASSUMED** |
| Solo/Mute product locks | Locked in Solo brief (Mute=α=1-style, exclusive Solo, …) |

---

## 5. File map

| Handoff path | Source / notes |
|--------------|----------------|
| `briefs/GROK_BUILD_BRIEF_Surfaces_materials_and_purge.md` | **Newly written** for this handoff (was missing under `docs/`) |
| `briefs/GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md` | Copy of `docs\GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md` |
| `findings/surfaces-crazy-kit-purge.md` | Copy of Desktop findings |
| `findings/surfaces-multi-bounce-diffusion-solo.md` | Copy of Desktop findings |
| `surfaces_fitter/**` | Full pack copy (~presets, plots, reports, PURGE_LIST, MORNING_REPORT, run_fit.py, …) |

**Desktop originals (diff):**

- `C:\Users\IdleHanz\Desktop\2011 Room Reverb\surfaces_fitter\`
- `C:\Users\IdleHanz\Desktop\2011 Room Reverb\findings\surfaces-crazy-kit-purge.md`
- `C:\Users\IdleHanz\Desktop\2011 Room Reverb\findings\surfaces-multi-bounce-diffusion-solo.md`
- `C:\Users\IdleHanz\Desktop\2011 Room Reverb\docs\GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md`

**Explicit:** Do **not** rewrite mic colour or air absorption. Do **not** touch the listened mix casually.

---

## 6. Phase order (Build)

1. Read this handoff + Track A brief → **Phase 1 materials+purge** (or Idle may ask for Track B first — honour Idle’s call; defaults to A then B).
2. Track B Solo/Mute Phase 1 per solo brief.
3. Polish / optional α→shelf drive / Solo chrome later — see briefs Phase 2+.
4. Out of scope: scattering `s`, wall_tone, MEASURED α, absorb_masks→audio, Hadamard/mic/air.

---

## 7. Paste prompt for Build

```
Point at: C:\Users\IdleHanz\Desktop\2011 Room Reverb\handoff_surfaces_for_build\

Read BUILD_HANDOFF.md first, then Track A materials+purge brief, then Track B solo/mute brief, then findings, then surfaces_fitter/presets/index.json.

Product locks for ALL Surfaces work: Hadamard unscaled; 1/r²; early cascade; Δd ≠ Dffs; no mic/air collision; no casual listened-mix retunes; material α is ASSUMED_TEXTBOOK; keep cards E/F.

Two tracks (sequential OK): A) wire 12 ASSUMED presets + crazy-kit purge from surfaces_fitter + purge doc; B) panel Solo/Mute per solo brief. Do not implement Solo inside the materials brief.

Do not rewrite mic colour or air absorption. Prefer handoff copies; Desktop originals listed in BUILD_HANDOFF if you need to diff. Implement against software/ only when Idle says go.
```

---

**END OF BUILD_HANDOFF**

---

## 8. ADDENDUM (26 Sep 2026, ~22:00 BST): Track C scattering + live Play audit

This is appended, and Tracks A and B above are unchanged. §6 item 4 ("Out of scope: scattering `s`") still holds **for Tracks A and B**. Scattering is now its own **Track C**, which comes **after A and B**, and only when Idle says go.

**Read order, continued** (after items 1–6 in §1):

7. **`findings/live_play_fix_audit.md`**: what the 26 Sep C/WASM Play rewrite actually is (VERIFIED), headroom, and **the new denormal/silence CPU risk**
8. **`briefs/GROK_BUILD_BRIEF_Surfaces_scattering.md`** (Track C): goal, locks, schema, algorithm, slots, parity, CPU, tests, A/B checklist, don'ts
9. **`findings/per_reflection_scattering_research.md`**: sources and bibliography (VERIFIED vs ASSUMED)
10. **`findings/c_wasm_performance_roadmap.md`**: shared C core for Render (ctypes) and Play (WASM), safety, test harness
11. **`scattering_fitter/REPORT.md`**, then `scattering_fitter/presets/index.json` (s[7] per material, same ids as `surfaces_fitter`)

| Track | Brief | Scope |
|-------|--------|--------|
| **C** | scattering | Per-hit specular √∏(1−s) + feed-forward Lambert velvet cluster on early taps; new card key `scatter[7]` (NOT `diffusion`); muted face = no scattering; FDN inject unchanged |

**Priority note from the audit:** fix the **denormal guard in `engine/live_stereo.c`** before adding any Play DSP. Silent tails measured 3.6–3.9 ms per 128-block on the box, against a 2.667 ms budget.
