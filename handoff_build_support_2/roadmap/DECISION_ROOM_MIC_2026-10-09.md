# D-ROOMMIC - room mic detaches and gets its own window

## Room mic spec (Idle, Fri 9 Oct 2026; locked decision D-ROOMMIC)
Idle's report: the room mic does not detach from the stand. It should move freely on the Source page like the other objects and have its own window and controls on the Mic page.
- Every strip (L, C, R) can be set to "Room mic" (T2 label, D-UI36). Each room mic has its OWN spot: room_<cap>_x / _y / _z / _yaw. The old shared room_x/y/z/yaw stays only as the fallback for old scenes (migration, bit-exact).
- LOCKED: when a strip is switched to Room mic, its spot starts at that strip's CURRENT position on the stand (and current aim), so the sound does not jump. Switching back ("Return to stand") restores the stand position. A saved scene's stored spot always wins on recall.
- Source page (floor and side views; drawn by room_editor.js): the room mic is its own object with its own icon and label, coloured to match its strip, never attached to the stand. Drag it on the floor (x, z), drag its height on the side view, and turn its aim with a small handle. It stops 10 cm short of walls (same "stop" rule as D-UI37). A faint line shows distance to the source. Pattern/aim are drawn on the icon.
- Mic page: a "Room mic" window below the stand mics, one per strip set to Room. Typed fields (T1 helper): X, Z, Height, Aim; read-only distance to source and nearest wall; its own preset, pattern, HPF and gain; a small polar diagram of that mic; a "Return to stand" button. Typing and dragging stay in sync.
- No sound change except through the controls themselves. Mirror and Linked must stay bit-exact; ORTF default unchanged (C off).
