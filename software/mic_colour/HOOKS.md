# Mic colour hooks

Phase 2 draws the same H on the Mic desk and `POST /api/polar`. That drawing is not a fifth audio tap. Phase 3 (Play) uses this same colour (SOS default).

Colour is the capsule, once, when the sound arrives. It is not inside the Hadamard loop.

Default colour is the 27 Sep K=3 SOS fit (`colour_impl: "sos"`): w-table of LS+HS+HS, RBJ at the live rate, manufacturer HPF as extra Butterworth sections. `colour_impl: "fir"` keeps the Phase 3 cepstral impulse. On-axis `relative_db` is 0 dB and skips the filter. Rebuild at the AudioContext / render rate. Do not copy coefficients across rates.

`apply_mic` stays false. Nothing calls `mic_one_pole_coeff` on this path. The Structure microphone one-pole is not a colour mode.

## Call sites

1. `render_listen_direct_ir` — filter `Ld`, `Cd`, and `Rd` at that capsule’s direct-tap θ, then `apply_capsule_weights`, then × 0.55. Spike amplitude stays 1. No `pattern_gain` on these spikes. Do not filter the stereo pair that comes back.

2. `render_early_ir` — after that tap’s air dose and surface-card EQ, filter `bl` / `br` at `theta_l` / `theta_r`. There is no centre early buffer. `gradient_hp_hz` and `beaming_lp_hz` run only when the mode is `ASSUMED_TOYS`.

3. `render_fdn_ir` — `process_block_poly` with `apply_mic` false, filter each line, then sum that bus. L lines use the seed image’s `theta_l` and the L preset, C uses `theta_c`, R uses `theta_r`. Colour is applied to the emitted `y` and is not written into the delay. Do not colour `inject`.

`offaxis_tail` (default off) replaces that per-line FDN colour with one K=3 SOS per mic bus. G_tail(f) = −DI(f). The filter sits on the bus sum, outside the Hadamard, after routing and Bloom, before the mixer fold. Early and direct keep today’s filters. Inject stays uncoloured. Binaural `icOn` keeps today’s tail. `apply_capsule_colour` stays uncalled.

4. `live_fdn_params` / `live_stereo` / `fdn_worklet.js` / `live_fdn.js` — Play. `build_live_bank` packs SOS records (magic −2011) or FIR impulses at `sample_rate` from the AudioContext. It does not reuse a 44.1 kHz design. `live_stereo` runs the 32-line loop and applies that colour on the way out: the per-bus direct read (then × 0.55), the early-delay read (left and right only), and FDN `y`. Nothing writes those copies back. `xin` and the FDN inject stay uncoloured. The page calls that one C function and gets left and right. There is no ConvolverNode bank. `MEASURED_SHELF` and `BYPASS` omit `offaxis_shelf_gain_linear` and recompute makeup from those scalars. `ASSUMED_TOYS` keeps the shelf, skips the bank, and the unfiltered mix is what you hear. Centre early has no colour. Air is untouched. `WORKLET_VER` is 30. The page loads the wasm and passes the bytes in; the audio thread has no fetch. Each line's four rings sit together, sized to the 1000 ms cap plus a few samples. Lines that share one impulse share one filter. Early L/R uses the FDN line's filter. Do not build a second early bank. Two-source Play adds B’s FDN line onto A’s line before that filter. Early B uses that same filter.

`combined_ir`, the moving hop, and two-sources call the three builders. They do not own a fourth filter.

## Modes

| Mode | Fitter colour | −6 dB shelf in scalars | Early gradient / beaming |
|------|---------------|------------------------|--------------------------|
| `MEASURED_SHELF` (default) | SOS (FIR if `colour_impl=fir`) | off | off |
| `BYPASS` | off | off | off |
| `ASSUMED_TOYS` | off | on | on |

Missing preset ids are Shure SM57 (`ShureSM57`) on L, C, and R. Missing mode is `MEASURED_SHELF`. A preset load may set that capsule’s pattern, family, and polar. It does not write yaw, space, or `mic_setup`.

Air (`air_lp`, `fc = Wet/Dis`, assumed shelf) is unchanged. Wall-tone is not in this phase.
