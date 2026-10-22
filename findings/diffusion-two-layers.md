# Two diffusion layers (2026-09-20)

Idle Hanz asked about an old bot thread: model diffusion as seeded distance jitter with a `1+sin²(θ)` envelope.

## Desktop Surfaces — that thread is already the ASSUMED desk

Implemented in `surface_colour.jittered_distance`. **Δd form**, not a scale of `d`:

`Δd = D · λ_ref · sin²(θ) · u`  
`d' = max(ε, d + Δd)`

- `D` = Surfaces card diffusion 0…1
- `λ_ref` default **0.02 m**
- `u` ∈ [−1, 1] from SHA-256 of `(seed, image index, surface, mic)`
- Seed once per render (default 0) ⇒ bit-identical IR

**Prefer Δd over `d · (1 + D · sin²θ · u)`.** A 6 m room and a 20 m hall should not get proportionally huge scatter. `1+sin²(θ)` alone with no `u` only changes level, not diffusion.

Keep the **ASSUMED** tag. This is the modern Surfaces desk, not a Structure restore.

## 2011 ensemble — different mechanism **VERIFIED** (module)

Sound Processing **Diffuser Delay** is NI’s Primary allpass delay (472). Diffusion there is **Dffs** (internal allpass feedback), not an RNG:

| Dffs | Behaviour (NI) |
|------|----------------|
| 0 | pure delay |
| ~0.5 | useful smear |
| ±1 | out ≈ ±in (delay disappears) |

`Dly` is still the image time in ms. Nested absorb macro (462–464) builds **Dffs** as a **deterministic** Mul of **Dis** (metres) × **Dff** × **1/x(Diffusion)**. No seed, no `sin²(θ)`, no `u`.

Do **not** replace that allpass with path-length jitter in a Structure-faithful FDN. Do **not** claim the Surfaces jitter *is* 2011 diffusion.

Scale **VERIFIED**: 464’s **202.633** is Diffusion **in** to `1/x`. `Dffs = Dis × Dff / 202.633` matches 461/465 (voice 1 −0.189804). Engine clips to [−1, 1] (**LIKELY** NI range). Wired as Schroeder allpass on each FDN delay. Dff source still **LIKELY** (geometric card sum, not A–F bits). Do not unify with Surfaces jitter.

## What not to do

- Unseeded `random()` on taps
- `1+sin²(θ)` with no random term
- Fold Surfaces jitter into Diffuser Delay Dffs, or the reverse, without an explicit go
- Drop the ASSUMED tag on jitter

Engine FDN is the delay+Hadamard loop (L/C/R). Surfaces jitter still runs on the early-tap overlay (`early_wet`). Leave Dffs vs jitter un-unified until asked.
