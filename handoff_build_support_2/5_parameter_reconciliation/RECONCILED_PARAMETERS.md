# Reconciled parameter table (the 10 CSV conflicts + the K5 default mismatches)

## LOCKED 28 Sep 2026 (Idle). These rows supersede the matching rows below

Implemented in `work/p5/software` (patches 04–09, package 4). VERIFIED by package 3 `test_decisions_2026_09_28.py` and the P0.5 tests.

| Key | Old server / client | **Locked value** | Where set (p5) | Note |
|---|---|---|---|---|
| yaw convention (K1) | look = (−sin yaw, cos yaw) → crossed | **`YAW_X_SIGN = +1`**: look = (+sin yaw, cos yaw); preset yaws unchanged (L −, R +) | `engine/early_field.py`, `static/js/room_math.js` | One constant per language, and they must stay equal |
| `air_lp` (K2) | 0.25 / 0.25 | **0** (1-pole code kept) | `app_server.py` (2 fallbacks), `render_pipeline.live_fdn_params`, `app.js` state, `index.html` slider | Revisit after the 2011 captures reveal the distance unit. The Reaktor-parity preset keeps 0.25 |
| `sx`, `sy` (K3) | 3.0, 1.5 / 3, 1.5 | **2.6, 1.2** | `DEFAULTS`, empty-body `params_from_body`, `app.js` (+ `sx_b` 3.4, `sy_b` 1.2), `index.html` | 29/29/29 distinct delays. `my` 1.5 unchanged |
| `fader_direct` / `fader_fdn` / `fader_early` (K4) | client 0.5 / 0.5 / 0 | **0 / 0.5 / 0** (FDN-first) | `app.js`, `index.html` | Idle mixes FDN first, then adds direct/early |
| `early_wet` (K4) | 0 / 0 | client **1.0** = early-bus *enable* (heard send = enable × fader); server field stays the post-fader send, default 0 | `app.js` state, parity preset, `heardMix` | The server `direct_wet` default of 1 is also unchanged (API callers only). The remaining K5 mismatch is listed by `test_p0_5_server_defaults_equal_client_state` |
| `diffusion_master` (#7) | −0.5 / −0.5 | **−0.25**, clamp **[−0.5, 0]** | `fdn.DIFFUSION_MASTER_DEFAULT = LIVE = −0.25`, `DIFFUSION_MASTER_MIN = −0.5`; server `_span`; all fallbacks; `app.js` | The Reaktor-parity preset keeps −0.5 (inside the clamp) |
| loop level trim (headroom) | none | **`fdn.LOOP_LEVEL_TRIM_DB`**: f2 −2.81 dB play and render (lock only), f3 play −1.70 dB (always); derived at diffusion −0.25, f5 reserved 0 | `engine/fdn.py`, applied in `render_pipeline` | Exact at the reference scene only; residuals ≤ 1.6 dB Play / ≤ 3.4 dB Render (DECISIONS file) |
| SOS colour rates | 48k tables at every rate | **44.1k and 48k tables; other rates off + notice** | `mic_colour/sos_table.py` `SUPPORTED_RATES` | FIR impl unchanged |
| `decay_s` 1.8 / `decay_lock` (#5, #6) | — | **still open**: confirm 1.8 s by ear now that F2 makes it real | — | Not changed |


**Tree:** `snapshot_2026-09-28_2040`. All "now" values are VERIFIED:
- server = `app_server.params_from_body({})` / `DEFAULTS`;
- client = `app.js` `var state` evaluated in node (`tools/defaults_diff.py` → `results/defaults_diff.json`).

## Principle (applies to every row)

- **The source of truth is `app_server.py` `DEFAULTS`.**
- `params_from_body` must take **every** fallback from `DEFAULTS`. Today several are hard-coded literals:
  - `humidity` 0.0 at `:339`
  - `decay_s` 0.0 at `:343`
  - `decay_lock` False at `:344`
  - `mirror_b` False at `:284`
  - `mic_proximity` 0.0 at `:231`
  - `diffusion_master` −0.5 at `:342`

  None of these keys is even in `DEFAULTS`.
- The client loads `GET /api/defaults` (it exists at `app_server.py:515-518` but **no client code calls it**, VERIFIED) and merges it over a minimal fallback state.
- The page sends its full state on every request. So **what Idle hears in the app today is the client value.** Moving the server to the client value changes nothing audible in the app; it only changes API/tool renders that send no body.
- A row is marked **DECISION FOR IDLE** only where the recommended value itself changes the sound Idle has been hearing, or where a known issue (K1/K2/K3/K4/F2) makes the current value questionable.

## Table

| # | Key | Server now | Client now (= heard) | Recommended | Sound change in the app? | Rationale | Files to change |
|---|---|---|---|---|---|---|---|
| 1 | `space` | 0.25 | 0.17 | **0.17** | No | 0.17 m is the ORTF spacing, and the default preset is ORTF (`app.js:26-30`, toe 55°). 0.25 matches no preset | `app_server.py:65` |
| 2 | `yaw_l_deg` | None (derived from toe → −55) | −55 | **explicit yaw in DEFAULTS**, sign per K1 fix | **Yes, if K1 is fixed** | Keep yaw as the stored representation and make `toe_half_deg` derived, as `mic_desk.js:882` already does. The sign is K1 | `app_server.py:71`, `:166-168`; `app.js:73`; K1 brief |
| 3 | `yaw_r_deg` | None (→ +55) | +55 | same as #2 | Yes, if K1 is fixed | as #2 | `app_server.py:73`; `app.js:73` |
| — | `toe_half_deg` (K5) | None | 55 | **55, derived** = mean(\|yaw_l\|, \|yaw_r\|) | No | One representation (PARAMETERS #7/#13) | `app_server.py:123-126` |
| 4 | `mic_hp_on` vs `mic_hpf_*` | false / false | false / false | **Rename the toy to `toy_hp_on`/`toy_hp_hz`** (accept the old names on load). Show it only when `colour_mode = ASSUMED_TOYS`. `mic_hpf_*` stays the real manufacturer HPF | No | A naming conflict, not a value conflict. The toy is read only in ASSUMED_TOYS; `live_fdn_params` does not read it | `app_server.py` (alias), `app.js`/`index.html` Mic tab, `parameters.csv` |
| 5 | `decay_s` | 0.0 | 1.8 | **1.8** in DEFAULTS | Today: no. **After F2: yes** | Today the lock at 1.8 s actually gives 4–12 s tails (run_all t10). After F2 it gives a true 1.8 s. So Idle has never heard "1.8 s" | `app_server.py:343` + add to DEFAULTS. **DECISION FOR IDLE**: confirm 1.8 s once F2 lands |
| 6 | `decay_lock` | false | true | **true**, plus add a UI checkbox "Lock to T60" (none exists, VERIFIED) | No | With F2 the lock is the only mode whose tail matches the dial. The Feedback slider stays for unlocked use | `app_server.py:344` + DEFAULTS; Lattice panel in `index.html`/`app.js` |
| 7 | `diffusion_master` | −0.5 (unclamped; `fdn.DIFFUSION_MASTER_DEFAULT` −0.25 unused) | −0.5 | **Keep −0.5** (the current sound) and clamp to [−1, 0] (package 4 patch 03). Delete or rename the unused `DIFFUSION_MASTER_DEFAULT` | No (keeping −0.5) | Structure: range 0…−0.5, default −0.25 (`fdn.py:195-198`). Live has always run −0.5 | `app_server.py:342`, `engine/fdn.py:197`. **LOCKED 28 Sep: −0.25, clamp [−0.5, 0]** (see top) |
| 8 | `humidity` | 0.0 | 0.35 | **0.35** in DEFAULTS | No | This is what is heard. But see K2: the 1-pole law makes humidity mostly a −2.5 dB broadband step for images beyond about 3 m | `app_server.py:339` + DEFAULTS. **DECISION FOR IDLE** after the K2 listen (keep 0.35 / change / set air_lp 0) |
| 9 | `surfaces[X].diffusion` | 0.15 | 0.15 | **Split** into `jitter_D` (Surfaces Δd) and `structure_dif` (Structure Dffs), both 0.15. Old saves: copy `diffusion` into both | No (bit-exact migration) | **Lock violation today**: one key drives both diffusion layers (`surface_colour.py:311`, `render_pipeline.py:480-497`) | `surface_colour.py`, `render_pipeline.py` (`tap_dff`), `app_server.py`, `static/js/colour_surfaces.js`, `app.js` (P0.3) |
| 10 | `mirror_b` | false | true | **true** | No | What is heard (only matters when `two_sources`) | `app_server.py:284` + DEFAULTS |
| K5 | `mic_proximity` | 0.0 | 0.25 | **0.25** (or drop it from the client) | **No**: it is dead in both paths. `render_pipeline.py:864` accepts it and nothing reads it (VERIFIED by grep); `live_fdn_params` ignores it | Keep the defaults equal so the `/api/defaults` test passes | `app_server.py:231` |
| K5 | `early_wet` / `fader_early` | 0 | 0 / 0 | **LOCKED 28 Sep: client early_wet 1.0 (enable), early fader 0** (see top) | **Yes** | K4: no early reflections by default | `app_server.py:74`; `app.js:85,90,167,179`. **DECISION FOR IDLE** |
| K5 | `sx`, `sy` (default geometry) | 3.0, 1.5 | 3, 1.5 | **LOCKED 28 Sep: sx 2.6, sy 1.2** (see top) | **Yes** | K3: 12/20 unique delays of 32 | `app_server.py:58,63`; `app.js:67`. **DECISION FOR IDLE** |
| K5 | `air_lp` | 0.25 (literal) | 0.25 | 0.25 (into DEFAULTS) | No | **LOCKED 28 Sep: 0** (see top) | `app_server.py:340` |
| K5 | `colour_impl` | "sos" | not in state | **"sos"** in DEFAULTS; the client need not send it | No | Build's new key (28 Sep) | `app_server.py` DEFAULTS |

**Client-only UI keys** are not parameters of the sound engine:
- `fader_*`, `trim_*`, `pan_*`, `phase_*`, `mute_*`, `solo_*`
- `link_lr_yaw`, `align_horizontal`, `preset_owns_pattern`, `mic_setup`, `natural_bus`, `stereo_mic`, `live_drag_render`

The client folds them into `direct_wet`/`fdn_wet`/`early_wet`/`dry_gain` and `mic_gain/pan/phase_*` (`app.js` `heardMix`, around line 280-315). Recommendation:
- Put them in `/api/defaults` under a `"ui"` block, so a single file holds every default.
- Keep the fold in one function (PARAMETERS #11).

**Server-only keys:** `sox`, `soz`, `mz` are legacy and are overridden when metres are sent; the `mic_gain/pan/phase_*` fallbacks equal the fold of the client defaults. No action beyond documenting them.

**Routes the client never calls** (VERIFIED by grep of `static/`): `/api/colour`, `/api/defaults`, `/api/geometry`, `/api/preview`, `/api/surfaces`. `/api/defaults` should become the load path; the others can stay for tools.

## Decisions needed from Idle (this package)

1. **K1 yaw sign** (#2/#3): approve the crossed-capsule fix and choose option A or B.
2. **decay_s 1.8 s** (#5): confirm it after F2, since today's "1.8 s" is really 4–12 s.
3. **diffusion_master** (#7): −0.5 (current) or −0.25 (Structure); clamp at −1 or −0.5.
4. **humidity 0.35 / air_lp** (#8, K2): after listening.
5. **Early level** (K4).
6. **Default geometry** (K3).

## Acceptance

Package 3 `test_p0_5_server_defaults_equal_client_state`:
- today it is an XFAIL listing the 9 shared-key mismatches;
- after this change it must PASS.
