#!/usr/bin/env python3
"""Play null test: FIR colour (current wasm) vs SOS colour (patched wasm), same scene.
Usage: null_test.py <fir_tree> <sos_tree> <params.json> <params_sosK.json> <tag> [secs]"""
import sys, json, subprocess, numpy as np, os
L = '/workspace/build_support/engine/tests/lib/wasm_run.js'
fir_sw, sos_sw, pj, psj, tag = sys.argv[1:6]; secs = sys.argv[6] if len(sys.argv) > 6 else '1.5'
def ir(sw, p, over, out):
    subprocess.run(['node', L, sw, p, json.dumps(over), 'ir', secs, out], check=True)
    return np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)
a = ir(fir_sw, pj, {}, f'/tmp/rr/{tag}_fir.f32')
b = ir(sos_sw, psj, {}, f'/tmp/rr/{tag}_sos.f32')
c = ir(fir_sw, pj, {'colour_on': False}, f'/tmp/rr/{tag}_off.f32')
def nd(x, y):
    return 10 * np.log10(np.sum((x - y) ** 2) / np.sum(x ** 2))
def band_err(x, y, sr=48000):
    X = np.abs(np.fft.rfft(x[:, 0] + x[:, 1])); Y = np.abs(np.fft.rfft(y[:, 0] + y[:, 1])); f = np.fft.rfftfreq(len(x), 1 / sr)
    out = {}
    for fc in (63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000):
        m = (f >= fc / 2 ** .5) & (f < fc * 2 ** .5)
        out[fc] = round(10 * np.log10(np.sum(Y[m] ** 2) / np.sum(X[m] ** 2)), 3)
    return out
res = {'tag': tag, 'null_sos_vs_fir_db': round(nd(a, b), 2), 'null_off_vs_fir_db (colour effect size)': round(nd(a, c), 2),
       'octave_energy_sos_minus_fir_db': band_err(a, b), 'peak_fir': float(np.abs(a).max()), 'peak_sos': float(np.abs(b).max())}
print(json.dumps(res))
