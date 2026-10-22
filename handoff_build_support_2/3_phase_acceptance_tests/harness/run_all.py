#!/usr/bin/env python3
"""2011 Room Reverb — engine regression / acceptance pack.

Run after any engine change:
    python run_all.py --sw "<path to software>"            # full (~6-10 min on the box)
    python run_all.py --sw "<path>" --quick                # skips the slow Render tests
    python run_all.py --sw "<path>" --only t60,parity      # substring filter on test ids
    python run_all.py --sw "<path>" --regen-golden         # rewrite goldens from this tree (see README)

Needs: a Python that can import software/app_server.py (numpy + fastapi; the app's .venv works),
node (for the Play/WASM tests), optionally gcc or zig (source-vs-wasm check). mic_fitter/ must sit
next to software/ (the mic colour code loads it). Nothing in software/ is written.
Status: PASS / FAIL / SKIP (tool missing) / PENDING (feature not built yet) / XFAIL (known gap, reported, does not fail the run).
Exit code 1 if any FAIL.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
LIB = HERE / 'lib'
sys.path.insert(0, str(LIB))
from analyze import t60_bands, late_t60, band, rms_db  # noqa: E402
import parity as PAR  # noqa: E402
import pack as PK  # noqa: E402

SR = 48000
BUDGET_MS = 128 / 48.0

SCENES = {
    # page default: decay lock armed at 1.8 s (app.js:85), humidity on so air filters run
    'std_lock18': {"decay_lock": True, "decay_s": 1.8, "humidity": 0.5, "early_wet": 1.0},
    # Feedback slider in charge (decay lock off): must be unaffected by decay-lock work
    'std_unlocked': {"decay_lock": False, "fdn_g": 0.8, "humidity": 0.5, "early_wet": 1.0},
    'small_lock08': {"decay_lock": True, "decay_s": 0.8, "humidity": 0.5, "W": 4, "H": 2.5, "L": 5, "sx": 2, "sz": 3, "mcx": 2, "mcz": 1},
    'hall_lock40': {"decay_lock": True, "decay_s": 4.0, "humidity": 0.5, "W": 20, "H": 10, "L": 30, "sx": 10, "sz": 18, "mcx": 10, "mcz": 6},
}

# ---------------------------------------------------------------- infrastructure
class Ctx:
    def __init__(self, a):
        self.sw = Path(a.sw).resolve()
        self.py = a.python or sys.executable
        self.node = shutil.which(a.node) if a.node else None
        self.golden = Path(a.golden).resolve()
        self.regen = a.regen_golden
        self.quick = a.quick
        self.perf_scale = a.perf_scale
        self.work = Path(tempfile.mkdtemp(prefix='rr_tests_', dir=a.workdir))
        self.cache = {}
        self._app_ok = None

    def app_ok(self):
        if self._app_ok is None:
            r = subprocess.run([self.py, '-c', 'import sys,os;sys.path[:0]=[sys.argv[1],os.path.join(sys.argv[1],"engine")];os.chdir(sys.argv[1]);import app_server', str(self.sw)],
                               capture_output=True, text=True)
            self._app_ok = (r.returncode == 0, (r.stderr or '')[-400:])
        return self._app_ok

    def params(self, scene, extra=None):
        body = dict(SCENES[scene] if isinstance(scene, str) else scene)
        body.update(extra or {})
        key = 'P' + hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()[:12]
        if key in self.cache: return self.cache[key]
        out = self.work / f'{key}.json'
        r = subprocess.run([self.py, str(LIB / 'dump_params.py'), str(self.sw), json.dumps(body), str(out), str(SR)], capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError('dump_params failed: ' + r.stderr[-600:])
        self.cache[key] = out
        return out

    def play(self, pjson, over, mode, *args, wasm=None):
        if not self.node: raise SkipTest('node not found')
        env = dict(os.environ)
        if wasm: env['WASM'] = str(wasm)
        r = subprocess.run([self.node, str(LIB / 'wasm_run.js'), str(self.sw), str(pjson), json.dumps(over), mode, *map(str, args)], capture_output=True, text=True, env=env)
        if r.returncode != 0: raise RuntimeError('wasm_run failed: ' + r.stderr[-600:])
        return r.stdout

    def play_ir(self, scene, over, secs, extra=None, wasm=None):
        p = self.params(scene, extra)
        out = self.work / ('ir_' + hashlib.sha1((str(p) + json.dumps(over) + str(secs) + str(wasm)).encode()).hexdigest()[:12] + '.f32')
        if not out.exists(): self.play(p, over, 'ir', secs, out, wasm=wasm)
        return np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)

    def render_ir(self, body, ms):
        ok, err = self.app_ok()
        if not ok: raise SkipTest('cannot import app_server with --python: ' + err)
        key = hashlib.sha1((json.dumps(body, sort_keys=True) + str(ms)).encode()).hexdigest()[:12]
        out = self.work / f'rir_{key}.f32'
        if not out.exists():
            r = subprocess.run([self.py, str(LIB / 'render_ir.py'), str(self.sw), json.dumps(body), str(out), str(ms), str(SR)], capture_output=True, text=True)
            if r.returncode != 0: raise RuntimeError('render_ir failed: ' + r.stderr[-600:])
        return np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)

class SkipTest(Exception): pass
class Pending(Exception): pass
class XFail(Exception): pass

def null_db(a, b):
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    return 10 * np.log10(max(float(np.sum((a - b) ** 2)), 1e-300) / max(float(np.sum(a ** 2)), 1e-300))

def golden_cmp(ctx, name, arr, tol_db=-100.0):
    g = ctx.golden / f'{name}.f32'
    if ctx.regen:
        ctx.golden.mkdir(parents=True, exist_ok=True)
        arr.astype(np.float32).tofile(g)
        return {'regenerated': str(g)}
    if not g.exists(): raise SkipTest(f'no golden {g.name}; run --regen-golden on a known-good tree')
    ref = np.fromfile(g, np.float32).reshape(-1, 2).astype(np.float64)
    nd = null_db(ref, arr)
    mx = float(np.max(np.abs(ref[:len(arr)] - arr[:len(ref)])))
    res = {'null_db': round(nd, 1), 'max_abs_diff': mx, 'tol_db': tol_db}
    if nd > tol_db: raise AssertionError(f'{name}: differs from golden (null {nd:.1f} dB > {tol_db} dB, max diff {mx:.3g}). If the change is intended, regenerate goldens and record why.')
    return res

def app_text(ctx):
    t = ''
    for f in ('app_server.py', 'render_pipeline.py', 'surface_colour.py', 'engine/early_field.py'):
        p = ctx.sw / f
        if p.exists(): t += p.read_text(encoding='utf-8', errors='replace')
    return t

def find_key(ctx, pattern):
    m = re.findall(r'["\'](' + pattern + r')["\']', app_text(ctx))
    return m[0] if m else None

# ---------------------------------------------------------------- tests
def t01_pack_matches_worklet(ctx):
    """Harness sanity: the Python packer (lib/pack.py) and the real fdn_worklet.js packRoom agree."""
    p = ctx.params('std_lock18')
    out = ctx.work / 'blob_w.f32'
    ctx.play(p, {"colour_on": False}, 'blob', out)
    w = np.fromfile(out, np.float32)
    P = json.load(open(p))
    pb, *_ = PK.pack(P, {"colour_on": False, **({"line_t60": P["line_t60"]} if P.get("line_t60") else {})})
    n = len(pb)
    d = float(np.max(np.abs(w[:n] - pb)))
    if d > 0: raise AssertionError(f'packRoom mismatch max {d}')
    return {'blob_len': n, 'max_diff': d}

def t02_wasm_matches_source(ctx):
    """static/wasm/live_stereo.wasm is built from engine/live_stereo.c (native build IR == wasm IR, bit-exact)."""
    cc = shutil.which('gcc') or shutil.which('clang')
    if not cc: raise SkipTest('no gcc/clang')
    exe = ctx.work / 'run_native'
    r = subprocess.run([cc, '-O3', f'-DLS_SRC="{ctx.sw / "engine" / "live_stereo.c"}"', str(LIB / 'run_native.c'), '-o', str(exe), '-lm'], capture_output=True, text=True)
    if r.returncode != 0: raise SkipTest('native build failed: ' + r.stderr[-300:])
    p = ctx.params('std_lock18'); P = json.load(open(p))
    over = {"colour_on": False, **({"line_t60": P["line_t60"]} if P.get("line_t60") else {})}
    blob, route, irs, lens = PK.pack(P, over)
    pre = ctx.work / 'nat'
    blob.tofile(f'{pre}.blob'); route.tofile(f'{pre}.route'); irs.tofile(f'{pre}.irs'); lens.tofile(f'{pre}.lens')
    subprocess.run([str(exe), str(pre), 'ir', '1.0', str(pre) + '.f32'], check=True)
    a = np.fromfile(str(pre) + '.f32', np.float32).reshape(-1, 2)
    b = ctx.play_ir('std_lock18', {"colour_on": False}, 1.0).astype(np.float32)
    n = min(len(a), len(b)); d = float(np.max(np.abs(a[:n] - b[:n])))
    if d > 1e-6: raise AssertionError(f'wasm output != native build of live_stereo.c (max diff {d:.3g}); rebuild the wasm')
    return {'max_diff': d}

def t03_golden_play_features_off(ctx):
    """Play IR with new features off equals the golden baseline (null <= -100 dB)."""
    res = {}
    for sc in ('std_unlocked', 'std_lock18'):
        for tag, over in (('byp', {"colour_on": False}), ('col', {})):
            res[f'{sc}_{tag}'] = golden_cmp(ctx, f'play_{sc}_{tag}', ctx.play_ir(sc, over, 1.5))
    return res

def t04_golden_render_features_off(ctx):
    """Render IR (BYPASS colour, 0.5 s) equals the golden baseline (null <= -100 dB)."""
    body = dict(SCENES['std_unlocked']); body.update({"colour_mode": "BYPASS", "direct_wet": 1, "fdn_wet": 1})
    return golden_cmp(ctx, 'render_std_unlocked_byp', ctx.render_ir(body, 500))

def t05_omni_source_identity(ctx):
    """Source radiation OMNI must reproduce today's golden (Play + Render)."""
    key = find_key(ctx, r'source_(?:pattern|radiation|directivity)[a-z_]*')
    if not key: raise Pending('source radiation not in this tree (no source_pattern/radiation key)')
    ext = {key: 'omni'}
    res = {'key': key}
    for tag, over in (('byp', {"colour_on": False}),):
        res['play'] = golden_cmp(ctx, f'play_std_unlocked_{tag}', ctx.play_ir('std_unlocked', over, 1.5, extra=ext))
    return res

def t06_scattering_zero_identity(ctx):
    """Per-reflection scattering amount 0 must reproduce today's golden (Play)."""
    key = find_key(ctx, r'scatter[a-z_]*')
    if not key: raise Pending('scattering (Track C) not in this tree')
    return golden_cmp(ctx, 'play_std_unlocked_byp', ctx.play_ir('std_unlocked', {"colour_on": False}, 1.5, extra={key: 0.0}))

def t07_tail_yaw_invariance(ctx):
    """Tail energy (80 ms-1 s) invariant (<=0.5 dB) under source yaw 0/90/180 (source radiation)."""
    key = find_key(ctx, r'(?:source|src)_yaw[a-z_]*')
    if not key: raise Pending('source yaw not in this tree')
    es = []
    for yaw in (0, 90, 180):
        x = ctx.play_ir('std_unlocked', {"colour_on": False, "early_wet": 0, "direct_wet": 0}, 1.0, extra={key: yaw})
        es.append(rms_db(x[int(0.08 * SR):, 0]))
    spread = max(es) - min(es)
    if spread > 0.5: raise AssertionError(f'tail energy spread {spread:.2f} dB over yaw')
    return {'key': key, 'tail_db': es, 'spread_db': spread}

def t08_fdn_stability(ctx):
    """No NaN/Inf/growth across the full Dffs range and max decay (8 s) / max loop gain; 15 s noise then 15 s silence."""
    base = json.load(open(ctx.params('std_lock18', {"decay_s": 8.0})))
    res = {}
    for name, dff in (('dffs0', 0.0), ('dffs+0.98', 0.98), ('dffs-0.98', -0.98), ('dffs_as_is', None)):
        P = json.loads(json.dumps(base))
        P['g'] = max(P['g'], 0.99 / 32 ** 0.5) if not P.get('line_t60') else P['g']
        if dff is not None:
            for ch in 'lcr': P['buses'][ch]['dffs'] = [dff] * 32
        pj = ctx.work / f'stab_{name}.json'; json.dump(P, open(pj, 'w'))
        out = ctx.work / f'stab_{name}.f32'
        ctx.play(pj, {"colour_on": False}, 'noise', 15, 30, out)
        x = np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)
        if not np.all(np.isfinite(x)): raise AssertionError(f'{name}: NaN/Inf')
        e1 = rms_db(x[int(15.5 * SR):int(20 * SR)]); e2 = rms_db(x[int(25 * SR):int(30 * SR)])
        res[name] = {'peak': float(np.max(np.abs(x))), 'silence_5s_db': round(e1, 1), 'silence_last5s_db': round(e2, 1)}
        if e2 > e1 - 3.0 and e2 > -200: raise AssertionError(f'{name}: tail not decaying ({e1:.1f} -> {e2:.1f} dB)')
    return res

def _bench_row(r):
    """Mean stays in the record. The gate reads the median, p90 and spike count."""
    out = {}
    for k in ('play_mean_ms', 'play_median_ms', 'play_p90_ms', 'silence_late_mean_ms', 'silence_late_median_ms'):
        if r.get(k) is not None:
            out[k] = round(float(r[k]), 3)
    if r.get('play_spikes') is not None:
        out['play_spikes'] = int(r['play_spikes'])
    return out

def t09_silence_cpu(ctx):
    """WASM cost after input stops stays near the playing cost (no denormal blow-up): late-silence median <= 1.3x play median and <= 50% budget (colour off)."""
    res = {}
    for tag, over, lim in (('byp', {"colour_on": False}, 0.5), ('col', {}, 0.75)):
        r = json.loads(ctx.play(ctx.params('std_lock18'), over, 'bench', 2, 14))
        row = _bench_row(r)
        res[tag] = row
        s, pm = r['silence_late_median_ms'], r['play_median_ms']
        cap = lim * BUDGET_MS * ctx.perf_scale
        if s > 1.3 * pm or s > cap:
            raise AssertionError(f'{tag}: silence median {s:.2f} ms/block vs play median {pm:.2f} (limit 1.3x and {cap:.2f} ms) -> denormals {row}')
    return res

def _t60_check(x, dial, tol=0.15, bands=(500, 1000, 2000, 4000, 8000)):
    t = t60_bands(x[:, 0], SR, bands=list(bands))
    bad = {b: round(t[b], 2) for b in bands if not (abs(t[b] / dial - 1) <= tol)}
    return {str(b): round(t[b], 2) for b in bands}, bad

def t10_t60_play(ctx):
    """Play FDN T30 per octave (500 Hz-8 kHz) within +-15 % of the dialled decay (decay lock)."""
    res, fails = {}, []
    for sc in ('std_lock18', 'small_lock08', 'hall_lock40'):
        dial = SCENES[sc]['decay_s']
        x = ctx.play_ir(sc, {"colour_on": False, "early_wet": 0, "direct_wet": 0}, max(4, 2.5 * dial), extra={"phys_ceiling": False})
        t, bad = _t60_check(x, dial)
        res[sc] = {'dial': dial, 't30': t}
        if bad: fails.append(f'{sc}: {bad} vs {dial}s')
    if fails: raise AssertionError('; '.join(fails) + f' | {res}')
    return res

def t11_hf_residue_play(ctx):
    """No slow HF residue: 9-11 kHz late decay (0.6-0.8 x dial after onset) T60 <= 1.25 x dial."""
    dial = 1.8
    x = ctx.play_ir('std_lock18', {"colour_on": False, "early_wet": 0, "direct_wet": 0}, 5)
    lt = {fc: round(late_t60(x[:, 0], SR, fc, 0.6 * dial, 0.8 * dial), 2) for fc in (9000, 11000)}
    if any(v > 1.25 * dial for v in lt.values()): raise AssertionError(f'late HF T60 {lt} vs dial {dial}')
    return lt

def t12_t60_render(ctx):
    """[slow] Render FDN T30 per octave within +-15 % of the dialled decay (std room, 1.8 s)."""
    if ctx.quick: raise SkipTest('--quick')
    body = dict(SCENES['std_lock18']); body.update({"early_wet": 0, "direct_wet": 0, "fdn_wet": 1, "colour_mode": "BYPASS", "phys_ceiling": False})
    x = ctx.render_ir(body, 4500)
    t, bad = _t60_check(x, 1.8)
    if bad: raise AssertionError(f'Render T30 {t} vs 1.8 s')
    return t

def t13_parity_play_render(ctx):
    """[slow] Play vs Render, same scene, colour off & on: tail T30 +-10 %/band, tail octave balance +-1.5 dB,
    tail level +-1 dB, stereo tail corr +-0.1, direct level +-0.5 dB. Early field: XFAIL until Play gets the per-hit cascade."""
    if ctx.quick: raise SkipTest('--quick')
    fails, res = [], {}
    for tag, over, cm in (('byp', {"colour_on": False}, 'BYPASS'), ('col', {}, 'MEASURED_SHELF')):
        body = dict(SCENES['std_lock18']); body.update({"direct_wet": 1, "fdn_wet": 1, "colour_mode": cm})
        R = ctx.render_ir(body, 3000); P = ctx.play_ir('std_lock18', over, 3.0)
        m = PAR.full_metrics(P, R)
        res[tag] = {'t30_play': m['t30_play'], 't30_render': m['t30_render'], 'tail_level_db': round(m['tail_level_diff_db_80ms_1s'], 2),
                    'balance': m['tail_octave_balance_diff_db_(norm)'], 'corr': [round(m['stereo_tail_80ms_1s']['corr_play'], 2), round(m['stereo_tail_80ms_1s']['corr_render'], 2)]}
        for b in ('500', '1000', '2000', '4000', '8000'):
            if abs(m['t30_play'][b] / m['t30_render'][b] - 1) > 0.10: fails.append(f'{tag} T30 {b}: {m["t30_play"][b]} vs {m["t30_render"][b]}')
        for b, v in m['tail_octave_balance_diff_db_(norm)'].items():
            if b != '16000' and abs(v) > 1.5: fails.append(f'{tag} balance {b} Hz {v} dB')
        if abs(m['tail_level_diff_db_80ms_1s']) > 1.0: fails.append(f'{tag} tail level {m["tail_level_diff_db_80ms_1s"]:.2f} dB')
        if abs(m['stereo_tail_80ms_1s']['corr_play'] - m['stereo_tail_80ms_1s']['corr_render']) > 0.1: fails.append(f'{tag} tail L/R corr {res[tag]["corr"]}')
    bd = dict(SCENES['std_lock18']); bd.update({"direct_wet": 1, "fdn_wet": 0, "early_wet": 0, "colour_mode": "BYPASS"})
    dm = PAR.direct_metrics(ctx.play_ir('std_lock18', {"colour_on": False, "fdn_wet": 0, "early_wet": 0}, 0.3), ctx.render_ir(bd, 300))
    res['direct'] = {k: {'dt': v['dt_samples'], 'dlevel_db': round(v['level_diff_db'], 2)} for k, v in dm.items()}
    for k, v in dm.items():
        if v['dt_samples'] != 0 or abs(v['level_diff_db']) > 0.5: fails.append(f'direct {k}: dt {v["dt_samples"]} smp, {v["level_diff_db"]:.2f} dB')
    be = dict(SCENES['std_lock18']); be.update({"direct_wet": 0, "fdn_wet": 0, "early_wet": 1, "colour_mode": "BYPASS"})
    em = PAR.early_metrics(ctx.play_ir('std_lock18', {"colour_on": False, "fdn_wet": 0, "direct_wet": 0}, 0.3), ctx.render_ir(be, 300))
    res['early'] = {k: {'energy_db': round(v['energy_diff_db_0_80ms'], 2), 'max_dt_ms': round(v['max_abs_dt_ms'], 2), 'med_dlevel_db': round(v['median_abs_dlevel_db'], 2)} for k, v in em.items()}
    if fails: raise AssertionError('; '.join(fails) + f' | {res}')
    early_bad = any(abs(v['energy_diff_db_0_80ms']) > 1.5 or v['median_abs_dlevel_db'] > 2.0 for v in em.values())
    if early_bad: raise XFail(f'tail/direct parity OK; early field differs (known gap: no per-hit surface cascade in Play) {res["early"]}')
    return res

# Pre-F2 reference (snapshot 28 Sep 20:40, measured on the box with T14_PIN): headroom decision 6.
# Mix RMS stays -16.37. FDN RMS was -27.18 then. On the pre-SRCDIST tree it was
# already -24.78 (delta +2.40). D-SRC-DIST-LEVEL moved makeup +0.23 dB on this
# posted source (sx 3.0, sy 1.5). Injects and delays were unchanged. FDN RMS
# is now -24.55 on the dial path. T14_PIN keeps that path (explicit phys_ceiling false).
# PHYSDEFAULT 2026-10-19 physics row: key absent, FDN-only RMS -26.71 (falling HF tail).
T14_REF = {'mix_peak': 0.512, 'mix_rms_db': -16.37, 'fdn_rms_db': -24.55}
T14_PIN = {"sx": 3.0, "sy": 1.5, "diffusion_master": -0.25, "air_lp": 0.25, "phys_ceiling": False}  # old source + air (K2/K3 do not enter), locked diffusion (trim operating point)
T14_PHYS_FDN_RMS = -26.71

def t14_level_sanity(ctx):
    """Nominal scene, colour on, uniform noise +-0.3 (-15.2 dBFS RMS, hot): Play peak < 0.95 (limiter idle), finite.
    Headroom decision 6, dial path: T14_PIN sets phys_ceiling false. The FDN bus (FDN only, source/air
    pinned to the old defaults, diffusion at the locked -0.25) must sit within +-0.5 dB of -24.55 dB.
    Whole-mix delta is reported (direct/early moved with F3's Play/Render parity fix, not trimmed).
    PHYSDEFAULT 2026-10-19 physics row: the same pin with the key absent. FDN-only RMS within +-0.5 dB
    of -26.71 dB. Whole-mix delta is reported. Play peak stays at or under 0.95."""
    p = ctx.params('std_lock18')
    out = ctx.work / 'lvl.f32'
    ctx.play(p, {}, 'noise', 3, 4, out)  # wasm_run noise is uniform +-0.3 (-15.2 dBFS rms)
    x = np.fromfile(out, np.float32).reshape(-1, 2)
    pk = float(np.max(np.abs(x)))
    res = {'play_peak': round(pk, 3), 'play_rms_db': round(rms_db(x[:3 * SR]), 1)}
    if not np.all(np.isfinite(x)) or pk >= 0.95: raise AssertionError(f'Play peak {pk:.3f} (soft limit starts at 0.95) {res}')
    for tag, ex in (('fdn', {"fdn_wet": 1.0, "direct_wet": 0.0, "early_wet": 0.0}), ('mix', {})):
        body = dict(SCENES['std_lock18'], **T14_PIN, **ex)
        ctx.play(ctx.params(body), {}, 'noise', 3, 4, out)
        y = np.fromfile(out, np.float32).reshape(-1, 2)
        res[f'pinned_{tag}_peak'] = round(float(np.max(np.abs(y))), 3)
        res[f'pinned_{tag}_rms_db'] = round(rms_db(y[:3 * SR]), 2)
        res[f'pinned_{tag}_delta_db'] = round(res[f'pinned_{tag}_rms_db'] - T14_REF[f'{tag}_rms_db'], 2)
    if abs(res['pinned_fdn_delta_db']) > 0.5:
        raise AssertionError(f"FDN bus {res['pinned_fdn_delta_db']:+.2f} dB vs pre-F2 (limit +-0.5 dB, decision 6) {res}")
    pin = {k: v for k, v in T14_PIN.items() if k != 'phys_ceiling'}
    phys = {'label': 'PHYSDEFAULT 2026-10-19 physics row', 'play_peak': res['play_peak']}
    for tag, ex in (('fdn', {"fdn_wet": 1.0, "direct_wet": 0.0, "early_wet": 0.0}), ('mix', {})):
        body = dict(SCENES['std_lock18'], **pin, **ex)
        if 'phys_ceiling' in body:
            raise AssertionError('physics row must leave phys_ceiling absent ' + str(sorted(body)))
        ctx.play(ctx.params(body), {}, 'noise', 3, 4, out)
        y = np.fromfile(out, np.float32).reshape(-1, 2)
        phys[f'{tag}_peak'] = round(float(np.max(np.abs(y))), 3)
        phys[f'{tag}_rms_db'] = round(rms_db(y[:3 * SR]), 2)
    phys['mix_delta_db'] = round(phys['mix_rms_db'] - T14_REF['mix_rms_db'], 2)
    phys['fdn_vs_pin_db'] = round(phys['fdn_rms_db'] - T14_PHYS_FDN_RMS, 2)
    res['physics'] = phys
    if phys['play_peak'] > 0.95:
        raise AssertionError(f"PHYSDEFAULT 2026-10-19 physics row peak {phys['play_peak']:.3f} over 0.95 {phys}")
    if abs(phys['fdn_vs_pin_db']) > 0.5:
        raise AssertionError(f"PHYSDEFAULT 2026-10-19 physics row FDN {phys['fdn_rms_db']:.2f} dB vs pin {T14_PHYS_FDN_RMS} (limit +-0.5 dB) {phys}")
    return res

def t15_perf_active(ctx):
    """Active cost on this machine: 1 source + colour median <= 60 % budget, 2 sources + colour median <= 85 % (x --perf-scale)."""
    res = {}
    for tag, over, lim in (('1src_col', {}, 0.60), ('2src_col', {"two_sources": True}, 0.85)):
        r = json.loads(ctx.play(ctx.params('std_lock18'), over, 'bench', 8, 8))
        cap = lim * BUDGET_MS * ctx.perf_scale
        row = _bench_row(r)
        row['limit_ms'] = round(cap, 3)
        res[tag] = row
        if r['play_median_ms'] > cap: raise AssertionError(f'{tag} median {r["play_median_ms"]:.2f} ms > {cap:.2f} ms {res}')
    return res

def t19_two_source_radiation_cpu(ctx):
    """Two directional sources, colour on. D-S5c-2 ceilings. BUDGET_MS is unchanged.

    Shared off: one bench, ceiling 0.90 * BUDGET_MS (2.40 ms). The 12-round
    paired A/B against the pre-S5 wasm is the acceptance measurement; this
    check is that ceiling on one bench. Shared on: one bench, ceiling
    0.80 * BUDGET_MS (2.133 ms). Silence-late stays within 1.3x the play
    median and within that run's ceiling. talking_head plus trumpet_byu,
    both SRC_RAD filters live.
    """
    key = find_key(ctx, r'source_(?:pattern|radiation|directivity)[a-z_]*')
    if not key:
        raise Pending('source radiation not in this tree')
    p = ctx.params('std_lock18', {
        key: 'talking_head',
        'source_radiation_b': 'trumpet_byu',
        'source_yaw': 35.0,
        'source_yaw_b': -25.0,
        'two_sources': True,
    })
    packed = json.load(open(p))
    src = packed.get('src_rad') or []
    if len(src) != 716 or src[0] < 0.5 or src[1] < 0.5:
        raise AssertionError(f'SRC_RAD not live for both sources (len {len(src)}, head {src[:2]})')

    def one(over, frac, tag):
        r = json.loads(ctx.play(p, over, 'bench', 4, 10))
        med, sil = r['play_median_ms'], r['silence_late_median_ms']
        limit = frac * BUDGET_MS * ctx.perf_scale
        row = _bench_row(r)
        row['limit_ms'] = round(limit, 3)
        if med > limit:
            raise AssertionError(f'{tag} median {med:.2f} ms > {limit:.2f} ms ({frac:.2f} of {BUDGET_MS:.3f} ms) {row}')
        if sil > 1.3 * med or sil > limit:
            raise AssertionError(f'{tag} silence median {sil:.2f} ms vs play median {med:.2f} (limit 1.3x and {limit:.2f} ms) {row}')
        return row

    off = one({}, 0.90, 'shared off')
    off['shared_on'] = one({"shared_tail": True}, 0.80, 'shared on')
    # SL3. One Surfaces bench each. The 12-round pair is the acceptance measurement, not this check.
    p_surf = ctx.params('std_lock18', {
        key: 'talking_head',
        'source_radiation_b': 'trumpet_byu',
        'source_yaw': 35.0,
        'source_yaw_b': -25.0,
        'two_sources': True,
        'decay_mode': 'surfaces',
    })
    packed_s = json.load(open(p_surf))
    if not packed_s.get('surf_on') or len(packed_s.get('surf_sos') or []) != 1440:
        raise AssertionError('Surfaces Play did not pack 1440 sections ' + str(packed_s.get('surf_refused')))

    def one_surf(over, frac, tag):
        r = json.loads(ctx.play(p_surf, over, 'bench', 4, 10))
        med, sil = r['play_median_ms'], r['silence_late_median_ms']
        limit = frac * BUDGET_MS * ctx.perf_scale
        row = _bench_row(r)
        row['limit_ms'] = round(limit, 3)
        if med > limit:
            raise AssertionError(f'{tag} median {med:.2f} ms > {limit:.2f} ms ({frac:.2f} of {BUDGET_MS:.3f} ms) {row}')
        if sil > 1.3 * med or sil > limit:
            raise AssertionError(f'{tag} silence median {sil:.2f} ms vs play median {med:.2f} (limit 1.3x and {limit:.2f} ms) {row}')
        return row

    off['surfaces'] = one_surf({}, 0.90, 'surfaces shared off')
    off['surfaces_shared_on'] = one_surf({"shared_tail": True}, 0.80, 'surfaces shared on')
    return off

def t16_diffusion_layers_separate(ctx):
    """Lock: Surfaces Δd jitter and Structure Dffs are separate controls (one key must not drive both)."""
    t = (ctx.sw / 'surface_colour.py').read_text(encoding='utf-8', errors='replace') + (ctx.sw / 'render_pipeline.py').read_text(encoding='utf-8', errors='replace')
    # Existing keys 'diffusion' (surface card) and 'dffs'/'tap_dff' (Structure) do NOT count: a NEW, separate surface-side key is required.
    keys = set(re.findall(r'["\']((?:surface_diffusion|dd_jitter|delta_d_jitter|surface_jitter|jitter)[a-z_]*|structure_diffusion|dffs_amount)["\']', t))
    keys -= {'dffs', 'tap_dff', 'diffusion'}
    if not keys: raise Pending('single "diffusion" card key still drives both tap_dff (Dffs) and Δd jitter; no separate key yet')
    return {'keys_found': sorted(keys), 'note': 'extend: vary one key, assert the other layer is unchanged'}

def t17_play_hadamard_n(ctx):
    """Play follows hadamard_n (8..128) like Render."""
    P = json.load(open(ctx.params('std_unlocked', {"hadamard_n": 16})))
    if int(P.get('n', 32)) != 16: raise Pending(f'Play N fixed at {P.get("n")} (render_pipeline.live_fdn_params n_had=32)')
    return {'n': P['n']}

def t18_tail_null_play_render(ctx):
    """[slow] FDN-only Play tail nulls Render (z^-1 in both, integer delays): residual <= -30 dB over 0-2 s. -60 dB is the expected null."""
    if ctx.quick: raise SkipTest('--quick')
    body = dict(SCENES['std_lock18']); body.update({"early_wet": 0, "direct_wet": 0, "fdn_wet": 1, "colour_mode": "BYPASS"})
    R = ctx.render_ir(body, 2000); P = ctx.play_ir('std_lock18', {"colour_on": False, "early_wet": 0, "direct_wet": 0}, 2.0)
    nd = [round(null_db(R[:, c], P[:, c]), 1) for c in (0, 1)]
    if max(nd) > -30: raise AssertionError(f'Play tail vs Render null {nd} dB (> -30): z^-1 in both should be one network')
    if max(nd) > -60: raise AssertionError(f'Play tail vs Render null {nd} dB (gate -30 met, z^-1 target -60 missed)')
    return {'null_db': nd}

TESTS = [t01_pack_matches_worklet, t02_wasm_matches_source, t03_golden_play_features_off, t04_golden_render_features_off,
         t05_omni_source_identity, t06_scattering_zero_identity, t07_tail_yaw_invariance, t08_fdn_stability, t09_silence_cpu,
         t10_t60_play, t11_hf_residue_play, t12_t60_render, t13_parity_play_render, t14_level_sanity, t15_perf_active,
         t16_diffusion_layers_separate, t17_play_hadamard_n, t18_tail_null_play_render,
         t19_two_source_radiation_cpu]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sw', required=True, help='path to the software/ tree to test (read-only)')
    ap.add_argument('--python', default=None, help='python that can import app_server (default: this one)')
    ap.add_argument('--node', default='node')
    ap.add_argument('--golden', default=str(HERE / 'golden'))
    ap.add_argument('--regen-golden', action='store_true')
    ap.add_argument('--reason', default='', help='stored on GOLDEN_META.json when regenerating')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--only', default='')
    ap.add_argument('--perf-scale', type=float, default=1.0, help='multiply CPU limits (slow machine > 1)')
    ap.add_argument('--workdir', default=None)
    ap.add_argument('--out', default=str(HERE / 'last_results.json'))
    a = ap.parse_args()
    ctx = Ctx(a)
    sel = [t for t in TESTS if not a.only or any(s.strip() and s.strip() in t.__name__ for s in a.only.split(','))]
    if a.regen_golden: sel = [t03_golden_play_features_off, t04_golden_render_features_off]
    results, nfail = [], 0
    for t in sel:
        t0 = time.time()
        try:
            d = t(ctx); st = 'PASS'
        except SkipTest as e: st, d = 'SKIP', str(e)
        except Pending as e: st, d = 'PENDING', str(e)
        except XFail as e: st, d = 'XFAIL', str(e)
        except AssertionError as e: st, d = 'FAIL', str(e); nfail += 1
        except Exception as e: st, d = 'ERROR', f'{type(e).__name__}: {e}'; nfail += 1
        dt = time.time() - t0
        results.append({'test': t.__name__, 'status': st, 'secs': round(dt, 1), 'detail': d, 'doc': (t.__doc__ or '').strip()})
        print(f'{st:8s} {t.__name__:34s} {dt:6.1f}s  {str(d)[:220]}', flush=True)
    meta = {'sw': str(ctx.sw), 'when': time.strftime('%Y-%m-%d %H:%M:%S'), 'node': ctx.node, 'python': ctx.py,
            'sha1': {f: hashlib.sha1((ctx.sw / f).read_bytes()).hexdigest()[:12] for f in ('engine/live_stereo.c', 'static/wasm/live_stereo.wasm', 'static/js/fdn_worklet.js', 'render_pipeline.py', 'engine/fdn.py') if (ctx.sw / f).exists()}}
    if a.reason:
        meta['reason'] = a.reason
    json.dump({'meta': meta, 'results': results}, open(a.out, 'w'), indent=1, default=str)
    if a.regen_golden:
        json.dump(meta, open(Path(a.golden) / 'GOLDEN_META.json', 'w'), indent=1)
    shutil.rmtree(ctx.work, ignore_errors=True)
    print(f'\n{sum(r["status"]=="PASS" for r in results)} pass, {nfail} fail/error, ' + ', '.join(f'{sum(r["status"]==s for r in results)} {s.lower()}' for s in ('SKIP', 'PENDING', 'XFAIL')))
    sys.exit(1 if nfail else 0)

if __name__ == '__main__':
    main()
