#!/usr/bin/env python3
"""K1 repro: default ORTF yaws (L -55, R +55; app.js state) aim the L capsule (lower X) toward +X.
Checks (a) look vectors, (b) cardioid capsule gains for a source at x = 1 m and x = 5 m through the real
early_field code, (c) the real Render direct-only IR: which speaker is louder/earlier. Then repeats with
the proposed fix (L +55, R -55)."""
import math, subprocess, json, sys
import numpy as np
from common import A, params, CLIENT_ORTF, dump, SW
from early_field import look_vector, direction_angles, direct_field_from_params, MicStand, capsule_gain, angles_from_toe_half_deg
res = {}
def gains(p):
    prep = direct_field_from_params(p)
    st = MicStand.from_prepare(prep, pattern_l=p.get('pattern_l'), pattern_r=p.get('pattern_r'), yaw_l_deg=p.get('yaw_l_deg'), yaw_r_deg=p.get('yaw_r_deg'))
    out = {}
    for name, pos, yaw in (('L', prep.mic_left, st.mlalr), ('R', prep.mic_right, st.mralr)):
        th, _ = direction_angles(pos, prep.source, yaw)
        out[name] = {'pos_x': pos[0], 'yaw_deg': math.degrees(yaw), 'look': look_vector(yaw), 'theta_deg': math.degrees(th),
                     'cardioid_gain': capsule_gain(th, pattern='cardioid')}
    return out
for label, yaws in (('current_default', dict(yaw_l_deg=-55.0, yaw_r_deg=55.0)), ('proposed_fix', dict(yaw_l_deg=55.0, yaw_r_deg=-55.0))):
    for sx in (1.0, 5.0):
        p = params(**dict(CLIENT_ORTF, **yaws, sx=sx))
        res[f'{label}_sx{sx}'] = gains(p)
res['angles_from_toe_half_deg(55)'] = [math.degrees(v) for v in angles_from_toe_half_deg(55.0)]
# (c) real Render, direct only, colour bypass, 48 kHz
R = '/workspace/build_support_2/1_iir_colour_verification/tools/render_ir_impl.py'
def render(sx, yl, yr, **mix):
    body = dict(CLIENT_ORTF, yaw_l_deg=yl, yaw_r_deg=yr, sx=sx, **mix)
    f = f'/tmp/k1_{sx}_{yl}.f32'
    subprocess.run([sys.executable, R, str(SW), json.dumps(body), f, '400', '48000'], check=True, capture_output=True)
    x = np.fromfile(f, np.float32).reshape(-1, 2).astype(float)
    X = np.abs(np.fft.rfft(x, axis=0)) ** 2; ff = np.fft.rfftfreq(len(x), 1 / 48000); hf = (ff >= 4000) & (ff <= 16000)
    e = (x ** 2).sum(0)
    return {'L_minus_R_level_db': float(10 * np.log10(e[0] / e[1])),
            'L_minus_R_4k_16k_db': float(10 * np.log10(X[hf, 0].sum() / X[hf, 1].sum())),
            'arrival_L_minus_R_samples': int(np.argmax(np.abs(x[:, 0])) - np.argmax(np.abs(x[:, 1])))}
MIXES = {'direct_bypass': dict(early_wet=0.0, fdn_wet=0.0, direct_wet=1.0, colour_mode='BYPASS'),
         'direct_measured_colour': dict(early_wet=0.0, fdn_wet=0.0, direct_wet=1.0, colour_mode='MEASURED_SHELF'),
         'early_only_bypass': dict(early_wet=1.0, fdn_wet=0.0, direct_wet=0.0, colour_mode='BYPASS')}
for mname, mix in MIXES.items():
    for sx in (1.0, 5.0):
        res[f'render_{mname}_current_sx{sx}'] = render(sx, -55.0, 55.0, **mix)
        res[f'render_{mname}_fix_sx{sx}'] = render(sx, 55.0, -55.0, **mix)
dump(res, 'k1_ortf_crossed.json')
c = res['current_default_sx1.0']; f = res['proposed_fix_sx1.0']
print(f"source x=1 m (left of stand at x=3): current L gain {c['L']['cardioid_gain']:.3f} vs R {c['R']['cardioid_gain']:.3f}; fix L {f['L']['cardioid_gain']:.3f} vs R {f['R']['cardioid_gain']:.3f}")
print('L look vector (current):', [round(v, 3) for v in c['L']['look']], ' (+x = toward the right wall per UI "+X right")')
for k in res:
    if k.startswith('render_'): print(k, res[k])
