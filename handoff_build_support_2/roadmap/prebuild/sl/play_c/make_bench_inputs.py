"""Writes bench_inputs.json (blob + designed sections) for bench_play_wasm.mjs. Same scene as the native bench."""
import importlib.util, json, sys
from pathlib import Path
import numpy as np
SW = Path(sys.argv[1]); sys.path[:0] = [str(SW), str(SW / "engine")]
spec = importlib.util.spec_from_file_location("bn", Path(__file__).with_name("bench_play_native.py"))
src = Path(__file__).with_name("bench_play_native.py").read_text()
# reuse the scene definition without running the benchmark
ns = {}
exec(src.split("imp = np.zeros")[0].replace("libA, libB, SW = sys.argv[1], sys.argv[2], Path(sys.argv[3])", f"libA=libB=None; SW=Path({str(SW)!r})"), ns)
secs, stab = ns["designed_sections"]()
json.dump(dict(blob=[float(x) for x in ns["BLOB"]], secs=np.asarray(secs).ravel().tolist(), stab=stab), open(Path(__file__).with_name("bench_inputs.json"), "w"))
print("ok", len(ns["BLOB"]))
