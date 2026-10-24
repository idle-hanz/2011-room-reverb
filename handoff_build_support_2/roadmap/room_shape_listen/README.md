# Room shape listen

Default scene, rendered twice. The only posted change is `room_shape`: `box` or `splay`. Room 6 × 3 × 8 m. Source (2.6, 1.2, 4.75) m. Stand (3.0, 1.5, 1.5) m, space 0.25 m. Neumann U87 Ai cardioid on L, C and R. Decay lock 1.8 s. An absent `room_shape` matched the box impulse, max-abs 0.

Guitar is the whole `robotic_1240\test_guitar_dualmono_clean.wav` (12.0 s, 48 kHz). Splay gain is 1.1404 so its RMS matches the box. The impulse is a unit sample with `ir_length_ms` 500. The lock still builds a 2790 ms tank. `box_ir.wav` and `splay_ir.wav` are the first 0.5 s. Splay impulse gain is 1.2699 on that 0.5 s. Untrimmed tank T20 is 1.799 s (box) and 1.800 s (splay).

T20 below is on the saved file: hypot(L, R), last 50 ms dropped, Schroeder fit from −5 dB to −25 dB, extrapolated to −60. 24-bit stereo, 48 kHz.

| file | T20 s | max-abs |
| --- | ---: | ---: |
| box.wav (previous file, replaced below) | 17.638 | 0.724533 |
| splay.wav | 17.065 | 0.702770 |
| box_ir.wav | 1.363 | 0.718252 |
| splay_ir.wav | 1.376 | 0.718930 |

`box.wav` and `splay.wav` were 14.79 s (guitar plus the tank). `box.wav` was rendered again with `lede.wav` and `live.wav`, so the box row above is the earlier file.

## LEDE and Live room (2026-10-24)

Same guitar, same scene, one file each. `room_shape` is the only change: `box`, `lede`, or `live`. No gain match. 24-bit stereo, 48 kHz. 709920 frames, 14.79 s. Decay lock still builds the 2790 ms tank.

| file | peak | RMS |
| --- | ---: | ---: |
| box.wav | 0.729355 | 0.063232 |
| lede.wav | 0.741062 | 0.055638 |
| live.wav | 0.717199 | 0.059114 |

`splay.wav`, `box_ir.wav`, and `splay_ir.wav` were not rendered again.

## Gable (2026-10-24)

Same guitar, same scene, one file. `room_shape` is `gable`. No gain match. 24-bit stereo, 48 kHz. 709920 frames, 14.79 s. Decay lock still builds the 2790 ms tank. The shape is engine-only: no picker and no 3D view. Box was not rendered again.

| file | peak | RMS |
| --- | ---: | ---: |
| box.wav | 0.729355 | 0.063232 |
| gable.wav | 0.656224 | 0.051748 |

## Hex (2026-10-24)

Same guitar, same scene, one file. `room_shape` is `hex`. No gain match. 24-bit stereo, 48 kHz. 709920 frames, 14.79 s. Decay lock still builds the 2790 ms tank. The shape is a hexagon floor inside the box, flat ceiling at H, built with `_prism`. Engine only: no picker and no 3D view. Box was not rendered again.

| file | peak | RMS |
| --- | ---: | ---: |
| box.wav | 0.729355 | 0.063232 |
| hex.wav | 0.611947 | 0.050041 |
