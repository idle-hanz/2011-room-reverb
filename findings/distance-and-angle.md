# Distance and angle — Euclidean vs the long trig (2026-09-20)

Idle Hanz asked whether the original Distances graph was over-long: distance should be the root of the sum of squares, and the angle could have been a dot product.

## Distance — you are not wrong **VERIFIED**

Image delays use **3D Euclidean** distance. Structure (batch 8, shots 420–433; Square Root probe 430):

1. Per axis: image − mic → Δ
2. Δ×Δ (square)
3. Add the three squares
4. **Square Root** → metres
5. × (1/340) × 1000 → delay ms (`TL` / `TC` / `TR`)

That is `d = √(Δx² + Δy² + Δz²)`. Sign of each Δ does not matter once squared. Engine `dist()` is this law. Distances `1/x` is **`1/340`**, not a gain. Geometric amp is Air Abs **`1/r²`** of this same `d` (see `air-absorption.md`).

**Direct Field `DD` is different:** 2D XZ only, Y ignored (`dist_xz`). Panel readout, not the image-delay path.

## Angle — the long-winded part **VERIFIED** (chain) / **LIKELY** (intent)

The same Distances macro then builds an angle the long way (417, 450, 451):

- Divider **ΔX / ΔZ** → **ArcTan** (floor-plane azimuth)
- **Sine/Cosine** of Prepare look (`MLALR` / `MRALR`)
- More squares → Square Root → another ArcTan
- Some of that feeds **`0-1-Degrees` lamps** (display, not Prepare audio)
- `DL` / `DC` / `DR` leave Distances into Microphone **Dir** (460)

A first-order polar pattern only needs **cos θ**, not θ:

`cos θ = (look · r) / (|look| |r|)`

In the **floor plane** (matching ΔX/ΔZ, not elevation):

`cos θ_xz = look_xz · r_xz / |r_xz|`

That is the same number as `cos(atan2(rx, rz))` after rotating the arrival into the look frame. Engine helper `arrival_cos_xz` is that dot product; selfcheck proves it equals `cos(direction_angles(...)[0])`.

**Not switched into `compute_taps`.** Tap polar still uses `direction_angles` (atan2) then `cos`. Audio numbers do not change.

A **3D** dot product would fold in ΔY (ceiling/floor more off-axis). Structure’s primary ArcTan is **ΔX/ΔZ**, and `compute_taps` already discards the vertical atan2. Do not move polar to 3D until a Dir wire proves elevation is in the audio path.

## Microphone Dir vs Desktop polar

Shot **410**: Microphone audio is **In → 1-pole → Out**. Nested Gain (411 **Power x^y**) × Log(Res) drives the 1-pole **cutoff**, not a `(1+cos θ)/2` audio multiply. Desktop cardioid/fig‑8 on the early taps is still the modern ASSUMED pattern. Power **X vs Y** pin order remains UNKNOWN — not in audio.
