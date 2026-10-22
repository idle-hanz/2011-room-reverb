"""Physical treatment model and AUTO-TREAT (box prototype).
Panels are tunable resonant absorbers placed on a face with a coverage fraction; broadband porous panels
come from the app library (modelled porous + air-gap presets). Each face card then carries alpha(f) as a
continuous function, which feeds the room target and the directional per-line decay (surfdecay.py)."""
import math, copy, numpy as np
import rooms as R, surfdecay as SD

C = 343.0
def modes(W, H, L, fmax=300.0):
    out = []
    for nx in range(0, 12):
        for ny in range(0, 12):
            for nz in range(0, 12):
                if nx == ny == nz == 0: continue
                f = C / 2 * math.sqrt((nx / W) ** 2 + (ny / H) ** 2 + (nz / L) ** 2)
                if f <= fmax:
                    k = sum(v > 0 for v in (nx, ny, nz))
                    out.append((f, (nx, ny, nz), {1: "axial", 2: "tangential", 3: "oblique"}[k]))
    return sorted(out)

def schroeder_hz(T, V):
    return 2000.0 * math.sqrt(T / V)          # Schroeder 1962 / Kuttruff (VERIFIED standard form)

def membrane_f0(m_kg_m2, d_m, porous_fill=True):
    return (50.0 if porous_fill else 60.0) / math.sqrt(m_kg_m2 * d_m)   # Cox & D'Antonio eqs 7.9/7.10

def helmholtz_f0(eps, t_m, a_m, d_m, delta=0.85):
    return C / (2 * math.pi) * math.sqrt(eps / ((t_m + 2 * delta * a_m) * d_m))  # Cox & D'Antonio eq 7.4/7.6

def resonant_alpha(f, f0, q, amax):
    """Single-resonance absorption curve (ASSUMED shape; peak amax at f0, -3 dB bandwidth f0/q)."""
    f = np.asarray(f, float)
    return amax / (1.0 + (q * (f / f0 - f0 / f)) ** 2)

# membrane builds: (sheet, surface mass kg/m2), cavity depths searched 50-300 mm
SHEETS = [("3 mm hardboard", 2.7), ("6 mm plywood", 3.6), ("9 mm plywood", 5.4), ("12 mm MDF", 9.0), ("18 mm MDF", 13.5), ("2 x 12.5 mm plasterboard", 21.0)]

def design_membrane(f0):
    best = None
    for name, m in SHEETS:
        d = (50.0 / f0) ** 2 / m
        if 0.05 <= d <= 0.30:
            cand = (abs(d - 0.12), name, m, d)
            best = min(best, cand) if best else cand
    if not best:
        return None
    _, name, m, d = best
    return dict(type="membrane", f0=round(membrane_f0(m, d), 1), q=2.0, amax=0.6,
                build=f"{name} ({m} kg/m2) on {round(d*1000)} mm cavity, mineral wool fill", m=m, d=d)

def design_helmholtz(f0):
    # perforated 12 mm board, 6 mm holes; cavity 50-200 mm; open area 0.5-20 %
    t, a = 0.012, 0.003
    for d in (0.10, 0.15, 0.20, 0.05):
        eps = ((2 * math.pi * f0 / C) ** 2) * (t + 2 * 0.85 * a) * d
        if 0.005 <= eps <= 0.20:
            return dict(type="helmholtz", f0=round(helmholtz_f0(eps, t, a, d), 1), q=3.0, amax=0.7,
                        build=f"12 mm board, 6 mm holes, {eps*100:.1f} % open, {round(d*1000)} mm cavity with wool", eps=eps, d=d)
    return None

def alpha_fn(card):
    """Continuous alpha(f) of a face: base material, porous coverage and panels (area-weighted)."""
    hz = np.asarray(card["absorb_hz"], float); a = np.asarray(card["absorb"], float)
    tr = card.get("treatment", [])
    def fn(f):
        f = np.asarray(f, float)
        base = np.interp(np.log(f), np.log(hz), a)
        tot_cov = sum(t["coverage"] for t in tr)
        out = (1 - tot_cov) * base
        for t in tr:
            if t["type"] == "porous":
                m = R.mat(t["material"]); out = out + t["coverage"] * np.interp(np.log(f), np.log(np.asarray(m["absorb_hz"], float)), np.asarray(m["absorb"], float))
            else:  # resonant panel: its face is still the panel sheet (reflective off-resonance, ~0.05)
                out = out + t["coverage"] * np.maximum(resonant_alpha(f, t["f0"], t["q"], t["amax"]), 0.05)
        return np.clip(out, 0.0, 0.99)
    return fn

def makivirta_target(f, t_mid, air_ratio=None):
    """EQ_PLAN R1.3 target: flat T_mid (500 Hz-2 kHz mean), +0.2 s linear on log f from 300 Hz down to 50 Hz.
    Above 2 kHz the target follows air alone (a perfect room still loses treble to air)."""
    f = np.asarray(f, float)
    T = np.full_like(f, t_mid)
    lo = f < 300.0
    T[lo] += 0.2 * np.clip(np.log(300.0 / f[lo]) / np.log(300.0 / 50.0), 0, 1)
    if air_ratio is not None:
        hi = f > 2000.0; T[hi] = T[hi] * air_ratio(f[hi]) / air_ratio(np.array([2000.0]))[0]
    return T

def ebu_tm(V):
    return 0.25 * (V / 100.0) ** (1 / 3)           # EBU Tech 3276 / ITU-R BS.1116 (VERIFIED), control rooms

THIRD = 1000.0 * 2.0 ** (np.arange(-14, 10) / 3.0)   # 40 Hz .. 8 kHz

POROUS = ["absorber_panel_1in_gap1in", "absorber_panel_2in", "absorber_panel_2in_gap2in", "absorber_panel_4in_gap4in"]

def auto_treat(W, H, L, surfaces, humidity, t_mid, max_panels=4, porous=None):
    """Tries each porous option and keeps the one closest to the target over 200 Hz-8 kHz."""
    best = None
    for pm in ([porous] if porous else POROUS):
        r = _auto_treat(W, H, L, surfaces, humidity, t_mid, max_panels, pm)
        band = (THIRD >= 200) & (THIRD <= 8000)
        err = float(np.sqrt(np.mean(np.log(r[3][band] / r[4][band]) ** 2)))
        r[1].insert(0, dict(kind="choice", porous=pm, rms_log_err_200_8k=round(err, 3)))
        if best is None or err < best[0]:
            best = (err, r)
    return best[1]

def _auto_treat(W, H, L, surfaces, humidity, t_mid, max_panels, porous):
    """Greedy auto-treat. 1) broadband porous coverage on ceiling (F) and rear wall (D), then side walls,
    until the 500 Hz-2 kHz T meets t_mid; 2) resonant panels at the worst low-frequency excess against the
    Makivirta target (1/3-octave, 40-500 Hz), sized to close it, up to max_panels (the 4-resonance budget).
    Returns treated surfaces, plan rows, and before/after T on THIRD."""
    s = copy.deepcopy(surfaces)
    for k in s: s[k].setdefault("treatment", [])
    def T_of(ss, f=THIRD):
        cards = {k: dict(ss[k], absorb_fn=alpha_fn(ss[k])) for k in ss}
        return SD.room_target(W, H, L, cards, humidity, f)
    before = T_of(s)
    plan = []
    # 1) broadband, AXIS-BALANCED: one common coverage on ceiling F, rear wall D and both side walls A/C
    #    (first-reflection points, cloud, rear wall), so every axis pair carries absorption. Treating only one
    #    face per axis leaves the untreated axis ringing (Fitzroy 1959 / Arau 1988 non-diffuse decay): on the
    #    box this showed as a double slope (EDT/T30 ~0.25). Front wall B is added only if 80 % is not enough.
    mid = (THIRD >= 500) & (THIRD <= 2000)
    for faces in (["F", "D", "A", "C"], ["F", "D", "A", "C", "B"]):
        trs = []
        for face in faces:
            tr = {"type": "porous", "material": porous, "coverage": 0.8, "face": face}
            s[face]["treatment"].append(tr); trs.append(tr)
        if float(np.mean(T_of(s)[mid])) > t_mid and len(faces) == 4:
            for face in faces: s[face]["treatment"].pop()
            continue
        lo, hi = 0.0, 0.8
        for _ in range(30):
            c = 0.5 * (lo + hi)
            for tr in trs: tr["coverage"] = c
            if float(np.mean(T_of(s)[mid])) > t_mid: lo = c
            else: hi = c
        for tr in trs: tr["coverage"] = round(hi, 3)
        for face in faces:
            plan.append(dict(face=face, kind="broadband", build=R.mat(porous)["display_name"], coverage=round(hi, 3)))
        break
    # 2) panels for low-frequency excess
    V = W * H * L
    m = lambda f: SD.air_db_per_m(f, humidity) / (10 * math.log10(math.e))
    A_mid = 0.161 * V / t_mid
    air_ratio = lambda f: (0.161 * V / (A_mid + 4 * m(f) * V)) / t_mid
    tgt = makivirta_target(THIRD, t_mid, air_ratio)
    lf = (THIRD >= 40) & (THIRD <= 500)
    n_pan = 0
    for _ in range(3 * max_panels):
        if n_pan >= max_panels: break
        T = T_of(s); ex = np.where(lf, T / tgt, 0)
        i = int(np.argmax(ex))
        if ex[i] < 1.10: break                    # within 10 % (EBU-style tolerance band)
        f0 = float(THIRD[i])
        pan = (design_membrane(f0) if f0 < 180 else None) or design_helmholtz(f0)
        if pan is None:
            lf[i] = False; continue
        # place on the face pair whose axis carries the strongest axial mode near f0, else rear wall
        md = [m for m in modes(W, H, L, 400) if m[2] == "axial" and abs(math.log(m[0] / f0)) < 0.25]
        prefs = ["D", "F", "A", "C", "B", "E"]  # floor last (riser)
        if md:
            ax = int(np.argmax(md[0][1])); first = {0: ["A", "C"], 1: ["F", "A", "C"], 2: ["D", "B"]}[ax]
            prefs = first + [x for x in prefs if x not in first]
        used = lambda k: sum(t["coverage"] for t in s[k]["treatment"])
        face = next((k for k in prefs if 0.9 - used(k) >= 0.1), None)   # real faces only hold 90 % treatment
        if face is None:
            break
        free = 0.9 - used(face)
        pan = dict(pan, coverage=0.0, face=face, target_hz=round(f0, 1),
                   modes_near=[f"{m[0]:.0f} Hz {m[1]}" for m in md][:3])
        s[face]["treatment"].append(pan)
        lo, hi = 0.0, min(0.5, free)
        for _ in range(25):
            pan["coverage"] = 0.5 * (lo + hi)
            if T_of(s)[i] / tgt[i] > 1.0: lo = pan["coverage"]
            else: hi = pan["coverage"]
        pan["coverage"] = round(hi, 3); n_pan += 1
        S = SD.face_areas(W, H, L)[face]
        plan.append(dict(face=face, kind=pan["type"], f0=pan["f0"], build=pan["build"], coverage=pan["coverage"],
                         area_m2=round(pan["coverage"] * S, 2), target_hz=pan["target_hz"], modes_near=pan["modes_near"]))
    after = T_of(s)
    return [s, plan, before, after, tgt]
