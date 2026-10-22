"""Shared-tail P5 fix research: harness glue. Box only; the PC software\\ is read via snapshot_2026-10-02_1840."""
import sys, os, json, types, numpy as np
B = '/workspace/build_support_2'
P = B + '/research_shared_fdn/p5_fix'
T = P + '/tpc'
sys.path[:0] = [T + '/harness', T + '/harness/lib', T + '/tests']
import run_all as RA
import test_shared_tail as TS
import test_s4b_tail_solo_runaway as TB
SW = B + '/snapshot_2026-10-02_1840/software'
PY = '/workspace/scratch_er_dropout/venv/bin/python'
SR = 48000
def ctx():
    a = types.SimpleNamespace(sw=SW, python=PY, node='node', golden=T + '/harness/golden', regen_golden=False, quick=False,
                              perf_scale=1.0, workdir=P + '/data/tmp')
    os.makedirs(a.workdir, exist_ok=True)
    return RA.Ctx(a)
BASE, BIG, TAIL, OCT = TS.BASE, TS.BIG, TS.TAIL, TS.OCT
P5_SCENES = {
    "default": (dict(BASE, **TAIL), 0.08, 1.0, 3.0),
    "big": (dict(BASE, **BIG, **TAIL), 0.25, 2.5, 7.0),
    "small": (dict(BASE, **TAIL, W=6.0, H=3.0, L=8.0, sx=3.4, sz=5.6, mcx=2.8, mcz=2.4, decay_s=0.8), 0.04, 0.5, 2.0),
    "mid": (dict(BASE, **TAIL, W=15.0, H=8.0, L=22.0, sx=6.0, sz=15.0, mcx=8.5, mcz=6.0, decay_s=2.2), 0.1, 1.2, 4.0),
    "ortf_wide": (dict(BASE, **TAIL, toe_half_deg=45, space=0.30), 0.08, 1.0, 3.0),
}
# held-out scenes (never used to pick a variant)
HOLD = {
    "default_2src": (dict(BASE, **TAIL, two_sources=True, source_balance=0.0), 0.08, 1.0, 3.0),
    "hall20_off": (dict(BASE, **TAIL, W=20.0, H=10.0, L=30.0, sx=7.0, sz=20.0, mcx=11.0, mcz=8.0, decay_s=2.5), 0.12, 1.5, 4.0),
    "ortf_narrow": (dict(BASE, **TAIL, toe_half_deg=55, space=0.10), 0.08, 1.0, 3.0),
    "big_off": (dict(dict(BASE, **BIG, **TAIL), sx=15.0, mcx=35.0), 0.25, 2.5, 7.0),
}
def p5(c, wasm, scenes=P5_SCENES, over_on=None, off_wasm=None):
    rows = {}
    for name, (body, t0, t1, secs) in scenes.items():
        off = c.play_ir(body, {"shared_tail": False}, secs, wasm=off_wasm or wasm)
        on = c.play_ir(body, dict({"shared_tail": True}, **(over_on or {})), secs, wasm=wasm)
        c0 = TS._coh(off[:, 0], off[:, 1], t0, t1); c1 = TS._coh(on[:, 0], on[:, 1], t0, t1)
        e = [c1[f] - c0[f] for f in OCT]
        a, b = int(t0 * SR), int(t1 * SR)
        lv = {}
        for ch, lab in ((0, 'L'), (1, 'R')):
            d_lvl = TS._rms_db(on[a:b, ch]) - TS._rms_db(off[a:b, ch])
            sb, sa = TS._third(on[:, ch], a, b), TS._third(off[:, ch], a, b)
            raw = float(np.max(np.abs([sb[f] - sa[f] for f in TS.THIRDS])))
            lv[lab] = (round(float(d_lvl), 2), round(raw, 2))
        rows[name] = dict(rms=round(float(np.sqrt(np.mean(np.square(e)))), 4), max=round(float(np.max(np.abs(e))), 4),
                          off=[round(c0[f], 3) for f in OCT], on=[round(c1[f], 3) for f in OCT], dev=[round(x, 3) for x in e],
                          p6=lv, p6_ok=all(abs(v[0]) <= 1.0 and v[1] <= 3.5 for v in lv.values()))
        rows[name]['p5_ok'] = rows[name]['rms'] <= 0.09 and rows[name]['max'] <= 0.15
    return rows
def p4(c, wasm, short=False):
    scenes = {"def_1": (dict(BASE, **TAIL), 1.8, 8.0), "def_2": (dict(BASE, **TAIL, two_sources=True, source_balance=0.0), 1.8, 8.0),
              "big_1": (dict(BASE, **BIG, **TAIL), 4.0, 12.0), "big_2": (dict(BASE, **BIG, **TAIL, two_sources=True, source_balance=0.0), 4.0, 12.0)}
    worst_on, worst_rel, fails = 0.0, -9, []
    for name, (body, dial, secs) in scenes.items():
        off = c.play_ir(body, {"shared_tail": False}, secs, wasm=wasm); on = c.play_ir(body, {"shared_tail": True}, secs, wasm=wasm)
        for fc in OCT:
            for ch in (0, 1):
                a = TS._t30(off[:, ch], fc); b = TS._t30(on[:, ch], fc)
                ea, eb = abs(a - dial) / dial, abs(b - dial) / dial
                worst_on = max(worst_on, eb); worst_rel = max(worst_rel, eb - ea)
                if not (np.isfinite(b) and eb <= 0.10 and eb <= ea + 0.03 + 1e-9): fails.append(f'{name} {ch} {fc} {b:.2f}')
    return dict(worst_err_on=round(worst_on, 4), worst_minus_off=round(worst_rel, 4), fails=fails, ok=not fails)
def p7(c, wasm):
    A = c.play_ir(dict(BASE, **TAIL, two_sources=True, source_balance=-1.0, shared_tail=True), {}, 3.0, wasm=wasm)
    Bv = c.play_ir(dict(BASE, **TAIL, two_sources=True, source_balance=1.0, shared_tail=True), {}, 3.0, wasm=wasm)
    n = min(len(A), len(Bv), SR); num = float(np.max(np.abs(Bv[:n, 0] - A[:n, 1]))); den = float(np.max(np.abs(A[:n]))) + 1e-30
    v = 20 * np.log10(num / den + 1e-30); return dict(null_db=round(float(v), 1), ok=v <= -120)
def p9(c, wasm):
    rows = {}; ok = True
    for name, body in {"default": dict(BASE, **TAIL, decay_s=8.0), "big": dict(dict(BASE, **BIG, **TAIL), decay_s=8.0)}.items():
        y = c.play_ir(body, {"shared_tail": True}, 30.0, wasm=wasm)
        n = 2 * SR; win = [TS._rms_db(y[i:i + n]) for i in range(0, len(y) - n + 1, n)]
        tail = win[1:]; rise = max(tail[i + 1] - tail[i] for i in range(len(tail) - 1)); drop = win[2] - win[-1]
        fin = bool(np.all(np.isfinite(y))); o = fin and rise <= 1.0 and drop > 3.0; ok &= o
        rows[name] = dict(rise=round(rise, 2), drop=round(drop, 1), end=round(win[-1], 1), ok=o)
    rows['ok'] = ok; return rows
def comb(c, wasm):
    """S4b comb metrics on the shared tail (default room DEFAULT_TAIL scene from the S4b test), on and off."""
    out = {}
    for tag, fl in (('on', True), ('off', False)):
        X = c.play_ir(TB.DEFAULT_TAIL, {"shared_tail": fl}, 1.5, wasm=wasm)
        out[tag] = dict(comb_db=[round(v, 2) for v in TB._comb_db(X, SR)], ac1936=[round(v, 3) for v in TB._acmax(X, SR, at_ms=19.36)],
                        acmax=[round(v, 3) for v in TB._acmax(X, SR)])
    o = out['on']; out['ok_play_gate'] = max(o['ac1936']) <= 0.20 and max(o['acmax']) <= 0.30
    return out
def bench(c, wasms, rounds=6):
    p = c.params(dict(BASE, two_sources=True, source_balance=0.0)); res = {k: [] for k in wasms}
    keys = list(wasms)
    for r in range(rounds):
        for k in (keys if r % 2 == 0 else keys[::-1]):
            res[k].append(json.loads(c.play(p, {"shared_tail": True}, "bench", 2, 2, wasm=wasms[k]))["play_mean_ms"])
    off = []
    for r in range(rounds):
        off.append(json.loads(c.play(p, {"shared_tail": False}, "bench", 2, 2, wasm=wasms[keys[0]]))["play_mean_ms"])
    return dict(on_min={k: round(min(v), 3) for k, v in res.items()}, off_min=round(min(off), 3), runs=res)
