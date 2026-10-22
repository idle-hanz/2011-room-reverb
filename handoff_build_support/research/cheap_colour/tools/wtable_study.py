#!/usr/bin/env python3
"""Proposed PRODUCTION design check: per-mic w-table of K=3 SOS parameters.
The fitter response depends on angle only through w = 0.5(1-cos th)^p (model.py), so one table
over w in [0,1] per (mic, sr) covers every angle. Built once (warm-started fits, ~65 x 60 ms),
cacheable in the preset JSON / on disk. At runtime: w -> linear interpolation of the section
parameters (log f, gain dB, log Q) -> RBJ coefficients (a few flops; can run in Python, JS or C).
Error is measured against the CURRENT Play FIR (design_ir 4096 taps @48k) at 36 angles x 20 mics,
plus the optional manufacturer HPF as exact extra biquads (Butterworth, bilinear) on the 3 mic
families that have one.
"""
import json, sys, time, math, os
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SW = Path('/workspace/build_support/snapshot_2026-09-27/software')
sys.path[:0] = [str(SW), str(SW / 'engine'), str(HERE)]
os.chdir(SW)
from mic_colour.design import design_ir
from mic_colour.preset_store import get_store
from mic_colour.model import relative_db, angle_weight
import sos_fit as SF

FS = int(sys.argv[1]) if len(sys.argv) > 1 else 48000
K = 3; NW = int(os.environ.get('NW', 65)); REPAIR_DB = float(os.environ.get('REPAIR_DB', 0.1)); REFINE_DB = float(os.environ.get('REFINE_DB', 0.2)); MAX_NODES = 160
OUT = HERE.parent / 'results'; OUT.mkdir(exist_ok=True)
store = get_store()
ids = [p['mic_id'] for p in json.load(open(SW.parent / 'mic_fitter' / 'presets' / 'index.json'))['presets']]
if os.environ.get('MICS'): ids = [i for i in ids if i in os.environ['MICS'].split(',')]
OUT_SUFFIX = os.environ.get('OUT_SUFFIX', '')
ANG_STEP = float(os.environ.get('ANG_STEP', 5))
NF = 1 << 16
def fir_db_fn(ir):
    H = np.fft.rfft(ir, NF); fr = np.fft.rfftfreq(NF, 1 / FS)
    db = 20 * np.log10(np.maximum(np.abs(H), 1e-12)); return lambda f: np.interp(f, fr, db)

def butter_hp_sos(fc, order, fs):
    """Exact digital Butterworth HPF sections (bilinear, prewarped at fc)."""
    from scipy.signal import butter
    s = butter(order, fc, btype='highpass', fs=fs, output='sos')
    return np.array([[r[0] / r[3], r[1] / r[3], r[2] / r[3], r[4] / r[3], r[5] / r[3]] for r in s])

table = {}; res = {}; t_build = []
for mid in ids:
    model = store.model_for(mid); p_exp = model.p
    t0 = time.time(); P = []; prev = None
    ws = np.linspace(0, 1, NW)
    for w in ws:
        if w == 0:
            P.append(None); continue
        # angle with this w: th = acos(1 - 2 w^(1/p))
        th = math.degrees(math.acos(max(-1.0, 1 - 2 * w ** (1 / p_exp))))
        tgt = lambda f, th=th: np.asarray(relative_db(model, np.asarray(f), th))
        sos, pp = SF.fit(tgt, FS, K, p0=prev); prev = pp; P.append(pp)
    P[0] = P[1].copy(); P[0][1::3] = 0.0          # w=0: identity (0 dB gains), same f/Q as w=1/64
    # Continuity repair: the fitter can jump to another parameter branch at one node (e.g. two
    # shelves swapping roles). Endpoints are then fine but the linear interpolation between them is
    # not. Check each interval midpoint against the model; refit the offending node seeded from its
    # neighbour and keep the candidate that lowers the worst adjacent midpoint error.
    def _tgt_w(w):
        th = math.degrees(math.acos(max(-1.0, 1 - 2 * w ** (1 / p_exp))))
        return lambda f, th=th: np.asarray(relative_db(model, np.asarray(f), th))
    def _mid_err_g(P, wl, i):
        return SF.errors(SF.params_to_sos(0.5 * (P[i] + P[i + 1]), SF.LAYOUTS[K], FS), _tgt_w(0.5 * (wl[i] + wl[i + 1])), FS)[0]
    def _mid_err(P, i):
        return SF.errors(SF.params_to_sos(0.5 * (P[i] + P[i + 1]), SF.LAYOUTS[K], FS), _tgt_w(0.5 * (ws[i] + ws[i + 1])), FS)[0]
    n_rep = 0
    for _pass in range(3):
        bad = [i for i in range(1, NW - 1) if _mid_err(P, i) > REPAIR_DB]
        if not bad: break
        for i in bad:
            for j, seed in ((i + 1, P[i]), (i, P[i + 1])):
                if j <= 0 or j >= NW: continue
                _, cand = SF.fit(_tgt_w(ws[j]), FS, K, p0=np.array(seed))
                adj = [k for k in (j - 1, j) if 1 <= k < NW - 1]
                before = max(_mid_err(P, k) for k in adj)
                Q = [x.copy() for x in P]; Q[j] = np.array(cand)
                if max(_mid_err(Q, k) for k in adj) < before - 1e-3:
                    P[j] = np.array(cand); n_rep += 1
    # Adaptive refinement: bisect any interval whose midpoint is still > REFINE_DB off the model
    # (branch jumps near a shelf gain sign change cannot be interpolated away). Non-uniform w grid.
    ws_l = list(ws); P = [np.array(x) for x in P]
    for _depth in range(4):
        new_nodes = 0; i = 1
        while i < len(ws_l) - 1:
            if len(ws_l) >= MAX_NODES: break
            if _mid_err_g(P, ws_l, i) > REFINE_DB:
                wm = 0.5 * (ws_l[i] + ws_l[i + 1])
                _, pm = SF.fit(_tgt_w(wm), FS, K, p0=np.array(P[i]))
                _, pm2 = SF.fit(_tgt_w(wm), FS, K, p0=np.array(P[i + 1]))
                e1 = SF.errors(SF.params_to_sos(pm, SF.LAYOUTS[K], FS), _tgt_w(wm), FS)[0]
                e2 = SF.errors(SF.params_to_sos(pm2, SF.LAYOUTS[K], FS), _tgt_w(wm), FS)[0]
                ws_l.insert(i + 1, wm); P.insert(i + 1, np.array(pm if e1 <= e2 else pm2)); new_nodes += 1; i += 2
            else:
                i += 1
        if not new_nodes: break
    ws = np.array(ws_l)
    worst_mid = max(_mid_err_g(P, ws_l, i) for i in range(1, len(ws_l) - 1))
    t_build.append(time.time() - t0)
    P = np.array(P); table[mid] = {'w': ws.tolist(), 'params': P.tolist()}
    rows = []
    for th in np.arange(ANG_STEP, 180.0001, ANG_STEP):
        ir = design_ir(model, th, FS)
        if ir is None: continue
        w = float(angle_weight(th, p_exp)); i = int(min(max(np.searchsorted(ws, w) - 1, 0), len(ws) - 2)); fr = (w - ws[i]) / (ws[i + 1] - ws[i])
        pl = (1 - fr) * P[i] + fr * P[i + 1]
        sos = SF.params_to_sos(pl, SF.LAYOUTS[K], FS)
        rows.append({'deg': th, 'w': w, 'err_vs_fir': SF.errors(sos, fir_db_fn(ir), FS)})
    hp = store.hpf_of(mid) or {}
    if hp.get('hpf_hz'):
        order = {6: 1, 12: 2, 18: 3}.get(int(hp.get('hpf_slope') or 12), 2)
        irh = design_ir(model, 90, FS, hpf=hp, hpf_engaged=True)
        w = float(angle_weight(90, p_exp)); i = int(min(max(np.searchsorted(ws, w) - 1, 0), len(ws) - 2)); fr = (w - ws[i]) / (ws[i + 1] - ws[i])
        sos = np.vstack([SF.params_to_sos((1 - fr) * P[i] + fr * P[i + 1], SF.LAYOUTS[K], FS), butter_hp_sos(hp['hpf_hz'], order, FS)])
        from mic_colour.hpf import stack_hpf
        f = np.geomspace(20, 20000, 600)
        ana = stack_hpf(np.asarray(relative_db(model, f, 90)), f, hp['hpf_hz'], hp.get('hpf_slope') or 12, True)
        e_fir = SF.sos_db(sos, f, FS) - fir_db_fn(irh)(f)
        e_ana = SF.sos_db(sos, f, FS) - ana
        e_fir_vs_ana = fir_db_fn(irh)(f) - ana
        hrow = {'hpf_hz': hp['hpf_hz'], 'order': order,
                'sos_vs_fir_max': float(np.max(np.abs(e_fir))), 'f_at_max': float(f[np.argmax(np.abs(e_fir))]),
                'sos_vs_analytic_max': float(np.max(np.abs(e_ana))), 'fir_vs_analytic_max': float(np.max(np.abs(e_fir_vs_ana))),
                'fir_vs_analytic_max_above_100hz': float(np.max(np.abs(e_fir_vs_ana[f >= 100])))}
    else:
        hrow = None
    res[mid] = {'rows': rows, 'hpf_90deg': hrow, 'repaired_nodes': n_rep, 'n_nodes': int(len(ws)), 'worst_midpoint_err_vs_model_db': worst_mid}
    print(mid, 'build %.1fs' % t_build[-1], 'repaired %d nodes %d worst-mid %.3f' % (n_rep, len(ws), worst_mid), 'max err %.3f dB' % max(r['err_vs_fir'][0] for r in rows), 'rms max %.3f' % max(r['err_vs_fir'][1] for r in rows),
          ('HPF@90: sos-vs-FIR %.1f dB @%.0f Hz; sos-vs-analytic %.2f; FIR-vs-analytic %.1f (>100 Hz %.1f)' % (hrow['sos_vs_fir_max'], hrow['f_at_max'], hrow['sos_vs_analytic_max'], hrow['fir_vs_analytic_max'], hrow['fir_vs_analytic_max_above_100hz'])) if hrow else '', flush=True)
json.dump({'fs': FS, 'K': K, 'NW': NW, 'layout': SF.LAYOUTS[K], 'build_s_mean': float(np.mean(t_build)), 'res': res}, open(OUT / f'wtable_{FS}{OUT_SUFFIX}.json', 'w'))
json.dump({'schema': 'colour_sos_wtable.v0 (prototype)', 'fs': FS, 'K': K, 'layout': SF.LAYOUTS[K], 'param_order': 'per section: log2(f_hz), gain_db, log2(Q)',
           'w_grid': 'per mic: base linspace(0,1,%d) + adaptive bisection (tables[mic].w)' % NW, 'tables': table}, open(OUT / f'wtable_params_{FS}{OUT_SUFFIX}.json', 'w'))
