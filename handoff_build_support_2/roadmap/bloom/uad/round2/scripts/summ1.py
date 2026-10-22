import csv, json, collections, numpy as np, units as U
AN = "/workspace/uad2/an"
def load_steps():
    R = list(csv.DictReader(open(AN + "/comp_colour_steps.csv")))
    d = collections.defaultdict(list)
    for r in R: d[(r["setting"], int(r["freq"]))].append(r)
    return d
def f(x):
    try: return float(x)
    except: return np.nan
def interp_at_gr(rows, key, target):
    gr = np.array([f(r["gr_db"]) for r in rows]); v = np.array([f(r[key]) for r in rows]); L = np.array([f(r["in_dbfs"]) for r in rows])
    if target == 0:
        idx = np.where(gr < 0.3)[0]
        if not len(idx): return np.nan, np.nan
        # highest level below threshold that is part of the initial below-threshold run
        k = 0
        while k + 1 < len(gr) and gr[k + 1] < 0.3: k += 1
        return v[k], L[k]
    # first crossing of target in ascending order
    for i in range(1, len(gr)):
        if gr[i - 1] < target <= gr[i]:
            a = (target - gr[i - 1]) / (gr[i] - gr[i - 1])
            return v[i - 1] + a * (v[i] - v[i - 1]), L[i - 1] + a * (L[i] - L[i - 1])
    return np.nan, np.nan
def interp_at_level(rows, key, L0):
    L = np.array([f(r["in_dbfs"]) for r in rows]); v = np.array([f(r[key]) for r in rows])
    if not (L.min() <= L0 <= L.max()): return np.nan
    return float(np.interp(L0, L, v))
GRT = [0, 3, 6, 10, 15]
def table():
    d = load_steps(); out = []
    for (name, fq), rows in sorted(d.items()):
        role = rows[0]["role"]; twin = U.TWIN.get(name)
        if name.startswith("dis_6_d"): twin = "dis_1_" + name[-2:]
        trow = d.get((twin, fq)) if twin else None
        for g in GRT:
            thd, L = interp_at_gr(rows, "thd_pct", g)
            if thd != thd: continue
            h2, _ = interp_at_gr(rows, "h2_dbc", g); h3, _ = interp_at_gr(rows, "h3_dbc", g)
            h5, _ = interp_at_gr(rows, "h5_dbc", g) if fq < 5000 else (np.nan, 0)
            o, _ = interp_at_gr(rows, "out_dbfs", g)
            r = {"setting": name, "freq": fq, "gr_target": g, "in_dbfs": round(L, 1), "out_dbfs": round(o, 1), "thd_pct": round(thd, 4),
                 "h2_dbc": round(h2, 1), "h3_dbc": round(h3, 1), "h5_dbc": round(h5, 1) if h5 == h5 else ""}
            if trow:
                tg = interp_at_level(trow, "gr_db", L)
                r.update({"twin": twin, "twin_gr_db": round(tg, 2), "twin_thd_pct": round(interp_at_level(trow, "thd_pct", L), 4),
                          "twin_h2_dbc": round(interp_at_level(trow, "h2_dbc", L), 1), "twin_h3_dbc": round(interp_at_level(trow, "h3_dbc", L), 1)})
            out.append(r)
    return out
if __name__ == "__main__":
    T = table()
    keys = []
    for r in T:
        for k in r:
            if k not in keys: keys.append(k)
    w = csv.DictWriter(open(AN + "/comp_colour_vs_gr.csv", "w", newline=""), keys); w.writeheader(); [w.writerow(r) for r in T]
    for r in T:
        if r["freq"] == 1000: print(r)
