#!/usr/bin/env python3
"""One-command entry: textbook α → fit musical R_db models → presets + plots + report."""

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

from surfaces_fitter.export import export_index, export_metrics, export_preset  # noqa: E402
from surfaces_fitter.fit import fit_all  # noqa: E402
from surfaces_fitter.materials import ROLES_ALL, list_materials, role_matrix  # noqa: E402
from surfaces_fitter.model import ABSORB_BAND_HZ, FREQ_RANGE_HZ  # noqa: E402
from surfaces_fitter.plot import (  # noqa: E402
    plot_alpha_bars,
    plot_gallery_index,
    plot_r_db_fit,
    plot_role_matrix,
)

UK = ZoneInfo("Europe/London")


def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("surfaces_fitter")
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
    by_rmse = sorted(results, key=lambda r: r.rmse_r_db)
    best, worst = by_rmse[0], by_rmse[-1]
    matrix = role_matrix()

    lines = []
    lines.append("# surfaces_fitter — MORNING_REPORT / FIT_REPORT")
    lines.append("")
    lines.append(f"**Generated:** {now} (Europe/London)")
    lines.append(f"**Elapsed:** {elapsed_s:.1f} s")
    lines.append(f"**Honesty:** ASSUMED_TEXTBOOK (Sengpiel-style octave α — not Structure VERIFIED)")
    lines.append(f"**Materials:** {len(results)}")
    lines.append("")
    lines.append("## Locks (do not violate)")
    lines.append("")
    lines.append("- Do **not** edit live `software/` / engine / static that Build may be editing for mic/air.")
    lines.append("- Do **not** change listened mix defaults in the live app.")
    lines.append("- Depth is **absolute per bounce**, not per metre.")
    lines.append("- Tag ASSUMED vs anything VERIFIED from Structure — these tables are ASSUMED.")
    lines.append("- Floor/Ceiling cards E/F stay; only illegal material kits on those faces are purged.")
    lines.append("")
    lines.append("## Physics")
    lines.append("")
    lines.append("Energy absorb α(f) at octave centres; log-frequency interpolate.")
    lines.append("Amplitude reflection:")
    lines.append("")
    lines.append("```")
    lines.append("R_db(f) = 20 * log10(√(max(1 − α(f), 1e-6)))")
    lines.append("```")
    lines.append("")
    lines.append(
        f"Fit grid: log-spaced {FREQ_RANGE_HZ[0]:g}–{FREQ_RANGE_HZ[1]:g} Hz. "
        f"Export absorb[{len(ABSORB_BAND_HZ)}] at {list(ABSORB_BAND_HZ)} Hz "
        "(Desktop Surfaces cards)."
    )
    lines.append("")
    lines.append("Candidates: **A** `dual_high_shelf` · **B** `low_shelf_high_shelf` (LF for plywood/glass/curtain).")
    lines.append("Loss: RMSE of model R_db vs target R_db; also absorb-band L1.")
    lines.append("")
    lines.append("## RMSE table")
    lines.append("")
    lines.append("| Material | Roles | Model | RMSE R_db | Absorb L1 | A | B |")
    lines.append("|----------|-------|-------|-----------|-----------|---|---|")
    for r in by_rmse:
        lines.append(
            f"| `{r.material_id}` | {','.join(r.roles)} | `{r.model}` | "
            f"**{r.rmse_r_db:.4f}** | {r.absorb_l1:.4f} | "
            f"{r.candidate_rmse.get('A', float('nan')):.4f} | "
            f"{r.candidate_rmse.get('B', float('nan')):.4f} |"
        )
    lines.append("")
    lines.append(f"- **Best RMSE:** `{best.material_id}` = {best.rmse_r_db:.4f} dB")
    lines.append(f"- **Worst RMSE:** `{worst.material_id}` = {worst.rmse_r_db:.4f} dB")
    lines.append("")
    lines.append("## Role matrix")
    lines.append("")
    lines.append("| Role | Allowed material ids |")
    lines.append("|------|----------------------|")
    for role in ROLES_ALL:
        ids = ", ".join(f"`{i}`" for i in matrix[role])
        lines.append(f"| **{role}** | {ids} |")
    lines.append("")
    lines.append("### Banned faces (from roles)")
    lines.append("")
    lines.append("| Material | banned_on |")
    lines.append("|----------|-----------|")
    for r in results:
        ban = ", ".join(r.banned_on) if r.banned_on else "_(none)_"
        lines.append(f"| `{r.material_id}` | {ban} |")
    lines.append("")
    lines.append("## Crazy-kit purge (Idle pick #11)")
    lines.append("")
    lines.append("See `PURGE_LIST.md` and Desktop `findings/surfaces-crazy-kit-purge.md`.")
    lines.append("")
    lines.append("- Curtain/Carpet must **not** be unrestricted paint-all chips.")
    lines.append("- Ban: curtains on floor (E) or ceiling (F); carpet on walls/ceiling unless Idle unlocks.")
    lines.append("- Shift-paint-all must skip illegal role combos.")
    lines.append("- Do **not** delete Floor/Ceiling cards E/F themselves.")
    lines.append("")
    lines.append("## Absolute paths (box)")
    lines.append("")
    lines.append(f"- Pack root: `{ROOT}`")
    lines.append(f"- Presets: `{ROOT / 'presets'}`")
    lines.append(f"- Plots: `{ROOT / 'plots'}`")
    lines.append(f"- Reports: `{ROOT / 'reports'}`")
    lines.append("")
    lines.append("## Desktop sync target")
    lines.append("")
    lines.append(r"`C:\Users\IdleHanz\Desktop\2011 Room Reverb\surfaces_fitter\`")
    lines.append(r"`C:\Users\IdleHanz\Desktop\2011 Room Reverb\findings\surfaces-crazy-kit-purge.md`")
    lines.append("")
    lines.append("## Per-material params")
    lines.append("")
    for r in results:
        lines.append(f"### `{r.material_id}`")
        lines.append("")
        lines.append(f"- {r.display_name} · roles={r.roles} · candidate {r.candidate} / `{r.model}`")
        lines.append(f"- RMSE R_db={r.rmse_r_db:.5f} · absorb L1={r.absorb_l1:.5f}")
        lines.append(f"- absorb={r.absorb}")
        lines.append(f"- source: {r.source_note}")
        lines.append("- params:")
        lines.append("```json")
        lines.append(json.dumps(r.params, indent=2))
        lines.append("```")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fit surface absorb models to textbook α")
    ap.add_argument("--presets-dir", type=Path, default=ROOT / "presets")
    ap.add_argument("--plots-dir", type=Path, default=ROOT / "plots")
    ap.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    ap.add_argument("--maxiter", type=int, default=50)
    args = ap.parse_args()

    for d in (args.presets_dir, args.plots_dir, args.reports_dir, ROOT / "logs"):
        d.mkdir(parents=True, exist_ok=True)

    log = setup_logging(ROOT / "logs" / "fit_run.log")
    t0 = time.time()
    log.info("=== surfaces_fitter run start ===")
    log.info("Materials in library: %d", len(list_materials()))

    results = []
    for mat in list_materials():
        log.info("Fitting %s …", mat.id)
        t_c = time.time()
        # fit one at a time for logging
        from surfaces_fitter.fit import fit_material

        res = fit_material(mat, maxiter=args.maxiter)
        dt = time.time() - t_c
        log.info(
            "  done in %.1fs | winner=%s/%s | RMSE=%.4f dB | L1=%.4f | %s",
            dt, res.candidate, res.model, res.rmse_r_db, res.absorb_l1, res.message,
        )
        export_preset(res, args.presets_dir)
        export_metrics(res, args.reports_dir)
        plot_alpha_bars(args.plots_dir / f"{res.material_id}_alpha.png", res)
        plot_r_db_fit(args.plots_dir / f"{res.material_id}_r_db.png", res)
        results.append(res)

    export_index(results, args.presets_dir)
    plot_gallery_index(args.plots_dir / "gallery_index.png", results)
    plot_role_matrix(args.plots_dir / "role_matrix.png", results)

    by_rmse = sorted(results, key=lambda r: r.rmse_r_db)
    summary = {
        "generated": datetime.now(UK).isoformat(),
        "n_materials": len(results),
        "best": {"id": by_rmse[0].material_id, "rmse_r_db": by_rmse[0].rmse_r_db},
        "worst": {"id": by_rmse[-1].material_id, "rmse_r_db": by_rmse[-1].rmse_r_db},
        "materials": [
            {
                "id": r.material_id,
                "model": r.model,
                "candidate": r.candidate,
                "rmse_r_db": r.rmse_r_db,
                "absorb_l1": r.absorb_l1,
                "roles": r.roles,
            }
            for r in results
        ],
        "role_matrix": role_matrix(),
    }
    (args.reports_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    elapsed = time.time() - t0
    write_morning_report(results, ROOT / "MORNING_REPORT.md", elapsed)
    write_morning_report(results, args.reports_dir / "FIT_REPORT.md", elapsed)

    log.info("=== surfaces_fitter done in %.1fs ===", elapsed)
    log.info(
        "BEST %s RMSE=%.4f | WORST %s RMSE=%.4f",
        by_rmse[0].material_id,
        by_rmse[0].rmse_r_db,
        by_rmse[-1].material_id,
        by_rmse[-1].rmse_r_db,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
