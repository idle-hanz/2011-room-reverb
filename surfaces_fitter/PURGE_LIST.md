# Surfaces crazy-kit purge list (Idle pick #11)

**Canonical Desktop copy:**  
`C:\Users\IdleHanz\Desktop\2011 Room Reverb\findings\surfaces-crazy-kit-purge.md`

**Honesty:** Role rules are product policy (ASSUMED sanity). Material α tables are
`ASSUMED_TEXTBOOK`. Do **not** delete Floor (E) / Ceiling (F) surface cards — only
illegal material kits on those faces.

---

## Current UI chips to REMOVE or RESTRICT

Any Surfaces kit chip that paints **Curtain** or **Carpet** (or similar soft kits)
as an **unrestricted paint-all** must be removed or role-gated:

| Old / loose chip (label) | Action | Reason |
|--------------------------|--------|--------|
| Curtain / Heavy curtain / Drape (paint-all) | **RESTRICT** → wall-only | Curtains are not floors or ceilings |
| Carpet / Rug / Carpeted (paint-all) | **RESTRICT** → floor-only | Carpet is a floor finish |
| Soft absorbent / “Studio soft” mega-kit | **REMOVE** or split | Often dumped curtain+carpet α onto all faces |
| Generic “Absorber” without role | **RESTRICT** | Map to `absorber_panel_2in` (wall) or ACT (ceiling) |

Keep hard / multi-role chips if present (plaster, gypsum, concrete) — they already
pass role filters.

---

## Hard bans (Build must enforce)

| Material id | Allowed roles | Banned faces | Cards |
|-------------|---------------|--------------|-------|
| `heavy_curtain` | wall | **floor, ceiling** | Never on **E** or **F** |
| `carpet_on_concrete` | floor | **wall, ceiling** | Never on A–D or **F** |
| `carpet_on_foam` | floor | **wall, ceiling** | Never on A–D or **F** |
| `wood_parquet` | floor | wall, ceiling | Floor only |
| `glass_window` | wall | floor, ceiling | Walls only |
| `brick_unglazed` | wall | floor, ceiling | Walls only |
| `plywood_panel` | wall | floor, ceiling | Walls only |
| `absorber_panel_2in` | wall | floor, ceiling | Walls only |
| `acoustic_ceiling_tile` | ceiling | floor, wall | Ceiling (**F**) only |
| `plaster_smooth` | wall, ceiling | floor | Not on **E** |
| `gypsum_painted` | wall, ceiling | floor | Not on **E** |
| `concrete_painted` | floor, wall, ceiling | _(none)_ | Legal everywhere |

**Idle unlock:** carpet on walls/ceiling stays banned unless Idle explicitly unlocks
an advanced override (default = locked).

---

## Role filter rules for Build

1. Each material preset carries `roles: [...]` and `banned_on: [...]`.
2. When applying a kit to a surface letter:
   - Map letter → role: `A,B,C,D → wall`, `E → floor`, `F → ceiling`.
   - If `role ∉ material.roles` → **skip** (or show disabled chip); do not write absorb.
3. **Shift-paint-all** (or paint-all):
   - Iterate A–F; for each letter, apply only if role is legal.
   - **Must skip illegal role combos** (e.g. curtain skips E and F; carpet skips A–D and F).
   - Do not partially invent illegal α on skipped faces.
4. UI: hide or grey-out kits that are illegal for the **currently selected** card.
5. Do **not** delete cards E/F themselves — empty / previous legal material stays.

---

## Mapping: old chip → new material ids

| Old chip (approx. label) | New `surfaces_fitter` id | Notes |
|--------------------------|--------------------------|-------|
| Plaster / Smooth plaster | `plaster_smooth` | wall, ceiling |
| Drywall / Gypsum / Painted gypsum | `gypsum_painted` | wall, ceiling |
| Brick | `brick_unglazed` | wall |
| Concrete / Painted concrete | `concrete_painted` | all faces |
| Wood floor / Parquet / Hardwood | `wood_parquet` | floor |
| Plywood / Panel / Wood panel | `plywood_panel` | wall |
| Carpet (thin / on slab) | `carpet_on_concrete` | floor |
| Carpet (thick / padded) | `carpet_on_foam` | floor |
| Glass / Window | `glass_window` | wall |
| Ceiling tile / ACT / Acoustic tile | `acoustic_ceiling_tile` | ceiling |
| Absorber / Foam panel / 2″ panel | `absorber_panel_2in` | wall |
| Curtain / Drape / Velour / Heavy curtain | `heavy_curtain` | wall **only** |

Preset files: `surfaces_fitter/presets/<id>.json`  
Schema: `surfaces_fitter.material.v1`  
Absorb bands: `[125,250,500,1000,2000,4000,8000]` → `absorb[7]`.

---

## What stays

- Surface cards **A–F** (including Floor **E** and Ceiling **F**).
- Per-card absorb sliders / EQ / diffusion (ASSUMED desk).
- Multi-bounce cascade of legal materials along the hit list.

## What goes

- Unrestricted Curtain/Carpet paint-all.
- Any kit that writes carpet α onto walls/ceiling or curtain α onto floor/ceiling
  without an Idle unlock.

---

## Checklist for Build

- [ ] Load presets from `surfaces_fitter/presets/index.json` (read-only pack).
- [ ] Role-filter chips by selected letter.
- [ ] Shift-paint-all skips illegal roles.
- [ ] Curtain never lands on E/F; carpet never on A–D/F (unless unlock).
- [ ] No edits that change listened mix defaults.
- [ ] No claim of Structure VERIFIED for these α tables.
