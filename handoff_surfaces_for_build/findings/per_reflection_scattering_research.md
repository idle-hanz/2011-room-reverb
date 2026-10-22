# Per-reflection scattering / diffusion: research memo (Track C)

**Written:** Sat 26 Sep 2026, ~22:00 BST
**Rule:** I only use numbers found in a cited source. Tags:
- **VERIFIED_MEASURED**: the source prints it as an ISO 17497-1 measurement.
- **VERIFIED_CITED_EST**: the source prints it but itself calls it an estimate or guidance.
- **DERIVED**: computed by us from a stated model.
- **ASSUMED**: our choice.
- **NOT FOUND**: I searched and found no table.

Nothing here is MEASURED by us.

---

## 1. The two coefficients: they are not interchangeable

- **Random-incidence scattering coefficient s(f), ISO 17497-1** [ISO1, VM2000]. This is the fraction of *reflected* energy that leaves the specular direction.
  - Measured in a reverberation room with a turntable, using four reverberation times T1–T4. This gives α_s (static) and α_spec (rotating), and s = (α_spec − α_s)/(1 − α_s) [ISO1 via PHON].
  - One-third-octave bands, 100–5000 Hz full scale [PHON].
  - The base plate alone may not exceed s_base = 0.05 up to 500 Hz, rising to 0.25 at 5 kHz (ISO 17497-1 Table 1; VERIFIED from the ISO preview [ISO1p]). So **values around 0.05 or below are at the method's noise floor.**
  - The method is unreliable for strongly absorbing specimens: the standard asks for α_s ≤ 0.5 [PHON].
  - Definition and method: Vorländer & Mommertz 2000 [VM2000].
- **Diffusion coefficient d, ISO 17497-2.** This measures the *uniformity* of the polar response (goniometer, autocorrelation) [ISO2 via PHON; HCLD2000]. It says nothing about how much energy left specular.
  - Savioja & Svensson: GA engines "typically employ only the scattering coefficient because no clear interpretation of how the diffusion coefficient should be implemented exists" [SS2015 §III.B.3].
  - **→ Track C uses s(f) only. d is not used.**
- The diffuse part is conventionally rendered as **Lambertian** (energy per solid angle ∝ cos θ) [SS2015].

## 2. Published s(f) tables actually found

| Surface class | What I found | Tag | Source |
|---|---|---|---|
| Brick wall | GRAS scene11 brick wall, 1/3-oct 20 Hz–20 kHz; s ≈ 0.05 @1 kHz, 0.24 @2 kHz, 0.42 @4 kHz, 0.45 @8 kHz | VERIFIED_CITED_EST (GRAS: "estimated according to structural dimensions") | [GRAS] |
| Brick, ODEON guidance @~707 Hz | filled joints, not plastered: 0.05–0.10; open joints: 0.10–0.20 | VERIFIED_CITED_EST | [ZCR2006 T5; CR2005 T1] |
| Smooth plaster | GRAS scene09 plaster: s ≈ 0.03 @1 kHz → 0.06 @8 kHz (0.59 @20 kHz) | VERIFIED_CITED_EST | [GRAS] |
| Smooth surfaces / painted concrete (ODEON) | smooth general 0.02–0.05; smooth painted concrete 0.005–0.02 [ZCR2006] (0.01–0.03 in [CR2005]) | VERIFIED_CITED_EST | [ZCR2006, CR2005] |
| Concrete | GRAS scene08 painted concrete (0.06 @1 kHz, 0.13 @8 kHz); scene09/11 concrete | VERIFIED_CITED_EST | [GRAS] |
| Wood panelling | GRAS scene11 wood panels: 0.09 @1 kHz, 0.36 @2 kHz, 0.47 @4 kHz, 0.50 @8 kHz | VERIFIED_CITED_EST | [GRAS] |
| Parquet / linoleum | GRAS scene11 parquet / linoleum: ≤0.03 below 8 kHz | VERIFIED_CITED_EST | [GRAS] |
| Glass | GRAS scene09 windows: ≤0.03 below 8 kHz | VERIFIED_CITED_EST | [GRAS] |
| Acoustic ceiling tile | GRAS RockFon Sonar G (absorption measured by GRAS; scattering line has no separate provenance) | VERIFIED_CITED_EST | [GRAS] |
| Seating / audience | GRAS scene10/11 seating (e.g. scene10: 0.74 @500 Hz → 0.88 @20 kHz); ODEON audience 0.6–0.7 @707 Hz | VERIFIED_CITED_EST | [GRAS, ZCR2006] |
| Bookshelves | ODEON "bookshelf with some books" 0.3 @707 Hz only; **no measured spectrum found** | VERIFIED_CITED_EST / NOT FOUND | [ZCR2006, CR2005] |
| Carpet | **NOT FOUND** (no s table for carpet in any source I reached) | — | — |
| Heavy curtain | **NOT FOUND** | — | — |
| Battens, blocks, pyramids, V-grooves, hemispheres, vegetation | Cox & D'Antonio App. D, ISO 17497-1, credited per row (46 rows). E.g. pyramids h=30.5 cm: 0.22 @1 kHz, 0.41 @2 kHz, 0.86 @4 kHz, 1.00 @5 kHz. Battens h=w=10 cm measured by two labs: 0.28 vs 0.44 @630 Hz | VERIFIED_MEASURED (read via a secondary row-by-row transcription [PHONcat]; book page not viewed by me) | [CD2016 App D] |
| Ceiling diffuser (Lviv opera / rehearsal room) | 250→8k Hz octave: 0.10, 0.15, 0.30, 0.47, 0.69, 0.89 | VERIFIED_MEASURED | [KRP2010] |
| QRD N=7 (1 m²) | stated in text: min 0.46 @400 Hz, max 0.87 @2.5 kHz (full curve only in a figure, not digitised) | VERIFIED_MEASURED (2 points) | [KG2023] |
| QRD N=7 commercial, 0.2 m deep | diffusion (d) BEM tables exist in Cox App. B; **no s table read** | NOT FOUND (for s) | [CD2016 App B via PHON] |

**GRAS caveat (important):**
- GRAS gives absorption *and* scattering for 35 materials in 1/3-octave bands, 20 Hz–20 kHz.
- GRAS's own documentation says the scattering values were *estimated* from structural dimensions, not measured [GRAS doc §2.3].
- They are the most complete public per-material s(f) set I found. They must stay tagged **VERIFIED_CITED_EST, never MEASURED**.
- Where the ODEON @707 Hz guidance and GRAS disagree (painted concrete: GRAS 0.05 vs ODEON 0.005–0.02; brick: GRAS 0.03 vs ODEON 0.05–0.10), I report both. Both are estimates.

## 3. The "roughness scale" rule
- **ODEON** has a guide graph: choose s from the depth of the structure (mm) and the surface width (m), and take the higher of the two [ODEONguide]. I could not extract numbers from it, so it is **not used numerically**.
- **Christensen & Rindel 2005** [CR2005] split scattering into two parts:
  - surface roughness s_s (user-given, frequency function from the 707 Hz value);
  - edge diffraction s_d = 1 − K_w·K_l.
  - K = f/f_x below the limiting frequency and 1 above.
  - f_w = c·a*/(2(w·cos θ)²), f_l = c·a*/(2 l²), a* = 2·d_inc·d_refl/(d_inc + d_refl).
  - **Combined: s_r = 1 − (1 − s_d)(1 − s_s)** (their Eq. 1, VERIFIED; the limiting-frequency formulas were reconstructed from a garbled PDF text layer, so re-check them against the PDF before use).
  - They state that 3–5 % at 1 kHz may be enough for all smooth surfaces once diffraction is handled geometrically.
- **Empirically (Cox App. D rows)** the frequency where s passes ≈0.2 does *not* follow a single depth/λ rule:
  - sinusoid h = 5.1 cm reaches 0.22 at 1 kHz (h/λ ≈ 0.15);
  - pyramids h = 30.5 cm reach 0.22 at 1 kHz (h/λ ≈ 0.9).
  - Period and coverage matter as much as depth. **So no universal c/depth rule is claimed here.**

## 4. How image-source / hybrid engines treat specular vs scattered energy
- **Per reflection:** fraction (1 − s) continues specular and s is scattered (Lambert) [SS2015; CR2005 Fig. 2 "Specular (weight 1−s) / Scattered (weight s)"].
- ODEON's vector-based scattering mixes ray directions as (1 − s)·specular + s·Lambert-random [CR2005 §2.1].
- **Serial hits → (1 − s)^k.** If each hit keeps (1 − s_h) specular, the purely specular energy after hits h1…hk is ∏(1 − s_h), which equals (1 − s)^k for equal s.
  - This follows directly from the per-reflection split, including CR2005's per-reflection product (1 − s_d)(1 − s_s). Tag DERIVED from VERIFIED.
  - Once scattered, energy stays diffuse in most hybrids. Lewers' 1993 beam/radiosity hybrid: "following a diffuse reflection, all consecutive reflections will also be diffuse" [SS2015 §V].
- **Handover to late reverb:**
  - ODEON computes early reflections below a transition order TO with image sources plus early scattering rays, and above TO with ray-tracing/radiosity. "Typical values of TO are 1 to 4" [CR2005 §2].
  - RAVEN (Schröder 2011 thesis [S2011]): image sources for early specular, stochastic ray tracing with diffuse rain for scattering and the late part.
  - Koutsouris et al. 2013 switch from specular to diffuse per path [SS2015].
  - **For us:** early images (N=32 taps, orders 0–4) = the "ISM" part. The **FDN is the late model and is already excited by the early images (lock)**. Scattered energy of early taps is still early energy: it should appear as a smeared cluster near the tap, **not** as extra FDN input (which would double-count).

## 5. Temporal smearing of scattered energy
- **DERIVED (ours):** first-order Lambert reflection from an infinite plane, source and receiver at equal height h.
  - The contribution of an annulus at radius ρ ∝ cos θ_i·cos θ_r/(r_i²r_r²)·2πρ dρ, with r_i = r_r = √(h² + ρ²).
  - In x = t/t_spec (t_spec = 2h/c): energy density ∝ x^−5, CDF = 1 − x^−4.
  - Median arrival at x = 2^¼ = 1.19. **90 % of the energy lies before x = 10^¼ = 1.78.**
  - So the cluster width scales with the tap's own path length: ≈0.78·t_spec for 90 %. Width therefore grows with image order automatically (longer paths).
  - Finite walls, oblique geometry and multiple scattering change the shape. **It is a shaping heuristic, not a measurement.**
- **ODEON "oblique Lambert"** re-orients the Lambert lobe toward specular by (1 − s) [CR2005 §3.3]. This is directional; we model time only.

## 6. Cheap cluster decorrelators
- **Velvet noise** (sparse ternary ±1 sequences) sounds smoother than Gaussian noise at low densities [JK2007].
  - In [VHAL2017], low-pass-filtered velvet noise "smoother than Gaussian white noise even with the lowest pulse density they tested, 600 pulses/s" (citing [JK2007]).
- **Velvet-noise decorrelator** [APV2017]: a sparse velvet FIR replaces the exponentially decaying white-noise decorrelator (20–30 ms typical length, citing their ref [1]). It uses **87 % fewer operations** for comparable perceptual results, has no FFT latency, and supports segmented decay envelopes.
- **Scattering FDN** (Schlecht & Habets 2020 [SH2020]): velvet-like "scattering" *feedback* matrices *inside* the FDN.
  - **Deliberately not used.** Our lock is feed-forward scattering on early taps only; the FDN loop stays the unscaled ±1 Hadamard.
- **Short Schroeder allpass cascades** are the classic alternative. But the product already has an in-loop allpass layer (Structure Dffs) and a geometric per-tap allpass order in Render (`tap.allpass_stages`). Adding another allpass family risks confusing the layers, so a **sparse velvet cluster is preferred**. It is also multiply-free apart from one gain.

## 7. What Track C adopts (summary; details in the brief)
1. Per material s(f) at the 7 absorb bands (125–8000 Hz), from the logistic-in-log-f fit to the table above (`scattering_fitter/`).
2. Per early tap: specular energy S_b = ∏_hits(1 − s_h,b). Specular tap × a shelf fitted to √S. The scattered share is a Lambert-envelope velvet cluster (K = 16 pulses, width ≈ 0.78·t_spec, clamped 1–30 ms) × a shelf fitted to √(1 − |H_spec|²). So only the band that scatters is smeared.
3. Feed-forward on the early lane only. The FDN inject is unchanged (no double count). A muted face contributes no absorption **and** no scattering.

## Bibliography
- **[ISO1]** ISO 17497-1:2004 (+A1:2014), *Acoustics — Sound-scattering properties of surfaces — Part 1: Measurement of the random-incidence scattering coefficient in a reverberation room.* https://www.iso.org/standard/31397.html
- **[ISO1p]** ISO 17497-1:2004 preview (Table 1 base-plate limits): https://cdn.standards.iteh.ai/samples/31397/e9d568d96d07484bb9b1cf86ff566064/ISO-17497-1-2004.pdf
- **[ISO2]** ISO 17497-2:2012, *Part 2: Measurement of the directional diffusion coefficient in a free field.*
- **[VM2000]** M. Vorländer, E. Mommertz, "Definition and measurement of random-incidence scattering coefficients", *Applied Acoustics* 60(2):187–199, 2000. doi:10.1016/S0003-682X(99)00056-0
- **[HCLD2000]** T. J. Hargreaves, T. J. Cox, Y. W. Lam, P. D'Antonio, "Surface diffusion coefficients for room acoustics: Free-field measures", *JASA* 108(4):1710–1720, 2000. doi:10.1121/1.1310192
- **[CD2016]** T. J. Cox, P. D'Antonio, *Acoustic Absorbers and Diffusers: Theory, Design and Application*, 3rd ed., CRC Press 2016/2017, ISBN 978-1-4987-4099-9, doi:10.1201/9781315369211 (App. B diffusion, App. D measured scattering, Tables C.1–C.3 computed).
- **[PHON] / [PHONcat]** phonometry docs (J. M. Requena Plens): "Diffusers and Their Coefficients" https://jmrplens.github.io/phonometry/materials/diffusers/diffusers/ and "Published catalogues" https://jmrplens.github.io/phonometry/reference/catalogues/ (row-by-row transcription of Cox & D'Antonio App. D with page references; secondary source).
- **[GRAS]** L. Aspöck, F. Brinkmann, D. Ackermann, S. Weinzierl, M. Vorländer, *GRAS – Ground Truth for Room Acoustical Simulation*, TU Berlin DepositOnce. https://depositonce.tu-berlin.de/items/19a794ad-0359-410e-bc9c-ad96df1434d5 (3_surface_descriptions.zip; Documentation.pdf §2.3). Check the dataset licence before redistributing CSVs; attribution is kept in each preset.
- **[ZCR2006]** X. Zeng, C. L. Christensen, J. H. Rindel, "Practical methods to define scattering coefficients in a room acoustics computer model", *Applied Acoustics* 67:771–786, 2006. doi:10.1016/j.apacoust.2005.12.001 (Table 5). PDF: https://odeon.dk/pdf/A15-ApplAc_2006_Zeng_Lynge_Rindel.pdf
- **[CR2005]** C. L. Christensen, J. H. Rindel, "A new scattering method that combines roughness and diffraction effects", Forum Acusticum 2005. https://odeon.dk/pdf/CLC%20fa2005.pdf
- **[ODEONguide]** "ODEON and scattering" guide (depth/width graphs): https://www.yumpu.com/en/document/view/24889863/odeon-and-scatteringpdf
- **[KRP2010]** T. Kamisiński, J. Rubacha, A. Pilch, "The Study of Sound Scattering Structures for the Purposes of Room Acoustic Enhancement", *Acta Physica Polonica A* 118(1), 2010. https://przyrbwn.icm.edu.pl/APP/PDF/118/a118z1p19.pdf
- **[KG2023]** O. Khrystoslavenko, R. Grubliauskas, "Experimental Studies of the Sound Scattering Coefficient of the Diffuser in the Reverberation Chamber", *Environmental and Climate Technologies* 27(1):464–475, 2023. doi:10.2478/rtuect-2023-0034
- **[SS2015]** L. Savioja, U. P. Svensson, "Overview of geometrical room acoustic modeling techniques", *JASA* 138(2):708–730, 2015. doi:10.1121/1.4926438
- **[S2011]** D. Schröder, *Physically Based Real-Time Auralization of Interactive Virtual Environments*, PhD thesis, RWTH Aachen, 2011. https://publications.rwth-aachen.de/record/50580
- **[JK2007]** H. Järveläinen, M. Karjalainen, "Reverberation Modeling Using Velvet Noise", AES 30th Int. Conf., Saariselkä, 2007. https://secure.aes.org/forum/pubs/conferences/?elib=13941
- **[APV2017]** B. Alary, A. Politis, V. Välimäki, "Velvet-Noise Decorrelator", Proc. DAFx-17, pp. 405–411, 2017. https://www.dafx.de/paper-archive/2017/papers/DAFx17_paper_96.pdf
- **[VHAL2017]** V. Välimäki, B. Holm-Rasmussen, B. Alary, H.-M. Lehtonen, "Late Reverberation Synthesis Using Filtered Velvet Noise", *Applied Sciences* 7(5):483, 2017. doi:10.3390/app7050483
- **[SH2020]** S. J. Schlecht, E. A. P. Habets, "Scattering in Feedback Delay Networks", *IEEE/ACM TASLP* 28:1915–1924, 2020. doi:10.1109/TASLP.2020.3001395

**Not reached / not used:** PTB scattering database (none found online); CATT default scattering tables (only the CATT "diffusion series" page was indexed, and I did not read numbers from it); the full Schröder thesis text (cited for architecture only).
