#!/usr/bin/env python3
"""Polygonal image-source prototype (Borish 1984 style). Research only, not engine code.

Rooms are closed polyhedra given as planar face polygons (inward normals).
Tree: root = source; child = mirror(parent, g) for every face g != parent's last face.
Validity (receiver-independent, prunes the whole subtree): parent must be in front of g.
Audibility (per receiver), checked backwards: receiver -> deepest image, crossing point
must lie inside the last face's outline; then crossing point -> parent image through the
previous face, and so on down to the source; in non-convex rooms every segment is also
tested against all other faces (obstruction).
"""
from __future__ import annotations
import json, math, random, sys, time
import numpy as np

EPS = 1e-9

class Face:
    def __init__(self, name, verts):
        self.name = name
        self.v = np.asarray(verts, float)
        # Newell normal
        n = np.zeros(3)
        for i in range(len(self.v)):
            a, b = self.v[i], self.v[(i + 1) % len(self.v)]
            n += np.array([(a[1]-b[1])*(a[2]+b[2]), (a[2]-b[2])*(a[0]+b[0]), (a[0]-b[0])*(a[1]+b[1])])
        self.n = n / np.linalg.norm(n)
        self.d = float(self.n @ self.v.mean(0))
        self._proj()
    def flip(self):
        self.n = -self.n; self.d = -self.d
    def _proj(self):
        ax = int(np.argmax(np.abs(self.n)))
        keep = [i for i in range(3) if i != ax]
        self.keep = keep
        self.p2 = self.v[:, keep]
    def sd(self, x):
        return float(self.n @ x - self.d)
    def inside(self, x, tol=1e-7):
        """Point (on plane) strictly inside the polygon outline (crossing number)."""
        px, py = x[self.keep[0]], x[self.keep[1]]
        poly = self.p2; c = False; m = len(poly)
        for i in range(m):
            x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % m]
            # reject points on an edge (grazing paths) as not inside
            ex, ey = x2 - x1, y2 - y1; L = math.hypot(ex, ey)
            if L > 0:
                t = ((px - x1) * ex + (py - y1) * ey) / (L * L)
                if -1e-9 <= t <= 1 + 1e-9 and abs((px - x1) * ey - (py - y1) * ex) / L < tol:
                    return False
            if (y1 > py) != (y2 > py):
                xi = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
                if px < xi:
                    c = not c
        return c
    def mirror(self, x):
        return x - 2.0 * self.sd(x) * self.n

def seg_hits_face(a, b, f):
    da, db = f.sd(a), f.sd(b)
    if da * db >= 0:
        return False
    t = da / (da - db)
    if t < 1e-6 or t > 1 - 1e-6:
        return False
    return f.inside(a + t * (b - a), tol=1e-9)

def point_in_room(x, faces):
    d = np.array([0.5377, 0.8338, 0.1250]); d /= np.linalg.norm(d)  # fixed generic direction
    far = x + d * 1e3; c = 0
    for f in faces:
        da, db = f.sd(x), f.sd(far)
        if da * db >= 0:
            continue
        t = da / (da - db)
        c += f.inside(x + t * (far - x), tol=1e-12)
    return c % 2 == 1

def orient(faces):
    """Make every normal point into the room (test a point just off each face)."""
    for f in faces:
        c = f.v.mean(0)
        if not f.inside(c):  # non-convex face: pick a point inside via triangle fan
            for i in range(1, len(f.v) - 1):
                c = (f.v[0] + f.v[i] + f.v[i + 1]) / 3
                if f.inside(c):
                    break
        if not point_in_room(c + 1e-4 * f.n, faces):
            f.flip()
    return faces

def prism(name_prefix, floor_xy, ceil_z):
    """Extruded floor polygon; ceil_z(x, y) linear (flat or sloped)."""
    P = [tuple(p) for p in floor_xy]
    faces = [Face("floor", [(x, y, 0.0) for x, y in P]),
             Face("ceiling", [(x, y, ceil_z(x, y)) for x, y in P])]
    for i in range(len(P)):
        (x1, y1), (x2, y2) = P[i], P[(i + 1) % len(P)]
        faces.append(Face(f"wall{i}", [(x1, y1, 0), (x2, y2, 0), (x2, y2, ceil_z(x2, y2)), (x1, y1, ceil_z(x1, y1))]))
    return orient(faces)

def gable(W, L, eave, ridge):
    v = lambda *p: p
    faces = [Face("floor", [(0, 0, 0), (W, 0, 0), (W, L, 0), (0, L, 0)]),
             Face("wallL", [(0, 0, 0), (0, L, 0), (0, L, eave), (0, 0, eave)]),
             Face("wallR", [(W, 0, 0), (W, L, 0), (W, L, eave), (W, 0, eave)]),
             Face("front", [(0, 0, 0), (W, 0, 0), (W, 0, eave), (W/2, 0, ridge), (0, 0, eave)]),
             Face("rear", [(0, L, 0), (W, L, 0), (W, L, eave), (W/2, L, ridge), (0, L, eave)]),
             Face("roofL", [(0, 0, eave), (0, L, eave), (W/2, L, ridge), (W/2, 0, ridge)]),
             Face("roofR", [(W, 0, eave), (W, L, eave), (W/2, L, ridge), (W/2, 0, ridge)])]
    return orient(faces)

def hexagon(R, H):
    return prism("hex", [(R * math.cos(math.pi / 3 * i), R * math.sin(math.pi / 3 * i)) for i in range(6)], lambda x, y: H)

ROOMS = {
    "Box 6 x 4.5 x 3 m": (prism("box", [(0, 0), (6, 0), (6, 4.5), (0, 4.5)], lambda x, y: 3.0), True),
    "Hexagon booth (R 1.6 m, 2.7 m)": (hexagon(1.6, 2.7), True),
    "Splayed control room (4->6 m, sloped ceiling)": (prism("ctl", [(-2, 0), (2, 0), (3, 6), (-3, 6)], lambda x, y: 2.6 + 0.1 * y), True),
    "LEDE-style (splayed front)": (prism("lede", [(-1.5, 0), (1.5, 0), (3, 2), (3, 7), (-3, 7), (-3, 2)], lambda x, y: 3.0), True),
    "Gable-ceiling vocal booth": (gable(2.0, 2.5, 2.4, 3.2), True),
    "L-shaped live room (non-convex)": (prism("L", [(0, 0), (7, 0), (7, 3.5), (3.5, 3.5), (3.5, 7), (0, 7)], lambda x, y: 3.2), False),
}

def build_tree(src, faces, K, prune=True):
    """Nodes: (pos, seq tuple of face idx, parent idx). Receiver-independent validity pruning."""
    nodes = [(np.asarray(src, float), (), -1)]
    per_order_valid = [1] + [0] * K
    frontier = [0]
    for k in range(1, K + 1):
        nxt = []
        for ni in frontier:
            pos, seq, _ = nodes[ni]
            last = seq[-1] if seq else -1
            for g, f in enumerate(faces):
                if g == last:
                    continue
                if prune and f.sd(pos) <= EPS:  # parent behind (or on) face g: no real path ever
                    continue
                nodes.append((f.mirror(pos), seq + (g,), ni))
                nxt.append(len(nodes) - 1)
        per_order_valid[k] = len(nxt)
        frontier = nxt
    return nodes, per_order_valid

def chain(nodes, i):
    out = []
    while i >= 0:
        out.append(i); i = nodes[i][2]
    return out[::-1]  # root .. node

def blocked(a, b, faces, skip):
    for h, f in enumerate(faces):
        if h in skip:
            continue
        if seg_hits_face(a, b, f):
            return True
    return False

def audible(nodes, i, rcv, faces, convex, path_out=None):
    ch = chain(nodes, i)
    seq = nodes[i][1]
    p = np.asarray(rcv, float)
    prev_face = None
    pts = [p]
    for j in range(len(seq) - 1, -1, -1):
        g = seq[j]; f = faces[g]; img = nodes[ch[j + 1]][0]
        dp, di = f.sd(p), f.sd(img)
        if dp <= EPS or di >= -EPS:
            return False
        q = p + (dp / (dp - di)) * (img - p)
        if not f.inside(q):
            return False
        if not convex and blocked(p, q, faces, {g, prev_face}):
            return False
        if prev_face is not None and faces[prev_face].sd(q) <= EPS:
            return False  # segment would leave through the back of the previous face
        pts.append(q); p = q; prev_face = g
    src = nodes[0][0]
    if not convex and blocked(p, src, faces, {prev_face}):
        return False
    pts.append(src)
    if path_out is not None:
        path_out.extend(pts)
    return True

def sample_point(faces, lo, hi, rng, margin=0.4, zr=(1.1, 1.8)):
    while True:
        x = np.array([rng.uniform(lo[0], hi[0]), rng.uniform(lo[1], hi[1]), rng.uniform(*zr)])
        if point_in_room(x, faces) and min(abs(f.sd(x)) for f in faces) > margin:
            # also require true distance to the face outline region; good enough for prisms
            return x

def run(K=4, pairs=30, seed=7):
    rng = random.Random(seed)
    res = {}
    for name, (faces, convex) in ROOMS.items():
        allv = np.vstack([f.v for f in faces]); lo, hi = allv.min(0), allv.max(0)
        N = len(faces)
        cand = [1] + [N * (N - 1) ** (k - 1) for k in range(1, K + 1)]
        aud = np.zeros(K + 1); hidden_parent_with_child = 0; hidden_total = 0
        t_tree = t_aud = 0.0; distinct_check = []
        valid_tree = None
        for _ in range(pairs):
            s = sample_point(faces, lo, hi, rng); r = sample_point(faces, lo, hi, rng)
            t0 = time.perf_counter()
            nodes, vt = build_tree(s, faces, K); valid_tree = vt if valid_tree is None else [a + b for a, b in zip(valid_tree, vt)]
            t1 = time.perf_counter()
            ok = np.zeros(len(nodes), bool)
            for i in range(len(nodes)):
                ok[i] = audible(nodes, i, r, faces, convex) if i else (convex or not blocked(r, s, faces, set()))
            t2 = time.perf_counter(); t_tree += t1 - t0; t_aud += t2 - t1
            for i, (_, seq, _) in enumerate(nodes):
                aud[len(seq)] += ok[i]
            # invisible nodes that still have an audible descendant (so visibility can't prune)
            has_desc = np.zeros(len(nodes), bool)
            for i in range(len(nodes) - 1, 0, -1):
                par = nodes[i][2]
                if ok[i] or has_desc[i]:
                    has_desc[par] = True
            for i in range(1, len(nodes)):
                if len(nodes[i][1]) < K and not ok[i]:
                    hidden_total += 1
                    hidden_parent_with_child += has_desc[i]
        res[name] = dict(N=N, convex=convex, candidates=cand,
                         after_validity=[v / pairs for v in valid_tree],
                         audible=list(aud / pairs),
                         hidden_with_audible_child_pct=100.0 * hidden_parent_with_child / max(hidden_total, 1),
                         ms_tree=1e3 * t_tree / pairs, ms_audibility=1e3 * t_aud / pairs)
    return res

def appear_events(name, K=3, steps=200, seed=3):
    """Walk the mic 2 m in 1 cm steps; count image appear/vanish events."""
    faces, convex = ROOMS[name]
    rng = random.Random(seed)
    allv = np.vstack([f.v for f in faces]); lo, hi = allv.min(0), allv.max(0)
    s = sample_point(faces, lo, hi, rng)
    nodes, _ = build_tree(s, faces, K)
    r0 = sample_point(faces, lo, hi, rng)
    d = np.array([1.0, 0.6, 0.0]); d /= np.linalg.norm(d)
    prev = None; ev = 0; used = 0
    for i in range(steps):
        r = r0 + d * (i * 0.01)
        if not point_in_room(r, faces) or min(abs(f.sd(r)) for f in faces) < 0.2:
            break
        used += 1
        cur = set()
        for j in range(1, len(nodes)):
            if audible(nodes, j, r, faces, convex):
                cur.add(tuple(np.round(nodes[j][0], 6)))
        if prev is not None:
            ev += len(cur ^ prev)
        prev = cur
    return dict(events=ev, metres=used * 0.01)

if __name__ == "__main__":
    out = run()
    ev = {n: appear_events(n) for n in ROOMS}
    for n, r in out.items():
        r["walk_events_order3"] = ev[n]
    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "results.json", "w"), indent=1)
    for n, r in out.items():
        print(n, "N=", r["N"], "cand", r["candidates"][1:], "valid-tree", [round(x, 1) for x in r["after_validity"][1:]],
              "audible", [round(x, 1) for x in r["audible"][1:]],
              "hid->child %.1f%%" % r["hidden_with_audible_child_pct"],
              "ms %.0f/%.0f" % (r["ms_tree"], r["ms_audibility"]), "walk", r["walk_events_order3"])
