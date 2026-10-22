# Source radiation: research notes and bibliography

Project: '2011 Room Reverb' rebuild, SOURCE RADIATION (directivity, orientation, apparent size).
Tag legend: **VERIFIED** means the claim comes from the cited source or from the live code/data file named. **ASSUMED** means it is our design choice or an engineering estimate.
Numbers are given only where we actually read them in the source or computed them from a downloaded dataset. Dataset-derived numbers come from our fits in `source_fitter/` (see `FIT_REPORT.md`).

---
## 1. Human voice and head

| Source | What it measured | Key content used here |
|---|---|---|
| Chu, W.T. & Warnock, A.C.C. (2002). *Detailed directivity of sound fields around human talkers.* NRC Canada, Research Report IRC-RR-104. doi:10.4224/20378930 | 40 talkers, 1/3-octave bands 160–8000 Hz, a microphone array around the talker | **VERIFIED:** the canonical speech-directivity reference. Directivity is weak at low frequency and grows with frequency. Front-to-back level difference rises with band, and the pattern is roughly symmetric left/right. Numeric tables live in the report; **we fit BYU data instead** because we could not download NRC tables in a machine-readable form. |
| Bellows, S.; Pincock, D.; Whiting, J.; Leishman, T. W. et al. (2019 dataset; paper JASA 149(3):1507–1523, 2021). *High-resolution directivity of speech / singing.* doi:10.1121/10.0003363. Data: https://scholarsarchive.byu.edu/directivity/1/ | Full-sphere 5° (azimuth) × 5° (polar) spherical data, 1/3-oct 100 Hz–10 kHz, median-plane symmetrised | **VERIFIED, downloaded (SpeechDirectivity.csv) and FITTED** → preset `talking_head`. |
| Monson, B. B., Hunter, E. J., Story, B. H. (2012). *Horizontal directivity of low- and high-frequency energy in speech and singing.* JASA 132(1):433–441. doi:10.1121/1.4725963 | 15 speakers, 13 mics at 15° steps, 60 cm, horizontal plane only | **VERIFIED:** energy above ~5 kHz is markedly more directional than lower bands, for both speech and singing. Supports the high shelf plus beaming LP in the model. |
| Kob, M. & Jers, H. (1999). *Directivity measurement of a singer.* JASA 105(2):1003. doi:10.1121/1.425813 | singer directivity, including elevation | **VERIFIED (abstract):** singer directivity depends on the vowel/phoneme and radiates noticeably below the horizontal (mouth + chest reflection). Motivates `aim_el` and `b_ud`. |
| Marshall, A. H. & Meyer, J. (1985). *The directivity and auditory impressions of singers.* Acustica 58:130–140 | singers (choir), directivity in horizontal plane | **VERIFIED (bibliographic):** directivity and perceived impression of singers. Cited for the singer–audience orientation issue. |
| Pörschmann, C. & Arend, J. M. (2021/2023). *Investigating phoneme-dependencies of spherical voice directivity patterns.* JASA 149(6), 2021, doi:10.1121/10.0005401; and follow-up doi:10.1121/10.0016821. Data: Zenodo 7452117 (SOFA) | 13 subjects, full-sphere, phoneme-dependent | **VERIFIED (existence/format):** SOFA files per phoneme. Not downloaded or fitted (time). A phoneme-variation preset could come later. |
| Brinkmann, F. et al. (2017/2019). *FABIAN HRTF / head-and-torso database.* TU Berlin, doi:10.14279/depositonce-5718 | head-and-torso HRTFs (receiver side) | **ASSUMED relevance:** by reciprocity the head-shadow part of voice directivity resembles HRTF ILD. Not used numerically. |
| BYU KEMAR HATS mouth-simulator directivity, https://scholarsarchive.byu.edu/directivity/16/ | HATS with mouth simulator | **VERIFIED exists.** Not downloaded. Would be a 'dummy-head talker' preset. |

**Take-aways for the model (VERIFIED from our fit of BYU speech; see FIT_REPORT DI table):**
- The voice is nearly omni at 100–250 Hz, reaching DI ≈ 3–5 dB at a few kHz and higher toward 8–10 kHz.
- The head shadows the back by up to ~10+ dB at HF.
- The pattern is mirror-symmetric L/R, so the preset fixes `b_lr=0` and `aim_az=0`.
- It has an up/down asymmetry (chest and chin), which the fitted `b_ud`/`aim_el` capture.

## 2. Musical instruments

| Source | Content | Use |
|---|---|---|
| Weinzierl, S., Vorländer, M., et al. / Ackermann, D., Brinkmann, F., Zotter, F., Kob, M., Weinzierl, S. *Comparative evaluation of interpolation methods for the directivity of musical instruments* / *Database of the directivity of 41 musical instruments.* JAES 2023/2024, doi:10.17743/jaes.2022.0128. Data: DepositOnce doi:10.14279/depositonce-19858, https://depositonce.tu-berlin.de/items/b194da8b-e98c-4761-9100-2b0bb6ba93e8 (Shabtai et al. 2017 JASA 141(3):1246, doi:10.1121/1.4976071 describes the original 32-mic measurement) | 41 modern and historical instruments, 32-mic surrounding spherical array (pentakis dodecahedron) r = 2.06 m, anechoic, 3rd-octave SOFA 20 Hz–20 kHz | **VERIFIED, downloaded and FITTED** (trumpet, violin, cello, acoustic guitar, soprano singer, and the whole `tu_*` library). **Licence: the SOFA attribute says CC BY-NC-SA 4.0**. This is non-commercial: fitted parameter presets are derived data. Flag it before any commercial release. |
| BYU Spatial Audio Library, https://scholarsarchive.byu.edu/directivity/ (Trumpet /13, Violin /15, guitar amps /19: Edelman, Anderson, Bellows, Leishman 2026) | 5° spherical, 1/3-oct | **VERIFIED, downloaded and FITTED:** trumpet_byu, violin_byu, six guitar combos. |
| Pätynen, J. & Lokki, T. (2010). *Directivities of symphony orchestra instruments.* Acta Acust. united Ac. 96(1):138–167. doi:10.3813/AAA.918265 | 22 mics, 14 instruments, anechoic | **VERIFIED (bibliographic):** orchestral directivities. Not downloaded (data availability uncertain). |
| Meyer, J. (2009). *Acoustics and the Performance of Music* (5th ed.). Springer. doi:10.1007/978-0-387-09517-2 | classic directivity tables (principal radiation directions per band) | **VERIFIED (bibliographic):** Meyer's tables give qualitative piano behaviour: a lid-open grand radiates strongly in the lid-reflection direction and the soundboard radiates downward. The `piano_grand_lid_open` preset is **ASSUMED**: its shape follows Meyer's description and no numbers are taken from the book. |
| ITA Aachen: Pollow, M. et al. / OpenDAFF directivities; RAVEN, doi:10.1016/j.apacoust... (see §4) | instrument directivity in DAFF format | **VERIFIED exists (format).** Not downloaded. |
| DirPat (IEM Graz), Brandner, M., Frank, M., Rudrich, D. *DirPat — database and viewer of 2D/3D directivity patterns of sound sources and receivers.* AES 144th Conv., e-Brief 425, 2018. https://phaidra.kug.ac.at/detail/o:68229 | loudspeakers, HATS, guitar cabinets | **Downloaded and REJECTED:** the file says "No license provided, ask the author". It was measured in a non-anechoic room at 1 m and the orientation is ambiguous. Not redistributed and not fitted. |
| Piston-in-baffle theory: Kinsler, Frey, Coppens, Sanders, *Fundamentals of Acoustics*, 4th ed. (Wiley 2000); Beranek & Mellow, *Acoustics: Sound Fields and Transducers* (2012). D(θ) = 2 J1(ka sinθ)/(ka sinθ); −3 dB half-angle narrows once ka > 1; beaming onset f ≈ c/(2πa) | theory | **VERIFIED (standard result):** used for the physical meaning of `size`. For a 12" driver (a ≈ 0.13 m effective, ASSUMED) the onset is ≈ 340/(2π·0.13) ≈ 420 Hz. For a 4x12 (array ~0.6 m wide, ASSUMED) the horizontal onset is ~90 Hz, and the vertical onset differs from the horizontal one. |
| CLF (Common Loudspeaker Format, http://www.clfgroup.org/) and AFMG GLL (EASE) | loudspeaker balloons: CLF1 10°, CLF2 5° resolution, 1/1 or 1/3 octave | **VERIFIED (format).** A future `import_clf.py` could fit loudspeaker presets from CLF text files with the same fitter. |

**Take-aways (VERIFIED from our fits, FIT_REPORT):**
- Brass (trumpet) is omni-ish below ~500 Hz and beams strongly along the bell above ~1–2 kHz; data DI reaches ~10+ dB at 4–8 kHz.
- Violin and cello have complex, frequency-dependent lobes; the smooth model captures the trend only (hold-out RMSE 2–3 dB).
- Guitar combos (BYU):
  - They combine an open-back dipole-like pattern at LF (the back can be louder than the front at 100 Hz) with severe HF beaming, with data DI up to ~20 dB at 4–6 kHz.
  - The smooth model reaches only ~5–5.5 dB RMSE here (low confidence).
- There is no measured 4x12 or piano in the open data we could use. Both presets are **ASSUMED**.

## 3. Perception: facing, width, size

| Source | Finding (VERIFIED from source) |
|---|---|
| Neuhoff, J. G., Rodstrom, M.-A., Vaidya, T. (2001). *The audible facing angle.* Acoustics Research Letters Online 2(4):109–114. doi:10.1121/1.1403595 (also JASA abstract "The minimum audible facing angle", doi:10.1121/1.4744371; Neuhoff 2003 Ecol. Psychol. 15(4) doi:10.1207/s15326969eco1504_7) | Listeners can tell which way a talker/loudspeaker faces. The minimum audible facing angle (MAFA) is ~15° about a 0° reference and grows off-axis (~21° at 30°, per our notes). It depends on source directivity and the listening environment. |
| Neuhoff, J. G. (2001, ICAD). *Perceiving acoustic source orientation in three-dimensional space.* | Orientation is perceptible in 3D, and the direct/reflected ratio matters. |
| Kato, H., Takemoto, H., Nishimura, R., Mokhtari, P. (2010). *Spatial acoustic cues for the auditory perception of speaker's facing direction.* Proc. ICA 2010 (Sydney) | Facing errors were ~23.5° (azimuth) and ~12.9° (elevation). Overall level changed by up to ~13 dB at 1.2 m and ~10 dB at 2.4 m as the talker turned. The cues are level and spectral tilt (front/back), with small ILD (≤ ~2 dB) for left/right. |
| Imbery, C., Ewert, S. D., et al. (2019). *Auditory facing angle perception: the effect of different source positions in a real and an anechoic environment.* Acta Acust. united Ac. 105(3):492–505. doi:10.3813/AAA.919331 | Facing perception works in rooms as well as anechoically. Reverberant rooms can improve it through the direct-to-reverberant spectral balance (DRR and its frequency dependence), not just level. |
| Otondo, F. & Rindel, J. H. (2004/2005). *The influence of the directivity of musical instruments in a room.* Acta Acust. united Ac. 90(6):1178–1184 (2004). PDF: odeon.dk | Instrument directivity audibly changes room acoustic parameters and timbre in auralisation (ODEON). Using time-varying or multi-channel directivity changed perceived width and naturalness. |
| Wang, L. M. & Vigeant, M. C. (2008). *Evaluations of output from room acoustic computer modeling and auralization due to different sound source directionalities.* Applied Acoustics 69(12):1281–1293. doi:10.1016/j.apacoust.2007.09.004 | Listeners distinguished omni from directional sources in auralisations. Realistic (measured, multi-channel) sources sounded more natural and more spacious. |
| Barron, M. & Marshall, A. H. (1981). *Spatial impression due to early lateral reflections in concert halls.* JSV 77(2):211–232. doi:10.1016/S0022-460X(81)80020-X | Early lateral energy (roughly 5–80 ms) drives spatial impression / ASW. The lateral energy fraction is the standard measure. |
| Potard, G. & Burnett, I. (2004). *Decorrelation techniques for the rendering of apparent sound source width in 3D audio displays.* Proc. DAFx-04, Naples | Multiple decorrelated point sources spread over an extent produce controllable apparent source width. Decorrelation is the key cue. |
| Morimoto, M. & Iida, K. / Blauert, J. (1997). *Spatial Hearing* (MIT Press) | ASW grows with interaural decorrelation (1−IACC_E), low-frequency lateral energy and level. |

**Take-aways (ASSUMED synthesis, backed by the rows above):**
- The strongest facing cue in a room is the **direct and early spectral tilt relative to the diffuse tail**, plus the overall direct level. The tail is roughly invariant to facing, so the key design rule is to **keep the FDN inject orientation-independent (diffuse power average) by default**. Turning the source then changes the D/R spectral ratio exactly as in a real room.
- Early lateral reflections matter too: when the source faces a side wall, that wall's first-order images get the on-axis (bright) spectrum.
- 'Big vs small' comes from:
  1. a lower beaming onset f ≈ c/(2πa) for a big radiator;
  2. multi-point emission, meaning decorrelated arrivals from different points of the extent, which widens ASW;
  3. at near field, a level gradient across the source and the absence of a single point-like HF arrival.
  See `source_size_and_dimension.md`.

## 4. How other engines do it

| Engine / method | Source | How directivity is represented (VERIFIED from docs) |
|---|---|---|
| ODEON | https://odeon.dk (User manual, 'Directivity patterns'; application note on GLL/CLF import) | Point sources with directivity files: `.SO8` (legacy balloon), CLF (CF1/CF2) import, GLL via app note. Balloon per octave band, applied per ray / image by emission direction. The source can be aimed (azimuth/elevation/rotation). |
| CATT-Acoustic | https://www.catt.se (CATT v9 manual) | `.SD0/.SD1/.SD2` directivity files per octave band, CLF import. Source aim point + roll. Applied per ray/image emission direction. |
| EASE (AFMG) | https://www.afmg.eu (GLL) | GLL: loudspeaker balloons, complex data, multi-way, arrays. |
| RAVEN (ITA Aachen) | Schröder, D. (2011). *Physically based real-time auralization of interactive virtual environments.* PhD, RWTH Aachen. OpenDAFF: https://www.opendaff.org | OpenDAFF directivity (magnitude spectra or IRs on a sphere). Image sources look up the emission direction. |
| Steam Audio (Valve) | https://valvesoftware.github.io/steam-audio/ (IPLDirectivity) | Parametric weighted dipole: `dipoleWeight` (0 = omni, 1 = dipole) and `dipolePower` (sharpness), plus a custom callback. Applied to direct and reflections. Broadband (no frequency dependence). |
| Resonance Audio (Google) | https://resonance-audio.github.io/resonance-audio/ | Source directivity r(θ) = \|(1−α) + α cosθ\|^sharpness (alpha 0 = omni, 0.5 = cardioid, 1 = figure-8). Broadband. |
| Wwise (Audiokinetic) | https://www.audiokinetic.com/library (Attenuation: cone attenuation, 'Spread'; 'radial emitter') | Cone attenuation (inner/outer angle + outer volume + outer LPF/HPF), which gives frequency-dependent facing with a low-pass. 'Spread' and radial emitters approximate volumetric sources. |
| Unreal / MetaSounds | Unreal docs 'Sound Attenuation: Focus / Non-spatialized radius / 3D stereo spread' | Focus azimuth + priority/volume scaling, spread for extended sources. |
| SH directivity | Mehra, R., Antani, L., Kim, S., Manocha, D. (2014). *Source and listener directivity for interactive wave-based sound propagation.* IEEE TVCG 20(4):495–503. doi:10.1109/TVCG.2014.38; Zotter, F. & Frank, M., *Ambisonics* (Springer 2019) doi:10.1007/978-3-030-17207-7 | Directivity encoded as spherical-harmonic coefficients per band. It rotates cheaply (Wigner-D) and low orders (N = 1–4) capture smooth patterns. |

**Our choice (ASSUMED, justified):**
- Use a **parametric low-order model** mirroring the mic model rather than a lookup balloon or SH set. The costs are: per image, one broadband gain, one RBJ high shelf and one soft one-pole (or two), which is cheap, alias-free, and has **exact identity on axis and for omni** (null test).
- Frequency dependence is essential: Steam and Resonance use broadband patterns only, which sound like a volume knob, not a turning source.
- The Wwise cone-LPF approach supports that 'LPF off-axis' is the perceptually dominant ingredient.
- **FDN inject weighting**: diffuse-field power average of the directivity, i.e. 10^(−DI(f)/10) relative to on-axis. This is the same quantity ODEON/CATT use when a directional source feeds a statistical reverberant tail (the directivity factor Q in the Hopkins–Stryker equation; Kuttruff, *Room Acoustics*, 6th ed., CRC 2016, doi:10.1201/9781315372150). **VERIFIED principle.** We fit it as gain + one RBJ shelf per preset (`diffuse_inject` in the preset).

## 5. Open data formats
- **SOFA** (AES69-2022), https://www.sofaconventions.org: the `GeneralTF`/`FreeFieldDirectivityTF` conventions hold directivity. TU Berlin data is SOFA (netCDF4/HDF5). **VERIFIED:** read with netCDF4 on the box.
- **OpenDAFF**, https://www.opendaff.org: RAVEN/ITA format.
- **BYU CSV**: 72×37 grids per 1/3-octave band (our reader `data_io.load_byu`). The axis convention was VERIFIED by symmetry (θ=0 front, φ=0 up). The left/right sign (φ=90 = left) is ASSUMED, and it matters only for presets with `b_lr` ≠ 0.
- **CLF/GLL**: loudspeaker formats (see §2).

## 6. Full reference list (URLs / DOIs)
1. Chu & Warnock 2002, NRC IRC-RR-104, doi:10.4224/20378930
2. Leishman et al. 2021, JASA 149(3):1507, doi:10.1121/10.0003363; data https://scholarsarchive.byu.edu/directivity/1/
3. Monson, Hunter, Story 2012, JASA 132(1):433, doi:10.1121/1.4725963
4. Kob & Jers 1999, JASA 105(2):1003, doi:10.1121/1.425813
5. Marshall & Meyer 1985, Acustica 58:130–140
6. Pörschmann & Arend 2021, JASA 149(6), doi:10.1121/10.0005401; 2023 doi:10.1121/10.0016821; data https://zenodo.org/records/7452117
7. TU Berlin 41-instrument directivity DB: doi:10.14279/depositonce-19858; paper doi:10.17743/jaes.2022.0128; Shabtai et al. 2017 JASA 141(3):1246 doi:10.1121/1.4976071
8. BYU Spatial Audio Library: https://scholarsarchive.byu.edu/directivity/ (items 1, 13, 15, 16, 19)
9. Pätynen & Lokki 2010, Acta Acust 96(1):138, doi:10.3813/AAA.918265
10. Meyer 2009, *Acoustics and the Performance of Music*, doi:10.1007/978-0-387-09517-2
11. DirPat, Brandner et al. AES 144 (2018); https://phaidra.kug.ac.at/detail/o:68229
12. Neuhoff et al. 2001 ARLO 2(4):109, doi:10.1121/1.1403595
13. Kato et al. 2010, Proc. ICA 2010
14. Imbery et al. 2019, Acta Acust 105(3):492, doi:10.3813/AAA.919331
15. Otondo & Rindel 2004, Acta Acust 90(6):1178
16. Wang & Vigeant 2008, Appl. Acoust. 69(12):1281, doi:10.1016/j.apacoust.2007.09.004
17. Barron & Marshall 1981, JSV 77(2):211, doi:10.1016/S0022-460X(81)80020-X
18. Potard & Burnett 2004, DAFx-04
19. Mehra et al. 2014, IEEE TVCG 20(4):495, doi:10.1109/TVCG.2014.38
20. Resonance Audio docs; Steam Audio docs; Audiokinetic Wwise docs; ODEON manual; CATT manual; AFMG GLL; CLF group; OpenDAFF; SOFA AES69 (URLs above)
21. Kuttruff, *Room Acoustics* 6th ed. doi:10.1201/9781315372150
22. Zotter & Frank, *Ambisonics*, doi:10.1007/978-3-030-17207-7

*Note on verification depth:*
- Rows marked "(abstract)" or "(bibliographic)" were checked at citation or abstract level only. We did not transcribe their tables.
- Every numeric directivity in the presets comes from the downloaded TU Berlin and BYU files.
- DOIs 2, 3, 4, 6, 7, 9, 12, 14, 16, 17 and 19 were checked against Crossref on 26 Sep 2026 (box).
- DOI 1 (NRC) is a DataCite DOI and resolves via doi.org.
