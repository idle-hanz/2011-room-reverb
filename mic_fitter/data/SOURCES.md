# Data sources used overnight

## Fit band (v3)

- **Analysis / loss frequencies:** **20 Hz – 16 kHz** (log-spaced, 64 points).  
  Overnight v1 used ~200 Hz–16 kHz.
- **Quasi-anechoic window:** 2 ms pre + **80 ms** post around direct peak (was 40 ms)  
  so LF bins near 20 Hz have usable SNR for the mild low shelf. Slightly more early-reflection
  leakage vs overnight — documented trade-off.


## v3.1 — Røde NT2-A (2026-09-24)

- Added **MEASURED** fits for `RodeNT2ACardioid` / `RodeNT2AOmni` / `RodeNT2ABidirect`
  (Franco Raw_IRs 5 m 24-bit; families `ldc_cardioid` / `omni` / `fig8`).
- **NT5** absent — see `presets/pending_rode_nt5.md`. NT2-A is LDC multipattern,
  not an NT5 stand-in for matched-pair SDC.
- SE2200A stub retained (non-MEASURED).

## Status update (2026-09-27)

- **20 MEASURED mics** total: the 17 original + `RodeNT2ACardioid` / `RodeNT2AOmni` / `RodeNT2ABidirect`.
- Idle confirmed he has **no data** for Røde NT5 or sE Electronics SE2200A →
  both are **no measured data available; not planned**. No presets exist or will be fabricated.

## v3 additions (2026-09-23)

- **shelf_slope bounds:** 1.5–12 → **0.6–12.0** (v2 pinned many fits at 1.5).
- **Plots / polar3d:** `DEFAULT_F_LO` 40→**20** Hz; ring freqs include **20 Hz**; z-ticks include 20.
- **Optional HPF:** schema `switches` only — **not** fitted from Zenodo. See `MANUFACTURER_HPF_DEFAULTS` / `apply_hpf`.
- **Extra MEASURED mics** from same zip (5 m Raw_IRs): SM58, MD441, U87 Omni/Bidirect,
  C414 Omni/Hyper/Bidirect, CMC5-U Omni/Bidirect, Coles 4038 (32-bit at 5 m — no 24-bit),
  DPA 4006. Original six retained.
- **SE2200A:** requested but **absent** from Zenodo — see `presets/pending_se2200a.md`.

## Primary (MEASURED) — Franco et al. Zenodo

- **Dataset:** Multi-Angle, Multi-Distance Microphone Impulse Response Dataset  
- **DOI:** [10.5281/zenodo.4633508](https://doi.org/10.5281/zenodo.4633508)  
- **Record:** https://zenodo.org/records/4633508  
- **Authors:** Franco Hernández, Brookes, De Sena (IoSR, University of Surrey)  
- **Archive used:** `Microphone_Impulse_Responses.zip` (~1.42 GB downloaded overnight)  
- **Subset extracted:** `data/zenodo/extracted/*.wav` — Raw_IRs, **5 m**, **24-bit**, angles  
  `0, 15, 30, 45, 60, 90, 120, 135, 150, 180` °

| Filename prefix | Display | Type / family | Honesty |
|-----------------|---------|---------------|---------|
| `ShureSM57` | Shure SM57 | dynamic cardioid | **MEASURED** |
| `SchoepsCMC5UCardioid` | Schoeps CMC5-U Cardioid | SDC cardioid | **MEASURED** |
| `NeumannU87AiCardioid` | Neumann U87 Ai Cardioid | LDC cardioid | **MEASURED** |
| `RoyerR121` | Royer R-121 | fig-8 ribbon | **MEASURED** |
| `ElectroVoiceRE20` | Electro-Voice RE20 | dynamic cardioid | **MEASURED** |
| `AKGC414Cardioid` | AKG C414 Cardioid | LDC cardioid | **MEASURED** |
| `ShureSM58` | Shure SM58 | dynamic cardioid | **MEASURED** |
| `SennheiserMD441` | Sennheiser MD 441 | dynamic hypercardioid | **MEASURED** |
| `NeumannU87AiOmni` | Neumann U87 Ai Omni | LDC omni | **MEASURED** |
| `NeumannU87AiBidirect` | Neumann U87 Ai Bidirect | LDC fig-8 | **MEASURED** |
| `AKGC414Omni` | AKG C414 Omni | LDC omni | **MEASURED** |
| `AKGC414Hyper` | AKG C414 Hyper | LDC hypercardioid | **MEASURED** |
| `AKGC414Bidirect` | AKG C414 Bidirect | LDC fig-8 | **MEASURED** |
| `SchoepsCMC5UOmni` | Schoeps CMC5-U Omni | SDC omni | **MEASURED** |
| `SchoepsCMC5UBidirect` | Schoeps CMC5-U Bidirect | SDC fig-8 | **MEASURED** |
| `Coles4038` | Coles 4038 | fig-8 ribbon (5 m **32-bit**) | **MEASURED** |
| `DPA4006` | DPA 4006 | measurement omni | **MEASURED** |
| `RodeNT2ACardioid` | Røde NT2-A Cardioid | LDC cardioid (1″ multipattern) | **MEASURED** |
| `RodeNT2AOmni` | Røde NT2-A Omni | LDC omni | **MEASURED** |
| `RodeNT2ABidirect` | Røde NT2-A Bidirect (fig-8) | LDC fig-8 | **MEASURED** |
| *(absent)* | sE Electronics SE2200A | — | **no measured data available; not planned** — not in Zenodo, no user data (not MEASURED; no preset) |
| *(absent)* | Røde NT5 | — | **no measured data available; not planned** — not in Zenodo, no user data; Idle chose NT2-A instead (LDC ≠ SDC matched-pair) (not MEASURED; no preset) |

Full zip kept on the box at `data/zenodo/Microphone_Impulse_Responses.zip` (not copied to Desktop by default — too large). Extracted MEASURED WAVs (20 MEASURED mics = 17 + NT2-A ×3 patterns) are included in Desktop sync tarballs when size permits; full zip is not.

## Secondary (ASSUMED) — synthetic proxies

Under `presets/assumed/` and matching plots under `plots/*/proxy_*`:

| id | Mimics | Honesty |
|----|--------|---------|
| proxy_dynamic_cardioid | SM57-ish | ASSUMED |
| proxy_sdc_cardioid | KM184-ish | ASSUMED |
| proxy_ldc_cardioid | U87-card-ish | ASSUMED |
| proxy_fig8_ribbon | Royer-ish | ASSUMED |
| proxy_supercardioid_dynamic | Beta58-ish | ASSUMED |
| proxy_omni_sdc | measurement omni-ish | ASSUMED |

## Structure LP

Room-engine **Structure LP is separate** — not fitted here.
