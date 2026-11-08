# CM5 — compressors and the Neve preamp

Natural, glue, swell, and the 610-A were left as they were. Swell is `241d3bfbf3ed1f91abd1eaa0c0a8a77f80d52283` on origin/main. Amount 100 is 12 dB. Listens are uncommitted under `software/listen/cm5/`. Limiter hits were 0. One scale per source keeps peaks ≤ 0.49.

## Stage B — nuke

Commit `fe8bb4235c9e0ee934b5ece21d2e17689ae8fccd`. Makeup is `min(amount, GR)` in `wet_gain_db` and in `bloom_sample` for pid 3. The hard knee stays: T −19.784 dBFS, W 0, R 1e6.

**VERIFIED.** Settled GR matches CM0 within 0.001 dB (gate 0.2): −30 → 0.000, −18 → 1.666, −6 → 13.564. Net tail at amount 100: 0.000, 0.000, −1.548 dB. All ≤ +0.5.

Play was passing `abs(x)` into a high-passed detector. For pid 3 and not split, `bloom_sample` rebuilds the signed sample as `0.5 * (pendL + pendR)`. `live_stereo.c` was not edited. Same-tone render − Play ≤ 0.1 dB at −18 and −6. Wasm rebuilt. `WORKLET_VER` stayed 63.

Listens: `software/listen/cm5/b/`. Drums scale 2.936711. Pad scale 2.248213.

## Stage C — room crush

Commit `c290afc93bf8c7c480b858585633d99a9089861c`. It does have makeup. Uncapped net at −30 dBFS, amount 100, was +4.871 dB. The same cap is on preset `room_crush` and pid 2.

**VERIFIED.** Character kept. T −37.875, R 30, W 8.251, release 33 ms on the 1 ms grid (CM0 sample value 32.61). GR −30 / −18 / −6 = 7.165 / 18.743 / 30.367. Net tail 0.000 / −6.705 / −15.000. The −18 net is still under −4 dB. No high-pass, so no detector change. Same-tone render − Play ≤ 0.1 dB. Wasm rebuilt. `WORKLET_VER` stayed 63.

**LIKELY.** The 15 dB duck is the Room Crush `bloom_defaults.max_duck_db` in `compressor_presets.json`, a tail cap, not a measured device maximum. It binds at −6, where amount − GR is about −18.4 dB. It was not changed.

Listens: `software/listen/cm5/c/`. Drums scale 4.692291. Pad scale 2.494325.

## Stage D — Neve 1073

The fault is the same pair the 610-A had, with the opposite sign on the level. Fix is in `pack_pre` only, `kind == neve1073`, after the unity H2 scale. The 610-A block is untouched. Play has no Neve SOS literals. It reads this packed row, so the wasm was not rebuilt. `WORKLET_VER` stayed 63.

**VERIFIED.** Chain is drive, H1, /vc, nclip, *vc, flux, H2, then /drive when drive is not 0. Render oversample 8, Play oversample 1. Raw |H1| at 1 kHz is 113.657206528785. Kernel G (`klin_neve`, delay 64) is 233.316274689952. |H1|/G = 0.48714, which is −6.247 dB. The unity scale on H2 hid that.

**VERIFIED.** Capture drive 0 is −36 dBFS (`pre_stairs.py`: `rel_drive_db = L − (−36)` for neve). The trim that lands an app −18 dBFS peak on that reference is −18 dB. Packed |H1| is G × 10^(−18/20) = 29.372778719233 for both the render pack and the Play pack. Quiet 1 kHz gain is 0.000 dB.

**VERIFIED.** Drive 0, −18 dBFS, harmonics 2–15, settled half: THD 0.8677%. Same-tone fundamental, render os 8 versus Play os 1: −0.0285 dB versus −0.0696 dB, delta 0.041 dB. Wasm Play at −30 dBFS (linear) matches that render gain within 0.1 dB. A −18 dBFS sine through the room is not this point: the FDN bus is hotter than the sine, and os 1 versus os 8 then diverges.

**VERIFIED, report only.** Drive 12, −18 dBFS: render THD 12.275%, fundamental −0.590 dB. Play os 1 on that same sine: THD 34.303%, fundamental −9.159 dB. That gap is the existing Play oversample, not this scale. Before the fix, Drive 0 at −18 was 12.521% THD and Drive 0 at −36 was 0.005%. UAD at the −36 dBFS stair is 9.2844% (`pre_stairs_r3.csv`, 1 kHz, rel drive 0). That remaining gap is the fit. It was not chased.

Listens, Drive 0: `software/listen/cm5/d/`. Drums scale 4.692291 (off 0.4900, old 0.4885, new 0.4881). Pad scale 1.824546 (off 0.3453, old 0.4900, new 0.3508).

## Pins

Empty MD5 `067adbca1930efcd3f7c83bdd1d4c359` and centre MD5 `35db578a18557d5729c0450e26f24a9d` did not move. `quiet.f32` stayed `e38862e337b2b5ebf394c9a09f93212b`. `WORKLET_VER` stayed 63. The render golden `2a806e334e06cc475868d4c3da3fc78431c9a0aa` did not move.

**VERIFIED, other bot.** `6c25000c5b13b26746dacbaf615e2d7aa54bf38e` re-pinned the four Play goldens and `GOLDEN_META` (`0bf64ef21a262723573e9d6c6d10d0dbf2397e7c`) after polar-once. This stage does not touch those files. QUICK was re-run on that tree with the Neve change present: `test_quick_pins` plus the Neve test, 8 passed; selfcheck 45; node 108/108.

Default off stays bit-exact: pre off returns an empty pack, and amount 0 does not run the makeup cap.
