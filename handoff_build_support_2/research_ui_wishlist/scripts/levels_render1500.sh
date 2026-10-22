#!/bin/bash
# Re-render the Render path at the client's IR length (1500 ms), same bodies as levels.sh.
SW=/workspace/build_support_2/snapshot_2026-10-02_1815/software
H=/workspace/build_support_2/3_phase_acceptance_tests/harness/lib
O=/workspace/build_support_2/research_ui_wishlist/data/levels
PY=/workspace/scratch_er_dropout/venv/bin/python
for k in default direct fdn early all0dB decay4 decay06 fb1_nolock; do
  (cd $SW && $PY $H/render_ir.py $SW "$(cat $O/body_$k.json)" $O/render1500_$k.f32 1500 48000 > $O/render1500_$k.log 2>&1) || echo "fail $k"
done; echo done
