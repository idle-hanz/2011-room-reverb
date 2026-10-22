# Pass-2 signal specs -> arrays (generated on the fly inside the renderer; deterministic).
import numpy as np
import siglib as S
SR = S.SR
def make(sp):
    k = sp["kind"]
    if k == "burst":
        f = sp.get("f", 1000.0); parts = [(sp["probe_db"], sp["pre_s"]), (sp["burst_db"], sp["burst_s"]), (sp["probe_db"], sp["tail_s"])]
        n = [int(round(d * SR)) for _, d in parts]; N = sum(n); t = np.arange(N) / SR
        a = np.concatenate([np.full(m, S.db2a(L)) for (L, _), m in zip(parts, n)])
        return a * np.sin(2 * np.pi * f * t)
    if k == "quad":
        x, i0, i1 = S.quad_step(sp["fc"], sp["lo_db"], sp["hi_db"], sp.get("t_step", 0.5), sp.get("t_hi", 0.3), sp.get("t_after", 0.7), sp.get("phase", 0.0))
        return x
    if k == "fstair":
        return S.freq_stair(sp["freqs"], sp["level_db"], sp["step_s"])
    if k == "link":
        n1 = int(sp["on_s"] * SR); n0 = int(sp["off_s"] * SR); N = n0 + n1 + n0; t = np.arange(N) / SR
        L = np.zeros(N); L[n0:n0 + n1] = S.db2a(sp["l_db"]) * np.sin(2 * np.pi * 1000.0 * t[n0:n0 + n1])
        R = S.db2a(sp["r_db"]) * np.sin(2 * np.pi * 3000.0 * t)
        return np.stack([L, R])
    raise ValueError(k)
