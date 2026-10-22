# Master parameter list

Written 27 Sep 2026 (BST). The full table is in **`parameters.csv`** (156 rows). This file explains it, maps controls to tabs, and lists the conflicts.

**Sources**

- `app_server.py` `DEFAULTS` + `params_from_body` (:257)
- `static/js/app.js` state, `static/index.html`
- `render_pipeline.py` `live_fdn_params` (:1347), which is what Play actually receives
- `surface_colour.py`, `engine/fdn.py`
- all pending briefs (surfaces A/B/C, source radiation, air_fitter, mic brief)

Everything is from the snapshot at `planning/snapshot/software/`. `tweak_app.py` is an older Gradio UI (VERIFIED present); its controls duplicate the FastAPI app and are **not** listed separately. Treat it as legacy.

## CSV columns

| column | meaning |
|---|---|
| key | the server or state key (`surfaces[X].field` = per card, X ∈ A..F; `(A,B)` = per source) |
| status | `current` (in the code) / `pending` (in a brief, not in the code) |
| default_server / default_client | `DEFAULTS` in `app_server.py` vs the initial state in `app.js` (they differ in places; see conflicts) |
| provenance | `VERIFIED-code` (behaviour read in code) · `Structure-derived` (from the 2011 Reaktor Structure) · `ASSUMED` (invented or approximated) · `BRIEF-pending` (spec'd in a handoff brief) |
| current_ui_location | where the control lives now (VERIFIED where known, `?` if not found) |
| recommended_tabs | Floor, Source, Mic, Mix, Lattice, Paths, Colour, Surfaces, Polar, Advanced |
| play / render | support in Play (WASM) and Render (Python). `N?` means the key is not read by `live_fdn_params`, so Play probably ignores it (VERIFIED by grep; behaviour ASSUMED) |
| flags | CONFLICT / DUPLICATE / lock notes |

## Counts

- **156 rows**: 135 current and 21 pending. Per-channel expansion is included: mix desk × 7 channels, capsules × 3, `src_rad` fields covering both sources.
- Collapsing the per-channel copies gives about **70 distinct current controls** and **about 20 distinct pending controls** (ASSUMED count after grouping). The pending ones are:
  - `air_climate`;
  - `jitter_D`, `structure_dif`;
  - `material_id`;
  - `surfaces_solo`, `surfaces_mute`;
  - `scatter[7]`, `scatter_preset`, `scatter_amount`, `scatter_pulses`, `scatter_seed`;
  - 9 `src_rad` fields;
  - mic designer knobs.
- **Flags**: 10 rows flagged CONFLICT and 13 flagged DUPLICATE.

## Conflicts and duplicates (fix list, all VERIFIED unless marked)

| # | Issue | Detail | Fix (roadmap step) |
|---|---|---|---|
| 1 | **`diffusion` drives two layers (LOCK VIOLATION)** | Card `diffusion` (0–1, default 0.15, `diffusionSlider`) feeds `jittered_distance` (Surfaces Δd = D·λ_ref·sin²θ·u) **and** `tap_dff` → `dff_after_master` → Structure Dffs | Split into `jitter_D` + `structure_dif`, and migrate old saves by copying the value into both (P0.3). `scatter[7]` is a third, separate concept (P5). |
| 2 | `diffusion_seed` has two UI inputs | Surfaces tab `diffusion_seed` and panelMix `diffusion_seed_mix` write the same key | Keep the Surfaces one only (P0.5) |
| 3 | `space` default | server 0.25 vs client 0.17 | server DEFAULTS become the single source; client loads `/api/defaults` (P0.5) |
| 4 | `humidity` default | server 0.0 vs client 0.35 | same (P0.5) |
| 5 | `decay_s` / `decay_lock` | server 0 / false vs client 1.8 / true; there is **no UI checkbox** for `decay_lock` | expose a Lattice checkbox "Lock to T60", fix defaults (P0.5); tail bug P0.2 |
| 6 | `mirror_b` | server false vs client true | P0.5 |
| 7 | `yaw_l_deg` / `yaw_r_deg` | server None (derived from `toe_half_deg`) vs client ∓55 | pick one representation: keep yaw, make `toe_half_deg` derived (P0.5) |
| 8 | `hadamard_n` | Render 8–128; Play hardcoded `n_had = 32` in `live_fdn_params` | label it Render-only until variable N in C (P7.6) |
| 9 | `diffusion_master` | no UI; `fdn.py` `DIFFUSION_MASTER_DEFAULT` −0.25 vs live −0.5 | pick one, keep it in Advanced (P0.5) |
| 10 | `mic_hp_*` (ASSUMED toy) vs `mic_hpf_*` (manufacturer HPF from the measured preset) | confusable names; toys are active only in `ASSUMED_TOYS` mode, and `live_fdn_params` does not read `mic_hp_on` / `mic_proximity` | hide the toy group unless `colour_mode = ASSUMED_TOYS`; rename it `toy_hp_*` in blob v2 (optional) |
| 11 | Mix `pan_*` / `phase_*` (client) vs `mic_pan_*` / `mic_phase_*` (server) | client aliases folded into server keys | document the fold in one function; no user change |
| 12 | Mix bus `solo_*` / `mute_*` vs pending `surfaces_solo` / `surfaces_mute` | different systems (buses vs panels) | distinct naming and styling (P3B) |
| 13 | `toe_half_deg`, `car_omni`, `diverg` hidden | overlap yaw and polar blend | Advanced only, or remove |
| 14 | `mic_preset` (legacy) vs `mic_preset_l/c/r`; the UI shows side/centre | three names for one idea | keep l/c/r in the API and side/centre in the UI; drop the legacy key after migration |
| 15 | `loop_mix` | computed in `_attach_loop_mix`, never packed | not a user parameter; delete it or pack it (P0.4/P0.5) |
| 16 | Heavy-curtain scatter preset | ASSUMED (battens proxy) in the Track C brief | label it ASSUMED in the UI |

## Tab plan (uncluttered: only what each view needs)

- **VERIFIED today**: tabs are Floor·Side·3D (`edit`), Mic, Mix, Lattice, Paths, Colour, Surfaces, Polar 3D. There is no Source tab.
- **Sidebar panels** (`syncSidebar`):

  | Panel | Shown on |
  |---|---|
  | panelRoom | always |
  | panelListen | mic / polar / lattice / paths |
  | panelMix | mix / lattice / paths / colour / surfaces / polar (holds Hadamard, IR length, humidity, air_lp, air_shelf, seed_mix, live_drag_render) |
  | panelPreview | everywhere except mic |
  | panelAdvanced | always |

- Hadamard is therefore already hidden on Floor and Mic (lock satisfied).
- The briefs name the tabs Floor, Source, Mic, Lattice, Paths, Colour, Surfaces, Polar, Advanced. **Mix exists in the app but is missing from that list.** Keep it; it is the bus desk.

| Tab | Should contain | Should NOT contain |
|---|---|---|
| Floor | W/H/L, source and mic positions, `link_heights`, `two_sources`, `mirror_b`, facing handle (P6) | Hadamard, air, surface EQ, mic colour |
| Source *(new, P6)* | `src_rad` preset / yaw / pitch / size / level_ref per source, `source_balance`, B position readouts | Hadamard, surfaces, mic |
| Mic | capsules (pattern / family / polar / yaw / centre_dz / ms_decode), `colour_mode`, presets, HPF; toy group only in ASSUMED_TOYS | Hadamard, air, surfaces |
| Mix | wets, desk trims / faders / pans / mutes / solos / phases | geometry |
| Lattice | `fdn_g`, `decay_s`, `decay_lock` (new checkbox), `hadamard_n` (Render-only badge), `structure_dif` global view | surface EQ |
| Paths | path_on / preset / ellipse params, hover info (P6) | mic colour |
| Colour | `humidity`, `air_lp`, `air_shelf` → `air_climate` (P2), colour reference / hold | geometry |
| Surfaces | cards A–F (material, absorb, EQ, `jitter_D`, `structure_dif`, `scatter`), `lambda_ref`, `diffusion_seed`, Solo/Mute (P3B) | mix desk, mic |
| Polar | visibility toggles, capsule readouts | air, surfaces |
| Advanced | `diffusion_master`, `ir_length_ms`, `reaktor_parity`, hidden mic params, `scatter_pulses` / `scatter_seed`, `tail_follow`, `live_drag_render` | — |

**Recommendation (ASSUMED)**: move humidity / air_lp / air_shelf out of panelMix and into the Colour tab. Right now they appear on six tabs, including Surfaces and Polar, where they are clutter.
