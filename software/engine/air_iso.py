"""ISO 9613-1 air colour for the engine. FITTED_TO_ISO_9613_1.

The analytic curve is candidate C (dual log-sigmoid high shelf). Presets
ship in ``engine/presets/air``; ``air_fitter/presets`` is only a fallback.
Realtime Render and Play use two RBJ high shelves (slope 1) with the same
corners and dB/m, so both paths share one gain law. Do not import the
``air_fitter`` package (its init pulls SciPy).

Humidity 0 bypasses the stage. Above 0 the slider sets relative humidity
at the climate's temperature: just above 0 is about 90 % RH, 0.35 is the
climate preset's RH, and 1.0 is the RH where 8–16 kHz loss peaks. The
slider never goes drier than that peak, so the loss stays monotonic.
Right is drier. The stored preset is the shelf at that preset's own RH.
Other humidities interpolate shipped RBJ knots (a numpy refit covers a
missing end). ``air_shelf`` 0..1 still scales the ISO depth. The Structure
1-pole stays a separate mix and still follows the slider's Wet law.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

_CACHE: Dict[str, dict] = {}
_FAMILY: Dict[Tuple[float, float], list] = {}
_FIT_CACHE: Dict[Tuple[float, float, float], np.ndarray] = {}
DEFAULT_CLIMATE = "studio_20C_50RH"
# Client default. This detent is the climate preset's RH, unless that RH
# is drier than the treble-loss peak (the dry preset is). Then it sits on
# the peak, so the shelf does not get brighter again.
HUMIDITY_NOMINAL = 0.35
# Just above 0. Wetter than this loses less 8–16 kHz, so the slider does
# not start wetter.
RH_WET_PCT = 90.0
# 8–16 kHz mean loss at 30 m, 101.325 kPa. 0.1 % search, confirmed when the
# presets were refit. Do not map the slider drier than the row for that
# temperature: past the peak the loss falls.
PEAK_RH_BY_T = ((20.0, 21.7), (22.0, 19.2))


def preset_roots() -> List[Path]:
    """Shipped climates first. The air_fitter pack remains a fallback."""
    here = Path(__file__).resolve()
    local = here.parent / "presets" / "air"
    pack = here.parents[2] / "air_fitter" / "presets"
    roots: List[Path] = []
    if (local / f"{DEFAULT_CLIMATE}.json").is_file():
        roots.append(local)
    if (pack / f"{DEFAULT_CLIMATE}.json").is_file():
        roots.append(pack)
    if not roots:
        roots.append(local)
    return roots


def preset_file(name: str) -> Path:
    """JSON for one climate. An unknown id uses the studio preset."""
    key = str(name or DEFAULT_CLIMATE)
    for root in preset_roots():
        path = root / f"{key}.json"
        if path.is_file():
            return path
    for root in preset_roots():
        path = root / f"{DEFAULT_CLIMATE}.json"
        if path.is_file():
            return path
    return preset_roots()[0] / f"{DEFAULT_CLIMATE}.json"

_REF_T = 293.15
_REF_P = 101.325
_TRIPLE = 273.16


def climate_record(name: str = DEFAULT_CLIMATE) -> dict:
    """Preset JSON. An unknown id falls back to the studio climate."""
    key = str(name or DEFAULT_CLIMATE)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit
    path = preset_file(key)
    data = json.loads(path.read_text(encoding="utf-8"))
    _CACHE[key] = data
    if key != data.get("id"):
        _CACHE[str(data.get("id") or key)] = data
    return data


def high_shelf_db(freqs, f0: float, depth_db: float, shelf_slope: float) -> np.ndarray:
    """Log-sigmoid high shelf in dB (the fitter's magnitude model, not RBJ)."""
    f = np.asarray(freqs, dtype=float)
    x = np.log10(np.maximum(f, 1.0) / max(float(f0), 1.0))
    blend = 1.0 / (1.0 + np.exp(-float(shelf_slope) * x))
    return float(depth_db) * blend


def h1_db_per_m(freqs, climate: str = DEFAULT_CLIMATE) -> np.ndarray:
    """H1(f) in dB/m. Path loss is distance times this."""
    p = climate_record(climate)["params"]
    lo = high_shelf_db(freqs, p["f0"], p["depth_db_per_m"], p["shelf_slope"])
    hi = high_shelf_db(freqs, p["f0_hi"], p["depth_hi_db_per_m"], p["shelf_slope_hi"])
    return lo + hi


def model_path_loss_db(freqs, distance_m: float, climate: str = DEFAULT_CLIMATE) -> np.ndarray:
    """Analytic candidate-C loss, dB (≤ 0). This is the fit the tolerance test checks."""
    return float(distance_m) * h1_db_per_m(freqs, climate)


def _iso_alpha_db_per_m(freqs, temperature_c: float, rh_pct: float, pressure_kpa: float) -> np.ndarray:
    """ISO 9613-1 α(f) in dB/m. Numpy only; same equations as air_fitter/iso9613.py."""
    t_k = float(temperature_c) + 273.15
    p = float(pressure_kpa)
    c = -6.8346 * (_TRIPLE / t_k) ** 1.261 + 4.6151
    p_sat = _REF_P * (10.0 ** c)
    # ISO 9613-1 note 3: h is the molar concentration in percent, not a fraction.
    h = float(rh_pct) * p_sat / p
    fr_o = (p / _REF_P) * (24.0 + 4.04e4 * h * (0.02 + h) / (0.391 + h))
    fr_n = (p / _REF_P) * (t_k / _REF_T) ** (-0.5) * (
        9.0 + 280.0 * h * np.exp(-4.170 * ((t_k / _REF_T) ** (-1.0 / 3.0) - 1.0))
    )
    f = np.asarray(freqs, dtype=float)
    t_ratio = t_k / _REF_T
    classical = 1.84e-11 * (_REF_P / p) * (t_ratio ** 0.5)
    oxygen = 0.01275 * np.exp(-2239.1 / t_k) * (fr_o + (f ** 2) / fr_o) ** (-1.0)
    nitrogen = 0.1068 * np.exp(-3352.0 / t_k) * (fr_n + (f ** 2) / fr_n) ** (-1.0)
    return 8.686 * (f ** 2) * (classical + (t_ratio ** (-2.5)) * (oxygen + nitrogen))


def iso_path_loss_db(
    freqs,
    distance_m: float,
    climate: str = DEFAULT_CLIMATE,
    rh_pct: float = None,
) -> np.ndarray:
    """A_db = −α(f)·d. Temperature and pressure stay with the climate.

    ``rh_pct`` None uses the preset's own relative humidity.
    """
    cond = climate_record(climate)["conditions"]
    rh = cond["relative_humidity_pct"] if rh_pct is None else float(rh_pct)
    alpha = _iso_alpha_db_per_m(
        freqs,
        cond["temperature_c"],
        rh,
        cond.get("pressure_kpa", _REF_P),
    )
    return -alpha * float(distance_m)


def peak_rh_pct(temperature_c: float) -> float:
    """RH percent where the 8–16 kHz mean loss peaks at this temperature."""
    t = float(temperature_c)
    _temp, rh = min(PEAK_RH_BY_T, key=lambda row: abs(row[0] - t))
    return float(rh)


def rh_pct_from_slider(humidity: float, climate: str = DEFAULT_CLIMATE):
    """Map the air-amount slider to relative humidity, percent.

    0 and below is off (None). Just above 0 is about ``RH_WET_PCT`` (90 %).
    ``HUMIDITY_NOMINAL`` (0.35) is the climate preset's RH. At 1.0 the RH is
    the treble-loss peak for that temperature. If the preset itself is drier
    than the peak, 0.35 sits on the peak too, so loss does not turn back.
    Right is drier, and drier (down to the peak) is more 8–16 kHz loss.
    """
    h = float(humidity)
    if not np.isfinite(h) or h <= 0.0:
        return None
    if h > 1.0:
        h = 1.0
    cond = climate_record(climate)["conditions"]
    preset = float(cond["relative_humidity_pct"])
    peak = peak_rh_pct(float(cond["temperature_c"]))
    anchor = preset if preset >= peak else peak
    if h <= HUMIDITY_NOMINAL:
        t = h / HUMIDITY_NOMINAL
        return RH_WET_PCT + t * (anchor - RH_WET_PCT)
    t = (h - HUMIDITY_NOMINAL) / (1.0 - HUMIDITY_NOMINAL)
    return anchor + t * (peak - anchor)


def _rbj_vec(p: dict) -> np.ndarray:
    return np.array(
        [float(p["f0"]), float(p["depth_db_per_m"]), float(p["f0_hi"]), float(p["depth_hi_db_per_m"])],
        dtype=float,
    )


def _params_of(rec: dict) -> np.ndarray:
    """Slope-1 RBJ corners and dB/m. Analytic ``params`` is the fallback."""
    if isinstance(rec.get("rbj"), dict):
        return _rbj_vec(rec["rbj"])
    return _rbj_vec(rec["params"])


def _index_presets() -> list:
    for root in preset_roots():
        path = root / "index.json"
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return list(data.get("presets") or [])
    return []


def _fit_freqs() -> np.ndarray:
    return np.geomspace(100.0, 16000.0, 200)


def _pair_db(freqs, sr: float, dist: float, params: np.ndarray) -> np.ndarray:
    """Realised dual RBJ (slope 1) in dB, the same shelves Play and Render run."""
    import early_field as ef

    f0, dep, f0h, deph = (float(x) for x in params)
    out = np.zeros(len(freqs), dtype=float)
    for corner, depth in ((f0, dep * dist), (f0h, deph * dist)):
        if abs(depth) < 1e-12:
            continue
        b0, b1, b2, a0, a1, a2 = ef.rbj_highshelf(sr, corner, depth, 1.0)
        z = np.exp(-2j * np.pi * freqs / sr)
        h = (b0 + b1 * z + b2 * z * z) / (a0 + a1 * z + a2 * z * z)
        out += 20.0 * np.log10(np.maximum(np.abs(h), 1e-20))
    return out


def _fit_score(params, temperature_c: float, rh_pct: float, pressure_kpa: float) -> float:
    f0, dep, f0h, deph = (float(x) for x in params)
    if f0 < 40.0 or f0h < f0 * 1.05 or f0h > 0.45 * 48000.0:
        return 1e6
    if dep > 0.0 or deph > 0.0 or dep < -4.0 or deph < -4.0:
        return 1e6
    freqs = _fit_freqs()
    vec = np.asarray(params, dtype=float)
    parts = []
    for dist in (10.0, 30.0):
        iso = -_iso_alpha_db_per_m(freqs, temperature_c, rh_pct, pressure_kpa) * dist
        parts.append(_pair_db(freqs, 48000.0, dist, vec) - iso)
    err = np.concatenate(parts)
    mx = float(np.max(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    return mx + 0.25 * rmse


def _nelder_mead(func, x0: np.ndarray, steps: np.ndarray, niter: int = 80) -> Tuple[np.ndarray, float]:
    n = len(x0)
    simplex = [np.array(x0, dtype=float)]
    for i in range(n):
        y = np.array(x0, dtype=float)
        y[i] += float(steps[i])
        simplex.append(y)
    vals = [func(x) for x in simplex]
    for _ in range(niter):
        order = list(np.argsort(vals))
        simplex = [simplex[i] for i in order]
        vals = [vals[i] for i in order]
        centroid = np.mean(simplex[:-1], axis=0)
        worst = simplex[-1]
        reflected = centroid + (centroid - worst)
        fr = func(reflected)
        if vals[0] <= fr < vals[-2]:
            simplex[-1], vals[-1] = reflected, fr
            continue
        if fr < vals[0]:
            expanded = centroid + 2.0 * (centroid - worst)
            fe = func(expanded)
            if fe < fr:
                simplex[-1], vals[-1] = expanded, fe
            else:
                simplex[-1], vals[-1] = reflected, fr
            continue
        contracted = centroid + 0.5 * (worst - centroid)
        fc = func(contracted)
        if fc < vals[-1]:
            simplex[-1], vals[-1] = contracted, fc
            continue
        for i in range(1, n + 1):
            simplex[i] = simplex[0] + 0.5 * (simplex[i] - simplex[0])
            vals[i] = func(simplex[i])
    best = int(np.argmin(vals))
    return simplex[best], float(vals[best])


def _fit_shelf_params(
    temperature_c: float, rh_pct: float, pressure_kpa: float, seed: np.ndarray,
) -> np.ndarray:
    """Two slope-1 RBJ shelves for one (T, RH, P). Cached. Numpy only."""
    key = (round(float(temperature_c), 3), round(float(pressure_kpa), 3), round(float(rh_pct), 3))
    hit = _FIT_CACHE.get(key)
    if hit is not None:
        return hit.copy()
    steps = np.array([200.0, 0.02, 600.0, 0.04], dtype=float)
    params, score = _nelder_mead(
        lambda x: _fit_score(x, key[0], key[2], key[1]),
        np.asarray(seed, dtype=float),
        steps,
        niter=140,
    )
    if score > 1.0:
        params = np.asarray(seed, dtype=float)
    params = np.asarray(params, dtype=float).copy()
    _FIT_CACHE[key] = params
    return params.copy()


def _interp_knots(rh: float, knots: list) -> np.ndarray:
    if rh <= knots[0][0]:
        return knots[0][1].copy()
    if rh >= knots[-1][0]:
        return knots[-1][1].copy()
    for i in range(len(knots) - 1):
        a, pa = knots[i]
        b, pb = knots[i + 1]
        if rh > b:
            continue
        if abs(rh - a) <= 0.02:
            return pa.copy()
        span = float(b - a)
        t = 0.0 if span <= 0.0 else (rh - a) / span
        f0 = float(np.exp(np.log(pa[0]) * (1.0 - t) + np.log(pb[0]) * t))
        f0h = float(np.exp(np.log(max(pa[2], 1.0)) * (1.0 - t) + np.log(max(pb[2], 1.0)) * t))
        dep = float(pa[1] * (1.0 - t) + pb[1] * t)
        deph = float(pa[3] * (1.0 - t) + pb[3] * t)
        return np.array([f0, dep, f0h, deph], dtype=float)
    return knots[-1][1].copy()


def _stored_rbj_knots(temperature_c: float, pressure_kpa: float) -> list:
    """Extra slope-1 shelves shipped beside the four climates (wet end, peak)."""
    out = []
    for root in preset_roots():
        path = root / "index.json"
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data.get("rbj_knots") or []:
            t = float(item.get("temperature_c", 1e9))
            p = float(item.get("pressure_kpa", _REF_P))
            if abs(t - float(temperature_c)) > 0.05 or abs(p - float(pressure_kpa)) > 0.05:
                continue
            out.append((float(item["relative_humidity_pct"]), _rbj_vec(item)))
        break
    return out


def _family_knots(temperature_c: float, pressure_kpa: float, fallback: dict) -> list:
    """Shipped shelves from the wet end down to the treble-loss peak.

    A missing end is fitted once and cached. The slider does not ask for an
    RH drier than the peak.
    """
    key = (round(float(temperature_c), 3), round(float(pressure_kpa), 3))
    hit = _FAMILY.get(key)
    if hit is not None:
        return hit
    knots = []
    for item in _index_presets():
        cond = item.get("conditions") or {}
        t = float(cond.get("temperature_c", 1e9))
        p = float(cond.get("pressure_kpa", _REF_P))
        if abs(t - key[0]) > 0.05 or abs(p - key[1]) > 0.05:
            continue
        rec = climate_record(str(item.get("id") or DEFAULT_CLIMATE))
        knots.append((float(rec["conditions"]["relative_humidity_pct"]), _params_of(rec)))
    if not knots:
        knots.append((float(fallback["conditions"]["relative_humidity_pct"]), _params_of(fallback)))
    for rh, params in _stored_rbj_knots(key[0], key[1]):
        if any(abs(k_rh - rh) < 0.05 for k_rh, _k_p in knots):
            continue
        knots.append((float(rh), params))
    for rh_end in (RH_WET_PCT, peak_rh_pct(key[0])):
        if any(abs(k_rh - rh_end) < 0.05 for k_rh, _k_p in knots):
            continue
        seed = min(knots, key=lambda k: abs(k[0] - rh_end))[1]
        fitted = _fit_shelf_params(key[0], rh_end, key[1], seed)
        knots.append((float(rh_end), fitted))
    knots.sort(key=lambda k: k[0])
    _FAMILY[key] = knots
    return knots


def shelf_params_for_rh(climate: str = DEFAULT_CLIMATE, rh_pct: float = None) -> np.ndarray:
    """(f0, depth dB/m, f0_hi, depth_hi dB/m). None keeps the stored preset."""
    rec = climate_record(climate)
    stored = _params_of(rec)
    if rh_pct is None:
        return stored
    rh = float(rh_pct)
    cond = rec["conditions"]
    knots = _family_knots(
        float(cond["temperature_c"]),
        float(cond.get("pressure_kpa", _REF_P)),
        rec,
    )
    for k_rh, params in knots:
        if abs(k_rh - rh) <= 0.02:
            return params.copy()
    return _interp_knots(rh, knots)


def shelf_specs(
    distance_m: float,
    mix: float,
    climate: str = DEFAULT_CLIMATE,
    sr: float = 48000.0,
    rh_pct: float = None,
) -> List[Tuple[float, float]]:
    """(f0 Hz, gain dB) for the two realtime RBJ shelves. Empty when the shelf is off.

    Gain is depth_db_per_m × distance × mix. Mix is the air-shelf fader.
    ``rh_pct`` None uses the stored climate shelf. Corners clamp to 0.45·sr.
    Gain clamps at −24 dB.
    """
    if float(distance_m) <= 0.0 or float(mix) <= 0.0 or float(sr) < 1.0:
        return []
    f0, dep, f0h, deph = shelf_params_for_rh(climate, rh_pct)
    cap_hz = 0.45 * float(sr)
    depth = float(distance_m) * float(mix)
    out: List[Tuple[float, float]] = []
    for f_hz, d_per_m in ((f0, dep), (f0h, deph)):
        corner = min(max(float(f_hz), 20.0), cap_hz)
        gain = max(float(d_per_m) * depth, -24.0)
        out.append((corner, gain))
    return out
