#!/usr/bin/env python3
"""K1b: every stereo preset in app.js MIC_SETUPS (yaw signs as shipped) vs negated yaws.
For a source 2 m left of the stand (x = 1 m, stand at x = 3 m, W = 6 m): capsule gain of the capsule NEARER the
source (L, lower X) minus the far one (R), in dB, through early_field.direction_angles + capsule_gain.
Positive = near capsule louder (level cue agrees with the time cue)."""
import math, re, json
from common import params, CLIENT_ORTF, dump, SW
from early_field import direction_angles, direct_field_from_params, MicStand, capsule_gain
js = (SW / 'static/js/app.js').read_text()
rows = {}
for m in re.finditer(r'\n    (\w+):\s*\{ space: ([0-9.]+), toe_half_deg: ([0-9.]+),[\s\S]*?pattern_l: "(\w+)"[\s\S]*?pattern_r: "(\w+)"[\s\S]*?yaw_l_deg: (-?[0-9.]+), yaw_c_deg: -?[0-9.]+, yaw_r_deg: (-?[0-9.]+) \}', js):
    name, space, toe, pl, pr, yl, yr = m.groups()
    out = {}
    for label, (a, b) in (('shipped', (float(yl), float(yr))), ('negated', (-float(yl), -float(yr)))):
        p = params(**dict(CLIENT_ORTF, space=float(space), toe_half_deg=float(toe), pattern_l=pl, pattern_r=pr, yaw_l_deg=a, yaw_r_deg=b, sx=1.0))
        prep = direct_field_from_params(p)
        st = MicStand.from_prepare(prep, pattern_l=pl, pattern_r=pr, yaw_l_deg=a, yaw_r_deg=b)
        g = []
        for pos, yaw, pat in ((prep.mic_left, st.mlalr, pl), (prep.mic_right, st.mralr, pr)):
            th, _ = direction_angles(pos, prep.source, yaw)
            g.append(abs(capsule_gain(th, pattern=pat)))
        out[label] = {'yaw_l': a, 'yaw_r': b, 'gain_L': round(g[0], 3), 'gain_R': round(g[1], 3),
                      'near_minus_far_db': round(20 * math.log10(max(g[0], 1e-6) / max(g[1], 1e-6)), 2),
                      'L_x': round(prep.mic_left[0], 3), 'R_x': round(prep.mic_right[0], 3)}
    rows[name] = dict(pattern=[pl, pr], **out)
dump(rows, 'k1b_all_presets.json')
for k, v in rows.items():
    print(f"{k:11s} {v['pattern']} shipped L{v['shipped']['yaw_l']:+.0f}/R{v['shipped']['yaw_r']:+.0f}: near-far {v['shipped']['near_minus_far_db']:+6.2f} dB | negated: {v['negated']['near_minus_far_db']:+6.2f} dB")
