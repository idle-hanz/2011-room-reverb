#!/bin/bash
cd /workspace/scratch_rot
PY=/workspace/scratch_er_dropout/venv/bin/python; OV='{"early_wet":0,"direct_wet":0,"dry_gain":0,"colour_mode":"BYPASS"}'; O=/workspace/scratch_rot/out
for v in "before 0 0.3" "rot5 0.05 0.3" "rot10 0.10 0.5"; do set -- $v
 ROT_EPS=$2 ROT_HZ=$3 nohup $PY render.py sw "$OV" $O/ir_$1.f32 4000 > $O/ir_$1.log 2>&1 &
 GUITAR_NPY=/workspace/scratch_rot/guitar_mono.npy ROT_EPS=$2 ROT_HZ=$3 nohup $PY render.py sw "$OV" $O/gtr_$1.f32 16000 > $O/gtr_$1.log 2>&1 &
done
