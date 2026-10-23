# Master strip in Play (one goal)

Do not touch 610-A, makeup, or array/room on Play. Those stay Render-only until R2. The brick stop stands: room-bus peak went from 0.246 to 301186 inside the 610 flux add. Do not reopen it.

The Master comp menu posts nothing while Amount is 0. `routing_scene.js` `live` requires amount > 0, and `test_routing.mjs` locks that. Selecting Room Crush leaves Amount at 0, so Play stays the off path.

Fix the menu, not the engine. When the Master comp changes off to a preset and Amount is 0, set Amount to 100 in that handler. A saved scene that already has Amount 0 stays off. Preamp-only is unchanged.

Gate: a node test that the menu arm posts `bloom_preset` and `bloom_amount` 100, and `masterScene` of a stored Amount 0 still returns {}. Off-body live MD5 stays `b6c55d429fa63d6d0d3cd1fcc7d23e88`.

QUICK, from `software\`:

```
node --test tests\test_routing.mjs
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py tests\test_routing.py -q -p no:cacheprovider
```

Report under 20 lines. No FULL suite. No app.
