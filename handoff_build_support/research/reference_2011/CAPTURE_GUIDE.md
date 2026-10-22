# 2011 reference capture guide (Idle, in Reaktor)

Written 27 Sep 2026 (BST). Goal: record impulse responses from the ORIGINAL `20 October 2011 room reverb.ens`, so `compare/compare_ref.py` can decide two things:

- **(a)** Keep the long two-stage tail (the in-loop Dffs allpass feeding back, late T60 6–25 s) or apply F2 so the tail follows the dial.
- **(b)** Play loop timing: one-sample (z^-1, Reaktor adds a unit delay in feedback loops) or same-sample solve (F5).

Tags: **VERIFIED** = seen in your Structure/panel screenshots (panel-controls.md, structure-screenshots-batch-6.md) or in the rebuild code. **ASSUMED** = my best guess. Check these before you trust them. **UNKNOWN** = you need to find it (list in section 8).

Time: about 60–90 min for the 6-capture core set. About 2.5 h for all 18.

---

## 0. What you need

| Item | Where |
|---|---|
| Impulse files (made for you, single sample at exactly 0.500 s, 40.5 s long, stereo 32-bit float) | `research\reference_2011\impulses\RR2011_impulse_48k_0dBFS_stereo.wav` (main). `..._48k_-20dBFS_stereo.wav` (use if 0 dBFS clips, see step 5.6). `..._44k1_...` (only for the optional 44.1 kHz capture, section 7). |
| Sidecar template (one JSON per WAV) | `research\reference_2011\compare\capture_template.json` |
| Host | Studio One (recommended, section 4A) or Reaktor standalone (section 4B) |
| The ensemble | `20 October 2011 room reverb.ens`. Open a **copy**, so nothing you change can hurt the original. |

**Why an impulse file and not a Reaktor-internal impulse:** the file goes through the same audio input path as music. It also puts the impulse at a known time (0.5 s), so pre-delay and sample-0 behaviour can be measured. **VERIFIED:** the harness finds the direct sound itself. It skips the first 0.3 ms after the impulse, because the Dffs allpass fires a feed-forward spike at t = 0.

---

## 1. Safety copy and snapshot (2 min)

1. In Explorer, copy `20 October 2011 room reverb.ens` to `RR2011_capture_copy.ens`, in the same folder.
2. Open the **copy** in Reaktor (File > Open Ensemble…).
3. Store your current panel state as a new snapshot, so you can always get back to it. In Reaktor 6: open the Side Pane (the **Browser/Snapshot** button at top left), go to the **Snapshot** tab, and click **Append** (or **+**). Name it `before_capture`. (Reaktor 5: the Snapshot window from the toolbar camera icon, then **Append**.) The exact button label differs between Reaktor versions (**ASSUMED**). You want "store a new snapshot", not "overwrite".

## 2. Audio settings: 48 kHz (2 min)

1. Reaktor standalone: **File > Audio and MIDI Settings… > Audio** tab. Set **Sample Rate = 48000**. Pick a **Buffer / Latency** of 512 samples or larger (it does not change the result, but it avoids dropouts).
   In Studio One, set **Studio One > Options > Audio Setup > Sample Rate = 48 kHz** in the Song Setup of the capture song instead, and ignore Reaktor's setting.
2. Write the Reaktor version from **Help > About** into the sidecar (`capture.reaktor_version`).

## 3. Fixed settings (same for every capture)

Set these once, then take a screenshot of each tab (section 6).

**Shared bottom strip (VERIFIED names, panel-controls.md):**

| Control | Set to | Why |
|---|---|---|
| **AGC** | **Off** | AGC would ride the gain and fake the decay. |
| **Clip Diffusion** | **On** (the green indicator, as in your live shots) | This is the state your screenshots show. The rebuild models the Clipper after × MDif. |
| **Volume trim** | Leave it, and **write the value down** | The harness normalises level, but the value is still useful. |
| **GainF** | the grid value (section 5) | This is the decay setting. |

**Surfaces tab (VERIFIED labels):**

| Control | Set to |
|---|---|
| **Stacked Macro** buttons | **All** (every surface on) |
| Sides / Ahead / Behind / Floor / Ceiling **dB** | **0** on all five (flat EQ). The harness cannot map the 2011 peak EQ yet, so flat makes the comparison fair. |
| **Freq / BW / Low** | Leave them (they do nothing at 0 dB, **ASSUMED**: a peak/shelf at 0 dB is flat). Write them down anyway. |
| Per-surface **Diffusion** (5 knobs) | **0.25 on all five** (**ASSUMED** to be a mid value; your live values were 0.16–0.85). Write down the exact values you land on. |
| **Diffusion Master** | the grid value (section 5). **VERIFIED** range 0 … −0.5, default −0.25 (Structure 485). |
| **Humidity** | the grid value (section 5). **VERIFIED** Structure range 100 … 700, default 400 (Structure 486). There is **no "off"** in 2011, so "humidity 0" becomes **700** (fc = Wet/Dis, highest = least air damping). |

**Room Dimension tab:** **Width X = 6**, **Ceiling Y = 3**, **Lenth Z = 8** (the typo is in the ensemble). The Lenth Z range 2…100 is **VERIFIED**. The Width X and Ceiling Y ranges are **UNKNOWN**: if 6 or 3 cannot be reached, use the nearest value you can get and write it down. Hold Ctrl (or Shift, depending on version) while dragging for fine steps, or double-click the value to type it if your Reaktor allows that.

**Sound Position tab:** leave the pad where it is, but **read the source position** (section 6, step 3). Do not move it between captures.

**Microphone tab (VERIFIED labels):**

| Control | Set to |
|---|---|
| **Mic Response** | **fully clockwise (max)**, then write the number down. The 2011 Res one-pole is not modelled in the rebuild, so max keeps it out of the comparison (**ASSUMED**: max = most open). |
| **Angle** | **0** |
| **Height / Depth / Car/Omni / Space** | Leave them and write them down (your live values: Height 1.1, Depth 0.1633, Car/Omni 0.764, Space 0.2145). |
| Instrument voices (sidebar, seen as **32**) | Do not change. |

When the fixed settings are in: **store them as a snapshot** named `capture_base` (Append again).

## 4. Recording

### 4A. Studio One (recommended: sample-exact and easy to repeat)

1. **File > New Song…** Sample rate **48 kHz**, resolution **32-bit float**. Name it `RR2011_capture`.
2. Drag `RR2011_impulse_48k_0dBFS_stereo.wav` onto a new **stereo** audio track, starting at **bar 1, beat 1** (time 0:00.000). In the Inspector, make sure the event is not transposed or faded (Event fade in/out = 0, no Timestretch: set the Track **Timestretch** mode to off / "Tempo = Don't follow").
3. On that track's **Insert** slot, add **Reaktor 6 (or 5) FX** (the effect version, not the instrument). Load `RR2011_capture_copy.ens` inside it, then recall the snapshot `capture_base`.
4. Track fader at **0.0 dB**, pan **centre**. Remove any plugins on the **Main** bus. Main fader at **0.0 dB**.
5. Set the loop range to exactly **0:00.000 → 0:40.500**. Drag the loop bar, then type the start/end times in the Transport.
6. For each grid point (section 5): set the panel values, then **Song > Export Mixdown…**. Use Format **Wave**, **32-bit float**, **48 kHz**, Range **Between Loop**, **no** dither, and **no** "Normalize". Enter the file name from section 5.
   - Export Mixdown renders offline, so buffer size and CPU cannot drop samples.
7. After each export, set a fresh value and export again. **Do not** reload the ensemble between captures. **Do** wait a moment after changing GainF so any old tail has died: Export Mixdown starts from silence anyway (**ASSUMED**: Studio One resets the plugin at render start. If you hear the old tail at the start of a file, press Stop, wait 40 s, and export again).

### 4B. Reaktor standalone (fallback)

1. **File > Audio and MIDI Settings… > Routing**: route the ensemble output to your interface. There are no audio inputs to worry about, because the impulse comes from Reaktor's own player.
2. Open the **Player/Recorder** (Reaktor 6: the audio-file / tape icon in the header. Reaktor 5: the toolbar Player). Load `RR2011_impulse_48k_0dBFS_stereo.wav` into the **Player** and switch its **loop off**. Set the **Recorder** format to 32-bit float at 48 kHz if it offers a choice. The exact button names are **ASSUMED**: look for the Player with a file slot and a separate **Rec** button.
3. Press **Rec**, then play the file, and stop at the end of the file (40.5 s). Rename the recorded file using section 5.
4. Standalone recording runs in real time. Check that there are no dropouts (the CPU meter stays under about 70%).

**Does the ensemble take audio in?** **ASSUMED yes** (it is a reverb). Check: in Structure, at the very top (Ensemble) level, look for **In** ports on the left of the instrument. If the only way sound gets in is an internal source, stop and tell the build team. The harness can still use the capture, but the time of the impulse must then be read from the file.

## 5. The settings grid and file names

**Decay setting = GainF.** The 2011 panel has **no Decay knob** (VERIFIED: panel-controls.md). Decay comes from **GainF** (the loop is Gain/32 into the unscaled ±1 Hadamard) and the Dffs self-loops. **Diffusion = Diffusion Master.**

| # | GainF | Diffusion Master | Humidity | Core set? |
|---|---|---|---|---|
| 1 | **1.00** | **−0.50** (your live value) | 400 | ✅ |
| 2 | 1.00 | −0.25 | 400 | ✅ |
| 3 | 1.00 | **0.00** | 400 | ✅ (no Dffs self-loop: this shows the plain FDN decay) |
| 4 | **0.80** | −0.50 | 400 | ✅ |
| 5 | **0.50** | −0.50 | 400 | ✅ |
| 6 | 1.00 | −0.50 | **700** (least air) | ✅ |
| 7–9 | 0.80 | −0.25 / 0.00 / −0.50 @700 | 400 / 400 / 700 | |
| 10–12 | 0.50 | −0.25 / 0.00 / −0.50 @700 | 400 / 400 / 700 | |
| 13–18 | 1.00 / 0.80 / 0.50 | −0.25 and 0.00 | 700 | |

- GainF range is **UNKNOWN** (you have seen about 0–1). If 1.00 is not the top of the range, also add one capture at the **top of the range**, and write down the range from its Properties (section 8).
- Humidity 700 only matters for the air-absorption comparison. Humidity 400 is the Structure default.

**File name** (the harness reads the JSON, not the name, but the name keeps things tidy):

```
RR2011_G{GainF:0.00}_DM{DiffusionMaster:+0.00}_HU{humidity}_R6x3x8_take{n}.wav
e.g.  RR2011_G1.00_DM-0.50_HU400_R6x3x8_take1.wav
      RR2011_G1.00_DM-0.50_HU400_R6x3x8_take1.json   <- same stem, copied from capture_template.json
```

For DM 0 write `DM+0.00`. Put all WAVs and JSONs in one folder, e.g. `Desktop\2011 Room Reverb\reference_2011_captures\`.

**Level check:** open the first file in Studio One. If the peak is above **0 dBFS** (32-bit float will not clip, but the ensemble's internal Clipper might), redo that capture with the **−20 dBFS** impulse and set `capture.impulse_dbfs = -20`. The harness scales for it.

## 6. What to screenshot and write down (per capture set, not per file)

The screenshots are for the record. The **numbers go into the JSON**. Put `null` for anything you could not read. Never guess.

1. **One screenshot of each panel tab** (Surfaces, Room Dimension, Sound Position, Microphone) after the fixed settings, plus the bottom strip. Name them `RR2011_panel_{tab}.png`.
2. For every capture, one screenshot of the **Surfaces tab** showing Diffusion Master and Humidity, plus the bottom strip showing **GainF**. Name it the same as the WAV, with `.png`.
3. **Structure readings** (once, after `capture_base`). Open Structure (the **Structure** button / F6 in Reaktor 5; the **Edit** / wrench view in Reaktor 6). Go to the **Controls** macro outputs (terminals 20–33, your shot 358). Hover the mouse over each output port. With the hint/info display on (the **i** button in the toolbar), the tooltip shows the current value (**ASSUMED**: the exact hint behaviour differs between versions. If no value shows, drag a **Numeric Readout** (Panel > Meter) onto the wire for a moment and delete it afterwards, without saving the ensemble). Write down:
   - **SX (23), SZ (24)**: source position → `source.SX_term23`, `source.SZ_term24`
   - **MSS (25), MRa (26), MY (27), HZ (28), Car (29), HF (30), HpF (31), Hp (32)** → the `mic.*` fields
   - **Diverg / MDPC** in the Prepare macro → `mic.diverg_MDPC`
4. **Diffuser Delay values** (the ones that decide the Dffs scale, and therefore the two-stage tail). Open the Diffuser Delay macro (your shots 462–465, 476). Read the **"Diffusion"** input value → `fdn.diffuser_diffusion_in`, plus **Dffs** and **Dis** on voices 1 and 2 → `fdn.dffs_voice1`, `fdn.dffs_voice2`, `fdn.dis_voice1`. Read these at **DM −0.50** and again at **DM 0.00**. If they change with DM, note both in `other.notes`.
   This is the single most useful number. The rebuild uses a constant (0.0333) for the Dffs knob, and the harness replaces it with your reading.

## 7. Optional extras (each is worth it if you have 10 min)

- **44.1 kHz capture:** set the song/Reaktor to **44.1 kHz** and use `RR2011_impulse_44k1_0dBFS_stereo.wav`. Capture grid point 1 only, named `..._SR44k1_take1.wav`, with `capture.sample_rate = 44100` in the JSON. The harness resamples it. It shows whether 2011 delay lengths are fixed in ms or in samples, which matters for F3 (48 kHz delay rounding).
- **Repeat take:** capture grid point 1 again as `take2`. If take1 and take2 differ, the ensemble has something random or time-varying in it, which is a very important thing to know.
- **Silence file:** export 10 s with the impulse event muted, as `RR2011_silence_take1.wav`, and put it in a subfolder `extras\` (the harness treats every top-level WAV as a capture and expects a JSON beside it). This gives the noise floor.

## 8. Controls whose exact name or range is UNKNOWN (please identify)

| What | How to identify |
|---|---|
| **GainF range / law** | Right-click the GainF knob > **Properties** (or select it in Structure and open Properties) > Function tab: write down Min / Max / Default / Step. |
| **Width X / Ceiling Y ranges** | Same Properties route (only Lenth Z is known: 2 … 100, default 51). |
| **Per-surface Diffusion range** and **Freq / BW / Low / dB** ranges (all except Ahead BW) | Properties on one knob of each type. |
| **Mic Response** max, and whether max = bypass | Properties. Also check whether the Res one-pole sits in the audio path at max. |
| **Ensemble audio inputs** (In ports) | Top-level Structure: look at the left edge of the instrument. |
| **Dry / direct control** | None was found on the panel. If you know of a dry/direct level anywhere (for example inside a macro), write it down. The harness assumes the direct path is at unity and there is no extra dry signal. |
| **HP Freq / HP In** panel location | These exist in Structure (terminals 31/32) but were not seen on the Microphone tab. Say where they are, or confirm they are hidden. |
| **Diffuser "Diffusion" input value** | Section 6, step 4. |
| **Sound Position pad** → SX/SZ | Section 6, step 3. |

## 9. Hand-off

Zip the capture folder and put it at `Desktop\2011 Room Reverb\reference_2011_captures.zip`. On the box, Grok (or Grok Build) runs:

```
PY=/workspace/scratch_er_dropout/venv/bin/python
$PY research/reference_2011/compare/compare_ref.py --refs <captures dir> --out <report dir> --lock-variants
```

and reads `COMPARE_REPORT.md` (verdicts (a)/(b) at the top) plus one EDC plot per capture. See `compare/README.md`.

When you are done: recall the `before_capture` snapshot, and close the copy **without saving**.
