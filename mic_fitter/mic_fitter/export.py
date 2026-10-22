"""Export preset JSON files for the room app to load later."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .fit import FitResult


def export_preset(result: FitResult, presets_dir: Path) -> Path:
    presets_dir = Path(presets_dir)
    presets_dir.mkdir(parents=True, exist_ok=True)
    path = presets_dir / f"{result.mic_id}.json"
    path.write_text(json.dumps(result.to_preset_dict(), indent=2), encoding="utf-8")
    return path


def export_index(results: Iterable[FitResult], presets_dir: Path) -> Path:
    presets_dir = Path(presets_dir)
    presets_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for r in results:
        items.append(
            {
                "mic_id": r.mic_id,
                "display_name": r.display_name,
                "honesty": r.honesty,
                "family": r.family,
                "file": f"{r.mic_id}.json",
                "holdout_rmse_db": r.holdout_rmse_db,
                "train_rmse_db": r.train_rmse_db,
            }
        )
    path = presets_dir / "index.json"
    path.write_text(
        json.dumps(
            {
                "schema": "mic_fitter.preset_index.v3",
                "presets": items,
                "note": "Structure LP is separate. Optional HPF switches are manufacturer defaults (not fitted).",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path
