#!/usr/bin/env python3
"""K5: machine diff of server defaults (params_from_body({}) and DEFAULTS) vs client initial state (app.js `var state`,
evaluated in node) and vs what the client actually SENDS (heardMix + liveRequestBody fold, evaluated in node).
Read-only on the tree. Usage: python defaults_diff.py [software_dir]"""
import json, os, re, subprocess, sys
from pathlib import Path
SW = Path(sys.argv[1] if len(sys.argv) > 1 else '/workspace/build_support_2/work/latest/software').resolve()
sys.path[:0] = [str(SW), str(SW / 'engine')]; os.chdir(SW)
import app_server as A
server = A.params_from_body({})
js = (SW / 'static/js/app.js').read_text()
m = re.search(r'\n  var state = (\{[\s\S]*?\n  \});', js)
knots = re.search(r'var FADER_KNOTS = (\[[\s\S]*?\]);', js).group(1)
fns = ''.join(re.search(p, js).group(1) for p in (r'(function dbFromTravel[\s\S]*?\n  }\n)', r'(function gainFromDb[\s\S]*?\n  }\n)', r'(function stripLinear[\s\S]*?\n  }\n)'))
node = f"var window = {{}}; var FADER_KNOTS = {knots};\n{fns}\nvar state = {m.group(1)};\nvar eff = {{direct_wet: stripLinear(state,'direct'), fdn_wet: stripLinear(state,'fdn'), early_wet: stripLinear(state,'early'), dry_gain: stripLinear(state,'dry')}};\nconsole.log(JSON.stringify({{state: state, eff: eff}}));"
r = subprocess.run(['node', '-e', node], capture_output=True, text=True)
if r.returncode: raise SystemExit(r.stderr)
cj = json.loads(r.stdout); client = cj['state']; eff = cj['eff']
rows = []
def norm(v):
    return round(v, 6) if isinstance(v, float) else v
for k in sorted(set(client) | set(server)):
    if k == 'surfaces': continue
    sv = server.get(k, '<absent>'); cv = client.get(k, '<absent>')
    sent = eff.get(k, cv)
    if norm(sv) != norm(cv) or (k in eff and norm(sv) != norm(eff[k])):
        rows.append({'key': k, 'server_params_from_body': sv, 'server_DEFAULTS': A.DEFAULTS.get(k, '<absent>'), 'client_state': cv, 'client_sends': sent})
routes = sorted(set(re.findall(r'@app\.(?:get|post)\("([^"]+)"', (SW / 'app_server.py').read_text())))
alljs = ''.join(p.read_text() for p in (SW / 'static/js').glob('*.js')) + (SW / 'static/index.html').read_text()
unused = [r_ for r_ in routes if r_.split('{')[0].rstrip('/') not in alljs]
out = {'tree': str(SW), 'n_diff': len(rows), 'diffs': rows, 'routes': routes, 'routes_not_referenced_by_client': unused}
dest = Path(__file__).resolve().parents[1] / 'results' / 'defaults_diff.json'
dest.write_text(json.dumps(out, indent=1, default=str))
for r_ in rows:
    print(f"{r_['key']:22s} server={r_['server_params_from_body']!s:10.10s} DEFAULTS={r_['server_DEFAULTS']!s:10.10s} client_state={r_['client_state']!s:10.10s} client_sends={r_['client_sends']!s:10.10s}")
print('routes not referenced by client JS/HTML:', unused)
