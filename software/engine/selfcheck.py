#!/usr/bin/env python3
"""
Self-checks for the 2011 early-field / FDN prototype.

Verifies:
  1. 32 image indices are the exact agreed set
  2. Polarity formula (-1)^(nx+ny+nz)
  3. Omit (0,0,-2)
  4. Direct (0,0,0) has no allpass stages
  5. Software geometric level 1/r decreases with distance (Structure graph remains 1/r²)
  6. Wall-crossing frozenset combos (once-per-axis; Behind=−z)
  7. VERIFIED mirror leaf algebra (full R, Sub pin order)
  8. VERIFIED Prepare MCZ = L − MZ (+ mic/source locks)
  9. Absorb mask tables (data only) length/values
  10. Sylvester Hadamard rows 1–2 match Structure shots 224–225
  11. To V tables (data only) X repeating-5 + Y/Z first-column subset
  12. absorb_masks / to_v_tables not imported by the audio path
  13. Dffs = Dis×Dff×(1/Diffusion) matches 461/465; 0 = pure delay
  14. AGC On Send = √(Σ 1/r²); no extra square of the sum
  15. Air Abs 1-pole fc = Wet/Dis; IR DC gain 1; humidity 0 = dirac inject
  16. Mic Gain = 1-(2·|Dir|)^C/O; FtoP×Gain; 1-pole on FDN out only
"""

from __future__ import annotations

from early_field import (
    build_image_indices,
    LIVE_32,
    LIVE_32_REAKTOR,
    enumerate_scaled_grid,
    polarity,
    geometric_level,
    image_order,
    compute_taps,
    MicStand,
    crossed_axes,
    wall_combo_key,
    behind_z_crossed,
    all_wall_combo_keys,
    precompute_wall_peaking_coeffs,
    peaking_stages_for_tap,
    image_position_corner,
    image_position_centre,
    SPEED_OF_SOUND_M_S,
    macro_passthrough,
    macro_neg,
    macro_2R_minus_S,
    macro_2R_plus_S,
    macro_S_minus_2R,
    macro_4L_minus_Z,
    prepare_mcx,
    prepare_mcz,
    prepare_mic_triplet,
    prepare_angles,
    prepare_source,
    prepare_direct_field,
    direct_field_from_metres,
    direct_field_from_params,
    delay_ms_from_distance,
    dist,
    dist_xz,
    mic_positions,
    direction_angles,
    arrival_cos_xz,
)


def test_32_indices_exact_set() -> None:
    """Default table is the symmetric 32. Reaktor order stays behind reaktor_parity."""
    from collections import Counter
    parity = build_image_indices(32, reaktor_parity=True)
    assert parity == list(LIVE_32_REAKTOR)
    assert len(set(parity)) == 29
    assert parity[2] == (0, 0, 0)
    assert parity[0] == (0, 2, 0)
    assert (0, 0, -2) not in parity
    assert all(n[2] >= 0 for n in parity)
    assert parity.count((0, 1, 1)) == 2
    assert parity.count((0, 0, 1)) == 2
    assert parity.count((-1, -2, 0)) == 2
    got = build_image_indices()
    assert got == list(LIVE_32)
    assert got == list(enumerate_scaled_grid(bias="32"))
    assert len(got) == 32
    assert got[0] == (0, 2, 0)
    assert got[10] == (0, 0, 0)
    assert len(set(got)) == 30
    counts = Counter(got)
    for (a, b, z), n in list(counts.items()):
        assert counts[(-a, b, z)] == n
    assert (0, 0, -2) not in got
    assert all(n[2] >= 0 for n in got)




def test_scaled_grid_presets() -> None:
    """Default 32 unchanged; optional scaled presets for render tables."""
    assert build_image_indices() == list(enumerate_scaled_grid(bias="32"))
    assert len(enumerate_scaled_grid(R=1)) == 27
    assert len(enumerate_scaled_grid(R=2)) == 125
    g64 = enumerate_scaled_grid(bias="64like")
    assert len(g64) == 64
    assert (0, 0, -2) not in g64
    assert (0, 0, 2) in g64

def test_omit_0_0_minus2() -> None:
    imgs = build_image_indices()
    assert (0, 0, -2) not in imgs
    assert (0, 0, -2) not in LIVE_32


def test_polarity_formula() -> None:
    for n in build_image_indices():
        nx, ny, nz = n
        expect = 1 if ((nx + ny + nz) % 2 == 0) else -1
        expect2 = (-1) ** (nx + ny + nz)
        assert polarity(n) == expect == expect2, f"polarity fail at {n}"


def test_direct_no_allpass() -> None:
    room = (5.0, 3.0, 7.0)
    source = (0.0, 0.0, 2.0)
    stand = MicStand(cx=0.0, cy=0.0, cz=-2.0, space=0.25, mlalr=0.0, mralr=0.0, car_omni=1.0)
    taps = compute_taps(room, source, stand, origin="centre")
    direct = [t for t in taps if t.n == (0, 0, 0)]
    assert len(direct) == 1
    assert direct[0].allpass_stages == 0, "direct must have no allpass order"
    assert direct[0].order == 0
    assert direct[0].peak_axes == ()
    for t in taps:
        if image_order(t.n) == 1:
            assert t.allpass_stages == 0, f"order-1 should bypass allpass: {t.n}"


def test_distance_euclidean_and_angle_is_xz_dot() -> None:
    """Image delay distance is √(Δx²+Δy²+Δz²). cos(horiz) = XZ look · r / |r|.

    Structure Distances (420–433) is the Euclidean chain. Polar gain only
    needs the cosine; the ArcTan / Sine/Cosine stack (417, 450, 451) is the
    long form of this 2D dot product. Not a 3D dot — primary ArcTan is ΔX/ΔZ.
    """
    import math
    mic = (1.0, 1.5, 2.0)
    img = (4.0, 3.5, 8.0)
    dx, dy, dz = 3.0, 2.0, 6.0
    assert abs(dist(mic, img) - math.sqrt(dx * dx + dy * dy + dz * dz)) < 1e-12
    assert abs(dist_xz(mic, img) - math.sqrt(dx * dx + dz * dz)) < 1e-12
    img_on = (1.0, 1.5, 9.0)
    assert abs(arrival_cos_xz(mic, img_on, 0.0) - 1.0) < 1e-12
    assert abs(direction_angles(mic, img_on, 0.0)[0]) < 1e-12
    for yaw in (0.0, -0.25, 0.25, 0.5, -1.2, 2.0):
        th, _vert = direction_angles(mic, img, yaw)
        assert abs(math.cos(th) - arrival_cos_xz(mic, img, yaw)) < 1e-12


def test_air_abs_one_over_r() -> None:
    """Software geometric level is 1/r (Idle 2026-10-10).

    Structure Air Abs (256) is still Dis×Dis then 1/x. Distances 1/x is
    1/340, not this gain. Pins: 1 m → 1, 2 m → 0.5, 4 m → 0.25.
    """
    d1, d2, d3 = 1.0, 2.0, 4.0
    g1, g2, g3 = geometric_level(d1), geometric_level(d2), geometric_level(d3)
    assert g1 > g2 > g3 > 0.0
    assert abs(g1 - 1.0) < 1e-12
    assert abs(g2 - 0.5) < 1e-12
    assert abs(g3 - 0.25) < 1e-12
    room = (5.0, 3.0, 7.0)
    source = (0.0, 0.0, 2.0)
    stand = MicStand(cx=0.0, cy=0.0, cz=-2.0, space=0.0, mlalr=0.0, mralr=0.0, car_omni=0.0)
    taps = compute_taps(room, source, stand, origin="centre")
    for t in taps:
        r = t.distance_l
        assert abs(geometric_level(r) - 1.0 / r) < 1e-12
    by_dist = sorted(taps, key=lambda t: t.distance_l)
    levels = [geometric_level(t.distance_l) for t in by_dist]
    for a, b in zip(levels, levels[1:]):
        assert a >= b - 1e-15, "1/r must decrease (non-increase) with distance"


def test_wall_combo_once_per_axis() -> None:
    """Nonzero axes → frozenset; |n|≥2 still once; Behind=−z; omit-only-behind already out."""
    assert crossed_axes((0, 0, 0)) == frozenset()
    assert wall_combo_key((2, 0, 0)) == frozenset({"X"})
    assert wall_combo_key((-2, 0, 0)) == frozenset({"X"})
    assert wall_combo_key((1, -1, 1)) == frozenset({"X", "Y", "Z"})
    assert behind_z_crossed((0, 0, -1)) is True
    assert behind_z_crossed((0, 0, 2)) is False
    assert behind_z_crossed((1, 0, -1)) is True
    # Pure behind-mic k≥2 omitted from live/64like
    assert (0, 0, -2) not in build_image_indices()
    assert (0, 0, -2) not in enumerate_scaled_grid(bias="64like")
    # All 8 combo keys exist; Sides=X shared cache has one stage for {X}
    room = (5.0, 3.0, 7.0)
    cache = precompute_wall_peaking_coeffs(room, 44100, 340.0, 1.5)
    assert len(all_wall_combo_keys()) == 8
    assert set(cache.keys()) == set(all_wall_combo_keys())
    assert len(cache[frozenset()]) == 0
    assert len(cache[frozenset({"X"})]) == 1
    assert len(cache[frozenset({"X", "Y", "Z"})]) == 3
    stand = MicStand(cx=0.0, cy=0.0, cz=-2.0, space=0.25, mlalr=0.0, mralr=0.0, car_omni=1.0)
    taps = compute_taps(room, (0.0, 0.0, 2.0), stand, grid="32", origin="centre")
    for t in taps:
        assert t.wall_combo == crossed_axes(t.n)
        assert t.behind_z == (t.n[2] < 0)
        peaks = peaking_stages_for_tap(t, room, 44100, 340.0, 1.5, wall_cache=cache)
        assert len(peaks) == len(t.wall_combo)
    # 64like still has no pure behind-mic k≥2
    taps64 = compute_taps(room, (0.0, 0.0, 2.0), stand, grid="64like", origin="centre")
    assert len(taps64) == 64
    assert all(not (t.n[0] == 0 and t.n[1] == 0 and t.n[2] <= -2) for t in taps64)




def test_corner_macros_and_c340() -> None:
    """Corner maps n∈{-2..2} via VERIFIED leaves; live (0,0,2) is 2L+Z; 4L-Z optional."""
    assert abs(SPEED_OF_SOUND_M_S - 340.0) < 1e-9
    room = (5.0, 3.0, 7.0)
    # corner-absolute source equivalent to old centre (0,0,2)
    source = (2.5, 1.5, 5.5)
    assert image_position_corner(source, room, (0, 0, 0)) == source
    assert image_position_corner(source, room, (-1, 0, 0)) == (-2.5, 1.5, 5.5)
    assert image_position_corner(source, room, (1, 0, 0)) == (7.5, 1.5, 5.5)
    assert image_position_corner(source, room, (2, 0, 0)) == (12.5, 1.5, 5.5)
    assert image_position_corner(source, room, (-2, 0, 0)) == (-7.5, 1.5, 5.5)
    # 4L-Z face
    assert image_position_corner(source, room, (0, 0, 2), z_face_4l=True) == (2.5, 1.5, 4 * 7.0 - 5.5)
    # without special: 2L+Z
    assert image_position_corner(source, room, (0, 0, 2), z_face_4l=False) == (2.5, 1.5, 2 * 7.0 + 5.5)
    # centre paper still available
    assert image_position_centre((0.0, 0.0, 2.0), room, (0, 0, 2)) == (0.0, 0.0, 2.0 + 2 * 7.0)
    stand = MicStand(cx=2.5, cy=1.5, cz=1.5, space=0.25, mlalr=0.0, mralr=0.0, car_omni=1.0)
    taps = compute_taps(room, source, stand, origin="corner", z_face_4l=False)
    assert len(taps) == 32
    face = [t for t in taps if t.n == (0, 0, 2)][0]
    assert abs(face.position[2] - (2 * 7.0 + 5.5)) < 1e-9
    # delay ms law
    assert abs(face.delay_ms_l - 1000.0 * face.distance_l / 340.0) < 1e-9


def test_verified_mirror_leaf_algebra() -> None:
    """Structure locks 2026-09-17: full-R Mul/Sub; no half-W; Const 4 on 4L-Z."""
    W, H, L = 5.0, 3.0, 7.0
    X, Y, Z = 2.5, 1.5, 5.5
    assert abs(macro_passthrough(X) - X) < 1e-12
    assert abs(macro_neg(X) - (-X)) < 1e-12
    assert abs(macro_neg(Y) - (-Y)) < 1e-12
    assert abs(macro_2R_minus_S(X, W) - ((2.0 * W) - X)) < 1e-12  # 2W-X
    assert abs(macro_2R_plus_S(X, W) - ((2.0 * W) + X)) < 1e-12   # 2W+X
    assert abs(macro_2R_minus_S(Y, H) - ((2.0 * H) - Y)) < 1e-12  # 2H-Y
    assert abs(macro_2R_plus_S(Y, H) - ((2.0 * H) + Y)) < 1e-12   # 2H+Y
    assert abs(macro_S_minus_2R(Y, H) - (Y - (2.0 * H))) < 1e-12  # -2H+Y
    assert abs(macro_2R_minus_S(Z, L) - ((2.0 * L) - Z)) < 1e-12  # 2L-Z
    assert abs(macro_2R_plus_S(Z, L) - ((2.0 * L) + Z)) < 1e-12   # 2L+Z
    assert abs(macro_4L_minus_Z(Z, L) - ((4.0 * L) - Z)) < 1e-12  # 4L-Z Const 4
    assert abs(macro_S_minus_2R(Z, L) - (Z - (2.0 * L))) < 1e-12  # -2L+Z
    # Equivalent form -2R+S == S-(2R); must NOT be half-W
    assert abs(macro_S_minus_2R(X, W) - (-2.0 * W + X)) < 1e-12
    assert abs(macro_2R_minus_S(X, W) - (2.0 * (W * 0.5) - X)) > 0.5  # differs from half-W guess


def test_verified_prepare_mcz_and_mics() -> None:
    """Prepare Direct Field locks: MCZ=L−MZ; MLX/MRX; angles; source."""
    W, H, L = 5.0, 3.0, 7.0
    mz, my, space = 5.5, 1.5, 0.25
    diverg, sox, soz = 1.0, 0.5, 4.0 / 5.5
    assert abs(prepare_mcx(W) - W * 0.5) < 1e-12
    assert abs(prepare_mcz(L, mz) - (L - mz)) < 1e-12
    mcz = prepare_mcz(L, mz)
    assert abs(mcz - 1.5) < 1e-12
    left, centre, right = prepare_mic_triplet(W, L, mz, my, space)
    assert centre == (2.5, 1.5, 1.5)
    assert abs(left[0] - (2.5 - 0.125)) < 1e-12
    assert abs(right[0] - (2.5 + 0.125)) < 1e-12
    assert left[1] == right[1] == centre[1] == my
    assert left[2] == right[2] == centre[2] == mcz
    mlalr, mralr = prepare_angles(diverg)
    assert abs(mlalr - (diverg * 0.5 + (-0.25))) < 1e-12
    assert abs(mralr - (diverg * 0.5 + 0.25)) < 1e-12
    assert abs((mralr - mlalr) - 0.5) < 1e-12
    src = prepare_source(W, L, mcz, my, sox, soz)
    assert abs(src[0] - W * sox) < 1e-12
    assert abs(src[1] - my) < 1e-12
    assert abs(src[2] - (mcz + (L - mcz) * soz)) < 1e-9
    prep = prepare_direct_field(
        W, H, L, mz=mz, my=my, space=space, diverg=diverg, sox=sox, soz=soz,
    )
    stand = MicStand.from_prepare(prep, car_omni=1.0)
    assert abs(stand.cz - (L - mz)) < 1e-12
    ml, mr = mic_positions(stand)
    assert abs(ml[0] - prep.mic_left[0]) < 1e-12
    assert abs(mr[0] - prep.mic_right[0]) < 1e-12
    # Direct Field DD = 2D XZ; image Distances stay 3D
    d2 = dist_xz(prep.mic_centre, prep.source)
    d3 = dist(prep.mic_centre, prep.source)
    # same when Δy=0 (SY=MY)
    assert abs(d2 - d3) < 1e-12
    assert abs(delay_ms_from_distance(d3, 340.0) - (d3 / 340.0) * 1000.0) < 1e-12


def test_direct_field_from_metres_identity() -> None:
    """Live metres path keeps poses Prepare knobs cannot name (source behind mics)."""
    W, H, L = 6.0, 3.0, 8.0
    behind = direct_field_from_metres(
        W, H, L, sx=2.0, sy=1.2, sz=0.4, mcx=3.0, my=1.5, mcz=2.0, space=0.2,
    )
    assert behind.source == (2.0, 1.2, 0.4)
    assert behind.mic_centre == (3.0, 1.5, 2.0)
    assert behind.source[2] < behind.mcz
    assert abs(behind.mz - (L - 2.0)) < 1e-12
    on_front = direct_field_from_metres(
        W, H, L, sx=3.0, sy=1.5, sz=4.0, mcx=3.0, my=1.5, mcz=L, space=0.17,
    )
    assert abs(on_front.source[2] - 4.0) < 1e-12
    assert abs(on_front.mcz - L) < 1e-12
    mz, sox, soz, my, space = 6.5, 0.5, 0.4, 1.5, 0.17
    old = prepare_direct_field(
        W, H, L, mz=mz, my=my, space=space, diverg=1.0, sox=sox, soz=soz, mcx=3.0, sy=1.6,
    )
    mcz = L - mz
    sx = W * sox
    sz = mcz + (L - mcz) * soz
    new = direct_field_from_metres(
        W, H, L, sx=sx, sy=1.6, sz=sz, mcx=3.0, my=my, mcz=mcz, space=space, diverg=1.0,
    )
    assert abs(old.source[0] - new.source[0]) < 1e-12
    assert abs(old.source[1] - new.source[1]) < 1e-12
    assert abs(old.source[2] - new.source[2]) < 1e-12
    assert abs(old.mcz - new.mcz) < 1e-12
    p = {
        "W": W, "H": H, "L": L,
        "sx": 1.0, "sy": 1.1, "sz": 0.3, "mcx": 2.5, "my": 1.4, "mcz": 5.0,
        "space": 0.2, "diverg": 1.0,
        "sox": 0.0, "soz": 0.0, "mz": 0.0,
    }
    from_p = direct_field_from_params(p)
    assert from_p.source == (1.0, 1.1, 0.3)
    assert from_p.mcz == 5.0


def test_press_grad_and_ms_decode() -> None:
    from early_field import (
        capsule_press_grad,
        prepare_direct_field,
        MicStand,
        compute_taps,
    )
    p, g = capsule_press_grad(0.0, family="cardioid", polar=0.0)
    assert abs(p - 1.0) < 1e-12 and abs(g) < 1e-12
    p, g = capsule_press_grad(0.0, family="bi", polar=0.5)
    assert abs(p) < 1e-12 and abs(g - 1.0) < 1e-12
    room = (6.0, 3.0, 8.0)
    prep = prepare_direct_field(
        6.0, 3.0, 8.0, mz=6.5, my=1.5, space=0.05, diverg=0.0,
        sox=0.5, soz=0.6, mcx=3.0,
    )
    stand = MicStand.from_prepare(
        prep, car_omni=1.0,
        pattern_c="cardioid", family_c="cardioid", polar_c=0.5,
        yaw_c_deg=0.0, ms_decode=True,
    )
    taps = compute_taps(room, prep.source, stand, hadamard_n=8)
    direct = [t for t in taps if t.n == (0, 0, 0)][0]
    assert abs(direct.level_l - direct.level_r) < 1e-9 * (1.0 + abs(direct.level_l))


def test_first_order_polar_slider() -> None:
    from early_field import polar_a_from_slider, first_order_gain, SUPER_A, capsule_gain
    assert abs(polar_a_from_slider(0.0) - 1.0) < 1e-12
    assert abs(polar_a_from_slider(0.5) - 0.5) < 1e-12
    assert abs(polar_a_from_slider(1.0) - SUPER_A) < 1e-12
    assert abs(first_order_gain(0.0, 0.5) - 1.0) < 1e-12
    assert abs(capsule_gain(0.0, family="bi") - 1.0) < 1e-12
    assert abs(capsule_gain(3.1415926535, family="bi") + 1.0) < 1e-6


def test_absorb_masks_reverified() -> None:
    """Bit tables 18–52; not used by the renderer — data integrity only."""
    from absorb_masks import MASKS, INDEX0, INDEX1, bit, _STRINGS
    assert INDEX0 == 18 and INDEX1 == 52
    for letter, s in _STRINGS.items():
        assert len(s) == 35, letter
        assert len(MASKS[letter]) == 35, letter
        assert set(MASKS[letter]) <= {0, 1}
    # Spot-check corrections vs batch-4 OCR
    assert bit("A", 18) == 0 and bit("A", 21) == 1 and bit("A", 33) == 0
    assert bit("F", 18) == 0 and bit("F", 19) == 1  # not a run of ones
    assert bit("C", 33) == 0
    assert bit("E", 19) == 0
    assert bit("B", 24) == 1 and bit("D", 31) == 1


def test_to_v_tables_verified_subset() -> None:
    """X repeating-5 + Y/Z first-column subset. Data only — not in audio."""
    from to_v_tables import (
        X_INDEX0,
        X_INDEX1,
        X_MACRO_BY_INDEX,
        Y_MACRO_BY_INDEX,
        Z_MACRO_BY_INDEX,
        triple,
        x_macro,
        y_macro,
        z_macro,
    )
    assert X_INDEX0 == 17 and X_INDEX1 == 52
    assert len(X_MACRO_BY_INDEX) == 36
    assert x_macro(17) == "X" and x_macro(18) == "2W-X" and x_macro(21) == "-2W+X"
    assert x_macro(52) == "X" and x_macro(16) is None
    assert y_macro(13) == "2H+Y" and y_macro(24) == "2H+Y"
    assert y_macro(19) == "2H-Y" and y_macro(28) == "2H-Y"
    assert y_macro(25) is None  # remainder not VERIFIED
    assert z_macro(19) == "2L+Z" and z_macro(24) == "2L+Z"
    assert z_macro(25) == "2L-Z" and z_macro(28) == "2L-Z"
    assert z_macro(29) == "Z" and z_macro(32) == "Z"
    assert z_macro(33) == "4L-Z" and z_macro(52) is None
    assert set(Z_MACRO_BY_INDEX) == set(range(19, 34))
    assert set(Y_MACRO_BY_INDEX) == {13, 14, 15, 16, 17, 18, 24, 19, 20, 21, 22, 23, 27, 28}
    assert triple(33) == ("2W-X", None, "4L-Z")
    assert triple(17) == ("X", "2H+Y", None)


def test_data_tables_not_imported_by_audio() -> None:
    """absorb_masks / to_v_tables stay out of the render path."""
    from pathlib import Path
    root = Path(__file__).resolve().parent
    for name in ("early_field.py", "fdn.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert "absorb_masks" not in text, name
        assert "to_v_tables" not in text, name
    rp = root.parent / "render_pipeline.py"
    text = rp.read_text(encoding="utf-8")
    assert "absorb_masks" not in text
    assert "to_v_tables" not in text


def test_air_abs_one_pole_cutoff_and_inject() -> None:
    """256: Log F=Wet/Dis → 1-Pole. fc=Wet/Dis. humidity 0 ⇒ t=0 dirac."""
    from early_field import (
        air_abs_cutoff_hz,
        air_abs_wet_from_humidity,
        one_pole_lp_ir,
        HUMIDITY_WET_MIN,
        HUMIDITY_WET_MAX,
        HUMIDITY_WET_DEFAULT,
    )
    from fdn import build_inject_from_taps
    import numpy as np
    assert abs(air_abs_cutoff_hz(10.0, 400.0) - 40.0) < 1e-12
    assert air_abs_cutoff_hz(10.0, 0.0) == 0.0
    assert air_abs_wet_from_humidity(0.0) == 0.0
    assert abs(air_abs_wet_from_humidity(0.5) - HUMIDITY_WET_DEFAULT) < 1e-12
    assert abs(air_abs_wet_from_humidity(1.0) - HUMIDITY_WET_MAX) < 1e-12
    assert HUMIDITY_WET_MIN == 100.0
    ir = one_pole_lp_ir(2048, 40.0, 44100)
    assert abs(float(np.sum(ir)) - 1.0) < 1e-3
    class T:
        distance_l = 10.0
        distance_r = 10.0
        distance_c = 10.0
        level_l = 0.5
        level_r = 0.5
        level_c = 0.5
    inj0 = build_inject_from_taps([T()], 64, 44100, 340.0, 4, channel="l", humidity=0.0)
    assert float(np.max(np.abs(inj0[1:]))) == 0.0
    assert abs(float(inj0[0, 0]) - 0.5) < 1e-12
    inj1 = build_inject_from_taps([T()], 64, 44100, 340.0, 4, channel="l", humidity=1.0)
    assert float(np.max(np.abs(inj1[1:, 0]))) > 0.0
    from early_field import humidity_shelf_coeffs
    assert humidity_shelf_coeffs(10.0, 44100, 1.0) is not None
    assert humidity_shelf_coeffs(10.0, 44100, 0.0) is None
    inj_off = build_inject_from_taps(
        [T()], 64, 44100, 340.0, 4, channel="l",
        humidity=1.0, air_lp=0.0, air_shelf=0.0,
    )
    assert float(np.max(np.abs(inj_off[1:]))) == 0.0
    inj_lp = build_inject_from_taps(
        [T()], 64, 44100, 340.0, 4, channel="l",
        humidity=1.0, air_lp=1.0, air_shelf=0.0,
    )
    inj_sh = build_inject_from_taps(
        [T()], 64, 44100, 340.0, 4, channel="l",
        humidity=1.0, air_lp=0.0, air_shelf=1.0,
    )
    assert float(np.max(np.abs(inj_lp[1:, 0]))) > 0.0
    assert float(np.max(np.abs(inj_sh[1:, 0]))) > 0.0


def test_mic_power_cutoff() -> None:
    """466 Gain=1-(2|Dir|)^C/O. 410 P=FtoP(Res)×Gain. On-axis fc=Res."""
    from early_field import (
        mic_power_gain, mic_cutoff_hz, f_to_p, p_to_f, MIC_RES_HZ,
        clamp_mic_res_hz, MIC_RES_MIN, MIC_RES_MAX,
    )
    assert abs(mic_power_gain(0.0, 1.0) - 1.0) < 1e-12
    assert abs(mic_power_gain(0.5, 1.0) - 0.0) < 1e-12  # 2*|0.5|=1
    g = mic_power_gain(0.17, 1.0)
    assert 0.65 < g < 0.67  # 1-0.34
    assert abs(p_to_f(f_to_p(20000.0)) - 20000.0) < 1e-6
    assert abs(mic_cutoff_hz(20000.0, 1.0) - 20000.0) < 1e-6
    assert MIC_RES_HZ == 10000.0
    assert clamp_mic_res_hz(5000.0) == MIC_RES_MIN
    assert clamp_mic_res_hz(25000.0) == MIC_RES_MAX
    assert abs(mic_cutoff_hz(MIC_RES_HZ, 1.0) - 10000.0) < 1e-6
    assert mic_cutoff_hz(MIC_RES_HZ, 0.0) < 10.0
    assert mic_cutoff_hz(MIC_RES_HZ, 0.5) < mic_cutoff_hz(MIC_RES_HZ, 1.0)


def test_agc_detector_is_sum_of_one_over_r_squared() -> None:
    """260: 1/√ of the Fr.V sum; 256 AGC In is already 1/r². Then 1/x."""
    from fdn import structure_agc_on_send
    import math
    geo = [1.0 / (d * d) for d in (1.0, 2.0, 4.0)]
    s = sum(geo)
    send = structure_agc_on_send(geo)
    inv_sqrt = s ** -0.5
    assert abs(send - math.sqrt(s)) < 1e-12
    assert abs(send - (1.0 / inv_sqrt)) < 1e-12
    assert structure_agc_on_send([]) == 0.0
    assert structure_agc_on_send([-1.0, 0.0]) == 0.0


def test_dffs_coeff_matches_structure_snapshot() -> None:
    """462–465: Dffs = Dis × Dff × (1/Diffusion). 202.633 is 1/x **in**."""
    from fdn import dffs_coeff, FDN
    import numpy as np
    g1 = dffs_coeff(83.6099, -0.46, 202.633)
    assert abs(g1 - (-0.189804)) < 1e-5, g1
    g32 = dffs_coeff(241.86, -0.29, 202.633)
    assert abs(g32 - (-0.346139)) < 1e-3, g32
    assert dffs_coeff(47.9665, 0.0, 202.633) == 0.0
    assert dffs_coeff(10.0, -0.5, 0.0) == 0.0
    assert dffs_coeff(1000.0, -1.0, 1.0) == -1.0
    assert dffs_coeff(1000.0, 1.0, 1.0) == 1.0
    from fdn import dff_after_master
    # 463 v1: Floor 0.27 + Ceiling 0.65, Master −0.5
    assert abs(dff_after_master(0.27 + 0.65, -0.5) - (-0.46)) < 1e-12
    assert dff_after_master(0.0, -0.5) == 0.0
    from fdn import diffusion_scale_from_room, DFFS_KNOB_DEFAULT
    # 276: max × mean × knob. 395 room 57×34.241×97; 464 Diffusion in 202.633
    sc1 = diffusion_scale_from_room((57.0, 34.241, 97.0), knob=1.0)
    assert abs(sc1 - 97.0 * (57.0 + 34.241 + 97.0) / 3.0) < 1e-6
    sc = diffusion_scale_from_room((57.0, 34.241, 97.0))
    assert abs(sc - 202.633) < 2.0
    assert abs(DFFS_KNOB_DEFAULT - 202.633 / sc1) < 1e-4
    delays = [8, 8, 8, 8]
    room = (5.0, 3.0, 7.0)
    n_samp = 32
    inj = np.zeros((n_samp, 4), dtype=np.float64)
    inj[0, 0] = 1.0
    a = FDN(delays, g=0.0, room=room, peaking=False, n=4)
    b = FDN(delays, g=0.0, room=room, peaking=False, n=4, dffs=[0.0, 0.0, 0.0, 0.0])
    La, Ra = a.process_block(inj.copy())
    Lb, Rb = b.process_block(inj.copy())
    assert np.allclose(La, Lb) and np.allclose(Ra, Rb)
    # |Dffs|=1, g_loop=0: delay disappears (NI: out ≈ ±in)
    c = FDN(delays, g=0.0, room=room, peaking=False, n=4, dffs=[1.0, 0.0, 0.0, 0.0])
    Lc, _Rc = c.process_block(inj.copy())
    assert abs(float(Lc[0]) + 1.0) < 1e-12


def test_hadamard_rows_match_structure_samples() -> None:
    """Voice 1 all+ (224); Voice 2 even −x (225). Sylvester rows 0 and 1."""
    from fdn import unscaled_hadamard_signs
    H = unscaled_hadamard_signs(32)
    assert all(v == 1 for v in H[0])
    assert H[1] == [1 if (i % 2 == 0) else -1 for i in range(32)]


def test_fdn_unscaled_hadamard_no_inv_sqrt() -> None:
    """FDN matrix is ±1 only; no 1/√N; g clamp in (0,1). Do not invent OCR rows."""
    from fdn import unscaled_hadamard_signs, FDN32, propose_fdn_delays_samples
    H = unscaled_hadamard_signs(32)
    assert len(H) == 32 and all(len(r) == 32 for r in H)
    for r in H:
        for v in r:
            assert v in (-1, 1)
    # No scaling factor baked in
    assert all(abs(abs(v) - 1.0) < 1e-15 for r in H for v in r)
    delays = propose_fdn_delays_samples(5.0, 3.0, 7.0)
    fdn = FDN32(delays, g=1.5, room=(5.0, 3.0, 7.0), peaking=False)
    import math
    lim = 0.99 / math.sqrt(32.0)
    assert 0.0 <= fdn.g <= lim + 1e-12
    assert abs(fdn.g - lim) < 1e-12
    fdn2 = FDN32(delays, g=-0.2, room=(5.0, 3.0, 7.0), peaking=False)
    assert abs(fdn2.g - 0.0) < 1e-12
    from fdn import (
        fdn_delays_from_taps,
        build_inject_from_taps,
        mixer_lcr_fold,
        automatic_wet_level,
        MAX_DELAY_MS,
        SAMPLE_RATE_HZ,
    )
    from early_field import compute_taps, MicStand, prepare_direct_field
    import numpy as np
    prep = prepare_direct_field(6.0, 3.0, 8.0, mz=6.5, my=1.5, space=0.17, diverg=0.5, sox=0.5, soz=0.2, mcx=3.0)
    stand = MicStand.from_prepare(prep, car_omni=1.0)
    taps = compute_taps((6.0, 3.0, 8.0), prep.source, stand, hadamard_n=8)
    d_img = fdn_delays_from_taps(taps, n=8)
    assert len(d_img) == 8
    assert min(d_img) >= 2
    cap = int(round(MAX_DELAY_MS * 0.001 * SAMPLE_RATE_HZ))
    d_cap = fdn_delays_from_taps(taps, n=8, max_delay_ms=MAX_DELAY_MS)
    assert max(d_cap) <= cap
    d_l = fdn_delays_from_taps(taps, n=8, channel="l")
    d_r = fdn_delays_from_taps(taps, n=8, channel="r")
    d_c = fdn_delays_from_taps(taps, n=8, channel="c")
    assert len(d_l) == len(d_r) == len(d_c) == 8
    assert all(getattr(t, "distance_c", 0.0) > 0.0 for t in taps)
    L = np.array([1.0, 0.0])
    R = np.array([0.0, 1.0])
    C = np.array([2.0, 2.0])
    Lf, Rf = mixer_lcr_fold(L, R, C)
    assert abs(float(Lf[0]) - 2.0) < 1e-12
    assert abs(float(Rf[1]) - 2.0) < 1e-12
    a = np.ones(64, dtype=np.float64) * 0.5
    b = np.ones(64, dtype=np.float64) * 2.0
    La, Ra = automatic_wet_level(a, a)
    Lb, Rb = automatic_wet_level(b, b)
    rms = lambda x, y: float(np.sqrt(np.mean(0.5 * (x * x + y * y))))
    assert abs(rms(La, Ra) - rms(Lb, Rb)) < 1e-9
    inj = build_inject_from_taps(taps, 64, SAMPLE_RATE_HZ, 340.0, 8, channel="l")
    assert inj.shape == (64, 8)
    assert float(np.max(np.abs(inj[1:]))) == 0.0
    assert float(np.max(np.abs(inj[0]))) > 0.0


def test_surface_reflect_and_rt60_gain() -> None:
    """ASSUMED wall |R| and Decay→Gain. Direct tap stays 1; more absorb → quieter."""
    from pathlib import Path
    import sys
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from render_pipeline import tap_reflect_gain, live_fdn_params
    from fdn import structure_gain_for_rt60
    from surface_colour import default_surfaces
    surfs = default_surfaces()
    g0 = tap_reflect_gain((0, 0, 0), surfs)
    assert abs(g0 - 1.0) < 1e-12
    surfs["E"]["absorb"] = [0.9] * 7
    surfs["F"]["absorb"] = [0.9] * 7
    g_hit = tap_reflect_gain((0, 2, 0), surfs)
    assert 0.0 < g_hit < 0.5
    g_gain = structure_gain_for_rt60([2205, 3307, 4410], rt60_s=1.5, sr=44100, n=32)
    assert 0.0 < g_gain
    assert g_gain <= 0.99 * (32.0 ** 0.5) + 1e-9
    assert structure_gain_for_rt60([2205], rt60_s=0.01, sr=44100, n=32) == 0.0
    p = {
        "W": 6.0, "H": 3.0, "L": 8.0,
        "mz": 6.5, "my": 1.5, "sy": 1.5, "space": 0.17, "diverg": 1.0,
        "sox": 0.5, "soz": 0.4, "mcx": 3.0,
        "sx": 3.0, "sz": 4.1, "mcz": 1.5, "fdn_g": 1.0,
        "fdn_wet": 1.0, "dry_gain": 0.1, "humidity": 0.35, "air_lp": 0.25, "air_shelf": 1.0,
        "surfaces": surfs, "car_omni": 1.0, "mic_response_hz": 10000.0,
        "diffusion_master": -0.5,
    }
    live = live_fdn_params(p)
    assert live["ok"] and live["n"] == 32
    assert "l" in live["buses"] and len(live["buses"]["l"]["delay_ms"]) == 32
    assert max(abs(x) for x in live["buses"]["l"]["dffs"]) <= 0.98 + 1e-9
    assert live["g"] > 0.0
    assert live["mean_delay_ms"] > 1.0
    assert len(live["peaking"]) == 3
    assert any(bank["on"] for bank in live["peaking"])
    assert len(live["buses"]["l"]["air_g"]) == 32
    assert live["buses"]["l"]["air_lp"] > 0.0
    assert live["buses"]["l"]["shelf"][0]["on"] is True
    p_dry = dict(p)
    p_dry["humidity"] = 0.0
    p_dry["fdn_g"] = 0.2
    m_lo = live_fdn_params(p_dry)["makeup"]
    p_dry["fdn_g"] = 1.0
    m_hi = live_fdn_params(p_dry)["makeup"]
    assert 0.05 <= m_hi <= m_lo <= 256.0


def test_mix_buses_independent() -> None:
    """Host dry / Direct / FDN wet are additive. fdn_wet must not cancel or master Direct."""
    from pathlib import Path
    import sys
    import numpy as np
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from early_field import (
        LIVE_32,
        LIVE_32_REAKTOR,
        MicStand,
        allpass_ir_for_stages,
        compute_taps,
        direct_line_index,
        prepare_direct_field,
        precompute_wall_peaking_coeffs,
    )
    from render_pipeline import clip_guard, combined_ir, live_fdn_params

    assert LIVE_32_REAKTOR[2] == (0, 0, 0)
    assert LIVE_32[0] == (0, 2, 0)
    assert LIVE_32[10] == (0, 0, 0)
    p = {
        "W": 6.0, "H": 3.0, "L": 8.0,
        "mz": 6.5, "my": 1.5, "sy": 1.5, "space": 0.17, "diverg": 1.0,
        "sox": 0.5, "soz": 0.4, "mcx": 3.0,
        "sx": 3.0, "sz": 4.1, "mcz": 1.5, "fdn_g": 1.0,
        "fdn_wet": 1.0, "direct_wet": 1.0, "dry_gain": 0.0,
        "humidity": 0.0, "air_lp": 0.0, "air_shelf": 0.0,
        "car_omni": 1.0, "mic_response_hz": 10000.0,
        "diffusion_master": -0.5,
    }
    live = live_fdn_params(p)
    assert live["direct_index"] == 10
    assert live["dry_gain"] == 0.0
    assert live["direct_wet"] == 1.0
    assert 0.05 <= live["makeup"] <= 256.0
    inj_l, inj_c, inj_r = live["buses"]["l"]["inject"], live["buses"]["c"]["inject"], live["buses"]["r"]["inject"]
    di = live["direct_index"]
    fold = abs(inj_l[di] + 0.5 * inj_c[di])
    # D-SRC-DIST-LEVEL. Makeup is the boot offset from the stand, not this
    # scene's source (sx 3.0, sz 4.1). The product is the live fold times
    # that scalar. Measured 0.883 here and 0.672 on the sz 4.75 card below.
    assert 0.45 < fold * live["makeup"] < 0.95
    assert 1.0 < live["direct_makeup"] <= 8.0
    assert max(abs(x) for x in live["buses"]["l"]["dffs"]) <= 0.98 + 1e-9
    p_ortf = dict(p)
    p_ortf.update({
        "sz": 4.75, "humidity": 0.35, "air_lp": 0.25, "air_shelf": 1.0,
        "pattern_l": "cardioid", "pattern_c": "cardioid", "pattern_r": "cardioid",
        "yaw_l_deg": -55, "yaw_c_deg": 0, "yaw_r_deg": 55,
    })
    live_ortf = live_fdn_params(p_ortf)
    di_o = live_ortf["direct_index"]
    assert di_o == 10
    assert 0.45 < abs(
        live_ortf["buses"]["l"]["inject"][di_o] + 0.5 * live_ortf["buses"]["c"]["inject"][di_o]
    ) * live_ortf["makeup"] < 0.95

    prep = prepare_direct_field(
        6.0, 3.0, 8.0, mz=6.5, my=1.5, space=0.17, diverg=1.0, sox=0.5, soz=0.4, mcx=3.0,
    )
    stand = MicStand.from_prepare(prep, car_omni=1.0)
    room = (6.0, 3.0, 8.0)
    taps = compute_taps(room, prep.source, stand, hadamard_n=32)
    assert direct_line_index(taps, 32) == 10
    sr = 44100
    c = 340.0
    wall_cache = precompute_wall_peaking_coeffs(room, sr, c, 1.5)
    ap_cache = {0: None, 1: allpass_ir_for_stages(1, sr), 2: allpass_ir_for_stages(2, sr)}
    delays = [64] * 32
    kw = dict(
        taps=taps, room=room, sr=sr, c=c, wall_cache=wall_cache, ap_cache=ap_cache,
        delays=delays, early_ms=20.0, fdn_ms=60.0, fdn_g=1.0 / 32.0,
        hadamard_n=32, humidity=0.0, air_lp=0.0, air_shelf=0.0,
        early_wet=0.0,
    )

    def e(ir):
        L, R = ir
        return float(np.sqrt(np.mean(0.5 * (L * L + R * R))))

    def crest(ir):
        L, R = ir
        peak = float(max(np.max(np.abs(L)), np.max(np.abs(R)), 1e-12))
        return peak / max(e(ir), 1e-12)

    ir_d = combined_ir(fdn_wet=0.0, direct_wet=1.0, **kw)
    ir_f = combined_ir(fdn_wet=1.0, direct_wet=0.0, **kw)
    ir_h = combined_ir(fdn_wet=0.5, direct_wet=0.0, **kw)
    ir_b = combined_ir(fdn_wet=1.0, direct_wet=1.0, **kw)
    only_d, only_f, half_f, both = e(ir_d), e(ir_f), e(ir_h), e(ir_b)
    assert only_d > 1e-8
    assert only_f > 1e-8
    assert 0.35 < half_f / only_f < 0.65
    assert both > only_d
    # FDN already includes the first hit; adding Direct can cancel at that
    # sample. The Direct fader must still change the mix (not a no-op).
    dL = ir_b[0] - ir_f[0]
    dR = ir_b[1] - ir_f[1]
    assert e((dL, dR)) > 1e-8
    # Direct is a first arrival, not Hadamard hash
    assert crest(ir_d) > 6.0
    assert crest(ir_d) > crest(ir_f)

    quiet = np.array([0.01, -0.01])
    L, R, peak, scale = clip_guard(quiet, quiet)
    assert scale == 1.0
    assert abs(float(L[0]) - 0.01) < 1e-15


def test_desk_fader_and_capsule_weights() -> None:
    """0 dB is gain 1. Default pans are the 477 fold. Mute and phase do what they say."""
    import numpy as np
    from fdn import (
        apply_capsule_weights,
        capsule_speaker_weights,
        fader_db,
        gain_from_db,
        mixer_lcr_fold,
        travel_from_db,
    )

    assert fader_db(0.0) == float("-inf")
    assert abs(fader_db(0.5)) < 1e-9
    assert abs(fader_db(0.02) - (-60.0)) < 1e-6
    assert abs(fader_db(1.0) - 12.0) < 1e-9
    assert abs(travel_from_db(0.0) - 0.5) < 1e-9
    assert gain_from_db(0.0, 0.0) == 1.0
    assert abs(gain_from_db(0.0, 6.0) - 10 ** (6.0 / 20.0)) < 1e-9
    assert gain_from_db(float("-inf"), 6.0) == 0.0

    L = np.array([1.0, 0.0])
    C = np.array([2.0, 2.0])
    R = np.array([0.0, 1.0])
    folded = mixer_lcr_fold(L, R, C)
    weighted = apply_capsule_weights(L, C, R, capsule_speaker_weights())
    assert abs(float(weighted[0][0] - folded[0][0])) < 1e-12
    assert abs(float(weighted[1][1] - folded[1][1])) < 1e-12
    hard_l = apply_capsule_weights(L, C, R, capsule_speaker_weights(pan_c=-1.0))
    assert abs(float(hard_l[0][0]) - 3.0) < 1e-12
    assert abs(float(hard_l[1][0]) - 0.0) < 1e-12
    muted = apply_capsule_weights(L, C, R, capsule_speaker_weights(gain_c=0.0))
    assert abs(float(muted[0][0]) - 1.0) < 1e-12
    assert abs(float(muted[1][1]) - 1.0) < 1e-12
    flipped = apply_capsule_weights(
        np.array([0.0]), np.array([1.0]), np.array([0.0]),
        capsule_speaker_weights(phase_c=-1.0),
    )
    assert abs(float(flipped[0][0]) - (-0.5)) < 1e-12
    assert abs(float(flipped[1][0]) - (-0.5)) < 1e-12


def test_diffuser_output_mix_holds_decay_lock() -> None:
    """z^-1 loop (D3). First sample is −d·xin. Zero Dffs stays the plain FDN.

    The 32-line closed-loop state matrix at the live g and Dffs stays at or
    under 1. The old memory-mix still grows; it is not the loop.
    """
    from pathlib import Path
    import sys
    import numpy as np
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from fdn import FDN, LOOP_SEMANTICS, loop_hadamard, unscaled_hadamard_matrix
    from render_pipeline import live_fdn_params

    assert LOOP_SEMANTICS == "z1_both"
    delays = [8, 11, 14, 17]
    room = (5.0, 3.0, 7.0)
    dffs = [0.5, -0.25, 0.0, 0.8]
    xin = np.array([1.0, 0.0, 0.0, 0.0])
    for parity in (False, True):
        fdn = FDN(delays, g=0.1, room=room, peaking=False, n=4, dffs=dffs, parity=parity)
        inj = np.zeros((1, 4), dtype=np.float64)
        inj[0, :] = xin
        y = fdn.process_block_poly(inj)[0]
        assert np.allclose(y, -fdn.dffs * xin, atol=1e-12)
    burst = np.zeros((8, 4), dtype=np.float64)
    burst[0, :] = 1.0
    plain = FDN(delays, g=0.1, room=room, peaking=False, n=4).process_block_poly(burst.copy())
    zeros = FDN(delays, g=0.1, room=room, peaking=False, n=4, dffs=[0, 0, 0, 0]).process_block_poly(burst.copy())
    assert np.allclose(plain, zeros)

    p = {
        "W": 6.0, "H": 3.0, "L": 8.0,
        "mz": 6.5, "my": 1.5, "sy": 1.5, "space": 0.17, "diverg": 1.0,
        "sox": 0.5, "soz": 0.4, "mcx": 3.0,
        "sx": 3.0, "sz": 4.75, "mcz": 1.5, "fdn_g": 1.0,
        "fdn_wet": 1.0, "direct_wet": 1.0, "dry_gain": 0.0,
        "humidity": 0.35, "air_lp": 0.25, "air_shelf": 1.0,
        "decay_s": 1.8, "decay_lock": True,
        "pattern_l": "cardioid", "pattern_c": "cardioid", "pattern_r": "cardioid",
        "yaw_l_deg": -55, "yaw_c_deg": 0, "yaw_r_deg": 55,
    }
    live = live_fdn_params(p)
    assert live["g"] > 0.10
    assert live["loop_semantics"] == 0
    assert abs(live["decay_s"] - 1.8) < 1e-9
    assert "loop_mix" not in live["buses"]["l"]
    g = float(live["g"])
    dffs_l = np.asarray(live["buses"]["l"]["dffs"], dtype=np.float64)
    n = 32
    # Short delays keep the exact state matrix small. Loss uses the live T60.
    dly = np.full(n, 4, dtype=int)
    sr = 48000.0
    t60 = float(live["line_t60"])
    lg = np.array([10.0 ** (-3.0 * float(d) / (sr * t60)) for d in dly])
    H = loop_hadamard(n)
    offs = np.concatenate([[0], np.cumsum(dly)[:-1]]).astype(int)
    S = int(dly.sum())
    dim = S + n
    F = np.zeros((dim, dim))
    for k in range(dim):
        x = np.zeros(dim)
        x[k] = 1.0
        reg = x[S:]
        r = np.array([lg[i] * x[offs[i] + dly[i] - 1] for i in range(n)])
        s = reg
        y = -dffs_l * s + r
        newreg = g * (H @ y)
        w = s + dffs_l * y
        col = np.empty(dim)
        for i in range(n):
            a = offs[i]
            col[a] = w[i]
            col[a + 1: a + dly[i]] = x[a: a + dly[i] - 1]
        col[S:] = newreg
        F[:, k] = col
    rho = float(np.max(np.abs(np.linalg.eigvals(F))))
    assert rho <= 1.0 + 1e-9
    G = np.diag(dffs_l)
    bug = (np.eye(n) - G @ G) * g @ unscaled_hadamard_matrix(n) + G
    assert float(np.max(np.abs(np.linalg.eigvals(bug)))) > 1.0


def test_decay_lock_lengthens_tail() -> None:
    """Armed Decay (UI default 1.8 s) must outrun Structure Gain 1 and duck onset makeup."""
    from render_pipeline import live_fdn_params

    p = {
        "W": 6.0, "H": 3.0, "L": 8.0,
        "mz": 6.5, "my": 1.5, "sy": 1.5, "space": 0.17, "diverg": 1.0,
        "sox": 0.5, "soz": 0.4, "mcx": 3.0,
        "sx": 3.0, "sz": 4.75, "mcz": 1.5, "fdn_g": 1.0,
        "fdn_wet": 1.0, "direct_wet": 1.0, "dry_gain": 0.0,
        "humidity": 0.35, "air_lp": 0.25, "air_shelf": 1.0,
        "decay_s": 1.8, "decay_lock": False,
    }
    off = live_fdn_params(p)
    on = live_fdn_params(dict(p, decay_lock=True))
    assert off["decay_s"] < 0.4
    assert abs(on["decay_s"] - 1.8) < 1e-9
    assert on["g"] > off["g"] * 2.0
    assert on["makeup"] < off["makeup"]


def test_two_source_balance_mirror_and_split() -> None:
    """ASSUMED stereo split. Centre (1, 1), hard A (1, 0), hard B (0, 1), mirror is W−sx."""
    from pathlib import Path
    import sys
    import numpy as np
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from render_pipeline import (
        live_fdn_params,
        mirror_source_b,
        render,
        source_balance_gains,
        two_source_excitation,
    )
    from early_field import image_position
    from app_server import params_from_body

    assert source_balance_gains(0.0) == (1.0, 1.0)
    assert source_balance_gains(-1.0) == (1.0, 0.0)
    assert source_balance_gains(1.0) == (0.0, 1.0)
    ga, gb = source_balance_gains(-0.25)
    assert ga == 1.0 and abs(gb - 0.75) < 1e-12
    ga, gb = source_balance_gains(0.4)
    assert abs(ga - 0.6) < 1e-12 and gb == 1.0
    assert mirror_source_b(6.0, 1.5, 1.2, 4.0) == (4.5, 1.2, 4.0)

    left = np.array([1.0, 0.0, 0.5])
    right = np.array([0.0, 1.0, 0.25])
    a, b, down, ga, gb = two_source_excitation(left, right, -1.0)
    assert ga == 1.0 and gb == 0.0
    assert np.allclose(a, left)
    assert np.allclose(b, 0.0)
    assert np.allclose(down, 0.5 * left)
    a, b, down, _, _ = two_source_excitation(left, right, 0.0)
    assert np.allclose(down, 0.5 * (left + right))

    room = (6.0, 3.0, 8.0)
    src_a = (1.25, 1.1, 3.4)
    src_b = mirror_source_b(room[0], *src_a)
    ks = (-2, -1, 0, 1, 2)
    ax = sorted(round(image_position(src_a, room, (k, 0, 0))[0], 6) for k in ks)
    bx = sorted(round(image_position(src_b, room, (k, 0, 0))[0], 6) for k in ks)
    mx = sorted(round(room[0] - image_position(src_a, room, (k, 0, 0))[0], 6) for k in ks)
    assert bx == mx

    body = {
        "W": 6.0, "H": 3.0, "L": 8.0,
        "sx": 1.0, "sy": 1.2, "sz": 4.0,
        "two_sources": True, "mirror_b": True,
        "sx_b": 0.2, "sy_b": 0.2, "sz_b": 0.2,
        "source_balance": -1.0,
    }
    parsed = params_from_body(body)
    assert abs(parsed["sx_b"] - (6.0 - parsed["sx"])) < 1e-9
    assert abs(parsed["sy_b"] - parsed["sy"]) < 1e-9
    assert abs(parsed["sz_b"] - parsed["sz"]) < 1e-9
    assert parsed["source_balance"] == -1.0

    p = {
        "W": 6.0, "H": 3.0, "L": 8.0,
        "mz": 6.5, "my": 1.5, "sy": 1.5, "space": 0.17, "diverg": 1.0,
        "sox": 0.5, "soz": 0.4, "mcx": 3.0,
        "sx": 1.0, "sz": 4.0, "mcz": 1.5, "fdn_g": 1.0,
        "fdn_wet": 1.0, "direct_wet": 1.0, "dry_gain": 0.0,
        "humidity": 0.0, "air_lp": 0.25, "air_shelf": 1.0,
        "decay_lock": False,
    }
    off = live_fdn_params(p)
    assert off["two_sources"] is False
    assert "b" not in off["buses"]["l"]
    assert off["gain_a"] == 1.0 and off["gain_b"] == 1.0
    on = live_fdn_params(dict(
        p, two_sources=True, mirror_b=True, source_balance=-1.0,
    ))
    assert on["gain_a"] == 1.0 and on["gain_b"] == 0.0
    assert abs(on["source_b"]["x"] - 5.0) < 1e-9
    assert abs(on["source_b"]["y"] - p["sy"]) < 1e-9
    assert abs(on["source_b"]["z"] - p["sz"]) < 1e-9
    di = int(on["direct_index"])
    bb = on["buses"]["l"]["b"]
    assert len(bb["delay_ms"]) == 32 and len(bb["inject"]) == 32
    assert abs(bb["delay_ms"][di] - on["buses"]["l"]["delay_ms"][di]) > 0.05
    centre = live_fdn_params(dict(
        p, two_sources=True, mirror_b=False, source_balance=0.0,
        sx_b=4.2, sy_b=1.1, sz_b=2.0,
    ))
    assert centre["gain_a"] == 1.0 and centre["gain_b"] == 1.0
    assert abs(centre["source_b"]["x"] - 4.2) < 1e-9
    hard_b = live_fdn_params(dict(p, two_sources=True, mirror_b=True, source_balance=1.0))
    assert hard_b["gain_a"] == 0.0 and hard_b["gain_b"] == 1.0

    sr = 8000
    n = 64
    impulse = np.zeros(n, dtype=np.float64)
    impulse[0] = 1.0
    silence = np.zeros(n, dtype=np.float64)
    common = dict(
        W=6.0, H=3.0, L=8.0,
        sox=0.2, soz=0.5, mz=6.5, my=1.5, sy=1.5,
        sx=1.0, sz=4.0, mcz=1.5,
        space=0.17, diverg=1.0, car_omni=1.0,
        early_wet=0.0, fdn_wet=0.0, dry_gain=0.0, direct_wet=1.0,
        fdn_g=1.0, ir_length_ms=40.0,
        path_on=False, path_preset="still",
        yaw_l_deg=-55.0, yaw_c_deg=0.0, yaw_r_deg=55.0,
        humidity=0.0, decay_lock=False,
        two_sources=True, mirror_b=True,
    )
    hard_a_l, hard_a_r, _info = render(
        impulse, sr, dry_l=impulse, dry_r=impulse, source_balance=-1.0, **common,
    )
    right_only_l, right_only_r, _info = render(
        silence, sr, dry_l=silence, dry_r=impulse, source_balance=-1.0, **common,
    )
    assert float(np.max(np.abs(right_only_l))) < 1e-8
    assert float(np.max(np.abs(right_only_r))) < 1e-8
    assert float(np.max(np.abs(hard_a_l))) > 1e-4
    left_b, _right_b, _info = render(
        impulse, sr, dry_l=silence, dry_r=impulse, source_balance=1.0, **common,
    )
    t_a = int(np.argmax(np.abs(hard_a_l)))
    t_b = int(np.argmax(np.abs(left_b)))
    assert t_a != t_b
    # K1 locked 28 Sep 2026 (YAW_X_SIGN = +1): ORTF capsules aim OUTWARD, so the source on the
    # visual left is hotter in the LEFT capsule (was: right capsule, crossed).
    a_l_e = float(np.dot(hard_a_l, hard_a_l))
    a_r_e = float(np.dot(hard_a_r, hard_a_r))
    b_l_e = float(np.dot(left_b, left_b))
    b_r_e = float(np.dot(_right_b, _right_b))
    assert a_l_e > a_r_e * 1.05
    assert b_r_e > b_l_e * 1.05
    assert "direct_gain" not in off["buses"]["l"]
    # Measured holds the polar in the fitter, so the broadband spike is flat.
    assert abs(on["buses"]["l"]["direct_gain"] - on["buses"]["r"]["direct_gain"]) < 1e-9
    assert abs(on["buses"]["r"]["b"]["direct_gain"] - on["buses"]["l"]["b"]["direct_gain"]) < 1e-9
    assert len(on["buses"]["l"]["b"]["dffs"]) == 32
    aimed = live_fdn_params(dict(
        p, two_sources=True, mirror_b=True, source_balance=0.0,
        yaw_l_deg=-55.0, yaw_c_deg=0.0, yaw_r_deg=55.0,
    ))
    assert abs(aimed["buses"]["l"]["direct_gain"] - aimed["buses"]["r"]["direct_gain"]) < 1e-9
    assert abs(aimed["buses"]["r"]["b"]["direct_gain"] - aimed["buses"]["l"]["b"]["direct_gain"]) < 1e-9
    tail = dict(common, direct_wet=0.0, fdn_wet=1.0, ir_length_ms=60.0)
    ta_l, ta_r, _info = render(
        impulse, sr, dry_l=impulse, dry_r=silence, source_balance=-1.0, **tail,
    )
    tb_l, tb_r, _info = render(
        impulse, sr, dry_l=silence, dry_r=impulse, source_balance=1.0, **tail,
    )
    quiet_l, quiet_r, _info = render(
        silence, sr, dry_l=silence, dry_r=impulse, source_balance=-1.0, **tail,
    )
    assert float(np.max(np.abs(quiet_l))) < 1e-8
    assert float(np.max(np.abs(quiet_r))) < 1e-8
    # K1 (28 Sep 2026): FDN tail follows the outward-aimed capsules too (was crossed).
    assert float(np.dot(ta_l, ta_l)) > float(np.dot(ta_r, ta_r))
    assert float(np.dot(tb_r, tb_r)) > float(np.dot(tb_l, tb_l))


def test_surf_default_fit_within_quarter_db() -> None:
    """D-UI26=A. Default cards: every LIVE_32 line fits within 0.25 dB."""
    from pathlib import Path
    import sys
    soft = Path(__file__).resolve().parent.parent
    if str(soft) not in sys.path:
        sys.path.insert(0, str(soft))
    import render_pipeline as rp
    import surface_colour as sc

    class _Tap:
        def __init__(self, n):
            self.n = n

    taps = [_Tap(n) for n in LIVE_32]
    tail, report = rp._play_surf_cascade(sc.default_surfaces(), taps, None, 48000.0, 32, False)
    line = report.get("worst_line")
    print(
        f"  SURF worst line {line} residual {float(report['worst_db']):.4f} dB"
        f" k_max {report.get('k_max')}"
    )
    assert tail is not None and report.get("k_max", 0) >= 1
    assert len(tail) == 2 + 64 * (1 + 5 * int(report["k_max"]))
    assert float(report["worst_db"]) <= 0.25
    assert not report.get("misses")


def _mic_colour_tests():
    from pathlib import Path
    import sys
    soft = Path(__file__).resolve().parent.parent
    if str(soft) not in sys.path:
        sys.path.insert(0, str(soft))
    import tests.test_mic_colour_relative as mic_tests
    return list(mic_tests.TESTS)


def main() -> int:
    tests = [
        test_32_indices_exact_set,
        test_scaled_grid_presets,
        test_omit_0_0_minus2,
        test_polarity_formula,
        test_direct_no_allpass,
        test_distance_euclidean_and_angle_is_xz_dot,
        test_air_abs_one_over_r,
        test_wall_combo_once_per_axis,
        test_corner_macros_and_c340,
        test_verified_mirror_leaf_algebra,
        test_verified_prepare_mcz_and_mics,
        test_direct_field_from_metres_identity,
        test_press_grad_and_ms_decode,
        test_first_order_polar_slider,
        test_absorb_masks_reverified,
        test_to_v_tables_verified_subset,
        test_data_tables_not_imported_by_audio,
        test_air_abs_one_pole_cutoff_and_inject,
        test_mic_power_cutoff,
        test_agc_detector_is_sum_of_one_over_r_squared,
        test_dffs_coeff_matches_structure_snapshot,
        test_hadamard_rows_match_structure_samples,
        test_fdn_unscaled_hadamard_no_inv_sqrt,
        test_surface_reflect_and_rt60_gain,
        test_mix_buses_independent,
        test_desk_fader_and_capsule_weights,
        test_diffuser_output_mix_holds_decay_lock,
        test_decay_lock_lengthens_tail,
        test_two_source_balance_mirror_and_split,
    ]
    mic_tests = _mic_colour_tests()
    failed = 0
    n = 0

    def _run(seq):
        nonlocal failed, n
        for fn in seq:
            n += 1
            try:
                fn()
                print(f"PASS  {fn.__name__}")
            except AssertionError as e:
                failed += 1
                print(f"FAIL  {fn.__name__}: {e}")
            except Exception as e:
                failed += 1
                print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")

    _run(tests)
    # live_fdn_params fits the cascade and imports scipy. The mic checks
    # assert that importing mic_colour does not load scipy.
    import sys
    for key in list(sys.modules):
        if key == "scipy" or key.startswith("scipy.") or key == "mic_fitter" or key.startswith("mic_fitter."):
            del sys.modules[key]
    _run(mic_tests)
    _run([test_surf_default_fit_within_quarter_db])
    print()
    if failed:
        print(f"{failed}/{n} failed")
        return 1
    print(f"All {n} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
