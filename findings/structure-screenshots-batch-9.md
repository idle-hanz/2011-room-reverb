# Structure screenshots batch 9 — shots 434–465 (2026-09-19 ~23:07)

PNGs in Pictures. Not copied into the repo.

---

## Room / stand at this snapshot **LIKELY** (debug InPorts)

| Port | Shot | Value | Note |
|------|------|------:|------|
| MLX | 436 | **28.2743** | |
| MRX | 442 | **28.7257** | Space = **0.4514**; MCX = **28.5** = W/2 |
| MLY / MRY | 437 / 443 | **1.88** | = source Y passthrough |
| MLZ / MRZ | 438 / 441 / 444 | **24.25** | |
| W | algebra | **57.0** | 2×MCX |
| H | SY clusters | **≈34.24** | `2H−Y` / `2H+Y` |
| L | SZ clusters | **≈97.0** | `2L−Z` / `2L+Z` |

Large hall vs Desktop default 6×3×8 — this is the **live Reaktor faders**, not a unit error.

---

## Image macros on the 32 voices **VERIFIED** (420 / 434 / 435 + Dis 462)

Ordered list and inversion: `findings/live-32-images.md` / `LIVE_32`. Dis matches CDist to 0.001 m.

**SX** three clusters only: `X` / `2W−X` / `−X`. No `2W+X` / `−2W+X`.

**SY** all five Y macros. **SZ** `Z` / `2L−Z` / `2L+Z`. No `4L−Z` / `−Z`.

Three duplicate voices. Direct = voice 3. Do **not** confuse with `voice_table_32.py` sink ids (To V 17–52).

---

## Sound Processing **Dly** = Distances delay_ms **VERIFIED** (460)

Path: `Instrument > Sound Processing`. Debug on **Dly** into **Diffuser Delay**.

The 32-voice list is the **same** as Distances TL (413 / 433): 245.912, 236.939, 141.078, …

So FDN / diffuser delay times are **the image delays**, per poly voice — not a separate prime table.

**462** nested absorb macro: `Out = Dis × Dff × (1/Diffusion)` (464: 1/x on Diffusion = 202.633). **Dis** debug = **distance metres** (voice 1 = 83.61), not milliseconds.

**461 / 465**: signed per-voice values on C/O or absorb — not delay times.

**459**: Instrument shell; Distances **TL** still feeding the early **Mixer** L/R (early field), cyan selected.

---

## Engine impact

`fdn_delays_from_taps()` now sizes FDN lines from image L/R mean distance. Tag **LIKELY** (Dly list match; FDN Core internals still unopened). Prime stagger kept as fallback only.
