"""Movement bench for BACKLOG_E. Measure only. Does not edit the engine.

Twelve harness benches at movement 0, then twelve at 100, one process.
Scene is std_lock18 plus the t19 two-source radiation body, shared tail off.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SW = ROOT / "software"
PY = SW / ".venv" / "Scripts" / "python.exe"
LIB = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "lib"
HERE = Path(__file__).resolve().parent

BASE = {
    "decay_lock": True,
    "decay_s": 1.8,
    "humidity": 0.5,
    "early_wet": 1.0,
    "source_radiation": "talking_head",
    "source_radiation_b": "trumpet_byu",
    "source_yaw": 35.0,
    "source_yaw_b": -25.0,
    "two_sources": True,
}


def dump(movement: int, dest: Path) -> None:
    body = dict(BASE)
    body["movement"] = movement
    r = subprocess.run(
        [str(PY), str(LIB / "dump_params.py"), str(SW), json.dumps(body), str(dest), "48000"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-800:])
        raise SystemExit(r.returncode)


def one(pjson: Path) -> dict:
    r = subprocess.run(
        ["node", str(LIB / "wasm_run.js"), str(SW), str(pjson), "{}", "bench", "4", "10"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-800:])
        raise SystemExit(r.returncode)
    return json.loads(r.stdout)


def median(xs: list[float]) -> float:
    ys = sorted(xs)
    return ys[len(ys) // 2]


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    score = {"ceiling_ms": 2.40, "burst_s": 4, "total_s": 10, "rounds": 12}
    for label, movement in (("movement_0", 0), ("movement_100", 100)):
        pj = Path(tempfile.gettempdir()) / f"movement_bench_{label}.json"
        dump(movement, pj)
        rounds = [one(pj)["play_median_ms"] for _ in range(12)]
        score[label] = {"median_ms": median(rounds), "max_ms": max(rounds), "rounds_ms": rounds}
    d0 = score["movement_0"]["median_ms"]
    d100 = score["movement_100"]["median_ms"]
    score["delta_ms"] = d100 - d0
    score["gap_to_2_40_ms"] = 2.40 - d0
    (HERE / "score.json").write_text(json.dumps(score, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "median_0": d0,
        "median_100": d100,
        "delta_ms": score["delta_ms"],
        "gap_to_2_40_ms": score["gap_to_2_40_ms"],
    }))


if __name__ == "__main__":
    main()
