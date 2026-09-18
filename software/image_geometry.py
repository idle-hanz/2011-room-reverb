#!/usr/bin/env python3
"""Image-source geometry for early-field visualization.

Lattice cells, folded in-room specular paths, and last-leg arrival rays.
Reuses VERIFIED early_field algebra only — no invented A–F / Hadamard tables.

Folding (method of images):
  The straight line from image source to mic in unfolded space is folded back
  into the home room [0,W]x[0,H]x[0,L] by reflecting across wall planes at
  integer multiples of W/H/L. Crossing a plane becomes a wall bounce; the
  polyline inside the real room is the classic zigzag specular path.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_ENGINE = Path(__file__).resolve().parent / "engine"
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from early_field import (  # noqa: E402
    DEFAULT_HADAMARD_N,
    SPEED_OF_SOUND_M_S,
    build_image_indices,
    delay_ms_from_distance,
    dist,
    grid_bias_for_hadamard_n,
    hadamard_n_for_grid,
    image_order,
    image_position,
    normalize_hadamard_n,
    polarity,
    prepare_direct_field,
)
from surface_colour import (  # noqa: E402
    last_hit_letter_from_n,
    surfaces_hit_by_n,
)

Vec3 = Tuple[float, float, float]
Index3 = Tuple[int, int, int]


def fold_coord(x: float, R: float) -> float:
    """Map an unfolded axis coordinate into [0, R] via even/odd mirror tiling."""
    if R <= 1e-15:
        return 0.0
    period = 2.0 * R
    m = math.fmod(x, period)
    if m < 0.0:
        m += period
    if m <= R:
        return m
    return period - m


def fold_point(p: Vec3, room: Vec3) -> Vec3:
    W, H, L = room
    return (fold_coord(p[0], W), fold_coord(p[1], H), fold_coord(p[2], L))


def folded_polyline(
    image: Vec3,
    mic: Vec3,
    room: Vec3,
    *,
    eps: float = 1e-9,
) -> List[Vec3]:
    """Fold the straight image->mic segment into the home room as a polyline.

    Wall crossings at planes x=kW, y=kH, z=kL become bounce vertices.
    """
    W, H, L = room
    p0, p1 = image, mic
    ts: List[float] = [0.0]
    for axis, R in enumerate((W, H, L)):
        a0, a1 = p0[axis], p1[axis]
        da = a1 - a0
        if abs(da) < eps:
            continue
        lo, hi = (a0, a1) if a0 < a1 else (a1, a0)
        k = math.floor(lo / R) + 1
        while k * R < hi - eps:
            plane = k * R
            t = (plane - a0) / da
            if eps < t < 1.0 - eps:
                ts.append(t)
            k += 1
    ts.append(1.0)
    uniq = sorted(set(round(t, 12) for t in ts))
    pts: List[Vec3] = []
    for t in uniq:
        p = (
            p0[0] + t * (p1[0] - p0[0]),
            p0[1] + t * (p1[1] - p0[1]),
            p0[2] + t * (p1[2] - p0[2]),
        )
        fp = fold_point(p, room)
        if not pts or math.dist(pts[-1], fp) > 1e-6:
            pts.append(fp)
    return pts


def wall_letter_at_point(p: Vec3, room: Vec3, eps: float = 1e-4) -> Optional[str]:
    """Which A–F wall a bounce vertex sits on (closest plane). ASSUMED geometric."""
    W, H, L = room
    x, y, z = p
    scores = [
        (abs(x - 0.0), "A"),
        (abs(x - W), "C"),
        (abs(y - 0.0), "E"),
        (abs(y - H), "F"),
        (abs(z - 0.0), "D"),
        (abs(z - L), "B"),
    ]
    scores.sort(key=lambda t: t[0])
    if scores[0][0] > eps:
        return None
    return scores[0][1]


def last_hit_letter(
    image: Vec3,
    mic: Vec3,
    room: Vec3,
    n: Optional[Index3] = None,
    *,
    eps: float = 1e-9,
) -> Optional[str]:
    """Last wall bounce on the folded image→mic path.

    Uses the last polyline vertex on a wall; falls back to image-index parity
    (surfaces_hit_by_n) if the path has no bounce.
    """
    path = folded_polyline(image, mic, room, eps=eps)
    if len(path) >= 3:
        letter = wall_letter_at_point(path[-2], room)
        if letter:
            return letter
    if n is not None:
        return last_hit_letter_from_n(n)
    return None


def cell_bounds(n: Index3, room: Vec3) -> Dict[str, Vec3]:
    """AABB of mirrored room cell for image index n (corner-origin lattice)."""
    W, H, L = room
    nx, ny, nz = n
    mn = (nx * W, ny * H, nz * L)
    mx = ((nx + 1) * W, (ny + 1) * H, (nz + 1) * L)
    ctr = (0.5 * (mn[0] + mx[0]), 0.5 * (mn[1] + mx[1]), 0.5 * (mn[2] + mx[2]))
    return {"min": mn, "max": mx, "center": ctr}


def _v(p: Vec3) -> Dict[str, float]:
    return {"x": float(p[0]), "y": float(p[1]), "z": float(p[2])}


def _poly(pts: Sequence[Vec3]) -> List[Dict[str, float]]:
    return [_v(p) for p in pts]


def build_images_payload(
    *,
    W: float,
    H: float,
    L: float,
    mz: float,
    my: float,
    space: float,
    diverg: float,
    sox: float,
    soz: float,
    mcx: Optional[float] = None,
    toe_half_deg: Optional[float] = None,
    mics: Optional[Sequence[str]] = None,
    origin: str = "corner",
    z_face_4l: bool = True,
    c: float = SPEED_OF_SOUND_M_S,
    hadamard_n: Optional[int] = None,
    grid: Optional[str] = None,
    sy: Optional[float] = None,
) -> dict:
    """JSON payload for Lattice / In-room / Last-leg views.

    mics: subset of {"L","C","R"}; default ["C"].
    hadamard_n / grid: select exactly N image indices (default 32).
    sy: optional absolute source height (None → VERIFIED SY=MY).
    """
    prep = prepare_direct_field(
        W, H, L,
        mz=mz, my=my, space=space, diverg=diverg, sox=sox, soz=soz, mcx=mcx,
        toe_half_deg=toe_half_deg,
        sy=sy,
    )
    room: Vec3 = (float(W), float(H), float(L))
    source = prep.source
    mic_map = {
        "L": prep.mic_left,
        "C": prep.mic_centre,
        "R": prep.mic_right,
    }
    wanted = [m.upper() for m in (mics or ["C"])]
    wanted = [m for m in wanted if m in mic_map]
    if not wanted:
        wanted = ["C"]

    if hadamard_n is not None:
        n_had = normalize_hadamard_n(hadamard_n)
    elif grid is not None:
        n_had = hadamard_n_for_grid(grid)
    else:
        n_had = DEFAULT_HADAMARD_N
    indices = build_image_indices(n_had)
    images_out: List[dict] = []
    by_mic: Dict[str, List[dict]] = {m: [] for m in wanted}

    for i, n in enumerate(indices):
        img_xyz = image_position(source, room, n, origin=origin, z_face_4l=z_face_4l)
        pol = int(polarity(n))
        order = int(image_order(n))
        bounds = cell_bounds(n, room)
        entry = {
            "index": i,
            "n": [int(n[0]), int(n[1]), int(n[2])],
            "order": order,
            "polarity": pol,
            "image_xyz": _v(img_xyz),
            "cell": {
                "min": _v(bounds["min"]),
                "max": _v(bounds["max"]),
                "center": _v(bounds["center"]),
            },
            "is_home": n == (0, 0, 0),
        }
        images_out.append(entry)

        for mic_id in wanted:
            mic = mic_map[mic_id]
            d = dist(img_xyz, mic)
            delay = delay_ms_from_distance(d, c)
            path = folded_polyline(img_xyz, mic, room)
            if len(path) >= 2:
                last_from, last_to = path[-2], path[-1]
            else:
                last_from, last_to = path[0], mic
            dx = last_to[0] - last_from[0]
            dy = last_to[1] - last_from[1]
            dz = last_to[2] - last_from[2]
            norm = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
            last_hit = None if n == (0, 0, 0) else (
                wall_letter_at_point(last_from, room) if len(path) >= 3 else last_hit_letter_from_n(n)
            )
            hits = surfaces_hit_by_n(n)
            by_mic[mic_id].append({
                "index": i,
                "n": entry["n"],
                "order": order,
                "polarity": pol,
                "image_xyz": entry["image_xyz"],
                "dist_m": float(d),
                "delay_ms": float(delay),
                "path": _poly(path),
                "last_leg": {
                    "from": _v(last_from),
                    "to": _v(last_to),
                    "dir": {"x": dx / norm, "y": dy / norm, "z": dz / norm},
                },
                "last_hit": last_hit,
                "hit_surfaces": hits,
                "is_direct": n == (0, 0, 0),
            })

    return {
        "room": {"W": float(W), "H": float(H), "L": float(L)},
        "source": _v(source),
        "mics": {k: _v(mic_map[k]) for k in ("L", "C", "R")},
        "selected_mics": wanted,
        "c": float(c),
        "origin": origin,
        "hadamard_n": int(n_had),
        "grid": grid_bias_for_hadamard_n(n_had),
        "count": len(indices),
        "lattice": images_out,
        "per_mic": by_mic,
    }


if __name__ == "__main__":
    payload = build_images_payload(
        W=6, H=3, L=8, mz=6.5, my=1.5, space=0.25,
        diverg=1.0, sox=0.5, soz=0.5, mcx=3.0, mics=["C", "L", "R"],
    )
    print("count", payload["count"], "mics", payload["selected_mics"])
    c0 = payload["per_mic"]["C"][0]
    print("direct path", c0["path"], "delay", round(c0["delay_ms"], 3))
