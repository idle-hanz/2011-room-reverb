#!/bin/bash
# TEST-ONLY: runs compare_ref.py on the four synthetic / self stand-ins (NOT 2011 data).
cd "$(dirname "$0")"
PY=${PY:-/workspace/scratch_er_dropout/venv/bin/python}
for ts in TS1_synth_two_stage TS2_synth_single TS3_rebuild_play_current TS4_rebuild_play_F5 TS5_rebuild_play_F1F3; do
  $PY compare_ref.py --refs test_standins/$ts --out test_reports/$ts --play-secs 10 --render-secs 4 \
      --label "TEST-ONLY stand-in $ts: NOT 2011 data" --jobs 2 || echo FAIL $ts
done
