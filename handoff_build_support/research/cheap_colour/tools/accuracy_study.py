#!/usr/bin/env python3
"""Accuracy of cheaper colour filters vs the CURRENT Play FIR (design_ir at 48 kHz, 4096 taps),
for all 20 measured presets and angles 5..180 deg (0 deg is identity in both).
Candidates:  SOS K=2/3/4 fitted per (mic, angle) to the FIR magnitude;
             SOS K=3 from a per-mic w-table (65 entries, nearest) = the proposed runtime design;
             truncated FIR 1024 / 512 taps (half-Hann fade of the last 25 %).
Writes results/accuracy.json + results/accuracy_table.md + plots/.
"""
import json, sys, time, math
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SW = Path('/workspace/build_support/snapshot_2026-09-27/software')
sys.path[:0] = [str(SW), str(SW / 'engine'), str(HERE)]
import os; os.chdir(SW)
from mic_colour.design import design_ir, design_n_fft
from mic_colour.preset_store import get_store
from mic_colour.model import relative_db
import sos_fit as SF

FS = 48000
OUT = HERE.parent / 'results'; OUT.mkdir(exist_ok=True)
store = get_store()
ids = json.load(open(SW.parent / 'mic_fitter' / 'presets' / 'index.json'))['presets']
ids = [p['mic_id'] for p in ids]
ANG = list(range(5, 181, 5))
NF = 1 << 16


def fir_db_fn(ir):
    H = np.fft.rfft(ir, NF); fr = np.fft.rfftfreq(NF, 1 / FS)
    db = 20 * np.log10(np.maximum(np.abs(H), 1e-12))
    return lambda f: np.interp(f, fr, db)


def trunc(ir, n):
    h = ir[:n].copy(); k = n // 4
    h[-k:] *= 0.5 * (1 + np.cos(np.pi * np.arange(k) / k))
    return h


res = {}
t_fit = {2: [], 3: [], 4: []}
for mid in ids:
    model = store.model_for(mid)
    rows = []
    p_prev = {K: None for K in (2, 3, 4)}
    for th in ANG:
        ir = design_ir(model, th, FS)
        if ir is None:
            continue
        tgt = fir_db_fn(ir)
        mdl = lambda f, th=th: np.asarray(relative_db(model, np.asarray(f), th))
        row = {'deg': th, 'fir_vs_model': SF.errors(np.array([[1, 0, 0, 0, 0]]), lambda f: tgt(f) - mdl(f), FS)}
        for K in (2, 3, 4):
            t0 = time.time()
            sos, p = SF.fit(tgt, FS, K, p0=p_prev[K])
            t_fit[K].append(time.time() - t0)
            p_prev[K] = p
            row[f'sos{K}'] = SF.errors(sos, tgt, FS)
            row[f'sos{K}_vs_model'] = SF.errors(sos, mdl, FS)
            row[f'sos{K}_params'] = [float(v) for v in p]
        for n in (1024, 512):
            h = trunc(ir, n)
            row[f'fir{n}'] = SF.errors(np.array([[1, 0, 0, 0, 0]]), lambda f, h=h: fir_db_fn(h)(f) - tgt(f), FS)
        rows.append(row)
    res[mid] = rows
    print(mid, 'sos3 max', round(max(r['sos3'][0] for r in rows), 3), 'sos4 max', round(max(r['sos4'][0] for r in rows), 3),
          'fir1024 max', round(max(r['fir1024'][0] for r in rows), 3), flush=True)

json.dump({'fit_time_s_mean': {K: float(np.mean(v)) for K, v in t_fit.items()}, 'res': res}, open(OUT / 'accuracy.json', 'w'))
print('fit time mean', {K: round(float(np.mean(v)) * 1000, 1) for K, v in t_fit.items()}, 'ms')
