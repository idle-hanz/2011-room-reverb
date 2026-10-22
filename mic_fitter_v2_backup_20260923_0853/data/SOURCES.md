# Data sources used overnight

## Fit band (v2)

- **Analysis / loss frequencies:** **20 Hz – 16 kHz** (log-spaced, 64 points).  
  Overnight v1 used ~200 Hz–16 kHz.
- **Quasi-anechoic window:** 2 ms pre + **80 ms** post around direct peak (was 40 ms)  
  so LF bins near 20 Hz have usable SNR for the mild low shelf. Slightly more early-reflection
  leakage vs overnight — documented trade-off.

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

Full zip kept on the box at `data/zenodo/Microphone_Impulse_Responses.zip` (not copied to Desktop by default — too large). Extracted 6-mic WAVs (~83 MB) are included in the Desktop v2 tarball so Desktop is self-runnable without re-extract.

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
