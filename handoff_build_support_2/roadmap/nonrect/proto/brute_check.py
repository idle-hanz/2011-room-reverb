"""Check: does any audible chain have an ancestor that the receiver-independent validity test would prune?"""
import random, numpy as np
from ism_proto import ROOMS, build_tree, audible, sample_point, chain, EPS
K = 3; rng = random.Random(11); tot = 0; bad = 0; aud_p = aud_np = 0
for name, (faces, convex) in ROOMS.items():
    allv = np.vstack([f.v for f in faces]); lo, hi = allv.min(0), allv.max(0)
    for _ in range(8):
        s = sample_point(faces, lo, hi, rng); r = sample_point(faces, lo, hi, rng)
        nodes, _ = build_tree(s, faces, K, prune=False)
        for i in range(1, len(nodes)):
            if not audible(nodes, i, r, faces, convex):
                continue
            aud_np += 1
            ch = chain(nodes, i)
            for a, b in zip(ch[:-1], ch[1:]):
                g = nodes[b][1][-1]
                if faces[g].sd(nodes[a][0]) <= EPS:
                    bad += 1; break
        nodes2, _ = build_tree(s, faces, K, prune=True)
        aud_p += sum(audible(nodes2, i, r, faces, convex) for i in range(1, len(nodes2)))
print("audible without pruning", aud_np, "with pruning", aud_p, "audible chains that pruning would have removed", bad)
