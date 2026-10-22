"""Fit the v1 radiation model to a Dataset (DI-normalised dB loss, direction hold-out)."""
from __future__ import annotations

import numpy as np
from scipy.optimize import differential_evolution, least_squares

from . import model as M

FLOOR_DB = 40.0      # data clipped at (band max - 35 dB) so nulls don't dominate (ASSUMED)
DI_WEIGHT = 0.5     # weight of the per-band DI-match residual (ASSUMED)
HOLDOUT_MOD = 5      # every 5th direction (index % 5 == 2) is hold-out (ASSUMED split)


def di_normalise(L_db, w):
    """dB relative to the power average over the sphere, per band. L_db (D,F)."""
    p = np.sum(w[:, None] * 10 ** (L_db / 10), 0)
    return L_db - 10 * np.log10(np.maximum(p, 1e-30))


def prepare(ds):
    ok = ds.band_ok
    L = ds.mag_db[:, ok].copy()
    L = np.maximum(L, L.max(0, keepdims=True) - FLOOR_DB)
    X = di_normalise(L, ds.weights)
    idx = np.arange(len(ds.dirs))
    hold = (idx % HOLDOUT_MOD) == 2
    return ds.freqs[ok], X, hold


def model_norm(params, ds, freqs):
    R = M.relative_db(params, ds.dirs, freqs)
    R = np.maximum(R, R.max(0, keepdims=True) - FLOOR_DB)
    return di_normalise(R, ds.weights)


def rmse(E, w):
    return float(np.sqrt(np.sum(w[:, None] * E ** 2) / (np.sum(w) * E.shape[1])))


def fit_dataset(ds, maxiter=120, popsize=14, seed=7, fixed=None, workers=1):
    freqs, X, hold = prepare(ds)
    train = ~hold
    wt = ds.weights[train]
    names = list(M.PARAM_NAMES)
    fixed = dict(fixed or {})
    free = [n for n in names if n not in fixed]
    # lp_order is a discrete, always-fixed field
    bounds = [M.PARAM_BOUNDS[n] for n in free]

    def unpack(x):
        p = dict(fixed)
        p.update({n: float(v) for n, v in zip(free, x)})
        return p

    fr = int(np.argmax(ds.dirs[:, 0]))   # data front axis -> DI term

    def resid(x):
        p = unpack(x)
        Mfull = model_norm(p, ds, freqs)
        E = (Mfull - X)[train]
        r = (E * np.sqrt(wt[:, None] / wt.sum() / E.shape[1])).ravel()
        # DI-match term (on-axis vs power average): keeps FDN-inject weighting honest (ASSUMED weight 0.5)
        r = np.concatenate([r, DI_WEIGHT * (Mfull[fr] - X[fr]) / np.sqrt(len(freqs))])
        prior = np.array([
            0.3 * p.get("lp_mix", 0.0),                        # shelves first, soft LP residual
            0.01 * (abs(p.get("aim_az", 0.0)) + abs(p.get("aim_el", 0.0))) / 10.0,
            0.1 * (abs(p.get("b_ud", 0.0)) + abs(p.get("b_lr", 0.0))),
        ])
        return np.concatenate([r, prior])

    def loss(x):
        r = resid(x)
        return float(np.sum(r ** 2))

    res = differential_evolution(loss, bounds, maxiter=maxiter, popsize=popsize, seed=seed, tol=1e-7,
                                 polish=False, updating="deferred" if workers != 1 else "immediate",
                                 workers=workers)
    lo = np.array([b[0] for b in bounds]); hi = np.array([b[1] for b in bounds])
    try:
        ls = least_squares(resid, np.clip(res.x, lo, hi), bounds=(lo, hi), max_nfev=400)
        x = ls.x if loss(ls.x) <= res.fun else res.x
    except Exception:
        x = res.x
    p = unpack(x)
    Mn = model_norm(p, ds, freqs)
    E = Mn - X
    out = {
        "params": p,
        "rmse_train_db": rmse(E[train], ds.weights[train]),
        "rmse_holdout_db": rmse(E[hold], ds.weights[hold]),
        "rmse_per_band_db": {f"{f:g}": rmse(E[:, j:j + 1], ds.weights) for j, f in enumerate(freqs)},
        "n_dirs": int(len(ds.dirs)), "n_train": int(train.sum()), "n_holdout": int(hold.sum()),
        "fit_bands_hz": [float(freqs[0]), float(freqs[-1])], "n_bands": int(len(freqs)),
        "free_params": free, "fixed_params": fixed,
    }
    # data DI at reference axis (+x) vs model DI at its own axis
    fr = int(np.argmax(ds.dirs[:, 0]))
    out["di_data_db"] = {f"{f:g}": float(X[fr, j]) for j, f in enumerate(freqs)}
    out["di_model_db"] = {f"{f:g}": float(v) for f, v in zip(freqs, M.directivity_index_db(p, freqs))}
    return out


def fit_diffuse_filter(params, fmin=50.0, fmax=16000.0):
    """Power-averaged (diffuse-field) response relative to on-axis, fitted by gain + RBJ high shelf.
    This is the FDN-inject weighting (one filter per source, shared by all lines)."""
    f = np.geomspace(fmin, fmax, 48)
    target = -M.directivity_index_db(params, f)   # dB, <= 0 for directional sources

    def r(x):
        g, f0, gh = x
        return (g + M.biquad_mag_db(M.rbj_high_shelf(f0, gh, 0.7), f)) - target
    lo_b, hi_b = np.array([-40.0, 100.0, -40.0]), np.array([3.0, 12000.0, 6.0])
    x0 = np.clip([target[0], 1500.0, target[-1] - target[0]], lo_b + 1e-6, hi_b - 1e-6)
    ls = least_squares(r, x0, bounds=(lo_b, hi_b))
    g, f0, gh = ls.x
    return {"gain_db": float(g), "shelf_f0": float(f0), "shelf_gain_db": float(gh), "shelf_s": 0.7,
            "fit_rmse_db": float(np.sqrt(np.mean(r(ls.x) ** 2))),
            "target_db": {f"{fi:.0f}": float(t) for fi, t in zip(f[::6], target[::6])}}
