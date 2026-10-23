# Backlog F — Surfaces re-scope (2026-10-23)

Read-only. No mode, no default flip, no golden re-pin. `software\` was not edited.

## Tree (VERIFIED)

`app_server.py` line 641: a missing `phys_ceiling` is on. `app.js` line 128 sets `phys_ceiling: true`. The checkbox `phys_ceiling` in `index.html` starts checked.

`DECAY_MODES` is `("flat", "surfaces")` (`app_server.py` line 441). Natural is the comment on that line. `_decay_mode` sends a missing or unknown value to `flat`.

Default mics are `ShureSM57` (`app.js` line 118, `mic_colour\preset_store.py` `DEFAULT_PRESET_ID`).

A missing `surf_directional` is false (`app_server.py` line 654). `RR_SL_STAGE` is 3 (`index.html`). SL1, SL2, and SL3 have rows in `BUILD_RUN_LOG.md`. SL4, SL5, SL6, SL7a, and SL7b have not run.

Movement is un-forced. The knob default is 0 (`render_pipeline.py`, `MOVEMENT_FORCED_OFF = False`).

## What PHYSDEFAULT already covered (VERIFIED)

Frequency-dependent decay is already the default. With the lock armed, a body that leaves `decay_mode` at `flat` takes `phys_ceiling_pack` with Surfaces off: air on, humidity 0.35, `k` set so the 500 Hz–1 kHz mean matches the dial, axial cuts kept (`surf_loop.py` `phys_ceiling_row`, `phys_teff_bands`). Idle accepted that sound on 19 Oct 2026. The default goldens were re-pinned for it. The current brief still holds `GOLDEN_META` `a362cf5e490089807b39346ba207633b88511548`.

That covers N11 and the default-air half of ST-1. Decay mode stays Flat. Surfaces stays opt-in (D-SL1 as first locked).

## Lines (PROPOSAL)

- SL4: still do it. Directional per-line decay and one Render calibration (D-SL2, D-SL4), Surfaces only. Does not change the default golden.
- SL5: still do it, after SL4. Treatment rows, the room-shell row inside Surfaces mode, and the plaster + parquet library (D-SL6, D-SL8 library only). Does not change the default golden.
- SL6: still do it, after SL5. Auto-treat suggests rows and waits for Accept (D-SL5, D-SL9). Does not change the default golden.
- SL7a: drop it. Its job is the Natural chip, the four-way A/B, and the unflipped 2026 default set for the bundled switch. Does not change the default golden.
- SL7b: drop it. The one re-record of Surfaces + natural decay + U87 (D-SL10, ST-1, N11, D-UI38) does not match this tree. It would change the default golden.

## Remaining default change

U87 Ai cardioid on L, C, and R (D-UI38). It still needs Idle's written OK. That OK is not in the tree. This is an audio law. Stop.
