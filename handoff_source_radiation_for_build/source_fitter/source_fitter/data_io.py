"""Loaders for open directivity datasets -> one standard container.

Every loader returns a Dataset with directions expressed in the SOURCE frame:
    x = forward (facing / radiation reference axis), y = source's left, z = up.
mag_db[d, f] is band level in dB (any common reference; the fitter normalises).
Tags: VERIFIED = read from file/metadata/cited doc; ASSUMED = our choice.
"""
from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


@dataclass
class Dataset:
    name: str
    freqs: np.ndarray            # (F,) band centres Hz
    dirs: np.ndarray             # (D,3) unit vectors, source frame
    weights: np.ndarray          # (D,) quadrature weights (sum 1)
    mag_db: np.ndarray           # (D,F)
    band_ok: np.ndarray          # (F,) bool, bands usable for fitting
    provenance: Dict[str, str] = field(default_factory=dict)


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def frame_from_forward(fwd, up_hint=(0.0, 0.0, 1.0)):
    """Rotation matrix whose rows are source x(fwd), y(left), z(up) in array coords."""
    f = _unit(fwd)
    u = np.asarray(up_hint, float)
    u = u - np.dot(u, f) * f
    if np.linalg.norm(u) < 1e-6:
        u = np.array([0.0, 1.0, 0.0]) - f[1] * f
    u = _unit(u)
    l = np.cross(u, f)  # left = up x fwd  (right-handed x fwd, y left, z up)
    return np.stack([f, l, u])


# --------------------------------------------------------------------------
# BYU ScholarsArchive "Spatial Audio Library" CSV (1/3-oct, 5 deg, SH-resampled)
# Layout VERIFIED from files: "<BAND>\t<f>" then 72 rows (phi 0..355) x 37 cols
# (theta 0..180). Frontal axis at theta=0 (VERIFIED from dataset notes);
# original zenith at (theta=90, phi=0) (VERIFIED). phi=90 -> source LEFT is
# ASSUMED (handedness not stated; speech file is median-plane symmetrised).
# --------------------------------------------------------------------------
def read_byu_csv(path):
    bands, blocks, cur = [], [], None
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith("<BAND>"):
                bands.append(float(line.split()[-1]))
                cur = []
                blocks.append(cur)
                continue
            vals = [float(x) for x in line.strip(",").split(",") if x.strip() != ""]
            cur.append(vals)
    arr = np.array([np.array(b, float) for b in blocks])  # (F, 72, 37)
    return np.array(bands), arr


def byu_grid(n_phi=72, n_theta=37, flip_front=False):
    th = np.deg2rad(np.arange(n_theta) * 5.0)
    ph = np.deg2rad(np.arange(n_phi) * 5.0)
    TH, PH = np.meshgrid(th, ph)  # (72,37)
    x = np.cos(TH)
    z = np.sin(TH) * np.cos(PH)    # phi=0 -> up (VERIFIED zenith mapping)
    y = np.sin(TH) * np.sin(PH)    # phi=90 -> left (ASSUMED)
    d = np.stack([x, y, z], -1)
    if flip_front:
        d = d * np.array([-1.0, -1.0, 1.0])  # rotate 180 deg about z
    dth = np.deg2rad(5.0)
    w = np.sin(TH) * dth * (2 * np.pi / n_phi)
    cap = 2 * np.pi * (1 - np.cos(dth / 2)) / n_phi
    w[:, 0] = cap
    w[:, -1] = cap
    return d.reshape(-1, 3), (w / w.sum()).reshape(-1)


def load_byu(path, name, provenance, fmin=0.0, fmax=1e9, flip_front=None, stride=1):
    f, arr = read_byu_csv(path)
    F = len(f)
    if flip_front is None:
        # infer front: HF (>=2 kHz) level at theta=0 vs theta=180 (ASSUMED rule)
        hf = f >= 2000
        a0 = arr[hf][:, :, 0].mean() if hf.any() else 0
        a180 = arr[hf][:, :, -1].mean() if hf.any() else 0
        flip_front = bool(a180 > a0)
    d, w = byu_grid(arr.shape[1], arr.shape[2], flip_front=flip_front)
    mag = arr.transpose(1, 2, 0).reshape(-1, F)
    if stride > 1:
        # subsample phi and theta for speed; keep poles
        ph_idx = np.arange(0, arr.shape[1], stride)
        th_idx = np.unique(np.r_[np.arange(0, arr.shape[2], stride), arr.shape[2] - 1])
        sel = (ph_idx[:, None] * arr.shape[2] + th_idx[None, :]).reshape(-1)
        d, w, mag = d[sel], w[sel], mag[sel]
        w = w / w.sum()
    ok = (f >= fmin) & (f <= fmax)
    prov = dict(provenance)
    prov["front_axis"] = ("theta=180 column (inferred from HF level; ASSUMED)" if flip_front
                          else "theta=0 column (VERIFIED dataset note for BYU instruments/speech)")
    return Dataset(name, f, d, w, mag, ok, prov)


# --------------------------------------------------------------------------
# TU Berlin (Ackermann/Weinzierl et al.) 1/3-octave SOFA FreeFieldDirectivityTF
# 32-mic pentakis dodecahedron, r=2.06 m (VERIFIED from files).
# Azimuth CCW from +x toward +y (AES69 spherical convention; VERIFIED spec).
# Forward = SourceView reference mic (VERIFIED text in file); up = array zenith
# (Mic#13, el=90) (ASSUMED up hint). Quadrature weights equal (ASSUMED).
# --------------------------------------------------------------------------
TU_FORWARD_MIC = {  # from SourceView.Reference strings (VERIFIED, see provenance)
    "Trumpet_modern": 4, "Soprano_m": 4, "Acoustic_guitar_modern": 4,
    "Violin_modern": 25, "Violin_historical": 25, "Viola_modern": 25,
    "Cello_modern": 4, "Cello_historical": 4, "Tenor_trombone_modern": 4,
    "Bass_trombone_modern": 4, "Alto_trombone_historical": 4, "Tenor_trombone_historical": 4,
    "Bass_trombone_historical": 4, "Natural_trumpet_historical": 4,
    "Alto_saxophone_modern": 29, "Tenor_saxophone_modern": 29, "Bass_clarinet_modern": 29,
    "Clarinet_modern": 6, "Clarinet_historical": 6, "Oboe_modern": 6, "English_horn_modern": 6,
    "Classic_oboe_historical": 6, "Classic_oboe_historical_rom": 6, "Romantic_oboe_historical": 6,
    "Bassoon_modern": 1, "Baroque_bassoon_historical": 1, "Classic_bassoon_historical": 1,
    "Dulcian_historical": 1, "French_horn_modern": 21, "Natural_horn_historical": 21,
    "Tuba_modern": 4, "Double_bass_modern": 18, "Double_bass_historical": 26,
    "Double_action_harp_modern": 1, "Timpani": 13, "Pedal_timpani": 13,
    "Transverse_flute_modern": 27, "Keyed_flute_historical": 27, "Baroque_traverse_flute_historical": 27,
    "Viola_historical": 13, "Basset_horn_historical": 16, "Contrabassoon_modern": 6,
}
# where the reference text says "between Mic#a and Mic#b" we use the first mic (ASSUMED)


def load_tu(name, fmin=0.0, fmax=16000.0):
    import netCDF4 as nc
    p = os.path.join(DATA, "tub", "sofa3rd", "1b_Directivities3rdOctave_SOFA", f"{name}_3rdOctave.sofa")
    f = nc.Dataset(p)
    freqs = np.array(f["N"][:], float)
    tf = np.abs(np.array(f["Data.Real"][:]) + 1j * np.array(f["Data.Imag"][:]))[0]  # (32,F)
    rp = np.array(f["ReceiverPosition"][:]).reshape(-1, 3)
    az, el = np.deg2rad(rp[:, 0]), np.deg2rad(rp[:, 1])
    arr = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], -1)
    mic = TU_FORWARD_MIC.get(name, 4)
    R = frame_from_forward(arr[mic - 1])
    d = arr @ R.T
    with np.errstate(divide="ignore"):
        mag = 20 * np.log10(np.maximum(tf, 1e-12))
    energy = (tf ** 2).mean(0)
    ok = (energy > 0) & (freqs >= fmin) & (freqs <= fmax)
    # drop bands with >25% zero mics (no partial there)
    ok &= (tf > 0).mean(0) > 0.75
    prov = {
        "dataset": "TU Berlin — A Database of Anechoic Microphone Array Measurements of Musical Instruments (1b_Directivities3rdOctave_SOFA)",
        "url": "https://depositonce.tu-berlin.de/items/b194da8b-e98c-4761-9100-2b0bb6ba93e8",
        "doi": "10.14279/depositonce-19858 ; paper 10.17743/jaes.2022.0128",
        "file": os.path.basename(p),
        "license": str(getattr(f, "License", "")) + " (file attribute; NC = non-commercial)",
        "source_type": str(getattr(f, "SourceType", "")),
        "manufacturer": str(getattr(f, "SourceManufacturer", "")),
        "source_view": str(f["SourceView"].Reference),
        "forward_axis": f"Mic#{mic:02d} direction (from SourceView text; VERIFIED text, mapping ASSUMED where 'between' / 'slightly')",
        "grid": "32-mic pentakis dodecahedron r=2.06 m; equal quadrature weights ASSUMED",
        "measurement": "MEASURED (anechoic, 3rd-octave band average of partials)",
    }
    return Dataset(name, freqs, d, np.full(len(d), 1.0 / len(d)), mag, ok, prov)


# --------------------------------------------------------------------------
# DirPat (IEM Graz) LSPs_HATS_GuitarCabinets_Akustikmessplatz.sofa (GeneralFIR)
# 12 sources x 540 dirs x 2048 taps @44.1k (VERIFIED). Room 5x4x2.7 m, r=1 m
# (VERIFIED metadata) -> not anechoic: we window the direct sound (ASSUMED
# 0.5 ms pre / 3.0 ms post, half-Hann tails) -> bands < 500 Hz NOT fitted.
# ReceiverPosition columns read as (azimuth rad, colatitude rad, r) — units
# say degree but values span 0..6.1 / 0.2..2.9 (VERIFIED values; interpretation ASSUMED).
# Front axis inferred as the direction of max 2–8 kHz energy (ASSUMED).
# --------------------------------------------------------------------------
DIRPAT_NAMES = ["Genelec_8020", "Lambda_Labs_CX-1A", "Bruel_und_Kjaer_4128C_Kunstkopf", "Tannoy_System_1200",
                "Neumann_KH120A", "Yamaha_DXR8", "BM_1x12inch_driver_closed_cabinet",
                "BM_1x12inch_driver_open_cabinet", "BM_open_stacked_on_closed_withCrossoverNetwork",
                "BM_open_stacked_on_closed_fullrange", "Palmer_1x12inch", "Vibrolux_2x10inch"]
THIRD_OCT = np.array([20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000,
                      1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000], float)

_DIRPAT_CACHE = {}


def load_dirpat(idx, fmin=500.0, fmax=16000.0, pre_ms=0.5, post_ms=3.0, nfft=4096):
    import netCDF4 as nc
    p = os.path.join(DATA, "dirpat", "LSPs_HATS_GuitarCabinets_Akustikmessplatz.sofa")
    if p not in _DIRPAT_CACHE:
        f = nc.Dataset(p)
        _DIRPAT_CACHE[p] = (np.array(f["Data.IR"][:], np.float32), np.array(f["ReceiverPosition"][:]).reshape(-1, 3),
                            float(np.array(f["Data.SamplingRate"][:]).ravel()[0]),
                            {k: str(getattr(f, k)) for k in f.ncattrs()})
    irs, rp, fs, attrs = _DIRPAT_CACHE[p]
    x = irs[idx].astype(float)  # (540, 2048)
    az, col = rp[:, 0], rp[:, 1]
    arr = np.stack([np.sin(col) * np.cos(az), np.sin(col) * np.sin(az), np.cos(col)], -1)
    env = np.abs(x)
    pk = np.argmax(env, 1)
    t0 = int(np.percentile(pk, 5))  # earliest robust direct arrival across dirs
    # per-direction window around own peak region (direct only)
    n_pre, n_post = int(pre_ms * 1e-3 * fs), int(post_ms * 1e-3 * fs)
    win = np.zeros_like(x)
    ramp = int(0.5e-3 * fs)
    for i in range(x.shape[0]):
        # direct arrives within +-1 ms of t0 for r=1 m (source centre offsets)
        seg0 = max(0, t0 - n_pre)
        seg1 = min(x.shape[1], t0 + n_post)
        w = np.ones(seg1 - seg0)
        w[:ramp] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, ramp))
        w[-ramp:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, ramp))
        win[i, seg0:seg1] = x[i, seg0:seg1] * w
    X = np.abs(np.fft.rfft(win, nfft, axis=1)) ** 2
    fr = np.fft.rfftfreq(nfft, 1 / fs)
    bands = THIRD_OCT[(THIRD_OCT >= 100) & (THIRD_OCT <= 16000)]
    mag = np.zeros((x.shape[0], len(bands)))
    for j, fc in enumerate(bands):
        m = (fr >= fc * 2 ** (-1 / 6)) & (fr < fc * 2 ** (1 / 6))
        mag[:, j] = 10 * np.log10(np.maximum(X[:, m].mean(1), 1e-20))
    # front = argmax of smoothed HF energy (ASSUMED)
    hf = (bands >= 2000) & (bands <= 8000)
    e = 10 ** (mag[:, hf] / 10).mean(1) if False else (10 ** (mag[:, hf] / 10)).mean(1)
    wq = np.sin(col)
    sm = np.array([(wq * e * np.maximum(arr @ a, 0) ** 8).sum() for a in arr])
    fwd = arr[int(np.argmax(sm))]
    R = frame_from_forward(fwd)
    d = arr @ R.T
    w = np.sin(col)
    ok = (bands >= fmin) & (bands <= fmax)
    name = DIRPAT_NAMES[idx]
    prov = {
        "dataset": "DirPat (IEM Graz) — LSPs_HATS_GuitarCabinets_Akustikmessplatz.sofa",
        "url": "https://phaidra.kug.ac.at/detail/o:68229",
        "reference": attrs.get("References", ""),
        "license": attrs.get("License", "") + " — raw data NOT redistributed; derived parameters only",
        "source_type": name,
        "room": attrs.get("RoomType", ""),
        "window": f"direct-sound window {pre_ms} ms pre / {post_ms} ms post (ASSUMED); bands < {fmin:.0f} Hz not fitted",
        "forward_axis": "direction of max 2-8 kHz energy (inferred; ASSUMED) az=%.0f deg colat=%.0f deg" % (
            np.rad2deg(np.arctan2(fwd[1], fwd[0])) % 360, np.rad2deg(np.arccos(np.clip(fwd[2], -1, 1)))),
        "measurement": "MEASURED (quasi-anechoic windowed IRs, 1 m, non-anechoic room)",
    }
    return Dataset(name, bands, d, w / w.sum(), mag, ok, prov)


def byu_prov(title, cite, url, extra=None):
    p = {"dataset": f"BYU ScholarsArchive Spatial Audio Library — {title}", "url": url, "citation": cite,
         "license": "free & open access; cite as requested (no explicit licence text found)",
         "grid": "5 deg dual-equiangular 72x37 (SH-resampled, 1/3 octave)",
         "measurement": "MEASURED (anechoic, rotating semicircular array)"}
    if extra:
        p.update(extra)
    return p
