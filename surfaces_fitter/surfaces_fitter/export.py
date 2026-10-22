"""Export material preset JSON + index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .fit import FitResult
from .model import PRESET_SCHEMA


def export_preset(result: FitResult, presets_dir: Path) -> Path:
    presets_dir = Path(presets_dir)
    presets_dir.mkdir(parents=True, exist_ok=True)
    path = presets_dir / f"{result.material_id}.json"
    path.write_text(json.dumps(result.to_preset_dict(), indent=2), encoding="utf-8")
    return path


def export_metrics(result: FitResult, reports_dir: Path) -> Path:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{result.material_id}_metrics.json"
    payload = {
        "id": result.material_id,
        "display_name": result.display_name,
        "candidate": result.candidate,
        "model": result.model,
        "rmse_r_db": result.rmse_r_db,
        "absorb_l1": result.absorb_l1,
        "candidate_rmse": result.candidate_rmse,
        "params": result.params,
        "roles": result.roles,
        "banned_on": result.banned_on,
        "absorb": result.absorb,
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
                "id": r.material_id,
                "display_name": r.display_name,
                "honesty": r.honesty,
                "roles": r.roles,
                "banned_on": r.banned_on,
                "model": r.model,
                "candidate": r.candidate,
                "file": f"{r.material_id}.json",
                "rmse_r_db": r.rmse_r_db,
                "absorb_l1": r.absorb_l1,
            }
        )
    path = presets_dir / "index.json"
    path.write_text(
        json.dumps(
            {
                "schema": "surfaces_fitter.preset_index.v1",
                "preset_schema": PRESET_SCHEMA,
                "presets": items,
                "note": (
                    "ASSUMED_TEXTBOOK α → R_db = 20*log10(sqrt(1-α)). "
                    "One bounce apply R(f); multi-bounce cascade. "
                    "Respect roles / banned_on. Do not import into live software/ here."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path
