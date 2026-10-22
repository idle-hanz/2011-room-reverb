#!/usr/bin/env python3
"""TEST-ONLY stand-in "references" for exercising compare_ref.py before Idle's captures exist.
NONE OF THESE ARE 2011 DATA. Every file is prefixed TESTONLY_ and every folder has a README.

  TS1_synth_two_stage/   synthetic noise IR: T1 0.7 s, T2 6 s, knee ~-25 dB, + slow 23.4 kHz residue
  TS2_synth_single/      synthetic noise IR: single slope 1.2 s, no residue
  TS3_rebuild_play_current/   the rebuild's own Play (current tree, z^-1 loop) as a fake reference
  TS4_rebuild_play_F5/        the rebuild's own Play (F1-F3+F5, same-sample) as a fake reference
  TS5_rebuild_play_F1F3/      the rebuild's own Play (F1-F3, z^-1 loop, 48 kHz integer delays) as a fake reference
Expected: TS1 -> (a) two-stage; TS2 -> (a) single-slope/apply F2; TS3, TS5 -> (b) one-sample; TS4 -> (b) same-sample.
"""
import json, sys, copy
from pathlib import Path
import numpy as np
from scipy.io import wavfile
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare_ref as C

SR = 48000; PRE = 0.5
root = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'test_standins'
tmpl = json.loads((HERE / 'capture_template.json').read_text())

def sidecar(g, dm, note):
    s = copy.deepcopy(tmpl)
    s['_readme'] = 'TEST-ONLY STAND-IN. NOT 2011 DATA. ' + note
    s['capture'].update(host='synthetic (box)', reaktor_version='none', impulse_at_s=PRE)
    s['source'].update(SX_term23=0.5, SZ_term24=0.5)
    s['mic'].update(MSS_term25=0.25, MY_term27=1.5, HZ_term28=6.5, Car_term29=1.0, HF_term30=20000)
    s['fdn'].update(GainF=g, diffusion_master=dm, surface_diffusion={k: 0.5 for k in ['Sides', 'Ahead', 'Behind', 'Floor', 'Ceiling']})
    s['air']['humidity_wet'] = 400
    return s

def write(folder, stem, L, R, sc):
    folder.mkdir(parents=True, exist_ok=True)
    x = np.zeros((int(PRE * SR) + len(L), 2), np.float32)
    x[int(PRE * SR):, 0] = L; x[int(PRE * SR):, 1] = R
    wavfile.write(str(folder / f'{stem}.wav'), SR, x)
    (folder / f'{stem}.json').write_text(json.dumps(sc, indent=1))
    (folder / 'README_TEST_ONLY.md').write_text('# TEST-ONLY stand-ins\n\nThese files are NOT 2011 Reaktor captures. They exist only to test compare_ref.py.\n')

def synth(T1_1k, T2_1k, knee_db, secs, residue_db=None, seed=1):
    rng = np.random.default_rng(seed)
    n = int(secs * SR); t = np.arange(n) / SR
    L = np.zeros(n); R = np.zeros(n)
    # frequency-dependent T via octave-band synthesis (HF shorter: x(1.0 .. 0.5))
    for fc, k in [(125, 1.1), (250, 1.05), (500, 1.0), (1000, 1.0), (2000, 0.9), (4000, 0.75), (8000, 0.6), (16000, 0.5)]:
        T1 = T1_1k * k; T2 = (T2_1k * k) if T2_1k else None
        env = 10 ** (-3 * t / T1)
        if T2:
            env = env + 10 ** (knee_db / 20) * 10 ** (-3 * t / T2) * np.clip(t / 0.05, 0, 1)
        for ch, arr in ((0, L), (1, R)):
            nz = rng.standard_normal(n)
            arr += C.MX.band(nz, SR, fc) * env
    d = int(0.0095 * SR)  # direct ~ 3.25 m / 340
    L = np.roll(L, d) * 0.05; R = np.roll(R, d) * 0.05; L[:d] = 0; R[:d] = 0
    L[d] += 1.0; R[d] += 1.0
    if residue_db is not None:
        tone = 10 ** (residue_db / 20) * 0.05 * np.sin(2 * np.pi * 23400 * t) * 10 ** (-3 * t / 20.0) * np.clip((t - 0.01) / 0.1, 0, 1)
        L += tone; R -= tone
    return L, R

if __name__ == '__main__':
    L, R = synth(0.7, 6.0, -25, 14, residue_db=-12)
    write(root / 'TS1_synth_two_stage', 'TESTONLY_TS1_G0.50_DM-0.50', L, R, sidecar(0.5, -0.5, 'synthetic two-stage T1 0.7 T2 6 knee -25 dB, 23.4 kHz residue'))
    L, R = synth(1.2, None, 0, 10)
    write(root / 'TS2_synth_single', 'TESTONLY_TS2_G0.50_DM-0.50', L, R, sidecar(0.5, -0.5, 'synthetic single slope 1.2 s'))
    class A: pass
    a = A(); a.python = C.DEFAULT_PY; a.node = 'node'; a.trees = C.DEFAULT_TREES; a.out = str(root / '_cache')
    Rn = C.Renderer(a)
    for ts, tree, g, dm in [('TS3_rebuild_play_current', 'current', 1.0, -0.5), ('TS4_rebuild_play_F5', 'F1-F3+F5', 1.0, -0.5),
                            ('TS5_rebuild_play_F1F3', 'F1-F3', 1.0, -0.5)]:
        sc = sidecar(g, dm, f'rebuild Play IR from tree {tree} used as a fake reference')
        body, knob, _ = C.body_from_sidecar(sc)
        l, r = Rn.play(tree, body, knob, 10.0)
        write(root / ts, f'TESTONLY_{ts[:3]}_G{g:.2f}_DM{dm:+.2f}', l, r, sc)
    print('wrote', root)
