#!/usr/bin/env python3
"""Prototype (research only): per-band T60 of the tail from Surfaces materials via Sabine / Eyring /
Fitzroy, for the 6 x 3 x 8 m reference room and a few material assignments from the surfaces_fitter
presets (octave alpha tables, honesty ASSUMED_TEXTBOOK). No air term (lock: no air on the FDN return);
the with-air Sabine is shown only for reference. MODEL OUTPUT, NOT MEASUREMENT."""
import json, math
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
OUT = Path(__file__).resolve().parents[1]
PRE = Path('/workspace/handoff_surfaces_for_build/surfaces_fitter/presets')
def A(pid): return np.array(json.load(open(PRE / f'{pid}.json'))['absorb'])
fq = np.array([125, 250, 500, 1000, 2000, 4000, 8000.])
W, H, L = 6.0, 3.0, 8.0; V = W * H * L
faces = {'x': 2 * H * L, 'y': 2 * W * L, 'z': 2 * W * H}   # x = side walls, y = floor+ceiling, z = front/back
# air: m (1/m, intensity) ~ ISO 9613-1 at 20 C / 50 % RH, rounded, reference only
m_air = np.array([0.0001, 0.0003, 0.0006, 0.0010, 0.0019, 0.0057, 0.0200])
def t60(assign):
    S = sum(faces.values()); aS = {}
    # side walls: A/C; floor E + ceiling F split; front/back B/D
    aS['x'] = A(assign['sides']) * faces['x']
    aS['y'] = 0.5 * faces['y'] * (A(assign['floor']) + A(assign['ceiling']))
    aS['z'] = 0.5 * faces['z'] * (A(assign['ahead']) + A(assign['behind']))
    Atot = sum(aS.values()); am = Atot / S
    sab = 0.161 * V / Atot
    sab_air = 0.161 * V / (Atot + 4 * m_air * V)
    ey = 0.161 * V / (-S * np.log(1 - am))
    fitz = np.zeros_like(fq)
    for k, Sk in faces.items():
        ak = aS[k] / Sk
        fitz += (Sk / S) * 0.161 * V / (-S * np.log(1 - ak))
    return {'sabine': sab, 'sabine_with_air_ref_only': sab_air, 'eyring': ey, 'fitzroy': fitz, 'alpha_mean': am}
cases = {
  'plaster room, parquet floor, plaster ceiling': dict(sides='plaster_smooth', floor='wood_parquet', ceiling='plaster_smooth', ahead='plaster_smooth', behind='plaster_smooth'),
  'same + tile ceiling': dict(sides='plaster_smooth', floor='wood_parquet', ceiling='acoustic_ceiling_tile', ahead='plaster_smooth', behind='plaster_smooth'),
  'studio: absorber sides, carpet, tile ceiling': dict(sides='absorber_panel_2in', floor='carpet_on_concrete', ceiling='acoustic_ceiling_tile', ahead='gypsum_painted', behind='plywood_panel'),
}
res = {}; fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
for a, (lab, asg) in zip(ax, cases.items()):
    r = t60(asg); res[lab] = {k: np.round(v, 3).tolist() for k, v in r.items()}; res[lab]['assignment'] = asg
    for k, st in (('sabine', 'C0-o'), ('eyring', 'C1-s'), ('fitzroy', 'C2-^'), ('sabine_with_air_ref_only', 'k:')):
        a.semilogx(fq, r[k], st, label=k)
    a.set_title(lab, fontsize=9); a.set_xlabel('Hz'); a.set_ylabel('T60 s'); a.grid(alpha=.3, which='both'); a.legend(fontsize=7)
    # normalised shape re 1 kHz (what a decay-lock dial would keep)
    res[lab]['eyring_shape_re_1k'] = np.round(r['eyring'] / r['eyring'][3], 3).tolist()
fig.suptitle('6 x 3 x 8 m: tail T60 per octave from Surfaces presets (MODEL, presets ASSUMED_TEXTBOOK)')
fig.tight_layout(); fig.savefig(OUT / 'plots' / 'wall_tone_t60.png', dpi=90)
json.dump({'octave_hz': fq.tolist(), 'room': [W, H, L], 'cases': res}, open(OUT / 'proto' / 'wall_tone_results.json', 'w'), indent=1)
for lab, r in res.items():
    print(lab); [print('  ', k, r[k]) for k in ('alpha_mean', 'sabine', 'eyring', 'fitzroy', 'eyring_shape_re_1k')]
