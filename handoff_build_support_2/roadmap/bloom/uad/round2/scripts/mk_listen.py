import numpy as np, sys, json, soundfile as sf
sys.path.insert(0, '.')
import io2, models as Mo, volterra as V
SR = 48000; OUT = '/workspace/uad2/listen/'; FIT = json.load(open('/workspace/uad2/an/static_fit.json'))
a0, a1 = int(1.0 * SR), int(5.0 * SR)
def fade(y):
    n = int(0.01 * SR); w = np.ones(len(y)); w[:n] = np.linspace(0, 1, n); w[-n:] = w[:n][::-1]; return y * w
def write_set(name, sigs):
    rms = {k: np.sqrt(np.mean(v[a0:a1] ** 2)) for k, v in sigs.items()}
    ref = min(rms.values()); out = {k: fade(v[a0:a1] * ref / rms[k]) for k, v in sigs.items()}
    pk = max(np.abs(v).max() for v in out.values()); g = 10 ** (-1 / 20) / pk
    for k, v in out.items():
        p = OUT + '%s__%s.wav' % (name, k); sf.write(p, (v * g).astype(np.float32), SR, subtype='PCM_24'); print(p)
for preset, unit in Mo.PRESET_UNIT.items():
    progs = ['mix'] + (['drums', 'bass'] if preset in ('room_crush', 'nuke') else []) + (['vocal'] if preset == 'natural' else [])
    for pk in progs:
        x, y = io2.rec('prog_%s_%s_b' % (unit, pk))
        ym, _ = Mo.run_preset(preset, x, FIT[preset]['T'])
        write_set('comp_%s_%s_hot' % (preset, pk), {'A_uad_%s' % unit: y, 'B_bloom_current': ym, 'C_dry_input': x})
for pre in ('neve', 'u610a', 'manley', 'api'):
    k = np.load('/workspace/uad2/an/hk_%s.npz' % pre)['klin']
    for pk in ('vocal', 'drums'):
        x, y = io2.rec('pprog_%s_%s_+0' % (pre, pk))
        yl = V.apply_hammerstein(x, k)
        write_set('pre_%s_%s_drive' % (pre, pk), {'A_uad_driven': y, 'B_clean_linear_only': yl})
