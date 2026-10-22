"""SL3 box proof: the REAL Play engine (live_stereo.c) built natively, pristine (A) vs SL3 patch (B).
1) B with Surfaces off nulls bit-exact against A (Flat Play unchanged).
2) B with identity sections nulls bit-exact against A.
3) B with real designed sections is finite and decays faster.
4) CPU per 128-sample block: A, B off, B on (median of interleaved runs). Box numbers are indicative;
   the gate is t19 on Idle's PC (SL3 stop if > +0.12 ms).
usage: python bench_play_native.py <libA.so> <libB.so> <software dir with tests/test_live_stereo.py> [out.json]"""
import ctypes, importlib.util, json, math, sys, time
from pathlib import Path
import numpy as np

libA, libB, SW = sys.argv[1], sys.argv[2], Path(sys.argv[3])
out_json = sys.argv[4] if len(sys.argv) > 4 else None
spec = importlib.util.spec_from_file_location("tls", SW / "tests" / "test_live_stereo.py")
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
sys.path[:0] = [str(SW), str(SW / "engine")]
N, SR, PART = 32, 48000, 128


def engine(lib):
    T.DLL = Path(lib)
    return T.Engine(SR)


rng = np.random.default_rng(7)
delay_ms = list(np.round(np.linspace(6.9, 49.9, N), 3))
inj = [[0.12] * N for _ in range(3)]
BLOB = T.make_blob(g=0.15, fdn_wet=1.0, direct_wet=0.5, early_wet=0.0, inject=inj, delay_ms=delay_ms, gains=[1.0, 1.0, 1.0])


def designed_sections():
    import surf_loop as SL, surf_target as ST
    from early_field import LIVE_32
    from surface_colour import surfaces_hit_by_n, default_surfaces
    d = [int(round(x * SR / 1000)) for x in delay_ms]
    s = default_surfaces()
    hits = [surfaces_hit_by_n(LIVE_32[i]) for i in range(N)]
    rates, _ = SL.line_rates(d, SR, 6.0, 3.0, 8.0, s, 0.35, SL.FIT_F, True, hits, 1.8)
    res = SL.design_bus(d, SR, np.ones(N), [None] * N, rates)
    return np.stack([res["secs"]] * 3), res["stab"]


def load_surf(eng, secs):
    eng.lib.live_surf_ptr.argtypes = [ctypes.c_void_p]; eng.lib.live_surf_ptr.restype = ctypes.c_void_p
    eng.lib.live_load_surf.argtypes = [ctypes.c_void_p, ctypes.c_int]; eng.lib.live_load_surf.restype = ctypes.c_int
    buf = (ctypes.c_double * (3 * N * 3 * 5)).from_address(eng.lib.live_surf_ptr(eng.st))
    flat = np.ascontiguousarray(secs, np.float64).ravel()
    ctypes.memmove(buf, flat.ctypes.data, flat.nbytes)
    return eng.lib.live_load_surf(eng.st, 1)


def run(eng, x, block=PART):
    L = np.zeros_like(x); R = np.zeros_like(x)
    for a in range(0, len(x), block):
        l, r = eng.process(x[a:a + block], x[a:a + block]); L[a:a + block] = l; R[a:a + block] = r
    return L, R


imp = np.zeros(SR * 2, np.float32); imp[0] = 1.0
res = {}
eA = engine(libA); eA.load(BLOB); yA = run(eA, imp)
eB = engine(libB); eB.load(BLOB); yB = run(eB, imp)
res["flat_off_bit_exact"] = bool(yA[0].tobytes() == yB[0].tobytes() and yA[1].tobytes() == yB[1].tobytes())
ident = np.zeros((3, N, 3, 5)); ident[..., 0] = 1.0
eI = engine(libB); eI.load(BLOB); res["identity_load_ok"] = int(load_surf(eI, ident)); yI = run(eI, imp)
res["identity_bit_exact"] = bool(yA[0].tobytes() == yI[0].tobytes())
secs, stab = designed_sections()
eS = engine(libB); eS.load(BLOB); res["designed_load_ok"] = int(load_surf(eS, secs)); yS = run(eS, imp)
bad = secs.copy(); bad[0, 0, 0, 4] = 1.2
eX = engine(libB); eX.load(BLOB); res["unstable_refused"] = int(load_surf(eX, bad)) == 0
def tail_db(y, a, b): return 10 * math.log10(float(np.sum(y[0][a:b].astype(np.float64) ** 2)) + 1e-30)
res["designed_finite"] = bool(np.all(np.isfinite(yS[0])))
res["tail_0p5_1s_db_flat"] = round(tail_db(yA, SR // 2, SR), 2)
res["tail_0p5_1s_db_surf"] = round(tail_db(yS, SR // 2, SR), 2)
res["design_stab"] = stab

# CPU
noise = (rng.standard_normal(SR * 4) * 0.1).astype(np.float32)
times = {"A": [], "B_off": [], "B_on": []}
engs = {"A": eA, "B_off": eB, "B_on": eS}
for rep in range(7):
    for k, e in engs.items():
        t = time.perf_counter(); run(e, noise); dt = time.perf_counter() - t
        times[k].append(1000.0 * dt / (len(noise) / PART))
med = {k: round(float(np.median(v)), 4) for k, v in times.items()}
res["ms_per_block_median"] = med
res["delta_on_vs_A_ms"] = round(med["B_on"] - med["A"], 4)
res["delta_off_vs_A_ms"] = round(med["B_off"] - med["A"], 4)
res["note"] = "gcc -O2 native .so via ctypes (call overhead included in all three); box CPU, indicative only"
print(json.dumps(res, indent=1))
if out_json:
    Path(out_json).write_text(json.dumps(res, indent=1))
