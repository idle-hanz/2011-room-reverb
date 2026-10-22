# SL7a · Default switch, prep (no golden change). Effort: high. Needs SL6 (and SL3 for Play). Decisions: **ST-1, ST-2, N11/D4 locked 4 Oct 20:40–20:41**, D-SL10 (one default switch), D-UI30/D-UI38 (amended), D-SL1/6/8.
**Prebuild to reuse** (`handoff_build_support_2\roadmap\prebuild\sl\README.md`): Natural mode is the SL2 hook with a different rate function. Use `surf_loop.design_bus` / `design_line` with `rate_fn` = air only, from `surf_target.air_db_per_m` at the scene humidity, anchored so that the 500 Hz–1 kHz mean = the dial. Keep every per-axis cut in the loop and count it as fixed loss in the fit (`make_spec(..., keep_cut_below_hz=float("inf"))`), so the bass decays to the dial (ST-2). Note that `None` means the D-SL3 default of 30 Hz. The UI already has a disabled `Natural (air)` chip (`#slMode_natural` in `sl_room_result.js`): enable it and add `natural` to `DECAY_MODES` in `app_server.py`. Flat bit-exact proof method: `prebuild\sl\tests\hash_scenes.py`.

SL7 is split in two, because building Natural mode, the parity suite, the migration and the A/B, *plus* re-recording every reference, is too much for one high-usage window. This half changes **no** default and **no** golden.
- **What to build:**
  1. **Natural (air) mode (ST-1 + ST-2).** A third Decay mode, `natural`, between Flat (2011) and Surfaces. It is the SL2 per-line hook with room-average rates from air only (ISO 9613-1 at the scene humidity, Eyring anchored so that the 500 Hz–1 kHz mean = the dial), the per-axis cut loss **folded** into the fit (ST-2: bass decays to the dial), the same guard, Render + Play.
     - Source: `handoff_build_support_2\roadmap\sound_tricks\proto\p1_freq_decay.diff` (the FREQ_DECAY hook) and SOUND_TRICKS §1/§3.
     - Surfaces mode already includes air, and D-SL3 handles its bass.
  2. **Flat (2011) parity suite.** Copy today's references (main golden + the ~77 references, current HANDOVER hashes) into a frozen `tests/refs_flat2011/`. Add `legacy_2011_profile()`: `decay_mode = "flat"`, SM57 on L/C/R, today's face cards, no Treatment rows. Add a test that renders every reference scene with that profile and compares it **bit-exact** against the frozen set. Today this test is identical to the normal golden test; after SL7b it is the only check on Flat mode.
  3. **Default flags, not flipped.** `DEFAULTS_2026 = {decay_mode: "surfaces", mic: "NeumannU87AiCardioid", cards: real_default + room-shell row}` and `DEFAULTS_2011` (today's values), selected by one switch `DEFAULT_SET = "2011"`. U87 touch points (from the old T6): app.js 97, app_server.py 636 / 1028–1030 / 1317–1319, render_pipeline.py 1351–1353 (rg first). **Migration:** a scene with no `decay_mode` loads as `flat` with its stored mics and cards.
  4. **Final A/B for Idle** (gate for SL7b). Render the golden scene + dry guitar + snare, loudness-matched to −23 LUFS, 24-bit, blind names plus a key file, into `handoff_build_support_2\ab_default_switch\`. Four renders:
     - A = today (`DEFAULT_SET = "2011"`);
     - B = Natural + U87;
     - C = Surfaces + U87 (the proposed new default);
     - D = Surfaces + SM57 (so the mic and decay changes can be told apart).

     Write the per-octave T20 of each render into the key file.
  5. **Dry run of the re-record:** run the reference-regeneration script with `DEFAULT_SET = "2026"` into a temp folder and record the count and time. Discard the output; don't commit it.
- **Cut line:**
  - Steps 1–3 + tests, committed.
  - Step 4 if green.
  - Step 5 last; if it is skipped, SL7b does it first.
- **Golden impact:** **NONE.** `DEFAULT_SET` stays "2011": the main golden and all references are bit-exact, and the new parity suite passes.
- **Done when:**
  - Natural mode T30 is within −4…+7 % of target at 500 Hz–8 kHz (box P1 result), and 125/250 Hz are no longer short (ST-2).
  - Flat parity is bit-exact.
  - Old scenes recall as Flat.
  - The A/B folder and key file exist.
- **Stop if:** any default render moves by one bit, Natural mode needs > +0.05 ms of Play CPU over Flat on top of Surfaces' budget, or the frozen refs can't be made bit-exact with the legacy profile. Report; don't patch the references.

**Idle 9 Oct (D-FLAT-2026):** the frozen refs_flat2011 set and legacy_2011_profile() use Smooth ON (as today's default, post-T4c). Smooth is not part of the 2011-vs-2026 default switch. Do not freeze the old Smooth-off proof.
