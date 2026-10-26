"""S5 / D-UI26=A acceptance. Face colour on the FDN inject and on Play early.

Run: software/.venv/Scripts/python.exe software/tests/test_s5_surf_tail.py [fast|exact|audio|passive|all]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

try:
    import pytest
except ImportError:  # pragma: no cover
    pytest = None

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
HARNESS = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness"
PY = SW / ".venv" / "Scripts" / "python.exe"
NODE = Path(os.environ.get(
    "RR_NODE",
    r"C:\Users\IdleHanz\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v26.7.0-win-x64\node.exe",
))
OLD_WASM = Path(os.environ["LOCALAPPDATA"]) / "Temp" / "live_stereo_pre_s5.wasm"
GOLDEN = HARNESS / "golden"
CLIENT = ROOT / "handoff_build_support_2" / "roadmap" / "s4_verify_1140" / "measure" / "client_body_1140.json"
SR = 48000.0
FC = [125, 250, 500, 1000, 2000, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000]
FC22 = [125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
        2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000]
MEAN_ABS = (0.05 + 0.06 + 0.08 + 0.10 + 0.14 + 0.18 + 0.22) / 7.0
CARPET = [0.02, 0.06, 0.14, 0.37, 0.60, 0.65, 0.70]


def _boot():
    sys.path[:0] = [str(HARNESS), str(HARNESS / "lib"), str(SW), str(SW / "engine"), str(SW / "tests")]
    os.chdir(SW)


def _ctx():
    import run_all as RA
    import types
    work = Path(os.environ["LOCALAPPDATA"]) / "Temp" / "s5_tests"
    work.mkdir(parents=True, exist_ok=True)
    return RA.Ctx(types.SimpleNamespace(
        sw=str(SW), python=str(PY), node=str(NODE),
        golden=str(GOLDEN), regen_golden=False, quick=False, perf_scale=1.0,
        workdir=str(work),
    ))


if pytest is not None:
    @pytest.fixture(scope="module")
    def ctx():
        """The two acceptance checks below are real tests. Thresholds stay."""
        _boot()
        return _ctx()


def _bands(x):
    x = np.asarray(x, dtype=np.float64)
    nfft = 1 << int(np.ceil(np.log2(max(len(x) + 1, 2))))
    X = np.abs(np.fft.rfft(x, nfft)) ** 2
    f = np.fft.rfftfreq(nfft, 1.0 / SR)
    out = []
    for fc in FC:
        m = (f >= fc * 2.0 ** -(1.0 / 6.0)) & (f < fc * 2.0 ** (1.0 / 6.0))
        out.append(float(X[m].sum()) + 1e-30)
    return np.array(out)


def _delta(ir, ref):
    """Third-octave dB, case minus reference, L/R mean. Windows 0-80 ms and 80 ms+."""
    return _delta_of(ir, ref, FC)


def _bands_of(x, centres):
    x = np.asarray(x, dtype=np.float64)
    nfft = 1 << int(np.ceil(np.log2(max(len(x) + 1, 2))))
    X = np.abs(np.fft.rfft(x, nfft)) ** 2
    f = np.fft.rfftfreq(nfft, 1.0 / SR)
    out = []
    for fc in centres:
        m = (f >= fc * 2.0 ** -(1.0 / 6.0)) & (f < fc * 2.0 ** (1.0 / 6.0))
        out.append(float(X[m].sum()) + 1e-30)
    return np.array(out)


def _delta_of(ir, ref, centres):
    """Third-octave dB on `centres`, L/R mean. Windows 0-80 ms and 80 ms+."""
    n = min(len(ir), len(ref))
    ir, ref = ir[:n], ref[:n]
    a = int(0.08 * SR)
    out = {}
    for name, sl in (("early", slice(0, a)), ("tail", slice(a, None))):
        cols = []
        for ch in (0, 1):
            cols.append(10.0 * np.log10(_bands_of(ir[sl, ch], centres) / _bands_of(ref[sl, ch], centres)))
        out[name] = np.mean(cols, axis=0)
    return out


def _maxabs(a, b):
    n = min(len(np.asarray(a).ravel()), len(np.asarray(b).ravel()))
    aa = np.asarray(a, dtype=np.float64).ravel()[:n]
    bb = np.asarray(b, dtype=np.float64).ravel()[:n]
    return float(np.max(np.abs(aa - bb)))


def _null_db(a, b):
    n = min(len(np.asarray(a).ravel()), len(np.asarray(b).ravel()))
    aa = np.asarray(a, dtype=np.float64).ravel()[:n]
    bb = np.asarray(b, dtype=np.float64).ravel()[:n]
    return 10.0 * np.log10(max(float(np.sum((aa - bb) ** 2)), 1e-300) / max(float(np.sum(aa ** 2)), 1e-300))


def _base():
    body = json.loads(CLIENT.read_text(encoding="utf-8"))
    body.update({"direct_wet": 1.0, "early_wet": 1.0, "fdn_wet": 1.0, "colour_mode": "BYPASS"})
    return body


def _flat(body):
    b = json.loads(json.dumps(body))
    for card in b["surfaces"].values():
        absorb = card.get("absorb") or []
        if absorb:
            m = sum(float(x) for x in absorb) / float(len(absorb))
            card["absorb"] = [m] * len(absorb)
        eq = card.get("eq") or {}
        for k in ("low_shelf_db", "high_shelf_db", "peak_db"):
            if k in eq:
                eq[k] = 0.0
    return b


def _faces():
    def hs_a(b):
        b["surfaces"]["A"]["eq"]["high_shelf_db"] = 6.0
    def hs_all(b):
        for card in b["surfaces"].values():
            card["eq"]["high_shelf_db"] = 6.0
    def carpet(b):
        b["surfaces"]["E"]["absorb"] = list(CARPET)
    def peak(b):
        eq = b["surfaces"]["A"]["eq"]
        eq["peak_db"] = 6.0
        eq["peak_q"] = 1.0
        eq["peak_hz"] = 1000.0
    return (
        ("default", None, 0.3),
        ("hs6_A", hs_a, 0.3),
        ("hs6_all", hs_all, 0.3),
        ("carpet", carpet, 0.8),
        ("peak_A", peak, 0.3),
    )


def test_fit_default_quarter_db():
    _boot()
    import render_pipeline as rp
    import surface_colour as sc
    from early_field import LIVE_32

    class Tap:
        def __init__(self, n):
            self.n = n

    taps = [Tap(n) for n in LIVE_32]
    tail, report = rp._play_surf_cascade(sc.default_surfaces(), taps, None, SR, 32, False)
    print(f"SURF worst {report.get('worst_line')} residual {report['worst_db']:.4f} dB k_max {report.get('k_max')}")
    assert tail is not None
    assert len(tail) == 2 + 64 * (1 + 5 * int(report["k_max"]))
    assert float(report["worst_db"]) <= 0.25
    assert not report["misses"]
    # Hadamard 8 still packs 32 lines, so the loader accepts the section.
    short, _ = rp._play_surf_cascade(sc.default_surfaces(), taps, None, SR, 8, False)
    assert short is not None and len(short) == len(tail)


@pytest.mark.slow
def test_packer_omits_flat_and_parity():
    _boot()
    from app_server import params_from_body, live_fdn_params
    from render_pipeline import pack_blob_v2

    flat = _flat(_base())
    p = live_fdn_params(params_from_body(flat))
    assert "surf_cascade" not in p
    assert p["surf_fit"]["bypass"] is True
    shaped = live_fdn_params(params_from_body(_base()))
    assert len(shaped["surf_cascade"]) == 2 + 64 * (1 + 5 * int(shaped["surf_fit"]["k_max"]))
    blob = pack_blob_v2(shaped)
    assert any(abs(float(x) - 1.0) < 1e-6 for x in blob)


def test_d16_inject_stays_and_early_gate_drops():
    """Mute gates the early read. The FDN inject and the cascade stay."""
    _boot()
    from app_server import params_from_body, live_fdn_params
    p = live_fdn_params(params_from_body(dict(_base(), surfaces_mute=["A"])))
    gates = p.get("early_gate") or []
    assert len(gates) == 192
    assert min(gates) == 0.0
    inj = p["buses"]["l"]["inject"]
    assert max(abs(float(x)) for x in inj) > 1e-8
    assert "surf_cascade" in p


@pytest.mark.slow
def test_render_flat_and_parity_match_gain_only():
    """The relative cascade is the only Render audio change. Flat and parity skip it."""
    _boot()
    import app_server as A
    import render_pipeline as rp
    from render_pipeline import render

    orig = rp._scale_inject_reflect

    def gain_only(inj, taps, surfaces, sr=None, reaktor_parity=False):
        return orig(inj, taps, surfaces, sr=sr, reaktor_parity=True)

    def one(body, force):
        rp._scale_inject_reflect = gain_only if force else orig
        b = dict(A.DEFAULTS)
        b.update(body)
        b["ir_length_ms"] = 500.0
        b["colour_mode"] = "BYPASS"
        p = A.params_from_body(b)
        dry = np.zeros(1)
        dry[0] = 1.0
        kw = dict(
            W=p["W"], H=p["H"], L=p["L"], sox=p["sox"], soz=p["soz"], mz=p["mz"], my=p["my"],
            sy=p.get("sy"), sx=p["sx"], sz=p["sz"], mcz=p["mcz"], space=p["space"], diverg=p["diverg"],
            car_omni=p["car_omni"], early_wet=p["early_wet"], fdn_wet=p["fdn_wet"], dry_gain=p["dry_gain"],
            direct_wet=p.get("direct_wet", 1.0), fdn_g=p["fdn_g"], ir_length_ms=p["ir_length_ms"],
            path_on=p["path_on"], path_preset=p["path_preset"], ellipse_rate=p["ellipse_rate"],
            ellipse_rx=p["ellipse_rx"], ellipse_rz=p["ellipse_rz"], mcx=p["mcx"],
            toe_half_deg=p.get("toe_half_deg"), hadamard_n=p["hadamard_n"],
            humidity=p.get("humidity") or 0.0,
            air_lp=p.get("air_lp") if p.get("air_lp") is not None else 0.25,
            air_shelf=p.get("air_shelf") if p.get("air_shelf") is not None else 1.0,
            reaktor_parity=bool(p.get("reaktor_parity")),
            air_climate=str(p.get("air_climate") or "studio_20C_50RH"),
            air_iso=True, diffusion_master=p.get("diffusion_master") if p.get("diffusion_master") is not None else -0.5,
            decay_s=p.get("decay_s") or 0.0, decay_lock=bool(p.get("decay_lock")),
            surfaces=p.get("surfaces"), diffusion_seed=p["diffusion_seed"], lambda_ref=p["lambda_ref"],
            colour_mode="BYPASS", two_sources=False, dry_l=None, dry_r=None,
            surfaces_solo=p.get("surfaces_solo"), surfaces_mute=p.get("surfaces_mute"),
        )
        L, R, info = render(dry, int(SR), **kw)
        sc = float(info.get("norm_scale") or 1.0)
        return np.stack([np.asarray(L) / sc, np.asarray(R) / sc], 1)

    try:
        unlocked = {"decay_lock": False, "fdn_g": 0.8, "humidity": 0.5, "early_wet": 1.0,
                    "colour_mode": "BYPASS", "direct_wet": 1, "fdn_wet": 1}
        gain = one(unlocked, True)
        shaped = one(unlocked, False)
        moved = _maxabs(gain, shaped)
        print("shaped render vs gain-only maxabs", moved)
        assert moved > 0.0
        for label, body in (
            ("flat", _flat(dict(unlocked, surfaces=json.loads(CLIENT.read_text(encoding="utf-8"))["surfaces"]))),
        ):
            d = _maxabs(one(body, False), one(body, True))
            print(label, "render vs gain-only maxabs", d)
            assert d == 0.0
        early = dict(unlocked, direct_wet=0.0, fdn_wet=0.0, early_wet=1.0)
        d_early = _maxabs(one(early, False), one(early, True))
        print("early bus vs gain-only maxabs", d_early)
        assert d_early == 0.0
    finally:
        rp._scale_inject_reflect = orig


@pytest.mark.slow
def test_play_cascade_off_matches_pre_s5():
    """Stripping the cascade block matches the pre-S5 wasm. Flat and parity already omit it."""
    ctx = _ctx()
    body = {"decay_lock": False, "fdn_g": 0.8, "humidity": 0.5, "early_wet": 1.0,
            "colour_mode": "BYPASS", "direct_wet": 1, "fdn_wet": 1,
            # A missing key is the rumble filter. This compare is the pre-S5 wasm.
            # A missing phys_ceiling is the physics pack. The lock-on scene inherits this.
            "sub_hp": False, "phys_ceiling": False}
    full = ctx.play_ir(body, {"colour_on": False}, 1.0)
    p = ctx.params(body)
    data = json.loads(Path(p).read_text(encoding="utf-8"))
    data.pop("surf_cascade", None)
    stripped = Path(p).with_name("stripped_gold.json")
    stripped.write_text(json.dumps(data), encoding="utf-8")
    out = Path(ctx.work) / "stripped.f32"
    ctx.play(stripped, {"colour_on": False}, "ir", 1.0, out)
    got = np.fromfile(out, np.float32).reshape(-1, 2)
    d = _maxabs(full, got)
    print("play cascade-on vs cascade-off maxabs", d)
    assert d > 0.0
    if OLD_WASM.exists():
        old = ctx.play_ir(body, {"colour_on": False}, 1.0, wasm=OLD_WASM)
        d0 = _maxabs(got, old)
        print("play cascade-off vs pre-S5 wasm maxabs", d0)
        assert d0 == 0.0
    if OLD_WASM.exists():
        for label, extra in (
            ("flat", {"surfaces": {L: {"absorb": [MEAN_ABS] * 7} for L in "ABCDEF"}}),
        ):
            scene = dict(body, decay_lock=True, decay_s=1.8, **extra)
            a = ctx.play_ir(scene, {"colour_on": False}, 1.0, wasm=OLD_WASM)
            b = ctx.play_ir(scene, {"colour_on": False}, 1.0)
            d = _maxabs(a, b)
            print(label, "play old vs new maxabs", d)
            assert d == 0.0


def assert_surf_parity(ctx, extras=True):
    """D-S5c-4. |dPlay − dRender| on third octaves 125 Hz–16 kHz, L/R mean.

    Gated at 0.3 dB: tail 80 ms+ of default (shaped − flat), face-A HS+6 and
    all-faces HS+6 (each case − default); full-mix 0–80 ms of default and face-A.
    Reported, not gated: all-faces full-mix 0–80 ms, and every early-bus row.
    Carpet and peak stay on the previous band list and tolerances.
    """
    base = _base()
    flat = _flat(base)
    fails = []
    irs = {}

    def grab(tag, body):
        irs[tag] = (
            ctx.render_ir(body, 1500),
            ctx.play_ir(body, {"colour_on": False}, 1.5),
        )

    def with_fn(fn):
        body = json.loads(json.dumps(base))
        if fn:
            fn(body)
        return body

    def early_of(body):
        b = json.loads(json.dumps(body))
        b.update({"direct_wet": 0.0, "fdn_wet": 0.0, "early_wet": 1.0})
        return b

    grab("flat", flat)
    grab("default", base)
    grab("early_flat", early_of(flat))
    grab("early_default", early_of(base))
    for name, fn, _tol in _faces():
        if name == "default":
            continue
        if not extras and name in ("carpet", "peak_A"):
            continue
        body = with_fn(fn)
        grab(name, body)
        if name in ("hs6_A", "hs6_all"):
            grab("early_" + name, early_of(body))

    def gap(num, den, window, centres):
        r_num, p_num = irs[num]
        r_den, p_den = irs[den]
        dR = _delta_of(r_num, r_den, centres)[window]
        dP = _delta_of(p_num, p_den, centres)[window]
        return float(np.max(np.abs(dP - dR))), dR, dP

    gated = (
        ("default", "flat", "tail", 0.3),
        ("hs6_A", "default", "tail", 0.3),
        ("hs6_all", "default", "tail", 0.3),
        ("default", "flat", "early", 0.3),
        ("hs6_A", "default", "early", 0.3),
    )
    for num, den, window, tol in gated:
        worst, dR, dP = gap(num, den, window, FC22)
        print("gate", num, "minus", den, window, "worst |dP-dR|", round(worst, 3), "tol", tol)
        print("  dR", [round(float(v), 3) for v in dR])
        print("  dP", [round(float(v), 3) for v in dP])
        if worst > tol + 1e-6:
            fails.append(("gate", num, den, window, round(worst, 3), tol))
    worst, dR, dP = gap("hs6_all", "default", "early", FC22)
    print("report full-mix hs6_all early worst |dP-dR|", round(worst, 3))
    print("  dR", [round(float(v), 3) for v in dR])
    print("  dP", [round(float(v), 3) for v in dP])
    for num, den in (("default", "flat"), ("hs6_A", "default"), ("hs6_all", "default")):
        worst, dR, dP = gap("early_" + num, "early_" + den, "early", FC22)
        print("report early-bus", num, "minus", den, "worst |dP-dR|", round(worst, 3))
        print("  dR", [round(float(v), 3) for v in dR])
        print("  dP", [round(float(v), 3) for v in dP])
    if extras:
        for name, _fn, tol in _faces():
            if name not in ("carpet", "peak_A"):
                continue
            for window in ("early", "tail"):
                worst, dR, dP = gap(name, "flat", window, FC)
                print("gate", name, "minus flat", window, "worst |dP-dR|", round(worst, 3), "tol", tol)
                if worst > tol + 1e-6:
                    fails.append(("gate", name, "flat", window, round(worst, 3), tol))
    # Tail movement is FDN-only, the case against the default shape (box definition).
    if extras:
        def fdn(body):
            b = json.loads(json.dumps(body))
            b.update({"direct_wet": 0.0, "early_wet": 0.0, "fdn_wet": 1.0})
            return b
        base_fdn_r = ctx.render_ir(fdn(base), 1500)
        base_fdn_p = ctx.play_ir(fdn(base), {"colour_on": False}, 1.5)
        for name, fn, need, bands in (
            ("hs6_A", _faces()[1][1], 0.3, (8000, 10000, 12500, 16000)),
            ("hs6_all", _faces()[2][1], 4.0, (10000, 12500, 16000)),
        ):
            body = json.loads(json.dumps(base))
            fn(body)
            for eng, ir, ref in (
                ("Render", ctx.render_ir(fdn(body), 1500), base_fdn_r),
                ("Play", ctx.play_ir(fdn(body), {"colour_on": False}, 1.5), base_fdn_p),
            ):
                tail = _delta(ir, ref)["tail"]
                print(name, eng, "fdn tail vs default", [round(float(v), 2) for v in tail])
                for fc, v in zip(FC, tail):
                    if fc in bands and float(v) < need:
                        fails.append((eng, name, "fdn", fc, round(float(v), 3), need))
    if fails:
        raise AssertionError(fails)


@pytest.mark.slow
def test_mirror_exact(ctx):
    """Centred ORTF pair, source mirrored in x, A and C cards swapped. L/R swap."""
    W = 6.0
    body = {
        "W": W, "H": 3.0, "L": 8.0, "sx": 1.4, "sz": 3.2, "mcx": W / 2, "mcz": 2.0,
        "yaw_l_deg": -55.0, "yaw_r_deg": 55.0, "toe_half_deg": 55.0,
        "decay_lock": False, "fdn_g": 0.8, "humidity": 0.5,
        "direct_wet": 1.0, "early_wet": 1.0, "fdn_wet": 1.0, "colour_mode": "BYPASS",
        "surfaces": {L: {"absorb": [MEAN_ABS] * 7} for L in "ABCDEF"},
        # Mirror/null mode. Smooth stays off even when the body asks for it.
        "mirror_null": True, "smooth": True,
    }
    body["surfaces"]["A"] = {"absorb": [0.05, 0.06, 0.08, 0.10, 0.14, 0.18, 0.22],
                             "eq": {"high_shelf_db": 6.0}}
    mir = json.loads(json.dumps(body))
    mir["sx"] = W - body["sx"]
    a, c = json.loads(json.dumps(body["surfaces"]["A"])), json.loads(json.dumps(body["surfaces"]["C"]))
    mir["surfaces"]["A"], mir["surfaces"]["C"] = c, a
    for secs, ms, two in ((1.0, 1000, False), (1.0, 1000, True)):
        b0, b1 = dict(body), dict(mir)
        if two:
            b0.update(two_sources=True, sx_b=2.2, sz_b=3.2)
            b1.update(two_sources=True, sx_b=W - 2.2, sz_b=3.2)
        P0 = ctx.play_ir(b0, {"colour_on": False}, secs)
        P1 = ctx.play_ir(b1, {"colour_on": False}, secs)
        d = _maxabs(P0, P1[:, ::-1])
        print("mirror play", "two" if two else "one", "maxabs", d)
        assert d == 0.0
        R0 = ctx.render_ir(b0, ms)
        R1 = ctx.render_ir(b1, ms)
        nd = _null_db(R0, R1[:, ::-1])
        print("mirror render", "two" if two else "one", "null_db", round(nd, 1))
        assert nd <= -120.0


def _carpet_levels(x):
    def level(i):
        s = x[int(i * SR):int((i + 1) * SR), 0]
        return 10.0 * np.log10(float(np.mean(s ** 2)) + 1e-30)
    seq = [level(i) for i in range(2, 20, 2)]
    return seq, level


def _assert_no_runaway(x, label):
    assert np.all(np.isfinite(x))
    seq, level = _carpet_levels(x)
    print(label, "levels", [round(v, 1) for v in seq])
    assert all(b < a or b < -240.0 for a, b in zip(seq, seq[1:]))
    assert max(level(18), level(19)) <= -150.0


@pytest.mark.slow
def test_passivity_carpet_ls(ctx):
    """Dial path (phys_ceiling false). The S5 cascade is outside the loop, so T30 stays within ±3% of flat.

    No runaway over 20 s. On this path the ratios sit about 0.92 to 1.00.
    """
    from analyze import t60_bands
    body = _base()
    body.update({
        "decay_lock": True, "decay_s": 8.0,
        "direct_wet": 0.0, "early_wet": 0.0, "fdn_wet": 1.0,
        "phys_ceiling": False,
    })
    loud = json.loads(json.dumps(body))
    loud["surfaces"]["E"]["absorb"] = list(CARPET)
    for card in loud["surfaces"].values():
        card["eq"]["low_shelf_db"] = 12.0
    flat = _flat(body)
    X = ctx.play_ir(loud, {"colour_on": False}, 20.0)
    F = ctx.play_ir(flat, {"colour_on": False}, 20.0)
    _assert_no_runaway(X, "carpet dial")
    bands = (500, 1000, 2000, 4000)
    t_loud = t60_bands(X[:, 0], SR, bands=list(bands))
    t_flat = t60_bands(F[:, 0], SR, bands=list(bands))
    for b in bands:
        ratio = t_loud[b] / t_flat[b]
        print("T30", b, round(t_loud[b], 3), round(t_flat[b], 3), "ratio", round(ratio, 4))
        assert abs(ratio - 1.0) <= 0.03


@pytest.mark.slow
def test_passivity_carpet_ls_physics(ctx):
    """Physics path, key absent. Carpet against the untreated default room. No runaway.

    Carpet T30 must not exceed 1.03 times the default at 500 Hz to 4 kHz.
    The ratio against the physical target is printed and not gated.
    """
    from analyze import t60_bands
    import app_server as A
    import surf_loop as SLP
    import surf_panels as SP
    body = _base()
    body.update({
        "decay_lock": True, "decay_s": 8.0,
        "direct_wet": 0.0, "early_wet": 0.0, "fdn_wet": 1.0,
    })
    assert "phys_ceiling" not in body
    loud = json.loads(json.dumps(body))
    loud["surfaces"]["E"]["absorb"] = list(CARPET)
    for card in loud["surfaces"].values():
        card["eq"]["low_shelf_db"] = 12.0
    X = ctx.play_ir(loud, {"colour_on": False}, 20.0)
    D = ctx.play_ir(body, {"colour_on": False}, 20.0)
    _assert_no_runaway(X, "carpet physics")
    bands = (500, 1000, 2000, 4000)

    def teff(scene):
        p = A.params_from_body(scene)
        cards = SP.cards_with_treatment(p["surfaces"], p.get("surf_treatment") or [])
        st = SLP.phys_ceiling_row(p["W"], p["H"], p["L"], cards, 8.0)
        return {int(hz): float(t) for hz, t in zip(st["hz"], st["t"])}

    target_c = teff(loud)
    target_d = teff(body)
    t_loud = t60_bands(X[:, 0], SR, bands=list(bands))
    t_def = t60_bands(D[:, 0], SR, bands=list(bands))
    for b in bands:
        ratio = float(t_loud[b] / t_def[b])
        target = target_c[b] / target_d[b]
        print(
            "T30", b, round(float(t_loud[b]), 3), round(float(t_def[b]), 3),
            "ratio", round(ratio, 4), "target", round(target, 4),
        )
        assert ratio <= 1.03


def main(argv):
    which = set(argv[1:] or ["all"])
    if "all" in which:
        which = {"fast", "exact", "audio", "passive"}
    if "fast" in which:
        test_fit_default_quarter_db()
        test_packer_omits_flat_and_parity()
        test_d16_inject_stays_and_early_gate_drops()
        print("FAST ok")
    ctx = None
    if which & {"exact", "audio", "passive"}:
        _boot()
        ctx = _ctx()
    if "exact" in which:
        test_render_flat_and_parity_match_gain_only()
        test_play_cascade_off_matches_pre_s5()
        print("EXACT ok")
    errors = []
    if "audio" in which:
        try:
            assert_surf_parity(ctx)
            print("AUDIO colour ok")
        except AssertionError as e:
            errors.append(e)
            print("AUDIO colour FAIL", e)
        try:
            test_mirror_exact(ctx)
            print("AUDIO mirror ok")
        except AssertionError as e:
            errors.append(e)
            print("AUDIO mirror FAIL", e)
    if "passive" in which:
        try:
            test_passivity_carpet_ls(ctx)
            test_passivity_carpet_ls_physics(ctx)
            print("PASSIVE ok")
        except AssertionError as e:
            errors.append(e)
            print("PASSIVE FAIL", e)
    print("s5 acceptance done", " ".join(sorted(which)))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv)
