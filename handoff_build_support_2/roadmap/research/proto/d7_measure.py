"""D7: measure small-room Play T30 on the box app copy (build 51) with the phase harness libs."""
import sys, json, types, numpy as np
H = '/workspace/audit_1852/3_phase_acceptance_tests/harness'
sys.path[:0] = [H, H + '/lib']
import run_all as RA
from analyze import t60_bands, rms_db
a = types.SimpleNamespace(sw=sys.argv[1], python=sys.executable, node='node', golden=H + '/golden', regen_golden=False, quick=False, perf_scale=1.0, workdir=None)
ctx = RA.Ctx(a)
SR = 48000
overs = {
  'harness FDN_ONLY': {"colour_on": False, "early_wet": 0, "direct_wet": 0},
  'mutes (v51 desk)': {"colour_on": False, "mute_direct": True, "mute_early": True, "mute_dry": True},
  'mutes + faders': {"colour_on": False, "mute_direct": True, "mute_early": True, "mute_dry": True, "fader_direct": 0, "fader_early": 0},
}
out = {}
for scene in ('small_lock08', 'std_lock18'):
    dial = RA.SCENES[scene]['decay_s']
    for tag, ov in overs.items():
        x = ctx.play_ir(scene, ov, max(4, 2.5 * dial))
        e = np.cumsum(x[:, 0] ** 2); onset = int(np.argmax(e > 1e-6 * e[-1]))
        t = t60_bands(x[:, 0], SR, bands=[250, 500, 1000, 2000, 4000, 8000])
        out[f'{scene} | {tag}'] = {str(k): round(float(v), 3) for k, v in t.items()} | {'dial': dial, 'peak_ms': round(1e3 * int(np.argmax(np.abs(x[:, 0]))) / SR, 1)}
        print(scene, tag, out[f'{scene} | {tag}'])
json.dump(out, open(sys.argv[2], 'w'), indent=1)
