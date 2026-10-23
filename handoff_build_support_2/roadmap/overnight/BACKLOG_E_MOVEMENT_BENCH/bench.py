"""Movement bench for BACKLOG_E. Measure only. Does not edit the engine.

Twelve harness benches at movement 0, then twelve at 100, one process.
Scene is std_lock18 plus the t19 two-source radiation body, shared tail off.

The product flag still omits movement_ms. --live (or RR_BENCH_MOVEMENT=1)
writes the locked curve onto the dumped JSON only. Knob 100 is 0.15 ms.
"""
from __future__ import annotations

import json
import os
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
    "shared_tail": False,
}


def live_requested() -> bool:
    if "--live" in sys.argv:
        return True
    return os.environ.get("RR_BENCH_MOVEMENT") == "1"


def curve_ms(pct: int) -> float:
    """Locked curve in movement_peak_ms. 100 snaps to 0.15. Flag is not read."""
    if pct <= 0:
        return 0.0
    if pct >= 100:
        return 0.15
    if pct <= 50:
        return 0.10 * (pct / 50.0)
    return 0.10 + 0.05 * ((pct - 50.0) / 50.0)


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


def arm(dest: Path, movement: int) -> float:
    data = json.loads(dest.read_text(encoding="utf-8"))
    leaked = float(data.get("movement_ms") or 0.0)
    if leaked > 0.0:
        raise SystemExit(f"product packed movement_ms {leaked}; flag is not forcing off")
    if data.get("shared_tail"):
        raise SystemExit("shared tail is on")
    if not data.get("two_sources"):
        raise SystemExit("two_sources is off")
    src = data.get("src_rad") or []
    if len(src) != 716:
        raise SystemExit(f"SRC_RAD len {len(src)}")
    ms = curve_ms(movement)
    if ms > 0.0:
        data["movement_ms"] = ms
    else:
        data.pop("movement_ms", None)
    dest.write_text(json.dumps(data), encoding="utf-8")
    return ms


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
    if not live_requested():
        raise SystemExit("refusing: pass --live or set RR_BENCH_MOVEMENT=1")
    HERE.mkdir(parents=True, exist_ok=True)
    score = {
        "ceiling_ms": 2.40,
        "burst_s": 4,
        "total_s": 10,
        "rounds": 12,
        "override": "bench.py --live",
        "product_forced_off": True,
    }
    armed = {}
    for label, movement in (("movement_0", 0), ("movement_100", 100)):
        pj = Path(tempfile.gettempdir()) / f"movement_bench_{label}.json"
        dump(movement, pj)
        armed[label] = arm(pj, movement)
        rounds = [one(pj)["play_median_ms"] for _ in range(12)]
        score[label] = {
            "median_ms": median(rounds),
            "max_ms": max(rounds),
            "movement_ms": armed[label],
            "rounds_ms": rounds,
        }
    d0 = score["movement_0"]["median_ms"]
    d100 = score["movement_100"]["median_ms"]
    score["delta_ms"] = d100 - d0
    score["cost_100_ms"] = d100
    score["gap_to_2_40_ms"] = d100 - 2.40
    score["headroom_at_0_ms"] = 2.40 - d0
    score["bench_moved_from_2_258"] = d0 != 2.258
    (HERE / "score.json").write_text(json.dumps(score, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "median_0": d0,
        "max_0": score["movement_0"]["max_ms"],
        "median_100": d100,
        "max_100": score["movement_100"]["max_ms"],
        "delta_ms": score["delta_ms"],
        "gap_to_2_40_ms": score["gap_to_2_40_ms"],
        "movement_ms_100": armed["movement_100"],
    }))


if __name__ == "__main__":
    main()
