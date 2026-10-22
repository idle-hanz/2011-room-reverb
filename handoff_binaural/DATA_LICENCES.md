# Binaural data licences (addendum to build_support/planning/LICENCE_AUDIT.md)

Written 30 Sep 2026 (BST). Same tags as LICENCE_AUDIT.md: **VERIFIED** = read from the source page, API metadata or the
file itself today; **ASSUMED** = not checked or inferred; **UNKNOWN** = could not be determined. Not legal advice.

## Summary verdicts (continues the LICENCE_AUDIT table)

| # | Item | Licence | Blocks sharing? |
|---|---|---|---|
| 23 | SADIE II v2-2, subjects D1 (KU100) + D2 (KEMAR), doi:10.5281/zenodo.12092466 | **Apache-2.0** (VERIFIED: Zenodo API `license.id = apache2.0`; SOFA `License` attribute "Copyright 2018, University of York, Licensed under the Apache License, Version 2.0"; LICENSE.txt in the record) | No. Ship `LICENSES/SADIE_II_Apache-2.0.txt` + `LICENSES/NOTICE_SADIE_II.txt` (states changes, Apache §4(b)), cite the paper |
| 24 | TH Köln KU100 far-field HRIRs (Bernschütz), doi:10.5281/zenodo.3928297 | **CC BY-SA 3.0** applied. CONFLICT (VERIFIED): SOFA `License` = "CC 3.0 BY-SA" and the DAGA paper say BY-SA; Zenodo metadata says `cc-by-3.0` | No, but **ShareAlike** on the derived THK data files (keep them as separate data files, like GRAS). Ask TH Köln (Christoph Pörschmann) to confirm which applies |
| 25 | MIT KEMAR (Gardner & Martin 1994) | "Copyright 1994 by the MIT Media Laboratory. It is provided free with no restrictions on use, provided the authors are cited" (VERIFIED, sound.media.mit.edu README) | Not used. Would be fine with citation |
| 26 | CIPIC HRTF database (UC Davis 2001) | Copyright Regents of the University of California; "permission to reproduce and/or use materials … for any purpose - educational, research or commercial", copyright notice must be kept; written acknowledgment requested for commercial products (VERIFIED, read_me.txt on the GitHub mirror amini-allight/cipic-hrtf-database; the original site is down) | Not used |
| 27 | FABIAN HRTF database (TU Berlin), doi:10.14279/depositonce-5718.5 | **CC BY 4.0** since v4, 22 Jan 2020 (VERIFIED, DepositOnce full record `dc.rights.uri` and version history) | Not used. The clean CC BY alternative if ShareAlike (item 24) is unwanted |

## What ships

- Only **derived** numbers: biquad parameters/coefficients per grid node, ITD tables, metrics. No HRIRs, no SOFA files.
  The downloaded SOFA files stay on the box in `binaural/data/` and are **not** copied to the Desktop or any publish.
- SADIE-derived presets (default `SADIE2_KU100`, plus `SADIE2_KEMAR`): Apache-2.0 notice + change statement.
- THK-derived preset (`THK_KU100_FF`): CC BY-SA 3.0, separate data files, `LICENSES/THK_KU100_CC-BY-SA-3.0.md`.
- About box / DATA_LICENCES text to add (web build too):
  > Binaural head presets "SADIE2_KU100" and "SADIE2_KEMAR" are derived from the SADIE II Database (University of York
  > AudioLab, subjects D1 and D2), doi:10.5281/zenodo.12092466, Copyright 2018 University of York, Apache License 2.0.
  > Paper: Armstrong et al., Appl. Sci. 8(11):2029, 2018, doi:10.3390/app8112029. Changes: diffuse-field EQ, smoothing,
  > L/R mirror averaging, biquad fit, ITD model.
  >
  > Binaural head preset "THK_KU100_FF" is adapted from the Spherical Far-Field HRIR Compilation of the Neumann KU100 by
  > Benjamin Bernschütz, TH Köln, doi:10.5281/zenodo.3928297, CC BY-SA 3.0; adapted data are shared under CC BY-SA 3.0.

## Sources checked (30 Sep 2026)

- https://zenodo.org/api/records/12092466 (SADIE II v2-2; also v2-1 10886409), LICENSE.txt and README from the record
- SOFA global attributes of `D1_48K_24bit_256tap_FIR_SOFA.sofa`, `D2_48K_24bit_256tap_FIR_SOFA.sofa`, `HRIR_FULL2DEG.sofa`, `HRIR_CIRC360.sofa`
- https://zenodo.org/api/records/3928297 (THK KU100 far field) and the DAGA 2013 paper in that record
- https://sound.media.mit.edu/resources/KEMAR/README
- https://github.com/amini-allight/cipic-hrtf-database (read_me.txt)
- https://depositonce.tu-berlin.de/items/3b423df7-a764-4ce1-9065-4e6034bba759/full (FABIAN)
