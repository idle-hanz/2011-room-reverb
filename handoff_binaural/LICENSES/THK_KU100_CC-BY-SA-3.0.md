# TH Köln Neumann KU100 far-field HRIR compilation: licence notice for derived data

Applies to: `presets/binaural/THK_KU100_FF.json` and `presets/binaural/sos_tables/*/THK_KU100_FF*.json` only.

- Source: B. Bernschütz, "Spherical Far-Field HRIR Compilation of the Neumann KU100", TH Köln,
  doi:10.5281/zenodo.3928297 (file used: `HRIR_FULL2DEG.sofa`, 16020-point Gauss grid, 3.25 m, 48 kHz).
- Paper: B. Bernschütz, "A Spherical Far Field HRIR/HRTF Compilation of the Neumann KU 100", Proc. DAGA 2013, pp. 592–595.
- Licence: **Creative Commons Attribution-ShareAlike 3.0** (CC BY-SA 3.0), https://creativecommons.org/licenses/by-sa/3.0/
  - VERIFIED 30 Sep 2026: the SOFA global attribute `License` reads `CC 3.0 BY-SA`; the DAGA 2013 paper says
    "freely available under a Creative Commons CC BY-SA 3.0 license".
  - CONFLICT (VERIFIED): the Zenodo record metadata says `cc-by-3.0` (no ShareAlike). The stricter reading
    (BY-SA 3.0) is applied here until the authors clarify.
- Changes made: diffuse-field equalisation computed from the full sphere, 1/6-octave smoothing, left/right mirror
  averaging at 60 grid nodes, fitting to RBJ biquad parameters and coefficients at 44.1 and 48 kHz, ITD analysis
  (tabulated LF ITD per lateral angle and a Woodworth fit). No raw HRIRs are redistributed.
- **ShareAlike**: these derived data files are themselves offered under CC BY-SA 3.0. Program code that merely reads
  them is not Adapted Material (ASSUMED standard reading, same as the GRAS note in LICENCE_AUDIT.md §1.2); do not
  hard-code these values into source.
- Attribution text to ship:
  > Binaural preset "THK_KU100_FF" is adapted from the Spherical Far-Field HRIR Compilation of the Neumann KU100 by
  > Benjamin Bernschütz, TH Köln (doi:10.5281/zenodo.3928297), licensed CC BY-SA 3.0. Adapted data are shared under
  > CC BY-SA 3.0. Changes: diffuse-field EQ, smoothing, L/R mirror averaging, biquad fit, ITD model.
