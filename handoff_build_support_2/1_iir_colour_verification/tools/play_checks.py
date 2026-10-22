#!/usr/bin/env python3
"""Package 1, Play/Render side: SOS vs FIR nulls in Play (real worklet + wasm via node), CPU per block,
Render cost + Render SOS-vs-FIR null, and a direct-path Play-vs-Render colour check (C run_sos vs Python apply_sos).
Usage: python play_checks.py --sw <software> --out results/"""
import argparse, json, subprocess, sys, time, statistics
from pathlib import Path
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument('--sw', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--python', default=sys.executable); ap.add_argument('--reps', type=int, default=3); ap.add_argument('--scenes', default=''); ap.add_argument('--skip-render', action='store_true'); ap.add_argument('--tag', default='play_checks'); a = ap.parse_args()
SW = str(Path(a.sw).resolve()); OUT = Path(a.out).resolve(); OUT.mkdir(parents=True, exist_ok=True)
LIB = Path('/workspace/build_support/engine/tests/lib'); HERE = Path(__file__).resolve().parent
TMP = OUT / '_tmp'; TMP.mkdir(exist_ok=True)
SR = 48000
sys.path.insert(0, str(LIB))
BASE = {"decay_lock": True, "decay_s": 1.8, "humidity": 0.5, "early_wet": 1.0}
SCENES = {
  'lock18': dict(BASE),
  'unl': {"decay_lock": False, "fdn_g": 0.8, "humidity": 0.5, "early_wet": 1.0},
  'two': dict(BASE, two_sources=True),                       # B at server-default position: 49 colour entries
  'two_apart': dict(BASE, two_sources=True, sx_b=1.5, sz_b=5.5),  # B moved: 90 colour entries > MAX_IRS 64
  'u87_hpf': dict(BASE, mic_preset_l='NeumannU87AiCardioid', mic_preset_c='NeumannU87AiCardioid', mic_preset_r='NeumannU87AiCardioid',
                  mic_hpf_engaged=True, mic_hpf_sides=True, mic_hpf_centre=True),
}
def dump(scene, impl):
    body = dict(SCENES[scene], colour_impl=impl); out = TMP / f'{scene}_{impl}.json'
    r = subprocess.run([a.python, str(LIB / 'dump_params.py'), SW, json.dumps(body), str(out), str(SR)], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr[-800:])
    return out, json.loads(r.stdout.strip().splitlines()[-1])
def play(pj, over, mode, *args):
    r = subprocess.run(['node', str(LIB / 'wasm_run.js'), SW, str(pj), json.dumps(over), mode, *map(str, args)], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr[-800:])
    return r.stdout
def ir(pj, over, secs, tag):
    f = TMP / f'{tag}.f32'; play(pj, over, 'ir', secs, f)
    return np.fromfile(f, np.float32).reshape(-1, 2).astype(np.float64)
def null_db(x, ref):
    return float(10 * np.log10(np.sum((x - ref) ** 2) / max(np.sum(ref ** 2), 1e-30)))
def oct_diff(x, y):
    X = np.abs(np.fft.rfft(x, axis=0)) ** 2; Y = np.abs(np.fft.rfft(y, axis=0)) ** 2; f = np.fft.rfftfreq(len(x), 1 / SR)
    out = {}
    for fc in (63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000):
        m = (f >= fc / 2 ** .5) & (f < fc * 2 ** .5)
        out[fc] = float(10 * np.log10(X[m].sum() / max(Y[m].sum(), 1e-30)))
    return out
res = {'tree': SW}
# 1. Play null SOS vs FIR (+ colour effect size)
play_null = {}
for sc in [x for x in SCENES if not a.scenes or x in a.scenes.split(',')]:
    ps, info_s = dump(sc, 'sos'); pf, info_f = dump(sc, 'fir')
    xs = ir(ps, {}, 1.5, f'{sc}_sos'); xf = ir(pf, {}, 1.5, f'{sc}_fir'); x0 = ir(ps, {'colour_on': False}, 1.5, f'{sc}_off')
    od = oct_diff(xs.sum(1), xf.sum(1))
    play_null[sc] = {'null_sos_vs_fir_db': [null_db(xs[:, c], xf[:, c]) for c in (0, 1)],
                     'colour_effect_db': [null_db(x0[:, c], xf[:, c]) for c in (0, 1)],
                     'octave_diff_db_63_16k': od, 'max_abs_octave_diff_db': max(abs(v) for k, v in od.items() if k <= 16000),
                     'finite': bool(np.all(np.isfinite(xs))), 'peak_sos': float(np.max(np.abs(xs))),
                     'sample0_db_re_direct': float(20*np.log10(abs(xs[0].mean()) / max(np.max(np.abs(xs[15:7200].mean(1))), 1e-30) + 1e-30)),
                     'n_irs_sos': info_s['n_irs'], 'n_irs_fir': info_f['n_irs'], 'colour_sr': info_s['colour_sr']}
    print(sc, play_null[sc], flush=True)
res['play_null'] = play_null
# 2. CPU per block (node bench, 3 s noise + 1 s silence), median of reps
bench = {}
for sc in [x for x in ('lock18', 'two', 'two_apart') if not a.scenes or x in a.scenes.split(',')]:
    for impl, over in (('sos', {}), ('fir', {}), ('off', {'colour_on': False})):
        pj = TMP / f'{sc}_{"sos" if impl != "fir" else "fir"}.json'
        pl, si = [], []
        for _ in range(a.reps):
            d = json.loads(play(pj, over, 'bench', 3, 4)); pl.append(d['play_mean_ms']); si.append(d['silence_late_mean_ms'])
        bench[f'{sc}_{impl}'] = {'play_ms': statistics.median(pl), 'silence_ms': statistics.median(si), 'runs': pl}
        print(sc, impl, bench[f'{sc}_{impl}'], flush=True)
res['bench_ms_per_block'] = bench
if a.skip_render:
    (OUT / f'{a.tag}.json').write_text(json.dumps(res, indent=1, default=float)); raise SystemExit(0)
# 3. Render: cost and SOS-vs-FIR null (0.5 s IR, default lock18 scene)
rend = {}
for impl in ('sos', 'fir', 'bypass'):
    body = dict(SCENES['lock18'], colour_impl=impl if impl != 'bypass' else 'sos')
    if impl == 'bypass': body['colour_mode'] = 'BYPASS'
    f = TMP / f'render_{impl}.f32'; t0 = time.time()
    r = subprocess.run([a.python, str(HERE / 'render_ir_impl.py'), SW, json.dumps(body), str(f), '1500', str(SR)], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr[-800:])
    rend[impl] = {'wall_s': round(time.time() - t0, 1), 'info': json.loads(r.stdout.strip().splitlines()[-1])}
    rend[impl]['ir'] = np.fromfile(f, np.float32).reshape(-1, 2).astype(np.float64)
res['render'] = {k: {'wall_s': v['wall_s']} for k, v in rend.items()}
res['render']['null_sos_vs_fir_db'] = [null_db(rend['sos']['ir'][:, c], rend['fir']['ir'][:, c]) for c in (0, 1)]
res['render']['colour_effect_db'] = [null_db(rend['bypass']['ir'][:, c], rend['fir']['ir'][:, c]) for c in (0, 1)]
print('render', res['render'], flush=True)
# 4. Direct-only colour parity Play vs Render (same SOS records: C run_sos vs Python apply_sos)
dp = {}
for sc in ('lock18', 'u87_hpf'):
    body = dict(SCENES[sc], colour_impl='sos', early_wet=0.0, fdn_wet=0.0, direct_wet=1.0)
    pj = TMP / f'dir_{sc}.json'
    subprocess.run([a.python, str(LIB / 'dump_params.py'), SW, json.dumps(body), str(pj), str(SR)], check=True, capture_output=True)
    xp = ir(pj, {}, 0.3, f'dir_{sc}_play'); xp0 = ir(pj, {'colour_on': False}, 0.3, f'dir_{sc}_play_off')
    f = TMP / f'dir_{sc}_render.f32'
    subprocess.run([a.python, str(HERE / 'render_ir_impl.py'), SW, json.dumps(body), str(f), '300', str(SR)], check=True, capture_output=True)
    xr = np.fromfile(f, np.float32).reshape(-1, 2).astype(np.float64)
    body0 = dict(body, colour_mode='BYPASS'); f0 = TMP / f'dir_{sc}_render_off.f32'
    subprocess.run([a.python, str(HERE / 'render_ir_impl.py'), SW, json.dumps(body0), str(f0), '300', str(SR)], check=True, capture_output=True)
    xr0 = np.fromfile(f0, np.float32).reshape(-1, 2).astype(np.float64)
    n = min(len(xp), len(xr), 8192)
    # colour transfer = coloured / uncoloured, per path; compare Play vs Render transfer (removes level/fold/geometry differences)
    def tf(x, x0):
        X = np.fft.rfft(x[:n], axis=0); X0 = np.fft.rfft(x0[:n], axis=0)
        return 20 * np.log10(np.maximum(np.abs(X), 1e-12) / np.maximum(np.abs(X0), 1e-12))
    ff = np.fft.rfftfreq(n, 1 / SR); m = (ff >= 40) & (ff <= 16000)
    tp, tr = tf(xp, xp0), tf(xr, xr0)
    dp[sc] = {'max_abs_colour_tf_diff_db_40_16k': [float(np.max(np.abs(tp[m, c] - tr[m, c]))) for c in (0, 1)],
              'play_direct_peak_idx': [int(np.argmax(np.abs(xp[:, c]))) for c in (0, 1)],
              'render_direct_peak_idx': [int(np.argmax(np.abs(xr[:, c]))) for c in (0, 1)],
              'colour_tf_at_50Hz_play_render_db': [float(np.interp(50, ff, tp[:, 0])), float(np.interp(50, ff, tr[:, 0]))]}
    print('direct', sc, dp[sc], flush=True)
res['direct_colour_parity'] = dp
(OUT / f'{a.tag}.json').write_text(json.dumps(res, indent=1, default=float))
