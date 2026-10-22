"""Shared tail (Live only, default off). Proofs P1 and P3-P10 from BUILD_BRIEF.md Part 2.

P2 (skip-empty-centre) landed in S4b. P1's binaural rows are the bit-exact check that
this build did not move it. The previous build is the S4b wasm copied before this
rebuild: roadmap/shared_tail/live_stereo_s4b.wasm (sha1 08a95563546d, goldens 16:07).
"""
from __future__ import annotations
import json
import re
from pathlib import Path
import numpy as np
import pytest

SR = 48000
OLD = Path(__file__).resolve().parents[2] / "roadmap" / "shared_tail" / "live_stereo_s4b.wasm"
PROOF = OLD.parent / "proof.json"
BASE = dict(toe_half_deg=55, space=0.17, decay_lock=True, decay_s=1.8, humidity=0.5,
            early_wet=1.0, mirror_b=True)
BIG = dict(W=57.0, H=34.2, L=97.0, sx=24.0, sz=60.0, mcx=28.5, mcz=30.0, decay_s=4.0)
TAIL = dict(fdn_wet=1.0, direct_wet=0.0, early_wet=0.0, dry_gain=0.0)
OCT = (250, 500, 1000, 2000, 4000, 8000)
THIRDS = (125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000,
          2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500)


def _note(key, val):
    d = {}
    if PROOF.exists():
        d = json.loads(PROOF.read_text(encoding="utf-8"))
    d[key] = val
    PROOF.write_text(json.dumps(d, indent=1), encoding="utf-8")
    print(key, val)


def _mx(a, b):
    n = min(len(a), len(b))
    return float(np.max(np.abs(a[:n] - b[:n])))


def _coh(L, R, t1, t2):
    from scipy import signal
    a, b = int(t1 * SR), int(t2 * SR)
    f, C = signal.coherence(L[a:b], R[a:b], fs=SR, nperseg=2048)
    out = {}
    for fc in OCT:
        m = (f >= fc / 2 ** 0.5) & (f < fc * 2 ** 0.5)
        out[fc] = float(np.sqrt(np.mean(C[m]))) if np.any(m) else float("nan")
    return out


def _t30(x, fc):
    from analyze import band, schroeder_db, t60_from_edc
    return float(t60_from_edc(schroeder_db(band(x, SR, fc)), SR))


def _third(x, a, b):
    X = np.abs(np.fft.rfft(x[a:b])) ** 2
    f = np.fft.rfftfreq(b - a, 1.0 / SR)
    out = {}
    for fc in THIRDS:
        m = (f >= fc / 2 ** (1.0 / 6.0)) & (f < fc * 2 ** (1.0 / 6.0))
        out[fc] = 10.0 * np.log10(float(np.sum(X[m])) + 1e-30)
    return out


def _rms_db(x):
    return 10.0 * np.log10(float(np.mean(np.asarray(x) ** 2)) + 1e-30)


def _pi(k):
    """Index-bit swap (b0 b4)(b1 b3). The line mirror."""
    b0, b1, b2 = k & 1, (k >> 1) & 1, (k >> 2) & 1
    b3, b4 = (k >> 3) & 1, (k >> 4) & 1
    return b4 | (b3 << 1) | (b2 << 2) | (b1 << 3) | (b0 << 4)


def _parse_csign(text, name):
    m = re.search(rf"static const double {name}\[32\]\s*=\s*\{{([^}}]*)\}}", text)
    assert m, name
    vals = [float(v) for v in re.findall(r"[-+]?\d+(?:\.\d*)?", m.group(1))]
    assert len(vals) == 32, name
    return vals


def _fwht32(a):
    a = list(a)
    length = 1
    while length < 32:
        step = length << 1
        i = 0
        while i < 32:
            for j in range(length):
                u, v = a[i + j], a[i + j + length]
                a[i + j] = u + v
                a[i + j + length] = u - v
            i += step
        length = step
    return a


@pytest.mark.phase("SHARED")
def test_sh_csign_ds_shared_loop_only():
    """CSIGN_DS is CSIGN_D with the mirror orbit {3, 24} set to +1. Shared loop only."""
    c = (Path(__file__).resolve().parents[3] / "software" / "engine" / "live_stereo.c").read_text(encoding="utf-8")
    d = _parse_csign(c, "CSIGN_DS")
    base = _parse_csign(c, "CSIGN_D")
    assert all(d[_pi(k)] == d[k] for k in range(32))
    assert d[0] == 1.0
    peak = max(abs(v) for v in _fwht32(d)) / 32.0
    assert peak < 1.0, peak
    differ = [k for k in range(32) if d[k] != base[k]]
    assert differ == [3, 24], differ
    assert "g_csignTab = CSIGN_DS;" in c and "g_csignTab = CSIGN_D;" in c
    assert "a[k] *= g_csignTab[k]" in c


@pytest.mark.phase("SHARED")
def test_sh_p1_off_bit_exact(ctx):
    """P1. shared_tail off matches the S4b wasm in the five scenes, colour on and off."""
    assert OLD.is_file(), OLD
    scenes = {
        "def_1": dict(BASE),
        "def_2": dict(BASE, two_sources=True, source_balance=0.0),
        "big_1": dict(BASE, **BIG),
        "big_2": dict(BASE, **BIG, two_sources=True, source_balance=0.0),
        "bin_2": dict(BASE, two_sources=True, source_balance=0.0, mic_setup="binaural"),
    }
    colours = ({}, {"colour_on": False})
    worst = 0.0
    rows = {}
    for name, body in scenes.items():
        for over in colours:
            tag = name + ("_on" if over.get("colour_on", True) else "_off")
            a = ctx.play_ir(body, over, 1.0, wasm=OLD)
            b = ctx.play_ir(body, over, 1.0)
            d = _mx(a, b)
            rows[tag] = d
            worst = max(worst, d)
            assert d == 0.0, f"P1 {tag} max diff {d} (stop: off changed the S4b sound)"
    changed = _mx(
        ctx.play_ir(dict(BASE), {"colour_on": False, "shared_tail": True}, 1.0),
        ctx.play_ir(dict(BASE), {"colour_on": False}, 1.0),
    )
    assert changed > 0.0, "shared tail on matched off in a stereo scene"
    _note("P1", {"max_diff": worst, "rows": rows, "stereo_on_vs_off": changed})


@pytest.mark.phase("SHARED")
def test_sh_p2_skip_centre_still_the_s4b_path(ctx):
    """P2 already landed. Binaural vs the S4b wasm is P1. This only checks the flag stays off the blob."""
    import pack as PK
    off = json.load(open(ctx.params(BASE)))
    blob = PK.pack_room(off)
    nsec = int(blob[3])
    ids = [int(blob[5 + 4 * s]) for s in range(nsec)]
    assert 6 not in ids
    on = json.load(open(ctx.params(dict(BASE, shared_tail=True))))
    assert on.get("shared_tail") is True
    ids_on = [int(PK.pack_room(on)[5 + 4 * s]) for s in range(int(PK.pack_room(on)[3]))]
    assert 6 in ids_on
    par = json.load(open(ctx.params(dict(BASE, shared_tail=True, reaktor_parity=True))))
    bina = json.load(open(ctx.params(dict(BASE, shared_tail=True, mic_setup="binaural"))))
    assert not par.get("shared_tail")
    assert not bina.get("shared_tail")
    _note("P2", {"section6_off": False, "section6_on": True, "parity_sets": False, "binaural_sets": False,
                 "note": "skip-centre CPU was measured in S4b; not re-benchmarked against the pre-S4b zip"})


@pytest.mark.slow
@pytest.mark.phase("SHARED")
def test_sh_p3_cpu_and_t19(ctx, RA):
    """P3: two-source block min, shared on, is at least 15% under off. t19 three times, shared off, median <= 2.40 ms (D-S5c-2)."""
    body = dict(BASE, two_sources=True, source_balance=0.0)
    p = ctx.params(body)
    off_ms, on_ms = [], []
    for i in range(6):
        r_off = json.loads(ctx.play(p, {"shared_tail": False}, "bench", 2, 2))
        r_on = json.loads(ctx.play(p, {"shared_tail": True}, "bench", 2, 2))
        off_ms.append(r_off["play_mean_ms"])
        on_ms.append(r_on["play_mean_ms"])
    off_min, on_min = min(off_ms), min(on_ms)
    save = (off_min - on_min) / off_min
    t19 = []
    for _ in range(3):
        t19.append(RA.t19_two_source_radiation_cpu(ctx))
    _note("P3", {"off_ms": off_ms, "on_ms": on_ms, "off_min": off_min, "on_min": on_min, "save": save})
    _note("t19", t19)
    assert save >= 0.15, f"CPU save {save:.3f} < 0.15 off {off_ms} on {on_ms}"
    for row in t19:
        assert row["play_median_ms"] <= 2.40, row


@pytest.mark.slow
@pytest.mark.phase("SHARED")
def test_sh_p4_t30(ctx):
    """P4. Octave T30 within 10% of the dial, and not more than 3 points worse than off."""
    scenes = {
        "def_1": (dict(BASE, **TAIL), 1.8, 8.0),
        "def_2": (dict(BASE, **TAIL, two_sources=True, source_balance=0.0), 1.8, 8.0),
        "big_1": (dict(BASE, **BIG, **TAIL), 4.0, 12.0),
        "big_2": (dict(BASE, **BIG, **TAIL, two_sources=True, source_balance=0.0), 4.0, 12.0),
    }
    rows = {}
    for name, (body, dial, secs) in scenes.items():
        off = ctx.play_ir(body, {"shared_tail": False}, secs)
        on = ctx.play_ir(body, {"shared_tail": True}, secs)
        for fc in OCT:
            for ch, label in ((0, "L"), (1, "R")):
                a = _t30(off[:, ch], fc)
                b = _t30(on[:, ch], fc)
                ea = abs(a - dial) / dial
                eb = abs(b - dial) / dial
                rows[f"{name}_{label}_{fc}"] = {"off": a, "on": b, "err_off": ea, "err_on": eb}
                assert np.isfinite(b) and eb <= 0.10, f"P4 {name} {label} {fc} T30 {b} vs dial {dial}"
                assert eb <= ea + 0.03 + 1e-9, f"P4 {name} {label} {fc} worse than off by {(eb - ea) * 100:.2f} points"
    _note("P4", rows)


@pytest.mark.slow
@pytest.mark.phase("SHARED")
def test_sh_p5_p6_coherence_and_level(ctx):
    """P5 coherence and P6 level, tail, shared on versus off."""
    scenes = {
        "default": (dict(BASE, **TAIL), 0.08, 1.0, 3.0),
        "big": (dict(BASE, **BIG, **TAIL), 0.25, 2.5, 7.0),
        "small": (dict(BASE, **TAIL, W=6.0, H=3.0, L=8.0, sx=3.4, sz=5.6, mcx=2.8, mcz=2.4, decay_s=0.8), 0.04, 0.5, 2.0),
        "mid": (dict(BASE, **TAIL, W=15.0, H=8.0, L=22.0, sx=6.0, sz=15.0, mcx=8.5, mcz=6.0, decay_s=2.2), 0.1, 1.2, 4.0),
        "ortf_wide": (dict(BASE, **TAIL, toe_half_deg=45, space=0.30), 0.08, 1.0, 3.0),
    }
    coh_rows, lvl_rows = {}, {}
    p5_fail, p6_fail = [], []
    for name, (body, t0, t1, secs) in scenes.items():
        off = ctx.play_ir(body, {"shared_tail": False}, secs)
        on = ctx.play_ir(body, {"shared_tail": True}, secs)
        c0 = _coh(off[:, 0], off[:, 1], t0, t1)
        c1 = _coh(on[:, 0], on[:, 1], t0, t1)
        e = [c1[fc] - c0[fc] for fc in OCT]
        rms = float(np.sqrt(np.mean(np.square(e))))
        mx = float(np.max(np.abs(e)))
        coh_rows[name] = {
            "rms": rms, "max": mx,
            "off": [c0[fc] for fc in OCT],
            "on": [c1[fc] for fc in OCT],
            "dev": e,
        }
        # one shared network can't decorrelate a wide spacing as much as separate networks; scene limit accepted by Idle, D2
        rms_lim, max_lim = (0.15, 0.25) if name == "ortf_wide" else (0.09, 0.15)
        if not (rms <= rms_lim and mx <= max_lim):
            p5_fail.append(f"{name} rms {rms:.4f} max {mx:.4f}")
        a, b = int(t0 * SR), int(t1 * SR)
        for ch, label in ((0, "L"), (1, "R")):
            d_lvl = _rms_db(on[a:b, ch]) - _rms_db(off[a:b, ch])
            d_b = _third(on[:, ch], a, b)
            d_a = _third(off[:, ch], a, b)
            shape = [d_b[fc] - d_a[fc] for fc in THIRDS]
            dev = float(np.max(np.abs(np.array(shape) - np.mean(shape))))
            raw = float(np.max(np.abs(shape)))
            lvl_rows[f"{name}_{label}"] = {"db": d_lvl, "shape": dev, "raw": raw}
            if abs(d_lvl) > 1.0:
                p6_fail.append(f"{name} {label} level {d_lvl:.3f} dB")
            if raw > 3.5:
                p6_fail.append(f"{name} {label} third-octave {raw:.3f} dB")
    # Record every scene before the gate. ortf_wide is 0.15 / 0.25 (D2). Every other scene stays 0.09 / 0.15.
    _note("P5", coh_rows)
    _note("P6", lvl_rows)
    assert not p5_fail and not p6_fail, "P5 " + "; ".join(p5_fail) + " | P6 " + "; ".join(p6_fail)


@pytest.mark.phase("SHARED")
def test_sh_p7_mirror(ctx):
    """P7. Two sources, balance -1 vs +1, B.L vs A.R, tail, null <= -120 dB."""
    A = ctx.play_ir(dict(BASE, **TAIL, two_sources=True, source_balance=-1.0, shared_tail=True), {}, 3.0)
    B = ctx.play_ir(dict(BASE, **TAIL, two_sources=True, source_balance=1.0, shared_tail=True), {}, 3.0)
    n = min(len(A), len(B), SR)
    num = float(np.max(np.abs(B[:n, 0] - A[:n, 1])))
    den = float(np.max(np.abs(A[:n]))) + 1e-30
    null = 20.0 * np.log10(num / den + 1e-30)
    _note("P7", {"swap_null_db": null, "max_abs": num})
    assert null <= -120.0, null


@pytest.mark.phase("SHARED")
def test_sh_p8_binaural_ignores_the_flag(ctx):
    """P8. shared_tail true on a binaural pack is bit-exact to false. The override reaches the worklet."""
    body = dict(BASE, two_sources=True, source_balance=0.0, mic_setup="binaural", **TAIL)
    off = ctx.play_ir(body, {"shared_tail": False}, 1.5)
    on = ctx.play_ir(body, {"shared_tail": True}, 1.5)
    d = _mx(off, on)
    _note("P8", {"max_diff": d})
    assert d == 0.0, d


@pytest.mark.slow
@pytest.mark.phase("SHARED")
def test_sh_p9_long_decay_falls(ctx):
    """P9. 30 s at decay 8 s, default room and big room, shared on and off: finite and still falling."""
    default = dict(BASE, **TAIL)
    default["decay_s"] = 8.0
    big = dict(BASE, **BIG, **TAIL)
    big["decay_s"] = 8.0
    rooms = {"default": default, "big": big}
    rows = {}
    for name, body in rooms.items():
        for flag in (False, True):
            y = ctx.play_ir(body, {"shared_tail": flag}, 30.0)
            assert np.all(np.isfinite(y)), f"{name} shared={flag} not finite"
            n = 2 * SR
            win = []
            for i in range(0, len(y) - n + 1, n):
                win.append(_rms_db(y[i:i + n]))
            # Windows after 2 s must not climb, and the end must sit under the 4-6 s window.
            tail = win[1:]
            rise = max(tail[i + 1] - tail[i] for i in range(len(tail) - 1))
            drop = win[2] - win[-1]
            rows[f"{name}_{'on' if flag else 'off'}"] = {"end_db": win[-1], "at_4s_db": win[2], "max_rise_db": rise, "drop_db": drop}
            assert rise <= 1.0, f"{name} shared={flag} rose {rise} dB"
            assert drop > 3.0, f"{name} shared={flag} drop {drop} dB"
    _note("P9", rows)


@pytest.mark.phase("SHARED")
def test_sh_p10_toggle_no_spike(ctx):
    """P10. Toggling shared_tail during noise: no NaN, no sample over the pre-toggle peak + 3 dB."""
    p = ctx.params(dict(BASE, two_sources=True, source_balance=0.0))
    out = ctx.work / "sh_toggle.f32"
    if out.exists():
        out.unlink()
    sched = json.dumps([[2.0, {"shared_tail": True}], [3.2, {"shared_tail": False}]])
    ctx.play(p, {}, "switch", 4, 4.5, out, sched)
    x = np.fromfile(out, np.float32).reshape(-1, 2)
    pre = x[:2 * SR]
    pk = float(np.max(np.abs(pre)))
    post = float(np.max(np.abs(x[2 * SR:])))
    _note("P10", {"pre_peak": pk, "post_peak": post, "finite": bool(np.all(np.isfinite(x)))})
    assert np.all(np.isfinite(x))
    assert post <= pk * 10 ** (3.0 / 20.0) + 1e-6, f"post {post} pre {pk}"
