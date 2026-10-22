#!/usr/bin/env python3
"""K2 repro: Structure air 1-pole corner fc = Wet/Dis (early_field.air_abs_cutoff_hz) and what the
air_lp mix does with it. Uses the real functions (Render: apply_air_absorption; Play: _live_air_for_distance)."""
import math
import numpy as np
from common import dump, SW
from early_field import air_abs_wet_from_humidity, air_abs_cutoff_hz, one_pole_g_from_fc, apply_air_absorption
from render_pipeline import _live_air_for_distance
SR = 48000
res = {'rows': []}
def one_pole_mix_db(fc, lp, f):
    g = one_pole_g_from_fc(fc, SR); z = np.exp(-1j * 2 * np.pi * f / SR)
    H = g / (1 - (1 - g) * z)
    return 20 * np.log10(np.abs((1 - lp) + lp * H))
F = np.array([50.0, 100.0, 1000.0, 10000.0])
for hum in (0.35, 0.5, 1.0):
    wet = air_abs_wet_from_humidity(hum)
    for d in (1.0, 3.0, 10.0, 30.0):
        fc = air_abs_cutoff_hz(d, wet)
        row = {'humidity': hum, 'wet': wet, 'd_m': d, 'fc_hz': fc,
               'mix0.25_db_at_50_100_1k_10k': [round(v, 2) for v in one_pole_mix_db(fc, 0.25, F)],
               'full_lp_db_at_50_100_1k_10k': [round(v, 2) for v in one_pole_mix_db(fc, 1.0, F)]}
        res['rows'].append(row)
# Render filter on an impulse vs the analytic mix (sanity: the code does what the formula says), shelf off
x = np.zeros(8192); x[0] = 1
y = apply_air_absorption(x.copy(), 3.0, SR, 0.5, air_lp=0.25, air_shelf=0.0)
Y = np.abs(np.fft.rfft(y)); ff = np.fft.rfftfreq(len(y), 1 / SR)
res['render_impulse_db_at_1k_10k'] = [float(20 * np.log10(np.interp(f, ff, Y))) for f in (1000.0, 10000.0)]
g_play, lp_play, _ = _live_air_for_distance(3.0, SR, 0.5, 0.25, 1.0)
res['play_air_g_equals_render'] = abs(g_play - one_pole_g_from_fc(air_abs_cutoff_hz(3.0, 400.0), SR)) < 1e-12
res['structure_note'] = "structure-screenshots-batch-4-full.md:255  'Ins: In, Dis, Met -> Humidity; filter P <- Log(Humidity/Dis)'  (VERIFIED note; unit of Dis and role of 'Met' UNKNOWN)"
dump(res, 'k2_air_corner.json')
for r in res['rows']:
    if r['humidity'] == 0.5: print(r)
print('Render impulse (3 m, hum 0.5, air_lp 0.25, shelf off) dB at 1k/10k:', [round(v, 2) for v in res['render_impulse_db_at_1k_10k']])
print('Play uses the same g as Render:', res['play_air_g_equals_render'])
