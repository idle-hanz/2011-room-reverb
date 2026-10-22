// build_support_2 verify_1600: copy of s7 bench_blocks.js; msgFrom now forwards surf_cascade and shared_tail like Build's 1600 wasm_run.js.
// Drives the REAL Play path (static/js/fdn_worklet.js + static/wasm/live_stereo.wasm) of a software tree in Node.
// Usage: node wasm_run.js <software_dir> <params.json> '<overrides json>' <mode> [args]
//   ir <seconds> <out.f32> | noise <burst_s> <total_s> <out.f32> | bench <burst_s> <total_s> [out.json] | blob <out.f32>
//   switch <burst_s> <total_s> <out.f32> '<[[t_s, {overrides}], ...]>'  (build_support_2: re-sends params at t_s, like a fader move)
// Env WASM=<path> overrides the wasm file. Mirrors live_fdn.js pushParams/takeColour.
const fs = require('fs'), path = require('path');
const [SW, PJ, OV, MODE, ...ARGS] = process.argv.slice(2);
const SR = 48000, BLK = 128;
const reg = {};
class AWP { constructor() { this.port = { postMessage: (m) => { (global.__errs = global.__errs || []).push(m); }, onmessage: null }; } }
new Function('AudioWorkletProcessor', 'registerProcessor', 'sampleRate', fs.readFileSync(path.join(SW, 'static/js/fdn_worklet.js'), 'utf8'))(AWP, (n, c) => { reg[n] = c; }, SR);
const wasmBytes = fs.readFileSync(process.env.WASM || path.join(SW, 'static/wasm/live_stereo.wasm'));
function decodeIr(s) { const b = Buffer.from(s, 'base64'); return new Float32Array(b.buffer.slice(b.byteOffset, b.byteOffset + b.length)); }
function at(v, d) { return (v == null || !isFinite(Number(v))) ? d : (Number(v) | 0); }
function buildRoute(b) { const r = new Int32Array(326); const n = ['l', 'c', 'r']; let o = 0;
  for (let c = 0; c < 3; c++) { const row = b.fdn && b.fdn[n[c]]; for (let i = 0; i < 32; i++) r[o++] = at(row && row[i], -1); }
  for (let c = 0; c < 2; c++) { const row = b.early && b.early[c ? 'r' : 'l']; for (let i = 0; i < 32; i++) r[o++] = at(row && row[i], -2); }
  for (let c = 0; c < 2; c++) { const row = b.early_b && b.early_b[c ? 'r' : 'l']; for (let i = 0; i < 32; i++) r[o++] = at(row && row[i], -2); }
  for (let c = 0; c < 3; c++) r[o++] = at(b.direct && b.direct[n[c]], -1); for (let c = 0; c < 3; c++) r[o++] = at(b.direct_b && b.direct_b[n[c]], -1);
  // MIRROR brief (1 Oct): optional B-side FDN map at 230..325; falls back to A's map; worklets with ROUTE_LEN 230 ignore it.
  for (let c = 0; c < 3; c++) { const row = (b.fdn_b && b.fdn_b[n[c]]) || (b.fdn && b.fdn[n[c]]); for (let i = 0; i < 32; i++) r[o++] = at(row && row[i], -1); } return r; }
function msgFrom(p, over) {
  over = Object.assign({}, over || {});
  const wantColour = over.colour_on !== false; delete over.colour_on;
  const c = p.colour || {}; const on = !!(c.on && c.sr === SR && wantColour);
  const m = { type: 'params', g: p.g, fdn_wet: p.fdn_wet, direct_wet: p.direct_wet, early_wet: p.early_wet, dry_gain: p.dry_gain,
    mic_gain_l: p.mic_gain_l, mic_gain_c: p.mic_gain_c, mic_gain_r: p.mic_gain_r, mic_pan_l: p.mic_pan_l, mic_pan_c: p.mic_pan_c, mic_pan_r: p.mic_pan_r,
    mic_phase_l: p.mic_phase_l, mic_phase_c: p.mic_phase_c, mic_phase_r: p.mic_phase_r, makeup: p.makeup, direct_index: p.direct_index, max_delay_ms: p.max_delay_ms,
    line_t60: p.line_t60 || 0,
    peaking: p.peaking, two_sources: !!p.two_sources, gain_a: p.gain_a, gain_b: p.gain_b, buses: p.buses, colour_on: on, mono: false };
  if (on) { const irs = c.irs.map(decodeIr); let n = 0; irs.forEach(a => n += a.length); const packed = new Float32Array(n); const lens = new Int32Array(irs.length); let o = 0;
    irs.forEach((a, i) => { packed.set(a, o); lens[i] = a.length; o += a.length; }); m.route = buildRoute(c); m.irs = packed; m.ir_len = lens; m.n_irs = irs.length; }
  // Binaural (1 Oct): pass the diffuse-tail IC mixer FIRs like live_fdn.js; worklets without live_load_ic ignore them.
  if (p.ic_hp && p.ic_hm) { m.ic_hp = Float32Array.from(p.ic_hp); m.ic_hm = Float32Array.from(p.ic_hm); }
  if (p.src_rad && p.src_rad.length) m.src_rad = p.src_rad;
  if (p.early_gate && p.early_gate.length) m.early_gate = p.early_gate;
  if (p.surf_cascade && p.surf_cascade.length) m.surf_cascade = p.surf_cascade;
  if (p.hadamard_n != null) m.hadamard_n = p.hadamard_n;
  else if (p.n != null) m.hadamard_n = p.n;
  if (p.loop_semantics != null) m.loop_semantics = p.loop_semantics;
  if (p.solo_mute) m.solo_mute = p.solo_mute;
  m.shared_tail = !!p.shared_tail;
  return Object.assign(m, over);
}
(async () => {
  const P = JSON.parse(fs.readFileSync(PJ)); const over = JSON.parse(OV || '{}');
  global.__errs = [];
  const pr = new reg['room-fdn']({ processorOptions: { wasm: wasmBytes } });
  for (let i = 0; i < 100 && !pr.ready; i++) await new Promise(r => setTimeout(r, 20));
  if (!pr.ready) throw new Error('wasm not ready ' + JSON.stringify(global.__errs));
  pr.port.onmessage({ data: msgFrom(P, over) });
  if (global.__errs.length) console.error('worklet errors', JSON.stringify(global.__errs));
  if (MODE === 'blob') {
    const head = pr._viewF(pr.api.live_blob_ptr(pr.st), 5);
    let n = head[0] === 2 ? (head[4] | 0) : 1982;
    if (n < 16) n = 16;
    if (n > 16384) n = 16384;
    fs.writeFileSync(ARGS[0], Buffer.from(Float32Array.from(pr._viewF(pr.api.live_blob_ptr(pr.st), n)).buffer));
    return;
  }
  const inp = [[new Float32Array(BLK), new Float32Array(BLK)]], out = [[new Float32Array(BLK), new Float32Array(BLK)]];
  let s = 7; const rnd = () => { s = (Math.imul(s, 1103515245) + 12345) >>> 0; return (s / 4294967296) - 0.5; };
  if (MODE === 'bench') {
    const burst = +ARGS[0], total = +ARGS[1], bps = SR / BLK; const nb = Math.round(total * bps), nbb = Math.round(burst * bps);
    const win = []; let acc = 0, n = 0, mx = 0; const all = { play: [], silence: [] };
    for (let b = 0; b < nb; b++) { const on = b < nbb; for (let i = 0; i < BLK; i++) { const v = on ? rnd() * 0.6 : 0; inp[0][0][i] = v; inp[0][1][i] = v; }
      const t0 = process.hrtime.bigint(); pr.process(inp, out); const dt = Number(process.hrtime.bigint() - t0) / 1e6;
      if (b > 50) (on ? all.play : all.silence).push(dt); acc += dt; n++; mx = Math.max(mx, dt);
      if ((b + 1) % Math.round(bps * 2) === 0) { win.push({ t: +((b + 1) / bps).toFixed(1), mean_ms: +(acc / n).toFixed(4), max_ms: +mx.toFixed(3), phase: on ? 'play' : 'silence' }); acc = 0; n = 0; mx = 0; } }
    const med = a => { const q = [...a].sort((x, y) => x - y); return q.length ? q[Math.floor(q.length / 2)] : null; };
    const mean = a => a.length ? a.reduce((x, y) => x + y, 0) / a.length : null;
    const lateSil = all.silence.slice(Math.floor(all.silence.length / 2));
    const res = { play_blocks: all.play, silence_blocks: all.silence, windows: win, play_mean_ms: mean(all.play), silence_mean_ms: mean(all.silence), silence_late_mean_ms: mean(lateSil), silence_late_median_ms: med(lateSil), budget_ms: 128 / 48 };
    if (ARGS[2]) fs.writeFileSync(ARGS[2], JSON.stringify(res, null, 1)); else console.log(JSON.stringify(res));
    return;
  }
  let total, burst = 0, outPath, sine = 0;
  if (MODE === 'ir') { total = Math.round(+ARGS[0] * SR); outPath = ARGS[1]; }
  else if (MODE === 'noise') { burst = Math.round(+ARGS[0] * SR); total = Math.round(+ARGS[1] * SR); outPath = ARGS[2]; }
  else if (MODE === 'sine') { sine = +ARGS[0]; total = Math.round(+ARGS[1] * SR); outPath = ARGS[2]; }
  let sched = [];
  if (MODE === 'switch') { burst = Math.round(+ARGS[0] * SR); total = Math.round(+ARGS[1] * SR); outPath = ARGS[2];
    sched = JSON.parse(ARGS[3] || '[]').map(e => [Math.round(+e[0] * SR / BLK) * BLK, e[1]]).sort((x, y) => x[0] - y[0]); }
  const buf = new Float32Array(Math.ceil(total / BLK) * BLK * 2); let o = 0;
  for (let t0 = 0; t0 < total; t0 += BLK) {
    while (sched.length && sched[0][0] <= t0) { const e = sched.shift(); pr.port.onmessage({ data: msgFrom(P, Object.assign({}, over, e[1])) }); }
    for (let i = 0; i < BLK; i++) { const t = t0 + i; let v = 0;
      if (MODE === 'ir') v = t === 0 ? 1 : 0; else if (MODE === 'noise' || MODE === 'switch') v = t < burst ? rnd() * 0.6 : 0; else v = 0.5 * Math.sin(2 * Math.PI * sine * t / SR);
      inp[0][0][i] = v; inp[0][1][i] = v; }
    pr.process(inp, out);
    for (let i = 0; i < BLK; i++) { buf[o++] = out[0][0][i]; buf[o++] = out[0][1][i]; }
  }
  fs.writeFileSync(outPath, Buffer.from(buf.buffer));
})().catch(e => { console.error(e); process.exit(1); });
