"""Pack tests for the decisions Idle locked on 2026-09-30 (DECISIONS_LOCKED_2026-09-30.md). These PASS now.

They check the reference implementation in this pack (binaural_fitter/, presets/binaural/) and use the p5
engine read-only (compute_taps, FDN). Build-side versions are in test_binaural_mode_acceptance.py (xfail).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

PACK = Path(__file__).resolve().parents[1]
P5 = Path("/workspace/build_support_2/work/p5/software")
sys.path.insert(0, str(P5)); sys.path.insert(0, str(P5 / "engine"))

from binaural_fitter.rear_images import BINAURAL_REAR32, LIVE_32_P5, REAR  # noqa: E402
from binaural_fitter.grid import engine_head_relative, grid_nodes, mirror_map, nearest_node  # noqa: E402
from binaural_fitter.reference import image_to_ears, load_preset, load_table, record_sos  # noqa: E402
from binaural_fitter.sosfit import sos_db  # noqa: E402
from binaural_fitter import tail_ic as T  # noqa: E402

PRESETS = ["SADIE2_KU100", "SADIE2_KEMAR", "THK_KU100_FF"]
ROOM, SRC, HEAD = (6.0, 3.0, 8.0), (2.6, 1.2, 4.75), (3.0, 1.5, 1.5)


def _ef():
    pytest.importorskip("engine.early_field")
    from engine import early_field as ef
    return ef


def _stand(ef, head=HEAD):
    return ef.MicStand(cx=head[0], cy=head[1], cz=head[2], space=0.18, car_omni=0.0,
                       mlalr=math.radians(-90), mralr=math.radians(90),
                       pattern_l="omni", pattern_r="omni", pattern_c="omni")


# ---------- locked 2, 3, 4: default head, K=6 symmetric table, level from head centre ----------

def test_locked_default_head_and_thk_flagged():
    idx = json.loads((PACK / "presets/binaural/index.json").read_text())
    assert idx["default_preset"] == "SADIE2_KU100"
    assert {p["preset_id"]: p["licence"] for p in idx["presets"]}["SADIE2_KU100"] == "Apache-2.0"
    thk = load_preset("THK_KU100_FF")["licence"]
    assert thk["share_alike"] is True and "CC BY 3.0" in thk["note"]  # conflict stays flagged
    assert idx["K"] == 6


@pytest.mark.parametrize("pid", PRESETS)
@pytest.mark.parametrize("sr", [44100, 48000])
def test_locked_k6_single_mirror_table_60(pid, sr):
    t = load_table(pid, sr)
    assert len(t["nodes"]) == 60 and len(t["sos"]["L"]) == 60
    assert all(len(r) == 6 for r in t["sos"]["L"])
    mm = t["mirror"]
    assert all(mm[mm[i]] == i for i in range(60))  # one table serves both ears


def test_locked_level_from_head_centre():
    p, t = load_preset("SADIE2_KU100"), load_table("SADIE2_KU100", 48000)
    L, R = image_to_ears(p, t, HEAD, 0.0, (1.0, 1.5, 1.5))  # 2 m left: per-ear 1/r^2 would differ by ~1.6 dB
    assert L.level == R.level


# ---------- locked 5: rear images ----------

def test_rear32_copy_matches_p5_live32():
    ef = _ef()
    assert tuple(tuple(n) for n in ef.LIVE_32) == LIVE_32_P5


def test_rear32_set_properties():
    s = BINAURAL_REAR32
    assert len(s) == 32 and len(set(s)) == 32              # 32 lines stay 32, no duplicate voices
    assert s[2] == (0, 0, 0)                                # direct index unchanged
    assert set(REAR) == {(0, 0, -1), (1, 0, -1), (-1, 0, -1), (0, 1, -1), (0, -1, -1)}
    assert {(-x, y, z) for x, y, z in s} == set(s)          # mirror-symmetric in X
    assert max(abs(a) + abs(b) + abs(c) for a, b, c in s) <= 3
    exported = json.loads((PACK / "presets/binaural/image_sets/binaural_rear32.json").read_text())
    assert [tuple(n) for n in exported["indices"]] == list(s)


def test_rear_images_arrive_from_behind():
    ef = _ef()
    taps = ef.compute_taps(ROOM, SRC, _stand(ef), indices=list(BINAURAL_REAR32))
    rear = [t for t in taps if t.n[2] < 0]
    assert len(rear) == 5
    for t in rear:
        az, el, r = engine_head_relative(HEAD, t.position, 0.0)
        assert abs(az) > 90.0, (t.n, az)
    live = ef.compute_taps(ROOM, SRC, _stand(ef), hadamard_n=32)
    assert all(abs(engine_head_relative(HEAD, t.position, 0.0)[0]) < 90.0 for t in live)  # today: none behind


@pytest.mark.parametrize("pid", PRESETS)
def test_rear_images_lateralised(pid):
    """Rear-left image: left ear first and louder (1-8 kHz mean); rear-right: the opposite."""
    ef = _ef()
    p, t = load_preset(pid), load_table(pid, 48000)
    band = np.geomspace(1000, 8000, 40)
    for tp in ef.compute_taps(ROOM, SRC, _stand(ef), indices=list(BINAURAL_REAR32)):
        if tp.n[2] >= 0 or tp.n[0] == 0:
            continue
        L, R = image_to_ears(p, t, HEAD, 0.0, tp.position)
        ild = float(np.mean(sos_db(record_sos(t, L.record), band, 48000) - sos_db(record_sos(t, R.record), band, 48000)))
        left = tp.position[0] < HEAD[0]   # L = smaller X (K1 convention)
        assert (L.az > 90) == left and (L.az < -90) == (not left)
        assert (R.delay_ms > L.delay_ms) == left
        assert (ild > 3.0) if left else (ild < -3.0), (pid, tp.n, ild)


@pytest.mark.parametrize("pid", PRESETS)
def test_rear_front_back_coloured(pid):
    """Every horizontal rear node's record differs from its front mirror (same lateral angle) by >= 1 dB RMS
    over 2-12 kHz (MEASURED minimum 1.2-2.2 dB, reports/rear_images.json), and rear taps use rear nodes."""
    ef = _ef()
    t = load_table(pid, 48000); nodes = t["nodes"]
    band = np.geomspace(2000, 12000, 60)
    for i, (az, el) in enumerate(nodes):
        if abs(el) > 1e-6 or abs(az) <= 90:
            continue
        j = int(nearest_node(nodes, [math.copysign(180 - abs(az), az)], [el])[0][0])
        d = sos_db(record_sos(t, i), band, 48000) - sos_db(record_sos(t, j), band, 48000)
        assert np.sqrt(np.mean(d ** 2)) >= 1.0, (pid, az)
    p = load_preset(pid)
    for tp in ef.compute_taps(ROOM, SRC, _stand(ef), indices=list(BINAURAL_REAR32)):
        if tp.n[2] < 0:
            L, _ = image_to_ears(p, t, HEAD, 0.0, tp.position)
            assert abs(nodes[L.node][0]) > 90 or abs(nodes[L.node][1]) >= 60


def test_rear32_entry_counts_within_max_irs():
    d = json.loads((PACK / "reports/rear_images.json").read_text())["entries"]
    assert d["worst_case_fixed_bank"] == 60 <= 64
    for k, v in d["BINAURAL_REAR32"].items():
        assert v["records_symmetric_shared"] <= 64, k
        assert v["filters_per_ear"] <= 32, k


# ---------- locked 1: diffuse tail with the head's measured IC ----------

@pytest.mark.parametrize("pid", PRESETS)
@pytest.mark.parametrize("sr", [44100, 48000])
def test_ic_mixer_design(pid, sr):
    f, ic = T.target_ic(pid)
    ship = json.loads((PACK / f"presets/binaural/tail_ic/{pid}.json").read_text())
    N = ship["ntaps"]
    hp, hm, hc, hs = T.design_mixer(f, ic, sr, N)
    assert np.allclose(hp, ship["fir"][str(sr)]["hp"]) and np.allclose(hm, ship["fir"][str(sr)]["hm"])
    fe = np.geomspace(125, 16000, 200)
    icd, gdb = T.designed_ic(hc, hs, sr, fe)
    assert np.max(np.abs(icd - np.interp(np.log(fe), np.log(f), ic))) <= 0.03
    assert np.max(np.abs(gdb)) <= 0.1  # power kept (Hc^2 + Hs^2 = 1)


def test_ic_mixer_on_independent_noise():
    f, ic = T.target_ic("SADIE2_KU100")
    hp, hm, _, _ = T.design_mixer(f, ic, 48000, 513)
    rng = np.random.default_rng(7)
    A, B = rng.standard_normal(20 * 48000), rng.standard_normal(20 * 48000)
    L, R = T.apply_mixer(A, B, hp, hm)
    ff, c = T.measure_ic(L[513:], R[513:], 48000, nperseg=8192)
    got = T.band_ic(ff, c, T.THIRD_OCT)
    want = np.interp(np.log(T.THIRD_OCT), np.log(f), ic)
    assert np.max(np.abs(got - want)) <= 0.06


def test_engine_tail_coherence_matches_head():
    """p5 FDN (read-only), default scene, BINAURAL_REAR32 images, 4 s tail: the even/odd split + IC mixer output
    matches the SADIE2_KU100 diffuse-field IC; the raw L/R loop sums (today) do not."""
    _ef()
    sys.path.insert(0, str(PACK / "scripts"))
    import rear_tail_study as S
    P = S.fdn_polys(S.SCENES["default_A"], BINAURAL_REAR32, 48000, length_s=4.0)
    f, ic = T.target_ic("SADIE2_KU100")
    want = np.interp(np.log(T.THIRD_OCT), np.log(f), ic)
    a0 = int(0.1 * 48000)
    A, B = T.split_even_odd(P["l"], P["r"])
    hp, hm, _, _ = T.design_mixer(f, ic, 48000, 513)
    L, R = T.apply_mixer(A, B, hp, hm)
    ff, c = T.measure_ic(L[a0 + 256:], R[a0 + 256:], 48000)
    got = T.band_ic(ff, c, T.THIRD_OCT)
    assert np.max(np.abs(got - want)) <= 0.15          # estimator noise floor p95 ~0.13 at this length
    assert np.sqrt(np.mean((got - want) ** 2)) <= 0.06
    fr, cr = T.measure_ic(P["l"].sum(1)[a0:], P["r"].sum(1)[a0:], 48000)
    raw = T.band_ic(fr, cr, T.THIRD_OCT)
    assert np.max(np.abs(raw - want)) > 0.3            # today's L/R loops miss the LF coherence
    pw = np.mean(L[a0 + 256:] ** 2) / np.mean(P["l"].sum(1)[a0:] ** 2)
    assert abs(10 * np.log10(pw)) <= 0.5               # tail level kept
