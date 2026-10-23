# Routing brick (one goal)

Do not open the app. Do not touch 610-A. Do not retune makeup. QUICK only if code changed. No FULL suite.

The routing listen guitar is a brick. `handoff_build_support_2\roadmap\overnight\routing_listen\array_neve_glue_room_610_crush.wav`, first 3 s: crest 0.26 dB, 93% of samples over 0.95. `handoff_build_support_2\roadmap\overnight\bloom_listen\room_crush.wav` at amount 100 stays under the knee: crest 24.9 dB, limiter samples 0.

On that same routing body, one render. Print six peaks, before `soft_limit`: room bus after the preamp, after the comp, after the fold; array bus the same three.

If the jump is the two amount makeups adding, put one trim on the sum and stop. If the jump is inside the 610 flux add, stop and say so. That trim is Idle's decision.

QUICK, from `software\`, only if you edited code:

```
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py tests\test_routing.py -q -p no:cacheprovider
```

Report under 20 lines: which of the six peaks jumped, by how much, and the one change or the stop.
