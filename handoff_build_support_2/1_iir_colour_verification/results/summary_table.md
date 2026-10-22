| Mic | SOS vs model max (48k/44.1k, 1-180 deg) | SOS vs MEASURED max / RMS (48k) | old FIR vs MEASURED max / RMS (48k) | model vs MEASURED max / RMS | SOS vs FIR max (48k) | HPF on: SOS <100 Hz / FIR <100 Hz (48k) | preset hash | verdict |
|---|---|---|---|---|---|---|---|---|
| AKGC414Bidirect | 0.19 / 0.19 | 39.26 / 6.76 | 39.30 / 6.76 | 39.30 / 6.76 | 0.24 | 0.19 / 26.3 | ok | PASS |
| AKGC414Cardioid | 0.19 / 0.20 | 33.18 / 3.84 | 33.21 / 3.85 | 33.21 / 3.85 | 0.19 | 0.19 / 20.3 | ok | PASS |
| AKGC414Hyper | 0.09 / 0.09 | 31.45 / 3.76 | 31.43 / 3.76 | 31.43 / 3.76 | 0.14 | 0.09 / 20.8 | ok | PASS |
| AKGC414Omni | 0.06 / 0.41 | 25.01 / 2.97 | 25.06 / 2.97 | 25.06 / 2.97 | 0.06 | 0.01 / 19.0 | ok | PASS |
| Coles4038 | 0.15 / 0.15 | 30.62 / 5.99 | 30.60 / 5.99 | 30.60 / 5.99 | 0.15 | no HPF | ok | PASS |
| DPA4006 | 0.09 / 0.53 | 4.76 / 0.90 | 4.84 / 0.90 | 4.84 / 0.90 | 0.09 | no HPF | ok | PASS |
| ElectroVoiceRE20 | 0.11 / 0.15 | 28.26 / 3.58 | 28.25 / 3.58 | 28.26 / 3.58 | 0.21 | no HPF | ok | PASS |
| NeumannU87AiBidirect | 0.06 / 0.07 | 28.52 / 5.60 | 28.52 / 5.60 | 28.52 / 5.60 | 0.13 | 0.06 / 20.5 | ok | PASS |
| NeumannU87AiCardioid | 0.08 / 0.09 | 27.33 / 3.70 | 27.35 / 3.71 | 27.35 / 3.70 | 0.14 | 0.04 / 18.0 | ok | PASS |
| NeumannU87AiOmni | 0.46 / 0.69 | 22.14 / 2.53 | 22.28 / 2.53 | 22.28 / 2.53 | 0.36 | 0.01 / 17.3 | ok | FAIL |
| RodeNT2ABidirect | 0.09 / 0.09 | 24.77 / 4.20 | 24.78 / 4.20 | 24.78 / 4.20 | 0.12 | 0.09 / 15.5 | ok | PASS |
| RodeNT2ACardioid | 0.19 / 0.19 | 33.84 / 3.83 | 33.86 / 3.84 | 33.86 / 3.84 | 0.19 | 0.19 / 15.5 | ok | PASS |
| RodeNT2AOmni | 0.17 / 0.62 | 15.59 / 1.83 | 15.65 / 1.83 | 15.65 / 1.83 | 0.16 | 0.01 / 15.5 | ok | FAIL |
| RoyerR121 | 0.22 / 0.22 | 38.70 / 9.13 | 38.70 / 9.13 | 38.70 / 9.13 | 0.25 | no HPF | ok | PASS |
| SchoepsCMC5UBidirect | 0.06 / 0.07 | 35.18 / 3.94 | 35.18 / 3.94 | 35.18 / 3.94 | 0.12 | no HPF | ok | PASS |
| SchoepsCMC5UCardioid | 0.18 / 0.17 | 24.91 / 3.93 | 24.93 / 3.92 | 24.93 / 3.92 | 0.17 | no HPF | ok | PASS |
| SchoepsCMC5UOmni | 0.06 / 0.55 | 13.13 / 1.23 | 13.13 / 1.23 | 13.13 / 1.23 | 0.05 | no HPF | ok | PASS |
| SennheiserMD441 | 0.10 / 0.10 | 33.47 / 4.16 | 33.50 / 4.17 | 33.49 / 4.17 | 0.25 | no HPF | ok | PASS |
| ShureSM57 | 0.37 / 0.38 | 19.62 / 3.31 | 19.65 / 3.32 | 19.65 / 3.32 | 0.25 | no HPF | ok | PASS |
| ShureSM58 | 0.10 / 0.10 | 21.51 / 4.45 | 21.53 / 4.45 | 21.53 / 4.45 | 0.26 | no HPF | ok | PASS |

Worst pole radius over all mics/angles/rates/HPF: 0.998927 at ['RodeNT2ACardioid', 96000, 12, 'hpf_off']
Worst float32-coefficient rounding effect: 0.0425 dB (RodeNT2ACardioid)
Render cost, 1 s mono buffer, one SOS entry: python apply_sos 55 ms vs FFT FIR 1.5 ms vs scipy sosfilt 0.55 ms
