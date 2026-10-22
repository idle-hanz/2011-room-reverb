# UAD round 3 progress (updated 19:50 BST)
## Done
- 204 r3 jobs rendered (PC out\). Real excerpts: drums/bass/guitar/vocal/mix (kept on PC).
- UAD harmonic phase map (harm_phase_uad.csv), UAD aliasing M1/M2 (alias_uad_tones.csv).
- Pre linear floor fixed (8192 taps + 20-19k band): Neve drums -27.8 -> -55.6 dB, 610 -25.5 -> -57.9.
- Dynamics fits: nuke (cost 3.51), room_crush v2 GR-dependent release (1.95), glue v2 (1.32, t63 7.90/7.9), natural (23.1, t63 0.896 OK, heavy-GR att90 4 vs 36 ms miss).
- Pre fits: 610 nclip -8.3 dB median held-out vs linear, nclip_emph -10.9 dB. Neve nclip ~0 (wins only at +0 drive: -1.5 dB vocal, -1.7 wetmix).
## Running (box /workspace/uad3)
- fit.py swell; pre_fit flux / emph_flux for both pres.
## Pending
- comp colour fits, prototype aliasing/CPU, real-music nulls, listen clips, report.
- 19:58 eq_fit.json: HP2+HS per preset, max err ~0.65 dB (<=15k). 18k/20k brickwall identical on every UADx unit -> plugin decimator, excluded. LF 31.5/50 Hz pattern is common to la2a/dis/ssl -> probably chain artefact; unit-specific: 1176 extra ~-1.2 dB @20, Fairchild -6.8/-1.75/-1.39/-0.53 @20/31/50/100, LA-2A +0.6 dB @15k.
- colour_fit.py running for 5 presets (poly, btanh, poly_mem, btanh_mem); no-colour costs: natural 13.1, room_crush 9.6, nuke 8.8, swell 14.8, glue 3.0.
- Neve nclip_emph loses on vocal+0 (+2.9 dB worse) -> plain nclip stays Neve front-runner.
- 20:15 KEY: r2 tone-FR "HP -3.4 dB @20 Hz" on LA-2A/Distressor/SSL is a measurement artefact (identical across units; ESS kernel flat, +0.2 dB @20). eq_fit2.py fits HP1+LS+HS complex to ESS kernel h1: natural 0.54 dB/3.4 deg, nuke 0.40/2.4, glue 0.35/2.2, swell 1.20/7.9 (real LF loss -3.2@20), room_crush 1.36/11.9 (h1 GR-coloured). EQ vs h1 nulls on mix: -37.9/-41.7/-43.0/-29.5/-23.3 dB. eq_fit.json = v2; v1 in eq_fit_v1_toneFR.json.
- Neve nclip_flux: held-out median -1.08 dB, worst -0.27 (wins everywhere) -> new Neve front-runner.
- prog3.py (null harness, box+PC via UADROOT) written; numba installed into PC scratch venv.
- 20:58 swell dyn fit done: static rms 0.51 / max 1.10 dB, t63 3.5 ms, rel63 within ~30%.
- colour poly results (cost none->poly): glue 2.98->1.35 (a3 +0.043 out-side, depth d0 0.05 Gs 2 dB), nuke 8.8->1.42 (a2 -0.020 a3 -0.108, d0 0.19 Gs 13.7), room_crush 9.6->2.20 (a2/a3 at bounds -> needs scale), swell 14.8->3.85 (a2 -0.005 a3 +0.077 expansive, const depth). btanh/mem running.
- bench2.c: efficient FIR47 halfband 2x ~ (box loaded) 46 ns/sample/ch up+down; latency 23 samples @48k (0.48 ms), linear phase.
- 20:40 btanh results: glue 2.16 (poly 1.35 better), natural poly 13.06->1.74 (a2 -0.039 a3 -0.128 d0 0.42 Gs 1.3), nuke btanh 1.424 = poly 1.423, room_crush btanh 1.96 (vr -14.1 dB, b -0.25; better than bounded poly 2.20; polyv running), swell btanh 4.83 (poly 3.85 better). Mem families still running.
- 20:45 pre_choice.json = nclip_flux for both (phi_fc at 200 Hz bound -> acts as freq-dependent cubic, not LF transformer).
- REAL MUSIC (PC, fully held-out) pre nulls linear->model: Neve gains -0.14..-3.15 dB on all 10 rows (bass+0 -48.2->-51.4); 610-A gains -7.4..-18.7 dB on all 10 (vocal+0 -25.7->-44.4, drums+0 -18.5->-33.8). real_pre_nulls.csv on PC; pre listen clips written to round3\listen.
- pcbundle.zip (code+fits+kernels, synthetic-derived only) on PC r3\box; real_eval.py there.
- 20:55 synth prog nulls (provisional colour) medians [current | current+EQ | proto+EQ]: natural -26.3|-27.4|-26.5 ; room_crush -13.0|-14.9|-16.8 ; nuke -14.0|-14.0|-21.6 ; swell -12.1|-20.9|-24.3 ; glue -27.8|-40.2|-38.9. Colour itself moves nulls <0.1 dB (harmonics below null floor); judged on harmonic cost instead. GR rms err current->proto: nat .42->.45, rc 1.50->1.06, nuke 1.49->.73, swell .69->.59, glue .11->.11.
- alias_proto done (M1/M2/sweep). Comps: natural 2x -92 (UAD -101), room_crush 2x -94.9 (UAD -68.9), nuke 1x -78.9 / ADAA=2x -90.6 (UAD -90.0, floor = gain path), swell 2x M1 -83.6 = 4x (gain-path, M2<16k -96.5; UAD -105), glue 1x -93.1 (UAD -97.3). Pres badly alias: Neve 4x worst -37 (UAD -25..-86 per row), 610 4x -55.8 (UAD -53). Testing 8x/16x. NOTE sweep metric has a constant -57.3 dB scale offset (double window normalisation); relative comparisons valid.
- 21:10 ALIAS per-row rule (proto <= UAD-10 dB OR < -90 dBFS), both M1 and M2<16k: glue 1x 16/16; nuke ADAA1 16/16 (1x 7/16); natural 2x 16/16 (ADAA M1 14/16); room_crush 2x 16/16 (1x 10/16); swell 2x M2 16/16, M1 14/16 - the two misses are k2/k3 images folded to 21-22 kHz (>20k, decimator transition), unchanged at 4x. Pres: Neve 4x fails 1 row, 8x passes all (worst -55.5 dBFS, >=21 dB below UAD); 610 4x fails 6 rows, 8x passes all (positive margins only below -116 dBFS). alias_pre_os.txt.
- IMD running (imd_proto.py): natural SMPTE proto 0.010-0.041% vs UAD 0.014-0.046% vs current 0.0001%.
- 21:15 IMD (median of top 6 stair steps, % ) uad|current|proto2x: natural SMPTE 2.51|0.90|1.30, CCIF .52|.15|.33; room_crush SMPTE 6.53|.73|5.33, CCIF 1.19|.14|1.49; nuke SMPTE 2.20|1.87|2.73, CCIF .38|.32|.50; swell SMPTE 23.2|.05|12.2 (fc_t2 data), CCIF 10.7|.003|5.3; glue SMPTE 1.30|.98|1.24, CCIF .17|.12|.17. SMPTE 1st sideband dBc uad|cur|proto: nat -53|-98|-48, rc -31|-95|-35, nuke -51|-99|-51, swell -30|-106|-45, glue -80|-104|-88. imd_proto.csv.
- 21:25 REAL MUSIC comps (PC, 5 excerpts x 2 levels, held out) median null dB: current | current+EQ | proto+EQ (shippable) ; proto-vs-current+EQ median/worst/best:
  natural -25.2|-26.7|-26.2 ; -0.46/+3.60/-1.39 (GR rms .34->.47 worse; guitar/vocal a lose 3-3.6 dB)
  room_crush -13.2|-15.6|-16.6 ; -1.77/-0.92/-4.54 (GR rms 1.57->1.10)
  nuke -16.1|-16.1|-24.2 ; -6.58/-4.86/-11.15 (GR 1.54->.71)
  swell -12.6|-22.3|-25.2 ; -2.41/+0.27/-9.62 (GR .67->.41)
  glue -28.1|-40.9|-42.9 ; -0.07/+5.45/-15.85 (GR .14->.10)
  real_comp_nulls.csv on PC. 48 listen clips written (provisional colour; re-render after mem fits).
- 21:30 glue poly_mem cost 0.737 (poly 1.354): a3 +0.477, LP 208 Hz on distortion, d0 0.39 Gs 2.3 -> memory term wins for SSL. room_crush polyv 1.963 = btanh 1.963 (bounds fixed; same optimum). Harmonic match (rows UAD>-80 dBc, median |dB| / |deg|): natural H2 1.7/0.3 H3 7.7/9.9; room_crush H2 3.6/70 (1176 H2 phase drifts with GR - static shaper can't follow) H3 1.8/9.9; nuke H2 2.7/11.5 H3 4.9/68; swell H2 11.8/21 H3 0.9/3.7; glue (poly) H3 1.2/4.9.
- 21:50 mem fits: nuke btanh_mem 1.358 (poly 1.423 kept: ADAA-able, gain marginal); room_crush btanh_mem 1.726 (chosen; b -1.28, LP 592 Hz, d0 .23 Gs 1.35); swell poly_mem 3.664 (chosen, LP 4.78k); glue poly_mem 0.737 (chosen). Neve nclip_emph_flux_mem: held-out median -3.28 dB, worst -0.28 (chosen; mem_m .575 tau 18.9 ms). 610 nclip_emph_flux -11.31 vs flux -11.16 (keep flux). FIX: comp_proto.colour now applies the memory LP (was only in colour_fit). Re-running alias for changed presets.
- 22:00 Neve mem model alias: 4x 8/16, 8x M1 15/16 (one row only 6.8 dB below UAD; worst -41.3 dBFS) M2 16/16. Testing 16x. alias_verdict.py = per-row rule tool.
- BLOOM_RUN found at roadmap\thursday_prompts\BLOOM_RUN_2026-10-19.md (read only). Binding rules checked: Neve ship rule (median >=0.5 dB better, never >0.5 worse), 610 >=6 dB on vocal+wetmix, colour "no worse than current+UAD EQ on any program", shaper order <=3 (5 for 610).
- 22:08 FINAL ALIAS (chosen models, per-row rule, M1 & M2): natural 2x 16/16; room_crush (btanh_mem) 1x 16/16 (-92.2 dBFS; the 592 Hz memory LP removes HF harmonics); nuke ADAA1 16/16; swell (poly_mem) 2x 16/16 (-94.9); glue (poly_mem) ADAA1 16/16 (1x 15/16, -89.9); Neve mem model 16x 16/16 (-54.0) [8x 15/16]; Neve flux model 8x 16/16; 610 8x 16/16.
- 22:20 pre_harm_check.csv (chosen models vs UAD stairs, drive -30..+6): 610-A THD within ~1.2 dB median at 40/100/1k/5k, H2/H3 within 1.3-2.8 dB, phases within 1-13 deg (tube -x^2 + output HPF signature reproduced: th2 37/68/88/90 vs UAD 31/61/87/89). Neve: near clip good (d0 40 Hz THD 1.04 vs 1.20 %, 100 Hz 1.57 vs 1.58 %, 1k 9.3 vs 7.4 %; H3 phase within 3-14 deg); below clip the model lacks the UAD fixed odd floor (~-81 dBFS abs, th3 ~180) -> THD 0.001 vs 0.011 % at 1k d-12; mem term over-distorts LF at d-6 (0.040 vs 0.009 %). Floor term not built (inaudible ~-60 dB rel on a tail).
- 22:30 synth binding-rule check (rule_check.py, synth_nulls_final.csv): colour on/off moves nulls only -0.23..+0.40 dB (natural +-0.03, nuke <=+0.12, glue <=+0.02, room_crush <=+0.34, swell <=+0.40). proto+EQ vs current+UAD-FR median: natural +0.36 (6/12 worse, tail_a +5.6, from dynamics), room_crush -0.89 (tail_a +3.7 from EQ), nuke -6.80 (0/12 worse), swell -3.29 (tail_a +9.3 from EQ), glue +1.07 (8/12 worse, dynamics; range -48.0..-30.4 breaks -35..-43). -> refitting EQ for room_crush/swell with more sections.
- 22:40 EQ v3 (HP2+2PK+LS+HS, eq_fit3.py) adopted for room_crush (0.80 dB/5.8 deg; tail_a EQ-vs-UAD-kernel null -16.9 -> -25.0) and natural (0.44/3.3; -30.1 -> -34.6). Swell keeps v2 (v3 worse on tail). eq_fit_v2.json = backup. Re-running synth nulls.
- 22:50 CPU (box Xeon, gcc -O2, load ~4.7, ns/sample/ch | us per 128-sample stereo block): comp hybrid 1x full (det+poly3+DC+3 biquads) 35 | 9.1; comp 2x FIR47 51 | 13.1; poly3 alone 6.6; 2x FIR47 up+down 21 | 5.3; pre nclip 1x 43 | 11; pre 8x FIR47 cascade + nclip 417 | 107 (filters alone 149 | 38). Latency: 2x = 23 samples (0.48 ms), 8x cascade ~40 samples (0.84 ms), linear phase (pure delay).
- 22:55 synth rule check with EQ v3 (synth_nulls_final2.csv): room_crush now median -1.23, worst +0.64 (drums_a); nuke -6.80 worst -3.70; swell -3.29 but tail_a +9.3 / drums_a +4.0 come from the fixed EQ (dyn-only vs current, both with UAD kernel: worst -0.33); natural +0.33 (dynamics); glue +1.07 (dynamics, hot rows 4-7 dB worse).
- 23:05 FINAL REAL (PC, final choices, EQ v3, swell fitted dyn; real_comp_nulls.csv / real_pre_nulls.csv; *_prov.csv = earlier run). Medians current|current+EQ|current+UADkernel|proto+EQ ; proto+EQ minus current+UADkernel med/worst:
  natural -25.2|-26.7|-26.4|-26.3 ; -0.74/+4.55 (guitar_a; from dynamics, dyn-only worst +4.15)
  room_crush -13.2|-15.0|-15.3|-16.7 ; -2.05/-0.46 (better on all 10)
  nuke -16.1|-16.1|-16.1|-24.2 ; -6.58/-4.83 (better on all 10)
  swell -12.6|-22.3|-22.9|-25.2 ; -1.70/+1.58 (drums_a)
  glue -28.1|-40.9|-40.1|-43.1 ; -2.04/+5.38 (vocal_b; dynamics)
  colour on/off on real: -0.52..+0.40 dB. GR rms current->proto: nat .34->.47, rc 1.57->1.10, nuke 1.54->.71, swell .67->.41, glue .14->.10.
  Neve (mem model) gains vs linear on all 10: median -1.64, worst -0.12, best -12.59 (vocal+0 -38.2 -> -50.8). 610-A median -11.79, worst -7.38. 48 listen clips re-rendered.
- 23:20 Report written: roadmap\bloom\UAD_ROUND3_2026-10-19.md; deliverables in round3\ (data, scripts, bench, listen 48 wav). DONE.
