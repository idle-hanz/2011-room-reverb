# Surfaces in the loop: listening checklist

All files are 24-bit / 48 kHz stereo. Within each group and source (guitar or snare) the files have **equal RMS**, and one shared gain sets the loudest file to −1 dBFS (`ab_levels.json`).

Because RMS is matched, long tails (brick, untreated) play a little quieter in the dry part. Judge **tail length and tone per band**, not loudness. The snare has 2 hits 3.9 s apart, so you can hear the tail die.

All Surfaces files use the 3-biquad per-line filter plus one Render calibration pass. The A_flat / *_flat files are today's engine, Flat (2011).

## Group 3: default room (plaster + parquet), dial 1.8 s, decay lock on
| File | What it is | Listen for |
|---|---|---|
| `3_surfaces_default_room__{guitar,snare}__A_flat_2011.wav` | today | same decay in every band |
| `…__B_room_average.wav` | Surfaces, every line uses the room-average loss | treble dies sooner (air + plaster), bass lasts longer. The tail (80–500 ms) is about +4 dB at 125 Hz and −9 dB at 8 kHz against A (measured on C). |
| `…__C_directional.wav` | Surfaces, each line uses the faces its image path hits (s′ ≥ 0.5) | against B: a slightly fuller bass and airier top (≤ 1 dB). Is it more natural, more "room"? |
| `…__D_directional_with_room_shell.wav` | C + room-shell membrane term (doors and glazing, ASSUMED) | the bass boom of textbook solid plaster tamed (125 Hz: 1.9 s instead of 3.4 s) |

Decisions: D-SL2 (C vs B), D-SL6 (D vs C), D-SL8 (B/C vs A).

## Group 4: material contrast (absolute length from the materials)
| File | Listen for |
|---|---|
| `4_material_contrast__*__studio_flat.wav` / `brick_flat.wav` | Flat (2011): only the length differs, and the tone stays the same |
| `…__studio_room_average.wav` / `…__studio_directional.wav` | carpet and panels: short, darker top, 1.0 s bass |
| `…__brick_room_average.wav` / `…__brick_directional.wav` | bare brick and plaster: long (6 s bass, 3.5 s mid), bright-ish middle, then air takes the top |

Question: does changing the material now change the *tone* of the tail, not just its length? (D-SL1)

## Group 5: auto-treat (default room, target T_mid 0.8 s, absolute)
| File | What it is | Listen for |
|---|---|---|
| `5_auto_treat__*__A_untreated.wav` | plaster + parquet, no treatment | long, boomy (about 5 s at 125 Hz, 2.6 s mid) |
| `…__B_broadband_only.wav` | 4″ porous on a 4″ gap, 21 % of ceiling, rear and side walls | the mids are controlled, but the bass still hangs (+35–100 % at 50–160 Hz) |
| `…__C_auto_treated_panels.wav` | B + 4 tuned panels (62.5 / 125 Hz membranes, 157 / 198 Hz Helmholtz) | an even decay across bands: the Mäkivirta target (16/23 ⅓-octaves within ±10 %) |

Decisions: D-SL5 (auto-treat suggests rows), D-SL3 (panels replace the 2011 per-axis cuts).
