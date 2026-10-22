#!/usr/bin/env python3
"""compare_ref.py: 2011 Reaktor reference IRs vs the rebuild (Render + Play variants).

Given Idle's captured WAVs (each with a sidecar JSON of panel / Structure values, see
../CAPTURE_GUIDE.md and capture_template.json), this renders matching IRs from:
  render_current      Python Render of the current tree (same-sample loop solve)
  play_current        Play (live_stereo.wasm via the real fdn_worklet.js) of the current tree
  play_F1-F3          Play of the engine-fix tree (denormal, per-line loss, 48 kHz delay rounding)
  play_F1-F3+F5       Play of the engine-fix tree + same-sample loop solve (F5)
  (optional, --lock-variants) lock_play_current / lock_play_F1-F3: decay lock ON with decay_s =
      the reference's own 1 kHz T30, to show what "dial the 2011 T30" gives with and without F2.
and reports per-band T20/T30/EDT, two-slope (early/late T60) fits, EDC plots, spectral balance,
HF residue (late 9/11 kHz T60, near-Nyquist energy), stereo correlation, levels/timing, and
a verdict on:
  (a) keep the long two-stage tail (in-loop Dffs allpass) vs apply F2 (tail follows the dial)
  (b) Play loop timing: one-sample (z^-1) loop vs same-sample solve (F5)

Run on the box (needs node for Play; Idle's PC has none):
  PY=/workspace/scratch_er_dropout/venv/bin/python
  $PY compare_ref.py --refs <dir with RR2011_*.wav + .json> --out <report dir>
Options: --play-secs 15 --render-secs 8 --no-render --lock-variants --jobs 2
         --tree NAME=/path/to/software (repeatable; replaces the defaults)
Nothing in any software/ tree is written. Reference WAVs are read only.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rr_metrics as MX  # noqa: E402

BS = HERE.parents[2]                      # .../build_support
ENGINE_LIB = BS / 'engine' / 'tests' / 'lib'
SR = 48000
DEFAULT_TREES = {
    'current': BS / 'snapshot_2026-09-27' / 'software',
    'F1-F3': BS / 'engine' / 'work' / 'sw_fix' / 'software',
    'F1-F3+F5': BS / 'engine' / 'work' / 'sw_fix_same' / 'software',
}
DEFAULT_PY = '/workspace/scratch_er_dropout/venv/bin/python'

# ----------------------------------------------------------------------------- sidecar mapping
SURF_MAP = {'Sides': ['A', 'C'], 'Ahead': ['B'], 'Behind': ['D'], 'Floor': ['E'], 'Ceiling': ['F']}


def _g(d, *path, default=None):
    for k in path:
        if not isinstance(d, dict) or k not in d or d[k] is None:
            return default
        d = d[k]
    return d


def body_from_sidecar(sc: dict):
    """Map 2011 panel/Structure readings to a rebuild app body. Returns (body, dffs_knob, notes).
    Each mapping is tagged: VERIFIED (Structure law in code) or ASSUMED."""
    notes = []
    W = float(_g(sc, 'room', 'W', default=6.0)); H = float(_g(sc, 'room', 'H', default=3.0)); L = float(_g(sc, 'room', 'L', default=8.0))
    sox = _g(sc, 'source', 'SX_term23'); soz = _g(sc, 'source', 'SZ_term24')
    mz = _g(sc, 'mic', 'HZ_term28'); my = _g(sc, 'mic', 'MY_term27')
    if sox is None: sox = 0.5; notes.append('SX (term 23) missing: SoX=0.5 ASSUMED')
    if soz is None: soz = 0.5; notes.append('SZ (term 24) missing: SoZ=0.5 ASSUMED')
    if mz is None: mz = L - 1.5; notes.append('HZ/MZ (term 28) missing: MZ=L-1.5 ASSUMED')
    if my is None: my = 1.5; notes.append('MY (term 27) missing: 1.5 m ASSUMED')
    mcz = L - float(mz)                                   # VERIFIED Prepare: MCZ = L - MZ
    sx = W * float(sox)                                   # VERIFIED Prepare: SX = W*SoX
    sz = mcz + (L - mcz) * float(soz)                     # VERIFIED Prepare: SZ = MCZ + (L-MCZ)*SoZ
    body = {'W': W, 'H': H, 'L': L, 'sx': sx, 'sz': sz, 'mcz': mcz, 'my': float(my), 'sy': float(my),
            'mcx': W * 0.5, 'reaktor_parity': True,
            'decay_lock': False, 'early_wet': 0.0, 'fdn_wet': 1.0, 'direct_wet': 1.0, 'dry_gain': 0.0,
            'colour_mode': 'BYPASS', 'hadamard_n': 32}
    space = _g(sc, 'mic', 'MSS_term25')
    if space is not None: body['space'] = float(space)
    else: notes.append('MSS/Space (term 25) missing: rebuild default 0.25 used')
    car = _g(sc, 'mic', 'Car_term29')
    if car is not None: body['car_omni'] = float(car)
    else: notes.append('Car/Omni (term 29) missing: rebuild default used')
    div = _g(sc, 'mic', 'diverg_MDPC')
    if div is not None: body['diverg'] = float(div); notes.append('diverg from Structure MDPC reading (ASSUMED same unit as rebuild diverg)')
    else: notes.append('Diverg/MDPC not read: rebuild default diverg=1.0 used (ASSUMED)')
    hf = _g(sc, 'mic', 'HF_term30')
    if hf is not None:
        body['mic_response_hz'] = float(hf)
        if float(hf) < 19000: notes.append(f'Mic Response {hf} Hz: the 2011 Res one-pole is NOT modelled in the rebuild (apply_mic false) -> expect extra HF loss in the reference')
    gf = _g(sc, 'fdn', 'GainF')
    if gf is None: gf = 1.0; notes.append('GainF missing: 1.0 ASSUMED')
    body['fdn_g'] = float(gf)                             # VERIFIED: UI fdn_g is Structure Gain; loop = Gain/32
    dm = _g(sc, 'fdn', 'diffusion_master')
    if dm is None: dm = -0.25; notes.append('Diffusion Master missing: -0.25 (485 default) ASSUMED')
    body['diffusion_master'] = float(dm)
    sd = _g(sc, 'fdn', 'surface_diffusion', default={}) or {}
    surfaces = {}
    for name, letters in SURF_MAP.items():
        v = sd.get(name)
        for Lt in letters:
            card = {'absorb': [0.0] * 7, 'eq': {'low_shelf_db': 0.0, 'high_shelf_db': 0.0, 'peak_db': 0.0}}
            if v is not None: card['diffusion'] = float(v)
            surfaces[Lt] = card
        if v is None: notes.append(f'surface Diffusion "{name}" missing: rebuild default 0.15')
    body['surfaces'] = surfaces
    if not _g(sc, 'other', 'surfaces_dB_all_zero', default=False):
        notes.append('Surfaces dB not confirmed 0: 2011 per-surface peak EQ is not mapped (rebuild cards flat, absorb 0)')
    wet = _g(sc, 'air', 'humidity_wet')
    if wet is None: wet = 400.0; notes.append('Humidity missing: 400 (486 default) ASSUMED')
    body['humidity'] = max(1e-3, min(1.0, (float(wet) - 100.0) / 600.0))   # VERIFIED map 100..700 -> 0..1 (0 = bypass)
    knob = None
    din = _g(sc, 'fdn', 'diffuser_diffusion_in')
    if din is not None:
        mean = (W + H + L) / 3.0; knob = float(din) / (max(W, H, L) * mean)
        notes.append(f'Diffuser "Diffusion" in = {din} -> dffs knob {knob:.5f} (rebuild constant 0.0333)')
    if _g(sc, 'other', 'AGC') not in (None, 'Off', 'off', False):
        notes.append('AGC was ON in the capture: reference level/tail may be gain-ridden')
    return body, knob, notes


# ----------------------------------------------------------------------------- IO
def read_wav(path):
    sr, x = wavfile.read(str(path))
    if x.dtype.kind == 'i':
        x = x.astype(np.float64) / float(np.iinfo(x.dtype).max + 1)
    elif x.dtype.kind == 'u':
        x = (x.astype(np.float64) - 128.0) / 128.0
    else:
        x = x.astype(np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    return sr, x[:, :2]


def prepare_ref(wav, sc, notes):
    sr, x = read_wav(wav)
    cap = sc.get('capture', {}) if isinstance(sc.get('capture'), dict) else {}
    t_imp = float(cap.get('impulse_at_s', 0.5)); lat = int(cap.get('latency_samples', 0) or 0)
    amp = 10 ** (float(cap.get('impulse_dbfs', 0.0)) / 20.0)
    i0 = int(round(t_imp * sr)) + lat
    pre = x[: max(0, i0 - 16)]
    post = x[i0:]
    if len(pre) and np.max(np.abs(pre)) > 1e-4 * max(np.max(np.abs(post)), 1e-30):
        notes.append('WARNING: energy before the impulse instant: pre-roll/latency wrong, or input not silent')
    y = post / amp
    if sr != SR:
        g = math.gcd(sr, SR)
        y = np.stack([resample_poly(y[:, c], SR // g, sr // g) for c in range(2)], 1)
        notes.append(f'reference resampled {sr} -> {SR} Hz (polyphase) for comparison with Play')
    if cap.get('sample_rate') and int(cap['sample_rate']) != sr:
        notes.append(f'sidecar sample_rate {cap["sample_rate"]} != WAV header {sr}')
    return y[:, 0], y[:, 1]


# ----------------------------------------------------------------------------- rendering
class Renderer:
    def __init__(self, a):
        self.py = a.python; self.node = a.node; self.trees = a.trees
        self.cache = Path(a.out).resolve() / 'cache'; self.cache.mkdir(parents=True, exist_ok=True)

    def _key(self, *parts):
        return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def render(self, tree, body, knob, secs):
        out = self.cache / f'R_{tree}_{self._key(tree, body, knob, secs)}.f32'
        if not out.exists():
            job = {'body': body, 'ir_ms': secs * 1000.0, 'sr': SR, 'dffs_knob': knob}
            r = subprocess.run([self.py, str(HERE / 'rr_tree_driver.py'), str(self.trees[tree]), 'render', json.dumps(job), str(out)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f'render {tree} failed: {r.stderr[-800:]}')
        x = np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)
        return x[:, 0], x[:, 1]

    def play(self, tree, body, knob, secs):
        k = self._key(tree, body, knob, secs)
        pj = self.cache / f'P_{tree}_{k}.json'; out = self.cache / f'Pir_{tree}_{k}.f32'
        if not out.exists():
            job = {'body': body, 'sr': SR, 'dffs_knob': knob}
            r = subprocess.run([self.py, str(HERE / 'rr_tree_driver.py'), str(self.trees[tree]), 'params', json.dumps(job), str(pj)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f'params {tree} failed: {r.stderr[-800:]}')
            r = subprocess.run([self.node, str(ENGINE_LIB / 'wasm_run.js'), str(self.trees[tree]), str(pj), json.dumps({'colour_on': False}),
                                'ir', str(secs), str(out)], capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f'play {tree} failed: {r.stderr[-800:]}')
        x = np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)
        return x[:, 0], x[:, 1]


def variant_jobs(a):
    v = []
    if not a.no_render and 'current' in a.trees:
        v.append(('render_current', 'render', 'current', {}))
    for t in a.trees:
        v.append((f'play_{t}', 'play', t, {}))
    return v


# ----------------------------------------------------------------------------- comparison
def fnum(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return 'n/a'
    return f'{x:.{nd}f}'


def compare_one(ref, var):
    """Distance of a variant from the reference (lower = closer)."""
    d = {}
    errs = []
    for fc in ('250', '500', '1000', '2000', '4000', '8000'):
        a = ref['bands'].get(fc, {}).get('T30'); b = var['bands'].get(fc, {}).get('T30')
        if a and b and np.isfinite(a) and np.isfinite(b) and a > 0 and b > 0:
            errs.append(abs(math.log(b / a)))
    d['t30_logerr'] = float(np.mean(errs)) if errs else float('nan')
    a = ref['bands']['1000']; b = var['bands']['1000']
    d['late_logerr'] = abs(math.log(b['T2'] / a['T2'])) if all(np.isfinite([a['T2'], b['T2']])) and a['T2'] > 0 and b['T2'] > 0 else float('nan')
    bal = [abs(ref['balance_tail'][k] - var['balance_tail'][k]) for k in ref['balance_tail'] if k in var['balance_tail'] and k <= 8000]
    d['balance_db'] = float(np.mean(bal)) if bal else float('nan')
    d['nyq_db_diff'] = abs(ref['hf']['nyq_db'] - var['hf']['nyq_db']) if np.isfinite(ref['hf']['nyq_db']) and np.isfinite(var['hf']['nyq_db']) else float('nan')
    d['corr_diff'] = abs(ref['stereo']['corr0'] - var['stereo']['corr0'])
    d['tail_level_diff_db'] = var['tail_vs_direct_db'] - ref['tail_vs_direct_db']
    d['arrival_diff_ms'] = var['first_arrival_ms'] - ref['first_arrival_ms']
    return d


def edc_rms_db(refLR, varLR, sr, floor=-50.0):
    """RMS dB difference of broadband EDCs over the range where the reference is above floor."""
    er = MX.schroeder(0.5 * (refLR[0] + refLR[1])); ev = MX.schroeder(0.5 * (varLR[0] + varLR[1]))
    n = min(len(er), len(ev)); er, ev = er[:n], ev[:n]
    m = er > floor
    return float(np.sqrt(np.mean((er[m] - ev[m]) ** 2))) if np.any(m) else float('nan')


def plot_capture(path, stem, curves, metrics, sr):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    names = list(curves)
    fig, axs = plt.subplots(2, 3, figsize=(16, 9))
    for ax, b in zip(axs.flat[:5], ['bb', '250', '1000', '4000', '8000']):
        for nm in names:
            t, e = curves[nm][b]
            ax.plot(t, e, lw=2.2 if nm == 'REFERENCE' else 1.0, color='k' if nm == 'REFERENCE' else None, label=nm)
        ax.set_ylim(-80, 2); ax.set_title(f'EDC {b if b != "bb" else "broadband"}' + (' Hz' if b != 'bb' else '')); ax.grid(alpha=.3)
        ax.set_xlabel('s'); ax.set_ylabel('dB')
    axs.flat[0].legend(fontsize=7)
    ax = axs.flat[5]
    for nm in names:
        bt = metrics[nm]['balance_tail']
        ks = sorted(bt); ax.semilogx(ks, [bt[k] for k in ks], 'o-', lw=2.2 if nm == 'REFERENCE' else 1, color='k' if nm == 'REFERENCE' else None, label=nm)
    ax.set_title('tail spectral balance (dB re 1 kHz octave)'); ax.grid(alpha=.3); ax.set_xlabel('Hz')
    fig.suptitle(stem); fig.tight_layout(); fig.savefig(path, dpi=90); plt.close(fig)


def verdicts(rows):
    """rows: list of per-capture dicts with ref metrics, variant metrics, distances, settings."""
    out = {'a': {}, 'b': {}}
    diff_rows = [r for r in rows if abs(r['settings'].get('diffusion_master', 0)) > 1e-6]
    zero_rows = [r for r in rows if abs(r['settings'].get('diffusion_master', 0)) <= 1e-6]
    # ---- (a) two-stage tail
    ratios, twos = [], []
    for r in diff_rows:
        b = r['metrics']['REFERENCE']['bands']['1000']
        if np.isfinite(b['T1']) and np.isfinite(b['T2']) and b['T1'] > 0:
            ratios.append(b['T2'] / b['T1'] if b['two_stage'] else 1.0); twos.append(b['two_stage'])
    A = out['a']
    A['n_captures_with_diffusion'] = len(diff_rows)
    A['ref_late_over_early_1k_median'] = float(np.median(ratios)) if ratios else float('nan')
    A['ref_two_stage_fraction'] = float(np.mean(twos)) if twos else float('nan')
    # sensitivity of reference late T60 to GainF vs Diffusion Master
    def late(r): return r['metrics']['REFERENCE']['bands']['1000']['T2']
    by_g, by_dm = {}, {}
    for r in rows:
        s = r['settings']; by_g.setdefault(s.get('diffusion_master'), []).append((s.get('fdn_g'), late(r)))
        by_dm.setdefault(s.get('fdn_g'), []).append((s.get('diffusion_master'), late(r)))
    def spread(groups):
        v = []
        for k, lst in groups.items():
            vals = [x[1] for x in lst if np.isfinite(x[1]) and x[1] > 0]
            if len(vals) >= 2: v.append(math.log(max(vals) / min(vals)))
        return float(np.mean(v)) if v else float('nan')
    A['late_T60_log_spread_vs_GainF'] = spread(by_g)
    A['late_T60_log_spread_vs_DiffMaster'] = spread(by_dm)
    def _late_err(r):
        for v in ('play_F1-F3+F5', 'play_F1-F3', 'render_current', 'play_current'):
            if v in r['dist'] and np.isfinite(r['dist'][v].get('late_logerr', np.nan)):
                return r['dist'][v]['late_logerr']
        return np.nan
    cur = [_late_err(r) for r in diff_rows]
    cur = [c for c in cur if np.isfinite(c)]
    A['rebuild_unlocked_late_T60_logerr_median'] = float(np.median(cur)) if cur else float('nan')
    rt = A['ref_late_over_early_1k_median']; fr = A['ref_two_stage_fraction']; le = A['rebuild_unlocked_late_T60_logerr_median']
    if not ratios:
        A['verdict'] = 'INCONCLUSIVE: no captures with Diffusion Master != 0.'
    elif fr >= 0.5 and rt >= 1.5:
        if np.isfinite(le) and le <= math.log(1.35):
            A['verdict'] = ('KEEP the two-stage tail as the authentic 2011 behaviour: the reference shows it '
                            f'(late/early T60 median {rt:.2f}, two-stage in {100*fr:.0f}% of Dffs captures) and the rebuild '
                            f'unlocked path reproduces the late slope (median |log err| {le:.2f}). Apply F2 ONLY to the decay-lock '
                            'path (dial honesty) and keep unlocked/GainF = 2011 mode untouched (F2 already leaves it alone).')
        else:
            A['verdict'] = ('2011 HAS a two-stage tail (late/early median %.2f), but the rebuild late slope does not match '
                            '(median |log err| %s). Keep the structure, fix the Dffs scale first (read the Diffuser "Diffusion" in value), '
                            'then re-run; apply F2 to decay-lock only.' % (rt, fnum(le)))
    elif rt < 1.3 or fr < 0.25:
        A['verdict'] = ('APPLY F2 generally: the 2011 reference decays single-slope (late/early median %.2f); '
                        'the rebuild\'s long second stage is not in the original.' % rt)
    else:
        A['verdict'] = 'MIXED: weak/partial two-stage in the reference (median ratio %.2f, fraction %.0f%%). Listen-test before deciding.' % (rt, 100 * fr)
    # ---- (b) loop timing
    B = out['b']
    cand = {'one-sample (z^-1, F1-F3 tree)': ['play_F1-F3'], 'same-sample (F5 / Render)': ['play_F1-F3+F5', 'render_current']}
    score = {}
    for lab, vs in cand.items():
        s = []
        for r in rows:
            best = []
            for v in vs:
                d = r['dist'].get(v)
                if not d: continue
                parts = [d.get('nyq_db_diff', np.nan) / 6.0, d.get('t30_logerr', np.nan) / math.log(1.15),
                         r['edc_rms'].get(v, np.nan) / 3.0]
                parts = [p for p in parts if np.isfinite(p)]
                if parts: best.append(float(np.mean(parts)))
            if best: s.append(min(best))
        score[lab] = float(np.mean(s)) if s else float('nan')
    B['score_lower_is_closer'] = score
    ref_nyq = [r['metrics']['REFERENCE']['hf']['nyq_db'] for r in rows]
    B['ref_near_nyquist_db_median'] = float(np.nanmedian(ref_nyq)) if ref_nyq else float('nan')
    for v in ('play_current', 'play_F1-F3', 'play_F1-F3+F5', 'render_current'):
        vals = [r['metrics'][v]['hf']['nyq_db'] for r in rows if v in r['metrics']]
        if vals: B[f'{v}_near_nyquist_db_median'] = float(np.nanmedian(vals))
    # sample-level timing test. ONLY play_F1-F3 (z^-1) vs play_F1-F3+F5 / render_current (same-sample)
    # decide (b): they share 48 kHz integer delays. play_current also differs in delay rounding (F3),
    # so it is reported but excluded from (b).
    ft = {}
    for v in ('play_current', 'play_F1-F3', 'play_F1-F3+F5', 'render_current'):
        c1 = [r['dist'][v]['ft_c1'] for r in rows if v in r['dist']]
        n2 = [r['dist'][v]['ft_null2_db'] for r in rows if v in r['dist']]
        l2 = [r['dist'][v]['ft_lag2'] - r['dist'][v]['ft_lag1'] for r in rows if v in r['dist']]
        if c1: ft[v] = {'c1_median': float(np.nanmedian(c1)), 'loop_window_null_db_median': float(np.nanmedian(n2)), 'trip_lag_median': float(np.median(l2))}
    B['fine_timing'] = ft
    zb = ft.get('play_F1-F3')
    s_ = [ft[v] for v in ('play_F1-F3+F5', 'render_current') if v in ft]
    sb = min(s_, key=lambda d: d['loop_window_null_db_median']) if s_ else None
    geometry_ok = bool(zb and sb and min(zb['c1_median'], sb['c1_median']) >= 0.5)
    B['fine_timing_valid'] = geometry_ok
    ks = [k for k in score if np.isfinite(score[k])]
    if geometry_ok:
        nz, ns = zb['loop_window_null_db_median'], sb['loop_window_null_db_median']
        B['loop_null_z_minus_same_db'] = nz - ns
    if geometry_ok and min(nz, ns) <= -10.0 and abs(nz - ns) >= 3.0:
        win = 'ONE-SAMPLE (z^-1 loop, Reaktor-style unit delay)' if nz < ns else 'SAME-SAMPLE (F5 / Render structure)'
        B['verdict'] = (f'{win} matches the 2011 reference at sample level: loop-trip window (40-150 ms) null vs reference '
                        f'z^-1 {nz:.1f} dB, same-sample {ns:.1f} dB (first-pass images line up, c1 >= 0.5).')
    elif geometry_ok and min(nz, ns) <= -10.0:
        B['verdict'] = (f'NOT DISTINGUISHABLE at this loop gain: both loop timings null the reference equally in the loop-trip window '
                        f'(z^-1 {nz:.1f} dB, same-sample {ns:.1f} dB). The choice is inaudible for these settings; pick F5 (nulls Render).')
    elif len(ks) < 2:
        B['verdict'] = 'INCONCLUSIVE: need both a z^-1 variant and a same-sample variant.'
    else:
        k1, k2 = sorted(ks, key=lambda k: score[k])
        best_c1 = max(ft, key=lambda v: ft[v]['c1_median']) if ft else None
        B['best_first_pass_match'] = best_c1
        hint = ''
        if best_c1 == 'play_current' and ft[best_c1]['c1_median'] >= 0.5:
            hint = (' The first-pass images line up best with play_current: the reference delays look like ms rounded at 44.1 kHz '
                    '+ fractional read (not 48 kHz integer): relevant to F3, not to (b).')
        B['verdict'] = (f'INCONCLUSIVE at sample level (first-pass images of the F1-F3 trees do not line up with the reference, or '
                        f'neither loop timing nulls it). Weak evidence from decay/spectral score: {k1} ({score[k1]:.2f} vs {score[k2]:.2f}, '
                        f'lower = closer). Default to same-sample (F5): it nulls Render.' + hint)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--refs', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--tree', action='append', default=[]); ap.add_argument('--python', default=DEFAULT_PY)
    ap.add_argument('--node', default='node'); ap.add_argument('--play-secs', type=float, default=15.0)
    ap.add_argument('--render-secs', type=float, default=8.0); ap.add_argument('--no-render', action='store_true')
    ap.add_argument('--lock-variants', action='store_true'); ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--label', default='')
    a = ap.parse_args()
    a.trees = {}
    for t in a.tree:
        k, v = t.split('=', 1); a.trees[k] = Path(v)
    if not a.trees:
        a.trees = {k: v for k, v in DEFAULT_TREES.items() if v.exists()}
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    R = Renderer(a)
    wavs = sorted(Path(a.refs).glob('*.wav'))
    if not wavs:
        sys.exit('no .wav in ' + a.refs)
    rows = []
    for w in wavs:
        scp = w.with_suffix('.json')
        sc = json.loads(scp.read_text()) if scp.exists() else {}
        notes = [] if scp.exists() else ['NO SIDECAR JSON: all settings ASSUMED (template defaults)']
        body, knob, n2 = body_from_sidecar(sc); notes += n2
        L, Rr = prepare_ref(w, sc, notes)
        irs = {'REFERENCE': (L, Rr)}
        jobs = variant_jobs(a)
        ref_m = MX.analyse(L, Rr, SR, 'REFERENCE')
        if a.lock_variants:
            t30 = ref_m['bands']['1000']['T30']
            if np.isfinite(t30):
                lb = dict(body, decay_lock=True, decay_s=float(min(max(t30, 0.3), 8.0)))
                for t in ('current', 'F1-F3'):
                    if t in a.trees: jobs.append((f'lock_play_{t}', 'play', t, lb))
        def run(j):
            name, kind, tree, bover = j
            b = bover or body
            t0 = time.time()
            if kind == 'render':
                x = R.render(tree, b, knob, a.render_secs)
            else:
                x = R.play(tree, b, knob, a.play_secs)
            return name, x, time.time() - t0
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            for name, x, dt in ex.map(run, jobs):
                irs[name] = x
                print(f'  {w.stem}: {name} {dt:.1f}s', flush=True)
        metrics = {'REFERENCE': ref_m}
        for nm, (l, r) in irs.items():
            if nm != 'REFERENCE':
                metrics[nm] = MX.analyse(l, r, SR, nm)
        dist = {nm: compare_one(ref_m, metrics[nm]) for nm in metrics if nm != 'REFERENCE'}
        erms = {nm: edc_rms_db(irs['REFERENCE'], irs[nm], SR) for nm in irs if nm != 'REFERENCE'}
        curves = {nm: MX.edc_curves(*irs[nm], SR) for nm in irs}
        plot_capture(out / f'{w.stem}_edc.png', w.stem + (f'  [{a.label}]' if a.label else ''), curves, metrics, SR)
        if ref_m['zero_time_db_re_direct'] > -30 and abs(body['diffusion_master']) < 1e-6:
            notes.append(f't=0 energy {ref_m["zero_time_db_re_direct"]:.1f} dB re direct with Diffusion Master 0 (no allpass feed-forward expected): a dry path is probably ON')
        i_dir = int(round(ref_m['first_arrival_ms'] * 1e-3 * SR))
        for nm in dist:
            ft = MX.fine_timing(0.5 * (irs['REFERENCE'][0] + irs['REFERENCE'][1]), 0.5 * (irs[nm][0] + irs[nm][1]), SR, i_dir)
            dist[nm].update({'ft_' + k: v for k, v in ft.items()})
        rows.append({'stem': w.stem, 'settings': body, 'dffs_knob': knob, 'notes': notes, 'metrics': metrics,
                     'dist': dist, 'edc_rms': erms})
    V = verdicts(rows)
    json.dump({'label': a.label, 'trees': {k: str(v) for k, v in a.trees.items()}, 'rows': rows, 'verdicts': V},
              open(out / 'compare_report.json', 'w'), indent=1, default=lambda o: float(o) if isinstance(o, (np.floating,)) else str(o))
    write_md(out / 'COMPARE_REPORT.md', rows, V, a)
    print(json.dumps(V, indent=1, default=str))


def _rnd(v):
    if isinstance(v, dict):
        return {k: _rnd(x) for k, x in v.items()}
    if isinstance(v, float):
        return round(v, 3) if np.isfinite(v) else None
    return v


def write_md(path, rows, V, a):
    L = [f'# 2011 reference vs rebuild: comparison report {("[" + a.label + "]") if a.label else ""}', '',
         f'Generated {time.strftime("%Y-%m-%d %H:%M %Z")} by compare_ref.py. Trees: ' + ', '.join(f'`{k}`' for k in a.trees) + '.', '']
    if a.label:
        L += [f'> **{a.label}**', '']
    L += ['## Verdicts', '', f'**(a) two-stage tail vs F2:** {V["a"]["verdict"]}', '',
          '| metric | value |', '|---|---|'] + [f'| {k} | {fnum(v) if isinstance(v, float) else v} |' for k, v in V['a'].items() if k != 'verdict'] + [
          '', f'**(b) loop timing:** {V["b"]["verdict"]}', '', '| metric | value |', '|---|---|'] + [
          f'| {k} | {json.dumps(_rnd(v)) if isinstance(v, dict) else (fnum(v) if isinstance(v, float) else v)} |'
          for k, v in V['b'].items() if k != 'verdict'] + ['']
    for r in rows:
        s = r['settings']
        L += [f'## {r["stem"]}', '', f'GainF {s["fdn_g"]}, Diffusion Master {s["diffusion_master"]}, humidity(ui) {s["humidity"]:.3f}, '
              f'room {s["W"]}x{s["H"]}x{s["L"]}, dffs knob {r["dffs_knob"] if r["dffs_knob"] is not None else "0.0333 (code default)"}', '',
              f'![EDC]({r["stem"]}_edc.png)', '']
        if r['notes']:
            L += ['Notes:'] + [f'- {n}' for n in r['notes']] + ['']
        names = list(r['metrics'])
        L += ['| IR | T30 250 | T30 1k | T30 4k | T30 8k | T1 early 1k | T2 late 1k | two-stage 1k | late T60 9k/11k | near-Nyq dB | corr0 | IACC | tail/direct dB | direct ms | t=0 dB re direct | EDC rms dB | c1 / loop-window null / trip lag |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for nm in names:
            m = r['metrics'][nm]; b = m['bands']
            L.append(f'| {nm} | {fnum(b["250"]["T30"])} | {fnum(b["1000"]["T30"])} | {fnum(b["4000"]["T30"])} | {fnum(b["8000"]["T30"])} | '
                     f'{fnum(b["1000"]["T1"])} | {fnum(b["1000"]["T2"])} | {"yes" if b["1000"]["two_stage"] else "no"} | '
                     f'{fnum(m["hf"]["late_t60_9000"])}/{fnum(m["hf"]["late_t60_11000"])} | {fnum(m["hf"]["nyq_db"],1)} | '
                     f'{fnum(m["stereo"]["corr0"])} | {fnum(m["stereo"]["iacc"])} | {fnum(m["tail_vs_direct_db"],1)} | {fnum(m["first_arrival_ms"])} | '
                     f'{fnum(m["zero_time_db_re_direct"],1)} | {fnum(r["edc_rms"].get(nm), 2) if nm != "REFERENCE" else "-"} | '
                     + (f'{fnum(r["dist"][nm]["ft_c1"])} / {fnum(r["dist"][nm]["ft_null2_db"],1)} dB / {r["dist"][nm]["ft_lag2"] - r["dist"][nm]["ft_lag1"]:+d}' if nm != 'REFERENCE' else '-') + ' |')
        L += ['', 'Tail spectral balance, dB re 1 kHz octave (reference, then variant minus reference):', '',
              '| IR | ' + ' | '.join(str(k) for k in MX.BAL_BANDS) + ' |', '|---|' + '---|' * len(MX.BAL_BANDS)]
        ref_b = r['metrics']['REFERENCE']['balance_tail']
        for nm in names:
            bt = r['metrics'][nm]['balance_tail']
            vals = [(bt.get(k, np.nan) - (0 if nm == 'REFERENCE' else ref_b.get(k, np.nan))) for k in MX.BAL_BANDS]
            L.append(f'| {nm} | ' + ' | '.join(fnum(v, 1) for v in vals) + ' |')
        L.append('')
    Path(path).write_text('\n'.join(L))


if __name__ == '__main__':
    main()
