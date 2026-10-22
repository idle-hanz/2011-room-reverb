#!/usr/bin/env python3
"""Fit s(f) presets for the 12 Surfaces library materials + 3 diffuser options. Writes presets/, plots/, reports/."""
import json, os, sys, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from scattering_fitter import sources as S
from scattering_fitter.model import s_logistic, fit_logistic

REFS = dict(gras=S.GRAS_REF, cox=S.COX_APPD_REF, kamisinski=S.KAMISINSKI_REF, khrys_qrd=S.KHRYS_REF)


def data_for(m):
    if m["src"] == "gras":
        f, _a, s = S.gras_csv(m["key"]); return S.thirds_window(f, s, 100.0, 10000.0)
    if m["src"] == "cox":
        row = S.COX_ROWS[m["key"]]; pts = [(f, v) for f, v in zip(S.COX_F, row) if v is not None]
        return [p[0] for p in pts], [p[1] for p in pts]
    if m["src"] == "kamisinski": return list(S.KAMISINSKI_F), list(S.KAMISINSKI_S)
    if m["src"] == "khrys_qrd": return list(S.KHRYS_F), list(S.KHRYS_S)


def octave_from_thirds(f, s, fc):
    sel = [v for fi, v in zip(f, s) if fc / 2 ** (1 / 2) <= fi <= fc * 2 ** (1 / 2) * 1.001]
    return float(np.mean(sel)) if sel else None


def main():
    os.makedirs(os.path.join(HERE, "presets"), exist_ok=True); os.makedirs(os.path.join(HERE, "plots"), exist_ok=True)
    kam, _ = fit_logistic(S.KAMISINSKI_F, S.KAMISINSKI_S)
    index = []; rows = []
    fig_all, ax_all = plt.subplots(figsize=(10, 6))
    for m in S.MATERIALS:
        f, s = data_for(m)
        if m["src"] == "khrys_qrd":
            p, rmse = fit_logistic(f, s, fixed=dict(k=kam["k"], s_lo=kam["s_lo"]))
        else:
            p, rmse = fit_logistic(f, s)
        band = [float(np.clip(v, 0.0, 1.0)) for v in s_logistic(S.BANDS7, **p)]
        data_oct = [octave_from_thirds(f, s, fc) for fc in S.BANDS7] if m["src"] in ("gras", "cox") else None
        s707 = float(s_logistic([707.0], **p)[0])
        anchor = None
        if m.get("odeon"):
            lo, hi = S.ODEON_MID[m["odeon"]]
            anchor = dict(odeon_class=m["odeon"], range_707=[lo, hi], model_707=round(s707, 4),
                          inside=bool(lo - 1e-9 <= s707 <= hi + 1e-9))
        preset = {
            "schema": "scattering_fitter.material_scatter.v1",
            "id": m["id"], "honesty": m["tag"],
            "scatter_hz": S.BANDS7, "scatter": [round(v, 4) for v in band],
            "scatter_data_octave": None if data_oct is None else [None if v is None else round(v, 4) for v in data_oct],
            "model": "logistic_log2f", "params": {k: round(float(v), 5) for k, v in p.items()},
            "rmse_s": round(rmse, 5), "n_points": len(f), "fit_range_hz": [min(f), max(f)],
            "source": REFS[m["src"]], "source_key": m["key"], "odeon_anchor": anchor, "note": m["note"],
            "usage": ("Per hit: E_spec *= (1 - s_b); E_scatter = 1 - prod(1 - s_b). Specular tap amplitude sqrt(prod(1-s)); "
                      "scattered share -> short Lambert-envelope velvet cluster, feed-forward on the early tap only. "
                      "Muted face contributes neither absorption nor scattering."),
            "locks": {"measured_by_us": False, "honesty_note": "never promote to MEASURED; cite source",
                      "live_software": "do not import into live software/ until Idle says go"},
        }
        json.dump(preset, open(os.path.join(HERE, "presets", m["id"] + ".json"), "w"), indent=2)
        index.append({k: preset[k] for k in ("id", "honesty", "scatter", "rmse_s", "source_key")} | {"file": m["id"] + ".json"})
        rows.append((m, p, rmse, band, data_oct, anchor, f, s))
        # plot
        ff = np.geomspace(63, 16000, 300)
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.semilogx(f, s, "o", ms=4, label="cited data (%s)" % m["tag"])
        ax.semilogx(ff, s_logistic(ff, **p), "-", label="logistic fit  rmse=%.3f" % rmse)
        ax.semilogx(S.BANDS7, band, "s", mfc="none", ms=8, label="7-band preset")
        if anchor: ax.axhspan(*anchor["range_707"], xmin=0.47, xmax=0.53, color="orange", alpha=0.3, label="ODEON @707 Hz")
        ax.set_ylim(0, 1.05); ax.set_xlabel("Hz"); ax.set_ylabel("s (random incidence)")
        ax.set_title(m["id"]); ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=7, loc="upper left")
        fig.tight_layout(); fig.savefig(os.path.join(HERE, "plots", m["id"] + "_s.png"), dpi=110); plt.close(fig)
        ax_all.semilogx(ff, s_logistic(ff, **p), label=m["id"])
    ax_all.set_ylim(0, 1.05); ax_all.grid(True, which="both", alpha=0.3); ax_all.legend(fontsize=7, ncol=2)
    ax_all.set_title("Fitted s(f) — all presets (see honesty tags)"); ax_all.set_xlabel("Hz")
    fig_all.tight_layout(); fig_all.savefig(os.path.join(HERE, "plots", "gallery_all_s.png"), dpi=110)
    json.dump({"schema": "scattering_fitter.preset_index.v1", "bands_hz": S.BANDS7,
               "matches": "surfaces_fitter.material.v1 absorb_hz (7 octave bands 125..8000)",
               "presets": index}, open(os.path.join(HERE, "presets", "index.json"), "w"), indent=2)
    # report table
    L = ["| id | honesty | s @125,250,500,1k,2k,4k,8k | s_lo | s_hi | fc Hz | k /oct | RMSE | ODEON 707 Hz check |", "|---|---|---|---|---|---|---|---|---|"]
    for m, p, rmse, band, d, anc, f, s in rows:
        chk = "—" if not anc else ("model %.3f vs %s–%s: %s" % (anc["model_707"], anc["range_707"][0], anc["range_707"][1], "inside" if anc["inside"] else "OUTSIDE"))
        L.append("| %s | %s | %s | %.3f | %.3f | %.0f | %.2f | %.3f | %s |" % (m["id"], m["tag"], ", ".join("%.2f" % v for v in band),
                 p["s_lo"], p["s_hi"], p["fc"], p["k"], rmse, chk))
    open(os.path.join(HERE, "reports", "fit_table.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
