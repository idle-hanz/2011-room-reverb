# Room shape listen

Default scene, rendered twice. The only posted change is `room_shape`: `box` or `splay`. Room 6 × 3 × 8 m. Source (2.6, 1.2, 4.75) m. Stand (3.0, 1.5, 1.5) m, space 0.25 m. Neumann U87 Ai cardioid on L, C and R. Decay lock 1.8 s. An absent `room_shape` matched the box impulse, max-abs 0.

Guitar is the whole `robotic_1240\test_guitar_dualmono_clean.wav` (12.0 s, 48 kHz). Splay gain is 1.1404 so its RMS matches the box. The impulse is a unit sample with `ir_length_ms` 500. The lock still builds a 2790 ms tank. `box_ir.wav` and `splay_ir.wav` are the first 0.5 s. Splay impulse gain is 1.2699 on that 0.5 s. Untrimmed tank T20 is 1.799 s (box) and 1.800 s (splay).

T20 below is on the saved file: hypot(L, R), last 50 ms dropped, Schroeder fit from −5 dB to −25 dB, extrapolated to −60. 24-bit stereo, 48 kHz.

| file | T20 s | max-abs |
| --- | ---: | ---: |
| box.wav | 17.638 | 0.724533 |
| splay.wav | 17.065 | 0.702770 |
| box_ir.wav | 1.363 | 0.718252 |
| splay_ir.wav | 1.376 | 0.718930 |

`box.wav` and `splay.wav` are 14.79 s (guitar plus the tank).
