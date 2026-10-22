# s5_surf_1010: D-UI26 = A folded into S5 (box, 3 Oct 2026 10:10–11:08 BST)

- `S5_PROMPT_D-UI26.md`: the S5 prompt to paste. The roadmap §5 S5 block summarises it and points here.
- `f2/`: F2 cold-fields patch rebased onto the 1010 tree (wasm a80209d2e69c) and proven bit-exact (`exact_1010.json`); SURF CPU prototypes (`SURF_proto.c`, K2/K4/K6/K4D2 wasm, all bit-exact); benches `bench2_1032/1054/1100.json`.
- `expect/`: expected default change, Render prototype A vs shipped (`expect_default.json`).
- `fit/`: per-line K-biquad fit error (`fit_k.json`).
- `guitar/`: before/after WAVs + `LISTENING_CHECKLIST.md`.
- `protoA_root/software/render_pipeline.py`: Render prototype A, box-only. Do not copy it into the real tree.
- `ROADMAP_before_1100.md` and `REPORT_sui2_before_1100.md`: copies taken before this edit.
