# Air Absorption `1/x` (shot 256) — 2026-09-20

Path: `Instrument > Sound Processing > Air Absorption`. Re-read of existing Pictures shot **256** (plus 214 / 257 / 460). No new screenshot.

## Amp path **VERIFIED** (256)

```
Dis ──► Order
          1 ──► × in1
          2 ──► × in2          Dis × Dis = Dis²
          3 ──► Value Trig
                    × out ──► 1/x ──► Value In ──► amp
                                      └──► AGC In
In ──► 1-Pole LP ──► × amp ──► Out ──► Diffuser Delay adder
```

Same Order idiom Distances uses to square a Δ. **`1/x` is Primary reciprocal of `Dis²`, not of `Dis`.**

`amp = 1 / Dis² = 1/r²`

`Dis` is metres (462 voice 1 = **83.61**, same as TL/340×1000). Port 3 is **Wet**, not Met.

Controls (359): **Humidity → Wet** (out 20). **Diffusion Mix → DMix** (out 19).

Humidity rotary **Function VERIFIED (486):** Min **100**, Max **700**, Default **400**, Step **6**. Idle Hanz: HF lost vs distance. Wet is that number; `fc = Wet/Dis` Hz. Default 400 at 10 m → 40 Hz (dark — `air_lp` mix). UI 0 = bypass; 0.5 = 400; 1 = 700.

394 tall fader is **Diffusion Master** (485: Min 0, Max **−0.5**, Default **−0.25**, live at Max). Not Humidity.

## Distances `1/x` is a different module **VERIFIED** (210–212, 431)

Const **340** → `1/x` → `0.00294118` = `1/340`. Then × distance × **1000** → delay ms.

Distances does **not** output a geometric gain. `LDist` / `CDist` / `RDist` stay metres.

## Filter path **VERIFIED** (256–257)

`Wet` → Humidity (257 = Order/Value latch of Wet) → `Wet / Dis` → **Log F→P** → 1-Pole **P**. Audio `In` → LP × amp.

Log pin **F** in, **P** out (same family as F-to-pitch). 1-Pole **P** is pitch. Units cancel:

`fc = Wet / Dis` Hz **LIKELY** (graph VERIFIED; P-units not on an Info shot).

Engine: humidity 0 = bypass; else Wet = 100 + humidity×600 (486).

Independent mixes (`air_lp`, `air_shelf` in 0…1). humidity 0 = off. Defaults: **0.25 1-pole + 1.0 shelf** (tune later; 1-pole can be drastic).

1. Structure 1-pole LP (`fc = Wet/Dis`) — dry/wet mix
2. High-shelf HF roll-off vs distance — **ASSUMED** upgrade (scales dB depth)

Either, both, or neither. Wired on FDN inject and the early overlay.

## Shell **VERIFIED** (214 / 460)

One Air Absorption feeds all three L/C/R adders. One `Dis` (poly per voice). Delays `DtL/DtC/DtR` still differ. Which Distances terminal is `Dis`: **LIKELY** LDist (voice-1 metres match TL); not a dedicated cyan pin.

## Engine

`geometric_level` is `1/r²`. 1-pole LP `fc=Wet/Dis` on inject (`air_lp` mix) — offline IR and Play live worklet. High-shelf is the ASSUMED upgrade on both paths. Tap polar is first-order `a+(1−a)cosθ` plus an ASSUMED off-axis shelf; Structure tap polar still **ASSUMED**.

## Do not confuse

| `1/x` | Input | Result |
|-------|--------|--------|
| Air Abs amp (256) | `Dis²` | `1/r²` |
| Distances delay (210) | Const 340 | `1/c` |
| Dffs macro (462–464) | Diffusion | `1/Diffusion` into Dffs |
| AGC (258–260) | Σ 1/r² | `1/√` then `1/x` → `√(Σ 1/r²)` |
