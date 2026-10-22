# Surfaces handoff for Grok Build

**What this is:** One folder with **all current Surfaces work** Idle needs Build to review/implement — material library + crazy-kit purge, panel Solo/Mute, architecture findings, and the `surfaces_fitter` pack.

**Audience:** Grok Build (implementer). Idle points Build at this folder.

**Created:** 2026-09-24 (Europe/London)

**Do not** treat this folder as live `software/`. Prefer the Desktop absolute paths below if you need to diff originals. **Do not** edit live engine/static while researching.

---

## Read order (mandatory)

1. **`BUILD_HANDOFF.md`** — priorities, locks, file map, Phase order, ASSUMED vs VERIFIED
2. **`briefs/GROK_BUILD_BRIEF_Surfaces_materials_and_purge.md`** — Track A (presets + purge)
3. **`briefs/GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md`** — Track B (Solo/Mute)
4. **`findings/`** — architecture + purge policy detail
5. **`surfaces_fitter/presets/`** — the 12 ASSUMED presets (`index.json` first)

---

## Layout

```
handoff_surfaces_for_build/
  README.md                 ← you are here
  BUILD_HANDOFF.md          ← single entry doc
  briefs/
    GROK_BUILD_BRIEF_Surfaces_materials_and_purge.md
    GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md
  findings/
    surfaces-crazy-kit-purge.md
    surfaces-multi-bounce-diffusion-solo.md
  surfaces_fitter/          ← full pack copy (presets, plots, reports, PURGE_LIST, …)
```

---

## Two implementation tracks

| Track | Brief | Scope |
|-------|--------|--------|
| **A** | materials + purge | Wire 12 ASSUMED presets; role filter; crazy-kit purge |
| **B** | panel solo/mute | Surfaces Solo A–F + Mute; `effective_surfaces`; Play+Render |

Tracks may be **sequential** (A then B recommended). **Do not** implement Solo inside the materials brief.

---

## Desktop / box paths

| Role | Path |
|------|------|
| **This handoff (Desktop)** | `C:\Users\IdleHanz\Desktop\2011 Room Reverb\handoff_surfaces_for_build\` |
| **Box mirror** | `/workspace/handoff_surfaces_for_build/` |
| Original fitter | `C:\Users\IdleHanz\Desktop\2011 Room Reverb\surfaces_fitter\` |
| Live app (implement when Idle says go) | `C:\Users\IdleHanz\Desktop\2011 Room Reverb\software\` |

---

## Hard product locks (all Surfaces work)

- Hadamard **unscaled**
- Geometric **1/r²**
- Early colour = **cascade** (not last-hit-only)
- Surfaces **Δd ≠** Structure **Dffs**
- **No** mic colour / air absorption collision
- **No** casual listened-mix retunes
- Material α = **ASSUMED_TEXTBOOK** (not Structure VERIFIED)

---

## Paste for Build (short)

See the closing paragraph in `BUILD_HANDOFF.md`.

---

## Addendum (26 Sep 2026, ~22:00 BST): Track C

**Read order, continued** (after items 1–5 above; full list in `BUILD_HANDOFF.md` §8):

6. **`findings/live_play_fix_audit.md`**: audit of the C/WASM Play fix (VERIFIED) + denormal risk
7. **`briefs/GROK_BUILD_BRIEF_Surfaces_scattering.md`**: **Track C** (scattering)
8. **`findings/per_reflection_scattering_research.md`**: sources and bibliography
9. **`findings/c_wasm_performance_roadmap.md`**: CPU roadmap
10. **`scattering_fitter/`**: `REPORT.md`, `presets/`, `plots/`, `proto/`, `bench/`

| Track | Brief | Scope |
|-------|--------|--------|
| **C** | scattering | Per-hit s(f) split, feed-forward clusters on early taps only; after A and B |

New layout entries: `briefs/GROK_BUILD_BRIEF_Surfaces_scattering.md`, `findings/{live_play_fix_audit,per_reflection_scattering_research,c_wasm_performance_roadmap}.md`, `scattering_fitter/`.
