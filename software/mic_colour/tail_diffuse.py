"""Off-axis tail colour. G_tail(f) = -DI(f). The key defaults off.

VERIFIED (research 2.6): P_diff is the sin-weighted power of |H(theta, f)|^2.
relative_db is already 0 dB on axis, so G_tail(f) = 10 log10 of that mean.
PROPOSAL: K=3 is the product layout LS+HS+HS, not the research parenthetical
LS+HS+PK. ESTIMATE: a preset that is not schema v3 is a flat -DI(a) plus a
log high shelf. The dead capsule-colour function stays uncalled. No SciPy.
"""

from __future__ import annotations

import math

import numpy as np

from mic_colour.model import relative_db
from mic_colour.pattern_map import capsule_law
from mic_colour.preset_store import get_store, resolve_preset_id
from mic_colour.sos_fit import LAYOUTS, params_to_sos, sos_db

LAYOUT = tuple(LAYOUTS[3])
SUPER_A = 0.37
# Hypercardioid a + (1−a)cosθ. a=0.25 gives 1 / 0.25 / −0.5 at 0° / 90° / 180°.
HYPER_A = 0.25
_FIT_F = np.concatenate(
    [np.geomspace(20.0, 20000.0, 240), np.linspace(20100.0, 23000.0, 12)]
)
_FIT_W = np.concatenate([np.ones(240), 0.25 * np.ones(12)])
_THETA = np.arange(5.0, 180.0, 5.0)
_CACHE: dict = {}


def polar_a(polar: float, pattern: str | None = None) -> float:
    """Omni a=1, cardioid 0.5, super SUPER_A. A hypercardioid name is HYPER_A.

    polar 1 with no name stays SUPER_A. Same map as the desk polar slider.
    """
    if pattern is not None:
        name = str(pattern).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
        if name in ("hypercardioid", "hyper"):
            return HYPER_A
    d = max(0.0, min(1.0, float(polar)))
    if d <= 0.5:
        return 1.0 - d
    return 0.5 - (d - 0.5) * (0.5 - SUPER_A) / 0.5


def diffuse_index_db(a: float) -> float:
    """DI = -10 log10(REE), REE = a^2 + (1-a)^2 / 3. G_tail flat is -DI."""
    aa = float(a)
    ree = aa * aa + (1.0 - aa) * (1.0 - aa) / 3.0
    if ree < 1e-20:
        ree = 1e-20
    return -10.0 * math.log10(ree)


def _shelf_depth_db(family: str) -> float:
    """ESTIMATE. LDC -7 dB, SDC -3 dB, ribbon -6 dB, at 16 kHz."""
    name = str(family or "").lower()
    if "sdc" in name:
        return -3.0
    if "ribbon" in name:
        return -6.0
    return -7.0


def _hf_shelf_db(freqs, depth_db: float) -> np.ndarray:
    f = np.asarray(freqs, dtype=np.float64)
    t = np.zeros(f.shape, dtype=np.float64)
    hi = f >= 16000.0
    mid = (f > 4000.0) & ~hi
    t[hi] = 1.0
    if np.any(mid):
        t[mid] = np.log(f[mid] / 4000.0) / math.log(16000.0 / 4000.0)
    return float(depth_db) * t


def _bounds(fs: float):
    lo, hi = [], []
    for _k in LAYOUT:
        lo += [math.log2(15.0), -40.0, math.log2(0.2)]
        hi += [math.log2(0.45 * float(fs)), 30.0, math.log2(2.0)]
    return np.asarray(lo, dtype=np.float64), np.asarray(hi, dtype=np.float64)


def _init_params(target_fn, fs: float) -> np.ndarray:
    lo = float(np.asarray(target_fn(np.array([20.0]))).reshape(-1)[0])
    mid = float(np.asarray(target_fn(np.array([1000.0]))).reshape(-1)[0])
    hi = float(np.asarray(target_fn(np.array([16000.0]))).reshape(-1)[0])
    return np.asarray(
        [
            math.log2(150.0), lo - mid * 0.5, math.log2(0.6),
            math.log2(1500.0), (hi - lo) * 0.6 + mid * 0.5, math.log2(0.5),
            math.log2(8000.0), (hi - lo) * 0.4, math.log2(0.6),
        ],
        dtype=np.float64,
    )


def _fit_grid(fs: float):
    mask = _FIT_F <= min(20000.0, 0.45 * float(fs))
    return _FIT_F[mask], _FIT_W[mask]


def _cost(p, layout, fs, ff, ww, tgt) -> float:
    err = (sos_db(params_to_sos(p, layout, fs), ff, fs) - tgt) * ww
    return float(np.dot(err, err)), err


def _fit(target_fn, fs: float) -> np.ndarray:
    ff, ww = _fit_grid(fs)
    tgt = np.asarray(target_fn(ff), dtype=np.float64).reshape(-1)
    lo, hi = _bounds(fs)
    second = np.asarray(
        [
            math.log2(120.0), float(tgt[0]), math.log2(0.7),
            math.log2(2500.0), float(tgt[-1] - tgt[len(tgt) // 2]), math.log2(0.5),
            math.log2(8000.0), float(tgt[-1] * 0.5), math.log2(0.7),
        ],
        dtype=np.float64,
    )
    best_p = None
    best_cost = 1e300
    for start in (_init_params(target_fn, fs), second):
        p = np.clip(np.asarray(start, dtype=np.float64), lo + 1e-6, hi - 1e-6)
        lam = 1e-2
        for _it in range(12):
            cost, resid = _cost(p, LAYOUT, fs, ff, ww, tgt)
            n = int(p.size)
            jac = np.empty((resid.size, n), dtype=np.float64)
            for j in range(n):
                step = 1e-4 if j % 3 == 1 else 1e-5
                q = p.copy()
                q[j] = min(float(hi[j]) - 1e-6, float(p[j]) + step)
                used = float(q[j] - p[j])
                if used <= 0.0:
                    jac[:, j] = 0.0
                    continue
                _cq, rq = _cost(q, LAYOUT, fs, ff, ww, tgt)
                jac[:, j] = (rq - resid) / used
            gram = jac.T @ jac
            gram.flat[:: n + 1] += lam
            rhs = -(jac.T @ resid)
            try:
                delta = np.linalg.solve(gram, rhs)
            except np.linalg.LinAlgError:
                delta = np.linalg.lstsq(gram, rhs, rcond=None)[0]
            accepted = False
            for alpha in (1.0, 0.5, 0.25):
                trial = np.clip(p + alpha * delta, lo + 1e-6, hi - 1e-6)
                trial_cost, _tr = _cost(trial, LAYOUT, fs, ff, ww, tgt)
                if trial_cost < cost:
                    p = trial
                    accepted = True
                    break
            if accepted:
                lam = max(lam * 0.3, 1e-6)
            else:
                lam = min(lam * 10.0, 1e6)
                if lam >= 1e6:
                    break
        cost, _resid = _cost(p, LAYOUT, fs, ff, ww, tgt)
        if cost < best_cost:
            best_cost = cost
            best_p = p
    return params_to_sos(best_p, LAYOUT, fs)


def _stable_sos(sos) -> np.ndarray:
    out = np.asarray(sos, dtype=np.float64).reshape(3, 5).copy()
    for i in range(3):
        row = out[i]
        if not np.all(np.isfinite(row)):
            out[i] = (1.0, 0.0, 0.0, 0.0, 0.0)
            continue
        a1 = float(row[3])
        a2 = float(row[4])
        if not (abs(a2) < 1.0 and abs(a1) < 1.0 + a2):
            out[i] = (1.0, 0.0, 0.0, 0.0, 0.0)
    rounded = np.asarray(out, dtype=np.float32).astype(np.float64)
    for i in range(3):
        a1 = float(rounded[i, 3])
        a2 = float(rounded[i, 4])
        if not (abs(a2) < 1.0 and abs(a1) < 1.0 + a2):
            rounded[i] = (1.0, 0.0, 0.0, 0.0, 0.0)
    return rounded


def _preset(preset_id: str):
    pid = resolve_preset_id(preset_id, explicit=False)
    store = get_store()
    preset = store.get(pid)
    return pid, preset


def measured_model(preset_id: str):
    """Schema v3 only. Assumed v2 and an unknown id are unmeasured."""
    pid, preset = _preset(preset_id)
    if not preset or str(preset.get("schema") or "") != "mic_fitter.preset.v3":
        return pid, preset, None
    return pid, preset, get_store().model_for(pid)


def gain_db(preset_id: str, sr: float, polar, freqs, pattern=None) -> np.ndarray:
    """G_tail(f) in dB. Absolute -DI, not the 1 kHz-normalised table."""
    _pid, preset, model = measured_model(preset_id)
    f = np.asarray(freqs, dtype=np.float64).reshape(-1)
    if model is not None:
        rel = np.asarray(relative_db(model, f, _THETA), dtype=np.float64)
        if rel.ndim == 1:
            rel = rel.reshape(1, -1)
        w = np.sin(np.deg2rad(_THETA))
        w = w / np.sum(w)
        power = np.sum(w[:, None] * np.power(10.0, rel / 10.0), axis=0)
        return 10.0 * np.log10(np.maximum(power, 1e-20))
    family = ""
    if preset is not None:
        family = str(preset.get("family") or "")
    if polar is None:
        law = capsule_law(family)
        polar = law["polar"]
        if pattern is None:
            pattern = law["pattern"]
    flat = -diffuse_index_db(polar_a(polar, pattern))
    return flat + _hf_shelf_db(f, _shelf_depth_db(family))


def design_bus(preset_id: str, sr: float, polar=None, pattern=None) -> np.ndarray:
    """One bus, shape (3, 5), float32-rounded. Same numbers Play packs."""
    pid, _preset_row, model = measured_model(preset_id)
    use_polar = model is None and polar is not None
    pol_key = round(float(polar), 6) if use_polar else None
    pat_key = None
    if use_polar and pattern is not None:
        pat_key = str(pattern).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
        if pat_key not in ("hypercardioid", "hyper"):
            pat_key = None
    key = (pid, int(sr), pol_key, pat_key)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit
    target = lambda freqs: gain_db(
        pid, sr, None if model is not None else polar, freqs,
        None if model is not None else pattern,
    )
    sos = _stable_sos(_fit(target, float(sr)))
    _CACHE[key] = sos
    return sos


def design_pack(ids, sr: float, polars=None, patterns=None) -> list:
    """45 floats, L then C then R, three biquads each."""
    row = list(ids)
    pols = list(polars) if polars is not None else [None, None, None]
    pats = list(patterns) if patterns is not None else [None, None, None]
    while len(row) < 3:
        row.append(row[-1] if row else "NeumannU87AiCardioid")
    while len(pols) < 3:
        pols.append(None)
    while len(pats) < 3:
        pats.append(None)
    out = []
    for i in range(3):
        sos = design_bus(row[i], sr, pols[i], pats[i])
        out.extend(float(v) for v in np.asarray(sos, dtype=np.float64).reshape(-1))
    return out


def apply_sos_df1(x, sos, part: int = 128) -> np.ndarray:
    """DF1 matching live_stereo run_sos, including the denormal flush."""
    y = np.asarray(x, dtype=np.float64).reshape(-1).copy()
    n = int(y.shape[0])
    rows = np.asarray(sos, dtype=np.float64).reshape(-1, 5)
    step = int(part) if int(part) > 0 else n
    for b0, b1, b2, a1, a2 in rows:
        z1 = 0.0
        z2 = 0.0
        for i in range(n):
            xv = float(y[i])
            yi = float(b0) * xv + z1
            z1 = float(b1) * xv - float(a1) * yi + z2
            z2 = float(b2) * xv - float(a2) * yi
            y[i] = yi
            if (i + 1) % step == 0 or i + 1 == n:
                if -1.0e-30 < z1 < 1.0e-30:
                    z1 = 0.0
                if -1.0e-30 < z2 < 1.0e-30:
                    z2 = 0.0
    return y
