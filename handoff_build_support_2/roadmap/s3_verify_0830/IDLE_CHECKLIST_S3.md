# S3 click-through for Idle (about 5 minutes)

1. Open the app and click the **Source** tab (2nd tab, after "Floor · Side · 3D"). You should see **Omni** and "Omni. No facing.", with no ring on the top view. The right column shows only Room size, Preview and Advanced, with no Mix or Hadamard.
2. In **Radiation**, choose **Strings → Violin (BYU, 200–2500 Hz)**. Yaw and Pitch jump to face the mic, the line says "+0° off the mic", and a hollow ring appears next to the source dot.
3. **Drag the ring** around the dot: Yaw follows. Hold **Shift** while dragging and it snaps in 15° steps.
4. Rest the pointer on the ring and **scroll the wheel**: each notch is 5°.
5. **Double-click the ring**: it faces the mic again.
6. Click the top view once, then press **→ / ←** (yaw ±5°), **↑ / ↓** (pitch ±5°), **F** (face the mic) and **O** (back to Omni).
7. Pick Violin again, press **Play live**, then click **Face away** and **Face mic** under the sliders. The direct sound gets duller and quieter facing away, and brighter facing the mic. The tail should not change.
8. Click the **Paths** tab and rest the pointer on a path line. A tooltip shows "az … el …" and "1 kHz … dB, 4 kHz … dB".
9. Click **Floor · Side · 3D** and look in the 3D panel for a small cone on source A (zoom with the wheel).
10. Known bug, waiting on the fix-up, so no need to report it: after **Upload WAV** (stereo) → **Two sources** → **Mirror** on, the **Source B** chip shows Omni, and B sounds omni.
    - Workaround for now: on the Source tab, click **Source B**, pick the same preset, then click **Face mic**.
