"""Chosen datasets (licences VERIFIED 30 Sep 2026 from Zenodo API + SOFA License attribute)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"

DATASETS = {
    "SADIE2_KU100": {
        "display_name": "Neumann KU100 dummy head (SADIE II, subject D1)",
        "head": "Neumann KU100",
        "files": {44100: D / "sadie2/D1_HRIR_SOFA/D1_44K_16bit_256tap_FIR_SOFA.sofa",
                  48000: D / "sadie2/D1_HRIR_SOFA/D1_48K_24bit_256tap_FIR_SOFA.sofa"},
        "dataset": "SADIE II Database v2-2 (University of York AudioLab)",
        "doi": "10.5281/zenodo.12092466",
        "url": "https://zenodo.org/records/12092466",
        "paper_doi": "10.3390/app8112029",
        "licence": "Apache-2.0",
        "licence_file": "LICENSES/SADIE_II_Apache-2.0.txt",
        "share_alike": False,
        "notice": "Copyright 2018, University of York. Licensed under the Apache License, Version 2.0.",
    },
    "SADIE2_KEMAR": {
        "display_name": "GRAS KEMAR dummy head (SADIE II, subject D2)",
        "head": "KEMAR (GRAS 45BB)",
        "files": {44100: D / "sadie2/D2_HRIR_SOFA/D2_44K_16bit_256tap_FIR_SOFA.sofa",
                  48000: D / "sadie2/D2_HRIR_SOFA/D2_48K_24bit_256tap_FIR_SOFA.sofa"},
        "dataset": "SADIE II Database v2-2 (University of York AudioLab)",
        "doi": "10.5281/zenodo.12092466",
        "url": "https://zenodo.org/records/12092466",
        "paper_doi": "10.3390/app8112029",
        "licence": "Apache-2.0",
        "licence_file": "LICENSES/SADIE_II_Apache-2.0.txt",
        "share_alike": False,
        "notice": "Copyright 2018, University of York. Licensed under the Apache License, Version 2.0.",
    },
    "THK_KU100_FF": {
        "display_name": "Neumann KU100 far-field 3.25 m (TH Koeln, Bernschuetz)",
        "head": "Neumann KU100",
        "files": {48000: D / "thk_ku100/HRIR_FULL2DEG.sofa"},
        "dataset": "Spherical Far-Field HRIR Compilation of the Neumann KU100 (TH Koeln)",
        "doi": "10.5281/zenodo.3928297",
        "url": "https://zenodo.org/records/3928297",
        "paper_doi": None,
        "paper": "B. Bernschuetz, 'A Spherical Far Field HRIR/HRTF Compilation of the Neumann KU 100', Proc. DAGA 2013, pp. 592-595",
        "licence": "CC-BY-SA-3.0",
        "licence_note": "Zenodo metadata says CC BY 3.0; the SOFA file License attribute and the DAGA paper say CC BY-SA 3.0. Stricter reading (BY-SA) applied.",
        "licence_file": "LICENSES/THK_KU100_CC-BY-SA-3.0.md",
        "share_alike": True,
        "notice": "Benjamin Bernschuetz, TH Koeln. CC BY-SA 3.0.",
    },
}
