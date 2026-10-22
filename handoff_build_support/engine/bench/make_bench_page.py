"""Build a self-contained HTML CPU bench for live_stereo.wasm (no node, no server, no install).
Open the .html in Chrome/Edge (double-click works: everything is inlined) and press Run."""
import sys, json, base64
sys.path.insert(0, '/workspace/build_support/engine/tools')
import numpy as np
from pack import pack
W = '/workspace/build_support/engine/work/'
def b64(a): return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
def packset(pjson, over):
    P = json.load(open(W + pjson))
    if P.get('line_t60'): over = dict(over, line_t60=P['line_t60'])
    blob, route, irs, lens = pack(P, over)
    return {'blob': b64(blob), 'route': b64(route), 'irs': b64(irs), 'lens': b64(lens), 'nblob': int(len(blob)), 'nirs': int(len(lens))}
engines = [
    ('current (shipped 2026-09-26)', '/workspace/build_support/snapshot_2026-09-27/software/static/wasm/live_stereo.wasm', 'S1.json', 'S1two.json'),
    ('fix F1+F2+F3 (z^-1 loop)', W + 'sw_fix/software/static/wasm/live_stereo.wasm', 'S1fix.json', 'S1fixtwo.json'),
    ('fix + F5 same-sample loop', W + 'variants/live_stereo_same.wasm', 'S1fix.json', 'S1fixtwo.json'),
]
data = []
for name, wasm, p1, p2 in engines:
    data.append({'name': name, 'wasm': base64.b64encode(open(wasm, 'rb').read()).decode(), 'cases': {
        '1 src, colour off': packset(p1, {'colour_on': False}),
        '1 src, colour on': packset(p1, {}),
        '2 src, colour on': packset(p2, {'two_sources': True}),
    }})
html = r'''<!doctype html><html><head><meta charset="utf-8"><title>2011 Room Reverb - Play CPU bench</title>
<style>body{font:14px system-ui,sans-serif;margin:24px;max-width:1000px}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:4px 8px;text-align:right}th{background:#eee}td:first-child,td:nth-child(2){text-align:left}.bad{background:#fcc}.ok{background:#cfc}pre{background:#f4f4f4;padding:8px;white-space:pre-wrap}</style></head><body>
<h2>2011 Room Reverb — Play engine CPU bench (live_stereo.wasm)</h2>
<p>Self-contained: nothing is installed, nothing talks to the tweak app. Runs the same WASM the Play button uses, on this browser's main thread
(same engine as the AudioWorklet thread). Budget per 128-sample block at 48 kHz = <b>2.667 ms</b>. Close other heavy tabs, then press Run (takes ~1-2 min; the page may look frozen between rows).</p>
<button id="run">Run bench</button> <button id="copy">Copy results</button> <span id="st"></span>
<table id="t"><tr><th>engine</th><th>case</th><th>playing ms/block</th><th>% budget</th><th>silence (4-10 s after stop) ms/block</th><th>% budget</th><th>silence / playing</th></tr></table>
<pre id="log"></pre>
<script>
const DATA = __DATA__;
const SR = 48000, B = 128, BUDGET = 128 / 48;
function u8(s){const b=atob(s);const a=new Uint8Array(b.length);for(let i=0;i<b.length;i++)a[i]=b.charCodeAt(i);return a;}
function f32(s){const a=u8(s);return new Float32Array(a.buffer,a.byteOffset,a.byteLength>>2);}
function i32(s){const a=u8(s);return new Int32Array(a.buffer,a.byteOffset,a.byteLength>>2);}
async function makeEngine(wasmBytes, c){
  const mod = await WebAssembly.instantiate(wasmBytes, {}); const api = mod.instance.exports;
  const heap = api.memory.buffer.byteLength; const need = api.live_bytes(SR); api.memory.grow(Math.ceil(need/65536));
  const st = api.live_bind(heap, need, SR); if(!st) throw new Error('bind failed');
  const F=(p,n)=>new Float32Array(api.memory.buffer,p,n), I=(p,n)=>new Int32Array(api.memory.buffer,p,n);
  const blob=f32(c.blob); F(api.live_blob_ptr(st),blob.length).set(blob); api.live_load_room(st, blob.length);
  if(c.nirs>0){const irs=f32(c.irs), lens=i32(c.lens); F(api.live_ir_ptr(st),irs.length).set(irs); I(api.live_len_ptr(st),lens.length).set(lens); api.live_load_irs(st,lens.length);
    I(api.live_route_ptr(st),230).set(i32(c.route)); api.live_load_route(st);}
  return {api, st, F};
}
function runBlocks(E, nBlocks, noise, rng){
  const {api,st,F}=E; const pl=api.live_in_l(st), pr=api.live_in_r(st), ol=api.live_out_l(st), or=api.live_out_r(st);
  const inL=F(pl,B), inR=F(pr,B); let t0=performance.now();
  for(let b=0;b<nBlocks;b++){ for(let i=0;i<B;i++){const v=noise?(rng()-0.5)*0.6:0; inL[i]=v; inR[i]=v;} api.live_stereo(st,pl,pr,ol,or,B); }
  return (performance.now()-t0)/nBlocks;
}
function lcg(){let s=7;return ()=>{s=(Math.imul(s,1103515245)+12345)>>>0;return s/4294967296;};}
const bps = SR/B; const rows=[];
async function run(){
  document.getElementById('run').disabled=true; const log=document.getElementById('log');
  const ua = navigator.userAgent, hw = navigator.hardwareConcurrency;
  log.textContent = 'UA: '+ua+'\ncores: '+hw+'\n';
  for(const eng of DATA){ const bytes=u8(eng.wasm);
    for(const [cname,c] of Object.entries(eng.cases)){
      document.getElementById('st').textContent='running '+eng.name+' / '+cname+' ...'; await new Promise(r=>setTimeout(r,30));
      const E=await makeEngine(bytes,c); const rng=lcg();
      runBlocks(E, Math.round(0.5*bps), true, rng);            // warm-up / JIT
      const play=runBlocks(E, Math.round(6*bps), true, rng);   // 6 s playing
      runBlocks(E, Math.round(4*bps), false, rng);             // 4 s: tail rings down
      const sil=runBlocks(E, Math.round(6*bps), false, rng);   // 4-10 s after stop
      const r={engine:eng.name,case:cname,play_ms:+play.toFixed(3),play_pct:+(100*play/BUDGET).toFixed(1),silence_ms:+sil.toFixed(3),silence_pct:+(100*sil/BUDGET).toFixed(1),ratio:+(sil/play).toFixed(2)};
      rows.push(r); const tr=document.createElement('tr');
      tr.innerHTML=`<td>${r.engine}</td><td>${r.case}</td><td>${r.play_ms}</td><td class="${r.play_pct>75?'bad':'ok'}">${r.play_pct}%</td><td>${r.silence_ms}</td><td class="${r.silence_pct>75?'bad':'ok'}">${r.silence_pct}%</td><td class="${r.ratio>1.5?'bad':'ok'}">${r.ratio}</td>`;
      document.getElementById('t').appendChild(tr); await new Promise(r=>setTimeout(r,30));
    } }
  document.getElementById('st').textContent='done'; log.textContent += JSON.stringify(rows,null,1);
  document.getElementById('run').disabled=false;
}
document.getElementById('run').onclick=()=>run().catch(e=>{document.getElementById('st').textContent='error: '+e.message;});
document.getElementById('copy').onclick=()=>navigator.clipboard.writeText(document.getElementById('log').textContent);
</script></body></html>'''
out = '/workspace/build_support/engine/bench/live_stereo_cpu_bench.html'
open(out, 'w').write(html.replace('__DATA__', json.dumps(data)))
print(out)
