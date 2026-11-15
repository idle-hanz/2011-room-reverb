# 2011 Room Reverb

Desktop room reverb. Play is the live preview. Render writes the WAV.

From `software\`:

```
.\.venv\Scripts\python.exe app_server.py
```

Open http://127.0.0.1:7860/

A Thursday run starts at `CURRENT_BRIEF.md` and `handoff_build_support_2\roadmap\thursday_prompts\RUN_RULES.md`.

The app has eight HTTP routes. Software level is 1/r. Shoebox faces stay A–F. Polygon faces are F1..Fn. `WORKLET_VER` is 65. There is no preamp, compressor, or bloom.

Pins: empty MD5 `06bb1aaa0f59d67402b160224e155089`, centre MD5 `64f8319d8bf4e33353f8681ec31140de`, splay live MD5 `6d996c03137772aaca9cebecab3358ac`. The full list is in `CURRENT_BRIEF.md`.

Tests, from `software\`, with `.\.venv\Scripts\python.exe`:

```
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe tests\selfcheck.py
node --test (Get-ChildItem tests\*.mjs | % FullName)
.\.venv\Scripts\python.exe -m pytest -n auto -m "not slow"
.\.venv\Scripts\python.exe -m pytest -n auto -m slow
```

PowerShell does not expand the glob. The last two commands are the end of a run, not each step.
