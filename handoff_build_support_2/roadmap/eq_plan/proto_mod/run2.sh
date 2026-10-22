#!/bin/bash
cd /workspace/scratch_rot
PY=/workspace/scratch_er_dropout/venv/bin/python; OV='{"early_wet":0,"direct_wet":0,"dry_gain":0,"colour_mode":"BYPASS"}'; O=/workspace/scratch_rot/out2
run() { # name MOD_MS DCAP
  MOD_MS=$2 DCAP=$3 nohup $PY render.py sw "$OV" $O/ir_$1.f32 4000 > $O/ir_$1.log 2>&1 &
  GUITAR_NPY=/workspace/scratch_rot/guitar_mono.npy MOD_MS=$2 DCAP=$3 nohup $PY render.py sw "$OV" $O/gtr_$1.f32 16000 > $O/gtr_$1.log 2>&1 &
  GUITAR_NPY=/workspace/scratch_rot/tone440.npy MOD_MS=$2 DCAP=$3 nohup $PY render.py sw "$OV" $O/tone_$1.f32 4000 > $O/tone_$1.log 2>&1 &
}
run mod10 0.10 0; run mod15 0.15 0; run dcap 0 0.7; run mod10dcap 0.10 0.7
GUITAR_NPY=/workspace/scratch_rot/tone440.npy nohup $PY render.py sw "$OV" $O/tone_before.f32 4000 > $O/tone_before.log 2>&1 &
