# GROK BUILD BRIEF — Surfaces material library + crazy-kit purge
### Companion handoff for Grok Build (Idle Hanz — paste entire file)
### **v1.0** — Wire 12 ASSUMED presets + role purge into the tweak app (2026-09-24)

| Field | Value |
|-------|--------|
| **Revision** | **v1.0** (2026-09-24) |
| **Canonical tree** | `C:\Users\IdleHanz\Desktop\2011 Room Reverb\` |
| **Canonical brief (this file in handoff)** | `...\handoff_surfaces_for_build\briefs\GROK_BUILD_BRIEF_Surfaces_materials_and_purge.md` |
| **Also place under docs when Idle wants** | `...\docs\GROK_BUILD_BRIEF_Surfaces_materials_and_purge.md` |
| **Solo/Mute brief (separate track)** | `...\docs\GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md` — **do not implement Solo in this brief** |
| **Material pack** | `...\surfaces_fitter\` (copied into handoff as `surfaces_fitter/`) |
| **Purge doc** | `...\findings\surfaces-crazy-kit-purge.md` (= pack `PURGE_LIST.md`) |
| **Architecture findings** | `...\findings\surfaces-multi-bounce-diffusion-solo.md` |
| **Style reference** | `...\docs\GROK_BUILD_BRIEF_Mic_tab_measured_colour.md` |
| **Live software** | `...\software\` (READ for mining; implement Surfaces materials+purge only) |
| **Owner** | Idle Hanz |
| **Architecture / locks** | Reaktor Reverb Bot |
| **Implementer** | Grok Build |

**Idle’s bar:** Clean, section-contained architecture. Prefer boring boundaries. Do not spend years fault-finding. Materials ship as one clear product behaviour — role-legal chips, no curtain-on-floor, no inventing MEASURED α.

**Revision:** v1.0 wires the **12 ASSUMED_TEXTBOOK** presets from `surfaces_fitter/presets/` into the Surfaces desk, enforces `roles` / `banned_on` (Idle pick #11 crazy-kit purge), and keeps Solo/Mute out of scope (own brief).

---

## LOCKED decisions (do not reopen without Idle)

### L0. Product gap this brief fills
**ASSUMED today:** Surfaces chips include loose Plaster / Wood / Concrete / Curtain / Carpet (and similar) that can paint Curtain/Carpet as unrestricted paint-all.

**VERIFIED pack:** `surfaces_fitter` exports **12** materials with schema `surfaces_fitter.material.v1`, `absorb[7]` at 125–8000 Hz, `roles`, `banned_on`, fit params, honesty `ASSUMED_TEXTBOOK`. Index: `presets/index.json`.

This brief replaces / role-gates those kits with the 12 presets and **enforces** purge rules. It does **not** implement panel Solo/Mute.

### L1. Honesty tag (LOCKED)
All 12 α tables are **ASSUMED_TEXTBOOK** (Sengpiel-style / typical published octave α). They are **not** Structure VERIFIED and **not** MEASURED lab product tests.

- UI / docs / comments: say ASSUMED (or ASSUMED_TEXTBOOK), never “Structure locked” or “measured ISO 354”.
- Do not claim OCR from Reaktor Structure for these tables.

### L2. Physics contract (LOCKED — product, not a fitter rewrite)
Energy absorb α(f) at octave centres; amplitude reflection:

```
R_db(f) = 20 * log10(sqrt(max(1 - α(f), 1e-6)))
```

- **One bounce:** apply R(f) for that hit’s card.
- **Multi-bounce:** **cascade** product along the hit list (serial `apply_surface_to_buffer` family — **VERIFIED** today).
- Depth / shelf params from fitter are **absolute per bounce**, not per metre (unlike air).
- Export bands for cards: `absorb[7]` @ `[125, 250, 500, 1000, 2000, 4000, 8000]` Hz.
- Keep existing early cascade family; this brief mainly **loads absorb[7]** (and optionally display names) onto cards A–F. Optional later: drive peaking stages from the same α→dB map without changing cascade topology.

### L3. Role map letter → face (LOCKED)

| Letter | Role |
|--------|------|
| A, B, C, D | **wall** |
| E | **floor** |
| F | **ceiling** |

**VERIFIED names:** A Left, B Ahead, C Right, D Behind, E Floor, F Ceiling.

### L4. Role filter + purge (LOCKED — Idle pick #11)

Each preset carries `roles: [...]` and `banned_on: [...]`. When applying a kit to a surface letter:

1. Map letter → role (L3).
2. If `role ∉ material.roles` → **skip** (grey-out / disabled chip); **do not** write absorb.
3. **Shift-paint-all** (paint-all): iterate A–F; apply only where role is legal; **must skip** illegal combos; do not invent illegal α on skipped faces.
4. UI: hide or grey-out kits illegal for the **currently selected** card.
5. **Do not delete** Floor (E) / Ceiling (F) cards — only illegal material kits on those faces.

**Hard bans (must enforce):**

| Material id | Allowed | Never on |
|-------------|---------|----------|
| `heavy_curtain` | wall | **E, F** |
| `carpet_on_concrete`, `carpet_on_foam` | floor | **A–D, F** |
| `wood_parquet` | floor | walls, ceiling |
| `glass_window`, `brick_unglazed`, `plywood_panel`, `absorber_panel_2in` | wall | floor, ceiling |
| `acoustic_ceiling_tile` | ceiling | floor, wall |
| `plaster_smooth`, `gypsum_painted` | wall, ceiling | floor (**E**) |
| `concrete_painted` | floor, wall, ceiling | _(none)_ |

**Idle unlock:** carpet on walls/ceiling stays **banned** unless Idle explicitly unlocks an advanced override (default = locked). Do not ship an unlock UI in Phase 1.

**Remove / restrict old chips:** unrestricted Curtain/Carpet paint-all; soft “studio absorbent” mega-kits that dump curtain+carpet α onto all faces. Map old labels → new ids (see purge doc mapping table).

### L5. What to load from the pack (LOCKED)

Read-only from handoff / Desktop pack (do **not** rewrite the fitter):

| Path | Use |
|------|-----|
| `surfaces_fitter/presets/index.json` | Chip list, roles, banned_on, display_name, file pointers |
| `surfaces_fitter/presets/<id>.json` | `absorb[7]`, honesty, optional fit `params` for future shelves |
| `surfaces_fitter/PURGE_LIST.md` / findings purge | Policy checklist |
| `surfaces_fitter/MORNING_REPORT.md` | RMSE / role matrix context |
| `plots/gallery_index.png`, `role_matrix.png` | Optional UI / review visuals |

**Phase 1 minimum:** load `absorb` (+ display name / id) onto the selected card when a legal chip is clicked; role-filter chips; paint-all skips illegal roles.

**Phase 1 does not require** wiring fitter `params` dual-shelf models into audio — today’s peaking/EQ path may keep writing from `absorb[7]` as now. Shipping the 12 α vectors + purge is the product win.

### L6. Solo/Mute is out of scope (LOCKED)

Panel Solo/Mute has its **own** brief: `GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md`.

- Do **not** implement Solo/Mute in this materials track.
- If Solo state already exists when materials ship later: paint / chip apply **must not** clear Solo/Mute (solo brief L8).
- Tracks may be sequential: **A = this brief**, then **B = Solo**.

### L7. Cards and cascade stay (LOCKED)

- Keep surface cards **A–F** including E/F.
- Keep serial multi-bounce cascade (**VERIFIED**).
- Keep Surfaces `D` (Δd) separate from Structure `Dffs` — **do not unify** (Δd ≠ Dffs).
- Do not wire `absorb_masks` A–F bits into audio.

### L8. Product locks that apply to ALL Surfaces work (LOCKED)

Do **not**:

- Retune unscaled Hadamard / FDN matrix
- Change geometric **1/r²** air amplitude law
- Break early **cascade** into last-hit-only
- Unify Surfaces **Δd** with Structure **Dffs**
- Edit **mic colour** package / Mic Phase hooks
- Edit **air absorption** engine toward ISO / retire Structure air one-pole (Mic brief Phase 6 ownership)
- Casually retune the **listened mix** defaults (Direct/Early/FDN wet, stock ORTF, etc.)
- Implement while researching — no live `software/` edits during research-only passes; Build implements from this brief against `software/` when Idle says go

### L9. Do-not-touch (LOCKED) — this brief’s implementation scope

- No rewrite of `surfaces_fitter/` fit math (consume presets; don’t re-fit in production)
- No Solo/Mute UI or `effective_surfaces` (other brief)
- No scattering `s` / new image paths
- No MEASURED absorption claims
- No Hadamard / mic / air collision
- No deleting cards E/F

---

## VERIFIED vs ASSUMED

| Item | Tag |
|------|-----|
| Cards A–F exist; absorb[7]; EQ shelves; diffusion D | **VERIFIED** |
| Hit names A Left … F Ceiling | **VERIFIED** |
| Early colour = serial cascade per hit letter | **VERIFIED** |
| FDN inject uses product of √(1−ᾱ); card EQ early_only today | **VERIFIED** |
| Diffusion: Surfaces D → Δd ≠ Structure Dffs | **VERIFIED** |
| No panel solo today | **VERIFIED** |
| Geometric A Left / C Right sides split | **ASSUMED** |
| 12 material α tables + fit params | **ASSUMED_TEXTBOOK** |
| Role bans (curtain≠floor/ceiling, etc.) | **ASSUMED** product policy (Idle pick #11) |
| Old chip set labels exactly | **ASSUMED** — purge by behaviour (unrestricted soft paint-all) |

---

## A. Mission

Give the Surfaces desk a **sane material library**: 12 role-tagged ASSUMED presets from `surfaces_fitter`, with crazy-kit purge so Curtain never lands on E/F and Carpet never on walls/ceiling (default). Leave Solo/Mute to the other brief. Leave mic colour and air alone.

---

## B. Phases

### Phase 0 — Inventory (short)

- List current Surfaces kit chips / paint-all paths in `software/static/js/colour_surfaces.js` (and related).
- Map each to a new id or **REMOVE/RESTRICT** per purge mapping table.
- Confirm letter→role map and paint-all entry points.

### Phase 1 — Wire presets + purge (ship)

1. Load `presets/index.json` + per-id JSON (bundle into static assets **or** read from a known Desktop/pack path Idle chooses — prefer shipping a copy under `software/static/` or `software/surfaces_materials/` so the app is self-contained; **do not** leave Build hunting the research folder at runtime without Idle’s path lock).
2. Replace / extend chip UI with the 12 display names; filter by selected card role.
3. On chip click: write that preset’s `absorb[7]` (and id/display metadata if useful) onto the selected card; leave Solo/Mute alone if present.
4. Shift-paint-all: role-skip illegal faces.
5. Remove or restrict unrestricted Curtain/Carpet paint-all chips.
6. Keep E/F cards.
7. Exit note: list chips, files changed, A/B notes; honesty ASSUMED_TEXTBOOK called out.

### Phase 2 — Optional polish

- Grey-out tooltips (“floor only”, “wall only”).
- Optional: show gallery / role_matrix thumbnail in a help drawer.
- Optional: drive peaking stages from fitter α→R_db more explicitly (same cascade).
- Align with Solo brief when both are live (paint must not clear Solo/Mute).

### Phase 3 — Out of scope here

- Solo/Mute, scattering `s`, wall_tone, MEASURED library, absorb_masks→audio, Hadamard/mic/air.

---

## C. File map (read these)

**In this handoff folder:**

```
handoff_surfaces_for_build/
  BUILD_HANDOFF.md
  README.md
  briefs/GROK_BUILD_BRIEF_Surfaces_materials_and_purge.md   ← this file
  briefs/GROK_BUILD_BRIEF_Surfaces_panel_solo_mute.md      ← Track B only
  findings/surfaces-crazy-kit-purge.md
  findings/surfaces-multi-bounce-diffusion-solo.md
  surfaces_fitter/presets/index.json
  surfaces_fitter/presets/*.json
  surfaces_fitter/PURGE_LIST.md
  surfaces_fitter/MORNING_REPORT.md
  surfaces_fitter/plots/gallery_index.png
  surfaces_fitter/plots/role_matrix.png
```

**Desktop originals (diff if needed):**

- `C:\Users\IdleHanz\Desktop\2011 Room Reverb\surfaces_fitter\`
- `C:\Users\IdleHanz\Desktop\2011 Room Reverb\findings\surfaces-crazy-kit-purge.md`
- `C:\Users\IdleHanz\Desktop\2011 Room Reverb\software\` (implement here when Idle says go)

**Likely implement touchpoints (mine, don’t thrash):**

- `software/static/js/colour_surfaces.js`
- `software/static/index.html` (Surfaces kit chrome)
- Surfaces parse / defaults if chip ids are stored in state
- **Do not** casually edit `mic_colour/`, air engine, Hadamard, `absorb_masks`→audio

---

## D. A/B listen checklist

| # | Action | Expect |
|---|--------|--------|
| 1 | Select E (Floor); try Heavy curtain chip | Disabled / no write |
| 2 | Select F; try Carpet | Disabled / no write |
| 3 | Select A; apply Heavy curtain | absorb[7] matches `heavy_curtain.json`; wall ok |
| 4 | Select E; apply Carpet on foam | absorb matches preset; floor ok |
| 5 | Shift-paint-all with Curtain | A–D get curtain; **E and F skipped** |
| 6 | Shift-paint-all with Carpet | **E only**; A–D and F skipped |
| 7 | Concrete on E then F then A | Legal all three |
| 8 | ACT on F only | Walls/floor reject |
| 9 | Null vs previous stock room **only** if defaults unchanged | Do not retune mix defaults in this brief |

---

## E. Acceptance criteria

- [ ] 12 presets available from `index.json`; honesty ASSUMED_TEXTBOOK in UI or docs note
- [ ] Role filter on selected card; paint-all skips illegal roles
- [ ] Curtain never on E/F; carpet never on A–D/F (no unlock in Phase 1)
- [ ] Cards E/F remain
- [ ] No Solo/Mute implemented from this brief
- [ ] No Hadamard / 1/r² / mic colour / air engine / listened-mix-default edits
- [ ] No claim of Structure VERIFIED α
- [ ] Cascade family unchanged (serial per-hit)

---

## F. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Shipping unrestricted soft paint-all still | **High** | L4 + purge checklist |
| Deleting E/F “to fix” curtain | High | L4 / L7 keep cards |
| Calling α MEASURED / Structure | Med | L1 honesty |
| Implementing Solo here and drifting from solo brief | Med | L6 |
| Touching mic/air “while here” | High | L8 / L9 |
| Runtime path still points at research-only folder | Med | Phase 1: bundle assets |

---

## G. Suggested Build prompt

**Phase 1:**  
`Read handoff_surfaces_for_build/BUILD_HANDOFF.md then briefs/GROK_BUILD_BRIEF_Surfaces_materials_and_purge.md (v1.0). Execute materials+purge Phase 1 only. Load the 12 ASSUMED_TEXTBOOK presets from surfaces_fitter/presets (index.json + absorb[7]). Role-filter chips (A–D wall, E floor, F ceiling). Enforce purge: curtain never E/F; carpet never A–D/F; paint-all skips illegal roles. Keep cards E/F. Do NOT implement Solo/Mute. Do NOT touch Hadamard, 1/r², mic colour, air engine, listened mix defaults, or unify Δd with Dffs. Stop with files changed, chip map, and A/B notes.`

---

**END OF BRIEF v1.0**
