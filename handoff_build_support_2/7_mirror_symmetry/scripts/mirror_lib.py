import sys, json, argparse, os, numpy as np
H = '/workspace/build_support_2/3_phase_acceptance_tests/harness'
sys.path[:0] = [H, H + '/lib']
import run_all as RA
from analyze import t60_bands, band
SR = 48000
BASE = dict(W=57.0, H=34.2, L=97.0, sx=44.09, sz=34.89, sy=1.88, mcx=28.5, mcz=24.25, my=1.90,
            space=0.0, hadamard_n=32, fdn_g=1.0, decay_lock=True, decay_s=0.71, ir_length_ms=1500.0,
            humidity=0.5, air_lp=0.25, air_shelf=1.0, mic_gain_l=1.0, mic_gain_c=0.0, mic_gain_r=1.0,
            direct_wet=0.0, early_wet=0.0, fdn_wet=1.0, dry_gain=0.0, colour_mode='measured',
            mic_preset_l='ShureSM57', mic_preset_r='ShureSM57', mic_preset_c='ShureSM57',
            toe_half_deg=55.0, yaw_l_deg=-55.0, yaw_r_deg=55.0, yaw_c_deg=0.0, pattern_l='cardioid', pattern_r='cardioid', car_omni=1.0)
SX_B = 57.0 - 44.09
_ctx = {}
def ctx(tree):
    if tree not in _ctx:
        ns = argparse.Namespace(sw=f'/workspace/build_support_2/work/mirror/{tree}/software', python=sys.executable, node='node',
                                golden='/tmp/nog', regen_golden=False, quick=True, perf_scale=1.0, workdir='/tmp')
        _ctx[tree] = RA.Ctx(ns)
    return _ctx[tree]
def body(kind, **kw):
    b = dict(BASE); b.update(kw.pop('over', {}))
    if kind == 'twoA': b.update(two_sources=True, mirror_b=True, source_balance=-1.0)
    elif kind == 'twoB': b.update(two_sources=True, mirror_b=True, source_balance=1.0)
    elif kind == 'oneA': b.update(two_sources=False)
    elif kind == 'oneB': b.update(two_sources=False, sx=SX_B)
    b.update(kw); return b
def play(tree, kind, secs=3.0, **kw):
    return ctx(tree).play_ir(body(kind, **kw), {}, secs)
def render(tree, kind, ms=2500, **kw):
    return ctx(tree).render_ir(body(kind, **kw), ms)
FC3 = [50*2**(k/3) for k in range(0, 29)]  # 50 Hz .. ~12.7 kHz
FC3 = [f for f in FC3 if f < 16500]
def _bands_energy(x):
    X = np.fft.rfft(x, axis=0); f = np.fft.rfftfreq(len(x), 1/SR)
    out = []
    for fc in FC3:
        m = (f >= fc*2**(-1/6)) & (f < fc*2**(1/6))
        out.append(X[m])
    return out
def onset(x):
    e = np.abs(x).max(1); return int(np.argmax(e > 1e-3*e.max()))
def null_db(a, b):
    n = min(len(a), len(b)); a, b = a[:n], b[:n]
    return 10*np.log10(max(np.sum((a-b)**2), 1e-300)/max(np.sum(a**2), 1e-300))
def compare(A, B, label='', verbose=True):
    """A: (n,2) for source A. B: (n,2) for mirrored source B. Compares A[:,0] with B[:,1] and A[:,1] with B[:,0]."""
    n = min(len(A), len(B)); A = A[:n]; Bs = B[:n, ::-1]
    r = {'label': label}
    r['level_A_db'] = 10*np.log10(np.sum(A**2)); r['level_Bs_db'] = 10*np.log10(np.sum(Bs**2))
    r['null_db'] = null_db(A, Bs)
    r['null_L_db'] = null_db(A[:, 0], Bs[:, 0]); r['null_R_db'] = null_db(A[:, 1], Bs[:, 1])
    bA = [_bands_energy(A[:, c]) for c in (0, 1)]; bB = [_bands_energy(Bs[:, c]) for c in (0, 1)]
    d = []; ildA = []; ildB = []; icA = []; icB = []
    for k in range(len(FC3)):
        eA = [np.sum(np.abs(bA[c][k])**2) for c in (0, 1)]; eB = [np.sum(np.abs(bB[c][k])**2) for c in (0, 1)]
        d.append([10*np.log10(eA[c]/eB[c]) for c in (0, 1)])
        ildA.append(10*np.log10(eA[0]/eA[1])); ildB.append(10*np.log10(eB[0]/eB[1]))
        icA.append(abs(np.sum(bA[0][k]*np.conj(bA[1][k])))/np.sqrt(eA[0]*eA[1]))
        icB.append(abs(np.sum(bB[0][k]*np.conj(bB[1][k])))/np.sqrt(eB[0]*eB[1]))
    d = np.array(d); r['band_diff_db'] = d.round(2).tolist()
    sel = np.array(FC3) >= 100
    r['band_maxabs_db'] = float(np.max(np.abs(d[sel]))); r['band_rms_db'] = float(np.sqrt(np.mean(d[sel]**2)))
    r['band_max_at_hz'] = float(np.array(FC3)[sel][np.argmax(np.max(np.abs(d[sel]), 1))])
    r['ild_A'] = np.round(ildA, 2).tolist(); r['ild_Bs'] = np.round(ildB, 2).tolist()
    r['ild_maxdiff_db'] = float(np.max(np.abs(np.array(ildA) - np.array(ildB))[sel]))
    r['ic_maxdiff'] = float(np.max(np.abs(np.array(icA) - np.array(icB))[sel]))
    r['ic_A_mean'] = float(np.mean(np.array(icA)[sel])); r['ic_Bs_mean'] = float(np.mean(np.array(icB)[sel]))
    o = min(onset(A), onset(Bs)); w = int(0.08*SR)
    eAe = [np.sum(A[o:o+w, c]**2) for c in (0, 1)]; eBe = [np.sum(Bs[o:o+w, c]**2) for c in (0, 1)]
    r['onset_ms'] = [onset(A)*1000/SR, onset(Bs)*1000/SR]
    r['early80_diff_db'] = [10*np.log10(eAe[c]/max(eBe[c], 1e-300)) for c in (0, 1)]
    oc = [125, 250, 500, 1000, 2000, 4000, 8000]
    tA = [t60_bands(A[:, c], SR, bands=oc) for c in (0, 1)]; tB = [t60_bands(Bs[:, c], SR, bands=oc) for c in (0, 1)]
    r['t30_A'] = {fc: [round(tA[c][fc], 3) for c in (0, 1)] for fc in oc}
    r['t30_Bs'] = {fc: [round(tB[c][fc], 3) for c in (0, 1)] for fc in oc}
    r['t30_maxpct'] = float(max(abs(tA[c][fc]/tB[c][fc]-1)*100 for c in (0, 1) for fc in oc))
    if verbose:
        print(f"{label:46s} null {r['null_db']:7.1f} dB | band max {r['band_maxabs_db']:5.2f} dB @{r['band_max_at_hz']:.0f} rms {r['band_rms_db']:4.2f} | "
              f"early80 {r['early80_diff_db'][0]:+.2f}/{r['early80_diff_db'][1]:+.2f} | T30 max {r['t30_maxpct']:4.1f}% | ILDdiff {r['ild_maxdiff_db']:.2f} ICdiff {r['ic_maxdiff']:.3f} | lvl {r['level_A_db']-r['level_Bs_db']:+.2f}")
    return r
