# DECISION D-SRC-DIST-LEVEL (Idle, 2026-10-11, locked)

A source that moves toward the mics must get LOUDER (and one that moves away, quieter), under the 1/r law (D-TLAW).

Idle's reasoning: the automatic gain (makeup) in 2011 exists to keep the tail level steady as the FDN feedback / decay goes up, so a room can be made more reverberant without turning a second control down. It was never meant to cancel the distance between source and mics. The distance law was 1/r.

Consequence for the build: makeup must follow the room's decay/feedback (energy the loop builds up), not the source-to-mic distance. Freeze makeup against source distance the same way D-MAKEUP-FREEZE froze it against mic (stand) distance: reference = the default source position. The default scene stays bit-exact (goldens do not move); a moved source then follows 1/r (about 6 dB per doubling) through the injects.
Overrides: the open question in OPEN_FAULTS "source approaching stand mics". Does NOT change the limiter, the 0.7 target logic for decay, Smooth, or TLAW.
Needs a read-only review first (standing rule).
