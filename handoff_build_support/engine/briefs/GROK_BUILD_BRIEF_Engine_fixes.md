# GROK BUILD BRIEF: engine fixes (denormals, tail length, Play/Render parity)

- **Source:** read-only analysis of the `software/` snapshot taken from Idle's PC on 2026-09-27 (`live_stereo.c` dated 2026-09-26).
- **Where the fixes were proven:** every fix below was applied to box copies (`work/sw_fix`, `work/sw_fix_same`), rebuilt with zig, and measured with the test pack in `../tests`.
- **What is not touched:** nothing in the live tree was changed.
- **Details:** `../findings/bug_denormal.md`, `../findings/bug_tail_length.md`, `../findings/play_vs_render_parity.md`.
- **Claim tags:** VERIFIED = measured or read in code. ASSUMED = reasoning, not measured.

## Order of work
1. **F1 denormal guard** (C only). Rebuild the wasm. Run the pack: **t09 FAIL→PASS**; t03 must still PASS (goldens unchanged, ASSUMED).
2. **F2 per-line absorption + F3 delays at the Play rate** (C, worklet JS, live_fdn.js, render_pipeline.py, engine/fdn.py). Rebuild the wasm.
   - Flips to PASS: t08, t10, t11, t12 (VERIFIED on `sw_fix`).
   - t03 FAILs on purpose (delays changed). Once everything else is as expected, regenerate the goldens with `python tests/run_all.py --sw <tree> --regen-golden` and record why.
3. **Server clamp:** clamp `diffusion_master` to [−1, 0] (or Dffs to [−0.98, 0]) in `params_from_body` (`app_server.py` 342). Positive Dffs is unstable in the current z⁻¹ loop (VERIFIED natively). The UI can't reach it; only the server can.
4. **F5 same-sample loop solve in Play (recommended).**
   - Flips: t18 FAIL→PASS; t13 FAIL→XFAIL (only the early-field gap remains).
   - Cost: about +0.16–0.27 ms/block (VERIFIED in WASM/node).
   - Before shipping, handle **t14**: the tail becomes 5.8 dB louder, now matching Render, and hot noise peaks at 0.997. Re-check the makeup (`ir_rms_makeup_from_inject`) or give about 3 dB of headroom, then confirm Render with the same change.
   - Optional speed-ups (ASSUMED): skip the matvec when `anyDffs` is 0; f32x4 SIMD matvec.
5. **F4 (optional):** design the air, shelf and peaking coefficients at the Play rate (currently 44.1 kHz designs run at 48 kHz, so corners are shifted ×1.088).
6. **Still-open gaps**, owned elsewhere or later:
   - Play N fixed at 32 (t17).
   - Split the "diffusion" key into the Surfaces Δd layer and the Structure Dffs layer. This is a product lock (t16).
   - Early per-hit cascade in Play (Track A; t13 early XFAIL).
   - Render IR truncated at `ir_length_ms`.

Locks respected:
- The unscaled ±1 Hadamard stays. F2 runs it at g = 1/√N and moves the decay into per-line gains lg_i = 10^(−3·d_i/(sr·T60)).
- Images still excite the FDN, and 1/r² is untouched.
- The air placement is unchanged. The lg gain is frequency-flat loss, not air.
- The two diffusion layers stay separate.

## Key numbers (VERIFIED, box Xeon)

**Silence cost** (ms/block, budget 2.667):

| Build | Current | Fixed | Note |
|---|---|---|---|
| WASM, colour off | 4.03 | 0.56 | |
| WASM, colour on | 4.66 | 1.26 | |
| Native, colour off | 3.7–3.8 | 0.38 | hardware FTZ on the old code: 0.35–0.37 |
| 2 sources + colour (bench page smoke test) | 15.5 | 1.53 | |

**Tail at a 1.8 s dial, std room** (T30 in s):

| Build | 125 Hz → 11 kHz | Late T60 at 9 / 11 kHz |
|---|---|---|
| Current | 1.22 / 2.22 / 3.65 / 5.3 / 7.59 / 9.47 / 17.7 / 21.4 | 22.4 / 25.4 |
| F2+F3 | 1.6–1.94 | 1.8 / 1.81 |

- The 3-room × 3-dial sweep lands within about ±8 % of the dial after the fix (1.5–6× over before).
- Render: current T30 1.75–4.56 s, late about 6.5 s; with F2, 1.57–1.81 s, late 1.8 s.

**Parity:**
- Direct level: −3.35 dB before, 0.00 dB after F3.
- FDN-only null against Render: +0.8 dB before, −47.5 dB after F1–F3+F5.

**Active cost** (1 source + colour / 2 sources + colour, ms/block): current 1.17/1.77, F1–F3 1.25/1.80, +F5 1.45/2.02.

## Acceptance (`tests/run_all.py`)
Done means:
- t01 and t02 PASS. Always rebuild the wasm from `live_stereo.c` with the zig line in its header.
- t08–t12 PASS.
- t13 PASS or XFAIL (early only).
- t14 and t15 PASS.
- t18 PASS if F5 is adopted.
- t03 and t04 PASS against the regenerated goldens.
- t05–t07, t16 and t17 stay PENDING until those features land. They must not FAIL.

Build line (from the `live_stereo.c` header):
`zig cc -target wasm32-freestanding -O3 -msimd128 -nostdlib -ffreestanding -Wl,--no-entry -Wl,--export-memory -Wl,--export=live_stereo -Wl,--max-memory=1073741824 ...`. Use the full export list exactly as in the header.

Remember to bump `WORKLET_VER` (done in the diff: 28 → 29) so browsers reload the worklet.

## Exact diffs
Separate files in this folder: `live_stereo.c.fix.diff` (F1+F2), `live_stereo.F5_same_sample.diff` (F5, on top of the fix), `fdn_worklet.js.fix.diff`, `live_fdn.js.fix.diff`, `render_pipeline.py.fix.diff` (F2 + F3), `fdn.py.fix.diff` (F2 Render). Apply from inside `software/` with `patch -p1 < file.diff` (F5 after the F1+F2 C diff). Timestamps in the headers are box times. Inlined below.

### live_stereo.c.fix.diff
```diff
--- a/engine/live_stereo.c	2026-09-26 15:20:59.000000000 +0100
+++ b/engine/live_stereo.c	2026-09-27 11:40:34.595486328 +0100
@@ -83,6 +83,8 @@
     double sb0b, sb1b, sb2b, sa1b, sa2b;
     double sz1, sz2, sz1e, sz2e, sz1b, sz2b, sz1f, sz2f;
     double pz1, pz2, pz1b, pz2b;
+    /* Per-line absorption for the decay lock: lg = 10^(-3 d / (sr T60)). 1 = off. */
+    double lg, lgB;
     int w;
 } Line;
 
@@ -119,6 +121,7 @@
     int n_irs;
     int direct_index;
     double g, fdn_wet, direct_wet, early_wet, dry_gain, makeup, gain_a, gain_b;
+    double lineT60;
     double micG[3], micPan[3], micPh[3];
     int peakOn[3];
     double pb0[3], pb1[3], pb2[3], pa1[3], pa2[3];
@@ -316,6 +319,19 @@
 LS_EXPORT("live_soft")
 float live_soft(float x) { return (float)soft_limit((double)x); }
 
+/* Denormal guard. WebAssembly has no FTZ/DAZ control, so states that decay
+ * toward zero are handled in code:
+ *  - feed-forward IIR states (air 1-pole, shelf) are flushed below LS_TINY;
+ *  - the FDN loop gets a constant LS_DC (about -360 dBFS) added to its input,
+ *    so recirculating values never fall into the subnormal range.
+ * Both are far below anything audible and cost ~nothing (measured). */
+#define LS_TINY 1.0e-20
+#define LS_DC 1.0e-18
+static inline double ls_flush(double x) {
+    double a = x < 0.0 ? -x : x;
+    return a < LS_TINY ? 0.0 : x;
+}
+
 static int finite_d(double x) {
     if (x != x) return 0;
     if (x > 1.0e30 || x < -1.0e30) return 0;
@@ -468,6 +484,8 @@
             st->bus[b].line[i].delayBT = 64.0;
             st->bus[b].line[i].sb0 = 1.0;
             st->bus[b].line[i].sb0b = 1.0;
+            st->bus[b].line[i].lg = 1.0;
+            st->bus[b].line[i].lgB = 1.0;
         }
     }
 }
@@ -702,6 +720,23 @@
         bus->dirGainB = clampf(rf(&r), -2.0, 2.0);
         bus->anyDffsB = anyB;
     }
+    /* Optional trailing float (blob length 1982): line T60 in seconds.
+     * > 0.05 turns on delay-proportional line absorption so every path through
+     * the loop (Hadamard or the Dffs allpass self-loop) loses 60 dB per T60. */
+    st->lineT60 = rf(&r);
+    for (b = 0; b < 3; b++) {
+        for (i = 0; i < N; i++) {
+            Line *line = &st->bus[b].line[i];
+            if (st->lineT60 > 0.05) {
+                double k = -6.907755278982137 / ((double)st->sr * st->lineT60);
+                line->lg = ls_exp(k * line->delayT);
+                line->lgB = ls_exp(k * line->delayBT);
+            } else {
+                line->lg = 1.0;
+                line->lgB = 1.0;
+            }
+        }
+    }
 }
 
 static void zero_filts(LiveStereo *st) {
@@ -922,6 +957,7 @@
         s2 = b2 * xin - a2 * yi;
         xin = yi;
     }
+    z = ls_flush(z); s1 = ls_flush(s1); s2 = ls_flush(s2);
     if (kind == 3) { line->airZf = z; line->sz1f = s1; line->sz2f = s2; }
     else if (kind == 2) { line->airZb = z; line->sz1b = s1; line->sz2b = s2; }
     else if (kind == 1) { line->airZe = z; line->sz1e = s1; line->sz2e = s2; }
@@ -933,7 +969,7 @@
     double v, yi, nz1, nz2;
     int ax = i % 3;
     double *z1, *z2;
-    v = read_lane(ring, lane, line->w, delay, st->cap);
+    v = (bankB ? line->lgB : line->lg) * read_lane(ring, lane, line->w, delay, st->cap);
     if (!st->peakOn[ax]) return v;
     z1 = bankB ? &line->pz1b : &line->pz1;
     z2 = bankB ? &line->pz2b : &line->pz2;
@@ -1011,10 +1047,10 @@
                 st->eaBlk[b][i][t] = ev;
                 early += ev;
             }
-            if (mix1) st->xinArr[i] = xin;
+            if (mix1) st->xinArr[i] = xin + LS_DC;
             else if (runFdn) {
                 double gi = line->dffs;
-                double mixed = st->g * st->reads[i] + xin;
+                double mixed = st->g * st->reads[i] + xin + LS_DC;
                 double y = -gi * mixed + st->delayed[i];
                 write_lane(st->ring[b][i], line->w, LANE_FDN, (float)(mixed + gi * y));
                 st->yBlk[b][i][t] = y;
@@ -1051,7 +1087,7 @@
             Line *line = &bus->line[i];
             st->delayed[i] = read_peaked(st, line, st->ring[b][i], LANE_FDN, i, 0, line->delay);
             st->reads[i] = st->delayed[i];
-            st->xinArr[i] = tint(line, 0.5 * xA * line->inj, 0);
+            st->xinArr[i] = tint(line, 0.5 * xA * line->inj, 0) + LS_DC;
         }
         if (mixA) diffuse(st, b, 0, st->xinArr, bus->fb, st->yA);
         else {
@@ -1069,7 +1105,7 @@
             Line *line = &bus->line[i];
             st->delayed[i] = read_peaked(st, line, st->ring[b][i], LANE_FDNB, i, 1, line->delayB);
             st->reads[i] = st->delayed[i];
-            st->xinArr[i] = tint(line, 0.5 * xB * line->injB, 3);
+            st->xinArr[i] = tint(line, 0.5 * xB * line->injB, 3) + LS_DC;
         }
         if (mixB) {
             diffuse(st, b, 1, st->xinArr, bus->fbB, st->yB);
@@ -1194,6 +1230,7 @@
     for (i = 0; i < PART; i++) {
         if (in[i] > 1.0e-12f || in[i] < -1.0e-12f) { silent = 0; break; }
     }
+    /* silent partitions are fed as exact zeros (denormal guard). */
     if (silent && f->cold >= f->npart) {
         for (i = 0; i < PART; i++) out[i] = 0;
         return;
@@ -1204,14 +1241,14 @@
     if (npart < 1) npart = 1;
     if (npart > MAX_PART) npart = MAX_PART;
     for (i = 0; i < PART; i++) { g_re[i] = f->prev[i]; g_im[i] = 0; }
-    for (i = 0; i < PART; i++) { g_re[PART + i] = in[i]; g_im[PART + i] = 0; }
+    for (i = 0; i < PART; i++) { g_re[PART + i] = silent ? 0.0f : in[i]; g_im[PART + i] = 0; }
     fft_complex(g_re, g_im, 0);
     pos = f->pos;
     xre = st->fdlRe + ((f - st->filt) * MAX_PART + pos) * FFTN;
     xim = st->fdlIm + ((f - st->filt) * MAX_PART + pos) * FFTN;
     ls_copy(xre, g_re, FFTN * (int)sizeof(float));
     ls_copy(xim, g_im, FFTN * (int)sizeof(float));
-    for (i = 0; i < PART; i++) f->prev[i] = in[i];
+    for (i = 0; i < PART; i++) f->prev[i] = silent ? 0.0f : in[i];
     for (i = 0; i < FFTN; i++) { g_accR[i] = 0; g_accI[i] = 0; }
     base = f->ir * MAX_PART * FFTN;
     hre = st->specRe + base;
```

### live_stereo.F5_same_sample.diff
```diff
--- b_fix/engine/live_stereo.c	2026-09-27 11:40:34.595486328 +0100
+++ c_same/engine/live_stereo.c	2026-09-27 12:02:06.100927961 +0100
@@ -95,6 +95,7 @@
     int dirW, dirWB;
     int anyDffs, anyDffsB;
     double fb[N], fbB[N];
+    double M[N * N], MB[N * N];  /* (I + g diag(dffs) H)^-1, Render's same-sample solve */
 } Bus;
 
 typedef struct Filt {
@@ -553,6 +554,7 @@
 LS_EXPORT("live_out_l") float *live_out_l(LiveStereo *st) { return st ? st->outL : 0; }
 LS_EXPORT("live_out_r") float *live_out_r(LiveStereo *st) { return st ? st->outR : 0; }
 
+static void build_mix(double g, const Line *line, int bankB, double *M);
 static double clampf(double x, double lo, double hi) {
     if (x < lo) return lo;
     if (x > hi) return hi;
@@ -725,6 +727,10 @@
      * the loop (Hadamard or the Dffs allpass self-loop) loses 60 dB per T60. */
     st->lineT60 = rf(&r);
     for (b = 0; b < 3; b++) {
+        build_mix(st->g, st->bus[b].line, 0, st->bus[b].M);
+        build_mix(st->g, st->bus[b].line, 1, st->bus[b].MB);
+    }
+    for (b = 0; b < 3; b++) {
         for (i = 0; i < N; i++) {
             Line *line = &st->bus[b].line[i];
             if (st->lineT60 > 0.05) {
@@ -739,6 +745,28 @@
     }
 }
 
+static void build_mix(double g, const Line *line, int bankB, double *M) {
+    double A[N][2 * N];
+    int r, c, k;
+    for (r = 0; r < N; r++) {
+        double d = bankB ? line[r].dffsB : line[r].dffs;
+        for (c = 0; c < N; c++) {
+            int bits = r & c, par = 0;
+            while (bits) { par ^= bits & 1; bits >>= 1; }
+            A[r][c] = (r == c ? 1.0 : 0.0) + g * d * (par ? -1.0 : 1.0);
+            A[r][N + c] = (r == c) ? 1.0 : 0.0;
+        }
+    }
+    for (c = 0; c < N; c++) {
+        int piv = c; double best = A[c][c] < 0 ? -A[c][c] : A[c][c];
+        for (r = c + 1; r < N; r++) { double v = A[r][c] < 0 ? -A[r][c] : A[r][c]; if (v > best) { best = v; piv = r; } }
+        if (piv != c) for (k = 0; k < 2 * N; k++) { double t = A[c][k]; A[c][k] = A[piv][k]; A[piv][k] = t; }
+        { double inv = 1.0 / A[c][c]; for (k = 0; k < 2 * N; k++) A[c][k] *= inv; }
+        for (r = 0; r < N; r++) if (r != c) { double f = A[r][c]; if (f != 0.0) for (k = 0; k < 2 * N; k++) A[r][k] -= f * A[c][k]; }
+    }
+    for (r = 0; r < N; r++) for (c = 0; c < N; c++) M[r * N + c] = A[r][N + c];
+}
+
 static void zero_filts(LiveStereo *st) {
     int i;
     int n = MAX_FILT * MAX_PART * FFTN;
@@ -985,18 +1013,28 @@
     Bus *bus = &st->bus[b];
     int i;
     double g;
+    const double *M = bankB ? bus->MB : bus->M;
+    double v[N];
+    int j;
+    (void)fb;
     for (i = 0; i < N; i++) {
-        Line *line = &bus->line[i];
-        double gi = bankB ? line->dffsB : line->dffs;
-        double s = xin[i] + fb[i];
-        double y = -gi * s + st->delayed[i];
-        write_lane(st->ring[b][i], line->w, bankB ? LANE_FDNB : LANE_FDN, (float)(s + gi * y));
-        yOut[i] = y;
-        st->reads[i] = y;
+        double gi = bankB ? bus->line[i].dffsB : bus->line[i].dffs;
+        v[i] = st->delayed[i] - gi * xin[i];
+    }
+    for (i = 0; i < N; i++) {
+        double acc = 0.0;
+        for (j = 0; j < N; j++) acc += M[i * N + j] * v[j];
+        yOut[i] = acc;
+        st->reads[i] = acc;
     }
     fwht(st->reads);
     g = st->g;
-    for (i = 0; i < N; i++) fb[i] = g * st->reads[i];
+    for (i = 0; i < N; i++) {
+        Line *line = &bus->line[i];
+        double gi = bankB ? line->dffsB : line->dffs;
+        double s = xin[i] + g * st->reads[i];
+        write_lane(st->ring[b][i], line->w, bankB ? LANE_FDNB : LANE_FDN, (float)(s + gi * yOut[i]));
+    }
 }
 
 static void bus_sample(LiveStereo *st, int b, double x, double xA, double xB, int two, int t) {
```

### fdn_worklet.js.fix.diff
```diff
--- a/static/js/fdn_worklet.js	2026-09-26 08:26:36.000000000 +0100
+++ b/static/js/fdn_worklet.js	2026-09-27 11:42:16.763636055 +0100
@@ -6,7 +6,7 @@
  * This thread has no fetch.
  */
 
-var BLOB_LEN = 1981;
+var BLOB_LEN = 1982;
 var ROUTE_LEN = 230;
 var MAX_AUDIO = 2048;
 var MAX_IR_FLOATS = 64 * 8192;
@@ -76,6 +76,7 @@
     pushSide(a, bus, di);
     pushSide(a, bus && bus.b, di);
   }
+  a.push(num(data.line_t60, 0));
   return a;
 }
 
```

### live_fdn.js.fix.diff
```diff
--- a/static/js/live_fdn.js	2026-09-26 15:20:00.000000000 +0100
+++ b/static/js/live_fdn.js	2026-09-27 11:42:21.143642457 +0100
@@ -15,7 +15,7 @@
   var monoFile = false;
   var colourRev = "";
   var bank = null;
-  var WORKLET_VER = 28;
+  var WORKLET_VER = 29;
   var ROUTE_LEN = 230;
 
   function status(msg) {
@@ -247,6 +247,7 @@
       makeup: params.makeup,
       direct_index: params.direct_index,
       max_delay_ms: params.max_delay_ms,
+      line_t60: params.line_t60 || 0,
       peaking: params.peaking,
       two_sources: !!params.two_sources && !monoFile,
       gain_a: params.gain_a,
```

### render_pipeline.py.fix.diff
```diff
--- a/render_pipeline.py	2026-09-25 14:24:36.000000000 +0100
+++ b/render_pipeline.py	2026-09-27 11:42:16.747636031 +0100
@@ -578,6 +578,7 @@
     apply_mic=False,
     weights=None,
     colour=None,
+    line_t60=0.0,
 ):
     """2011 wet: L / C / R Diffuser Delay loops + Hadamard feedback + Mixer fold.
 
@@ -627,6 +628,7 @@
             n=n_lines,
             dffs=dffs,
             mic_g=mic_g,
+            line_t60=line_t60,
         )
         poly = fdn.process_block_poly(inj)
         if colour is not None and colour.measured and n_t:
@@ -750,6 +752,8 @@
     mic_phase_c: float = 1.0,
     mic_phase_r: float = 1.0,
     colour=None,
+    line_t60: float = 0.0,
+    loop_g=None,
 ):
     weights = capsule_speaker_weights(
         mic_gain_l, mic_gain_c, mic_gain_r,
@@ -776,7 +780,7 @@
         taps, sr, fdn_ms, n_lines=hadamard_n, weights=weights, colour=colour,
     )
     Lf, Rf = render_fdn_ir(
-        taps, room, sr, c, fdn_ms, fdn_g, DEFAULT_DEPTH, delays,
+        taps, room, sr, c, fdn_ms, fdn_g if loop_g is None else loop_g, DEFAULT_DEPTH, delays,
         n_lines=hadamard_n, surfaces=surfaces, humidity=humidity,
         air_lp=air_lp, air_shelf=air_shelf,
         diffusion_master=diffusion_master,
@@ -785,6 +789,7 @@
         apply_mic=False,
         weights=weights,
         colour=colour,
+        line_t60=line_t60,
     )
     n = max(len(Le), len(Lf), len(Ld))
     def _pad(a):
@@ -1010,10 +1015,14 @@
             taps_b, prep_b = taps_for(bx, by, bz)
             delays = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_had)
             g_split = g
+            line_t60 = 0.0
             if decay_lock and float(decay_s) > 0.05:
                 g_split = structure_gain_for_rt60(delays, float(decay_s), sr, n_had) / float(n_had)
                 lim = 0.99 / math.sqrt(float(n_had))
                 g_split = float(max(0.0, min(lim, g_split)))
+                line_t60 = float(decay_s)
+            # Loop runs lossless when line absorption carries the decay; makeup keeps g_split.
+            g_loop = (1.0 / math.sqrt(float(n_had))) if line_t60 > 0.05 else g_split
             weights = capsule_speaker_weights(
                 mic_gain_l, mic_gain_c, mic_gain_r,
                 mic_pan_l, mic_pan_c, mic_pan_r,
@@ -1068,7 +1077,7 @@
 
             def _fdn_stereo(taps_src):
                 left, right = render_fdn_ir(
-                    taps_src, room, sr, c, fdn_ms, g_split, DEFAULT_DEPTH, delays,
+                    taps_src, room, sr, c, fdn_ms, g_loop, DEFAULT_DEPTH, delays,
                     n_lines=n_had, surfaces=surfaces, humidity=humidity,
                     air_lp=air_lp, air_shelf=air_shelf,
                     diffusion_master=diffusion_master,
@@ -1077,6 +1086,7 @@
                     apply_mic=False,
                     weights=weights,
                     colour=mic_colour,
+                    line_t60=line_t60,
                 )
                 return float(fdn_wet) * mk * left, float(fdn_wet) * mk * right
 
@@ -1143,10 +1153,12 @@
         else:
             taps, prep = taps_at(sox, soz)
         delays = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_had)
+        line_t60 = 0.0
         if decay_lock and float(decay_s) > 0.05:
             g = structure_gain_for_rt60(delays, float(decay_s), sr, n_had) / float(n_had)
             lim = 0.99 / math.sqrt(float(n_had))
             g = float(max(0.0, min(lim, g)))
+            line_t60 = float(decay_s)
         ir_L, ir_R = combined_ir(
             taps,
             room,
@@ -1177,6 +1189,8 @@
             mic_pan_l=mic_pan_l, mic_pan_c=mic_pan_c, mic_pan_r=mic_pan_r,
             mic_phase_l=mic_phase_l, mic_phase_c=mic_phase_c, mic_phase_r=mic_phase_r,
             colour=mic_colour,
+            line_t60=line_t60,
+            loop_g=(1.0 / math.sqrt(float(n_had))) if line_t60 > 0.05 else None,
         )
         yL = fft_convolve(dry, ir_L)
         yR = fft_convolve(dry, ir_R)
@@ -1239,10 +1253,12 @@
         )
         taps, last_prep = taps_at(sox_v, soz_v)
         delays = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_had)
+        line_t60 = 0.0
         if decay_lock and float(decay_s) > 0.05:
             g = structure_gain_for_rt60(delays, float(decay_s), sr, n_had) / float(n_had)
             lim = 0.99 / math.sqrt(float(n_had))
             g = float(max(0.0, min(lim, g)))
+            line_t60 = float(decay_s)
         ir_L, ir_R = combined_ir(
             taps,
             room,
@@ -1272,6 +1288,8 @@
             mic_pan_l=mic_pan_l, mic_pan_c=mic_pan_c, mic_pan_r=mic_pan_r,
             mic_phase_l=mic_phase_l, mic_phase_c=mic_phase_c, mic_phase_r=mic_phase_r,
             colour=mic_colour,
+            line_t60=line_t60,
+            loop_g=(1.0 / math.sqrt(float(n_had))) if line_t60 > 0.05 else None,
         )
         end = min(start + frame, n_dry)
         block = np.zeros(frame, dtype=np.float64)
@@ -1405,14 +1423,18 @@
     dff_per_tap = [tap_dff(t.n, surfaces, master=diffusion_master) for t in taps]
     diffusion = diffusion_scale_from_room(room)
     peaking = live_peaking_banks(room, sr, c, DEFAULT_DEPTH)
+    # Line lengths are rounded at the rate Play runs at. Rounding at 44.1 kHz and
+    # reading at 48 kHz leaves fractional delays, and Play's linear-interp read is
+    # then an in-loop low-pass (HF T60 far below the dial).
+    dsr = colour_sr_i if colour_sr_i >= 8000 else int(sr)
     buses = {}
     mean_ms_acc = 0.0
     mean_ms_n = 0
     for ch in ("l", "c", "r"):
-        dly = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_had, channel=ch)
+        dly = fdn_delays_from_taps(taps, sr=dsr, c=c, n=n_had, channel=ch)
         dffs = dffs_from_taps(taps, dff_per_tap, diffusion, n=n_had, channel=ch)
         mic_g = mic_g_from_taps(taps, n_had, ch, sr, res_hz=mic_response_hz)
-        delay_ms = [1000.0 * float(d) / float(sr) for d in dly]
+        delay_ms = [1000.0 * float(d) / float(dsr) for d in dly]
         inject = []
         air_g = []
         shelf = []
@@ -1449,6 +1471,10 @@
         g = structure_gain_for_rt60(dly_mean, decay_s, sr, n_had) / float(n_had)
     lim = 0.99 / math.sqrt(float(n_had))
     g = float(max(0.0, min(lim, g)))
+    # Decay lock: the loop runs lossless (g = 1/√N) and each line carries
+    # 10^(-3 d/(sr T60)) (live_stereo.c line_t60). makeup/decay_out keep g.
+    line_t60 = float(decay_s) if (decay_lock and decay_s > 0.05) else 0.0
+    g_loop = (1.0 / math.sqrt(float(n_had))) if line_t60 > 0.0 else g
     di = direct_line_index(taps, n_had)
     makeup = ir_rms_makeup_from_inject(
         buses["l"]["inject"], buses["c"]["inject"], buses["r"]["inject"],
@@ -1507,8 +1533,8 @@
         )
         dff_b = [tap_dff(t.n, surfaces, master=diffusion_master) for t in taps_b]
         for ch in ("l", "c", "r"):
-            dly_b = fdn_delays_from_taps(taps_b, sr=sr, c=c, n=n_had, channel=ch)
-            delay_ms_b = [1000.0 * float(d) / float(sr) for d in dly_b]
+            dly_b = fdn_delays_from_taps(taps_b, sr=dsr, c=c, n=n_had, channel=ch)
+            delay_ms_b = [1000.0 * float(d) / float(dsr) for d in dly_b]
             inject_b = []
             air_g_b = []
             shelf_b = []
@@ -1549,14 +1575,16 @@
         p.get("sample_rate"), p.get("colour_rev") or "",
     )
     for _ch in ("l", "c", "r"):
-        _attach_loop_mix(buses[_ch], g)
+        _attach_loop_mix(buses[_ch], g_loop)
         _bb = buses[_ch].get("b")
         if isinstance(_bb, dict):
-            _attach_loop_mix(_bb, g)
+            _attach_loop_mix(_bb, g_loop)
     return {
         "ok": True,
         "n": n_had,
-        "g": g,
+        "g": g_loop,
+        "g_decay": g,
+        "line_t60": line_t60,
         "fdn_wet": float(p.get("fdn_wet", 1.0)),
         "direct_wet": float(p.get("direct_wet", 1.0)),
         "early_wet": float(p.get("early_wet", 0.0)),
```

### fdn.py.fix.diff
```diff
--- a/engine/fdn.py	2026-09-25 14:24:14.000000000 +0100
+++ b/engine/fdn.py	2026-09-27 11:42:06.607621197 +0100
@@ -726,6 +726,7 @@
         n: Optional[int] = None,
         dffs: Optional[Sequence[float]] = None,
         mic_g: Optional[Sequence[float]] = None,
+        line_t60: float = 0.0,
     ) -> None:
         n_lines = int(n) if n is not None else len(delays)
         if n_lines < 1 or (n_lines & (n_lines - 1)) != 0:
@@ -734,9 +735,19 @@
             raise ValueError(f"need {n_lines} delays, got {len(delays)}")
         self.n = n_lines
         # Unscaled Hadamard: stable only if g < 1/√N. Structure is Gain/N.
-        lim = 0.99 / math.sqrt(float(self.n))
+        # With line absorption (decay lock) every line loses gain < 1 per
+        # trip, so the loop may run at the lossless g = 1/√N.
+        self.line_t60 = float(line_t60 or 0.0)
+        lim = (1.0 if self.line_t60 > 0.05 else 0.99) / math.sqrt(float(self.n))
         self.g = float(max(0.0, min(lim, g)))
         self.delays = [int(d) for d in delays]
+        # lg_i = 10^(-3 d_i / (sr T60)): delay-proportional absorption (Jot).
+        self._lg = None
+        if self.line_t60 > 0.05:
+            self._lg = np.asarray(
+                [10.0 ** (-3.0 * float(d) / (float(sr) * self.line_t60)) for d in self.delays],
+                dtype=np.float64,
+            )
         self.max_d = max(self.delays) if self.delays else 0
         self.bufs = [np.zeros(d, dtype=np.float64) for d in self.delays]
         self.idx = [0] * self.n
@@ -814,7 +825,7 @@
         Prefers fdn_core.so (C) when N==32; otherwise Python+numpy.
         """
         assert inject.shape[1] == self.n
-        if _FDN_CORE is not None and self.n == 32 and not self._any_dffs and not self._any_mic:
+        if _FDN_CORE is not None and self.n == 32 and not self._any_dffs and not self._any_mic and self._lg is None:
             return self._process_block_c(inject)
         return self._process_block_py(inject)
 
@@ -846,9 +857,12 @@
         any_mic = self._any_mic
         mg = self.mic_g
         mz = self._mic_z
+        lg = self._lg
         for t in range(n_samp):
             for i in range(n):
                 reads[i] = bufs[i][idx[i]]
+            if lg is not None:
+                reads *= lg
             if peaking:
                 for i in range(n):
                     if use_peak[i]:
```

### Server clamp (not in the diffs; suggested, not tested)
```python
# app_server.py params_from_body, line ~342
"diffusion_master": max(-1.0, min(0.0, _f(body.get("diffusion_master"), -0.5))),
```
