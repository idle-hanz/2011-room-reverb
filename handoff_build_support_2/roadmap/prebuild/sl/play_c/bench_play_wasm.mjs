// SL3 box proof in wasm (the real Play engine, built like static/wasm/live_stereo.wasm: freestanding, SIMD).
// usage: node bench_play_wasm.mjs lsf_A.wasm lsf_B.wasm bench_inputs.json [out.json]
import fs from "node:fs";
import crypto from "node:crypto";
const [wa, wb, inp, out] = process.argv.slice(2);
const I = JSON.parse(fs.readFileSync(inp, "utf8"));
const SR = 48000, PART = 128;
async function engine(path) {
  const { instance } = await WebAssembly.instantiate(fs.readFileSync(path), {});
  const api = instance.exports;
  const heap = api.memory.buffer.byteLength, need = api.live_bytes(SR);
  api.memory.grow(Math.ceil(need / 65536));
  const st = api.live_bind(heap, need, SR);
  const buf = api.memory.buffer;
  new Float32Array(buf, api.live_blob_ptr(st), I.blob.length).set(I.blob);
  api.live_load_room(st, I.blob.length);
  return { api, st };
}
function loadSurf(e, secs) {
  new Float64Array(e.api.memory.buffer, e.api.live_surf_ptr(e.st), secs.length).set(secs);
  return e.api.live_load_surf(e.st, 1);
}
function run(e, x) {
  const { api, st } = e, buf = api.memory.buffer;
  const inL = new Float32Array(buf, api.live_in_l(st), PART), inR = new Float32Array(buf, api.live_in_r(st), PART);
  const oL = new Float32Array(buf, api.live_out_l(st), PART), oR = new Float32Array(buf, api.live_out_r(st), PART);
  const L = new Float32Array(x.length);
  for (let a = 0; a < x.length; a += PART) {
    inL.set(x.subarray(a, a + PART)); inR.set(x.subarray(a, a + PART));
    api.live_stereo(st, inL.byteOffset, inR.byteOffset, oL.byteOffset, oR.byteOffset, PART);
    L.set(oL, a);
  }
  return L;
}
const h = (a) => crypto.createHash("sha256").update(Buffer.from(a.buffer)).digest("hex");
const imp = new Float32Array(SR * 2); imp[0] = 1;
const A = await engine(wa), Boff = await engine(wb), Bon = await engine(wb), Bid = await engine(wb);
const res = {};
res.surf_load_ok = loadSurf(Bon, I.secs);
const ident = new Array(I.secs.length).fill(0); for (let j = 0; j < ident.length; j += 5) ident[j] = 1;
res.identity_load_ok = loadSurf(Bid, ident);
const yA = run(A, imp), yB = run(Boff, imp), yI = run(Bid, imp), yS = run(Bon, imp);
res.flat_off_bit_exact = h(yA) === h(yB);
res.identity_bit_exact = h(yA) === h(yI);
res.designed_finite = yS.every(Number.isFinite);
let seed = 7; const rnd = () => ((seed = (seed * 1103515245 + 12345) >>> 0) / 4294967296 - 0.5) * 0.2;
const noise = new Float32Array(SR * 4).map(rnd);
const T = { A: [], B_off: [], B_on: [] }, E = { A, B_off: Boff, B_on: Bon };
for (let r = 0; r < 9; r++) for (const k of Object.keys(E)) {
  const t = process.hrtime.bigint(); run(E[k], noise);
  T[k].push(Number(process.hrtime.bigint() - t) / 1e6 / (noise.length / PART));
}
const med = (v) => { const s = [...v].sort((a, b) => a - b); return +s[s.length >> 1].toFixed(4); };
res.ms_per_block_median = { A: med(T.A), B_off: med(T.B_off), B_on: med(T.B_on) };
res.delta_on_vs_A_ms = +(res.ms_per_block_median.B_on - res.ms_per_block_median.A).toFixed(4);
res.delta_off_vs_A_ms = +(res.ms_per_block_median.B_off - res.ms_per_block_median.A).toFixed(4);
res.note = `node ${process.version}, zig cc wasm32-freestanding -O2 -msimd128 (pristine build is ${fs.statSync(wa).size} B vs the app's 221793 B); box CPU, indicative only`;
console.log(JSON.stringify(res, null, 1));
if (out) fs.writeFileSync(out, JSON.stringify(res, null, 1));
