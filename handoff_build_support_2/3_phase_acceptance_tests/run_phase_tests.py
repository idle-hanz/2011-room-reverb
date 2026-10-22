#!/usr/bin/env python3
"""run_all.py-style front end for the pytest phase acceptance suite.
    python run_phase_tests.py --sw <software> [--slow] [--perf-scale 1.5] [--out results.json] [-k expr]
Prints one line per test (PASS / FAIL / XFAIL / XPASS / SKIP + phase + reason) and writes JSON. Exit 1 on any FAIL."""
import argparse, json, subprocess, sys, tempfile, xml.etree.ElementTree as ET
from pathlib import Path
HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--sw', required=True); ap.add_argument('--slow', action='store_true')
ap.add_argument('--perf-scale', default='1.0'); ap.add_argument('--out', default=str(HERE / 'last_phase_results.json'))
ap.add_argument('-k', default=None); ap.add_argument('--app-python', default=sys.executable)
a = ap.parse_args()
xml = Path(tempfile.mkdtemp()) / 'j.xml'
cmd = [sys.executable, '-m', 'pytest', str(HERE / 'tests'), '-q', '-p', 'no:cacheprovider', f'--junitxml={xml}', '-o', 'junit_family=xunit1',
       '--sw', a.sw, '--perf-scale', a.perf_scale, '--app-python', a.app_python, '-rN']
if a.slow: cmd.append('--slow')
if a.k: cmd += ['-k', a.k]
p = subprocess.run(cmd, capture_output=True, text=True)
rows, nfail = [], 0
for tc in ET.parse(xml).getroot().iter('testcase'):
    name = tc.get('name'); t = float(tc.get('time') or 0)
    st, msg = 'PASS', ''
    for tag in ('failure', 'error', 'skipped'):
        e = tc.find(tag)
        if e is not None:
            m = (e.get('message') or '').strip()
            if tag in ('failure', 'error'): st = 'FAIL'
            elif e.get('type') == 'pytest.xfail' or m.startswith('xfail') or 'xfail' in (e.get('type') or ''): st = 'XFAIL'
            else: st = 'SKIP'
            msg = m.replace('\n', ' ')[:300]
    if st == 'FAIL': nfail += 1
    rows.append({'test': f"{Path(tc.get('file') or tc.get('classname','')).stem}::{name}", 'status': st, 'secs': round(t, 1), 'detail': msg})
for r in rows:
    print(f"{r['status']:6s} {r['secs']:6.1f}s  {r['test']:70s} {r['detail']}")
summary = {s: sum(r['status'] == s for r in rows) for s in ('PASS', 'FAIL', 'XFAIL', 'SKIP')}
print(summary)
json.dump({'sw': a.sw, 'summary': summary, 'results': rows, 'pytest_tail': p.stdout[-3000:]}, open(a.out, 'w'), indent=1)
sys.exit(1 if nfail else 0)
