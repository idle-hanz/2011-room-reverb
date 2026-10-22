#!/usr/bin/env python3
"""K4 repro: early field is off out of the box.
(a) server DEFAULTS early_wet; (b) client app.js: state.early_wet/fader_early and the heardMix fader law,
executed in node on the real app.js functions; (c) Render IR with defaults vs early_wet=1: early bus contributes
nothing by default, and the FDN part (images still excite the FDN - lock) is unchanged."""
import json, re, subprocess, sys
from pathlib import Path
import numpy as np
from common import A, dump, SW, CLIENT_ORTF
res = {'server_DEFAULTS_early_wet': A.DEFAULTS.get('early_wet')}
js = (SW / 'static/js/app.js').read_text()
m_state = re.search(r'early_wet: ([0-9.]+), fdn_wet', js); m_f = re.search(r'fader_early: ([0-9.]+)', js)
res['client_state_early_wet'] = float(m_state.group(1)); res['client_state_fader_early'] = float(m_f.group(1))
knots = re.search(r'var FADER_KNOTS = (\[[\s\S]*?\]);', js).group(1)
fns = re.search(r'(function dbFromTravel[\s\S]*?\n  }\n)', js).group(1) + re.search(r'(function gainFromDb[\s\S]*?\n  }\n)', js).group(1)
node = f"var FADER_KNOTS = {knots};\n{fns}\nconsole.log(JSON.stringify({{early_default: gainFromDb(dbFromTravel({res['client_state_fader_early']}), 0), fader_half: gainFromDb(dbFromTravel(0.5), 0)}}));"
r = subprocess.run(['node', '-e', node], capture_output=True, text=True, check=True)
res['client_heardMix'] = json.loads(r.stdout)
R = '/workspace/build_support_2/1_iir_colour_verification/tools/render_ir_impl.py'
def render(tag, **over):
    body = dict(CLIENT_ORTF, humidity=0.35, decay_lock=True, decay_s=1.8, **over)
    f = f'/tmp/k4_{tag}.f32'
    subprocess.run([sys.executable, R, str(SW), json.dumps(body), f, '600', '48000'], check=True, capture_output=True)
    return np.fromfile(f, np.float32).reshape(-1, 2).astype(float)
x0 = render('e0', early_wet=0.0); x1 = render('e1', early_wet=1.0)
f0 = render('f0', early_wet=0.0, direct_wet=0.0); f1 = render('f1', early_wet=1.0, direct_wet=0.0, fdn_wet=1.0)
e_only = render('eo', early_wet=1.0, direct_wet=0.0, fdn_wet=0.0)
w = slice(0, int(0.08 * 48000))
res['early_bus_energy_db_re_total_first80ms_when_on'] = float(10 * np.log10((e_only[w] ** 2).sum() / (x1[w] ** 2).sum()))
res['default_vs_early_on_diff_db_first80ms'] = float(10 * np.log10(((x1[w] - x0[w]) ** 2).sum() / (x0[w] ** 2).sum()))
late = slice(int(0.1 * 48000), None)
res['fdn_part_unchanged_by_early_wet (max abs diff)'] = float(np.max(np.abs((f1 - e_only)[late] - f0[late])))
dump(res, 'k4_early_off.json')
print(json.dumps(res, indent=1))
