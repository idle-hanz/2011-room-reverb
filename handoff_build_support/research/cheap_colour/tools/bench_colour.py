#!/usr/bin/env python3
"""WASM (node, real fdn_worklet.js + live_stereo.wasm, zig -O3 -msimd128) CPU bench: FIR colour vs SOS colour.
Each config: wasm_run.js bench 3 s noise + 1 s silence, repeated R times, median of play_mean_ms / silence_late_mean_ms.
Usage: bench_colour.py out.json   (paths below are the box layout)"""
import json, subprocess, sys, statistics
WR = '/workspace/build_support/engine/tests/lib/wasm_run.js'
SNAP = '/workspace/build_support/snapshot_2026-09-27/software'
SOS = '/workspace/build_support/research/cheap_colour/work/sw_sos/software'
SAME = '/workspace/build_support/engine/work/sw_fix_same/software'
SAMESOS = '/workspace/build_support/research/cheap_colour/work/sw_same_sos/software'
P = '/tmp/rr/'
R = 3
cfg = [
    ('snapshot FIR colour, 1 src', SNAP, P + 'lock18.json', {}),
    ('snapshot SOS K=3, 1 src', SOS, P + 'lock18_sos3.json', {}),
    ('snapshot SOS K=4, 1 src', SOS, P + 'lock18_sos4.json', {}),
    ('snapshot colour off, 1 src', SNAP, P + 'lock18.json', {'colour_on': False}),
    ('snapshot FIR colour, 2 src', SNAP, P + 'two.json', {}),
    ('snapshot SOS K=3, 2 src', SOS, P + 'two_sos3.json', {}),
    ('snapshot SOS K=4, 2 src', SOS, P + 'two_sos4.json', {}),
    ('snapshot colour off, 2 src', SNAP, P + 'two.json', {'colour_on': False}),
    ('F1-F3+F5 FIR colour, 1 src', SAME, P + 'f_lock18.json', {}),
    ('F1-F3+F5 SOS K=3, 1 src', SAMESOS, P + 'f_lock18_sos3.json', {}),
    ('F1-F3+F5 SOS K=4, 1 src', SAMESOS, P + 'f_lock18_sos4.json', {}),
    ('F1-F3+F5 colour off, 1 src', SAME, P + 'f_lock18.json', {'colour_on': False}),
    ('F1-F3+F5 FIR colour, 2 src', SAME, P + 'f_two.json', {}),
    ('F1-F3+F5 SOS K=3, 2 src', SAMESOS, P + 'f_two_sos3.json', {}),
    ('F1-F3+F5 SOS K=4, 2 src', SAMESOS, P + 'f_two_sos4.json', {}),
    ('F1-F3+F5 colour off, 2 src', SAME, P + 'f_two.json', {'colour_on': False}),
]
out = {}
for name, sw, pj, over in cfg:
    play, sil = [], []
    for _ in range(R):
        r = subprocess.run(['node', WR, sw, pj, json.dumps(over), 'bench', '3', '4'], capture_output=True, text=True, check=True)
        d = json.loads(r.stdout); play.append(d['play_mean_ms']); sil.append(d['silence_late_mean_ms'])
    out[name] = {'play_ms': round(statistics.median(play), 3), 'silence_ms': round(statistics.median(sil), 3),
                 'play_pct_budget': round(100 * statistics.median(play) / (128 / 48), 1), 'runs': [round(x, 3) for x in play]}
    print(name, out[name], flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
