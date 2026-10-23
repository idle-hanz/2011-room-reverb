# Hear the three Play strips (one goal)

Start at `CURRENT_BRIEF.md`. RUN_RULES 17-22. Do not reconcile `HANDOVER.md`. Do not touch 610-A. Do not lower 2.40 or 2.133.

R2 is in the tree. `WORKLET_VER` is 62. `app.js?v=69`. `pack_room.js?v=54`. Play posts the master strip, and an array or room strip only while that strip is on. Restart the app and Ctrl+F5 before listening. One strip per complaint.

If a strip is silent, that is one wiring fault. Trace that strip from the menu through `heardMix` to the worklet section (master is 10 and 12, array and room are section 13) and fix the break. Add a QUICK test. Empty live MD5 stays `b6c55d429fa63d6d0d3cd1fcc7d23e88`. If the level, the 610 trim, or a makeup formula is the complaint, stop and report. That is an audio law.

If the listen is clean, this run changes no DSP. Confirm the empty MD5 with the QUICK below and stop. No FULL. No app automation.

QUICK, from `software\`:

```
node --test tests\test_routing.mjs
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py tests\test_routing.py -q -p no:cacheprovider
```

Report under 20 lines.
