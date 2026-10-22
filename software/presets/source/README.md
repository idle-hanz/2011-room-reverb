# Source radiation presets

Shipped with the app so Play and Render do not need `handoff_source_radiation_for_build` beside `software/`.

`engine/source_radiation.py` reads this folder first. Omni skips the stage, so the current sound stays bit-exact. The FDN inject uses each preset's diffuse filter, which does not follow yaw.

| id | tag | data |
|---|---|---|
| `omni` | exact bypass | none |
| `talking_head` | MEASURED-FIT | BYU average speech |
| `trumpet_byu` | MEASURED-FIT | BYU trumpet |
| `violin_byu` | MEASURED-FIT | BYU violin |
| `cab_1x12_closed` | ASSUMED | derived, no anechoic set |
| `cab_4x12_closed` | ASSUMED | derived, no anechoic set |
| `piano_grand_lid_open` | ASSUMED | placeholder |

TU Berlin fits stay out of this folder (`tu_*`, and the TU `trumpet`, `violin`, `cello`, `singer_soprano`, and `acoustic_guitar`). `combo_*` stays in the fitter pack (low-confidence fits).

Source directivity presets marked BYU are fitted to data from the BYU Acoustics Research Group directivity database (BYU ScholarsArchive); see T. W. Leishman et al., J. Acoust. Soc. Am. 149(3):1507, 2021, doi:10.1121/10.0003363. Raw balloons are not in this folder. The BYU pages state no licence; these files are the fitted shelf parameters only.
