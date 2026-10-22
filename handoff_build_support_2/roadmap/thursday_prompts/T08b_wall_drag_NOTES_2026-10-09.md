# T8b - Wall, corner and ceiling drag (U2, U4, D-UI37 "stop") + P1 canvas scaling. Effort: high. Needs T8 (room mic drag). Golden impact: NONE.
NOT YET WRITTEN IN FULL. Must-fix list from Build's review of 9 Oct (REVIEW_T8 findings 4, 5, 6, 7, 9, 10), to be turned into a RUN prompt after T8 lands and reviewed:
- Before any wall code: snap Width and Ceiling to step 0.1 and Length to step 0.5 in the direction that does not cross an object; cap Height at 40; keep Stand X 0-40 and Stand Z 0-60 (wall drag must not add more out-of-range values). Change test_drag_model.mjs expectations to match.
- Ceiling drag floor max(1, highest+0.10) must never exceed the Ceiling slider max 40.
- Point test_drag_model.mjs at ../static/js/drag_model.js. Keep roomSpot. Never copy the prebuild drag_model.js over the live one.
- P1 (canvas scaling): fitSourceBuffer only handles canvas ids starting "src", so #floorCanvas stays 900x640; do P1 first, then the 8 px / 12 px hit bands.
- Proof: Playwright on the real #floorCanvas / #elevCanvas, not prove_t8.py.
