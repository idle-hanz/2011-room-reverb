# Mixer Voice Combiner + RMS Volume (478–482)

Idle Hanz: a Receive in Mixer might be AGC so raising feedback makes the field wetter without a volume jump. That is the 2011 design.

## Mixer graph **VERIFIED** (477–482)

```
L ──────────────┐
                ├ Add ─┐
C ─× 0.5 ──┬────┤      │
           └────┤      ├ Audio Voice Combiner ─┬─ × ─ L out
R ──────────────┴ Add ─┘                       │
                                               ├─ × ─ R out
                         Receive (RMS Volume) ─┘
```

| Module | Role | Shot |
|--------|------|------|
| Const **0.5** × C | centre at −6 dB into L and R | 477 |
| **Audio Voice Combiner** | *“Mixes a polyphonic audio signal to mono.”* Sums 32 voices. | **479–481** Info |
| **Receive** | Wireless from Send **RMS Volume** (also listed: Diffusion, Volume). Debug on Receive ≈ **223.768** (482). Feeds both **×**. | **478**, **482** |

No Delay in Mixer. Distances → Mixer still **REJECTED**.

## AGC Send **VERIFIED** (256, 258–260)

Path: `Sound Processing > Air Absorption > AGC`. Info: *Automatic Gain Control*.

**What is squared:** Air Abs already did Dis×Dis then `1/x`, so AGC **In** is per-voice **`1/r²`** (256, yellow event into AGC). Fr.V 1… pick those values. Upper `+` **sums** them. **No extra square** between that sum and **1 / Sq. Root** (260).

```
AGC In = 1/r_i²          (256)
S = Σ Fr.V(In)           (upper +)
1/√S  →  1/x  →  √S      (AGC On → Send RMS Vol)
```

Send On = **`√(Σ 1/r_i²)`**. Geometry only — does **not** see FDN loop gain.

AGC Off path (260): Volume trim × dB(lower `+`). Panel 394 **AGC Off**. Receive still live **223.768** (482). Do not treat Off as “no Send.”

AGC nested Macro (483–484): Info **“Multiplier for multiple signals.”** In fans into a × then Out. Idle Hanz: **wiring bus** so the poly In reaches Fr.V **34–52** at the bottom, not a designed extra power. Engine AGC On still uses the upper sum of Fr.V 1… of `1/r²` only. Do not fold 34–52 or In³ into makeup.

Fr.V 17–52 appear in AGC (259 / 484). Image-index leftovers vs live 32. Lower `+` → dB Off path **LIKELY**.

## Design (from-them + Structure)

Raising loop gain / feedback should change **wetness / decay**, not overall loudness. Structure AGC does not do that (geometry Send). **Render** RMS-normalizes the FDN wet IR (ASSUMED). **Play live** uses the same target RMS via first-arrival energy × `1/(1−(g√N)²)` (full IR too slow to bake while dragging). Peak ceiling only as clip guard on Render. `fdn_wet` still mixes that field against dry / early overlay. No extra slider.

Tag: Mixer wiring **VERIFIED**. Structure detector **VERIFIED** (sum of 1/r², then 1/√, then 1/x). **Render** IR RMS **ASSUMED** (g-compensation). **Play live** makeup is the same target from inject energy (ASSUMED). Makeup target **ASSUMED**.
