"""Tiny 2D image-source helper for the diagrams (same rules as ism_proto.py, walls = segments)."""
import numpy as np
EPS = 1e-9
class Wall:
    def __init__(self, name, a, b, interior):
        self.name = name; self.a = np.array(a, float); self.b = np.array(b, float)
        t = self.b - self.a; n = np.array([-t[1], t[0]]); n /= np.linalg.norm(n)
        if n @ (np.array(interior) - self.a) < 0: n = -n
        self.n = n; self.d = float(n @ self.a)
    def sd(self, x): return float(self.n @ x - self.d)
    def mirror(self, x): return x - 2 * self.sd(x) * self.n
    def param(self, q):
        t = self.b - self.a; return float((q - self.a) @ t / (t @ t))
def room(poly):
    c = np.mean(poly, 0)
    names = "ABCDEFGH"
    return [Wall(names[i], poly[i], poly[(i + 1) % len(poly)], c) for i in range(len(poly))]
def tree(src, walls, K, prune=True):
    nodes = [dict(pos=np.array(src, float), seq=(), parent=-1, pruned=False)]
    front = [0]
    for k in range(1, K + 1):
        nxt = []
        for ni in front:
            nd = nodes[ni]; last = nd["seq"][-1] if nd["seq"] else -1
            for g, w in enumerate(walls):
                if g == last: continue
                pr = nd["pruned"] or w.sd(nd["pos"]) <= EPS
                nodes.append(dict(pos=w.mirror(nd["pos"]), seq=nd["seq"] + (g,), parent=ni, pruned=pr))
                nxt.append(len(nodes) - 1)
        front = nxt
    return nodes
def backtrace(nodes, i, rcv, walls):
    """Returns (ok, points[], fail_info). points = receiver, hit points..., source."""
    chain = []; j = i
    while j >= 0: chain.append(j); j = nodes[j]["parent"]
    chain = chain[::-1]
    seq = nodes[i]["seq"]; p = np.array(rcv, float); pts = [p]; prev = None
    for k in range(len(seq) - 1, -1, -1):
        w = walls[seq[k]]; img = nodes[chain[k + 1]]["pos"]
        dp, di = w.sd(p), w.sd(img)
        if dp <= EPS or di >= -EPS: return False, pts, ("side", seq[k], None)
        q = p + dp / (dp - di) * (img - p); u = w.param(q)
        if not (0 < u < 1): return False, pts, ("outline", seq[k], q)
        if prev is not None and walls[prev].sd(q) <= EPS: return False, pts, ("back", seq[k], q)
        pts.append(q); p = q; prev = seq[k]
    pts.append(nodes[0]["pos"]); return True, pts, None
