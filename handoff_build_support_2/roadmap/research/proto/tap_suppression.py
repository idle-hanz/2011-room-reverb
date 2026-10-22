"""How many of the 32 fixed LIVE_32 taps sit > 20 dB down at the capsules, per mic setup?
Also: if we picked the loudest 32 out of the 128-image grid, how much early energy would we gain?"""
import sys, math, json, numpy as np
SW = sys.argv[1]; sys.path[:0] = [SW, SW + '/engine']
from early_field import compute_taps, MicStand, geometric_level
room = (6.0, 3.0, 8.0); src = (2.6, 1.2, 4.75)          # app defaults (app.js state)
def st(**kw):
    base = dict(cx=3.0, cy=1.5, cz=1.5, space=0.17, car_omni=1.0)
    base.update(kw); return MicStand(**base)
r = math.radians
SETUPS = {
  'ORTF cardioids ±55°, 17 cm': st(mlalr=r(-55), mralr=r(55)),
  'XY cardioids ±45°': st(space=0.0, mlalr=r(-45), mralr=r(45)),
  'Blumlein fig-8 ±45°': st(space=0.0, mlalr=r(-45), mralr=r(45), pattern_l='fig8', pattern_r='fig8', family_l='bi', family_r='bi', polar_l=1.0, polar_r=1.0),
  'MS: cardioid M + fig-8 S (ms_decode)': st(space=0.0, ms_decode=True, mlalr=r(-90), mralr=r(90)),
  'MS: omni M + fig-8 S (ms_decode)': st(space=0.0, ms_decode=True, mlalr=r(-90), mralr=r(90), pattern_c='omni', family_c='omni', polar_c=0.0),
  'Fig-8 side pair L/R ±90° (2-mic S)': st(space=0.0, mlalr=r(-90), mralr=r(90), pattern_l='fig8', pattern_r='fig8', family_l='bi', family_r='bi', polar_l=1.0, polar_r=1.0),
}
def db(x): return 20 * math.log10(max(abs(x), 1e-12))
out = {}
for name, s in SETUPS.items():
    t32 = compute_taps(room, src, s, grid='32')
    t128 = compute_taps(room, src, s, grid='128')
    row = {}
    for ch in ('l', 'r'):
        lev = np.array([getattr(t, 'level_' + ch) for t in t32])
        geo = np.array([abs(geometric_level(getattr(t, 'distance_' + ch))) * abs(getattr(t, 'shelf_' + ch) or 1.0) for t in t32])
        g = np.abs(lev) / np.maximum(geo, 1e-12)  # pattern (decode) gain only, distance removed
        pk = np.max(np.abs(lev))
        row['pattern_gain_below_-20dB_' + ch] = int(np.sum(g < 0.1))
        row['level_20dB_below_loudest_' + ch] = int(np.sum(np.abs(lev) < pk * 0.1))
    both = [t for t in t32 if abs(t.level_l) < 0.1 * max(abs(x.level_l) for x in t32) and abs(t.level_r) < 0.1 * max(abs(x.level_r) for x in t32)]
    row['wasted_on_both_capsules'] = len(both)
    # energy captured: fixed 32 vs loudest 32 of the 128 grid (sum of squares over L and R)
    e = lambda ts: sum(t.level_l ** 2 + t.level_r ** 2 for t in ts)
    best = sorted(t128, key=lambda t: -(t.level_l ** 2 + t.level_r ** 2))[:32]
    fixed_keys = {tuple(t.n) for t in t32}
    row['early_energy_gain_dB_if_loudest32_of_128'] = round(10 * math.log10(e(best) / e(t32)), 2)
    row['overlap_loudest32_with_LIVE_32'] = len([t for t in best if tuple(t.n) in fixed_keys])
    out[name] = row; print(name, row)
json.dump(out, open('tap_suppression.json', 'w'), indent=1)
