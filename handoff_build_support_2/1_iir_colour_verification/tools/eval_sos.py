#!/usr/bin/env python3
"""Package 1: verify Build's SOS (IIR) mic colour against MEASURED data, the analytic
fitter model, and the old Phase-3 FIR.  Read-only on the tree passed with --sw.

Usage: python eval_sos.py --sw <.../software> --mf <.../mic_fitter data root> --out results/
Needs numpy, scipy, soundfile.  mic_fitter/ must sit next to software/ (the code loads it).
"""
from __future__ import annotations
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--sw', required=True)
ap.add_argument('--mf', default='/workspace/mic_fitter')   # holds data/zenodo/extracted (MEASURED wavs)
ap.add_argument('--out', required=True)
a = ap.parse_args()
SW = Path(a.sw).resolve(); OUT = Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(SW), str(SW / 'engine'), str(Path(a.mf).resolve())]

from mic_colour.preset_store import get_store
from mic_colour.model import relative_db
from mic_colour.design import design_ir, design_n_fft
from mic_colour.sos_fit import sos_db, unpack_record, apply_sos
from mic_colour.sos_table import pack_for, tables_dir, preset_hash, _load_one
from mic_colour.hpf import stack_hpf
from mic_colour.colour import MicColour
from mic_fitter.data import load_zenodo_relative

store = get_store()
MICS = sorted(p.stem for p in tables_dir().glob('*.json'))
F_MEAS = np.geomspace(20.0, 16000.0, 200)       # fitter band (20 Hz-16 kHz)
F_DENSE = np.geomspace(20.0, 20000.0, 600)      # Build's AT-C1 grid
DATA = Path(a.mf) / 'data' / 'zenodo' / 'extracted'

def fir_db(ir, f, sr):
    n = 1 << 18
    H = np.fft.rfft(np.asarray(ir, float), n=n)
    ff = np.fft.rfftfreq(n, 1.0 / sr)
    return np.interp(f, ff, 20 * np.log10(np.maximum(np.abs(H), 1e-12)))

def rec_for(mic, deg, sr, hpf_on):
    model = store.model_for(mic)
    r = pack_for(mic, model, float(deg), int(sr), hpf=store.hpf_of(mic), hpf_engaged=hpf_on)
    return r

def sos_resp(rec, f, sr):
    if rec is None or rec is False: return np.zeros_like(f)
    return sos_db(unpack_record(rec), f, sr)

def fir_resp(mic, deg, sr, hpf_on, f):
    ir = design_ir(store.model_for(mic), float(deg), int(sr), hpf=store.hpf_of(mic), hpf_engaged=hpf_on)
    return np.zeros_like(f) if ir is None else fir_db(ir, f, sr)

def target(mic, deg, f, hpf_on):
    db = np.asarray(relative_db(store.model_for(mic), f, float(deg)), float)
    if hpf_on:
        h = store.hpf_of(mic) or {}
        db = np.asarray(stack_hpf(db, f, h.get('hpf_hz'), h.get('hpf_slope') or 12, True), float)
    return db

def stats(e):
    e = np.asarray(e); return float(np.max(np.abs(e))), float(np.sqrt(np.mean(e ** 2)))

res = {'tree': str(SW), 'mics': MICS, 'n_mics': len(MICS)}

# ---- 0. table provenance: preset hash in each sos table == current preset
prov = {}
for m in MICS:
    t = _load_one(m); pr = store.get(m)
    prov[m] = {'hash_ok': (t.get('preset_hash') == preset_hash(pr)), 'n_w': len(t['w']), 'K': t['K'], 'layout': t['layout'], 'fit_fs': t.get('fit_fs'),
               'hpf': store.hpf_of(m)}
res['provenance'] = prov

# ---- 1. vs MEASURED (Zenodo angles), SOS / FIR / model, 48k and 44.1k, HPF off
meas = {}
for m in MICS:
    d = load_zenodo_relative(DATA, m, F_MEAS)
    if d is None:
        meas[m] = {'error': 'no measured data found'}; continue
    rows = []
    for ang, mdb in zip(d['angles_all'], d['db_all']):
        if ang == 0: continue
        row = {'deg': float(ang)}
        mod = target(m, ang, F_MEAS, False)
        row['model_vs_meas'] = stats(mod - mdb)
        for sr in (48000, 44100):
            s = sos_resp(rec_for(m, ang, sr, False), F_MEAS, sr)
            fr = fir_resp(m, ang, sr, False, F_MEAS)
            row[f'sos_vs_meas_{sr}'] = stats(s - mdb)
            row[f'fir_vs_meas_{sr}'] = stats(fr - mdb)
            row[f'sos_vs_model_{sr}'] = stats(s - mod)
            row[f'fir_vs_model_{sr}'] = stats(fr - mod)
            row[f'sos_vs_fir_{sr}'] = stats(s - fr)
        rows.append(row)
    agg = {}
    for k in rows[0]:
        if k == 'deg': continue
        agg[k] = {'max': max(r[k][0] for r in rows), 'rms': float(np.sqrt(np.mean([r[k][1] ** 2 for r in rows])))}
    meas[m] = {'angles': [r['deg'] for r in rows], 'rows': rows, 'agg': agg}
res['vs_measured'] = meas

# ---- 2. dense grid 1..180 deg: SOS vs model at 44.1/48/96 kHz, HPF off + stability incl. float32
dense = {}; worst_pole = (0.0, None)
for m in MICS:
    out = {}
    for sr in (44100, 48000, 96000):
        errs = []; nid = 0
        for deg in range(0, 181):
            rec = rec_for(m, deg, sr, False)
            mod = target(m, deg, F_DENSE[F_DENSE < 0.45 * sr], False)
            if rec is None:
                nid += 1; errs.append(float(np.max(np.abs(mod)))); continue
            sos = unpack_record(rec)
            errs.append(float(np.max(np.abs(sos_db(sos, F_DENSE[F_DENSE < 0.45 * sr], sr) - mod))))
            for b0, b1, b2, a1, a2 in sos:
                r = float(np.max(np.abs(np.roots([1.0, a1, a2]))))
                if r > worst_pole[0]: worst_pole = (r, [m, sr, deg, 'hpf_off'])
        out[str(sr)] = {'max': max(errs), 'p95': float(np.percentile(errs, 95)), 'median': float(np.median(errs)), 'identity_angles': nid,
                        'worst_deg': int(np.argmax(errs))}
    dense[m] = out
res['dense_sos_vs_model'] = dense

# ---- 3. HPF engaged: SOS and FIR vs (model + analog Butterworth), <100 Hz and >=100 Hz, 48k & 44.1k
hpf = {}
for m in MICS:
    h = store.hpf_of(m) or {}
    if not h.get('hpf_hz'): continue
    per = {}
    for sr in (48000, 44100):
        lo = F_DENSE[(F_DENSE < 100)]; hi = F_DENSE[(F_DENSE >= 100) & (F_DENSE < 16000)]
        rows = []
        for deg in (0, 30, 60, 90, 120, 150, 180):
            rec = rec_for(m, deg, sr, True)
            sos = unpack_record(rec)
            for b0, b1, b2, a1, a2 in sos:
                r = float(np.max(np.abs(np.roots([1.0, a1, a2]))))
                if r > worst_pole[0]: worst_pole = (r, [m, sr, deg, 'hpf_on'])
            r = {'deg': deg, 'n_sections': int(sos.shape[0])}
            for name, f in (('lt100', lo), ('ge100', hi)):
                t = target(m, deg, f, True)
                r[f'sos_{name}'] = float(np.max(np.abs(sos_db(sos, f, sr) - t)))
                r[f'fir_{name}'] = float(np.max(np.abs(fir_resp(m, deg, sr, True, f) - t)))
                # float64 (unquantised) re-design, to isolate float32 coefficient rounding
            rows.append(r)
        per[str(sr)] = {'rows': rows,
                        'sos_lt100_max': max(r['sos_lt100'] for r in rows), 'sos_ge100_max': max(r['sos_ge100'] for r in rows),
                        'fir_lt100_max': max(r['fir_lt100'] for r in rows), 'fir_ge100_max': max(r['fir_ge100'] for r in rows)}
    hpf[m] = {'hpf': h, **per}
res['hpf_on'] = hpf
res['worst_pole_radius'] = worst_pole

# ---- 4. float32 coefficient rounding effect (record is float32): compare with float64 design
from mic_colour.sos_table import interpolate_params
from mic_colour.sos_fit import params_to_sos, butter_hp_sos, hpf_order
from mic_colour.model import angle_weight
q = {}
for m in MICS:
    t = _load_one(m); model = store.model_for(m); h = store.hpf_of(m) or {}
    worst = 0.0
    for sr in (44100, 48000):
        for deg in range(0, 181, 5):
            w = float(np.asarray(angle_weight(float(deg), model.p)).reshape(-1)[0])
            s64 = params_to_sos(interpolate_params(t, w), t['layout'], sr)
            if h.get('hpf_hz'): s64 = np.vstack([s64, butter_hp_sos(h['hpf_hz'], hpf_order(h.get('hpf_slope') or 12), sr)])
            s32 = s64.astype(np.float32).astype(np.float64)
            worst = max(worst, float(np.max(np.abs(sos_db(s64, F_DENSE[F_DENSE < 0.45*sr], sr) - sos_db(s32, F_DENSE[F_DENSE < 0.45*sr], sr)))))
    q[m] = worst
res['float32_coeff_rounding_max_db'] = q

# ---- 5. Render-side cost: Python apply_sos (pure-python loop) vs apply_fir per buffer
x = np.random.default_rng(0).normal(size=48000)
rec = rec_for('ShureSM57', 90, 48000, False); sos = unpack_record(rec)
t0 = time.perf_counter(); y1 = apply_sos(x, sos); t_sos = time.perf_counter() - t0
from mic_colour.design import apply_fir
ir = design_ir(store.model_for('ShureSM57'), 90.0, 48000)
t0 = time.perf_counter(); y2 = apply_fir(x, ir); t_fir = time.perf_counter() - t0
from scipy.signal import sosfilt
t0 = time.perf_counter(); y3 = sosfilt(np.hstack([sos[:, :3], np.ones((len(sos), 1)), sos[:, 3:]]), x); t_scipy = time.perf_counter() - t0
res['render_cost_1s_buffer_s'] = {'apply_sos_python': t_sos, 'apply_fir_fft': t_fir, 'scipy_sosfilt_equiv': t_scipy,
                                  'sosfilt_vs_apply_sos_maxdiff': float(np.max(np.abs(y1 - y3)))}

(OUT / 'eval_sos.json').write_text(json.dumps(res, indent=1, default=float))

# ---- summary table
lines = ['| Mic | SOS vs model max (48k/44.1k, 1-180 deg) | SOS vs MEASURED max / RMS (48k) | old FIR vs MEASURED max / RMS (48k) | model vs MEASURED max / RMS | SOS vs FIR max (48k) | HPF on: SOS <100 Hz / FIR <100 Hz (48k) | preset hash | verdict |', '|---|---|---|---|---|---|---|---|---|']
for m in MICS:
    d = dense[m]; me = meas[m].get('agg', {})
    hp = hpf.get(m)
    hps = f"{hp['48000']['sos_lt100_max']:.2f} / {hp['48000']['fir_lt100_max']:.1f}" if hp else 'no HPF'
    ok = d['48000']['max'] <= 0.5 and d['44100']['max'] <= 0.6 and prov[m]['hash_ok'] and (not hp or hp['48000']['sos_lt100_max'] <= 0.5)
    lines.append(f"| {m} | {d['48000']['max']:.2f} / {d['44100']['max']:.2f} | {me['sos_vs_meas_48000']['max']:.2f} / {me['sos_vs_meas_48000']['rms']:.2f} | "
                 f"{me['fir_vs_meas_48000']['max']:.2f} / {me['fir_vs_meas_48000']['rms']:.2f} | {me['model_vs_meas']['max']:.2f} / {me['model_vs_meas']['rms']:.2f} | "
                 f"{me['sos_vs_fir_48000']['max']:.2f} | {hps} | {'ok' if prov[m]['hash_ok'] else 'MISMATCH'} | {'PASS' if ok else 'FAIL'} |")
lines.append('')
lines.append(f"Worst pole radius over all mics/angles/rates/HPF: {worst_pole[0]:.6f} at {worst_pole[1]}")
lines.append(f"Worst float32-coefficient rounding effect: {max(q.values()):.4f} dB ({max(q, key=q.get)})")
lines.append(f"Render cost, 1 s mono buffer, one SOS entry: python apply_sos {t_sos*1000:.0f} ms vs FFT FIR {t_fir*1000:.1f} ms vs scipy sosfilt {t_scipy*1000:.2f} ms")
(OUT / 'summary_table.md').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
