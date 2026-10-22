# T2 · Mixer L/R buttons (D-UI31). Effort: high. Decisions: **D-UI36 locked** ("On stand"/"Room mic", mic Solo = solo-in-place).
Read `handoff_build_support_2\roadmap\prebuild\t2_mixer\README.md`; integrate `lr_buttons.js` (route rows index.html 219–226/238–245/257–264, Ø buttons 230/249/268, bindDesk 830–837 + 850–861, paintDesk 610). Copy `test_lr_buttons.mjs` and `handoff_build_support_2\roadmap\prebuild\tests_py\test_t2_lr_null_draft.py` + `_harness.py` into `software\tests`.
- **Cut line:** buttons + state mapping + both test files green. Then B8 (pot greyed off-pan). Mic Solo + rename (D-UI36), then B5 (Host strip at 1280), P5/P6 only if green.
- **Golden impact:** none. Old scenes must map 1:1 (null test). `tests/test_smix_desk.py` must stay green.
- **Stop if:** any null row fails, a golden moves, or MS classic stops reading L+R = both on C.
