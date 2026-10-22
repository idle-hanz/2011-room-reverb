"""Head-relative direction grids for binaural colour entries, and engine mapping.

Engine convention (p5 early_field.py, K1-fixed, VERIFIED): X right, Y up, Z forward;
yaw 0 looks +Z; look(psi) = (sin psi, 0, cos psi); L capsule at smaller X.
So head right(psi) = (cos psi, 0, -sin psi) and left = -right.
SOFA azimuth (+ = left) = atan2(u.left, u.look); elevation = asin(u_y).
"""
from __future__ import annotations

import math

import numpy as np

from .core import sph_to_vec


def ring_grid(rings):
    """rings: list of (el_deg, az_step_deg). el +-90 use step 360 -> one node."""
    nodes = []
    for el, step in rings:
        n = max(1, int(round(360.0 / step)))
        for k in range(n):
            az = (k * 360.0 / n + 180.0) % 360.0 - 180.0
            if abs(el) >= 89.9:
                az = 0.0
            nodes.append((round(az, 6), float(el)))
    return nodes


GRIDS = {
    # id: rings (el, az step)
    "G26": [(90, 360), (45, 60), (0, 30), (-45, 60), (-90, 360)],
    "G50": [(90, 360), (60, 60), (30, 30), (0, 30), (-30, 30), (-60, 60), (-90, 360)],
    # G60 = shipping grid (60 nodes; mirror-symmetric -> 60 shared records <= MAX_IRS 64)
    "G60": [(90, 360), (60, 45), (30, 30), (0, 20), (-30, 30), (-60, 45), (-90, 360)],
    "G86": [(90, 360), (60, 30), (30, 20), (0, 15), (-30, 20), (-60, 30), (-90, 360)],
}


def grid_nodes(gid):
    return ring_grid(GRIDS[gid])


def mirror_map(nodes):
    """index of the node at (-az, el) for each node (grid must be mirror-closed)."""
    V = sph_to_vec([n[0] for n in nodes], [n[1] for n in nodes])
    Vm = V * np.array([1.0, -1.0, 1.0])
    d = Vm @ V.T
    m = np.argmax(d, axis=1)
    assert np.all(d[np.arange(len(nodes)), m] > 0.99999), "grid not mirror-closed"
    return m.tolist()


def nearest_node(nodes, az, el):
    V = sph_to_vec([n[0] for n in nodes], [n[1] for n in nodes])
    u = sph_to_vec(az, el)
    d = np.atleast_2d(u) @ V.T
    i = np.argmax(d, axis=1)
    ang = np.degrees(np.arccos(np.clip(d[np.arange(len(i)), i], -1, 1)))
    return i, ang


def engine_head_relative(head_xyz, image_xyz, head_yaw_deg=0.0, yaw_x_sign=1.0):
    """Engine room coords -> (az_sofa_deg, el_deg, r) relative to head centre."""
    dx, dy, dz = (image_xyz[i] - head_xyz[i] for i in range(3))
    r = math.sqrt(dx * dx + dy * dy + dz * dz)
    if r < 1e-12:
        return 0.0, 0.0, 0.0
    psi = math.radians(head_yaw_deg)
    look = (yaw_x_sign * math.sin(psi), 0.0, math.cos(psi))
    right = (math.cos(psi), 0.0, -yaw_x_sign * math.sin(psi))
    f = (dx * look[0] + dz * look[2]) / r
    rt = (dx * right[0] + dz * right[2]) / r
    az = math.degrees(math.atan2(-rt, f))
    el = math.degrees(math.asin(max(-1.0, min(1.0, dy / r))))
    return az, el, r


def ear_positions(head_xyz, spacing_m, head_yaw_deg=0.0, yaw_x_sign=1.0):
    """Left/right ear points; ears rotate with head yaw (unlike today's capsule X offsets)."""
    psi = math.radians(head_yaw_deg)
    right = (math.cos(psi), 0.0, -yaw_x_sign * math.sin(psi))
    h = 0.5 * spacing_m
    L = tuple(head_xyz[i] - h * right[i] for i in range(3))
    R = tuple(head_xyz[i] + h * right[i] for i in range(3))
    return L, R


def lateral_angle(az_deg, el_deg):
    """Interaural-polar lateral angle (rad), + = left: asin(cos el * sin az)."""
    return np.arcsin(np.clip(np.cos(np.radians(el_deg)) * np.sin(np.radians(az_deg)), -1, 1))
