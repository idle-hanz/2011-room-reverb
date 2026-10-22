// Box benchmark: scattering kernel as WASM (zig cc -O3 -msimd128) and as plain JS, in Node 20 (V8, same engine family as Chrome).
const fs=require('fs');const {performance}=require('perf_hooks');
const Ns=[32,64,128],Ks=[0,8,16,24];const REP=7,NB=1500;
function timeit(fn){for(let i=0;i<300;i++)fn();let best=1e9;for(let r=0;r<REP;r++){const t=performance.now();for(let i=0;i<NB;i++)fn();best=Math.min(best,(performance.now()-t)/NB);}return best;}
async function wasm(file,label){const {instance}=await WebAssembly.instantiate(fs.readFileSync(file),{});const e=instance.exports;
 for(const N of Ns)for(const K of Ks){e.sk_init(N,K);const inp=new Float32Array(e.memory.buffer,e.sk_in(),128);for(let i=0;i<128;i++)inp[i]=Math.random()-0.5;
  const ms=timeit(()=>e.sk_block());console.log(`${label} N=${String(N).padStart(3)} K=${String(K).padStart(2)}  ${ms.toFixed(4)} ms/128-block (${(ms/2.6667*100).toFixed(2)}%)`);}}
// JS block-major port (Float32Array, same structure as scatter_kernel_block.c)
function jsKernel(N,K){const RING=16384,MASK=RING-1,HIST=2048;const ring=[],hist=[],dly=new Float32Array(N),off=[],amp=[],bs=[],bd=[];
 for(let i=0;i<N;i++){ring.push(new Float32Array(RING));hist.push(new Float32Array(2*HIST));dly[i]=400+2400*Math.random();
  const o=new Int32Array(K),a=new Float32Array(K);for(let k=0;k<K;k++){o[k]=1+k*40+((40*Math.random())|0);a[k]=(Math.random()<.5?-1:1)*.25;}off.push(o);amp.push(a);
  bs.push(new Float64Array([0.9,-0.5,0.2,-0.55,0.22,0,0]));bd.push(new Float64Array([0.1,-0.05,0.02,-0.55,0.22,0,0]));}
 const inp=new Float32Array(128),out=new Float32Array(128),sc=new Float32Array(128);let w=0,hp=0;for(let i=0;i<128;i++)inp[i]=Math.random()-.5;
 return ()=>{out.fill(0);for(let i=0;i<N;i++){const r=ring[i],h=hist[i],d=dly[i],q=bs[i],p=bd[i];
   for(let t=0;t<128;t++){const ww=(w+t)&MASK;r[ww]=inp[t];let pp=(w+t)-d;if(pp<0)pp+=RING;const i0=pp|0,fr=pp-i0;const v=r[i0&MASK]*(1-fr)+r[(i0+1)&MASK]*fr;h[hp+t]=v;h[hp+HIST+t]=v;}
   sc.fill(0);const o=off[i],a=amp[i];for(let k=0;k<K;k++){const ak=a[k],s0=hp+HIST-o[k];for(let t=0;t<128;t++)sc[t]+=ak*h[s0+t];}
   let z1=q[5],z2=q[6],y1=p[5],y2=p[6];for(let t=0;t<128;t++){const x=h[hp+HIST+t];const y=q[0]*x+z1;z1=q[1]*x-q[3]*y+z2;z2=q[2]*x-q[4]*y;
     const s=sc[t];const yy=p[0]*s+y1;y1=p[1]*s-p[3]*yy+y2;y2=p[2]*s-p[4]*yy;out[t]+=y+yy;}q[5]=z1;q[6]=z2;p[5]=y1;p[6]=y2;}
  w=(w+128)&MASK;hp=(hp+128)&(HIST-1);};}
(async()=>{await wasm('scatter_kernel.wasm','wasm-scalar');await wasm('scatter_kernel_block.wasm','wasm-block ');
 for(const N of Ns)for(const K of Ks){const f=jsKernel(N,K);const ms=timeit(f);console.log(`js-block    N=${String(N).padStart(3)} K=${String(K).padStart(2)}  ${ms.toFixed(4)} ms/128-block (${(ms/2.6667*100).toFixed(2)}%)`);}})();
