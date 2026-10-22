# Diffuser Delay vs Hadamard loop (2026-09-20)

Idle Hanz: the **Diffuser Delay** is where all the delay happens. The FDN / Hadamard only recombines the delayed voices with a unique inversion set per parallel voice, then that mix is fed **back into the Diffuser Delay**.

## Structure shell **VERIFIED**

Path: `Instrument > Sound Processing` (shots **214**, **460**). Three parallel L / C / R columns.

| Block | Role | Tag |
|-------|------|-----|
| **Diffuser Delay** | Built-in Primary **allpass delay** (472 Info). No nested graph. `Dly` ms = image Distances (460 = TL). `Dffs` = internal allpass feedback (0 = pure delay). **Max Delay = 1000 ms**, High Quality Interpolation (**476**). | module / buffer **VERIFIED**; Dly list **VERIFIED** |
| **Feedback Delay** | Hadamard mix only. **Fr.V** = From-Voice picker (468–471 Info), not a delay. Matrix → To V → Gain `In×(1/32)×Gain`. | mix / Fr.V / `1/32` **VERIFIED** |
| Loop | `+` adder on Diffuser Delay In (473). **Two** audio summands, both cyan with the adder selected: Air Abs Out (upper) and **Feedback Delay Out** (lower). Adder → Diffuser Delay In. | **VERIFIED** (473) |
| Then | Diffuser Delay Out → Microphone L / C / R | **VERIFIED** (214 / 460 / 472) |

So: one set of 32 poly delay lines per capsule, times from that capsule’s image distances. Hadamard is the feedback matrix (unique inversion row per voice). No separate prime-ms table inside the FDN.

Do **not** re-screenshot Hadamard Voice 1–32 (219–254). Voice 1 all+ and Voice 2 `+−+−` already match Sylvester.

## Desktop engine (2026-09-20)

Three FDN loops L/C/R, image ms, cap 1000, **no uniquify**, inject t=0, Mixer `L+0.5·C`, Voice Combiner sum, RMS makeup. Early FIR only if `early_wet > 0` (default 0).

Dffs allpass **wired** (`Dis × Dff × 1/Diffusion`, 462–465). Air Abs amp is `1/r²` (256).

## Mixer (477) — no delay **VERIFIED**

`L + 0.5·C`, `R + 0.5·C`. Voice Combiner (479). Receive **RMS Volume** (478). Distances → Mixer **REJECTED**.

## Next click (optional only)

Diffuser Delay, Fr.V, loop adder, Dffs formula, and Humidity Wet 100–700 are done. Skip Hadamard Voice rows.

- Next: C/O Function tab (Power Y) or listen vs Reaktor (Play live / Render, Early overlay 0, FDN wet 1, IR 1500, Voices 32). Mic 1-pole is on delay out, not in the loop.
