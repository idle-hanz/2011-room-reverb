"""Per-mic w-tables from the 27 Sep K=3 fit. Runtime: interpolate, then RBJ at sr."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from mic_colour.model import angle_weight, repo_root
from mic_colour.sos_fit import (
    LAYOUTS,
    butter_hp_sos,
    hpf_order,
    pack_record,
    params_to_sos,
)

SCHEMA = "colour_sos_wtable.v1"
_TABLES: dict = {}
# Fitted w-tables exist only at these rates. 48000 stays in sos_tables/;
# 44100 lives in sos_tables/44100/. Any other rate disables SOS colour.
SUPPORTED_RATES = (44100, 48000)


def rate_supported(sr) -> bool:
    try:
        return int(sr) in SUPPORTED_RATES
    except (TypeError, ValueError):
        return False


def unsupported_rate_notice(sr) -> str:
    try:
        rate = str(int(sr))
    except (TypeError, ValueError):
        rate = "unknown rate"
    return (
        f"Mic colour is OFF at {rate} Hz: SOS colour runs at 44100 and 48000 only."
    )


def tables_dir(sr: int | None = None) -> Path:
    base = Path(__file__).resolve().parent / "sos_tables"
    if sr is not None and int(sr) != 48000:
        return base / str(int(sr))
    return base


def preset_hash(preset: dict) -> str:
    payload = {
        "mic_id": preset.get("mic_id"),
        "params": preset.get("params"),
        "model": preset.get("model"),
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _load_one(mic_id: str, sr: int = 48000):
    key = (mic_id, int(sr))
    if key in _TABLES:
        return _TABLES[key]
    if not rate_supported(sr):
        _TABLES[key] = None
        return None
    path = tables_dir(int(sr)) / f"{mic_id}.json"
    if not path.is_file():
        _TABLES[key] = None
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if str(data.get("schema") or "") != SCHEMA or int(data.get("fit_fs") or 48000) != int(sr):
        _TABLES[key] = None
        return None
    _TABLES[key] = data
    return data


def interpolate_params(table: dict, w: float) -> np.ndarray:
    ws = np.asarray(table["w"], dtype=np.float64)
    P = np.asarray(table["params"], dtype=np.float64)
    w = float(np.clip(w, float(ws[0]), float(ws[-1])))
    i = int(np.searchsorted(ws, w) - 1)
    i = max(0, min(i, len(ws) - 2))
    den = float(ws[i + 1] - ws[i])
    fr = 0.0 if abs(den) < 1e-18 else (w - float(ws[i])) / den
    return (1.0 - fr) * P[i] + fr * P[i + 1]


def pack_for(mic_id: str, model, theta_deg: float, sr: int, hpf=None, hpf_engaged: bool = False):
    """SOS record (float32, magic -2011) or None for identity / missing table."""
    table = _load_one(mic_id, int(sr))
    if table is None:
        return False
    layout = list(table.get("layout") or LAYOUTS[int(table.get("K") or 3)])
    w = float(np.asarray(angle_weight(float(theta_deg), model.p)).reshape(-1)[0])
    params = interpolate_params(table, w)
    gains = params[1::3]
    use_hpf = bool(hpf_engaged) and hpf and hpf.get("hpf_hz")
    if (not use_hpf) and float(np.max(np.abs(gains))) < 1e-5:
        return None
    sos = params_to_sos(params, layout, int(sr))
    if use_hpf:
        hz = float(hpf.get("hpf_hz"))
        if hz > 0.0:
            extra = butter_hp_sos(hz, hpf_order(hpf.get("hpf_slope") or 12), int(sr))
            sos = np.vstack([sos, extra])
    return pack_record(sos)


def write_v1_from_v0(src: Path | None = None, dest: Path | None = None) -> list[str]:
    """Split the 27 Sep prototype JSON into per-mic v1 tables. Run once."""
    root = repo_root()
    if src is None:
        src = (
            root
            / "handoff_build_support"
            / "research"
            / "cheap_colour"
            / "results"
            / "wtable_params_48000.json"
        )
    dest = Path(dest) if dest is not None else tables_dir()
    dest.mkdir(parents=True, exist_ok=True)
    blob = json.loads(Path(src).read_text(encoding="utf-8"))
    tables = blob.get("tables") or {}
    layout = list(blob.get("layout") or LAYOUTS[3])
    k = int(blob.get("K") or 3)
    from mic_colour.preset_store import get_store

    store = get_store()
    written = []
    for mic_id, row in tables.items():
        preset = store.get(mic_id)
        if not preset:
            continue
        out = {
            "schema": SCHEMA,
            "K": k,
            "layout": layout,
            "fit_fs": int(blob.get("fs") or 48000),
            "preset_hash": preset_hash(preset),
            "param_order": "per section: log2(f_hz), gain_db, log2(Q)",
            "w": row["w"],
            "params": row["params"],
        }
        path = dest / f"{mic_id}.json"
        path.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
        written.append(mic_id)
    return written


if __name__ == "__main__":
    names = write_v1_from_v0()
    print("wrote", len(names), "tables")
