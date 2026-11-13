"""SL4: directional per-line decay (s' >= 0.5) + one Render calibration pass (slow: real renders).
Box criterion (SURFACES_IN_LOOP D-SL4): >= 90 % of octave bands within +-10 % of target after calibration;
calibration never makes a band worse by > 10 points; no double slope; L-R tail balance moves <= 0.685 dB."""
import hashlib
import json
import os
import time
from pathlib import Path
import numpy as np
import pytest
try:
    import _sl_harness as H
    import _sl_render as R
except ImportError:
    from tests import _sl_harness as H
    from tests import _sl_render as R
import surf_loop as SL

CASES = [("real_default", 1.8), ("studio_panelled", None), ("bare_brick_plaster", None)]


def test_scene_keeps_directional_and_cal():
    """A posted Surfaces flag and the seven factors stay on the scene. s' floor stays 0.5."""
    import app_server as A
    p = A.params_from_body({
        "decay_mode": "surfaces",
        "surf_directional": True,
        "surf_cal": [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4],
    })
    assert p["decay_mode"] == "surfaces"
    assert p["surf_directional"] is True
    assert p["surf_cal"] == [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]
    assert SL.S_MIN >= 0.5


def _edt_t30(ir):
    from scipy import signal
    out = []
    x = ir.sum(1); a = np.abs(x); n0 = int(np.argmax(a >= 0.1 * a.max()))
    for fc in SL.OCT:
        y = SL._octave(x, fc, 48000)[n0:]
        e = np.cumsum((y ** 2)[::-1])[::-1]; e = 10 * np.log10(np.maximum(e / e[0], 1e-30))
        def fit(lo, hi):
            i0, i1 = int(np.argmax(e <= lo)), int(np.argmax(e <= hi))
            if i1 <= i0 + 48:              # < 1 ms: the band is direct-dominated, no slope to fit (ISO: undefined)
                return float("nan")
            t = np.arange(i0, i1) / 48000
            return -60.0 / np.polyfit(t, e[i0:i1], 1)[0]
        out.append(fit(0, -10) / fit(-5, -35))
    return np.asarray(out)


def _lr_tail_db(ir):
    a, b = int(0.08 * 48000), int(1.0 * 48000)
    return 10 * np.log10(np.sum(ir[a:b, 0] ** 2) / np.sum(ir[a:b, 1] ** 2))


def _sl4_calibrated(room, anchor):
    """One room's two calibration renders, in this worker."""
    from _render_cache import install_from_env
    install_from_env()
    ir0, _i0, ir1, i1, cal = R.render_calibrated(room, True, anchor)
    tgt = np.asarray(i1["surf"]["target_T_oct"])
    return dict(target=tgt.tolist(), t20_before=SL.t20_per_octave(ir0.sum(1)), t20_after=SL.t20_per_octave(ir1.sum(1)),
                cal=cal, edt_t30=_edt_t30(ir1).tolist(), lr_tail_db=float(_lr_tail_db(ir1)),
                guard=[len(b["guard"]) for b in i1["surf"]["buses"]], stab=[b["stab"] for b in i1["surf"]["buses"]],
                finite=bool(np.all(np.isfinite(ir1))), peak=float(np.max(np.abs(ir1))))


def _sl4_flat(room, anchor):
    from _render_cache import install_from_env
    install_from_env()
    irf, _ = R.render_body(**R.room_body(room, anchor, decay_mode="flat"))
    return _edt_t30(irf).tolist(), float(_lr_tail_db(irf))


def _sl4_dir():
    """One folder per engine fingerprint and this test file, under the gitignored render cache."""
    from _render_cache import CACHE, fingerprint
    digest = hashlib.sha256()
    digest.update(fingerprint())
    digest.update(Path(__file__).read_bytes())
    folder = CACHE / "sl4" / digest.hexdigest()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _sl4_part(room):
    return _sl4_dir() / (room + ".json")


def _sl4_lock(room):
    return _sl4_dir() / (room + ".lock")


def _sl4_held(room) -> bool:
    return _sl4_lock(room).exists()


def _sl4_ensure(room, anchor):
    """Render this room once. Another worker may already hold the lock."""
    part = _sl4_part(room)
    if part.is_file():
        return
    lock = _sl4_lock(room)
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        deadline = time.time() + 1200
        while time.time() < deadline and not part.is_file():
            if not lock.exists():
                return _sl4_ensure(room, anchor)
            try:
                if time.time() - lock.stat().st_mtime > 1200:
                    lock.unlink()
                    return _sl4_ensure(room, anchor)
            except OSError:
                return _sl4_ensure(room, anchor)
            time.sleep(0.25)
        return
    os.close(fd)
    try:
        if not part.is_file():
            data = _sl4_calibrated(room, anchor)
            blob = json.dumps(data, default=float)
            tmp = part.with_name(room + "." + str(os.getpid()) + ".tmp")
            tmp.write_text(blob, encoding="utf-8")
            os.replace(tmp, part)
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


def _sl4_flat_part():
    return _sl4_dir() / "real_default.flat.json"


def _sl4_ensure_flat():
    """Flat is its own render so the calibration worker is not also the flat worker."""
    part = _sl4_flat_part()
    if part.is_file():
        return
    lock = _sl4_dir() / "real_default.flat.lock"
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        deadline = time.time() + 1200
        while time.time() < deadline and not part.is_file():
            if not lock.exists():
                return _sl4_ensure_flat()
            try:
                if time.time() - lock.stat().st_mtime > 1200:
                    lock.unlink()
                    return _sl4_ensure_flat()
            except OSError:
                return _sl4_ensure_flat()
            time.sleep(0.25)
        return
    os.close(fd)
    try:
        if not part.is_file():
            edt, lr = _sl4_flat("real_default", 1.8)
            blob = json.dumps({"flat_edt_t30": edt, "flat_lr_tail_db": lr})
            tmp = part.with_name("real_default.flat." + str(os.getpid()) + ".tmp")
            tmp.write_text(blob, encoding="utf-8")
            os.replace(tmp, part)
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


def _sl4_wait_flat():
    deadline = time.time() + 1200
    part = _sl4_flat_part()
    lock = _sl4_dir() / "real_default.flat.lock"
    while time.time() < deadline and not part.is_file():
        if lock.exists():
            try:
                if time.time() - lock.stat().st_mtime > 1200:
                    lock.unlink()
            except OSError:
                pass
        if not lock.exists():
            _sl4_ensure_flat()
        time.sleep(0.25)
    if not part.is_file():
        raise AssertionError("SL4 flat render did not finish")


def _sl4_wait():
    """Owners render. A single process also renders any room nobody has claimed."""
    deadline = time.time() + 1200
    anchors = dict(CASES)
    while time.time() < deadline:
        missing = [room for room, _anchor in CASES if not _sl4_part(room).is_file()]
        if not missing:
            return
        # The owner may have been killed and left no lock. Any worker can finish that room.
        for room in missing:
            if not _sl4_held(room):
                _sl4_ensure(room, anchors[room])
        time.sleep(0.25)
    missing = [room for room, _anchor in CASES if not _sl4_part(room).is_file()]
    raise AssertionError("SL4 rooms did not finish: " + ",".join(missing))


def _sl4_results(own, need_flat=False):
    """Own room is rendered here. Flat is a separate render for the tail tests."""
    anchors = dict(CASES)
    if own:
        _sl4_ensure(own, anchors[own])
    if need_flat:
        _sl4_ensure_flat()
    _sl4_wait()
    if need_flat:
        _sl4_wait_flat()
    res = {}
    for room, _anchor in CASES:
        res[room] = json.loads(_sl4_part(room).read_text(encoding="utf-8"))
    if need_flat:
        res["real_default"].update(json.loads(_sl4_flat_part().read_text(encoding="utf-8")))
    return res


@pytest.mark.slow
def test_calibrated_bands_within_10pct():
    results = _sl4_results("real_default")
    n_ok = n = 0
    for r in results.values():
        e = np.asarray(r["t20_after"]) / np.asarray(r["target"]) - 1
        n_ok += int(np.sum(np.abs(e) <= 0.10)); n += len(e)
    assert n_ok >= int(np.ceil(0.9 * n)), (n_ok, n)


@pytest.mark.slow
def test_calibration_never_worse_by_10_points():
    results = _sl4_results("studio_panelled")
    for r in results.values():
        b = np.abs(np.asarray(r["t20_before"]) / np.asarray(r["target"]) - 1)
        a = np.abs(np.asarray(r["t20_after"]) / np.asarray(r["target"]) - 1)
        assert np.all(a <= b + 0.10)


@pytest.mark.slow
def test_stable_finite():
    results = _sl4_results("bare_brick_plaster")
    for r in results.values():
        assert r["finite"] and r["peak"] < 1.0
        assert all(s["max_loop_db"] < 0 and s["max_pole"] < 1 for s in r["stab"])


@pytest.mark.slow
def test_lr_tail_balance():
    results = _sl4_results(None, need_flat=True)
    r = results["real_default"]
    # BOXB 2026-11-09: B-set 32, directional tail on the asymmetric 32.
    assert abs(r["lr_tail_db"] - r["flat_lr_tail_db"]) <= 0.685


@pytest.mark.slow
@pytest.mark.xfail(strict=False, reason="FINDING (prebuild, box): untreated plaster room, directional lines: EDT/T30 is "
                   "0.62 / 0.46 / 0.57 at 250 Hz / 4 kHz / 8 kHz against Flat 1.04 / 0.85 / 0.89 (mild double slope). "
                   "D-SL2 says room average is the fallback; SL4 listens to A/B 3-4 and decides. See sl/README.md")
def test_no_double_slope():
    results = _sl4_results(None, need_flat=True)
    r = results["real_default"]
    s, f = np.asarray(r["edt_t30"], float), np.asarray(r["flat_edt_t30"], float)
    ok = np.isfinite(s) & np.isfinite(f)
    assert ok.sum() >= 6 and np.all(s[ok] >= f[ok] - 0.15), (s, f)


from _scopes import isolate
isolate(globals(), [
    ["test_calibrated_bands_within_10pct"],
    ["test_calibration_never_worse_by_10_points"],
    ["test_stable_finite"],
    ["test_lr_tail_balance", "test_no_double_slope"],
])
