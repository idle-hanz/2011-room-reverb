#!/usr/bin/env python3
"""
Minimal polygonal image-source API stub (NOT a full beam tracer).

Live product path remains shoebox cubic tables (bias=32). Non-cubic /
irregular rooms are a later render tier — see /workspace/non-cubic-rooms.md.

This module only sketches:
  * planar mirror of a point through a facet plane
  * a visibility / occlusion stop rule (commented algorithm)
  * a tiny 2D rectangle-with-notch toy to show corner occlusion

Tags: proposal / literature (Borish, Funkhouser, interactiveacoustics).
Do not claim this restores anything from 2011-room-reverb.ens.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]


@dataclass(frozen=True)
class Plane3:
    """Infinite supporting plane: n·x = d  (n unit preferred)."""

    n: Vec3
    d: float


@dataclass(frozen=True)
class Facet:
    """Finite planar mirror fragment (polygon in 3D or segment in 2D toy)."""

    plane: Plane3
    # Optional polygon vertices in plane (unused by mirror math; for visibility later)
    verts: Tuple[Vec3, ...] = ()
    name: str = ""


def _dot3(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub3(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add3(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale3(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def _norm3(a: Vec3) -> float:
    return math.sqrt(_dot3(a, a))


def mirror_point_through_plane(p: Vec3, plane: Plane3) -> Vec3:
    """Reflect point p through infinite plane n·x = d.

    p' = p - 2 ((n·p - d) / ||n||^2) n
    """
    n = plane.n
    nn = _dot3(n, n)
    if nn <= 1e-18:
        raise ValueError("degenerate plane normal")
    t = (_dot3(n, p) - plane.d) / nn
    return _sub3(p, _scale3(n, 2.0 * t))


def mirror_point_through_facet(p: Vec3, facet: Facet) -> Vec3:
    """Planar mirror only — does not test whether p projects inside the polygon."""
    return mirror_point_through_plane(p, facet.plane)


# ---------------------------------------------------------------------------
# Visibility / occlusion stop — algorithm comment (not a full beam tracer)
# ---------------------------------------------------------------------------
#
# State for a candidate image I = (p, sequence σ of facets, beam P):
#   p  = mirrored source position
#   σ  = ordered reflecting facets
#   P  = visibility region still reachable through σ (polygon / beam)
#
# Grow (polygonal ISM / beam-style):
#   for each front-facing facet f ≠ last(σ):
#     1. Mirror p through plane(f) → p'
#     2. Intersect current beam P with f; if empty → STOP this branch
#        (occluded / miss — "stop around the corner")
#     3. Else spawn child (p', σ+f, clipped beam)
#
# Validate to listener R:
#   Backtrace R → p' through σ; each hit must land in the finite polygon
#   and the segment must not pierce other occluders.
#
# This stub does NOT implement beam clipping or 3D occlusion. Live FX
# keeps the shoebox lattice. Use the 2D toy below only as a teaching aid.
# ---------------------------------------------------------------------------


@dataclass
class Seg2:
    """Axis-aligned or general wall segment in 2D (a→b)."""

    a: Vec2
    b: Vec2
    name: str = ""


def mirror_point_2d_across_segment(p: Vec2, seg: Seg2) -> Vec2:
    """Reflect 2D point across the infinite line through segment endpoints."""
    ax, ay = seg.a
    bx, by = seg.b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 <= 1e-18:
        raise ValueError("degenerate segment")
    # Project p onto line; reflect
    t = ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2
    qx, qy = ax + t * dx, ay + t * dy
    return (2.0 * qx - p[0], 2.0 * qy - p[1])


def _cross2(ox: float, oy: float, ax: float, ay: float, bx: float, by: float) -> float:
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


def segments_properly_intersect(s1: Seg2, s2: Seg2) -> bool:
    """True if open segments cross (proper intersection, not endpoint-only)."""
    a, b = s1.a, s1.b
    c, d = s2.a, s2.b
    d1 = _cross2(c[0], c[1], d[0], d[1], a[0], a[1])
    d2 = _cross2(c[0], c[1], d[0], d[1], b[0], b[1])
    d3 = _cross2(a[0], a[1], b[0], b[1], c[0], c[1])
    d4 = _cross2(a[0], a[1], b[0], b[1], d[0], d[1])
    if d1 * d2 >= 0 or d3 * d4 >= 0:
        return False
    return True


def path_occluded_2d(
    listener: Vec2,
    image: Vec2,
    occluders: Sequence[Seg2],
) -> bool:
    """Crude LOS test: segment listener→image crosses any occluder."""
    path = Seg2(listener, image, name="path")
    for occ in occluders:
        if segments_properly_intersect(path, occ):
            return True
    return False


def rectangle_with_notch_toy() -> dict:
    """
    Tiny 2D demo: axis-aligned rectangle with a rectangular notch on the
    right wall. Source left of notch; listener around the corner on the
    bottom. First-order mirror through the right outer wall is occluded
    by the notch lip; mirror through an open wall remains visible.

    Returns a small dict of positions / flags for self-demo prints.
    Not used by early_field audio path.
    """
    # Room outline (outer): [0,4] x [0,3] with notch on right: missing
    # (3.5..4) x (1.0..2.0) — notch mouth faces +x.
    walls = [
        Seg2((0.0, 0.0), (4.0, 0.0), "floor"),
        Seg2((4.0, 0.0), (4.0, 1.0), "right_lower"),
        Seg2((4.0, 1.0), (3.5, 1.0), "notch_bottom"),
        Seg2((3.5, 1.0), (3.5, 2.0), "notch_back"),
        Seg2((3.5, 2.0), (4.0, 2.0), "notch_top"),
        Seg2((4.0, 2.0), (4.0, 3.0), "right_upper"),
        Seg2((4.0, 3.0), (0.0, 3.0), "ceiling"),
        Seg2((0.0, 3.0), (0.0, 0.0), "left"),
    ]
    source = (1.0, 1.5)
    # Listener sits in the notch pocket (right of notch_back) — "around the corner"
    listener = (3.7, 1.5)

    # Notch back wall is the corner occluder for pocket ↔ main room
    occluders = [
        Seg2((3.5, 1.0), (3.5, 2.0), "notch_back"),
    ]

    # Direct LOS source→listener crosses notch_back → occluded (stop / drop)
    direct_occluded = path_occluded_2d(listener, source, occluders)

    # Candidate image: mirror source across left wall x=0; path listener→image
    # still crosses notch_back in this geometry → also occluded
    left_wall = Seg2((0.0, 0.0), (0.0, 3.0), "left")
    image_left = mirror_point_2d_across_segment(source, left_wall)
    left_path_occluded = path_occluded_2d(listener, image_left, occluders)

    # Contrast: mirror across notch_back itself (the visible facet from the pocket).
    # Unfolded image sits further right; path listener→image stays in the pocket
    # half-plane and does not cross notch_back → visible (keep).
    notch_back = Seg2((3.5, 1.0), (3.5, 2.0), "notch_back")
    image_notch = mirror_point_2d_across_segment(source, notch_back)
    notch_path_occluded = path_occluded_2d(listener, image_notch, occluders)

    return {
        "walls": walls,
        "source": source,
        "listener": listener,
        "image_left": image_left,
        "image_notch": image_notch,
        "direct_occluded": direct_occluded,
        "left_path_occluded": left_path_occluded,
        "notch_path_occluded": notch_path_occluded,
        "note": "Stop spawning / drop tap when path_occluded (corner occlusion).",
    }


def demo_print() -> None:
    toy = rectangle_with_notch_toy()
    print("polygonal_stub 2D rectangle-with-notch toy")
    print("  source   ", toy["source"])
    print("  listener ", toy["listener"])
    print("  direct LOS occluded=", toy["direct_occluded"], "(expect True — around corner)")
    print("  image_L  ", toy["image_left"], " occluded=", toy["left_path_occluded"], "(expect True)")
    print("  image_N  ", toy["image_notch"], " occluded=", toy["notch_path_occluded"], "(expect False — reflecting facet)")
    print(" ", toy["note"])
    # 3D planar mirror smoke
    plane = Plane3(n=(1.0, 0.0, 0.0), d=2.5)  # x = 2.5
    p = (1.0, 0.0, 0.0)
    p2 = mirror_point_through_plane(p, plane)
    print("  3D mirror through x=2.5:", p, "→", p2)


if __name__ == "__main__":
    demo_print()
