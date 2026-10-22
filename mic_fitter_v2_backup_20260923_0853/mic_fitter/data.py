"""Data loading: Zenodo Franco et al. IRs when present, else ASSUMED synthetic."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .synthetic import build_dataset, log_freqs

ZENODO_DOI = "10.5281/zenodo.4633508"
ZENODO_URL = "https://zenodo.org/records/4633508"
ZENODO_ZIP_NAME = "Microphone_Impulse_Responses.zip"

# Preferred Franco mic IDs (folder / filename stem prefix) for overnight fit
PREFERRED_ZENODO_MICS = [
    ("ShureSM57", "dynamic_cardioid", "Shure SM57 — dynamic cardioid"),
    ("SchoepsCMC5UCardioid", "sdc_cardioid", "Schoeps CMC5-U Cardioid — SDC"),
    ("NeumannU87AiCardioid", "ldc_cardioid", "Neumann U87 Ai Cardioid — LDC"),
    ("RoyerR121", "fig8_ribbon", "Royer R-121 — fig-8 ribbon"),
    ("ElectroVoiceRE20", "dynamic_cardioid", "Electro-Voice RE20 — dynamic cardioid"),
    ("AKGC414Cardioid", "ldc_cardioid", "AKG C414 Cardioid — LDC multipattern"),
]

# Filename: ShureSM57_5m_30Deg_24bit.wav
WAV_RE = re.compile(
    r"^(?P<mic>.+?)_(?P<dist>[\d.]+)m_(?P<angle>\d+)Deg(?:_(?P<bit>\d+bit))?$",
    re.IGNORECASE,
)


def discover_zenodo_wavs(data_dir: Path) -> Dict[str, Dict[float, Path]]:
    """
    Scan data_dir for Franco-style WAVs.
    Returns mic_key -> {angle_deg: path}, preferring 24-bit over 32-bit when both exist.
    """
    data_dir = Path(data_dir)
    if not data_dir.exists():
        return {}

    # mic -> angle -> list of (bit_pref, path)  bit_pref lower is better (24 before 32)
    found: Dict[str, Dict[float, List[Tuple[int, Path]]]] = {}
    for p in data_dir.rglob("*.wav"):
        m = WAV_RE.match(p.stem)
        if not m:
            continue
        mic = m.group("mic")
        angle = float(m.group("angle"))
        bit = (m.group("bit") or "").lower()
        pref = 0 if "24" in bit else (1 if "32" in bit else 2)
        found.setdefault(mic, {}).setdefault(angle, []).append((pref, p))

    out: Dict[str, Dict[float, Path]] = {}
    for mic, ang_map in found.items():
        out[mic] = {}
        for ang, candidates in ang_map.items():
            candidates.sort(key=lambda t: t[0])
            out[mic][ang] = candidates[0][1]
    return out


def magnitude_db_from_wav(path: Path, freqs: np.ndarray, n_fft: int = 16384) -> np.ndarray:
    """Quasi-anechoic magnitude on `freqs` from a mic IR WAV.

    v2 fit band starts at 20 Hz. The overnight 40 ms post-window is only ~0.8
    periods at 20 Hz, so LF bins were noisy/biased. We lengthen the post-window
    to 80 ms (~1.6 periods at 20 Hz, ~3.2 at 40 Hz) and bump default n_fft.
    Trade-off: slightly more early-reflection leakage vs usable LF for the
    mild low shelf. Documented in README / SOURCES / MORNING_REPORT.
    """
    import soundfile as sf

    audio, sr = sf.read(str(path), always_2d=False)
    if getattr(audio, "ndim", 1) > 1:
        audio = np.mean(audio, axis=-1)
    audio = np.asarray(audio, dtype=float)
    # Quasi-anechoic: window around the direct-arrival peak (v2: 80 ms post)
    peak = int(np.argmax(np.abs(audio)))
    pre = int(0.002 * sr)
    post = int(0.080 * sr)
    start = max(0, peak - pre)
    end = min(len(audio), peak + post)
    seg = audio[start:end]
    if len(seg) < 64:
        seg = audio[: min(len(audio), n_fft)]
    w = np.hanning(len(seg))
    n_fft = max(n_fft, 1 << int(np.ceil(np.log2(max(len(seg), 256)))))
    spec = np.fft.rfft(seg * w, n=n_fft)
    f_hz = np.fft.rfftfreq(n_fft, d=1.0 / sr)
    mag = np.abs(spec)
    # Slightly wider smooth at LF where bin SNR is weaker
    kern = np.ones(9) / 9.0
    mag = np.convolve(mag, kern, mode="same")
    mag_i = np.interp(freqs, f_hz, mag, left=mag[0], right=mag[-1])
    return 20.0 * np.log10(np.maximum(mag_i, 1e-12))


def _meta_for(mic_key: str) -> Tuple[str, str]:
    for key, family, display in PREFERRED_ZENODO_MICS:
        if key.lower() == mic_key.lower():
            return family, display
    # heuristics
    low = mic_key.lower()
    if "royer" in low or "bidirect" in low or "coles" in low:
        family = "fig8_ribbon"
    elif "omni" in low:
        family = "omni"
    elif "schoeps" in low or "c451" in low or "cmc" in low:
        family = "sdc_cardioid"
    elif "sm57" in low or "sm58" in low or "re20" in low or "md441" in low:
        family = "dynamic_cardioid"
    else:
        family = "ldc_cardioid"
    return family, f"{mic_key} (Franco et al. Zenodo)"


def load_zenodo_relative(
    data_dir: Path,
    mic_key: str,
    freqs: np.ndarray,
    angles: Optional[np.ndarray] = None,
) -> Optional[dict]:
    catalog = discover_zenodo_wavs(data_dir)
    # exact or case-insensitive
    if mic_key not in catalog:
        matches = [k for k in catalog if k.lower() == mic_key.lower()]
        if not matches:
            matches = [k for k in catalog if mic_key.lower() in k.lower()]
        if not matches:
            return None
        mic_key = matches[0]

    ang_map = catalog[mic_key]
    on_keys = [a for a in ang_map if abs(a) < 1e-6]
    if not on_keys:
        return None
    on_axis = magnitude_db_from_wav(ang_map[on_keys[0]], freqs)

    if angles is None:
        # prefer a sparse classic set if available, else all
        preferred = [0, 15, 30, 45, 60, 90, 120, 135, 150, 180]
        angles = np.array([a for a in preferred if a in ang_map], dtype=float)
        if len(angles) < 4:
            angles = np.array(sorted(ang_map.keys()), dtype=float)

    rows = []
    used = []
    for a in angles:
        a = float(a)
        if a not in ang_map:
            nearest = min(ang_map.keys(), key=lambda x: abs(x - a))
            if abs(nearest - a) > 2.5:
                continue
            path = ang_map[nearest]
            a_used = nearest
        else:
            path = ang_map[a]
            a_used = a
        db = magnitude_db_from_wav(path, freqs) - on_axis
        rows.append(db)
        used.append(a_used)
    if not rows:
        return None

    angles_arr = np.array(used, dtype=float)
    db_all = np.stack(rows)
    holdout = {45.0, 135.0}
    train_idx = [i for i, a in enumerate(angles_arr) if float(a) not in holdout]
    hold_idx = [i for i, a in enumerate(angles_arr) if float(a) in holdout]
    family, display = _meta_for(mic_key)

    class _Spec:
        pass

    spec = _Spec()
    spec.id = mic_key
    spec.display_name = display
    spec.family = family
    spec.honesty = "MEASURED"
    spec.pattern_null_db = -18.0
    if family == "fig8_ribbon":
        spec.pattern_null_db = -6.0
    elif family == "omni":
        spec.pattern_null_db = -4.0

    return {
        "spec": spec,
        "mic_id": mic_key,
        "freqs": freqs,
        "angles_all": angles_arr,
        "db_all": db_all,
        "train_angles": angles_arr[train_idx],
        "train_db": db_all[train_idx],
        "holdout_angles": angles_arr[hold_idx],
        "holdout_db": db_all[hold_idx] if hold_idx else np.zeros((0, len(freqs))),
        "honesty": "MEASURED",
        "source": f"Franco et al. Zenodo {ZENODO_DOI} (Raw_IRs, 5m, 24-bit, selected angles)",
    }


def try_partial_zenodo_note(data_dir: Path) -> str:
    data_dir = Path(data_dir)
    zips = list(data_dir.glob("*.zip"))
    wavs = list(data_dir.rglob("*.wav"))
    if wavs:
        return f"Found {len(wavs)} WAV(s) under {data_dir}."
    if zips:
        return (
            f"Found zip(s): {[z.name for z in zips]} — extract selected mic WAVs "
            f"into data/zenodo/extracted/ then re-run."
        )
    return (
        f"No Zenodo files in {data_dir}. Full archive is ~1.5 GB ({ZENODO_URL}). "
        f"Place extracted WAVs under data/zenodo/ or set MIC_FITTER_DATA."
    )


def load_all(data_dir: Path, prefer_zenodo: bool = True) -> Tuple[Dict[str, dict], str]:
    """
    Returns (datasets_by_id, mode_note).
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    freqs = log_freqs(64)

    if prefer_zenodo:
        catalog = discover_zenodo_wavs(data_dir)
        if catalog:
            # Prefer curated list order; fall back to whatever we have
            chosen = []
            for key, _, _ in PREFERRED_ZENODO_MICS:
                if key in catalog:
                    chosen.append(key)
            if len(chosen) < 2:
                chosen = sorted(catalog.keys())[:6]
            out = {}
            for k in chosen[:6]:
                ds = load_zenodo_relative(data_dir, k, freqs)
                if ds:
                    out[ds["mic_id"]] = ds
            if out:
                note = (
                    f"MEASURED from Franco et al. Zenodo extract "
                    f"({len(out)} mics, DOI {ZENODO_DOI}). "
                    f"WAVs under {data_dir}. Angles held out: 45°, 135°."
                )
                return out, note

    note = try_partial_zenodo_note(data_dir)
    synth = build_dataset()
    return synth, (
        "ASSUMED DEMO DATA — synthetic curves mimicking published off-axis shapes. "
        + note
        + f" When available, drop Franco et al. WAVs into {data_dir} and re-run."
    )


def write_data_manifest(path: Path, mode_note: str, mic_ids: List[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "honesty": "MEASURED" if mode_note.startswith("MEASURED") else "ASSUMED",
                "note": mode_note,
                "zenodo": ZENODO_URL,
                "doi": ZENODO_DOI,
                "mic_ids": mic_ids,
                "preferred_mics": [
                    {"id": a, "family": b, "display": c} for a, b, c in PREFERRED_ZENODO_MICS
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
