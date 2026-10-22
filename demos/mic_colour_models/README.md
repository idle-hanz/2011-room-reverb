# Mic off-axis colour models (prototype)

Res = 10 kHz (dynamic). C/O = 1. Not a Structure OCR of shelf — ASSUMED comparisons.

| Angle | A: Structure law on **radians** fc | B: same law on **θ/π** fc | C: high-shelf dB | D: shelf + soft LP fc |
|------:|-----------------------------------:|---------------------------:|-----------------:|---------------------:|
| 0° | 10000.0 Hz | 10000.0 Hz | -0.0 dB | -0.0 dB / 10000.0 Hz |
| 30° | 8.2 Hz | 935.1 Hz | -0.8 dB | -0.54 dB / 3852.6 Hz |
| 60° | 8.2 Hz | 87.4 Hz | -3.0 dB | -2.0 dB / 3450.0 Hz |
| 90° | 8.2 Hz | 8.2 Hz | -6.0 dB | -4.0 dB / 2900.0 Hz |
| 120° | 8.2 Hz | 8.2 Hz | -9.0 dB | -6.0 dB / 2350.0 Hz |
| 150° | 8.2 Hz | 8.2 Hz | -11.2 dB | -7.46 dB / 1947.4 Hz |
| 180° | 8.2 Hz | 8.2 Hz | -12.0 dB | -8.0 dB / 1800.0 Hz |

## Takeaways

1. **Model A** (current engine if θ is radians): by 90° Gain hits 0 → fc ≈ 8 Hz. That is the phone-filter feeling.
2. Structure dump Dir was **0.002–0.17**, not 0–π. So either Dir is a small look-error, or we must **normalize** angle before the Power law.
3. **High-shelf alone** keeps lows and mids, tilts HF — closer to real off-axis plots (DPA etc.).
4. **Combo D**: shelf does the audible HF dulling; soft LP with a floor adds a little air loss without muting the tap.
5. Keep Structure 1-pole path as an option (Mic Response), but default colour should be **shelf-led**.
