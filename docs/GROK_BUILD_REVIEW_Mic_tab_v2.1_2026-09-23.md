# Grok Build read-only review — Mic tab measured colour (second pass, v2.1)
### Archived 2026-09-23 for audit (Idle Hanz)

| Field | Value |
|-------|--------|
| **Date** | 2026-09-23 |
| **Source** | Grok Build — second read-only architecture review of brief **v2.1** |
| **Status** | Archived as Idle pasted via Reaktor Reverb Bot; Idle decisions locked into brief **v2.2** |
| **Follow-up** | Folded into brief **v2.2** |
| **Prior archive** | `docs\GROK_BUILD_REVIEW_Mic_tab_2026-09-23.md` (v1 → v2) |
| **Tree** | `C:\Users\IdleHanz\Desktop\2011 Room Reverb\` |

**Exact Desktop symbols (keep verbatim — do not invent):** `offaxis_shelf_gain_linear`, `MIC_OFFAXIS_SHELF_DB = -6.0`; `relative_db`, `MODEL_NAME = "dual_shelf_plus_soft_one_pole"`; `LIVE_DIRECT_FOLD = 0.55`; `early_wet: 0`, `direct_wet: 1`, `fdn_wet: 1`; `mic_one_pole_coeff`, `apply_capsule_colour` (dead), `direction_angles` (radians); `gradient_hp_hz`, `beaming_lp_hz`; `POST /api/colour` = IR spectrum (do not reuse for presets).

Decisions Idle locked live in brief **v2.2** LOCKED / Ambiguities-resolved / Phase 1 / tests / risks. Text below is the Build feedback Idle accepted (paraphrased cleanly for archive; product code untouched).

---

## Second review of brief v2.1 — findings Idle accepted

### L0 migration / boot vs fixture
- Boot scene remains **ORTF ±55°**.
- Mix Direct is **uncoloured today**; applying Measured colour on Direct at ~55° **changes the listened file** vs today — expected under REPLACE, not a regression to paper over.
- “On-axis level ≈ today” is a **fixture**, not the boot scene. Do not treat stock ORTF as the on-axis loudness proof.
- Preset load may set `family_*` / `polar_*` only; must **not** write yaw / space / `mic_setup`.

### Default preset
- Default Measured preset id = **SM57** (not an ASSUMED cardioid proxy).
- Thread three preset ids all = SM57 at Phase 1.

### Phase 1 A/B contract
- Phase 1 A/B = **Render only**.
- Play live keeps today’s −6 dB shelf until **Phase 3**. Do not use Play as the A/B.
- A/B reference mode = **ASSUMED_TOYS** (today’s FDN shelf), **not** BYPASS.
- BYPASS = pattern-only, shelf off, fitter off.

### L8 mode list (shelf vs makeup)
- Every mode **except** `ASSUMED_TOYS` builds inject scalars **without** `offaxis_shelf_gain_linear`. Makeup uses those pre-colour scalars.
- `ASSUMED_TOYS` alone restores the old shelf and must **NOT** leave the fitter on the Direct spike.
- **STRUCTURE** mode must strip the shelf too (align matrix with L8).

### Early toys
- Gate `gradient_hp_hz` and `beaming_lp_hz` **off** unless mode is `ASSUMED_TOYS`.

### SciPy / import graph
- Do **not** import `mic_fitter` through package `__init__` (pulls SciPy).
- Port goldens into software tests, or load `model.py` alone.
- Importable paths: outer folder on path → `mic_fitter.model`; repo root → `mic_fitter.mic_fitter.model` (package at `mic_fitter/mic_fitter/`).

### Moving path
- Moving renders use the **same colour helper** as `combined_ir` (still path).

### Phase 1 exit
- Report **stock ORTF Render Direct+FDN vs today**.
- Moving path same helper.
- Play keeps shelf until Phase 3.

### Tests (called out for brief fold)
- Test 1: default preset **SM57**; colour is `relative_db` not −6 shelf on Direct and FDN inject.
- A/B against ASSUMED_TOYS via Render; on-axis via fixture.

### Risks Idle accepted as known phase risks (High)
- **(a)** Stock ORTF Direct will dull vs today (Direct uncoloured today; filtering at ~55°).
- **(b)** Play ≠ Render until Phase 3 — called out so Idle does not treat as broken hook.

### Med risks (also folded)
- STRUCTURE mode must strip shelf too (align matrix with L8).
- Early toys still on under non-ASSUMED modes.
- SciPy import via package `__init__`.
- Moving helper miss.

---

## Idle locks baked into brief v2.2 (authoritative summary)

1. Default Measured preset id = **SM57**; pattern map must not rewrite yaw/space/mic_setup on preset load.
2. “On-axis level ≈ today” is a **fixture**, not boot; boot is ORTF ±55°; Phase 1 exit reports stock ORTF Direct+FDN vs today.
3. Phase 1 A/B = **Render only**; Play keeps −6 dB shelf until Phase 3.
4. A/B reference = **ASSUMED_TOYS**; BYPASS = pattern-only / shelf off / fitter off.
5. L8: every mode except ASSUMED_TOYS strips shelf; ASSUMED_TOYS restores shelf and must not leave fitter on Direct.
6. Gate early `gradient_hp_hz` / `beaming_lp_hz` off unless ASSUMED_TOYS.
7. No SciPy via package `__init__`; port goldens or load `model.py` alone.
8. Moving renders share the still-path colour helper.

---

**END OF REVIEW ARCHIVE (second pass, v2.1 → v2.2)**
