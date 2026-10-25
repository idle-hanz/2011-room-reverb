# EQ to treatment, 2026-10-25

Verdict: do not solve a reverb EQ with auto-treat rows. Map a broad tail cut and a high shelf onto the room-average rate that `design_bus` already fits. A bass boost does not survive this path.

`SL6_AMOUNT_PLAN_2026-10-25.md` is not in the tree. No product file was edited. No impulse was rendered. The model calls below are `room_target`, `auto_treat`, `phys_ceiling_row`, and `design_line` / `design_bus`.

Scene for the model: page-default cards, absorb 0.05, 0.06, 0.08, 0.10, 0.14, 0.18, 0.22, room 6 × 3 × 8 m, humidity 0.35, Decay lock 1.8 s. Live delays are the default stand, image taps, c = 340, 32 lines. L is 9.6–57.5 ms, median 28.7 ms, five lines under 20 ms. C and R sit within 0.2 ms of that. The EQ examples are an RBJ peak, Q = 1, and an RBJ high shelf. The tail map used here is T × 10^(dB/10), so −3 dB is 0.5× T and +2 dB is 1.58× T. ASSUMED as the translation. The code does not apply it today.

## 1. dB, decay, and the bare card

On one frequency, with the other bands left alone, the lock scale stays put, so a change in material T is the change in heard T. At 250 Hz the page card is α 0.060, material T 2.113 s, one bounce −0.27 dB. VERIFIED, uniform α in `room_target`, bounce from `10·log10(1−α)` as in `_absorb_to_db`.

| α | material T | tail vs the card | one bounce vs the card |
|---|---|---|---|
| 0.038 | 3.35 s | +2.0 dB | +0.10 dB |
| 0.060 | 2.113 s | 0 | 0 |
| 0.121 | 1.056 s | −3.01 dB | −0.29 dB |
| 0.529 | 0.243 s | −9.39 dB | −3.00 dB |
| 0.99 | 0.130 s | −12.1 dB | −19.7 dB |

Halving T (−3 dB if the tail level follows T) moves one bounce by −0.29 dB. The α that cuts one bounce by −3 dB shortens T by −9.4 dB. Early and tail do not share the dial. α = 0 would add +18 dB of T and only +0.27 dB on that bounce. Treatment only adds absorption (`_auto`, and `test_target_longer_than_room_fits_shape_only`), so an α under the card is out of reach. The early boost above this card stops at +0.27 dB per bounce. Plaster + parquet is lower still: area-mean α about 0.025 at 125–250 Hz, one bounce −0.11 dB.

Cuts have room. α 0.99 is still inside the 0.99 clip and is −12 dB of T at 250 Hz. Air is 26% of the loss at 8 kHz on these cards (57% on plaster + parquet). Air is not what stops a 2 dB move.

The Decay lock is a second knob. Thin porous on F, D, A, and C shortens the mid, the lock lifts every band the porous did not eat, and the heard bass can rise while the wall α rises. One inch porous at 20% coverage: locked tail +1.92, +1.07, +0.24, −0.32, +0.03, +0.55, +0.96 dB across 125 Hz–8 kHz. The 125 Hz figure is near +2 dB. The top comes up about +1 dB with it. Early on F goes the other way, a few tenths negative. Four inch porous at 80% drives the top the wrong way for a dark shelf: locked tail at 4 kHz and 8 kHz is +2.58 and +3.64 dB, while one bounce on F at 8 kHz is −6.2 dB. VERIFIED, `room_target` with the lock scale dial / mid.

A Helmholtz row at 250 Hz, Q 3, 50% of F: locked tail −3.20 dB at 250 Hz, neighbors −0.26 and −0.03 dB, one bounce on F −1.81 dB. The tail center of a −3 dB ask can be hit. The early field and the Q = 1 shoulders are not that number.

## 2. The solver and how wide a row is

`auto_treat(W, H, L, surfaces, humidity, t_mid, existing_rows=None, max_panels=4, porous=None)` has no target curve. The target it returns is `makivirta_target`. VERIFIED, `np.allclose` on this room at `t_mid` 0.8. The call still suggests the bass hunt: porous 10.8% on F, D, A, C, membrane 62.5 Hz on F, membrane 125 Hz on D, Helmholtz 198 Hz on D, Helmholtz 315 Hz on A. At 250 Hz the −3 dB ask on the locked curve is 1.35 s. That call's target is 0.82 s.

The panel loop only runs while T / target > 1.10 and the band is 40–500 Hz. It places at most four resonators. Porous is one coverage, the same number on F, D, A, C, chosen so the 500–2000 Hz mean meets `t_mid`. A shelf above 4 kHz is outside that loop. A boost is a deficit, and the loop only removes excess.

Width of the closed-form α, half-maximum. VERIFIED.

- Membrane Q 2 at 125 Hz: 98–160 Hz, 0.71 octave, thirds 99, 125, 157 Hz.
- Helmholtz Q 3 at 250 Hz: 212–295 Hz, 0.47 octave, the 250 Hz third only.
- Shell Q 1 at 90 Hz: 56–146 Hz, 1.39 octave.

`design_helmholtz(250)` and `design_membrane(125)` land on those frequencies. Porous α is seven octave knots, log-interpolated, rising from the bass to about 0.9. A row can follow a half-octave bump or one rising curve. It cannot follow a third-octave wiggle, and four panels do not add that resolution. They add four bumps, all chosen under 500 Hz.

## 3. Bending the loop target

`design_bus` fits three biquads per line (low shelf, high shelf, two peaks, Q at most 4) so the loop T matches the rate. Direct sound does not go through them. Early taps use the face α chain. The biquad count stays 3, so the Play callback cost stays the Surfaces cost. A new curve misses the line cache. One live L bus, cold: 2.7 s for the −3 dB peak, 3.6 s for the shelf, 3.7 s for the +2 dB peak. A second `design_bus` of the same 32 rates returned in 0.02 s. Play designs L, C, and R, so the first push of a new curve is three of those cold fits. The 2.40 ms ceiling is the callback.

Default Play and Render, lock armed, `phys_ceiling` on, take `phys_ceiling_pack`. That calls `make_spec` with no dial anchor, then keeps the greater of the Surfaces rate and 60/T_phys. On this room T_phys mid is 1.800 s, k 0.776, reachable. The ceiling binds at 125 Hz only: material T 2.559 s is pulled to 2.340 s. From 250 Hz up the material is already shorter, so the loop follows the material. VERIFIED, `phys_ceiling_row`.

Put the user multiply on that Surfaces rate, after `cal_fn`, and the ceiling then does this. VERIFIED as rates, before the fitter:

- −3 dB at 250 Hz, Q 1: 250 Hz lands at −3.0 dB against the heard baseline. The 125 Hz shoulder lands at −0.5 dB because that band was already on the ceiling. The ask there was −0.9 dB.
- High shelf −2 dB from 4 kHz: 4 kHz and 8 kHz land on the ask (−1.0 and −1.9 dB). The ceiling does not bind those bands.
- +2 dB at 125 Hz, Q 1: 125 Hz and 250 Hz stay clamped. Heard T at 125 Hz stays 2.340 s. The boost is gone before the fitter runs.

The fitter, on the rate itself, ceiling not applied. One 30 ms line is near the live median. A zero `surf_cal`. VERIFIED.

- Shelf: octave error 7.6%, third-octave 8.9%. At 8 kHz the line returns −2.23 dB against an ask of −1.91 dB.
- −3 dB peak, Q 1: octave error 15.7%. At 250 Hz the line returns −2.36 dB.
- +2 dB peak, Q 1: octave error 2.3%. At 125 Hz the line returns +1.94 dB. This line has 1.0 dB of loop loss to give back. The shortest live line has 0.32 dB and returns +0.47 dB (octave error 28.7%).
- Q 4 peak, −3 dB at 250 Hz: the 30 ms line returns −1.01 dB, octave error 52%. That is past the 0.5 guard.

Same three curves on the live L delays, still the pre-ceiling rate. VERIFIED.

- Shelf: worst line 7.6%, system octave error at 8 kHz +0.3%, guard 0.
- −3 dB peak: worst line 25.8%, system error at 250 Hz +2.5%, guard 0. The short lines hit the center (the 9.6 ms line returns −3.04 dB). Longer lines smear it.
- +2 dB peak: worst line 29.8%, system error at 125 Hz −21.3%, guard 0. The bus does not deliver +2 dB, and the ceiling would remove it anyway.
- Q 4: 16 of 32 lines leave S1P2 for the shelf-only fit. None fall through to identity. System error at 250 Hz +39.9%. The shortest line alone can reach −2.81 dB. The bus cannot.

`surf_cal` stays a multiply on the same rate. The proved room-average list holds 125, 250, and 500 Hz at 1 and leaves the highs under 1. A 0 dB curve multiplies by 1, so that list is untouched. On the 30 ms line, shelf plus those factors, the fitter returns −1.45 dB at 8 kHz against a stacked target of −1.46 dB. The user's delta sits on the calibrated rate. Clearing `surf_cal` when the curve moves would jump the highs by the proved factors. Leave the list. Do not retune it.

## 4. How close it got

Show seven numbers the fitter already has, beside the seven asked dB: `system_oct_err_pct`, plus the worst-line percent. A shelf that lands is under 1% at 4 kHz and 8 kHz. The −3 dB peak's bus sum is a few percent at 250 Hz, with a worst line near 26%. The +2 dB peak's −21% at 125 Hz is the miss, and the ceiling makes that miss total on the default path. Label the row tail only. Early taps do not move when only the rate changes.

`n_within_10pct` on the room-result panel is the Mäkivirta gate. ±10% of T is about 0.4 dB on this map, and it is the wrong curve. A rendered T20 of the whole impulse includes direct and early. The SL6 review already has the split at 198 Hz: calibrated tail 1.16, full impulse 0.79. Do not render a badge for this.

## One-goal run

Step 0 stays on. The edit is the rate in `make_spec`, which is audio core.

One change. On the room-average Surfaces rate, after `cal_fn` and before the ceiling `maximum`, multiply by 10^(−dB/10). The curve is one RBJ peak with Q fixed at 1, and one RBJ high shelf. A zero curve leaves the rate as it is. The seven `system_oct_err_pct` values and the seven asked dB go on the surf report that `design_bus` already feeds.

Gate, live L delays, this room, pre-ceiling rate so the fitter number is visible, then the ceiling max still applied on the default path. The shelf's system error at 4 kHz and 8 kHz stays under 2%. The −3 dB peak's system error at 250 Hz stays under 5%, guard 0. The +2 dB peak stays a miss near −21% at 125 Hz and is not tuned. Q above 1 is not a control.

Out of the run: `design_line` and its guard, `surf_cal` values, `surf_autotreat`, early taps, panels, `phys_ceiling` k, the Decay lock, `live_stereo.c`. `RR_SL_STAGE` stays 5. Auto-treat stays hidden. No impulse, no SURFACES tier, no FULL. QUICK after the edit. The callback stays three biquads. The 2.40 ms ceiling stays.

Polygon rooms still take this rate from the shoebox. This run does not change that.
