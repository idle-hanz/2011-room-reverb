# INVESTIGATE chips (read-only, plan mode, no edits, no builds, no files written)

Read handoff_build_support_2/roadmap/OPEN_FAULTS_2026-10-10.md (F4, F5) and HANDOVER.md Current pin first.

Idle's reports: (F5) clicking a preset chip (room chips such as Hall/Studio/Club, and any other chips that load a preset) does not keep the mics where he put them; (F4) Hall still jumps in level when clicked.

Answer from the real code, with file and symbol names, each point tagged VERIFIED or ASSUMED:
1. List every chip/preset button in app.js and index.html and what each one writes (which state keys). For each, say whether it writes any of: mic_x_*, mic_y_*, mic_z_*, mic_pos_*, pin_m, mic yaw/aim, room_<cap>_x/y/z/yaw, third_mic, place_r, mic stand position, source position.
2. For F5: exactly which keys get reset or overwritten by which chip, and why (does the chip load a whole scene, replace state wholesale, or only call a reset?). Does it differ between room-size chips and mic-setup chips (ORTF, MS, etc.)?
3. What would "chips keep mic positions" mean safely? List which keys a room-size chip must NOT touch, and what must still change (room size, walls, materials). Flag any case where the old mic position would fall outside the new room and what the code does then (clamp, wall stop).
4. For F4: when a chip is clicked, does makeup, gain or anything level-related change in one step with no ramp? Is it the room size change, the makeup scalar (makeup_at_stand), the FDN parameters being swapped with no crossfade, or a mic moving? Separate cause from the sudden-parameter-change explanation Idle expects. Do not measure with new files; reason from code and existing measure_*.json.
5. Report small, safe cut lines for a fix session (F5 first, F4 separate), which tests and goldens each would touch, and whether either needs a sound decision from Idle. Make no recommendation to change sound.

Write nothing. Report findings only.
