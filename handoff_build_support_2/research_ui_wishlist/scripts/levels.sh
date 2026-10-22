#!/bin/bash
# Item 11: per-bus IR energy at the default client state, Render (Python) and Play (wasm) paths.
set -e
SW=/workspace/build_support_2/snapshot_2026-10-02_1815/software
H=/workspace/build_support_2/3_phase_acceptance_tests/harness/lib
O=/workspace/build_support_2/research_ui_wishlist/data/levels
PY=/workspace/scratch_er_dropout/venv/bin/python
BASE=$(cat /workspace/build_support_2/research_ui_wishlist/data/client_state_1815.json | $PY -c "import json,sys;print(json.dumps(json.load(sys.stdin)))")
MICS='"mic_gain_l":1,"mic_gain_c":1,"mic_gain_r":1,"mic_pan_l":-1,"mic_pan_c":0,"mic_pan_r":1,"mic_phase_l":1,"mic_phase_c":1,"mic_phase_r":1'
declare -A SC
SC[default]='{"direct_wet":0,"fdn_wet":1,"early_wet":0,"dry_gain":0,'$MICS'}'
SC[direct]='{"direct_wet":1,"fdn_wet":0,"early_wet":0,"dry_gain":0,'$MICS'}'
SC[fdn]='{"direct_wet":0,"fdn_wet":1,"early_wet":0,"dry_gain":0,'$MICS'}'
SC[early]='{"direct_wet":0,"fdn_wet":0,"early_wet":1,"dry_gain":0,'$MICS'}'
SC[all0dB]='{"direct_wet":1,"fdn_wet":1,"early_wet":1,"dry_gain":0,'$MICS'}'
SC[hall]='{"direct_wet":1,"fdn_wet":1,"early_wet":0,"dry_gain":0,'$MICS',"W":57,"H":34,"L":97,"reaktor_parity":true,"decay_lock":false,"fdn_g":1}'
SC[studio_fb085]='{"direct_wet":0,"fdn_wet":1,"early_wet":0,"dry_gain":0,'$MICS',"decay_lock":false,"fdn_g":0.85}'
SC[fb1_nolock]='{"direct_wet":0,"fdn_wet":1,"early_wet":0,"dry_gain":0,'$MICS',"decay_lock":false,"fdn_g":1}'
SC[decay4]='{"direct_wet":0,"fdn_wet":1,"early_wet":0,"dry_gain":0,'$MICS',"decay_s":4.0}'
SC[decay06]='{"direct_wet":0,"fdn_wet":1,"early_wet":0,"dry_gain":0,'$MICS',"decay_s":0.6}'
for k in "${!SC[@]}"; do
  OV=$($PY -c "import json,sys;b=json.loads(sys.argv[1]);b.update(json.loads(sys.argv[2]));print(json.dumps(b))" "$BASE" "${SC[$k]}")
  echo "$OV" > $O/body_$k.json
  (cd $SW && $PY $H/render_ir.py $SW "$OV" $O/render_$k.f32 3000 48000 > $O/render_$k.log 2>&1) || echo "render $k failed"
  $PY $H/dump_params.py $SW "$OV" $O/params_$k.json 48000 > $O/params_$k.log 2>&1 || echo "params $k failed"
  node $H/wasm_run.js $SW $O/params_$k.json '{}' ir 3 $O/play_$k.f32 > $O/play_$k.log 2>&1 || echo "play $k failed"
done
echo done
