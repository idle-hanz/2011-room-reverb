# Source fitter: FIT REPORT (box run, 26 Sep 2026)

Model `radiation_shelf_plus_soft_one_pole`, schema `source_fitter.preset.v1`.
- **Loss:** dB error of the model vs the data, both normalised to their own sphere power average (DI-normalised), with the data floor-clipped at band max − 40 dB. There is also a per-band DI-match term (weight 0.5, ASSUMED).
- **Hold-out:** every 5th direction (index % 5 == 2) is never used in training.
- **Optimiser:** DE + least-squares polish. `lp_order` 1 and 2 are both fitted and the lower train loss is kept.

RMSE is over all fit bands (TU: 1/3-oct 100 Hz–10 kHz within data; BYU: dataset band range) and over train or hold-out directions.
DI values are those of the **model** (dB, re sphere average). The data DI per band is stored in each JSON under `fit.di_data_db`.

## Main presets
| id | label | tag | RMSE train dB | RMSE hold-out dB | DI 250 | DI 1k | DI 4k | diffuse-fit RMSE | LP order | data |
|---|---|---|---|---|---|---|---|---|---|---|
| `talking_head` | Talking head (average speech, 6 talkers) | MEASURED-FIT | 1.85 | 1.86 | 1.3 | 2.5 | 4.2 | 0.23 | 2 | BYU ScholarsArchive Spatial Audio Library — Average Speech Directivity |
| `singer_soprano` | Singer (soprano, TU Berlin) | MEASURED-FIT | 2.40 | 3.17 | 3.1 | 3.9 | 6.2 | 0.22 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `acoustic_guitar` | Acoustic guitar (steel/modern, TU Berlin) | MEASURED-FIT | 2.34 | 2.33 | 3.5 | 3.9 | 3.9 | 0.09 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `trumpet` | Trumpet (Bach 239, TU Berlin) | MEASURED-FIT | 1.97 | 1.82 | 2.2 | 5.1 | 13.2 | 0.64 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `trumpet_byu` | Trumpet (BYU, 160-3150 Hz) | MEASURED-FIT | 1.85 | 1.82 | 1.4 | 3.5 | 12.6 | 0.07 | 2 | BYU ScholarsArchive Spatial Audio Library — Trumpet Directivity |
| `violin` | Violin (modern, TU Berlin) | MEASURED-FIT | 2.17 | 2.67 | -0.2 | 0.8 | 1.5 | 0.01 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `violin_byu` | Violin (BYU, 200-2500 Hz) | MEASURED-FIT | 2.12 | 2.11 | 1.3 | 1.8 | 3.9 | 0.36 | 2 | BYU ScholarsArchive Spatial Audio Library — Violin Directivity |
| `cello` | Cello (modern, TU Berlin) | MEASURED-FIT | 2.40 | 3.17 | 1.9 | 2.6 | 3.6 | 0.17 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `combo_1x12` | Guitar combo 1x12 open-back (Fender Deluxe Reverb) | MEASURED-FIT | 5.49 | 5.48 | 9.8 | 13.4 | 19.1 | 1.03 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `combo_1x12_bluesjr` | Guitar combo 1x12 (Fender Blues Junior) | MEASURED-FIT | 5.54 | 5.49 | 7.9 | 12.8 | 19.4 | 1.30 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `combo_1x12_bluesdlx` | Guitar combo 1x12 (Fender Blues Deluxe) | MEASURED-FIT | 4.92 | 4.85 | 8.8 | 12.6 | 18.0 | 1.19 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `combo_1x10` | Guitar combo 1x10 (Fender Princeton Reverb) | MEASURED-FIT | 5.26 | 5.32 | 8.3 | 12.6 | 18.5 | 1.08 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `combo_2x12` | Guitar combo 2x12 (Fender Twin Reverb) | MEASURED-FIT | 5.66 | 5.73 | 9.0 | 14.0 | 20.7 | 1.20 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `combo_2x12_ac30` | Guitar combo 2x12 (Vox AC30) | MEASURED-FIT | 5.81 | 5.87 | 10.0 | 15.8 | 24.3 | 1.41 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `cab_1x12_closed` | Guitar cab 1x12 closed-back (ASSUMED, derived) | ASSUMED | — | — | 3.8 | 10.3 | 17.9 | 1.08 | 2 | none — derived |
| `cab_4x12_closed` | Guitar cab 4x12 closed-back (ASSUMED, derived) | ASSUMED | — | — | 5.4 | 13.4 | 19.4 | 0.98 | 2 | none — derived |
| `piano_grand_lid_open` | Grand piano, lid open (ASSUMED placeholder) | ASSUMED | — | — | 1.1 | 2.8 | 4.1 | 0.10 | 1 | none |
| `omni` | Omni (current engine sound — null) | ASSUMED-EXACT | — | — | -0.0 | -0.0 | -0.0 | 0.00 | 1 | none (analytic) |

**Tags:**
- `MEASURED-FIT` (VERIFIED data) means fitted to downloaded measured data (provenance in the JSON).
- `ASSUMED` means a derived or placeholder preset with no measurement:
  - `cab_1x12_closed` is derived from the Deluxe Reverb fit with the back-lobe/dipole removed and the broadband depth limited.
  - `cab_4x12_closed` is the same law with f0 and lp_hz halved (size ×2).
  - `piano_grand_lid_open` is a qualitative placeholder after Meyer (2009), with no numbers.
  - `omni` is the exact null.

## Quality notes
- **Speech / brass / strings / woodwinds (TU, BYU):** hold-out 1.6–3.3 dB. The smooth model captures the frequency trend of beaming and the front/back ratio, but not narrow lobes (violin/cello at some bands, flute side lobes).
- **French horn** (bell to the rear-right, player-dependent): hold-out 8.2 dB. The main axis is far from the TU 'forward' mic, so do **not** ship it without re-aiming.
- **Timpani, tuba:** 3–4 dB.
- **Guitar combos (BYU): LOW CONFIDENCE, 4.9–5.9 dB.**
  - The data combine an open-back pattern at LF (DI 4–6 dB; back ≈ front at 100–250 Hz) with very strong HF beaming (DI 15–20 dB at 1.6–4 kHz) and a rear lobe.
  - The v1 model's broadband 'dip' stage is frequency-independent, so the optimiser uses it for HF side rejection and over-attenuates the LF sides. At 250 Hz and 90° the model is about −30 dB where the data is about −3 to −6 dB.
  - Fixing `dip=0` did not help (6.1 dB).
  - **Recommendation:** v2 adds a frequency-limited dipole term (the broadband stage becomes a low shelf, or a two-band k-law). Until then, use `cab_1x12_closed` / `cab_4x12_closed` (limited broadband depth, no dipole null) for listening and treat `combo_*` as research presets.
- **Data we could NOT use:** DirPat guitar cabinets and loudspeakers (no licence; non-anechoic; ambiguous orientation). There is no piano in the TU/BYU sets and no 4x12 in any open anechoic set we found.

## All presets
| id | label | tag | RMSE train dB | RMSE hold-out dB | DI 250 | DI 1k | DI 4k | diffuse-fit RMSE | LP order | data |
|---|---|---|---|---|---|---|---|---|---|---|
| `acoustic_guitar` | Acoustic guitar (steel/modern, TU Berlin) | MEASURED-FIT | 2.34 | 2.33 | 3.5 | 3.9 | 3.9 | 0.09 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `cab_1x12_closed` | Guitar cab 1x12 closed-back (ASSUMED, derived) | ASSUMED | — | — | 3.8 | 10.3 | 17.9 | 1.08 | 2 | none — derived |
| `cab_4x12_closed` | Guitar cab 4x12 closed-back (ASSUMED, derived) | ASSUMED | — | — | 5.4 | 13.4 | 19.4 | 0.98 | 2 | none — derived |
| `cello` | Cello (modern, TU Berlin) | MEASURED-FIT | 2.40 | 3.17 | 1.9 | 2.6 | 3.6 | 0.17 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `combo_1x10` | Guitar combo 1x10 (Fender Princeton Reverb) | MEASURED-FIT | 5.26 | 5.32 | 8.3 | 12.6 | 18.5 | 1.08 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `combo_1x12` | Guitar combo 1x12 open-back (Fender Deluxe Reverb) | MEASURED-FIT | 5.49 | 5.48 | 9.8 | 13.4 | 19.1 | 1.03 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `combo_1x12_bluesdlx` | Guitar combo 1x12 (Fender Blues Deluxe) | MEASURED-FIT | 4.92 | 4.85 | 8.8 | 12.6 | 18.0 | 1.19 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `combo_1x12_bluesjr` | Guitar combo 1x12 (Fender Blues Junior) | MEASURED-FIT | 5.54 | 5.49 | 7.9 | 12.8 | 19.4 | 1.30 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `combo_2x12` | Guitar combo 2x12 (Fender Twin Reverb) | MEASURED-FIT | 5.66 | 5.73 | 9.0 | 14.0 | 20.7 | 1.20 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `combo_2x12_ac30` | Guitar combo 2x12 (Vox AC30) | MEASURED-FIT | 5.81 | 5.87 | 10.0 | 15.8 | 24.3 | 1.41 | 2 | BYU ScholarsArchive Spatial Audio Library — Guitar Amplifier Directivi |
| `omni` | Omni (current engine sound — null) | ASSUMED-EXACT | — | — | -0.0 | -0.0 | -0.0 | 0.00 | 1 | none (analytic) |
| `piano_grand_lid_open` | Grand piano, lid open (ASSUMED placeholder) | ASSUMED | — | — | 1.1 | 2.8 | 4.1 | 0.10 | 1 | none |
| `singer_soprano` | Singer (soprano, TU Berlin) | MEASURED-FIT | 2.40 | 3.17 | 3.1 | 3.9 | 6.2 | 0.22 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `talking_head` | Talking head (average speech, 6 talkers) | MEASURED-FIT | 1.85 | 1.86 | 1.3 | 2.5 | 4.2 | 0.23 | 2 | BYU ScholarsArchive Spatial Audio Library — Average Speech Directivity |
| `trumpet` | Trumpet (Bach 239, TU Berlin) | MEASURED-FIT | 1.97 | 1.82 | 2.2 | 5.1 | 13.2 | 0.64 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `trumpet_byu` | Trumpet (BYU, 160-3150 Hz) | MEASURED-FIT | 1.85 | 1.82 | 1.4 | 3.5 | 12.6 | 0.07 | 2 | BYU ScholarsArchive Spatial Audio Library — Trumpet Directivity |
| `tu_alto_saxophone_modern` | Alto saxophone modern (TU Berlin) | MEASURED-FIT | 2.39 | 2.46 | 1.5 | 2.3 | 6.7 | 0.17 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_alto_trombone_historical` | Alto trombone historical (TU Berlin) | MEASURED-FIT | 2.05 | 1.79 | 1.6 | 4.7 | 13.2 | 0.64 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_baroque_bassoon_historical` | Baroque bassoon historical (TU Berlin) | MEASURED-FIT | 2.26 | 2.66 | 1.2 | 2.0 | 4.1 | 0.19 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_baroque_traverse_flute_historical` | Baroque traverse flute historical (TU Berlin) | MEASURED-FIT | 3.36 | 2.97 | 0.8 | 1.9 | 4.1 | 0.13 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_bass_clarinet_modern` | Bass clarinet modern (TU Berlin) | MEASURED-FIT | 2.55 | 2.69 | 1.7 | 1.9 | 3.1 | 0.04 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_bass_trombone_historical` | Bass trombone historical (TU Berlin) | MEASURED-FIT | 1.83 | 1.45 | 1.8 | 5.4 | 15.2 | 0.68 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_bass_trombone_modern` | Bass trombone modern (TU Berlin) | MEASURED-FIT | 1.84 | 1.79 | 2.3 | 8.1 | 14.4 | 1.06 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_basset_horn_historical` | Basset horn historical (TU Berlin) | MEASURED-FIT | 3.19 | 3.08 | 3.0 | 4.6 | 10.1 | 0.37 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_bassoon_modern` | Bassoon modern (TU Berlin) | MEASURED-FIT | 2.33 | 2.19 | -1.2 | 1.2 | 6.2 | 0.24 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_cello_historical` | Cello historical (TU Berlin) | MEASURED-FIT | 2.15 | 2.55 | 1.9 | 2.3 | 2.9 | 0.06 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_clarinet_historical` | Clarinet historical (TU Berlin) | MEASURED-FIT | 2.67 | 2.55 | 2.4 | 4.3 | 16.9 | 0.24 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_clarinet_modern` | Clarinet modern (TU Berlin) | MEASURED-FIT | 2.76 | 2.40 | 3.0 | 4.2 | 14.2 | 0.10 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_classic_bassoon_historical` | Classic bassoon historical (TU Berlin) | MEASURED-FIT | 2.29 | 2.60 | 2.1 | 2.4 | 3.4 | 0.08 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_classic_oboe_historical` | Classic oboe historical (TU Berlin) | MEASURED-FIT | 2.70 | 2.45 | 1.4 | 2.2 | 13.1 | 0.37 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_classic_oboe_historical_rom` | Classic oboe historical rom (TU Berlin) | MEASURED-FIT | 2.95 | 2.71 | 1.5 | 2.7 | 10.3 | 0.08 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_contrabassoon_modern` | Contrabassoon modern (TU Berlin) | MEASURED-FIT | 2.41 | 2.34 | 0.9 | 1.0 | 2.3 | 0.08 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_double_action_harp_modern` | Double action harp modern (TU Berlin) | MEASURED-FIT | 3.23 | 3.26 | -1.0 | 0.6 | 1.5 | 0.57 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_double_bass_historical` | Double bass historical (TU Berlin) | MEASURED-FIT | 2.11 | 2.49 | 1.6 | 2.0 | 2.9 | 0.06 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_double_bass_modern` | Double bass modern (TU Berlin) | MEASURED-FIT | 2.18 | 2.49 | -3.4 | -5.5 | -6.8 | 0.36 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_dulcian_historical` | Dulcian historical (TU Berlin) | MEASURED-FIT | 2.06 | 2.45 | 1.0 | 2.0 | 3.5 | 0.09 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_english_horn_modern` | English horn modern (TU Berlin) | MEASURED-FIT | 2.23 | 2.18 | 2.8 | 3.5 | 7.1 | 0.12 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_french_horn_modern` | French horn modern (TU Berlin) | MEASURED-FIT | 4.23 | 8.20 | 3.5 | 18.3 | 31.5 | 0.55 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_keyed_flute_historical` | Keyed flute historical (TU Berlin) | MEASURED-FIT | 3.45 | 3.27 | -1.9 | 3.7 | 4.6 | 0.22 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_natural_horn_historical` | Natural horn historical (TU Berlin) | MEASURED-FIT | 2.50 | 2.83 | 5.0 | 15.2 | 18.7 | 1.07 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_natural_trumpet_historical` | Natural trumpet historical (TU Berlin) | MEASURED-FIT | 2.01 | 1.88 | 3.1 | 5.2 | 14.3 | 0.57 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_oboe_modern` | Oboe modern (TU Berlin) | MEASURED-FIT | 2.47 | 3.04 | -0.4 | 1.3 | 3.0 | 0.29 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_pedal_timpani` | Pedal timpani (TU Berlin) | MEASURED-FIT | 2.66 | 3.35 | -3.1 | -1.9 | -0.9 | 0.53 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_romantic_oboe_historical` | Romantic oboe historical (TU Berlin) | MEASURED-FIT | 2.95 | 2.71 | 1.5 | 2.7 | 10.3 | 0.08 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_tenor_saxophone_modern` | Tenor saxophone modern (TU Berlin) | MEASURED-FIT | 2.31 | 2.53 | 1.2 | 3.9 | 7.1 | 0.31 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_tenor_trombone_historical` | Tenor trombone historical (TU Berlin) | MEASURED-FIT | 1.95 | 1.64 | 0.7 | 3.5 | 13.5 | 0.56 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_tenor_trombone_modern` | Tenor trombone modern (TU Berlin) | MEASURED-FIT | 1.92 | 1.78 | 3.1 | 7.6 | 15.1 | 0.89 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_timpani` | Timpani (TU Berlin) | MEASURED-FIT | 3.99 | 3.75 | -3.2 | -2.0 | -1.3 | 0.20 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_transverse_flute_modern` | Transverse flute modern (TU Berlin) | MEASURED-FIT | 3.46 | 3.76 | -3.2 | 1.2 | 3.9 | 0.34 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_tuba_modern` | Tuba modern (TU Berlin) | MEASURED-FIT | 3.89 | 3.04 | 3.1 | 13.4 | 25.3 | 1.18 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_viola_historical` | Viola historical (TU Berlin) | MEASURED-FIT | 2.25 | 3.07 | -1.4 | -0.1 | 0.7 | 0.07 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_viola_modern` | Viola modern (TU Berlin) | MEASURED-FIT | 2.02 | 2.44 | 0.9 | 1.4 | 2.3 | 0.04 | 2 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `tu_violin_historical` | Violin historical (TU Berlin) | MEASURED-FIT | 2.15 | 3.08 | 1.1 | 1.6 | 2.1 | 0.07 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `violin` | Violin (modern, TU Berlin) | MEASURED-FIT | 2.17 | 2.67 | -0.2 | 0.8 | 1.5 | 0.01 | 1 | TU Berlin — A Database of Anechoic Microphone Array Measurements of Mu |
| `violin_byu` | Violin (BYU, 200-2500 Hz) | MEASURED-FIT | 2.12 | 2.11 | 1.3 | 1.8 | 3.9 | 0.36 | 2 | BYU ScholarsArchive Spatial Audio Library — Violin Directivity |

## Licences
- **TU Berlin** (DOI 10.14279/depositonce-19858): the SOFA attribute says CC BY-NC-SA 4.0. The presets are derived parameters: attribute them and keep them non-commercial unless cleared.
- **BYU ScholarsArchive:** open access, cite as requested. No explicit licence text was found.

Plots: `plots/polars/*.png` (horizontal and median plane, 250 Hz–8 kHz, lines = model, dots = data), `plots/balloons/*.png`, `plots/di/*.png` (model vs data DI).
