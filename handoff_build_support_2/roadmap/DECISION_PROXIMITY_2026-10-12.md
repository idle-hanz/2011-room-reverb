# D-PROX (locked by Idle, 2026-10-12)
1. Level floor: a source closer than r_floor (default 0.5 m) to a mic stops getting louder; level uses max(r, r_floor). Applies only below r_floor, so every scene with r >= 0.5 m is unchanged.
2. Proximity effect: below r_floor, a per-mic bass shelf rises instead, using the TRUE r. It is applied AT THE MIC (that mic's direct + early pickup) and NEVER enters the FDN or the tail.
3. A "Proximity" tick box appears on a mic only when its source is inside r_floor; default ON. Off = no shelf (the floor still applies).
4. Tuned by ear (Idle chose ear over measuring). Ear settings: d0 (acoustic-centre offset, default 0.055 m) and cap (default +18 dB).
Model: B = |a + (1-a)(1 + 1/(j k r_eff)) cos(theta)| / |a + (1-a) cos(theta)|, r_eff = r + d0. Omni none, cardioid about half of fig-8.
Research: /workspace/proximity/PROXIMITY_FIT.md (box). The data is thin; the fig-8 values are theory only.
