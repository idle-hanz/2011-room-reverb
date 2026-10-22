# K2: the Structure air 1-pole corner is very low (133 Hz at 3 m). CONFIRMED numerically; cause UNKNOWN

## LOCKED 28 Sep 2026: KEEP the Structure 1-pole code, default mix `air_lp` = 0 (Idle). Revisit after the 2011 captures reveal the distance unit.

- Implemented in patch `05_K2_K3_K4_defaults.diff`:
  - `app_server.py` `air_lp` fallback 0.25 → 0.0 (twice: `params_from_body` and the render call).
  - `render_pipeline.live_fdn_params` fallback 0.25 → 0.0.
  - `app.js` state `air_lp: 0`.
  - `index.html` slider value 0 / output 0.00.
- The C/Python 1-pole code is untouched. Raising the "Air 1-pole mix" slider brings it back.
- HF air loss at the default comes from the **air shelf** (`air_shelf` 1, still on).
  - ISO 9613-1 is **not implemented yet** (P2 XFAIL). Today the ASSUMED shelf does it.
  - When P2 lands, the ISO model replaces the shelf as the HF air loss.
- The Reaktor-parity preset (`app.js` about line 189) still sets `air_lp = 0.25`, because it reproduces the Reaktor dump. It was left as is (ASSUMED intended).
- Test: `test_k2_air_1pole_default_zero` (server, client state and slider are all 0; the 1-pole code is still present).

---

*Original brief (history, before the decision):*

**Status:** the numbers are CONFIRMED (VERIFIED by `scripts/k2_air_corner.py`). Whether it is a bug is **UNKNOWN**.

**NEEDS IDLE LISTENING** (or the reference captures from `CAPTURE_GUIDE`, humidity grid, compared with `compare_ref`).

## What the code does (VERIFIED)

- `engine/early_field.py:1673-1690`:
  - `Wet = 100 + 600·humidity`
  - `fc = Wet / d` (Hz, with d in metres)
- `apply_air_absorption` (`early_field.py:1796-1824`) mixes the 1-pole in at `air_lp`, default 0.25:
  - `buf = (1 − air_lp)·buf + air_lp·LP(buf)`
- Play uses the same law: `render_pipeline.py:1322-1336` (`_live_air_for_distance`) feeds `air_g` into `tint()`.

| humidity | d | fc | Response at 50 / 100 / 1k / 10k Hz, air_lp 0.25 | Same, full LP (air_lp 1) |
|---|---|---|---|---|
| 0.35 (client default) | 3 m | 103 Hz | −0.4 / −1.0 / −2.4 / −2.5 dB | −0.9 / −2.9 / −19.8 / −39.1 dB |
| 0.5 | 3 m | 133 Hz | −0.2 / −0.7 / −2.4 / −2.5 dB | −0.6 / −1.9 / −17.6 / −36.9 dB |
| 0.5 | 30 m | 13 Hz | −2.3 / −2.4 / −2.5 / −2.5 dB | −11.8 / −17.6 / −37.5 / −56.9 dB |

- With the default mix, this is not an HF roll-off. It is a **broadband step of about −2.5 dB** above a few hundred Hz for every image beyond about 3 m. In practice it acts as a distance-dependent level drop.
- ASSUMED physics reference: real air at 20 °C / 50 % RH absorbs about 0.45 dB at 10 kHz over 3 m. A 1-pole that matched that would need fc ≈ 30 kHz at 3 m, about 225× higher than the code gives.

## The Structure source

- `/workspace/structure-screenshots-batch-4-full.md:255` reads: "Ins: In, Dis, Met → Humidity; filter P ← Log(Humidity/Dis)".
- The code matches the formula. **But the unit of `Dis` and the role of `Met` are not known.**
  - If `Dis` in Structure was a delay in samples, or a scaled distance rather than metres, the corner would be much higher.
  - "Log(...)" may also mean the filter parameter is on a log/pitch scale, not Hz.
- All of this is ASSUMED. I found no other Structure note that fixes the units.

## Options (all DECISION FOR IDLE; the lock says the humidity 1-pole stays separate from the shelf, so none of these merges them)

1. **Leave the law and keep `air_lp` at 0.25.** Accept the about −2.5 dB step as a "Structure character".
2. **Keep the law but set the default `air_lp` to 0.** The ASSUMED shelf (and ISO air after P2) then carries the HF loss.
   - One-line change: `app_server.py` DEFAULTS `air_lp` 0.25 → 0, `app.js:97` `air_lp: 0.25` → 0.
   - `apply_air_absorption` skips the 1-pole when lp = 0 (VERIFIED, `early_field.py:1815`).
3. **Re-scale the corner once the Structure unit is known**, e.g. `fc = Wet·k/d` with k from a Structure measurement. Do not guess k.

## Acceptance (after a decision)

- A test pins `fc(d, humidity)` to the chosen law.
- Render and Play still agree: Play `air_g` equals the Render corner.
- Direct stays air-free (lock; already tested in package 3).

## What to listen to

- 20 m room, humidity 0 vs 0.5 vs 1, air_lp 0.25 vs 1.
- Does the early field get darker, or just quieter?
