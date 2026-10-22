# Shared FDN with decorrelated outputs: literature notes (2026-10-02)

Status: these are notes from web searches and abstracts, plus what I already knew about each paper.
I have not read the full papers here. Treat each "key point" as ASSUMED until someone checks it against the PDF.
Where a point is backed by a measurement made in this folder, it says VERIFIED (here).

## 1. The classic structure: one network, several outputs
- **Stautner & Puckette 1982**, "Designing multi-channel reverberators", Computer Music Journal 6(1).
  - The first FDN with a unitary (Hadamard-like) feedback matrix.
  - Several output channels are taken from one network.
- **Jot & Chaigne 1991**, "Digital delay networks for designing artificial reverberators", AES 90th Convention, preprint 3030.
  - Introduces absorptive filters per line, which give frequency-dependent T60, plus a tone corrector.
  - Multichannel output: each output is a different linear combination of the line outputs, i.e. an output vector c_k per channel.
  - With an orthogonal set of output vectors and a well-mixed network, the outputs are roughly mutually incoherent. **This is the standard way to get L/R from ONE network.**
  - Relevance: this is exactly Idle's idea. Today's per-mic networks are the "N independent reverbs" design. Jot's approach is the "one reverb, many taps" design.
- **Jot 1992 / 1997** (IRCAM Spat, "Efficient models for reverberation and distance rendering...", ICMC 1997):
  - in Spat, one late-reverb FDN feeds all output channels;
  - per-channel decorrelation comes from the output matrix;
  - early reflections are rendered per channel.
  - That is the same split we keep here: early lanes per mic, shared tail.

## 2. How decorrelation arises in an FDN
- **Schlecht, Fagerström & Välimäki 2023**, "Decorrelation in Feedback Delay Networks", IEEE/ACM TASLP 31, 3478–3487.
  - Output coherence is decided by the feedforward part (input gains b, output gains c, direct paths). The recursive part does not add correlation.
  - Output delays on their own do not decorrelate two outputs of one FDN. Different output *mixing* (different c vectors), combined with delays, does.
  - More lines help.
  - Filter feedback matrices (velvet / dense scattering) decorrelate best.
  - **Relevance:** our L/R/C taps read the SAME 32 line outputs. They differ only by small per-line delay offsets (d_mic,i − d_C,i) and, in the candidate, a hashed jitter of up to 0.3 ms. Because the offset differs line by line, the tap set is a frequency-dependent mixing, not one common output delay.
    - Measured: without jitter, L/R coherence is too high above 2 kHz (VERIFIED here: m1 at 4 kHz is 0.80 vs 0.46 today, default room).
    - Measured: with 0.3 ms jitter it lands near today (VERIFIED here, see the report).
- **Fagerström, Alary, Schlecht & Välimäki 2020**, "Velvet-noise feedback delay network", DAFx-20.
  - Sparse velvet filters in the feedback matrix.
  - A future option for more decorrelation, but it breaks the "unscaled ±1 Hadamard" lock. **Not proposed.**
- **Schlecht & Habets 2017**, "Feedback delay networks: echo density and mixing time", IEEE/ACM TASLP 25(2).
  - Mixing time depends on N, the delays and the matrix.
  - A shared 32-line network has the same per-network mixing as each of today's networks, because N, the matrix and the delays are unchanged.

## 3. Directional / multichannel FDNs
- **Alary, Politis, Schlecht & Välimäki 2019**, "Directional feedback delay network", JAES 67(10), 752–762.
  - The lines are Ambisonic channels and the matrix mixes them per direction.
  - Gives a directional, anisotropic tail from ONE network, decoded to any layout.
  - Supports "one network, many outputs" for spatial audio. It is a much bigger change than our proposal.

## 4. Controlling interchannel coherence (binaural and stereo)
- **Menzer & Faller 2009**, "Binaural reverberation using a modified Jot reverberator with frequency-dependent interaural coherence matching", AES 126th Convention, paper 7765.
  - One Jot FDN gives two output weight vectors, chosen to be nearly incoherent.
  - Coherence-matching filters outside the loop then mix the two outputs to the target frequency-dependent IACC of a head.
  - **Relevance:** this is how our binaural path already works. ic_collect sums the even lines of bus L into A and the odd lines of bus R into B, then ic_apply runs the M/S IC FIRs (VERIFIED in live_stereo.c).
  - A shared FDN keeps that structure. A and B still come from disjoint line subsets, just of one network.
  - Measured: big-room binaural coherence matches today within 0.02 (VERIFIED here).
- **Menzer, Faller & Lissek 2011**, "Obtaining binaural room impulse responses from B-format impulse responses using frequency-dependent coherence matching", IEEE TASLP 19(2), 396–405. Same matching idea, applied to measured responses.
- **Habets & Gannot 2007**, "Generating sensor signals in isotropic noise fields", JASA 122(6), 3464–3470.
  - Mixes M independent signals per frequency with a Cholesky / eigen factor of the target coherence matrix.
  - This gives an exact target spatial coherence (e.g. sinc(kd) for omnis, or a mic-pattern model).
- **Habets, Cohen & Gannot 2008**, "Generating nonstationary multisensor signals under a spatial coherence constraint", JASA 124(5), 2911–2917.
- **Mirabilii, Schlecht & Habets 2021**, "Generating coherence-constrained multisensor signals using balanced mixing and spectrally smooth filters", JASA 149(3), 1425–1433.
  - The Cholesky mix colours the outputs. Balanced mixing (symmetric square root) plus smoothing avoids that.
  - **Relevance:** this is the principled upgrade path if the hashed jitter is not good enough. Take 3 near-incoherent shared-FDN outputs (L/C/R) and apply a 3×3 per-band balanced mix to the ORTF diffuse-field coherence target.
  - It would sit outside the loop, after the line taps and before mic colour, like the binaural IC stage.
- **Elko 2001**, "Spatial coherence functions for differential microphones in isotropic noise fields", in *Microphone Arrays* (Brandstein & Ward, eds.), Springer.
  - Gives closed-form diffuse-field coherence for cardioids and other patterns, spaced and angled.
  - That is the physical target for an ORTF pair (17 cm, ±55°).
  - Today's per-mic networks reach their coherence "by accident of geometry": the delay offsets between mics and the separate loops. They do not target Elko's curve.

## 5. Takeaways for 2011 Room Reverb
1. One FDN with per-output taps is the textbook design (Stautner-Puckette, Jot, Spat). Per-output networks are the unusual choice. (ASSUMED from the literature; consistent with what was measured here.)
2. Output decorrelation must come from differences in output mixing. Delays alone are not enough (Schlecht 2023). Our taps differ per line, which counts as mixing. Jitter adds more. (Literature: ASSUMED. Our numbers: VERIFIED here.)
3. Frequency-dependent coherence is best set outside the loop with matching filters (Menzer-Faller; Habets; Mirabilii). Binaural already does this. ORTF/AB could get the same treatment later.
4. Exact mirror symmetry plus a perfectly symmetric scene forces L == R for ANY deterministic, mirror-equivariant engine. This is logic, not literature. Today's engine shows it (VERIFIED here: hall_lock40, L−R = 0.0). A fixed L/R decorrelation pattern fixes it but gives up bit-exact mirroring.
