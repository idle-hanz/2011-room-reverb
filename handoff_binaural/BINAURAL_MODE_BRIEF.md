# BINAURAL MODE: build brief for Grok Build

Written 30 Sep 2026 (BST) for the 2011 Room Reverb rebuild. Target tree: the p5 layout (`build_support_2/work/p5/software`).
Tags: **VERIFIED** = measured or read by a script/test in this pack; **ASSUMED** = judgement; **LOCKED** = decided by Idle
on 30 Sep 2026 (`DECISIONS_LOCKED_2026-09-30.md`, read that first). Updated 30 Sep 2026 21:20 BST for the locked decisions.
Nothing in `software\` was changed. This brief is the spec; `binaural_fitter/reference.py` is a runnable reference of §3.

## 0. What Build gets

| Item | Path in the pack |
|---|---|
| 3 MEASURED binaural presets | `presets/binaural/{SADIE2_KU100,SADIE2_KEMAR,THK_KU100_FF}.json` (`mic_fitter.binaural_preset.v1`) |
| Per-rate SOS grid tables, K = 6 (ship) and K = 3 (alt) | `presets/binaural/sos_tables/{44100,48000}/<id>.json`, `<id>.K3.json` (`colour_sos_grid.v1`) |
| Index (separate from the 20 mic presets, which are untouched) | `presets/binaural/index.json` |
| Reference mapping (ears, ITD, level, node, record) | `binaural_fitter/reference.py` |
| Tests: pack (pass now) and acceptance (xfail until built) | `tests/test_binaural_presets.py`, `tests/test_binaural_mode_acceptance.py` |
| Numbers | `reports/SUMMARY.md`, `reports/metrics_G60.json` |
| Licences | `DATA_LICENCES.md`, `LICENSES/` |
| Locked decisions (read first) | `DECISIONS_LOCKED_2026-09-30.md` |
| Binaural image set with rear images (LOCKED) | `presets/binaural/image_sets/binaural_rear32.json`, `binaural_fitter/rear_images.py` |
| Diffuse tail IC target + mixer FIRs per head, 44.1/48 kHz (LOCKED) | `presets/binaural/tail_ic/<id>.json`, `binaural_fitter/tail_ic.py` |
| Locked-decision proofs (pass now) | `tests/test_binaural_locked.py`; numbers `reports/rear_images.json`, `reports/tail_ic.json` |

## 1. Locks respected (unchanged)

Unscaled Hadamard FDN; early images excite the FDN; 1/r² level; per-hit filter cascade; stage order
**source > air > surfaces/scattering > mic colour** (the HRTF *is* the mic colour stage, last); direct path air-free.
The HRTF colour replaces the capsule pattern + measured-mic colour for the two ears. It is not inside the Hadamard loop
(same rule as HOOKS.md: colour on the way out, never written back, inject stays uncoloured).

## 2. UI

### 2.1 Mic setup dropdown

Add `<option value="binaural">Binaural (dummy head)</option>` to `#mic_setup` (`static/index.html`, after `mono_c`),
and a `binaural` entry in `MIC_SETUPS` (`static/js/app.js`):

```js
binaural: { space: null /* from preset */, toe_half_deg: 90, car_omni: 0, polar: ["L", "R"],
  pattern_l: "omni", pattern_c: "omni", pattern_r: "omni",
  family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
  polar_l: 0, polar_c: 0, polar_r: 0,
  yaw_l_deg: -90, yaw_c_deg: 0, yaw_r_deg: 90, binaural: true }
```

When `mic_setup == "binaural"`:

- **Centre capsule muted and disabled**: C row greyed, `mic_gain_c` forced 0 on the server, C bus skipped in the colour
  bank (buses `l`, `r` only). Mix desk C strip shows "off (binaural)".
- **Ears at a FIXED spacing** = the head preset's `ear_spacing_m` (VERIFIED from SOFA `ReceiverPosition`):
  **0.180 m** for `SADIE2_KU100` (default) and `SADIE2_KEMAR`, **0.175 m** for `THK_KU100_FF`. The Space slider is hidden
  (or shown read-only "Ear spacing 0.180 m (head)").
- **Fixed ear yaw ±90°** (L −90, R +90 in the K1 convention). Capsule yaw handles, `link_lr_yaw`, `align_horizontal`,
  `toe_half_deg`, `centre_dz`, `ms_decode` hidden/locked.
- **Patterns replaced by the HRTF**: pattern/family/polar rows hidden; `mic_preset_l/c/r`, `preset_owns_pattern`,
  `mic_hpf_*` hidden (no manufacturer HPF on a dummy head). A **Head** selector replaces the mic preset selectors:
  lists `presets/binaural/index.json` (default `SADIE2_KU100`), with licence shown in the tooltip.
- **Head placed and rotated as one unit**: position = existing Stand X/Z (`mcx`, `mcz`) and height (`my`); new
  **Head yaw** (`head_yaw_deg`, ±180°, 0 = facing +Z) slider and a rotate handle on the Floor view. The ears rotate with
  the head (today capsule X offsets do *not* rotate with yaw; binaural must, see §3.1).
- Leaving binaural restores the previous setup's values (keep a stash, like the `custom` path).

### 2.2 Display changes (Mic tab)

- The capsule array drawing becomes a **head with ears**: top view (circle, nose toward look, L/R ear markers at
  ±spacing/2), side view (head at `my`, ear axis), and the 3D view (sphere + nose + ear stubs; three.js already vendored).
- The capsule polar is replaced by an **HRTF polar + ILD panel**: per-ear octave-band level vs azimuth at el 0 for
  500 / 2k / 4k / 8k Hz from the shipped tables (the same curves as `plots/binaural/*_polar_top.png`), and an ILD-vs-azimuth
  plot (like `*_ild_itd.png` left). Draw from the fitted SOS (what you hear), not the raw data.
- A persistent note: **"Binaural: listen on headphones. Speakers will not reproduce the head cues."**
- A status line if the rate is unsupported (§4) and the head preset's licence line (Apache-2.0 / CC BY-SA 3.0).

## 3. Engine mapping (reference: `binaural_fitter/reference.py`, tests in `tests/test_binaural_presets.py` PASS)

### 3.1 Ear positions (rotate with the head)

Engine axes (VERIFIED p5): X right, Y up, Z forward; `look(ψ) = (sin ψ, 0, cos ψ)` with `YAW_X_SIGN = +1`.
Head right vector `right(ψ) = (cos ψ, 0, −sin ψ)`. With head centre `H = (mcx, my, mcz)` and spacing `s`:
`L = H − (s/2)·right(ψ)`, `R = H + (s/2)·right(ψ)`. At ψ = 0 this equals today's `mic_positions` (L at smaller X).

### 3.2 Direction of each image relative to the head

`u = (image − H)/|image − H|`; `az = atan2(u·(−right), u·look)` (degrees, **+ = left**, SOFA convention),
`el = asin(u_y)`. Store `az_head_deg`, `el_head_deg` on each `ImageTap`. One direction per image from the **head
centre** for both ears (the per-ear colour is the HRTF of that direction). Lateral angle for ITD:
`θ_lat = asin(cos el · sin az)`.

### 3.3 Delay: geometry + ITD correction (VERIFIED numbers, `reports/SUMMARY.md` ITD table)

Each ear keeps its own geometric path delay `d_ear / c` (c = 340 m/s engine constant), which gives the near-field
parallax for free. Free-field ear points under-estimate the ITD of a real head:

| preset | measured max ITD (LF x-corr < 1.5 kHz) | geometry-only max | RMS error: geometry / +Woodworth / +table |
|---|---|---|---|
| SADIE2_KU100 (0.180 m) | 797 µs | 529 µs | 132 / 28 / **25 µs** |
| SADIE2_KEMAR (0.180 m) | 721 µs | 529 µs | 106 / 39 / **36 µs** |
| THK_KU100_FF (0.175 m) | 773 µs | 515 µs | 130 / 20 / **13 µs** |

So add a per-image correction, computed once at tap-build time (no audio-rate cost):
`D = correction_us(θ_lat)` from the preset's `itd.correction_us` table (5° lateral bins, linear interpolation;
table = median measured LF ITD − (s/c)·sin θ_lat, antisymmetrised so D(0) = 0). Apply causally to the far ear only:
`t_R += max(D, 0)`, `t_L += max(−D, 0)`. Fallback (`binaural_itd_mode = woodworth`): `ITD = k(θ + sin θ)` with the
preset's `itd.k_us` (a_eff 0.111–0.119 m at c = 343; LF ITD of a real head is larger than the HF/Woodworth-radius value).
Sign (VERIFIED): a left source gives `t_R > t_L`. Play already has fractional delays (F3), so the correction is just a
different delay per line/tap.

### 3.4 Level: 1/r² from the head centre (LOCKED 2026-09-30)

The engine lock is amplitude 1/r² per receiver. With point ears 0.18 m apart that alone would add a lateral "ILD" of
**+3.1 dB at 1 m, +1.6 dB at 2 m, +1.0 dB at 3 m, +0.3 dB at 10 m** (VERIFIED) on top of the HRTF, whose ILD already
includes the head. **Locked:** in binaural mode both ears use `1/r_head²`, with r measured from the head centre, so
`level_l == level_r` and the ILD comes only from the HRTF. The 1/r² law itself is unchanged; only its reference point
moves. `per_ear` is not offered in the UI.

### 3.5 Pattern and centre

`press = level`, `grad = 0` (omni) for L/R; C: `level_c = press_c = grad_c = 0`. `ms_decode` false.
The ASSUMED_TOYS early gradient/beaming filters are off in binaural.

### 3.6 Colour entries (the IIR colour format)

- **Grid G60** (60 nodes, head-relative): el +90 (1), +60 (8, 45° az), +30 (12, 30°), 0 (18, **20°**), −30 (12),
  −60 (8), −90 (1). Lookup: nearest node by great-circle angle (no interpolation).
- **K = 6 and one mirror-symmetric table (LOCKED 2026-09-30):** tables are L/R mirror-averaged, so the R ear at node n
  uses the **L record of mirror(n)**. One 60-record table serves both ears. Entry key: `(binaural_preset, node, sr)`; no θ.
  The K = 3 tables stay in the pack for comparison only; they are not exposed.
- **Entry count vs MAX_IRS 64 (VERIFIED, with the LOCKED rear-image set, `reports/rear_images.json`):** records
  (mirror-shared) and filters per ear. Head yaw 0: default scene 24 / 21, two sources apart (A 2.6 / B 3.4) 24 / 24,
  small room 28 / 25, hall 19 / 19, head mid-room 28 / 22. Head yaw 90°: 32–38 records (max 38, small room), two
  sources 36. Head yaw 180°: same as yaw 0. Worst case (every node) is still the **fixed bank of 60 ≤ 64**. So
  two-source Play colour stays on in binaural mode, unlike ORTF today (146 > 64, colour off). The p5 front-only set
  needed 17–22 records at yaw 0 (up to 40 at yaw 90 with two sources).
- **Records**: `pack_record(sos)` unchanged (magic −2011, K sections, b0 b1 b2 a1 a2), `run_sos` unchanged. K = 6 ≤
  `MAX_SOS` 6 (VERIFIED live_stereo.c). No HPF sections are added in binaural mode, so K never exceeds 6.
- Build a `mic_colour/binaural.py` (`BinauralColour`) alongside `MicColour`; `build_live_bank` gets a binaural branch
  that indexes by node instead of θ (same `_Indexer` dedupe, `direct`/`fdn`/`early` maps for buses l/r only).
- **Float32 (VERIFIED):** storing coefficients as float32 changes the response by ≤ 0.005 dB; max pole radius 0.9988.

### 3.7 Early reflections (floor/ceiling and rear included)

Same per-image mapping, over the binaural image set (§3.10). Floor/ceiling images have elevation (−65° … +65°,
VERIFIED), covered by the ±30/±60 rings. Rear images arrive from |az| > 90° (VERIFIED for the default scene).
Surfaces/scattering/air stay before the HRTF (stage order).
**Play routing change (VERIFIED need):** today early L/R joins the FDN line's filter, and `early_target()` in
`live_stereo.c` falls back to the line's FDN filter unless some FDN line uses the early record. In diffuse tail mode
(§3.9) the FDN lines are uncoloured (`fdnIdx = −1`), so each early tap must be routed to **its own node record**. The
filter count is unchanged (distinct records per ear, the numbers in §3.6).

### 3.8 Direct path

Gets the HRTF too: `render_listen_direct_ir` filters `Ld`/`Rd` with the direct tap's node record per ear (no `Cd`),
then the existing ×0.55 fold. Direct stays air-free.

### 3.9 FDN tail: diffuse, mixed to the head's measured interaural coherence (LOCKED 2026-09-30)

**Target (MEASURED):** the chosen head's diffuse-field interaural coherence Re{IC(f)}, area-weighted over the measured
sphere, shipped per head in `presets/binaural/tail_ic/<id>.json` (`target.f_hz`, `target.ic_real`). SADIE2_KU100
(default): 0.94 at 100 Hz, 0.52 at 300 Hz, first zero at about 500 Hz, −0.145 at 700 Hz, |IC| ≤ 0.05 above 1 kHz.

**Why a mixer is needed (VERIFIED, p5 FDN, `reports/tail_ic.json`):** Play/Render run one 32-line loop per bus. In
binaural mode the L and R loops differ only by per-ear delays (and small level differences), and their tail sums are coherent at 0.03–0.35 in the
125–250 Hz bands. That is far below the head's 0.66–0.91 there (max band error 0.76–0.88). So today's tail sounds too
wide at low frequencies over headphones.

**Method (reference `binaural_fitter/tail_ic.py`; Build implements the same):**
1. Lines stay **uncoloured** in this mode. The presets are diffuse-field equalised, so the diffuse-field average of the
   HRTF power is flat (SADIE within 0.3 dB over 100 Hz–16 kHz, VERIFIED), and no timbre jump is expected (ASSUMED).
   Loops, delays, Hadamard and injection are unchanged (locks).
2. Two near-uncorrelated tail signals: `A = √2·Σ even lines of the L loop`, `B = √2·Σ odd lines of the R loop`.
   Measured |IC(A,B)| ≤ 0.17 in every 1/3-octave band and within the estimator noise. Power A/L-sum = 1.04 (VERIFIED).
3. 2×2 frequency-dependent mixer: `L = Hc·A + Hs·B`, `R = Hs·A + Hc·B`, where `Hc = cos φ(f)`, `Hs = sin φ(f)` and
   `sin 2φ(f) = IC_target(f)`. For uncorrelated, equal-power inputs the output coherence equals the target exactly and
   the power is kept (`Hc² + Hs² = 1`).
4. Realised as **two linear-phase FIRs on mid/side**: `M = A + B`, `S = A − B`, `L = (hp∗M + hm∗S)/2`,
   `R = (hp∗M − hm∗S)/2`, with `hp = hc + hs` and `hm = hc − hs`. **N = 513 taps** (Hann-windowed frequency sampling)
   at both 44.1 and 48 kHz, shipped in `tail_ic/<id>.json` → `fir["44100"|"48000"].hp/hm`.
   Design error (VERIFIED, 125 Hz–16 kHz): max |ΔIC| 0.016–0.024 and power ≤ 0.06 dB (N = 257: 0.057–0.085 / 0.19 dB;
   N = 1025: 0.007). Latency is 256 samples (5.3 ms at 48 kHz, 5.8 ms at 44.1 kHz), and only the FDN tail gets it.
   The tail is not directional, so this is ASSUMED inaudible. If Build wants less, N = 257 (2.7 ms) is the fallback.
5. **Result on the p5 FDN (VERIFIED, rear-image set, 4 s tail, 100 ms onward):**
   - Default scene: max 1/3-octave |ΔIC| 0.065, RMS 0.028.
   - Small room: max 0.098, RMS 0.044.
   - These are inside the estimator noise floor for that length (independent-noise max |IC| median 0.09, p95 0.13).
   - Synthetic independent noise (20 s): max 0.039. Tail level change +0.17 dB.

In binaural mode the C loop is not needed (C muted). Skipping it is a Build option; the CPU saving has not been measured.
Plot: `plots/binaural/tail_ic_SADIE2_KU100.png`. Proof: `tests/test_binaural_locked.py::test_engine_tail_coherence_matches_head`.

### 3.10 Rear images in binaural mode (LOCKED 2026-09-30)

VERIFIED today: the p5 32-image set (`LIVE_32`) uses n_z ∈ {0, 1, 2} only, so with the head facing +Z every early arrival
is within about ±65°. Nothing arrives from behind.

**What changes:** Play is compiled with **N = 32 lines, one early image per line** (VERIFIED `live_stereo.c`), and the
FDN is excited by those images (lock). So in binaural mode the image table is **`binaural_rear32`**, a 32-image set
(`presets/binaural/image_sets/binaural_rear32.json`). It keeps `LIVE_32`'s order and replaces 7 slots:
- the 3 duplicate voices go: (0,1,1)#2, (0,0,1)#2 and (−1,−2,0)#2;
- the 4 weakest images go, the order-4 corners (±1,±2,1);
- 2 missing partners come in: (0,−1,1), the floor + front-wall partner of (0,1,1), and (−1,−1,0), the partner of
  (1,−1,0). The set is now mirror-symmetric in X;
- **5 rear images come in (Behind wall, n_z = −1):** (0,0,−1), (±1,0,−1) and (0,±1,−1).

The direct image stays at index 2 (`direct_line_index` unchanged). The selection rule is ASSUMED (design). The counts,
symmetry and arrival directions are VERIFIED. The FDN delays follow the new images (delays = image ms, as the lock
says), so the tail changes slightly in binaural mode only. Every other mic setup keeps `LIVE_32`. Render with
`hadamard_n ≠ 32` keeps its own set; `64like` already contains the full n_z = −1 slab.

**Checked on the pack reference (VERIFIED, `tests/test_binaural_locked.py`):**
- In the default scene all 5 rear images arrive from behind: az 176° (three, at el −23°, −3° and +28°), +138° and −134°.
- Lateralisation: rear-left (+138°) has the left ear first by 461–480 µs and louder by 6.8–8.0 dB (mean 1–8 kHz);
  rear-right is the mirror.
- Front/back colour: every horizontal rear node's record differs from its front mirror, which has the same ITD, by
  1.2–2.2 dB RMS minimum (median 4.1–5.1 dB) over 2–12 kHz. The default-scene rear taps differ by 2.2–7.0 dB.
- A single-frequency ILD at 4 kHz is not a reliable rear cue (THK gives the wrong sign there at ±134°), so the tests use
  the 1–8 kHz mean.

**Entry count:** see §3.6 (max 38 records seen, fixed bank 60 ≤ 64).
**CPU:** see §5 (+4 filters per ear at yaw 0 compared with the front-only set).
Plot: `plots/binaural/rear_images_top.png`.

## 4. Sample-rate rules

Same as the locked colour rule: tables for **44.1 kHz** (`sos_tables/44100/`) and **48 kHz** (`sos_tables/48000/`,
put at the top level if Build keeps its 48k-at-top convention). Each was fitted at its own rate with RBJ at that rate;
SADIE from its native 44.1/48 files, THK from 48 kHz data (magnitude target in Hz, valid to 20 kHz < 22.05 kHz).
Reject a table whose `fit_fs` ≠ rate. **Any other rate: binaural colour OFF with a visible notice**
("Binaural colour is OFF: the audio device runs at X kHz; binaural HRTF tables exist for 44.1 and 48 kHz only.").
Ear geometry + ITD correction stay on (they are rate-independent), so it degrades to a spaced pair with head ITD.

## 5. CPU estimate (VERIFIED on the box: native C, gcc -O2, `reports/bench_sos_box.log`, `bench_sos_rear32_box.log`, `bench_fir_box.log`)

Play filters are the distinct records per bus; lines or taps sharing a record share a filter (VERIFIED `mix_partition`).
In the locked binaural mode the FDN lines are uncoloured, so the filters are the early+direct records per ear.

| setup | filters (both ears) | K | % of one box core @ 48 kHz |
|---|---|---|---|
| ORTF today, one source (29 θ × 3 buses) | 87 | 3 | **4.0 %** (3.2 ns/biquad) |
| Binaural (rear set), default scene, yaw 0 (21 per ear) | 42 | 6 | **3.3 %** (bench 2.7 ns) · 3.75 % at 3.1 ns |
| Binaural, two sources apart (24 per ear) | 48 | 6 | 3.7 % · 4.3 % at 3.1 ns |
| Binaural, small room (25 per ear, the most seen) | 50 | 6 | 3.9 % · 4.5 % at 3.1 ns |
| + diffuse tail IC mixer, 2 FIRs × 513 taps, direct form | — | — | **+1.3 %** (upper bound; the partitioned-FFT path would be cheaper) |
| Binaural worst case (every node on both ears, never seen) | 60+ | 6 | ≥ 5.4 % (+1.3 %) |

Total, locked binaural: about **4.6–5.8 %** of one box core at 48 kHz. ORTF today is 4.0 % without two-source colour,
which it cannot fit. The ns/biquad varied between runs (2.7 today, 3.1 earlier), so both are shown.
wasm is slower than native (ASSUMED 1.5–2×). Render (Python) cost scales the same way; Package 6's speed-up applies.

## 6. Parameters to add (parameters.csv style)

```
key,group,status,what_it_does,range,default_server,default_client,units,provenance,current_ui_location,recommended_tabs,play,render,flags
mic_setup,Mic colour,current,Array preset name (adds binaural),ortf|…|binaural,ortf,ortf,,VERIFIED-code,Mic tab,Mic,Y,Y,binaural locks space/yaw/pattern/C
binaural_preset,Binaural,proposed,Dummy-head HRTF preset,SADIE2_KU100|SADIE2_KEMAR|THK_KU100_FF,SADIE2_KU100,SADIE2_KU100,,MEASURED (SADIE II Apache-2.0 / THK CC BY-SA 3.0 flagged),Mic tab Head selector,Mic,Y,Y,LOCKED 2026-09-30 default; THK shows licence flag
head_yaw_deg,Binaural,proposed,Head yaw (whole head rotates; ears move with it),±180,0,0,deg,proposed,Mic tab + Floor rotate handle,Floor; Mic,Y,Y,0 = facing +Z; + toward +X (K1 convention)
ear_spacing_m,Binaural,proposed,Ear spacing (read-only; from preset SOFA ReceiverPosition),preset,0.18,0.18,m,VERIFIED-file,Mic tab (read-only),Mic,Y,Y,locked; replaces space in binaural
binaural_itd_mode,Binaural,proposed,ITD correction on top of ear geometry,table|woodworth|geometry,table,table,,MEASURED (LF x-corr table),Advanced,Advanced,Y,Y,
binaural_level_ref,Binaural,proposed,1/r² reference point (both ears),head_centre,head_centre,head_centre,,LOCKED 2026-09-30,hidden,—,Y,Y,read-only; level_l == level_r
binaural_tail_mode,Binaural,proposed,FDN tail handling,diffuse_ic,diffuse_ic,diffuse_ic,,LOCKED 2026-09-30 (target MEASURED per head),hidden,—,Y,Y,even/odd split + IC mixer; lines uncoloured
binaural_ic_mixer_taps,Binaural,proposed,IC mixer FIR length,513|257,513,513,taps,VERIFIED (design sweep),hidden,Advanced,Y,Y,latency (N-1)/2 on the tail only
binaural_image_set,Binaural,proposed,Image table in binaural mode (rear images),binaural_rear32,binaural_rear32,binaural_rear32,,LOCKED 2026-09-30 (selection ASSUMED),hidden,—,Y,Y,N=32 kept; 5 rear images n_z=-1
binaural_K,Binaural,proposed,Biquads per HRTF entry,6,6,6,,LOCKED 2026-09-30 (fit sweep VERIFIED),hidden,—,Y,Y,K=3 tables kept in the pack for comparison only
binaural_symmetric,Binaural,proposed,One L/R mirror-averaged table (60 records) for both ears,true,true,true,,LOCKED 2026-09-30,hidden,—,Y,Y,R ear at node n = L record of mirror(n)
binaural_eq,Binaural,proposed,HRTF equalisation,diffuse_field,diffuse_field,diffuse_field,,as shipped (not changed),hidden,—,Y,Y,
binaural_headphones_note,Binaural,proposed,Show "listen on headphones" note,bool,—,true,,UI,Mic tab,Mic,n/a,n/a,client-only
```

Locked (ignored by the server) while binaural: `space`, `diverg`, `toe_half_deg`, `car_omni`, `pattern_*`, `family_*`,
`polar_*`, `yaw_l_deg`, `yaw_c_deg`, `yaw_r_deg`, `link_lr_yaw`, `align_horizontal`, `centre_dz`, `ms_decode`,
`mic_preset_l/c/r`, `preset_owns_pattern`, `mic_hpf_*`, `mic_gain_c` (forced 0), toys.

## 7. Proposed API (the acceptance tests use these names)

- `engine.early_field.MicStand.binaural(cx, cy, cz, head_yaw_deg=0.0, preset="SADIE2_KU100", **ignored)` → stand with
  `binaural=True`, `space = ear_spacing_m`, `mlalr = −90°`, `mralr = +90°`, omni patterns; ignores user space/yaw/pattern.
- `compute_taps(...)` with a binaural stand: rotated ear positions, `az_head_deg` / `el_head_deg` per tap, delays
  with the ITD correction, `level_l == level_r` (D3 default), C zeros.
- `mic_colour.binaural.BinauralColour(preset_id, sr)`: `.measured`, `.notice`, `.record_for(bus, az, el)` (packed record),
  `.all_records()`, `.bank_for(taps, taps_b, n, direct_index)` (live bank dict like `build_live_bank`).
- `compute_taps(..., hadamard_n=32)` with a binaural stand uses the `binaural_rear32` indices (§3.10).
- `render_pipeline.render_binaural_fdn_ir(taps, room, sr, c, length_ms, g, depth, preset=, tail_mode="diffuse_ic")` → (L, R)
  diffuse tail (§3.9). Play: the same even/odd split and M/S FIR pair after the per-bus line sums.
- `app_server.DEFAULTS`: `binaural_preset`, `binaural_tail_mode`, `binaural_level_ref`, `binaural_K`, `binaural_symmetric`,
  `binaural_image_set` with the §6 defaults.

## 8. Tests

**Build acceptance** (`tests/test_binaural_mode_acceptance.py`; all `xfail` now: **22 xfailed**, VERIFIED):
- UI and stand: `binaural` option and headphones note in index.html · C muted (`level_c == press_c == grad_c == 0`) ·
  spacing fixed at the preset value, Space ignored · patterns omni, ear yaw ±90 locked.
- ITD and levels: ITD sign for a left source (`t_R > t_L`) and size within ±30 µs of the table · head yaw rotates the ears
  as one unit · ILD for a left source at 4 kHz > 6 dB via the records, with equal 1/r² levels (44.1 + 48 kHz).
- Filters and bank: all records stable · two-source bank ≤ 64 at head yaw 0/90/180 with rear images ·
  32 / 88.2 / 96 kHz colour off with a notice · direct path gets the HRTF.
- **New (locked):**
  - `test_binaural_locked_defaults`;
  - `test_binaural_image_set_has_rear_images` (32 images, 5 rear, direct index 2);
  - `test_rear_images_lateralised_and_front_back_coloured`;
  - `test_binaural_tail_coherence_matches_head` (1/3-octave bands 125 Hz–8 kHz: max |ΔIC| ≤ 0.15 and RMS ≤ 0.06 against
    the head's target, 4 s tail).
- parameters.csv has the new rows, including `binaural_image_set`, `binaural_level_ref` and `binaural_K`.

**Pack proofs, passing now:** `test_binaural_presets.py` (35) and `test_binaural_locked.py` (26), with the same
tolerances on the reference implementation and the p5 FDN.
Run: `RR_SW=<software> pytest tests/ -rx` → **61 passed, 22 xfailed** (VERIFIED 30 Sep 2026).

## 9. Fit quality (VERIFIED, 100 Hz–16 kHz, vs diffuse-field-EQ 1/6-oct smoothed measured, G60, 48 kHz; 44.1k within ±0.3 dB)

| K | node max error median / p95 / max (dB), 3 presets | node RMS median (dB) | hold-out RMS median (dB, incl. grid) |
|---|---|---|---|
| 3 | 4.3–4.6 / 7.6–8.1 / 9.8–12.3 | 1.1–1.2 | 1.9 |
| 4 | 3.0–3.1 / 5.2–6.0 / 6.8–7.5 | 0.8 | 1.7–1.9 |
| 5 | 2.2–2.5 / 4.1–4.7 / 4.8–7.0 | 0.6 | 1.7–1.8 |
| **6** | **1.4–1.7 / 3.0–3.4 / 4.0–4.4** | **0.4–0.5** | **1.7–1.8** |

Hold-out directions (15° from nodes) are dominated by the **grid** (quantisation alone 1.67–1.84 dB RMS median), not by
K. G86 (86 nodes) would only improve that to 1.58–1.80 dB and needs MAX_IRS > 64. Symmetrising costs ~0.4 dB RMS
median against the per-ear raw data (L/R asymmetry of the raw heads 1.2–1.5 dB RMS median). Lateralisation is not
quantised: ITD is continuous (§3.3); only the spectral cues step between nodes.

## 10. Decisions (LOCKED by Idle, 30 Sep 2026: full text in `DECISIONS_LOCKED_2026-09-30.md`)

| # | decision | locked value | where |
|---|---|---|---|
| D1 | FDN tail | **diffuse**: uncoloured lines, even/odd split, M/S FIR mixer to the head's MEASURED diffuse-field IC | §3.9 |
| D2 | Tables | **one mirror-symmetric table, 60 entries**, both ears | §3.6 |
| D3 | Level reference | **1/r² from the head centre** | §3.4 |
| D4 | Default head | **SADIE2_KU100** (Apache-2.0); THK_KU100_FF stays available with its licence flagged; SADIE2_KEMAR available | §2.1 |
| D5 | Rear images | **added**: `binaural_rear32` (5 rear images, N = 32 kept) | §3.10 |
| D6 | EQ | diffuse-field (as shipped, not changed) | §4, §9 |
| D7 | THK licence | not asked; stays flagged (CC BY-SA 3.0 applied; Zenodo says CC BY 3.0) | `DATA_LICENCES.md` |
| D8 | K | **6** biquads per ear | §3.6, §9 |

Build details that are not decisions (ASSUMED, reversible): the 7-slot selection in `binaural_rear32`, the mixer FIR
length (513, fallback 257), and skipping the C loop in binaural mode.

## 11. Known limits

- Rear coverage is 5 first-order-behind images; second-order rear (n_z = −2) is not in a 32-line Play set.
- The tail mixer assumes the even/odd split is uncorrelated; this was measured on two scenes, not all rooms.
- Nearest-node lookup (no crossfade between nodes): a moving source steps in spectrum every ~15–20°. Crossfading two
  nodes would double filters (ASSUMED still < today's ORTF at K=6).
- No headphone EQ, no head tracking, no individual HRTFs. SADIE is measured at 1.2 m, THK at 3.25 m; neither is
  distance-corrected. Below ~200 Hz the data are LF-extended by the dataset authors (SADIE VERIFIED in SOFA `History`).
