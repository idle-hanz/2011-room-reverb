# K3: the default room has only 12 unique FDN delays (of 32) on the C bus. CONFIRMED

## LOCKED 28 Sep 2026: default source x 2.6 m, height 1.2 m (Idle). Implemented in patch `05_K2_K3_K4_defaults.diff`

- `app_server.py` DEFAULTS `sx` 3.0 → 2.6 and `sy` 1.5 → 1.2.
- `app.js` state `sx: 2.6, sy: 1.2`, and the `index.html` height slider is 1.2.
- `my` stays 1.5, `link_heights` stays false, and the Reaktor-parity preset is untouched.
- VERIFIED on p5: `live_fdn_params` at the defaults gives **29 / 29 / 29** distinct delays (L / C / R, of 32). The old default gave 20 / 12 / 20 (on both trees when pinned to 3.0 / 1.5).
- Tests: `test_k3_default_source_29_distinct_delays` and `test_k3_client_default_matches`.

---

*Original brief (history, before the decision):*

**Status:** CONFIRMED (VERIFIED by `scripts/k3_unique_delays.py`, using `live_fdn_params` on the snapshot).

## Evidence

| Scene | Unique delays L / C / R (of 32) |
|---|---|
| Server defaults (`app_server.py:55-63`) | 20 / **12** / 20 |
| Client defaults (`app.js:67`, ORTF, humidity 0.35, lock 1.8 s) | 20 / **12** / 20 |
| Source off-centre in X (sx = 2.6) | 20 / 20 / 20 |
| Source height ≠ mic height (sy = 1.2, my = 1.5) | 29 / 20 / 29 |
| Both | **29 / 29 / 29** |

- The Structure "Live-32" reference has **29 unique**. This matches the last row, not the default.

## Cause (VERIFIED)

- The default geometry is doubly symmetric:
  - Source and mic stand are both on the room's centre line: `sx = mcx = W/2 = 3`.
  - Source and mic are at the same height, which is half the room height: `sy = my = H/2 = 1.5`.
- Mirror images then pair up with identical path lengths.
- `engine/fdn.py:667-695` (`fdn_delays_from_taps`) keeps duplicates on purpose. Its docstring at line 678 reads: "Duplicate lengths are kept (Distances had real pairs). No +1 uniquify."
- Duplicate delays in an FDN give coincident modes. The ASSUMED audible effect is a more metallic / less dense tail.

## Options

1. **Change the default geometry (recommended, DECISION FOR IDLE because it changes the default sound).**
   - Nudge only the defaults, e.g. `sx` 3.0 → 2.6 and `sy` 1.5 → 1.2, in:
     - `app_server.py:58` / `:63`
     - `app.js:67`
     - PARAMETERS / `parameters.csv`
   - Result: 29/29/29, as in Structure.
   - The "studio" / "club" presets (`app.js:1872/1877`) already use sy = my but off-centre x. Worth checking these too.
2. **De-dup nudge in `fdn_delays_from_taps`:** +1 sample on repeats. This contradicts the stated Structure intent ("real pairs") and would make Render and Play diverge from the image distances. **Not recommended.**
3. **Do nothing.** Document that symmetric placements lose density.

## Acceptance

- A test asserts ≥ 29 unique delays per bus for the default scene (if option 1 is chosen).
- The package 3 suite already reads `live_fdn_params`, so this is a small addition.

## Listening check

- Default room: current vs sx 2.6 / sy 1.2.
- Snare tail: listen for ringing and flutter.
