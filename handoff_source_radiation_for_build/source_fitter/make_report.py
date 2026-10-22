"""Build FIT_REPORT.md from presets/*.json (box)."""
import glob, json, os
H = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in sorted(glob.glob(os.path.join(H, "presets", "*.json"))):
    if f.endswith("index.json"):
        continue
    p = json.load(open(f)); fit = p.get("fit", {}) or {}
    prov = p.get("provenance", {}) or {}
    di = p.get("di_db", {}) or {}
    rows.append((p["id"], p.get("label", ""), p.get("tag", ""), fit.get("rmse_train_db"), fit.get("rmse_holdout_db"),
                 di.get("250"), di.get("1000"), di.get("4000"), (p.get("diffuse_inject") or {}).get("fit_rmse_db"),
                 int(p["params"].get("lp_order", 1)), prov.get("dataset", prov.get("basis", ""))[:70], prov.get("license", "")[:40]))
main = ["talking_head", "singer_soprano", "acoustic_guitar", "trumpet", "trumpet_byu", "violin", "violin_byu", "cello",
        "combo_1x12", "combo_1x12_bluesjr", "combo_1x12_bluesdlx", "combo_1x10", "combo_2x12", "combo_2x12_ac30",
        "cab_1x12_closed", "cab_4x12_closed", "piano_grand_lid_open", "omni"]
def fmt(v, n=2):
    return "—" if v is None or v != v else f"{v:.{n}f}"
def tbl(sel):
    out = ["| id | label | tag | RMSE train dB | RMSE hold-out dB | DI 250 | DI 1k | DI 4k | diffuse-fit RMSE | LP order | data |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sel:
        out.append(f"| `{r[0]}` | {r[1]} | {r[2]} | {fmt(r[3])} | {fmt(r[4])} | {fmt(r[5],1)} | {fmt(r[6],1)} | {fmt(r[7],1)} | {fmt(r[8])} | {r[9]} | {r[10]} |")
    return "\n".join(out)
byid = {r[0]: r for r in rows}
txt = f"""# Source fitter: FIT REPORT (box run, 26 Sep 2026)

Model `radiation_shelf_plus_soft_one_pole`, schema `source_fitter.preset.v1`.
- **Loss:** dB error of the model vs the data, both normalised to their own sphere power average (DI-normalised), with the data floor-clipped at band max − 40 dB. There is also a per-band DI-match term (weight 0.5, ASSUMED).
- **Hold-out:** every 5th direction (index % 5 == 2) is never used in training.
- **Optimiser:** DE + least-squares polish. `lp_order` 1 and 2 are both fitted and the lower train loss is kept.

RMSE is over all fit bands (TU: 1/3-oct 100 Hz–10 kHz within data; BYU: dataset band range) and over train or hold-out directions.
DI values are those of the **model** (dB, re sphere average). The data DI per band is stored in each JSON under `fit.di_data_db`.

## Main presets
{tbl([byid[i] for i in main if i in byid])}

**Tags:**
- `MEASURED-FIT` (VERIFIED data) means fitted to downloaded measured data (provenance in the JSON).
- `ASSUMED` means a derived or placeholder preset with no measurement:
  - `cab_1x12_closed` is derived from the Deluxe Reverb fit with the back-lobe/dipole removed and the broadband depth limited.
  - `cab_4x12_closed` is the same law with f0 and lp_hz halved (size ×2).
  - `piano_grand_lid_open` is a qualitative placeholder after Meyer (2009), with no numbers.
  - `omni` is the exact null.

## Quality notes
- **Speech / brass / strings / woodwinds (TU, BYU):** hold-out 1.6–3.3 dB. The smooth model captures the frequency trend of beaming and the front/back ratio, but not narrow lobes (violin/cello at some bands, flute side lobes).
- **French horn** (bell to the rear-right, player-dependent): hold-out 8.2 dB. The main axis is far from the TU 'forward' mic, so do **not** ship it without re-aiming.
- **Timpani, tuba:** 3–4 dB.
- **Guitar combos (BYU): LOW CONFIDENCE, 4.9–5.9 dB.**
  - The data combine an open-back pattern at LF (DI 4–6 dB; back ≈ front at 100–250 Hz) with very strong HF beaming (DI 15–20 dB at 1.6–4 kHz) and a rear lobe.
  - The v1 model's broadband 'dip' stage is frequency-independent, so the optimiser uses it for HF side rejection and over-attenuates the LF sides. At 250 Hz and 90° the model is about −30 dB where the data is about −3 to −6 dB.
  - Fixing `dip=0` did not help (6.1 dB).
  - **Recommendation:** v2 adds a frequency-limited dipole term (the broadband stage becomes a low shelf, or a two-band k-law). Until then, use `cab_1x12_closed` / `cab_4x12_closed` (limited broadband depth, no dipole null) for listening and treat `combo_*` as research presets.
- **Data we could NOT use:** DirPat guitar cabinets and loudspeakers (no licence; non-anechoic; ambiguous orientation). There is no piano in the TU/BYU sets and no 4x12 in any open anechoic set we found.

## All presets
{tbl(rows)}

## Licences
- **TU Berlin** (DOI 10.14279/depositonce-19858): the SOFA attribute says CC BY-NC-SA 4.0. The presets are derived parameters: attribute them and keep them non-commercial unless cleared.
- **BYU ScholarsArchive:** open access, cite as requested. No explicit licence text was found.

Plots: `plots/polars/*.png` (horizontal and median plane, 250 Hz–8 kHz, lines = model, dots = data), `plots/balloons/*.png`, `plots/di/*.png` (model vs data DI).
"""
open(os.path.join(H, "FIT_REPORT.md"), "w").write(txt)
print(tbl([byid[i] for i in main if i in byid]))
