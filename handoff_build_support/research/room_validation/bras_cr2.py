"""BRAS CR2 (small seminar room, RWTH Aachen) scene constants + loaders.
Data: BRAS v3, doi:10.14279/depositonce-6726.3, CC BY-SA 4.0 (VERIFIED: DepositOnce record
dc.rights.uri and SOFA 'License' attribute). Data are NOT redistributed here; run fetch_bras.sh.
Positions VERIFIED from CR2_RIRs_Dodecahedron.sofa (EmitterPosition = dodecahedron mid-frequency
driver centre, ReceiverPosition = B&K 4134 capsule), metres, BRAS global frame (z=0 floor).
"""
import os, glob
import numpy as np
import scipy.io.wavfile as wavfile

BRAS_DIR = os.environ.get("BRAS_DIR", "/workspace/bras")
CR2_DIR = os.path.join(BRAS_DIR, "cr2", "1 Scene descriptions", "CR2 small room (seminar room)")
SR = 44100
TEMP_C = 19.5          # BRAS doc CR2 page (VERIFIED)
HUMIDITY_PCT = 41.7    # BRAS doc CR2 page (VERIFIED)
VOLUME_M3 = 145.0      # BRAS doc CR2 page (VERIFIED)
C_AIR = 331.3 + 0.606 * TEMP_C  # ~343.1 m/s (standard approximation)

SOURCES = {1: (0.931, -2.547, 0.723), 2: (0.119, 2.880, 0.723)}
RECEIVERS = {1: (-0.993, 1.426, 1.23), 2: (0.439, -0.147, 1.23), 3: (1.361, -0.603, 1.23),
             4: (-1.110, -0.256, 1.23), 5: (-0.998, -1.409, 1.23)}

# BRAS fitted absorption estimates (3_surface_descriptions.zip, _csv/fitted_estimates), 1/3-oct 20 Hz-20 kHz.
MAT_DIR = os.path.join(BRAS_DIR, "surf", "3 Surface descriptions", "_csv", "fitted_estimates")
MATS = ["ceiling", "concrete", "floor", "plaster", "windows"]


def load_rir(ls, mp):
    f = os.path.join(CR2_DIR, "RIRs", "wav", f"CR2_RIR_LS{ls}_MP{mp}_Dodecahedron.wav")
    sr, x = wavfile.read(f)
    assert sr == SR
    return x.astype(np.float64)


def load_material(name):
    f = os.path.join(MAT_DIR, f"mat_CR2_{name}.csv")
    rows = [list(map(float, l.split(","))) for l in open(f) if l.strip()]
    return np.array(rows[0]), np.array(rows[1]), np.array(rows[2])  # freqs, alpha, scattering


def reference_params():
    """BRAS-provided mean over the 10 dodecahedron RIRs (ITA-Toolbox, 1/3 oct)."""
    d = os.path.join(BRAS_DIR, "add", "4 Additional data", "Room acoustic parameters", "data")
    out = {}
    for p in ("T20", "EDT", "C80", "D50"):
        rows = [list(map(float, l.split(","))) for l in open(os.path.join(d, f"Evaluation_CR2_{p}.txt")) if l.strip()]
        out[p] = (np.array(rows[0]), np.array(rows[1]))
    return out
