"""Export climate preset JSON + index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .fit import FitResult
from .model import PRESET_SCHEMA


def export_preset(result: FitResult, presets_dir: Path) -> Path:
    presets_dir = Path(presets_dir)
    presets_dir.mkdir(parents=True, exist_ok=True)
    path = presets_dir / f"{result.climate_id}.json"
    path.write_text(json.dumps(result.to_preset_dict(), indent=2), encoding="utf-8")
    return path


def export_metrics(result: FitResult, reports_dir: Path) -> Path:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{result.climate_id}_metrics.json"
    payload = {
        "id": result.climate_id,
        "candidate": result.candidate,
        "model": result.model,
        "joint_rmse_db": result.joint_rmse_db,
        "per_distance_rmse_db": result.per_distance_rmse_db,
        "flat_naive_rmse_db": result.flat_rmse_db,
        "candidate_rmse": result.candidate_rmse,
        "assumed_rmse": result.assumed_rmse,
        "params": result.params,
        "alpha_check": result.alpha_check,
        "extras": result.extras,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def export_index(results: Iterable[FitResult], presets_dir: Path) -> Path:
    presets_dir = Path(presets_dir)
    presets_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for r in results:
        items.append(
            {
                "id": r.climate_id,
                "label": r.label,
                "honesty": r.honesty,
                "model": r.model,
                "candidate": r.candidate,
                "file": f"{r.climate_id}.json",
                "joint_rmse_db": r.joint_rmse_db,
                "conditions": r.conditions,
            }
        )
    path = presets_dir / "index.json"
    path.write_text(
        json.dumps(
            {
                "schema": "air_fitter.preset_index.v1",
                "preset_schema": PRESET_SCHEMA,
                "presets": items,
                "note": (
                    "Geometric 1/r^2 stays. Structure 1-pole Wet/Dis separate. "
                    "Apply once on early + FDN inject — not Direct, not feedback."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path
