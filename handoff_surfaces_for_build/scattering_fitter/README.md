# scattering_fitter (Track C pack)

Per-material random-incidence scattering s(f) presets (ISO 17497-1 sense), fitted to cited tables, plus an offline per-hit scattering prototype and CPU kernels.

**Read `REPORT.md` first, then `../briefs/GROK_BUILD_BRIEF_Surfaces_scattering.md`.**

| Path | What |
|---|---|
| `presets/index.json`, `presets/<id>.json` | 12 library materials (same ids as `surfaces_fitter/presets`) + `diffuser_qrd_n7`, `diffuser_ceiling_measured`, `diffuser_pyramids` |
| `scattering_fitter/sources.py` | every cited number and its reference |
| `scattering_fitter/model.py` | logistic s(f), per-hit split, Lambert cluster, velvet pulses, shelf fit |
| `run_fit.py` | writes presets/, plots/, reports/fit_table.md |
| `proto/room_proto.py` | offline prototype on the audited live params (6×3×8 m) |
| `bench/` | scalar and block-major kernels: C (native), WASM (zig), JS; logs |
| `data/` | GRAS surface CSVs (TU Berlin DepositOnce; attribution in each preset; check the licence before redistribution) |

**Locks:** feed-forward on early taps only. Never inside the FDN. Never MEASURED by us. Don't import into live `software/` until Idle says go.
