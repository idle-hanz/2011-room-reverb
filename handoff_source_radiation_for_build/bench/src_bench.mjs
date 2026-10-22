// Box micro-benchmark (Node, JS JIT ~ AudioWorklet JS path). Same kernel as src_bench.c, Float32Array SoA.
const BLK = 128;
function bank(n) {
  const f = () => new Float32Array(n);
  const B = { g: f(), b0: f(), b1: f(), b2: f(), a1: f(), a2: f(), pg: f(), pm: f(), z1: f(), z2: f(), p1: f(), p2: f() };
  for (let i = 0; i < n; i++) { coef(B, i, Math.cos(i * 0.1), Math.sin(i * 0.1)); }
  return B;
}
function coef(B, i, cx, cz) {
  const lo = -4.6, hi = -11, f0 = 1800, S = 1, p = 0.6, q = 0.14, plo = 4, dip = 0.48, lphz = 555, fs = 48000;
  const u = 0.5 * (1 - cx), back = 1 - q * u ** 8, A = Math.max(0, 1 - 0.2 * cz);
  const khi = A * u ** p * back, klo = A * ((1 - dip) * u ** plo * back + dip * 4 * u * (1 - u));
  const Ag = 10 ** (khi * hi / 40), w0 = 2 * Math.PI * f0 / fs, cw = Math.cos(w0), sw = Math.sin(w0);
  const al = sw / 2 * Math.sqrt(Math.max((Ag + 1 / Ag) * (1 / S - 1) + 2, 1e-9)), sa = 2 * Math.sqrt(Ag) * al;
  const a0 = (Ag + 1) - (Ag - 1) * cw + sa;
  B.b0[i] = Ag * ((Ag + 1) + (Ag - 1) * cw + sa) / a0; B.b1[i] = -2 * Ag * ((Ag - 1) + (Ag + 1) * cw) / a0;
  B.b2[i] = Ag * ((Ag + 1) + (Ag - 1) * cw - sa) / a0; B.a1[i] = 2 * ((Ag - 1) - (Ag + 1) * cw) / a0;
  B.a2[i] = ((Ag + 1) - (Ag - 1) * cw - sa) / a0; B.g[i] = 10 ** (klo * lo / 20);
  const fc = lphz / Math.max(khi, 1e-6); B.pg[i] = fc < 0.45 * fs ? 1 - Math.exp(-2 * Math.PI * fc / fs) : 0; B.pm[i] = 0.99;
}
function process(B, n, inp, out) {
  const { g, b0, b1, b2, a1, a2, pg, pm, z1, z2, p1, p2 } = B;
  for (let i = 0; i < n; i++) {
    let Z1 = z1[i], Z2 = z2[i], P1 = p1[i], P2 = p2[i];
    const G = g[i], B0 = b0[i], B1 = b1[i], B2 = b2[i], A1 = a1[i], A2 = a2[i], PG = pg[i], PM = pm[i];
    const off = i * BLK;
    for (let s = 0; s < BLK; s++) {
      const v = G * inp[off + s];
      const o = B0 * v + Z1;
      Z1 = B1 * v - A1 * o + Z2; Z2 = B2 * v - A2 * o;
      P1 += PG * (o - P1); P2 += PG * (P1 - P2);
      out[off + s] = o + PM * (P2 - o);
    }
    z1[i] = Z1; z2[i] = Z2; p1[i] = P1; p2[i] = P2;
  }
}
console.log("Node " + process.version + " box benchmark, per 128-sample block, lines = 3*N");
console.log("N_images,lines,static_us,coef_recompute_us(all lines),x4_multipoint_us");
for (const N of [32, 64, 128]) {
  const n = 3 * N, reps = 20000;
  const B = bank(n), inp = new Float32Array(n * BLK).map(() => (Math.random() - 0.5) * 1e-3), out = new Float32Array(n * BLK);
  for (let r = 0; r < 1000; r++) process(B, n, inp, out);
  let t0 = performance.now(); for (let r = 0; r < reps; r++) process(B, n, inp, out); let t1 = performance.now();
  for (let r = 0; r < reps / 10; r++) for (let i = 0; i < n; i++) coef(B, i, Math.cos(i * 0.1 + r), Math.sin(i * 0.1)); let t2 = performance.now();
  const B4 = bank(4 * n), in4 = new Float32Array(4 * n * BLK).map(() => (Math.random() - 0.5) * 1e-3), out4 = new Float32Array(4 * n * BLK);
  for (let r = 0; r < 500; r++) process(B4, 4 * n, in4, out4);
  let t3 = performance.now(); for (let r = 0; r < reps / 4; r++) process(B4, 4 * n, in4, out4); let t4 = performance.now();
  console.log(`${N},${n},${((t1 - t0) / reps * 1000).toFixed(2)},${((t2 - t1) / (reps / 10) * 1000).toFixed(2)},${((t4 - t3) / (reps / 4) * 1000).toFixed(2)}`);
}
