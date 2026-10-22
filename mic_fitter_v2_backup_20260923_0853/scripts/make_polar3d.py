#!/usr/bin/env python3
"""One-shot: MEASURED presets → plots/polar3d/*_polar3d.png (+ rings)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mic_fitter.model import MicShelfModel, PARAM_NAMES  # noqa: E402
from mic_fitter.polar3d import plot_polar_rings, plot_polar_solid  # noqa: E402


def load_model(params: dict) -> MicShelfModel:
    """Build MicShelfModel from preset params dict (v2 keys)."""
    vec = [float(params[n]) for n in PARAM_NAMES]
    return MicShelfModel.from_vector(vec)


def main() -> int:
    presets_dir = ROOT / "presets"
    out_dir = ROOT / "plots" / "polar3d"
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = sorted(presets_dir.glob("*.json"))
    written = []
    skipped = []

    for path in paths:
        if path.name == "index.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        honesty = str(data.get("honesty", "")).upper()
        if honesty != "MEASURED":
            skipped.append((path.name, honesty or "missing"))
            continue

        mic_id = data["mic_id"]
        display = data.get("display_name", mic_id)
        family = data.get("family", "cardioid")
        model = load_model(data["params"])

        solid = out_dir / f"{mic_id}_polar3d.png"
        rings = out_dir / f"{mic_id}_polar3d_rings.png"
        plot_polar_solid(solid, display, model, family, honesty)
        plot_polar_rings(rings, display, model, family, honesty)
        written.append(solid)
        written.append(rings)
        print(f"OK  {mic_id} → {solid.name}, {rings.name}")

    readme = out_dir / "README.md"
    readme.write_text(
        "# 3D polar solids\n\n"
        "Stacked polar fields: **height = frequency (log10)**, "
        "radial distance = linear magnitude from "
        "`frequency_dependent_polar_db` (geometric family + dual-shelf colour).\n\n"
        "- Low freq at base, high at top (~40 Hz–16 kHz).\n"
        "- `*_polar3d.png` — dense surface solid.\n"
        "- `*_polar3d_rings.png` — wireframe rings at 63, 125, 250, 1k, 4k, 8k, 16k.\n"
        "- MEASURED presets only (assumed/proxy skipped).\n\n"
        "**Visual caveats:** fig-8 (e.g. Royer R-121) looks like an hourglass stack; "
        "cardioids look like tapered bulbs. Radius is pressure-linear "
        "`10**(pol_db/20)` with peak=1 per frequency layer.\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(written)} PNGs under {out_dir}")
    if skipped:
        print("Skipped:", skipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
