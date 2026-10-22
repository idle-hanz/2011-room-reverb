# Dffs allpass (462–465) — 2026-09-20

Path: `Instrument > Sound Processing > Macro` (Dffs builder) and Diffuser Delay **Dffs** pin. Existing Pictures shots **461–465**, **262**, **202**, **472**. No new screenshot.

## Formula **VERIFIED** (462–465)

```
Dffs = Dis × Dff × (1 / Diffusion)
```

Three-input Mul. `1/x` sits on **Diffusion** only.

Shot **464** debug **202.633** is Diffusion **in** to `1/x`, not `1/x` out.

| Voice | Dis (462) | Dff (463) | Dffs (461 = 465 Out) | Dis×Dff/202.633 |
|------:|----------:|----------:|---------------------:|----------------:|
| 1 | 83.6099 | −0.46 | −0.189804 | −0.189804 |
| 3 | 47.9665 | 0 | 0 | 0 |
| 32 | 241.86 | −0.29 | −0.346139 | −0.34614 |

Dis is metres (same family as TL/340). Dff is per-voice, live snapshot all **≤ 0**. Diffusion is monophonic.

No clip module on this Mul. Live Dffs already in (−1, 1). NI Diffuser Delay Dffs is nominally [−1, 1] (472: 0 = pure delay; ±1 delay disappears). Engine clips to [−1, 1] as a **LIKELY** pin-range guard.

## Allpass **VERIFIED** (module spec 472)

Schroeder form, same as `early_field.schroeder_allpass_ir`:

`y[n] = −g·x[n] + u[n−M]`  
`u[n] = x[n] + g·y[n]`

`g = Dffs`. `g = 0` ⇒ `y = u[n−M]` (pure delay, previous engine). `|g| = 1` ⇒ out ≈ ±in.

Wired on each FDN Diffuser Delay line. Do **not** replace Surfaces seeded Δd jitter with this; do **not** fold jitter into Dffs.

## Dff and Diffusion sources

| Port | What | Tag |
|------|------|-----|
| Dis | image metres | VERIFIED |
| Dff | sum(hit Dif) × **Diffusion Master** (202 MDif, 359 DMix, 485) | Master **VERIFIED** Min 0 Max −0.5 Default −0.25; live −0.5. v1 Floor+Ceiling 0.92×−0.5=−0.46 (463) |
| Diffusion | Room Dim (276): **max(W,H,L) × mean(W,H,L) × knob** | 3-input Mul **VERIFIED**. Live knob **0.0333** from 464/395 (57×34.241×97 → 202.633). IC Default unread. |

Live Dff ≤ 0: engine stores card diffusion 0…1 as **negative** after the Clipper. Clipper range **LIKELY** [−1, 1].

## Engine

`dffs_coeff` / `dffs_from_taps` in `fdn.py`. `tap_dff` in `render_pipeline.py` uses `surfaces_hit_by_n` (geometric, ASSUMED A/C split). `diffusion_scale_from_room` = max × mean × `DFFS_KNOB_DEFAULT` (0.0333).

## Do not confuse

| `1/x` | Input | Result |
|-------|--------|--------|
| Air Abs amp (256) | `Dis²` | `1/r²` |
| Distances delay | Const 340 | `1/c` |
| Dffs macro (462) | Diffusion | `1/Diffusion` into Dffs |
| AGC (258–260) | Σ 1/r² | `√(Σ 1/r²)` Send On |
