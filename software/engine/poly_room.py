"""Render-only polygon image sources. The shoebox path does not call this.

``room_shape`` absent or ``box`` stays in ``compute_taps``. Three convex presets
scale with W / L / H. Order 4, parent-side prune, distance cut. Thirty-two taps
by the live per-order quota, nearest first, geometry only. FDN lengths are the
path from the stand centre, the same on L, C, and R.

Faces are not mapped onto A–F. Every tap keeps ``n = (0, 0, 0)`` so the shoebox
wall cards, diffusion hits, and surface solo stay off this path.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import numpy as np

from early_field import (
    PATTERN_CARDIOID,
    PATTERN_FIG8,
    ImageTap,
    SPEED_OF_SOUND_M_S,
    arrival_theta_ray,
    capsule_press_grad,
    delay_ms_from_distance,
    dist,
    geometric_level,
    mic_positions,
    offaxis_shelf_gain_linear,
    pattern_from_car_omni,
)

EPS = 1e-9
MAX_DELAY_MS = 1000.0
QUOTA = (1, 6, 11, 10, 4)
Vec3 = Tuple[float, float, float]


def normalize_shape(raw) -> str:
    """Absent, blank, box, or an unknown word is the shoebox."""
    if raw is None:
        return "box"
    key = "".join(ch for ch in str(raw).strip().lower() if ch.isalnum())
    if key in ("", "box", "shoebox"):
        return "box"
    if key in ("splay", "splayed", "rfz", "control", "splayedcontrol", "splayedcontrolroom"):
        return "splay"
    if key in ("lede", "ledestyle"):
        return "lede"
    if key in ("live", "nonparallel", "nonparallellive", "nonparallelliveroom"):
        return "live"
    return "box"


def poly_on(raw) -> bool:
    return normalize_shape(raw) != "box"


class Face:
    """Planar polygon. After ``orient``, the normal points into the room."""

    def __init__(self, name: str, verts):
        self.name = name
        self.v = np.asarray(verts, float)
        n = np.zeros(3)
        m = len(self.v)
        for i in range(m):
            a = self.v[i]
            b = self.v[(i + 1) % m]
            n += np.array(
                [
                    (a[1] - b[1]) * (a[2] + b[2]),
                    (a[2] - b[2]) * (a[0] + b[0]),
                    (a[0] - b[0]) * (a[1] + b[1]),
                ]
            )
        self.n = n / np.linalg.norm(n)
        self.d = float(self.n @ self.v.mean(0))
        self._proj()

    def flip(self) -> None:
        self.n = -self.n
        self.d = -self.d

    def _proj(self) -> None:
        ax = int(np.argmax(np.abs(self.n)))
        keep = [i for i in range(3) if i != ax]
        self.keep = keep
        self.p2 = self.v[:, keep]

    def sd(self, x) -> float:
        return float(self.n @ np.asarray(x, float) - self.d)

    def inside(self, x, tol: float = 1e-7) -> bool:
        """Strictly inside the outline. A point on an edge is outside."""
        p = np.asarray(x, float)
        px = float(p[self.keep[0]])
        py = float(p[self.keep[1]])
        poly = self.p2
        c = False
        m = len(poly)
        for i in range(m):
            x1, y1 = float(poly[i][0]), float(poly[i][1])
            x2, y2 = float(poly[(i + 1) % m][0]), float(poly[(i + 1) % m][1])
            ex, ey = x2 - x1, y2 - y1
            length = math.hypot(ex, ey)
            if length > 0.0:
                t = ((px - x1) * ex + (py - y1) * ey) / (length * length)
                if -1e-9 <= t <= 1.0 + 1e-9 and abs((px - x1) * ey - (py - y1) * ex) / length < tol:
                    return False
            if (y1 > py) != (y2 > py):
                xi = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
                if px < xi:
                    c = not c
        return c

    def mirror(self, x):
        p = np.asarray(x, float)
        return p - 2.0 * self.sd(p) * self.n


def _point_in_room(x, faces) -> bool:
    p = np.asarray(x, float)
    direction = np.array([0.5377, 0.8338, 0.1250])
    direction /= np.linalg.norm(direction)
    far = p + direction * 1e3
    hits = 0
    for face in faces:
        da, db = face.sd(p), face.sd(far)
        if da * db >= 0.0:
            continue
        t = da / (da - db)
        if face.inside(p + t * (far - p), tol=1e-12):
            hits += 1
    return hits % 2 == 1


def orient(faces: Sequence[Face]) -> List[Face]:
    """Turn every normal into the room."""
    for face in faces:
        centre = face.v.mean(0)
        if not face.inside(centre):
            for i in range(1, len(face.v) - 1):
                centre = (face.v[0] + face.v[i] + face.v[i + 1]) / 3.0
                if face.inside(centre):
                    break
        if not _point_in_room(centre + 1e-4 * face.n, faces):
            face.flip()
    return list(faces)


def _prism(floor_xz, height_at) -> List[Face]:
    """Extrude a floor polygon. Y is height. ``height_at(x, z)`` is the ceiling."""
    pts = [(float(x), float(z)) for x, z in floor_xz]
    floor = [(x, 0.0, z) for x, z in pts]
    ceil = [(x, float(height_at(x, z)), z) for x, z in pts]
    faces = [Face("floor", floor), Face("ceiling", ceil)]
    n = len(pts)
    for i in range(n):
        x1, z1 = pts[i]
        x2, z2 = pts[(i + 1) % n]
        y1 = float(height_at(x1, z1))
        y2 = float(height_at(x2, z2))
        faces.append(
            Face(
                f"wall{i}",
                [(x1, 0.0, z1), (x2, 0.0, z2), (x2, y2, z2), (x1, y1, z1)],
            )
        )
    return orient(faces)


def box_faces(W: float, H: float, L: float) -> List[Face]:
    return _prism([(0.0, 0.0), (W, 0.0), (W, L), (0.0, L)], lambda x, z: H)


def faces_for(shape, W: float, H: float, L: float) -> List[Face]:
    """Presets are fractions of the shoebox that contains them."""
    name = normalize_shape(shape)
    W, H, L = float(W), float(H), float(L)
    if name == "splay":
        # Prototype trapezoid 4→6 over length 6, ceiling 2.6→3.2, shifted into the box.
        def h(x, z, H=H, L=L):
            t = 0.0 if L <= 0.0 else z / L
            return H * (0.8125 + 0.1875 * t)

        return _prism([(W / 6.0, 0.0), (5.0 * W / 6.0, 0.0), (W, L), (0.0, L)], h)
    if name == "lede":
        # Splayed front for the first 2/7 of the length, then parallel. Flat ceiling.
        z1 = (2.0 / 7.0) * L
        return _prism(
            [(0.25 * W, 0.0), (0.75 * W, 0.0), (W, z1), (W, L), (0.0, L), (0.0, z1)],
            lambda x, z: H,
        )
    if name == "live":
        # One pair of side walls and the ceiling, 6° each. Sides sum to 12°.
        tan6 = math.tan(math.radians(6.0))
        inset_x = min(0.25 * W, L * tan6)
        inset_y = min(0.45 * H, L * tan6)

        def h(x, z, H=H, L=L, inset_y=inset_y):
            t = 0.0 if L <= 0.0 else z / L
            return (H - inset_y) + inset_y * t

        return _prism([(inset_x, 0.0), (W - inset_x, 0.0), (W, L), (0.0, L)], h)
    return box_faces(W, H, L)


def _aabb(faces):
    verts = np.vstack([face.v for face in faces])
    return verts.min(0), verts.max(0)


def _aabb_dist(point, lo, hi) -> float:
    p = np.asarray(point, float)
    d = np.maximum(lo - p, 0.0) + np.maximum(p - hi, 0.0)
    return float(np.linalg.norm(d))


def build_tree(src, faces, order: int = 4, max_dist: Optional[float] = None, prune: bool = True):
    """Source tree. A parent behind a face drops that whole branch.

    An image further from the room than ``max_dist`` is dropped, and so are
    its children. ``max_dist`` is a path-length cap in metres.
    """
    nodes = [(np.asarray(src, float), tuple(), -1)]
    frontier = [0]
    lo, hi = _aabb(faces)
    for _k in range(1, int(order) + 1):
        nxt = []
        for ni in frontier:
            pos, seq, _parent = nodes[ni]
            last = seq[-1] if seq else -1
            for g, face in enumerate(faces):
                if g == last:
                    continue
                if prune and face.sd(pos) <= EPS:
                    continue
                child = face.mirror(pos)
                if max_dist is not None and _aabb_dist(child, lo, hi) > float(max_dist):
                    continue
                nodes.append((child, seq + (g,), ni))
                nxt.append(len(nodes) - 1)
        frontier = nxt
    return nodes


def _chain(nodes, i: int) -> List[int]:
    out = []
    while i >= 0:
        out.append(i)
        i = nodes[i][2]
    out.reverse()
    return out


def audible(nodes, i: int, receiver, faces) -> bool:
    """Backward outline check. These presets are convex, so nothing blocks."""
    seq = nodes[i][1]
    p = np.asarray(receiver, float)
    prev = None
    ch = _chain(nodes, i)
    for j in range(len(seq) - 1, -1, -1):
        face = faces[seq[j]]
        img = nodes[ch[j + 1]][0]
        dp, di = face.sd(p), face.sd(img)
        if dp <= EPS or di >= -EPS:
            return False
        q = p + (dp / (dp - di)) * (img - p)
        if not face.inside(q):
            return False
        if prev is not None and faces[prev].sd(q) <= EPS:
            return False
        p = q
        prev = seq[j]
    return True


def _unique(images):
    best = {}
    for pos, order, seq in images:
        key = tuple(round(float(v), 6) for v in pos)
        prev = best.get(key)
        if prev is None or (order, seq) < (prev[1], prev[2]):
            best[key] = (pos, order, seq)
    return list(best.values())


def collect_audible(src, faces, receiver, order: int = 4, max_dist: Optional[float] = None, prune: bool = True):
    """Audible images as ``(position, reflection order, face sequence)``."""
    nodes = build_tree(src, faces, order=order, max_dist=max_dist, prune=prune)
    found = []
    rec = np.asarray(receiver, float)
    for i in range(len(nodes)):
        if not audible(nodes, i, rec, faces):
            continue
        pos, seq, _parent = nodes[i]
        found.append((tuple(float(v) for v in pos), len(seq), seq))
    return _unique(found)


def _inside_margin(point, faces, margin: float) -> bool:
    if not _point_in_room(point, faces):
        return False
    return min(face.sd(point) for face in faces) > margin


def clamp_inside(point, faces, margin: float = 0.02):
    """Leave an interior point. An outside point walks in toward the centroid."""
    p = np.asarray(point, float)
    if _inside_margin(p, faces, margin):
        return (float(p[0]), float(p[1]), float(p[2]))
    verts = np.vstack([face.v for face in faces])
    centre = verts.mean(0)
    if not _point_in_room(centre, faces):
        centre = faces[0].v.mean(0)
    best = centre
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        trial = centre + mid * (p - centre)
        if _inside_margin(trial, faces, margin):
            best = trial
            lo = mid
        else:
            hi = mid
    return (float(best[0]), float(best[1]), float(best[2]))


def quota_pick(images, receiver: Vec3, n: int = 32):
    """Nearest per order: 1 / 6 / 11 / 10 / 4. A short order fills from the next."""
    def dkey(im):
        return (dist(receiver, im[0]), im[2])

    buckets = [[] for _ in range(5)]
    for im in images:
        order = im[1]
        if 0 <= order <= 4:
            buckets[order].append(im)
    for bucket in buckets:
        bucket.sort(key=dkey)
    picked = []
    cursors = [0, 0, 0, 0, 0]
    carry = 0
    for k, quota in enumerate(QUOTA):
        need = quota + carry
        got = buckets[k][cursors[k] : cursors[k] + need]
        cursors[k] += len(got)
        picked.extend(got)
        carry = need - len(got)
    if len(picked) < n:
        left = []
        for k in range(5):
            left.extend(buckets[k][cursors[k] :])
        left.sort(key=dkey)
        picked.extend(left[: n - len(picked)])
    return picked[:n]


def _ap(order: int) -> int:
    if order >= 4:
        return 2
    if order >= 2:
        return 1
    return 0


def compute_poly_taps(
    room: Vec3,
    source: Vec3,
    stand,
    shape,
    c: float = SPEED_OF_SOUND_M_S,
    n: int = 32,
    include_offaxis_shelf: bool = True,
) -> List[ImageTap]:
    """Thirty-two (or ``n``) taps for one preset. Levels use 1/r. Delays use the stand."""
    W, H, L = float(room[0]), float(room[1]), float(room[2])
    faces = faces_for(shape, W, H, L)
    src = clamp_inside(source, faces)
    stand_pt = clamp_inside((float(stand.cx), float(stand.cy), float(stand.cz)), faces)
    cap = float(c) * MAX_DELAY_MS * 0.001
    images = collect_audible(src, faces, stand_pt, order=4, max_dist=cap, prune=True)
    chosen = quota_pick(images, stand_pt, n=int(n))
    left, right = mic_positions(stand)
    centre = (
        float(stand.cx),
        float(stand.cy) if getattr(stand, "hy_c", None) is None else float(stand.hy_c),
        float(stand.cz) + float(getattr(stand, "centre_dz", 0.0) or 0.0),
    )
    pc = getattr(stand, "pos_c", None)
    if pc is not None:
        centre = (float(pc[0]), float(pc[1]), float(pc[2]))
    binaural = bool(getattr(stand, "is_binaural", False))
    ms = bool(getattr(stand, "ms_decode", False)) and not binaural
    yaw_l = float(stand.mlalr)
    yaw_r = float(stand.mralr)
    yaw_m = float(stand.mcalr)
    yaw_s = yaw_m + 0.5 * math.pi

    def shelf(theta: float) -> float:
        if not include_offaxis_shelf:
            return 1.0
        return offaxis_shelf_gain_linear(theta)

    taps: List[ImageTap] = []
    for i, (pos, order, _seq) in enumerate(chosen):
        pol = 1 if (order % 2 == 0) else -1
        d_stand = dist(stand_pt, pos)
        d_l = dist(left, pos)
        d_r = dist(right, pos)
        d_c = dist(centre, pos)
        if ms:
            d_l = d_c
            d_r = d_c
            th_m = arrival_theta_ray(centre, pos, yaw_m)
            th_s = arrival_theta_ray(centre, pos, yaw_s)
            p_m, g_m = capsule_press_grad(
                th_m,
                family=getattr(stand, "family_c", None),
                polar=getattr(stand, "polar_c", None),
                pattern=getattr(stand, "pattern_c", None) or PATTERN_CARDIOID,
            )
            _ps, g_s = capsule_press_grad(th_s, family="bi", polar=0.5, pattern=PATTERN_FIG8)
            geo = geometric_level(d_l) * pol
            sh = shelf(th_m)
            press_l = geo * p_m * sh
            press_r = press_l
            grad_l = geo * (g_m + g_s) * sh
            grad_r = geo * (g_m - g_s) * sh
            g_l = p_m + g_m + g_s
            g_r = p_m + g_m - g_s
            g_c = p_m + g_m
            press_c = geo * p_m * sh
            grad_c = geo * g_m * sh
            th_l = th_r = th_c = th_m
            sh_l = sh_r = sh_c = sh
        else:
            th_l = arrival_theta_ray(left, pos, yaw_l)
            th_r = arrival_theta_ray(right, pos, yaw_r)
            th_c = arrival_theta_ray(centre, pos, yaw_m)
            th_pat_l, th_pat_r, th_pat_c = th_l, th_r, th_c
            cy_l = getattr(stand, "colour_yaw_l", None)
            cy_r = getattr(stand, "colour_yaw_r", None)
            cy_c = getattr(stand, "colour_yaw_c", None)
            if cy_l is not None:
                th_l = arrival_theta_ray(left, pos, float(cy_l))
            if cy_r is not None:
                th_r = arrival_theta_ray(right, pos, float(cy_r))
            if cy_c is not None:
                th_c = arrival_theta_ray(centre, pos, float(cy_c))
            p_l, g_l_d = capsule_press_grad(
                th_pat_l,
                family=getattr(stand, "family_l", None),
                polar=getattr(stand, "polar_l", None),
                pattern=getattr(stand, "pattern_l", None) or pattern_from_car_omni(stand.car_omni),
            )
            p_r, g_r_d = capsule_press_grad(
                th_pat_r,
                family=getattr(stand, "family_r", None),
                polar=getattr(stand, "polar_r", None),
                pattern=getattr(stand, "pattern_r", None) or pattern_from_car_omni(stand.car_omni),
            )
            p_c, g_c_d = capsule_press_grad(
                th_pat_c,
                family=getattr(stand, "family_c", None),
                polar=getattr(stand, "polar_c", None),
                pattern=getattr(stand, "pattern_c", None) or pattern_from_car_omni(stand.car_omni),
            )
            sh_l, sh_r, sh_c = shelf(th_l), shelf(th_r), shelf(th_c)
            geo_l = geometric_level(d_l) * pol * sh_l
            geo_r = geometric_level(d_r) * pol * sh_r
            geo_c = geometric_level(d_c) * pol * sh_c
            press_l, press_r, press_c = geo_l * p_l, geo_r * p_r, geo_c * p_c
            grad_l, grad_r, grad_c = geo_l * g_l_d, geo_r * g_r_d, geo_c * g_c_d
            g_l, g_r, g_c = p_l + g_l_d, p_r + g_r_d, p_c + g_c_d
        if binaural:
            d_c = 0.0
            press_c = grad_c = g_c = 0.0
            sh_c = 1.0
        taps.append(
            ImageTap(
                index=i,
                n=(0, 0, 0),
                position=pos,
                distance_l=d_l,
                distance_r=d_r,
                delay_ms_l=delay_ms_from_distance(d_l, c),
                delay_ms_r=delay_ms_from_distance(d_r, c),
                polarity=pol,
                order=order,
                cardio_l=g_l,
                cardio_r=g_r,
                level_l=press_l + grad_l,
                level_r=press_r + grad_r,
                theta_l=th_l,
                theta_r=th_r,
                shelf_l=sh_l,
                shelf_r=sh_r,
                peak_axes=(),
                peak_freqs=(),
                wall_combo=frozenset(),
                behind_z=False,
                allpass_stages=_ap(order),
                press_l=press_l,
                press_r=press_r,
                grad_l=grad_l,
                grad_r=grad_r,
                distance_c=d_c,
                delay_ms_c=0.0 if binaural else delay_ms_from_distance(d_c, c),
                cardio_c=g_c,
                level_c=press_c + grad_c,
                theta_c=th_c,
                shelf_c=sh_c,
                press_c=press_c,
                grad_c=grad_c,
                fdn_distance_l=d_stand,
                fdn_distance_r=d_stand,
                fdn_distance_c=d_stand,
            )
        )
    return taps
