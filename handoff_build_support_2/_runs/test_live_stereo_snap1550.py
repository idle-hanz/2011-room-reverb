"""Play's one C block: 32 lines, 0.55 after the mic FIR, colour not written back."""

from __future__ import annotations

import ctypes
import math
import time
from ctypes import POINTER, c_float, c_int, c_void_p
from pathlib import Path

import numpy as np

ROOT = Path("/workspace/build_support_2/snapshot_2026-10-01_1550/software")
DLL = Path("/workspace/build_support_2/_runs/live_stereo_snap1550.so")
N = 32
PART = 128


def soft_py(x: float) -> float:
    a = abs(x)
    if a <= 0.95:
        return x
    u = (a - 0.95) * 20.0
    if u > 16.0:
        return -0.999 if x < 0.0 else 0.999
    e = math.exp(-2.0 * u)
    th = (1.0 - e) / (1.0 + e)
    return (-1.0 if x < 0.0 else 1.0) * (0.95 + 0.05 * th)


class Engine:
    def __init__(self, sr: int = 48000):
        self.lib = ctypes.CDLL(str(DLL))
        lib = self.lib
        lib.live_bytes.argtypes = [c_int]
        lib.live_bytes.restype = c_int
        lib.live_bind.argtypes = [c_void_p, c_int, c_int]
        lib.live_bind.restype = c_void_p
        for name in (
            "live_blob_ptr", "live_ir_ptr", "live_in_l", "live_in_r",
            "live_out_l", "live_out_r",
        ):
            fn = getattr(lib, name)
            fn.argtypes = [c_void_p]
            fn.restype = c_void_p
        lib.live_len_ptr.argtypes = [c_void_p]
        lib.live_len_ptr.restype = c_void_p
        lib.live_route_ptr.argtypes = [c_void_p]
        lib.live_route_ptr.restype = c_void_p
        lib.live_load_room.argtypes = [c_void_p, c_int]
        lib.live_load_room.restype = None
        lib.live_load_irs.argtypes = [c_void_p, c_int]
        lib.live_load_irs.restype = None
        lib.live_load_route.argtypes = [c_void_p]
        lib.live_load_route.restype = None
        lib.live_force_delay.argtypes = [c_void_p, c_float]
        lib.live_force_delay.restype = None
        lib.live_probe.argtypes = [c_void_p, c_int, c_int, c_int, c_int]
        lib.live_probe.restype = c_float
        lib.live_soft.argtypes = [c_float]
        lib.live_soft.restype = c_float
        lib.live_stereo.argtypes = [c_void_p, POINTER(c_float), POINTER(c_float), POINTER(c_float), POINTER(c_float), c_int]
        lib.live_stereo.restype = None
        self.nbytes = lib.live_bytes(sr)
        self.mem = (ctypes.c_byte * self.nbytes)()
        self.st = lib.live_bind(ctypes.addressof(self.mem), self.nbytes, sr)
        if not self.st:
            raise RuntimeError("live_bind failed")
        self.sr = sr

    def _f(self, ptr, n):
        return (c_float * n).from_address(ptr)

    def _i(self, ptr, n):
        return (c_int * n).from_address(ptr)

    def load(self, blob, irs=None, route=None, delay=None):
        b = self._f(self.lib.live_blob_ptr(self.st), len(blob))
        for i, v in enumerate(blob):
            b[i] = float(v)
        self.lib.live_load_room(self.st, len(blob))
        if irs:
            packed = np.concatenate([np.asarray(h, np.float32).ravel() for h in irs])
            dst = self._f(self.lib.live_ir_ptr(self.st), int(packed.size))
            for i, v in enumerate(packed):
                dst[i] = float(v)
            lens = self._i(self.lib.live_len_ptr(self.st), len(irs))
            for i, h in enumerate(irs):
                lens[i] = int(len(h))
            self.lib.live_load_irs(self.st, len(irs))
        if route is not None:
            dst = self._i(self.lib.live_route_ptr(self.st), len(route))
            for i, v in enumerate(route):
                dst[i] = int(v)
            self.lib.live_load_route(self.st)
        if delay is not None:
            self.lib.live_force_delay(self.st, float(delay))

    def process(self, left, right):
        L = np.ascontiguousarray(left, np.float32)
        R = np.ascontiguousarray(right, np.float32)
        n = int(L.shape[0])
        outL = np.zeros(n, np.float32)
        outR = np.zeros(n, np.float32)
        self.lib.live_stereo(
            self.st,
            L.ctypes.data_as(POINTER(c_float)),
            R.ctypes.data_as(POINTER(c_float)),
            outL.ctypes.data_as(POINTER(c_float)),
            outR.ctypes.data_as(POINTER(c_float)),
            n,
        )
        return outL, outR

    def probe(self, bus, line, which, back):
        return float(self.lib.live_probe(self.st, bus, line, which, back))


def shelf():
    return [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]


def bus_block(delay_ms, inject, dffs, air_g, air_lp, dir_ms, dir_gain, delay_ms_b=None, inject_b=None, dffs_b=None):
    if delay_ms_b is None:
        delay_ms_b = delay_ms
    if inject_b is None:
        inject_b = [0.0] * N
    if dffs_b is None:
        dffs_b = [0.0] * N
    out = []
    out.extend(delay_ms)
    out.extend(inject)
    out.extend(dffs)
    out.extend(air_g)
    out.append(air_lp)
    for _ in range(N):
        out.extend(shelf())
    out.extend([dir_ms, dir_gain])
    out.extend(delay_ms_b)
    out.extend(inject_b)
    out.extend(dffs_b)
    out.extend(air_g)
    out.append(air_lp)
    for _ in range(N):
        out.extend(shelf())
    out.extend([dir_ms, dir_gain])
    return out


def make_blob(
    g=0.0, fdn_wet=0.0, direct_wet=0.0, early_wet=0.0, dry=0.0, makeup=1.0,
    gain_a=1.0, gain_b=1.0, two=0, colour=0, mono=0, direct_index=2,
    max_ms=1000, snap=1, inject=None, dffs=None, air_g=None, air_lp=0.0,
    pans=None, gains=None, dir_gain=1.0, delay_ms=None, inject_b=None, dffs_b=None,
):
    if inject is None:
        inject = [[0.0] * N, [0.0] * N, [0.0] * N]
    if dffs is None:
        dffs = [[0.0] * N, [0.0] * N, [0.0] * N]
    if air_g is None:
        air_g = [[0.0] * N, [0.0] * N, [0.0] * N]
    if delay_ms is None:
        delay_ms = [20.0] * N
    if pans is None:
        pans = [-1.0, 0.0, 1.0]
    if gains is None:
        gains = [1.0, 1.0, 1.0]
    blob = [1, g, fdn_wet, direct_wet, early_wet, dry, makeup, gain_a, gain_b,
            two, colour, mono, direct_index, max_ms, snap, 0]
    for i in range(3):
        blob.extend([gains[i], pans[i], 1.0])
    for _ in range(3):
        blob.extend([0.0, 1.0, 0.0, 0.0, 0.0, 0.0])
    for b in range(3):
        blob.extend(bus_block(delay_ms, inject[b], dffs[b], air_g[b], air_lp, delay_ms[0], dir_gain,
                              inject_b=inject_b[b] if inject_b else None,
                              dffs_b=dffs_b[b] if dffs_b else None))
    return blob


def impulse(n, both=True):
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)
    L[0] = 1.0
    if both:
        R[0] = 1.0
    return L, R


def route_fill(fdn=None, early=None, early_b=None, direct=None, direct_b=None, fdn_b=None):
    r = [-2] * (3 * N + 2 * N + 2 * N + 3 + 3 + 3 * N)
    o = 0
    for b in range(3):
        row = fdn[b] if fdn else [-1] * N
        for i in range(N):
            r[o] = row[i]
            o += 1
    for b in range(2):
        row = early[b] if early else [-2] * N
        for i in range(N):
            r[o] = row[i]
            o += 1
    for b in range(2):
        row = early_b[b] if early_b else [-2] * N
        for i in range(N):
            r[o] = row[i]
            o += 1
    for b in range(3):
        r[o] = -1 if direct is None else direct[b]
        o += 1
    for b in range(3):
        r[o] = -1 if direct_b is None else direct_b[b]
        o += 1
    for b in range(3):
        row = fdn_b[b] if fdn_b else [-1] * N
        for i in range(N):
            r[o] = row[i]
            o += 1
    return r


def inj_one(bus, line, amp=1.0):
    inj = [[0.0] * N, [0.0] * N, [0.0] * N]
    inj[bus][line] = amp
    return inj


def test_soft_knee():
    eng = Engine()
    assert abs(eng.lib.live_soft(c_float(0.4)) - 0.4) < 1e-6
    got = eng.lib.live_soft(c_float(1.2))
    assert abs(got - soft_py(1.2)) < 1e-4
    got = eng.lib.live_soft(c_float(-1.05))
    assert abs(got - soft_py(-1.05)) < 1e-4


def test_direct_fold_and_not_written_back():
    eng = Engine()
    blob = make_blob(direct_wet=1.0, fdn_wet=0.0, early_wet=0.0, gains=[1.0, 0.0, 0.0])
    eng.load(blob, delay=64)
    yL, yR = eng.process(*impulse(PART))
    assert abs(float(yL[64]) - 0.55) < 1e-4
    assert abs(float(yR[64])) < 1e-5
    assert abs(eng.probe(0, 0, 4, PART - 1) - 1.0) < 1e-5


def test_direct_sos_identity_then_fold():
    eng = Engine()
    ir = np.array([-2011.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0], np.float32)
    fdn = [[0] * N, [0] * N, [0] * N]
    blob = make_blob(direct_wet=1.0, colour=1, gains=[1.0, 0.0, 0.0])
    eng.load(blob, irs=[ir], route=route_fill(fdn=fdn, direct=[0, 0, 0]), delay=64)
    yL, _ = eng.process(*impulse(PART * 2))
    assert abs(float(yL[64]) - 0.55) < 1e-3
    assert abs(eng.probe(0, 0, 4, PART * 2 - 1) - 1.0) < 1e-4


def test_direct_fir_then_fold():
    eng = Engine()
    ir = np.array([0.0, 1.0], np.float32)
    fdn = [[0] * N, [0] * N, [0] * N]
    blob = make_blob(direct_wet=1.0, colour=1, gains=[1.0, 0.0, 0.0])
    eng.load(blob, irs=[ir], route=route_fill(fdn=fdn, direct=[0, 0, 0]), delay=64)
    yL, _ = eng.process(*impulse(PART * 2))
    assert abs(float(yL[64])) < 1e-3
    assert abs(float(yL[65]) - 0.55) < 1e-3
    assert abs(eng.probe(0, 0, 4, PART * 2 - 1) - 1.0) < 1e-4


def test_fdn_fir_not_written_back_and_line_31():
    eng = Engine()
    inj = inj_one(0, 31, 0.5)
    blob = make_blob(fdn_wet=1.0, inject=inj, gains=[1.0, 0.0, 0.0])
    eng.load(blob, delay=64)
    yL, _ = eng.process(*impulse(PART))
    assert abs(float(yL[64]) - 0.5) < 1e-4, float(yL[64])
    assert abs(eng.probe(0, 31, 0, PART - 1) - 0.5) < 1e-4

    eng = Engine()
    ir = np.array([0.0, 1.0], np.float32)
    inj = inj_one(0, 0, 0.5)
    fdn = [[-1] * N, [-1] * N, [-1] * N]
    fdn[0][0] = 0
    blob = make_blob(fdn_wet=1.0, colour=1, inject=inj, gains=[1.0, 0.0, 0.0])
    eng.load(blob, irs=[ir], route=route_fill(fdn=fdn), delay=64)
    yL, _ = eng.process(*impulse(PART))
    assert abs(float(yL[64])) < 1e-3
    assert abs(float(yL[65]) - 0.5) < 1e-3
    assert abs(eng.probe(0, 0, 0, PART - 1) - 0.5) < 1e-3


def test_early_centre_plain_and_lr_shares_fdn_filter():
    eng = Engine()
    inj = inj_one(1, 0, 0.5)
    ir_line = np.array([0.0, 1.0], np.float32)
    ir_private = np.array([0.0, 0.0, 1.0], np.float32)
    fdn = [[-1] * N, [-1] * N, [-1] * N]
    fdn[1][0] = 0
    blob = make_blob(early_wet=1.0, colour=1, inject=inj, pans=[-1.0, -1.0, 1.0])
    eng.load(blob, irs=[ir_line, ir_private], route=route_fill(fdn=fdn), delay=64)
    yL, _ = eng.process(*impulse(PART))
    assert abs(float(yL[64]) - 0.5) < 1e-3, float(yL[64])
    assert abs(float(yL[66])) < 1e-3

    eng = Engine()
    inj = inj_one(0, 0, 0.5)
    fdn = [[-1] * N, [-1] * N, [-1] * N]
    fdn[0][0] = 0
    early = [[-1] * N, [-1] * N]
    early[0][0] = 1
    blob = make_blob(early_wet=1.0, colour=1, inject=inj)
    eng.load(blob, irs=[ir_line, ir_private], route=route_fill(fdn=fdn, early=early), delay=64)
    yL, _ = eng.process(*impulse(PART))
    assert abs(float(yL[64])) < 1e-3
    assert abs(float(yL[65]) - 0.5) < 1e-3, float(yL[65])
    assert abs(float(yL[66])) < 1e-3


def test_two_tanks_added_before_colour():
    eng = Engine()
    inj = inj_one(0, 0, 1.0)
    inj_b = inj_one(0, 0, 1.0)
    ir = np.array([0.0, 1.0], np.float32)
    fdn = [[-1] * N, [-1] * N, [-1] * N]
    fdn[0][0] = 0
    blob = make_blob(fdn_wet=1.0, colour=1, two=1, inject=inj, inject_b=inj_b)
    eng.load(blob, irs=[ir], route=route_fill(fdn=fdn, fdn_b=fdn), delay=64)
    L = np.zeros(PART, np.float32)
    R = np.zeros(PART, np.float32)
    R[0] = 1.0
    yL, _ = eng.process(L, R)
    assert abs(eng.probe(0, 0, 0, PART - 1)) < 1e-3
    assert abs(eng.probe(0, 0, 1, PART - 1) - 0.5) < 1e-3
    assert abs(float(yL[65]) - 0.5) < 1e-3

    eng = Engine()
    eng.load(blob, irs=[ir], route=route_fill(fdn=fdn, fdn_b=fdn), delay=64)
    L[0] = 1.0
    R[0] = 1.0
    yL, _ = eng.process(L, R)
    assert abs(eng.probe(0, 0, 0, PART - 1) - 0.5) < 1e-3
    assert abs(eng.probe(0, 0, 1, PART - 1) - 0.5) < 1e-3
    assert abs(float(yL[65]) - soft_py(1.0)) < 1e-3


def test_source_b_uses_its_own_colour():
    ir_a = np.array([0.0, 1.0], np.float32)
    ir_b = np.array([0.0, 0.0, 1.0], np.float32)
    fdn = [[-1] * N, [-1] * N, [-1] * N]
    fdn_b = [[-1] * N, [-1] * N, [-1] * N]
    fdn[0][0] = 0
    fdn_b[0][0] = 1
    inj = inj_one(0, 0, 1.0)
    blob = make_blob(fdn_wet=1.0, colour=1, two=1, inject=inj, inject_b=inj)
    route = route_fill(fdn=fdn, fdn_b=fdn_b)
    eng = Engine()
    eng.load(blob, irs=[ir_a, ir_b], route=route, delay=64)
    L = np.zeros(PART, np.float32)
    R = np.zeros(PART, np.float32)
    R[0] = 1.0
    yL, _ = eng.process(L, R)
    assert abs(float(yL[65])) < 1e-3, float(yL[65])
    assert abs(float(yL[66]) - 0.5) < 1e-3, float(yL[66])

    eng = Engine()
    eng.load(blob, irs=[ir_a, ir_b], route=route, delay=64)
    L[0] = 1.0
    R[0] = 0.0
    yL, _ = eng.process(L, R)
    assert abs(float(yL[65]) - 0.5) < 1e-3, float(yL[65])
    assert abs(float(yL[66])) < 1e-3, float(yL[66])

    early_b = [[-1] * N, [-1] * N]
    early_b[0][0] = 1
    blob = make_blob(early_wet=1.0, colour=1, two=1, inject=inj, inject_b=inj)
    route = route_fill(fdn=fdn, early_b=early_b, fdn_b=fdn_b)
    eng = Engine()
    eng.load(blob, irs=[ir_a, ir_b], route=route, delay=64)
    L[0] = 0.0
    R[0] = 1.0
    yL, _ = eng.process(L, R)
    assert abs(float(yL[65])) < 1e-3, float(yL[65])
    assert abs(float(yL[66]) - soft_py(1.0)) < 1e-3, float(yL[66])


def test_numpy_fir_and_inject_scale():
    eng = Engine()
    rng = np.random.default_rng(7)
    ir = rng.normal(size=300).astype(np.float64)
    ir *= np.exp(-np.arange(300) / 40.0)
    ir = (ir / np.max(np.abs(ir))).astype(np.float32)
    inj = inj_one(0, 0, 0.25)
    fdn = [[-1] * N, [-1] * N, [-1] * N]
    blob = make_blob(direct_wet=1.0, colour=1, gains=[1.0, 0.0, 0.0])
    eng.load(blob, irs=[ir], route=route_fill(fdn=fdn, direct=[0, 0, 0]), delay=64)
    n = PART * 8
    yL, _ = eng.process(*impulse(n))
    expected = np.zeros(n, np.float64)
    expected[64:64 + len(ir)] = ir * 0.55
    err = float(np.max(np.abs(yL[:64 + len(ir)] - expected[:64 + len(ir)])))
    assert err < 2e-3, err

    eng = Engine()
    blob = make_blob(fdn_wet=1.0, inject=inj)
    eng.load(blob, delay=64)
    yL, _ = eng.process(*impulse(PART))
    assert abs(float(yL[64]) - 0.25) < 1e-4


def test_air_pole_and_no_gain_cap():
    eng = Engine()
    inj = inj_one(0, 0, 1.0)
    air = [[0.0] * N, [0.0] * N, [0.0] * N]
    air[0][0] = 0.5
    blob = make_blob(fdn_wet=1.0, inject=inj, air_g=air, air_lp=1.0)
    eng.load(blob, delay=64)
    yL, _ = eng.process(*impulse(PART))
    assert abs(float(yL[64]) - 0.5) < 1e-4
    assert abs(float(yL[65]) - 0.25) < 1e-4

    def tail(g):
        e = Engine()
        inj = [[0.08] * N, [0.08] * N, [0.08] * N]
        dffs = [[-0.5] * N, [-0.5] * N, [-0.5] * N]
        delay = [12.0 + i * 0.7 for i in range(N)]
        blob = make_blob(g=g, fdn_wet=1.0, inject=inj, dffs=dffs, delay_ms=delay, snap=1)
        e.load(blob)
        n = 48000
        rng = np.random.default_rng(3)
        x = rng.normal(scale=0.01, size=n).astype(np.float32)
        yL, yR = e.process(x, x)
        assert np.all(np.isfinite(yL)) and np.all(np.isfinite(yR))
        assert float(np.max(np.abs(yL))) < 1.0
        return float(np.sqrt(np.mean(yL[12000:36000] ** 2)))

    loud = tail(0.158)
    quiet = tail(0.12)
    assert loud > quiet * 1.15, (loud, quiet)


def test_colour_stays_finite_and_realtime():
    eng = Engine()
    rng = np.random.default_rng(11)
    irs = []
    for k in range(24):
        h = rng.normal(size=4096).astype(np.float64)
        h *= np.exp(-np.arange(4096) / (80.0 + 10 * k))
        h /= np.max(np.abs(h))
        irs.append(h.astype(np.float32))
    fdn = []
    for b in range(3):
        fdn.append([(b * N + i) % 24 for i in range(N)])
    inj = [[0.05] * N, [0.04] * N, [0.05] * N]
    dffs = [[-0.4] * N, [-0.4] * N, [-0.4] * N]
    delay = [10.0 + (i * 1.3) for i in range(N)]
    blob = make_blob(g=0.158, fdn_wet=1.0, early_wet=1.0, direct_wet=1.0, colour=1,
                     inject=inj, dffs=dffs, delay_ms=delay)
    early = [fdn[0][:], fdn[2][:]]
    eng.load(blob, irs=irs, route=route_fill(fdn=fdn, early=early, direct=[0, 1, 2]))
    n = 48000
    x = rng.normal(scale=0.05, size=n).astype(np.float32)
    t0 = time.perf_counter()
    yL, yR = eng.process(x, x)
    elapsed = time.perf_counter() - t0
    assert np.all(np.isfinite(yL)) and np.all(np.isfinite(yR))
    assert float(np.max(np.abs(yL))) < 1.0
    assert float(np.sqrt(np.mean(yL ** 2))) > 1e-4
    print("colour 1s cpu", round(elapsed, 3))
    assert elapsed < 1.0, elapsed

    eng2 = Engine()
    blob2 = make_blob(g=0.158, fdn_wet=1.0, early_wet=1.0, direct_wet=1.0, colour=1, two=1,
                      inject=inj, inject_b=inj, dffs=dffs, dffs_b=dffs, delay_ms=delay)
    eng2.load(blob2, irs=irs, route=route_fill(
        fdn=fdn, early=early, early_b=early, direct=[0, 1, 2], direct_b=[0, 1, 2],
        fdn_b=fdn))
    r = np.roll(x, 17)
    t1 = time.perf_counter()
    yL, yR = eng2.process(x, r)
    elapsed2 = time.perf_counter() - t1
    assert np.all(np.isfinite(yL)) and np.all(np.isfinite(yR))
    assert float(np.max(np.abs(yL))) < 1.0
    print("two-source colour 1s cpu", round(elapsed2, 3))
    assert elapsed2 < 1.0, elapsed2


def test_silence_after_air_stays_finite():
    eng = Engine()
    inj = inj_one(0, 0, 1.0)
    air = [[0.5] * N, [0.5] * N, [0.5] * N]
    dffs = [[-0.5] * N, [-0.5] * N, [-0.5] * N]
    blob = make_blob(g=0.158, fdn_wet=1.0, inject=inj, air_g=air, air_lp=1.0, dffs=dffs)
    eng.load(blob, delay=64)
    rng = np.random.default_rng(2)
    n = PART * 200
    x = rng.normal(scale=0.05, size=n).astype(np.float32)
    yL, yR = eng.process(x, x)
    assert np.all(np.isfinite(yL)) and np.all(np.isfinite(yR))
    z = np.zeros(n, np.float32)
    yL, yR = eng.process(z, z)
    assert np.all(np.isfinite(yL)) and np.all(np.isfinite(yR))
    assert float(np.max(np.abs(yL))) < 1.0


def test_early_lane_written_while_fader_down():
    """Early stays silent under the gate, and matches an always-on run once raised.

    The down stretch is longer than the line delay. Air is on, so a lane that
    was not tinted and written while Early was down cannot match.
    """
    delay = 64
    n0 = PART * 4
    n1 = PART * 4
    n = n0 + n1
    cases = (
        ("one fdn", False, 1.0, False),
        ("one both down", False, 0.0, False),
        ("one fdn diffuse", False, 1.0, True),
        ("two fdn", True, 1.0, False),
        ("two both down", True, 0.0, False),
        ("two fdn diffuse", True, 1.0, True),
    )

    def maxabs(a, b):
        return float(np.max(np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64))))

    for name, two, fdn, diffuse in cases:
        rng = np.random.default_rng(21 if two else 9)
        if two:
            left = rng.normal(scale=0.08, size=n).astype(np.float32)
            right = rng.normal(scale=0.08, size=n).astype(np.float32)
            left[n0 - 1] = np.float32(0.5)
            right[n0 - 1] = np.float32(-0.45)
        else:
            left = rng.normal(scale=0.08, size=n).astype(np.float32)
            left[n0 - 1] = np.float32(0.5)
            right = left
        if diffuse:
            inj = [[0.05] * N, [0.0] * N, [0.0] * N]
            dffs = [[-0.4] * N, [0.0] * N, [0.0] * N]
            air = [[0.5] * N, [0.0] * N, [0.0] * N]
            g = 0.158
        else:
            inj = inj_one(0, 0, 1.0)
            dffs = [[0.0] * N, [0.0] * N, [0.0] * N]
            air = [[0.0] * N, [0.0] * N, [0.0] * N]
            air[0][0] = 0.5
            g = 0.0

        def blob(early):
            return make_blob(
                g=g, fdn_wet=fdn, direct_wet=0.0, early_wet=early, dry=0.0,
                two=1 if two else 0, colour=0, inject=inj,
                inject_b=inj if two else None, dffs=dffs,
                dffs_b=dffs if two else None, air_g=air, air_lp=1.0,
                gains=[1.0, 0.0, 0.0],
            )

        def run(early0):
            eng = Engine()
            eng.load(blob(early0), delay=delay)
            aL, aR = eng.process(left[:n0], right[:n0])
            lane = eng.probe(0, 0, 2, 0)
            lane_b = eng.probe(0, 0, 3, 0) if two else 0.0
            fdn_lane = eng.probe(0, 0, 0, 0)
            fdn_b = eng.probe(0, 0, 1, 0) if two else 0.0
            eng.load(blob(1.0), delay=delay)
            bL, bR = eng.process(left[n0:], right[n0:])
            return aL, aR, bL, bR, lane, lane_b, fdn_lane, fdn_b

        off = run(0.0)
        low = run(5.0e-5)
        on = run(1.0)
        down_gap = max(maxabs(off[0], on[0]), maxabs(off[1], on[1]))
        up_gap = max(maxabs(off[2], on[2]), maxabs(off[3], on[3]))
        low_gap = max(maxabs(low[0], off[0]), maxabs(low[1], off[1]))
        assert down_gap > 1.0e-3, (name, down_gap)
        assert up_gap < 1.0e-6, (name, up_gap)
        assert low_gap < 1.0e-8, (name, low_gap)
        if fdn == 0.0:
            assert max(float(np.max(np.abs(off[0]))), float(np.max(np.abs(off[1])))) < 1.0e-8, name
        assert abs(off[4] - on[4]) < 1.0e-6, (name, off[4], on[4])
        assert abs(on[4]) > 1.0e-4, (name, on[4])
        assert abs(off[6] - on[6]) < 1.0e-6, (name, off[6], on[6])
        if two:
            assert abs(off[5] - on[5]) < 1.0e-6, (name, off[5], on[5])
            assert abs(on[5]) > 1.0e-4, (name, on[5])
            assert abs(off[7] - on[7]) < 1.0e-6, (name, off[7], on[7])


def test_source_has_no_cap_and_keeps_32():
    text = (ROOT / "engine" / "live_stereo.c").read_text(encoding="utf-8")
    assert "0.68" not in text
    assert "mic_one_pole" not in text
    assert "N = 32" in text
    assert "DIRECT_FOLD = 0.55" in text
    live = (ROOT / "static" / "js" / "live_fdn.js").read_text(encoding="utf-8")
    work = (ROOT / "static" / "js" / "fdn_worklet.js").read_text(encoding="utf-8")
    page = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    assert "createConvolver" not in live
    assert "WORKLET_VER = 37" in live
    assert "LANES = 4" in text
    assert "live_fdn.js?v=37" in page
    assert "MAX_SOS" in text
    assert "design_sos" in text
    assert "LS_DC" in text
    assert "ls_flush" in text
    assert "live_stereo" in work
    assert "outputChannelCount: [2]" in live or "outputChannelCount: [2]" in work


if __name__ == "__main__":
    test_soft_knee()
    test_direct_fold_and_not_written_back()
    test_direct_sos_identity_then_fold()
    test_direct_fir_then_fold()
    test_fdn_fir_not_written_back_and_line_31()
    test_early_centre_plain_and_lr_shares_fdn_filter()
    test_two_tanks_added_before_colour()
    test_source_b_uses_its_own_colour()
    test_numpy_fir_and_inject_scale()
    test_air_pole_and_no_gain_cap()
    test_silence_after_air_stays_finite()
    test_early_lane_written_while_fader_down()
    test_source_has_no_cap_and_keeps_32()
    print("core ok")
    test_colour_stays_finite_and_realtime()
    print("PASS")
