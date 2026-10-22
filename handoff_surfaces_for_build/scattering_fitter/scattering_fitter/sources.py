"""Cited scattering data. Every number here is copied from the source named next to it.

Nothing in this file is MEASURED by us. See per_reflection_scattering_research.md for full bibliography.
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

BANDS7 = [125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0]  # == surfaces_fitter absorb_hz

GRAS_REF = ("Aspöck, Brinkmann, Ackermann, Weinzierl, Vorländer: GRAS – Ground Truth for Room Acoustical "
            "Simulation, TU Berlin DepositOnce, 3_surface_descriptions.zip, "
            "https://depositonce.tu-berlin.de/items/19a794ad-0359-410e-bc9c-ad96df1434d5 ; CSV line 3 = scattering; "
            "material descr files: 'Estimated data for absorption and scattering coefficients'; documentation §2.3: "
            "'Scattering coefficients were estimated according to structural dimensions of the materials.'")
COX_APPD_REF = ("Cox & D'Antonio, Acoustic Absorbers and Diffusers, 3rd ed., CRC 2016/2017, doi:10.1201/9781315369211, "
                "Appendix D (ISO 17497-1 measured, credited per row), printed pp. 497-502 — values read via the "
                "row-by-row transcription at https://jmrplens.github.io/phonometry/reference/catalogues/ "
                "(secondary transcription; primary book page not viewed by us)")
KAMISINSKI_REF = ("Kamisiński T., Rubacha J., Pilch A.: The Study of Sound Scattering Structures for the Purposes of Room "
                  "Acoustic Enhancement, Acta Physica Polonica A 118(1) 2010, "
                  "https://przyrbwn.icm.edu.pl/APP/PDF/118/a118z1p19.pdf — Table: ceiling-mounted diffuser, ISO 17497-1")
KHRYS_REF = ("Khrystoslavenko O., Grubliauskas R.: Experimental Studies of the Sound Scattering Coefficient of the Diffuser "
             "in the Reverberation Chamber, Environmental and Climate Technologies 27(1) 2023 464-475, "
             "doi:10.2478/rtuect-2023-0034 — QRD N7 values quoted in text (figure not digitised)")
ODEON_REF = ("Zeng, Christensen, Rindel: Practical methods to define scattering coefficients in a room acoustics computer "
             "model, Applied Acoustics 67 (2006) 771-786, doi:10.1016/j.apacoust.2005.12.001, Table 5; and "
             "Christensen & Rindel, 'A new scattering method that combines roughness and diffraction effects', "
             "Forum Acusticum 2005, https://odeon.dk/pdf/CLC%20fa2005.pdf, Table 1 (values at ~707 Hz)")



def gras_csv(name):
    """Return (freqs[31], alpha[31], s[31]) from a GRAS CSV (line1 f, line2 alpha, line3 s)."""
    with open(os.path.join(DATA, name + ".csv"), newline="") as fh:
        rows = [[float(x) for x in r] for r in csv.reader(fh) if r]
    return rows[0], rows[1], rows[2]


def thirds_window(f, s, lo=100.0, hi=10000.0):
    out = [(fi, si) for fi, si in zip(f, s) if lo * 0.99 <= fi <= hi * 1.01]
    return [a for a, _ in out], [b for _, b in out]


# Cox & D'Antonio App. D rows (1/3 octave 100..5000 Hz), None = cell empty ('–').
COX_F = [100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000]
COX_ROWS = {
    "periodic_1d_battens_h5cm": [0.01, 0, 0, 0.01, 0.02, 0.02, 0, 0.06, 0.16, 0.25, 0.25, 0.31, 0.36, 0.52, 0.44, 0.31, 0.32, 0.61],
    "pyramids_h30p5_L2h": [0, 0, 0, 0, 0, 0.02, 0.05, 0.08, 0.12, 0.18, 0.22, 0.22, 0.39, 0.41, 0.55, 0.69, 0.86, 1.0],
    "sinusoidal_1d_h5p1_L17p7": [0.02, 0.02, 0.03, 0.03, 0.04, 0.04, 0.05, 0.05, 0.1, 0.13, 0.22, 0.42, 0.59, 0.72, 0.8, 0.85, 0.87, 0.89],
}

# Kamisiński 2010 Table (octave, ISO 17497-1 measured), ceiling-mounted diffuser.
KAMISINSKI_F = [250, 500, 1000, 2000, 4000, 8000]
KAMISINSKI_S = [0.10, 0.15, 0.30, 0.47, 0.69, 0.89]

# Khrystoslavenko 2023: QRD N7 (1 m^2) — only two numbers are stated in the text for the untreated N7:
#   minimum 0.46 at 400 Hz; maximum 0.87 at 2500 Hz. (Charcoal-treated variants excluded.)
KHRYS_F = [400, 2500]
KHRYS_S = [0.46, 0.87]

# ODEON/Zeng 2006 Table 5 mid-frequency (~707 Hz) guidance ranges — used only as sanity anchors, not fitted.
ODEON_MID = {
    "smooth_painted_concrete": (0.005, 0.02),
    "smooth_surfaces_general": (0.02, 0.05),
    "brick_filled_joints_not_plastered": (0.05, 0.10),
    "brick_open_joints": (0.10, 0.20),
    "bookshelf_some_books": (0.30, 0.30),
    "rough_structures_0p3_0p5m": (0.40, 0.50),
    "audience_area": (0.60, 0.70),
}

# Library material -> evidence. kind: gras | cox | kamisinski | khrys_qrd
MATERIALS = [
    dict(id="plaster_smooth", src="gras", key="mat_scene09_plaster", tag="VERIFIED_CITED_EST",
         odeon="smooth_surfaces_general", note="GRAS scene09 plaster (estimated by GRAS)."),
    dict(id="gypsum_painted", src="gras", key="mat_scene10_plaster", tag="PROXY",
         odeon="smooth_surfaces_general", note="No gypsum-board s table found; GRAS scene10 (painted) plaster used as smooth-wall proxy."),
    dict(id="brick_unglazed", src="gras", key="mat_scene11_brickwall", tag="VERIFIED_CITED_EST",
         odeon="brick_filled_joints_not_plastered", note="GRAS scene11 brick wall (estimated by GRAS)."),
    dict(id="concrete_painted", src="gras", key="mat_scene08_paintedConcrete", tag="VERIFIED_CITED_EST",
         odeon="smooth_painted_concrete", note="GRAS scene08 painted concrete (estimated). ODEON guidance is lower (0.005-0.02 @707 Hz)."),
    dict(id="glass_window", src="gras", key="mat_scene09_windows", tag="VERIFIED_CITED_EST",
         odeon="smooth_surfaces_general", note="GRAS scene09 windows (estimated)."),
    dict(id="plywood_panel", src="gras", key="mat_scene11_woodPanels", tag="VERIFIED_CITED_EST",
         odeon=None, note="GRAS scene11 wood panels (estimated)."),
    dict(id="wood_parquet", src="gras", key="mat_scene11_parquet", tag="VERIFIED_CITED_EST",
         odeon="smooth_surfaces_general", note="GRAS scene11 parquet (estimated)."),
    dict(id="acoustic_ceiling_tile", src="gras", key="mat_RockFonSonarG_00deg", tag="VERIFIED_CITED_EST",
         odeon=None, note="GRAS RockFon Sonar G (absorption measured by GRAS; scattering line supplied without separate provenance → treat as estimate)."),
    dict(id="absorber_panel_2in", src="gras", key="mat_scene08_absorber", tag="VERIFIED_CITED_EST",
         odeon=None, note="GRAS scene08 absorber (estimated). NB ISO 17497-1 is unreliable for alpha>0.5 specimens."),
    dict(id="carpet_on_concrete", src="gras", key="mat_scene11_linoleum", tag="PROXY",
         odeon="smooth_surfaces_general", note="No carpet s table found; flat floor covering proxy = GRAS scene11 linoleum."),
    dict(id="carpet_on_foam", src="gras", key="mat_scene11_linoleum", tag="PROXY",
         odeon="smooth_surfaces_general", note="No carpet s table found; flat floor covering proxy = GRAS scene11 linoleum."),
    dict(id="heavy_curtain", src="cox", key="periodic_1d_battens_h5cm", tag="ASSUMED",
         odeon=None, note="No curtain s table found. ASSUMED proxy: folds ~5 cm deep ≈ Cox App.D periodic battens h=w=5 cm (measured, different object)."),
    # Diffuser options (not in the 12-material library; offered as extra presets)
    dict(id="diffuser_qrd_n7", src="khrys_qrd", key="qrd_n7", tag="VERIFIED_MEASURED(2 pts)+ASSUMED(shape)",
         odeon=None, note="Only 2 stated points (0.46@400 Hz, 0.87@2500 Hz). Slope and floor borrowed from Kamisiński fit (ASSUMED)."),
    dict(id="diffuser_ceiling_measured", src="kamisinski", key="kamisinski", tag="VERIFIED_MEASURED",
         odeon=None, note="Kamisiński 2010 ceiling diffuser, octave table 250-8k, ISO 17497-1."),
    dict(id="diffuser_pyramids", src="cox", key="pyramids_h30p5_L2h", tag="VERIFIED_MEASURED",
         odeon=None, note="Cox App.D pyramids h=30.5 cm, L=b=2h (secondary transcription)."),
]
