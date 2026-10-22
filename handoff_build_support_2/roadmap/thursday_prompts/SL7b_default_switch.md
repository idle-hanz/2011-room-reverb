# SL7b · "Default switch": Surfaces + natural decay + U87 in one re-record. Effort: high. **GATED: run only after Idle's written OK on the SL7a final A/B** (D-UI38 amended; it replaces the old T5→T6 gate). Needs SL7a. Decisions: D-SL10, ST-1, ST-2, N11/D4, D-UI30, D-SL1, D-SL6, D-SL8.
Replaces the old T6 (U87 default) and the old single SL7. One switch, one re-record.
- **What to do:**
  - Set `DEFAULT_SET = "2026"`: default Decay = **Surfaces** (air in the loop = natural decay), default mics **U87 Ai Cardioid** on L/C/R, default cards **real "plaster + parquet"** plus the room-shell row.
  - "Flat (2011)" and "Natural (air)" stay selectable in the Decay mode control.
  - Regenerate **all** references once (main golden, the ~77 default references, all FDN references, the SL2–SL6 Surfaces references) with GOLDEN_META reason **"SL7b default switch: Surfaces + natural decay (ST-1/ST-2) + U87 (D-UI30)"**.
  - Record the new main golden hash in HANDOVER, plus a line saying the 2011 hashes now live in `tests/refs_flat2011/`.
- **Cut line:** **whole session or nothing.** The flag flip + every regenerated reference + GOLDEN_META + HANDOVER go in one commit. If the regeneration can't finish, revert to `DEFAULT_SET = "2011"` and commit nothing.
- **Golden impact:** **YES, everything default.** This is the only change in the session. The Flat (2011) parity suite (SL7a) must still pass **bit-exact**.
- **Done when:**
  - The new default render matches the approved A/B render C (hash noted in the key file): T20 per octave within 5 %, or bit-identical if the tree hasn't moved.
  - Flat parity is green.
  - Old scenes recall as Flat with their stored mics.
  - The full suite is green.
- **Stop if:** Idle's OK is not written down, the parity suite fails, or any change other than the default set is needed to make the suite green. Revert and report.
