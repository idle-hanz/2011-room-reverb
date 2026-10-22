"""IIR (SOS) mic colour acceptance (Build's 28 Sep work; brief AT-C1..AT-C4) + Play bank capacity."""
from __future__ import annotations
import json, re
import numpy as np
import pytest
import probes as PR
from conftest import call_harness

F = np.geomspace(20.0, 20000.0, 400)
ANGLES = (0, 30, 60, 90, 120, 150, 180)


@pytest.fixture(scope='module')
def mc(sw, app):
    PR.need(PR.sos_colour, sw)
    from mic_colour.preset_store import get_store
    from mic_colour.model import relative_db
    from mic_colour.sos_fit import sos_db, unpack_record
    from mic_colour.sos_table import pack_for, tables_dir, preset_hash, _load_one
    from mic_colour.hpf import stack_hpf
    st = get_store()
    mics = sorted(p.stem for p in tables_dir().glob('*.json'))
    return dict(st=st, rel=relative_db, sos_db=sos_db, unpack=unpack_record, pack_for=pack_for, hash=preset_hash,
                load=_load_one, hpf=stack_hpf, mics=mics)


def _err(mc, mic, deg, sr, hpf_on=False, f=F):
    st = mc['st']; model = st.model_for(mic)
    rec = mc['pack_for'](mic, model, float(deg), int(sr), hpf=st.hpf_of(mic), hpf_engaged=hpf_on)
    got = np.zeros_like(f) if (rec is None or rec is False) else mc['sos_db'](mc['unpack'](rec), f, sr)
    want = np.asarray(mc['rel'](model, f, float(deg)), float)
    if hpf_on:
        h = st.hpf_of(mic) or {}
        want = np.asarray(mc['hpf'](want, f, h.get('hpf_hz'), h.get('hpf_slope') or 12, True), float)
    return got - want, rec


def _worst(mc, sr, limit, f=F):
    bad, worst = [], (0.0, None)
    for m in mc['mics']:
        for a in ANGLES:
            e, _ = _err(mc, m, a, sr, f=f)
            mx = float(np.max(np.abs(e)))
            if mx > worst[0]: worst = (mx, f'{m}@{a}')
            if mx > limit: bad.append(f'{m}@{a}deg {mx:.2f} dB @ {f[int(np.argmax(np.abs(e)))]:.0f} Hz')
    return bad, worst


@pytest.mark.phase('COLOUR')
def test_colour_tables_match_presets(mc):
    """Every sos_tables/*.json carries the preset_hash of the current preset (stale-table guard; sos_table._load_one does not check)."""
    stale = [m for m in mc['mics'] if mc['load'](m).get('preset_hash') != mc['hash'](mc['st'].get(m))]  # 48 kHz set
    assert len(mc['mics']) == 20, f"expected 20 MEASURED presets, found {len(mc['mics'])}"
    assert not stale, f'stale SOS tables: {stale}'


@pytest.mark.phase('COLOUR')
def test_colour_at_c1_48k_within_0p5db(mc):
    bad, worst = _worst(mc, 48000, 0.5)
    assert not bad, f'AT-C1 48 kHz: {bad[:8]} (worst {worst})'


@pytest.mark.phase('COLOUR')
def test_colour_at_c4_44k1_within_0p6db(mc):
    """Build's own test checks SM57 only at 44.1 kHz (test_mic_colour_relative.py:727-733); this checks all 20 mics."""
    bad, worst = _worst(mc, 44100, 0.6, f=F[F < 0.45 * 44100])
    assert not bad, f'AT-C4 44.1 kHz: {bad[:8]} (worst {worst})'


def _rate_aware(sw):
    return 'SUPPORTED_RATES' in (sw / 'mic_colour' / 'sos_table.py').read_text(encoding='utf-8', errors='replace')


@pytest.mark.phase('COLOUR')
def test_colour_44k1_tables_match_presets(sw, mc):
    """Locked 28 Sep 2026 (decision 7): a separate fitted table set for 44.1 kHz, same presets/hashes."""
    if not _rate_aware(sw):
        pytest.xfail('per-rate SOS tables not in tree (decision 7: sos_tables/44100/ + SUPPORTED_RATES)')
    miss = [m for m in mc['mics'] if not mc['load'](m, 44100)]
    stale = [m for m in mc['mics'] if mc['load'](m, 44100) and
             (mc['load'](m, 44100).get('preset_hash') != mc['hash'](mc['st'].get(m)) or int(mc['load'](m, 44100).get('fit_fs')) != 44100)]
    assert not miss and not stale, f'44.1 kHz tables missing {miss} / stale {stale}'


@pytest.mark.phase('COLOUR')
@pytest.mark.parametrize('sr', [32000, 88200, 96000])
def test_colour_unsupported_rate_disabled_with_notice(sw, app, sr):
    """Locked 28 Sep 2026 (decision 7): rates without a table set turn colour OFF with a visible notice
    (Play: colour payload 'notice' -> live_fdn.js status(); Render: status text). Never silently."""
    if not _rate_aware(sw):
        pytest.xfail(f'{sr} Hz: old tree reuses the 48k parameters silently (decision 7 not landed)')
    from mic_colour.colour import MicColour
    mcol = MicColour('MEASURED_SHELF', 'ShureSM57', 'ShureSM57', 'ShureSM57', sr)
    assert mcol.measured is False and 'OFF' in mcol.notice, (mcol.measured, mcol.notice)
    p = app.params_from_body(dict(app.DEFAULTS, sample_rate=sr, colour_mode='MEASURED_SHELF'))
    c = app.live_fdn_params(p).get('colour') or {}
    assert c.get('on') is False and c.get('notice'), c
    js = (sw / 'static' / 'js' / 'live_fdn.js').read_text(encoding='utf-8')
    assert re.search(r'colour\.notice', js) and 'status(msg)' in js, 'live_fdn.js must show colour.notice via status()'


@pytest.mark.phase('COLOUR')
@pytest.mark.parametrize('sr', [44100, 48000])
def test_colour_sos_stable(mc, sr):
    worst = 0.0
    for m in mc['mics']:
        for a in ANGLES:
            _, rec = _err(mc, m, a, sr)
            if (rec is None or rec is False):
                continue
            for b0, b1, b2, a1, a2 in np.asarray(mc['unpack'](rec), float).reshape(-1, 5):
                r = float(np.max(np.abs(np.roots([1.0, a1, a2]))))
                worst = max(worst, r)
    assert worst < 0.9995, f'{sr} Hz: worst pole radius {worst:.6f}'


@pytest.mark.phase('COLOUR')
@pytest.mark.parametrize('sr', [44100, 48000])
def test_colour_hpf_on_low_end(mc, sr):
    """Manufacturer HPF engaged: SOS within 0.5 dB of model+HPF below 100 Hz (old FIR missed by 15-26 dB)."""
    fl = np.geomspace(20.0, 100.0, 60)
    bad = []
    for m in mc['mics']:
        if not (mc['st'].hpf_of(m) or {}).get('hpf_hz'):
            continue
        for a in (0, 90, 180):
            e, _ = _err(mc, m, a, sr, hpf_on=True, f=fl)
            if np.max(np.abs(e)) > 0.5: bad.append(f'{m}@{a} {np.max(np.abs(e)):.2f} dB')
    assert not bad, f'HPF-on low end: {bad}'


@pytest.mark.phase('COLOUR')
def test_colour_play_bank_fits_two_sources_apart(sw, ctx, src):
    """Two sources placed apart must not overflow the Play colour bank (MAX_IRS) - otherwise the worklet
    fails 'Live mic filters are too long.' and colour is silently not applied."""
    m = re.search(r'MAX_IRS\s*=\s*(\d+)', src('engine/live_stereo.c'))
    assert m, 'MAX_IRS not found'
    cap = int(m.group(1))
    P = json.loads(open(ctx.params({"decay_lock": True, "decay_s": 1.8, "humidity": 0.5, "early_wet": 1.0,
                                    "two_sources": True, "sx_b": 1.5, "sz_b": 5.5})).read())
    n = len((P.get('colour') or {}).get('irs') or [])
    assert n <= cap, f'{n} colour entries > MAX_IRS {cap} (live_stereo.c) -> Play colour silently off with two sources'


@pytest.mark.phase('COLOUR')
def test_colour_cpu_active(sw, ctx, RA):
    """Colour on, 1 and 2 sources, within the run_all t15 CPU limits."""
    call_harness(RA, RA.t15_perf_active, ctx)


@pytest.mark.phase('COLOUR')
def test_colour_numpy_sos_matches_loop(sw, mc):
    """Decision 7 recommendation: vectorised, SciPy-free apply_sos (build_support_2/6_colour_per_rate/tools/
    apply_sos_fast.py) equals Build's per-sample loop (mic_colour.sos_fit.apply_sos) to <= 1e-9 abs."""
    import importlib.util
    from pathlib import Path
    f = Path(__file__).resolve().parents[2] / '6_colour_per_rate' / 'tools' / 'apply_sos_fast.py'
    if not f.exists():
        pytest.skip('6_colour_per_rate/tools/apply_sos_fast.py not next to this package')
    spec = importlib.util.spec_from_file_location('apply_sos_fast', f); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    from mic_colour.sos_fit import apply_sos
    x = np.random.default_rng(3).standard_normal(20000) * 0.3
    worst = 0.0
    for m, a, hpf in (('ShureSM57', 90, False), ('NeumannU87AiOmni', 180, False), ('AKGC414Cardioid', 120, True)):
        st = mc['st']
        rec = mc['pack_for'](m, st.model_for(m), float(a), 48000, hpf=st.hpf_of(m), hpf_engaged=hpf)
        sos = np.asarray(mc['unpack'](rec), float).reshape(-1, 5)
        worst = max(worst, float(np.max(np.abs(mod.apply_sos_numpy(x, sos) - apply_sos(x, sos)))))
    assert worst <= 1e-9, worst
