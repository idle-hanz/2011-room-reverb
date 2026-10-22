# Licence audit — datasets, references and code used by the 2011 Room Reverb rebuild

Written 27 Sep 2026 (BST). **This is not legal advice**; it is a checklist for what to do before sharing with Ben Supper (supperware.net) and publishing on idlehanz.com / github.com/idle-hanz/2011-room-reverb.

**Tags**

- **VERIFIED**: read from the source page, API metadata or the file itself on 27 Sep 2026.
- **ASSUMED**: not checked, or inferred.
- **UNKNOWN**: could not be determined.

## Summary verdicts

| # | Item | Licence | Blocks sharing? |
|---|---|---|---|
| 1 | Franco et al. mic IRs (Zenodo 4633508) | **CC BY 4.0** (VERIFIED, Zenodo API) | No. Attribute. |
| 2 | GRAS scattering/absorption database (DepositOnce 10.14279/depositonce-6726) | **CC BY-SA 4.0** (VERIFIED, `dc.rights.uri` on the item's full-record page) | No, but **ShareAlike** applies to GRAS-derived data files |
| 3 | TU Berlin 41-instrument directivities (DepositOnce 10.14279/depositonce-19858) | **Conflicting**: repository metadata says **In Copyright (rightsstatements.org InC 1.0)** (VERIFIED on the full record and DataCite). The SOFA files say **"cc by-nc-sa 4.0"** (VERIFIED in `Clarinet_modern_3rdOctave.sofa`) | **YES. Blocking** for the public repo and any commercial use until the authors clarify in writing |
| 4 | BYU ScholarsArchive directivity (Leishman et al.) | **No licence stated** (VERIFIED on the pages: "presented here for general usage", please cite) | Derived parameters with citation: low risk. Raw CSV redistribution: **ask first**. Commercial: **ask** |
| 5 | DirPat | "No license provided, ask the author" (VERIFIED) | **Yes, if shipped.** Not used in presets; it sits on the box in `/workspace/source_fitter/data/dirpat` and must stay out of any publish |
| 6 | Khrystoslavenko & Grubliauskas 2023 (doi 10.2478/rtuect-2023-0034) | **CC BY 4.0** (VERIFIED, Crossref) | No. Attribute. |
| 7 | Cox & D'Antonio, *Acoustic Absorbers and Diffusers* 3rd ed. (CRC), values via jmrplens/phonometry (repo **MIT**, VERIFIED GitHub API) | Book is copyright; individual numeric values are facts | No, if you cite and don't reproduce tables wholesale |
| 8 | Kamisiński et al., Acta Physica Polonica A 118(1), 2010 | UNKNOWN (not checked) | Numbers only, cite: low risk. Check before quoting tables |
| 9 | Textbook absorption α ("Sengpiel-style / Everest / typical NRC", ASSUMED_TEXTBOOK) | sengpielaudio licence UNKNOWN; Everest is copyright | Numeric facts: low risk. Cite; label ASSUMED_TEXTBOOK |
| 10 | PTB absorption data | **Not used**: no PTB source appears in any pack (VERIFIED by grep) | n/a |
| 11 | ISO 9613-1:1993 | Standard text © ISO; the formulas may be implemented | No. Don't copy the standard's text or tables; cite it |
| 12 | python-acoustics (equations used by air_fitter) | **BSD-3-Clause** (VERIFIED raw LICENSE, "Copyright (c) 2013, Python Acoustics") | No. Keep the notice if code is ported, not just the maths |
| 13 | three.js (vendored `three.min.js`) | **MIT** (VERIFIED header "Copyright 2010-2023 Three.js Authors") | No. Keep the header |
| 14 | Python deps: FastAPI **MIT**, uvicorn **BSD-3-Clause**, python-multipart **Apache-2.0**, numpy **BSD-3-Clause** (+0BSD/MIT/Zlib/CC0 parts), scipy **BSD-3** | all VERIFIED on PyPI metadata 27 Sep 2026 | No. Not redistributed, just listed in requirements |
| 15 | Fitter-only deps: matplotlib (PSF-based matplotlib licence), netCDF4 **MIT**, h5py **BSD-3** | VERIFIED PyPI | No |
| 16 | zig toolchain | MIT (ASSUMED; the compiler's output is not encumbered) | No |
| 17 | CLAP SDK | **MIT** (VERIFIED, GitHub API free-audio/clap) | No |
| 18 | VST3 SDK | **MIT since 3.8.0 (20 Oct 2025)**, VST2 excluded (VERIFIED, Steinberg developer portal) | No (use ≥ 3.8.0) |
| 19 | JUCE 8 | dual **AGPLv3 / JUCE 8 EULA** (VERIFIED, juce.com licence page + JUCE staff forum statement) | Only if JUCE is chosen: AGPL means the whole plugin is open source under the AGPL; otherwise a paid tier by revenue |
| 20 | Apple AU SDK | Apple terms (not checked) | check if AU is built |
| 21 | **The original 2011 Reaktor ensemble, its Structure screenshots and OCR notes** | **UNKNOWN authorship and ownership** | **Yes, for publishing the .ens / screenshots.** Publishing your own re-implementation code is a separate question; see §4 |
| 22 | **github.com/idle-hanz/2011-room-reverb** | **No LICENSE file** (GitHub API `license: null`, VERIFIED earlier today) | Without a licence, nobody may legally reuse it. Add one |

## 1. Per-dataset detail

### 1.1 Franco et al., measured microphone IRs: used for the mic colour presets (`mic_fitter`, SM57 etc.)

- Source: Zenodo record 4633508, doi:10.5281/zenodo.4633508. Licence **CC BY 4.0** (VERIFIED, Zenodo API `license.id = cc-by-4.0`).
- Allowed: redistribution and adaptation, including commercial use, with attribution. Shipping derived presets (fitted shelves, FIR partitions) is fine.
- Don't rehost the 1.5 GB raw zip; link to it.
- Attribution text to ship (in `DATA_LICENCES.md` and the About box):
  > Microphone colouration presets are derived from the measured microphone impulse responses of J. Franco, B. Băcilă, T. Brookes and E. De Sena, dataset doi:10.5281/zenodo.4633508, licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Dataset: "Multi-Angle, Multi-Distance Microphone Impulse Response Dataset". Paper: "A Multi-Angle, Multi-Distance Dataset of Microphone Impulse Responses", J. Audio Eng. Soc. 70(10):882–893, 2022, doi:10.17743/jaes.2022.0027. Changes: fitted to shelf/FIR models by the 2011 Room Reverb project.

### 1.2 GRAS: scattering presets (Track C `scattering_fitter`)

- Source: TU Berlin DepositOnce, doi:10.14279/depositonce-6726 (GRAS, Ground Truth for Room Acoustical Simulation). Authors: Aspöck, Brinkmann, Ackermann, Weinzierl, Vorländer.
- Licence **CC BY-SA 4.0** (VERIFIED, record metadata `dc.rights.uri`).
- Allowed: commercial use and redistribution, with attribution **and ShareAlike on adapted material**.
- How to comply: put every GRAS-derived value (scatter coefficients, absorption curves, CSV/JSON presets) in **separate data files** licensed CC BY-SA 4.0, e.g. `presets/scatter/gras_*.json` with a `LICENSE-DATA-CC-BY-SA-4.0` note.
- ShareAlike does not extend to the program code that merely reads those files (ASSUMED standard reading of CC BY-SA 4.0 §1(a) "Adapted Material"). It would apply if values were hard-coded into source; don't do that.
- Label the values "estimated" (as the GRAS authors describe them), never MEASURED.
- Attribution:
  > Scattering/absorption presets marked "GRAS" are adapted from L. Aspöck, F. Brinkmann, D. Ackermann, S. Weinzierl, M. Vorländer, "GRAS – Ground Truth for Room Acoustical Simulation," TU Berlin, doi:10.14279/depositonce-6726, CC BY-SA 4.0. Adapted data are shared under CC BY-SA 4.0.

### 1.3 TU Berlin 41 musical instruments directivity: source radiation presets

- Source: doi:10.14279/depositonce-19858. The SOFA attributes reference contact david.ackermann@tu-berlin.de and earlier record depositonce-5861.3.
- **Two conflicting statements (both VERIFIED)**:
  - Repository: **In Copyright** (InC 1.0).
  - File metadata: **CC BY-NC-SA 4.0**.
- Even the more permissive reading, CC BY-NC-SA, **forbids commercial use** and imposes ShareAlike on derived presets.
- Affected presets (source brief first set): **singer_soprano, acoustic_guitar, trumpet, violin, cello** (TU-derived), plus any `tu_*` preset.
- **Before sharing**:
  1. Email the authors (David Ackermann, TU Berlin Audio Communication) asking which licence governs, and for permission to redistribute fitted parameters in an open-source, possibly commercial, reverb.
  2. Until then, keep TU-derived presets **out of the public repo**. Use `trumpet_byu`, `violin_byu` and the other non-TU presets instead.
  3. A private share with Ben for evaluation is lower risk (non-commercial, not redistribution to the public), but label them "TU Berlin data, licence unresolved, not for redistribution".

### 1.4 BYU directivity (ScholarsArchive "directivity" collection)

- Pages checked: /directivity/1, 13, 15, 19. No licence stated (VERIFIED). The text says the data are "presented here for general usage" and asks users to cite Leishman et al., JASA 149(3):1507, 2021, doi:10.1121/10.0003363, plus the per-dataset recommended citations.
- Treat it as **all rights reserved with an informal permission to use**.
- Shipping *derived* fit parameters (a few shelf / one-pole numbers per preset) with citation is low risk (ASSUMED).
- Don't commit the raw CSV/balloon files to the repo.
- Email directivity@byu.edu for written permission, especially before any commercial release.
- Citation:
  > Source directivity presets marked "BYU" are fitted to data from the BYU Acoustics Research Group directivity database (BYU ScholarsArchive); see T. W. Leishman et al., J. Acoust. Soc. Am. 149(3):1507, 2021, doi:10.1121/10.0003363.

### 1.5 DirPat

"No license provided, ask the author" (VERIFIED). It was rejected and not used in presets. Exclude `source_fitter/data/dirpat` from any archive or repo.

### 1.6 Absorption values (Surfaces Track A)

- The 12 presets are `ASSUMED_TEXTBOOK`: typical α tables in the style of Sengpiel, Everest and NRC catalogues.
- Numbers are facts, but compilations can carry database rights in the EU/UK (ASSUMED).
- Mitigation: cite the sources per preset, round to 2 decimals, and don't copy whole tables verbatim.
- Khrystoslavenko & Grubliauskas 2023 is CC BY 4.0: attribute it.
- Cox & D'Antonio: cite the book; the jmrplens/phonometry repo is MIT (keep its notice if any of its code or data files are copied).

### 1.7 ISO 9613-1 air absorption

- Implementing the published equations is fine. Don't reproduce ISO's text or tables.
- Cite: ISO 9613-1:1993, *Acoustics — Attenuation of sound during propagation outdoors — Part 1: Calculation of the absorption of sound by the atmosphere*.
- If code is ported from python-acoustics, include its BSD-3 notice.

## 2. Code dependencies (repo `software/requirements.txt`, VERIFIED)

- numpy ≥ 1.24, fastapi ≥ 0.110, uvicorn[standard] ≥ 0.27, python-multipart ≥ 0.0.9: all permissive (VERIFIED, PyPI).
- **Missing from requirements**: `scipy`. Render imports `scipy.signal.lfilter` (VERIFIED). It is BSD-3, so there is no licence issue; add it for correctness.
- Vendored three.js: MIT. Keep the header. The build is deprecated r150+ (an upgrade note, not a licence issue).
- Fitters (not shipped in the app): scipy, matplotlib, netCDF4, h5py/pysofaconventions: permissive.
- Plugin phase: prefer CLAP (MIT) + VST3 (MIT ≥ 3.8.0). JUCE only if AGPL is acceptable or a licence is bought.

## 3. What to do before sharing (checklist)

1. **Add `LICENSE` to the repo.** Recommendation (ASSUMED; Idle's choice):
   - MIT or Apache-2.0 for the code. Apache adds a patent grant. GPL-3.0 if copyleft is wanted. If the plugin will ever use JUCE under AGPL, the code licence must be AGPL-compatible.
   - Add a separate **`DATA_LICENCES.md`** listing each preset family, its licence, and the attribution text from §1.
2. **Split presets by licence** into folders:

   | Folder | Licence |
   |---|---|
   | `presets/mic/` | CC BY 4.0 |
   | `presets/scatter/gras_*` | CC BY-SA 4.0 |
   | `presets/source/byu_*` | citation, permission pending |
   | `presets/source/tu_*` | **excluded from public** until cleared |
   | `presets/surfaces/` | project's own licence + citations |

3. **Emails to send**:
   - TU Berlin (Ackermann): which licence governs, and permission for the fitted presets.
   - BYU (directivity@byu.edu): permission for derived presets, commercial or otherwise.
   - Optional courtesy to the Franco / De Sena group (Surrey), and to the GRAS authors.
4. **Scrub before publishing**:
   - DirPat data;
   - raw BYU / TU / Franco archives;
   - the Reaktor `.ens` and Structure screenshots / OCR;
   - the `.venv`, `renders/` and any personal paths.
5. **Reaktor original**:
   - Establish who made the 2011 ensemble. If it isn't Idle's own work, ask the author before publishing screenshots or describing it as a port.
   - A clean-room re-implementation of an algorithm is generally not a copyright problem (ASSUMED; not legal advice), but naming and trade-dress should not imply NI or the original author endorses it.
   - "Reaktor" is a Native Instruments trademark: use it descriptively only.
   - Whether Ben Supper has any connection to the original is UNKNOWN; there is no mention of him in the packs.
6. **About box / README credits**: Franco et al., GRAS, BYU, the TU Berlin note (if cleared), ISO 9613-1, python-acoustics, three.js, FastAPI / uvicorn / numpy / scipy.
7. **Hosting on idlehanz.com**: the same licence files ship with the web build (`static/`). The measured-mic FIR partitions in the wasm blob are CC BY derived data, so attribution must also be visible in the web UI (About link).

## Sources checked (27 Sep 2026)

- Zenodo record API, https://zenodo.org/api/records/4633508
- GRAS: https://doi.org/10.14279/depositonce-6726 (DepositOnce full record, `dc.rights.uri` → CC BY-SA 4.0)
- TU Berlin instruments: doi:10.14279/depositonce-19858 (full record → rightsstatements.org InC/1.0; DataCite metadata); SOFA global attributes in `Clarinet_modern_3rdOctave.sofa`
- BYU ScholarsArchive: https://scholarsarchive.byu.edu/directivity/1 (/13, /15, /19)
- Crossref for doi:10.2478/rtuect-2023-0034
- GitHub API: jmrplens/phonometry (MIT), free-audio/clap (MIT), idle-hanz/2011-room-reverb (license null)
- python-acoustics LICENSE (BSD-3-Clause)
- Steinberg: https://steinbergmedia.github.io/vst3_dev_portal/pages/VST+3+Licensing/Index.html
- JUCE: https://juce.com/legal/juce-8-licence/
- PyPI JSON metadata for fastapi, uvicorn, python-multipart, numpy, scipy, matplotlib, netCDF4, h5py, pysofaconventions

## Update 2026-09-27: original 2011 Reaktor ensemble ownership (VERIFIED by the author)
Idle Hanz confirmed he built the original 2011 Reaktor ensemble himself, so the ensemble, its Structure design and his own Structure screenshots are his to publish. One remaining check: if any stock Native Instruments factory-library macros or modules were used unmodified inside it, cite them as NI components (the rebuild re-implements the ideas in new code, so no NI code is redistributed). Choose and add a LICENSE file to the public repo; data-derived presets keep their own licences (see above).
