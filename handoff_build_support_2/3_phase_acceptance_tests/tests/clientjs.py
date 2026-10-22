"""Evaluate app.js `var state = {...}` (and the fader->gain fold) in node, read-only."""
import json, re, shutil, subprocess
from pathlib import Path


def client_state(sw: Path):
    node = shutil.which('node')
    if not node:
        return None
    js = (sw / 'static/js/app.js').read_text(encoding='utf-8')
    m = re.search(r'\n  var state = (\{[\s\S]*?\n  \});', js)
    if not m:
        raise AssertionError('could not find `var state = {...}` in app.js')
    prog = f"var window = {{}};\nvar state = {m.group(1)};\nconsole.log(JSON.stringify(state));"
    r = subprocess.run([node, '-e', prog], capture_output=True, text=True)
    if r.returncode:
        raise AssertionError('node could not evaluate app.js state: ' + r.stderr[-400:])
    return json.loads(r.stdout)


def shared_mismatches(server: dict, client: dict):
    out = {}
    for k in sorted(set(server) & set(client)):
        if k in ('surfaces', 'colour_rev', 'sample_rate'):
            continue
        a, b = server[k], client[k]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
            if abs(float(a) - float(b)) <= 1e-9:
                continue
        elif a == b:
            continue
        out[k] = {'server': a, 'client': b}
    return out
