#!/usr/bin/env python3
"""One-command entry: ISO 9613-1 → fit climate presets → plots + JSON + report."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from air_fitter.export import export_index, export_metrics, export_preset  # noqa: E402
from air_fitter.fit import CLIMATE_PRESETS, fit_climate  # noqa: E402
from air_fitter.iso9613 import Climate, alpha_db_per_m  # noqa: E402
from air_fitter.model import (  # noqa: E402
    DISTANCES_M,
    FREQ_RANGE_HZ,
    AirAbsModel,
    fit_freqs,
)
from air_fitter.plot import (  # noqa: E402
    plot_fit_distances,
    plot_hall_long_path,
    plot_shape_h1,
)

UK = ZoneInfo("Europe/London")


def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("air_fitter")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def write_morning_report(results, path: Path, elapsed_s: float) -> None:
    now = datetime.now(UK).strftime("%Y-%m-%d %H:%M %Z")
    primary = next((r for r in results if r.climate_id == "studio_20C_50RH"), results[0])
    lines = []
    lines.append("# air_fitter — MORNING_REPORT / FIT_REPORT")
    lines.append("")
    lines.append(f"**Generated:** {now} (Europe/London)")
    lines.append(f"**Elapsed:** {elapsed_s:.1f} s")
    lines.append(f"**Honesty:** FITTED_TO_ISO_9613_1 (not measured IRs)")
    lines.append("")
    lines.append("## Locks (do not violate)")
    lines.append("")
    lines.append("- Geometric **1/r²** stays; this only replaces the ASSUMED high-shelf colour path.")
    lines.append("- Structure **1-pole Wet/Dis** is a separate musical control — not replaced unless Idle asks later.")
    lines.append("- Placement: **once** on early + FDN inject; **not** Direct; **not** feedback return.")
    lines.append("- Do **not** import into live `software/` engine in this task.")
    lines.append("")
    lines.append("## Physics")
    lines.append("")
    lines.append("ISO 9613-1:1993 α(f) in dB/m (python-acoustics equations):")
    lines.append("saturation vapour pressure → molar h → frO / frN → attenuation_coefficient.")
    lines.append("Path attenuation: `A_db(f) = −α(f)·d` (model outputs ≤ 0 dB).")
    lines.append("Fit grid: log-spaced %g-%g Hz x distances %s m." % (FREQ_RANGE_HZ[0], FREQ_RANGE_HZ[1], list(DISTANCES_M)))
    lines.append("HF weight ×1.5 on 4–16 kHz. Candidates A (high shelf) → B (+ soft 1-pole) → C (dual shelf).")
    lines.append("")
    lines.append("### ISO sanity (studio 20 °C / 50 % RH)")
    lines.append("")
    lines.append("| f | α (dB/m) |")
    lines.append("|---|----------|")
    for k, v in primary.alpha_check.items():
        lines.append(f"| {k} | {v:.6f} |")
    a1k = primary.alpha_check.get("1000Hz", float("nan"))
    lines.append("")
    lines.append(
        f"Check: α(~1 kHz) = **{a1k:.5f} dB/m** "
        "(expected rough order **0.003–0.005** at 20 °C / 50 % RH); rises toward 8–16 kHz."
    )
    lines.append("")
    lines.append("## Winning models")
    lines.append("")
    lines.append("| Climate | Candidate | Model | Joint RMSE (dB) | Flat naive RMSE | vs ASSUMED hum=0.5 |")
    lines.append("|---------|-----------|-------|-----------------|-----------------|--------------------|")
    for r in results:
        a05 = r.assumed_rmse.get("humidity_0.5_joint_db", float("nan"))
        lines.append(
            f"| `{r.climate_id}` | **{r.candidate}** | `{r.model}` | "
            f"{r.joint_rmse_db:.5f} | {r.flat_rmse_db:.5f} | {a05:.5f} |"
        )
    lines.append("")
    lines.append("### Primary studio params")
    lines.append("")
    lines.append(f"- **Winner:** candidate **{primary.candidate}** — `{primary.model}`")
    lines.append(f"- **Joint RMSE:** {primary.joint_rmse_db:.6f} dB (weighted)")
    lines.append(f"- **Flat naive RMSE:** {primary.flat_rmse_db:.6f} dB")
    lines.append(
        f"- **ASSUMED shelf RMSE:** hum=0.5 → {primary.assumed_rmse['humidity_0.5_joint_db']:.5f} dB; "
        f"hum=1.0 → {primary.assumed_rmse['humidity_1.0_joint_db']:.5f} dB"
    )
    lines.append("- **All candidates (joint RMSE):** "
                 + ", ".join(f"{k}={v:.5f}" for k, v in primary.candidate_rmse.items()))
    lines.append("- **Params:**")
    lines.append("```json")
    lines.append(json.dumps(primary.params, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("### Per-distance RMSE (studio)")
    lines.append("")
    lines.append("| Distance | RMSE (dB) |")
    lines.append("|----------|-----------|")
    for k, v in primary.per_distance_rmse_db.items():
        lines.append(f"| {k} | {v:.6f} |")
    lines.append("")
    lines.append("## ASSUMED engine shelf (compare only)")
    lines.append("")
    lines.append("Current listened path (`software/engine/early_field.py`):")
    lines.append("`gain_db = -0.15 * distance * humidity`, RBJ high-shelf corner ≈ `0.35 * Nyquist`")
    lines.append("(≈ 7718 Hz at 44.1 kHz). Humidity UI 0.5 and 1.0 plotted vs ISO — **not fitted**.")
    lines.append("ISO α(f) is strongly frequency-dependent; the flat-above-shelf ASSUMED curve is a coarse colour only.")
    lines.append("")
    lines.append("## hall_long_path note")
    lines.append("")
    lines.append("No extra fit. Studio coeffs reused at 40 / 60 / 80 m — see `plots/fit/hall_long_path_studio.png`.")
    lines.append("Useful for hall / outdoor-path distance colouring without a new climate preset.")
    lines.append("")
    lines.append("## Absolute paths (box)")
    lines.append("")
    lines.append(f"- Pack root: `{ROOT}`")
    lines.append(f"- Presets: `{ROOT / 'presets'}`")
    lines.append(f"- Plots fit: `{ROOT / 'plots' / 'fit'}`")
    lines.append(f"- Plots shape: `{ROOT / 'plots' / 'shape'}`")
    lines.append(f"- Reports: `{ROOT / 'reports'}`")
    lines.append("")
    lines.append("## Desktop sync target")
    lines.append("")
    lines.append(r"`C:\Users\IdleHanz\Desktop\2011 Room Reverb\air_fitter\`")
    lines.append("")
    lines.append("## Usage reminder")
    lines.append("")
    lines.append("`A_db(f,d) = d * H1(f)`; magnitude `10^(A_db/20)` once per path (early) or inject distance (FDN).")
    lines.append("Do not put on feedback return. Do not replace geometric 1/r².")
    lines.append("")
    for r in results:
        lines.append(f"### `{r.climate_id}` detail")
        lines.append("")
        lines.append(f"- Label: {r.label}")
        lines.append(f"- Conditions: {r.conditions}")
        lines.append(f"- Candidate {r.candidate} / `{r.model}`")
        lines.append(f"- Params: `{json.dumps(r.params)}`")
        lines.append(f"- Message: {r.message}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fit air-absorption filters to ISO 9613-1")
    ap.add_argument("--presets-dir", type=Path, default=ROOT / "presets")
    ap.add_argument("--plots-dir", type=Path, default=ROOT / "plots")
    ap.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    ap.add_argument("--maxiter", type=int, default=80)
    args = ap.parse_args()

    plots_fit = args.plots_dir / "fit"
    plots_shape = args.plots_dir / "shape"
    for d in (plots_fit, plots_shape, args.presets_dir, args.reports_dir, ROOT / "logs"):
        d.mkdir(parents=True, exist_ok=True)

    log = setup_logging(ROOT / "logs" / "fit_run.log")
    t0 = time.time()
    log.info("=== air_fitter run start ===")

    # Quick ISO table check before fitting
    studio = Climate(20.0, 50.0, 101.325)
    for f in (1000.0, 4000.0, 8000.0, 16000.0):
        a = float(alpha_db_per_m(f, studio))
        log.info("ISO studio α(%.0f Hz) = %.6f dB/m", f, a)

    freqs = fit_freqs(192)  # denser for plots
    results = []

    for preset in CLIMATE_PRESETS:
        log.info("Fitting %s …", preset["id"])
        t_c = time.time()
        res = fit_climate(preset, distances=DISTANCES_M, maxiter=args.maxiter)
        dt = time.time() - t_c
        log.info(
            "  done in %.1fs | winner=%s | joint RMSE=%.5f dB | flat=%.5f | %s",
            dt, res.candidate, res.joint_rmse_db, res.flat_rmse_db, res.message,
        )
        log.info("  params=%s", res.params)

        export_preset(res, args.presets_dir)
        export_metrics(res, args.reports_dir)
        results.append(res)

        climate = Climate(
            res.conditions["temperature_c"],
            res.conditions["relative_humidity_pct"],
            res.conditions["pressure_kpa"],
        )
        model = AirAbsModel(model=res.model, **res.params)

        plot_fit_distances(
            plots_fit / f"{res.climate_id}_distances.png",
            res.label,
            freqs,
            DISTANCES_M,
            climate,
            model,
        )
        plot_shape_h1(
            plots_shape / f"{res.climate_id}_h1.png",
            res.label,
            freqs,
            climate,
            model,
        )

    # hall_long_path note using studio
    studio_res = next(r for r in results if r.climate_id == "studio_20C_50RH")
    studio_model = AirAbsModel(model=studio_res.model, **studio_res.params)
    plot_hall_long_path(
        plots_fit / "hall_long_path_studio.png",
        freqs,
        Climate(20.0, 50.0, 101.325),
        studio_model,
    )

    export_index(results, args.presets_dir)

    # Summary JSON
    summary = {
        "generated": datetime.now(UK).isoformat(),
        "primary": studio_res.climate_id,
        "winner_candidate": studio_res.candidate,
        "winner_model": studio_res.model,
        "studio_params": studio_res.params,
        "studio_joint_rmse_db": studio_res.joint_rmse_db,
        "studio_flat_rmse_db": studio_res.flat_rmse_db,
        "climates": [
            {
                "id": r.climate_id,
                "candidate": r.candidate,
                "model": r.model,
                "joint_rmse_db": r.joint_rmse_db,
            }
            for r in results
        ],
    }
    (args.reports_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    elapsed = time.time() - t0
    write_morning_report(results, ROOT / "MORNING_REPORT.md", elapsed)
    # Mirror into reports/
    write_morning_report(results, args.reports_dir / "FIT_REPORT.md", elapsed)

    log.info("=== air_fitter done in %.1fs ===", elapsed)
    log.info(
        "PRIMARY studio: candidate %s / %s | RMSE=%.6f (flat naive %.6f)",
        studio_res.candidate,
        studio_res.model,
        studio_res.joint_rmse_db,
        studio_res.flat_rmse_db,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
