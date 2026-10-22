#!/usr/bin/env python3
"""One-command entry: load data → fit mics → presets + polars + colour plots + reports."""

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

from mic_fitter.data import load_all, write_data_manifest  # noqa: E402
from mic_fitter.export import export_index, export_preset  # noqa: E402
from mic_fitter.fit import fit_mic  # noqa: E402
from mic_fitter.model import PARAM_NAMES, MicShelfModel  # noqa: E402
from mic_fitter.plot import plot_comparison  # noqa: E402
from mic_fitter.polar import plot_colour_curves, plot_polar_gallery, plot_measured_polar_gallery  # noqa: E402

UK = ZoneInfo("Europe/London")


def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("mic_fitter")
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Fit tiny off-axis mic colour models")
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data" / "zenodo")
    ap.add_argument("--presets-dir", type=Path, default=ROOT / "presets")
    ap.add_argument("--plots-dir", type=Path, default=ROOT / "plots")
    ap.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    ap.add_argument("--maxiter", type=int, default=70)
    ap.add_argument("--no-zenodo", action="store_true")
    ap.add_argument(
        "--mics",
        nargs="+",
        default=None,
        help="Optional mic_id filter (e.g. RodeNT2ACardioid). Other presets on disk kept.",
    )
    args = ap.parse_args()

    plots_polars = args.plots_dir / "polars"
    plots_colour = args.plots_dir / "colour"
    plots_fit = args.plots_dir / "fit"
    for d in (plots_polars, plots_colour, plots_fit, args.presets_dir, args.reports_dir):
        d.mkdir(parents=True, exist_ok=True)

    log = setup_logging(ROOT / "logs" / "fit_run.log")
    t0 = time.time()
    log.info("=== mic_fitter run start ===")

    datasets, mode_note = load_all(args.data_dir, prefer_zenodo=not args.no_zenodo)
    if args.mics:
        want = {m.lower() for m in args.mics}
        datasets = {k: v for k, v in datasets.items() if k.lower() in want}
        missing = want - {k.lower() for k in datasets}
        if missing:
            log.warning("Requested mics not found in data: %s", sorted(missing))
        mode_note = mode_note + f" [--mics filter: {sorted(datasets.keys())}]"
    write_data_manifest(ROOT / "data" / "manifest.json", mode_note, list(datasets.keys()))
    log.info(mode_note)
    log.info("Mics to fit: %s", list(datasets.keys()))

    results = []
    gallery_rows = []

    for mic_id, ds in datasets.items():
        spec = ds.get("spec")
        display = spec.display_name if spec else mic_id
        family = spec.family if spec else "measured"
        honesty = ds.get("honesty", "ASSUMED")
        source = ds.get("source", "")
        pattern_null = float(getattr(spec, "pattern_null_db", -18.0)) if spec else -18.0

        log.info("Fitting %s (%s / %s) …", mic_id, honesty, family)
        t_mic = time.time()
        res = fit_mic(
            mic_id=mic_id,
            freqs=ds["freqs"],
            train_angles=ds["train_angles"],
            train_db=ds["train_db"],
            holdout_angles=ds["holdout_angles"],
            holdout_db=ds["holdout_db"],
            display_name=display,
            honesty=honesty,
            family=family,
            source=source,
            maxiter=args.maxiter,
        )
        dt = time.time() - t_mic
        log.info(
            "  done in %.1fs | train RMSE=%.3f dB | holdout RMSE=%.3f dB | %s",
            dt, res.train_rmse_db, res.holdout_rmse_db, res.message,
        )
        log.info("  params=%s", res.params)

        preset_path = export_preset(res, args.presets_dir)
        results.append(res)

        model = MicShelfModel.from_vector([res.params[k] for k in PARAM_NAMES])

        # Fit meas-vs-model panels
        plot_comparison(
            plots_fit / f"{mic_id}_train.png",
            display, ds["freqs"], ds["train_angles"], ds["train_db"],
            model, honesty, "TRAIN angles",
        )
        holdout_png = None
        if len(ds["holdout_angles"]):
            holdout_png = plot_comparison(
                plots_fit / f"{mic_id}_holdout.png",
                display, ds["freqs"], ds["holdout_angles"], ds["holdout_db"],
                model, honesty, "HOLD-OUT angles",
            )

        # Colour curves
        key = [0, 30, 60, 90, 120, 180]
        ang_all = list(ds["angles_all"])
        idx = [ang_all.index(a) for a in key if a in ang_all]
        colour_png = plot_colour_curves(
            plots_colour / f"{mic_id}_colour.png",
            display, ds["freqs"],
            [ang_all[i] for i in idx], ds["db_all"][idx],
            model, honesty,
        )

        # Polar gallery at 63 / 125 / 250 / 1k / 4k / 8k (model-based)
        polar_png = plot_polar_gallery(
            plots_polars / f"{mic_id}_polar.png",
            display, model, family, honesty,
            freqs=(20.0, 63.0, 125.0, 250.0, 1000.0, 4000.0, 8000.0),
            pattern_null_db=pattern_null,
        )
        # Measured polar when we have IR magnitudes
        if honesty == "MEASURED":
            plot_measured_polar_gallery(
                plots_polars / f"{mic_id}_polar_measured.png",
                display,
                (20.0, 63.0, 125.0, 250.0, 1000.0, 4000.0, 8000.0),
                ds["angles_all"],
                ds["freqs"],
                ds["db_all"],
                honesty,
                family=family,
            )

        # Per-mic metrics JSON
        metrics_path = args.reports_dir / f"{mic_id}_metrics.json"
        metrics_path.write_text(
            json.dumps(
                {
                    "mic_id": mic_id,
                    "display_name": display,
                    "honesty": honesty,
                    "family": family,
                    "source": source,
                    "params": res.params,
                    "train_rmse_db": res.train_rmse_db,
                    "holdout_rmse_db": res.holdout_rmse_db,
                    "train_mse_db": res.train_mse_db,
                    "holdout_mse_db": res.holdout_mse_db,
                    "holdout_angles_deg": res.holdout_angles,
                    "train_angles_deg": res.train_angles,
                    "fit_message": res.message,
                    "preset": str(preset_path.name),
                    "plots": {
                        "polar": str(polar_png.relative_to(ROOT)),
                        "colour": str(colour_png.relative_to(ROOT)),
                        "fit_train": f"plots/fit/{mic_id}_train.png",
                        "fit_holdout": f"plots/fit/{mic_id}_holdout.png" if holdout_png else None,
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        gallery_rows.append(
            {
                "mic_id": mic_id,
                "display": display,
                "honesty": honesty,
                "family": family,
                "source": source,
                "type": family,
                "holdout_rmse_db": res.holdout_rmse_db,
                "train_rmse_db": res.train_rmse_db,
                "polar": f"plots/polars/{mic_id}_polar.png",
                "colour": f"plots/colour/{mic_id}_colour.png",
                "preset": f"presets/{mic_id}.json",
            }
        )

    if args.mics:
        # Keep other presets: rebuild index from all MEASURED JSON on disk
        rebuild_index_from_disk(args.presets_dir)
        elapsed = time.time() - t0
        log.info("Filtered fits complete in %.1fs", elapsed)
        append_morning_report_section(results, gallery_rows, elapsed, log)
    else:
        export_index(results, args.presets_dir)
        elapsed = time.time() - t0
        log.info("All fits complete in %.1fs", elapsed)
        write_morning_report(results, mode_note, gallery_rows, elapsed, log)
        write_gallery_html(gallery_rows, args.reports_dir / "gallery.html")
    log.info("Wrote MORNING_REPORT.md and reports/")
    return 0


def rebuild_index_from_disk(presets_dir: Path) -> Path:
    """Rebuild presets/index.json from all non-assumed preset JSON files on disk."""
    presets_dir = Path(presets_dir)
    items = []
    for path in sorted(presets_dir.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("schema") not in ("mic_fitter.preset.v3", "mic_fitter.preset.v2"):
            continue
        items.append(
            {
                "mic_id": d.get("mic_id", path.stem),
                "display_name": d.get("display_name", path.stem),
                "honesty": d.get("honesty", "ASSUMED"),
                "family": d.get("family", ""),
                "file": path.name,
                "holdout_rmse_db": (d.get("metrics") or {}).get("holdout_rmse_db"),
                "train_rmse_db": (d.get("metrics") or {}).get("train_rmse_db"),
            }
        )
    out = presets_dir / "index.json"
    out.write_text(
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
    return out


def append_morning_report_section(results, gallery_rows, elapsed, log) -> None:
    """Append a short NT2-A / filtered-fit section without wiping the full report."""
    now = datetime.now(UK).strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        "",
        "---",
        "",
        f"## Røde NT2-A MEASURED add-on — {now}",
        "",
        f"- Filtered re-fit of **{len(results)}** mic(s) in {elapsed:.1f} s; other presets left intact.",
        "- Source: Franco et al. Zenodo Raw_IRs 5 m 24-bit (cardioid / omni / bidirect).",
        "- **NT5 still absent** from Zenodo — see `presets/pending_rode_nt5.md`.",
        "- NT2-A is a **1\" LDC multipattern**, not an NT5 stand-in for matched-pair SDC use.",
        "- Room Reverb mix / worklet / default engine: **untouched**.",
        "",
        "| mic_id | display | family | train RMSE | hold-out RMSE |",
        "|--------|---------|--------|------------:|--------------:|",
    ]
    for r in gallery_rows:
        lines.append(
            f"| `{r['mic_id']}` | {r['display']} | {r['family']} | "
            f"**{r['train_rmse_db']:.3f}** | **{r['holdout_rmse_db']:.3f}** |"
        )
    lines += ["", "### Fit details", ""]
    for res in results:
        lines += [
            f"#### `{res.mic_id}` — {res.display_name}",
            "",
            f"- Honesty: **{res.honesty}** · Family: `{res.family}`",
            f"- Train RMSE: **{res.train_rmse_db:.3f} dB** · Hold-out RMSE: **{res.holdout_rmse_db:.3f} dB**",
            f"- Fit: `{res.message}`",
            f"- Params: `{json.dumps(res.params)}`",
            f"- Plots: `plots/polars/{res.mic_id}_polar.png`, `plots/colour/{res.mic_id}_colour.png`, "
            f"`plots/fit/{res.mic_id}_{{train,holdout}}.png`",
            "",
        ]
    block = "\n".join(lines)
    for path in (ROOT / "MORNING_REPORT.md", ROOT / "reports" / "MORNING_REPORT.md"):
        if path.exists():
            path.write_text(path.read_text(encoding="utf-8") + block, encoding="utf-8")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# MORNING_REPORT\n" + block, encoding="utf-8")
    log.info("Appended filtered-fit section to MORNING_REPORT.md")



def write_gallery_html(rows, path: Path) -> None:
    cards = []
    for r in rows:
        cards.append(
            f"""<div class="card">
  <h3>{r['display']}</h3>
  <p><b>id:</b> <code>{r['mic_id']}</code> · <b>type:</b> {r['type']} ·
     <b>honesty:</b> <span class="tag">{r['honesty']}</span></p>
  <p><b>source:</b> {r['source']}<br>
     train RMSE {r['train_rmse_db']:.3f} dB · hold-out RMSE {r['holdout_rmse_db']:.3f} dB</p>
  <p><img src="../{r['polar']}" alt="polar" style="max-width:100%"/></p>
  <p><img src="../{r['colour']}" alt="colour" style="max-width:100%"/></p>
  <p><a href="../{r['preset']}">preset JSON</a></p>
</div>"""
        )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>mic_fitter gallery</title>
<style>
body{{font-family:system-ui,sans-serif;margin:24px;background:#111;color:#eee}}
.tag{{background:#664;padding:2px 8px;border-radius:4px}}
.card{{border:1px solid #444;border-radius:8px;padding:16px;margin:16px 0;background:#1a1a1a}}
img{{background:#222;border-radius:4px}}
a{{color:#8cf}}
</style></head><body>
<h1>mic_fitter — mic gallery</h1>
<p>Polar fields + off-axis colour. Structure LP is separate.</p>
{''.join(cards)}
</body></html>"""
    path.write_text(html, encoding="utf-8")


def write_morning_report(results, mode_note, gallery_rows, elapsed, log) -> None:
    now = datetime.now(UK).strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        "# MORNING_REPORT — mic_fitter v3 (freer shelf + more MEASURED) — 2026-09-23",
        "",
        f"**Generated:** {now} (Europe/London)",
        f"**Runtime:** {elapsed:.1f} s",
        f"**Deadline target:** ready by 08:00 Europe/London",
        "",
        "## Executive summary",
        "",
        f"- Fitted **{len(results)}** microphones end-to-end (v3 dual-shelf + soft one-pole, ≤9 free scalars).",
        "- Deliverables: `presets/`, `plots/polars/`, `plots/colour/`, `plots/fit/`, `reports/`, `logs/fit_run.log`.",
        "- **Room Reverb mix / worklet / default engine path: NOT modified.**",
        "- Structure LP remains a separate room-engine control.",
        "",
        "## Data sources (what was actually used)",
        "",
        f"> {mode_note}",
        "",
        "| mic_id | display name | type / family | source | honesty |",
        "|--------|--------------|---------------|--------|---------|",
    ]
    for r in gallery_rows:
        lines.append(
            f"| `{r['mic_id']}` | {r['display']} | {r['type']} | {r['source']} | **{r['honesty']}** |"
        )

    lines += [
        "",
        "### Zenodo note",
        "",
        "- Preferred dataset: Franco et al. — "
        "[Zenodo 4633508](https://zenodo.org/records/4633508) "
        "(`Microphone_Impulse_Responses.zip`, ~1.5 GB, 25 mics, 5° steps).",
        "- Overnight: full zip not extracted on the box (size). Pipeline auto-detects WAVs in "
        "`data/zenodo/` and flips honesty to **MEASURED** when present.",
        "- Proxy curves mimic published off-axis shapes (omni LF → directional HF shelf + mild LP).",
        "",
        "## Mic gallery (visual index)",
        "",
        "| Mic | Polar (20/63/125/250/1k/4k/8k) | Colour curves | Preset | Hold-out RMSE |",
        "|-----|----------------------|---------------|--------|---------------|",
    ]
    for r in gallery_rows:
        lines.append(
            f"| **{r['display']}**<br>`{r['mic_id']}` | "
            f"[polar PNG]({r['polar']}) | [colour PNG]({r['colour']}) | "
            f"[`{r['mic_id']}.json`]({r['preset']}) | "
            f"**{r['holdout_rmse_db']:.3f} dB** |"
        )

    lines += [
        "",
        "Open `reports/gallery.html` in a browser for an inline visual gallery.",
        "",
        "## Method (v3 — freer high-shelf slope + optional HPF schema)",
        "",
        "### Model (9 free scalars — dual shelf + soft LP)",
        "",
        "Relative magnitude `H(θ)/H(0°)` in dB on log freqs **20 Hz–16 kHz**:",
        "",
        "1. **High shelf** with free slope: `f0` (200–12000 Hz), `depth_max_db`, `shelf_slope` "
        "(sigmoid steepness in log10-freq; v2 bound 1.5–12 pinned at 1.5; v3 **0.6–12.0**).",
        "2. **Mild low shelf**: `f_lo` (40–400 Hz), `depth_lo_db` (±9 dB) — soft prior toward 0. "
        "Low-shelf steepness fixed at 2.5 (keeps param count at 9).",
        "3. **Soft one-pole** residual: `res_hz`, `lp_mix`, `fc_floor` — **strongly penalised** "
        "so `lp_mix` stays mild (~0.15–0.35) and shelves do the colour work.",
        "4. Angle law unchanged: `½(1 − cos θ)^p` with free `p`.",
        "",
        "On-axis is identically 0 dB. No deep learning. No per-frequency free EQ.",
        "",
        "### Loss & anti-overfit choices",
        "",
        "- **Primary loss:** mean squared error in dB of relative `H(θ)/H(0°)`.",
        "- **Hold-out angles:** 45° and 135° (never used in training loss).",
        "- **Smoothness penalty:** quadratic pull toward mid-bounds on all params.",
        "- **Extra priors:** quadratic on `lp_mix` toward 0.25; quadratic on `|depth_lo_db|` toward 0.",
        "- **Hard bounds** on every parameter (see `mic_fitter/model.py` `PARAM_BOUNDS`).",
        "- **Tiny capacity:** 9 scalars cannot memorise lobing notches — intentional.",
        "- Optimiser: `differential_evolution` (maxiter≈55, popsize=14) → `least_squares` TRF polish.",
        "- **LF window:** quasi-anechoic post-window lengthened 40→80 ms for usable 20 Hz bins.",
        "",
        "## Hold-out errors & fitted params",
        "",
        f"- Mean fitted `lp_mix`: **{sum(r.params.get('lp_mix', 0) for r in results)/max(len(results),1):.3f}** "
        f"(v1 overnight was universally ≈1.0; v2 targets ≪ 1 via prior).",
        f"- Mean `|depth_lo_db|`: **{sum(abs(r.params.get('depth_lo_db', 0)) for r in results)/max(len(results),1):.3f} dB**.",
        "",
    ]
    for res in results:
        lines += [
            f"### `{res.mic_id}` — {res.display_name}",
            "",
            f"- Honesty: **{res.honesty}** · Family: `{res.family}`",
            f"- Source: `{res.source}`",
            f"- Train RMSE: **{res.train_rmse_db:.3f} dB** (MSE {res.train_mse_db:.3f})",
            f"- Hold-out RMSE: **{res.holdout_rmse_db:.3f} dB** (MSE {res.holdout_mse_db:.3f})",
            f"- Hold-out angles: {res.holdout_angles}",
            f"- Train angles: {res.train_angles}",
            f"- Fit log: `{res.message}`",
            f"- Params:",
            "",
            "```json",
            json.dumps(res.params, indent=2),
            "```",
            "",
            f"- Plots: `plots/polars/{res.mic_id}_polar.png`, "
            f"`plots/colour/{res.mic_id}_colour.png`, "
            f"`plots/fit/{res.mic_id}_{{train,holdout}}.png`",
            f"- Metrics JSON: `reports/{res.mic_id}_metrics.json`",
            "",
        ]

    lines += [
        "## Evidence the fitter ran end-to-end",
        "",
        f"- Log file: [`logs/fit_run.log`](logs/fit_run.log)",
        f"- Per-mic metrics under `reports/*_metrics.json`",
        f"- Preset index: [`presets/index.json`](presets/index.json)",
        f"- This report timestamp: {now}",
        f"- Wall time: {elapsed:.1f} s for {len(results)} mics",
        "",
        "## How to re-run",
        "",
        "```bat",
        'cd "C:\\Users\\IdleHanz\\Desktop\\2011 Room Reverb\\mic_fitter"',
        "REM use software\\.venv if present, else:",
        "python -m venv .venv",
        ".venv\\Scripts\\activate",
        "pip install -r requirements.txt",
        "python run_fit.py",
        "```",
        "",
        "With Zenodo WAVs extracted into `data\\zenodo\\`:",
        "",
        "```bat",
        "python run_fit.py",
        "```",
        "",
        "Force ASSUMED proxies:",
        "",
        "```bat",
        "python run_fit.py --no-zenodo",
        "```",
        "",
        "Box mirror:",
        "",
        "```bash",
        "cd /workspace/mic_fitter && source .venv/bin/activate && python run_fit.py",
        "```",
        "",
        "## Optional HPF (schema only — not fitted)",
        "",
        "- Preset field `switches: { hpf_hz, hpf_slope (6|12|18), hpf_engaged }` (default engaged=false).",
        "- Manufacturer defaults documented in `mic_fitter.model.MANUFACTURER_HPF_DEFAULTS` "
        "(U87 ≈140 Hz, C414 bass-cut options, SM57/SM58 none, etc.).",
        "- Helper `apply_hpf(db, freqs, ...)` for future UI; colour/polar/fit plots stay filter-out.",
        "- Zenodo Raw_IRs are used without engaging HPF (filters out of the MEASURED fit).",
        "",
        "## SE Electronics SE2200A — pending",
        "",
        "- **Requested but absent** from Franco et al. Zenodo 4633508.",
        "- See `presets/pending_se2200a.md` — need manufacturer curve or user IR; no fake MEASURED fit.",
        "",
        "## Limitations",
        "",
        "- ASSUMED proxies ≠ measured Franco IRs until WAVs are provided.",
        "- 9-scalar dual-shelf model will still miss sharp diffraction notches / strong rear-lobe colour.",
        "- Fig-8 side null is approximate.",
        "- Polar plots combine geometric pattern + fitted colour (presentation aid).",
        "- Absolute sensitivity / pad / proximity not modelled.",
        "",
        "## Folder map on Desktop",
        "",
        "```",
        "C:/Users/IdleHanz/Desktop/2011 Room Reverb/mic_fitter/",
        "  README.md",
        "  MORNING_REPORT.md",
        "  run_fit.py",
        "  requirements.txt",
        "  mic_fitter/          # package",
        "  presets/             # *.json + index.json",
        "  plots/",
        "    polars/            # classic polar at 20/63/125/250/1k/4k/8k",
        "    colour/            # off-axis colour curves",
        "    fit/               # meas-vs-model train/holdout panels",
        "  data/                # zenodo/ + manifest.json",
        "  reports/             # metrics + gallery.html",
        "  logs/fit_run.log",
        "```",
        "",
        "## Room software",
        "",
        "Pointer only — **untouched**: `../software/` (Desktop) / "
        "`/workspace/2011-Room-Reverb/software/` (box).",
        "",
    ]
    (ROOT / "MORNING_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    # also copy into reports/
    (ROOT / "reports" / "MORNING_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    log.info("MORNING_REPORT.md written")


if __name__ == "__main__":
    raise SystemExit(main())
