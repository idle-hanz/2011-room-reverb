# Microphone 1-pole Power cutoff (410, 466–467) — 2026-09-20

Path: `Instrument > Sound Processing > Microphone`. Existing Pictures. No new screenshot.

## Gain **VERIFIED** (466)

```
Dir → |x| → × 2 → Power X
C/O ───────────── Power Y
Power → 1 − → Gain
```

`Gain = 1 − (2·|Dir|)^C/O`

Clip to [0, 1] **LIKELY** (2·|Dir| can exceed 1). Dir=0 ⇒ Gain=1.

467 |Dir| ≈ 0.002…0.17 (32 voices). Engine uses `|θ|` from capsule look (**LIKELY** Distances Dir).

## Cutoff **VERIFIED** graph (410)

`Res → Log F→P → × Gain → 1-Pole P`. Audio In → LP → Out (to Mixer).

Same Log F/P as Air Abs. On-axis Gain=1 ⇒ **fc = Res**. Off-axis Gain→0 ⇒ P→0 ⇒ fc ≈ 8.2 Hz (MIDI P=0).

`fc = PtoF(FtoP(Res) × Gain)` with MIDI 69/440 (**LIKELY** NI F→P constants).

## Not in the FDN loop **VERIFIED** (472 / 410)

Diffuser Delay Out → Feedback Delay **and** Microphone. Hadamard sees unfiltered delay. Mic 1-pole is Mixer-facing only.

Sound Processing **MiF → Res**, **C/O → C/O** (214 / 460). MiF is **Mic Response**: **10 kHz dynamic → 20 kHz condenser** (Idle Hanz). Live dump **10000** (399). C/O Power Y still **1** (**LIKELY**; Function unread, not Car/Omni).

Polar `(1+cosθ)/2` on tap levels stays **ASSUMED**. This 1-pole is extra colour, not a replacement.
