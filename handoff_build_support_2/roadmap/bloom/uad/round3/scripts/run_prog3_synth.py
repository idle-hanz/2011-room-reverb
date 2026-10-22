import sys, csv; sys.path.insert(0, '/workspace/uad3'); import prog3, io2, models as Mo
rows = []
for p, u in Mo.PRESET_UNIT.items():
    for pk in ('drums', 'vocal', 'bass', 'tail', 'mix', 'wetmix'):
        for ab in ('a', 'b'):
            x, y = io2.rec('prog_%s_%s_%s' % (u, pk, ab)); r, _ = prog3.compare(p, u, x, y, pk + '_' + ab); rows.append(r); print(*r.values(), flush=True)
w = csv.DictWriter(open(sys.argv[1], 'w', newline=''), list(rows[0])); w.writeheader(); w.writerows(rows)
