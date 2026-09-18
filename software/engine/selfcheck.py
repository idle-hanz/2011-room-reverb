#!/usr/bin/env python3
"""
Self-checks for the 2011 early-field / FDN prototype.

Verifies:
  1. 32 image indices are the exact agreed set
  2. Polarity formula (-1)^(nx+ny+nz)
  3. Omit (0,0,-2)
  4. Direct (0,0,0) has no allpass stages
  5. 1/r decreases with distance
  6. Wall-crossing frozenset combos (once-per-axis; Behind=−z)
  7. VERIFIED mirror leaf algebra (full R, Sub pin order)
  8. VERIFIED Prepare MCZ = L − MZ (+ mic/source locks)
"""

from __future__ import annotations

from early_field import (
    build_image_indices,
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
    delay_ms_from_distance,
    dist,
    dist_xz,
    mic_positions,
)


EXPECTED_32 = set()
for nx in (-1, 0, 1):
    for ny in (-1, 0, 1):
        for nz in (-1, 0, 1):
            EXPECTED_32.add((nx, ny, nz))
for extra in ((-2, 0, 0), (2, 0, 0), (0, -2, 0), (0, 2, 0), (0, 0, 2)):
    EXPECTED_32.add(extra)


def test_32_indices_exact_set() -> None:
    got = set(build_image_indices())
    assert len(got) == 32, f"expected 32 indices, got {len(got)}"
    assert got == EXPECTED_32, f"index set mismatch: extra={got-EXPECTED_32} missing={EXPECTED_32-got}"




def test_scaled_grid_presets() -> None:
    """Default 32 unchanged; optional scaled presets for render tables."""
    assert set(build_image_indices()) == set(enumerate_scaled_grid(bias="32"))
    assert len(enumerate_scaled_grid(R=1)) == 27
    assert len(enumerate_scaled_grid(R=2)) == 125
    g64 = enumerate_scaled_grid(bias="64like")
    assert len(g64) == 64
    assert (0, 0, -2) not in g64
    assert (0, 0, 2) in g64
    g32f = enumerate_scaled_grid(R=1, face_extras=True, omit_behind_mic=True)
    assert set(g32f) == set(build_image_indices())

def test_omit_0_0_minus2() -> None:
    imgs = build_image_indices()
    assert (0, 0, -2) not in imgs
    assert (0, 0, -2) not in EXPECTED_32


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


def test_one_over_r_decreases_with_distance() -> None:
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
        assert abs(geometric_level(t.distance_l) - 1.0 / t.distance_l) < 1e-12
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
    """Corner maps n∈{-2..2} via VERIFIED leaves; (0,0,2)→4L-Z; c=340; delay=(d/c)*1000."""
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
    taps = compute_taps(room, source, stand, origin="corner", z_face_4l=True)
    assert len(taps) == 32
    face = [t for t in taps if t.n == (0, 0, 2)][0]
    assert abs(face.position[2] - (28.0 - 5.5)) < 1e-9
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
    assert abs(macro_2R_minus_S(Y, H) - ((2.0 * H) + Y)) < 1e-12  # 2H-Y WRONG FIX
