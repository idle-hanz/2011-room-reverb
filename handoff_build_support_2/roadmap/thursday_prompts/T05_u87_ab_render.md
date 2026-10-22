# T5 · U87 A/B render (box job, no Build usage). Effort: low. Needs T4 and T4b merged (so Idle hears the final tail and ORTF without C). Decisions: an **early** U87 listen. Since 20:40 the U87 switch is gated on the SL7a final A/B (D-UI38 amended); T6 is merged into SL7b.
Follow `handoff_build_support_2\roadmap\research\R05_T5_T6_u87.md` "A/B plan": golden scene + dry guitar, ORTF (C off, D20); SM57 ×3, U87 Ai Cardioid ×3, CMC5-U ×3; loudness-matched −23 LUFS; Render; blind names A/B/C plus a key file; one folder in `handoff_build_support_2`.
- Also do the double-count check (single tap at 90°/180° per mic) and write one line on the result.
- **Golden impact:** none (no code change). Do not touch `software\`.
- (Stale-fact fix 2026-10-09 from REVIEW_RUN_PLAN_findings.md) Render on the **post-T4c tree** with Smooth left ON and ORTF C off. Do **not** render from `prebuild\tests_py\fixtures\ui_body_ortf.json` (it still has `third_mic: "centre"`). `R05` lines 16-17 ("after T4") are superseded by this line. Do not compare against `eq1_out` smooth-off as the baseline.
- **Stop if:** the post-T4c tree is not on the box, or the renders clip.
