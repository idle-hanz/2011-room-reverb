import numpy as np, json, os, glob
H=os.path.dirname(os.path.abspath(__file__)); O=H+'/old_a80209'; N=H+'/new_9b7cdf'; SR=48000
def ld(d,n): return np.fromfile(f'{d}/{n}.f32',dtype=np.float32)
def maxabs(a,b): m=min(len(a),len(b)); return float(np.max(np.abs(a[:m].astype(np.float64)-b[:m])))
def nulldb(a,b):
    m=min(len(a),len(b)); a=a[:m].astype(np.float64); b=b[:m].astype(np.float64); return float(10*np.log10(np.sum((a-b)**2)/max(np.sum(b**2),1e-30)+1e-300))
F=[125,160,200,250,315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300,8000,10000,12500,16000]
def bands(x,stereo,t0=0.08,t1=None):
    if stereo: x=x.reshape(-1,2)
    else:
        # render .f32 layout: try stereo interleaved
        x=x.reshape(-1,2)
    s=int(t0*SR); e=len(x) if t1 is None else int(t1*SR); y=x[s:e].astype(np.float64)
    X=np.abs(np.fft.rfft(y,axis=0))**2; f=np.fft.rfftfreq(len(y),1/SR)
    return np.array([10*np.log10(X[(f>=fc/2**(1/6))&(f<fc*2**(1/6))].sum()+1e-300) for fc in F])
res={'max_abs':{}, 'null_db':{}, 'tail_delta_db':{}, 'early_delta_db':{}}
for f in sorted(glob.glob(N+'/*.f32')):
    n=os.path.basename(f)[:-4]
    if not os.path.exists(f'{O}/{n}.f32'): continue
    a,b=ld(N,n),ld(O,n); res['max_abs'][n]=maxabs(a,b); res['null_db'][n]=round(nulldb(a,b),2)
    if n.startswith(('play_default','render_default','play_hs6','render_hs6')):
        res['tail_delta_db'][n]=[round(x,3) for x in bands(a,1)-bands(b,1)]
        res['early_delta_db'][n]=[round(x,3) for x in bands(a,1,0.0,0.08)-bands(b,1,0.0,0.08)]
res['bands_hz']=F
json.dump(res,open(H+'/compare_1600.json','w'),indent=1)
for k in res['max_abs']: print(f"{k:24s} maxabs {res['max_abs'][k]:.3g}  null {res['null_db'][k]}")
for k,v in res['tail_delta_db'].items(): print('TAIL',k,v)
for k,v in res['early_delta_db'].items(): print('EARLY',k,v)
