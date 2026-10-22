"""Guitar A/B at 48 kHz (dry = estimate from Idle's render, 44.1k -> 48k). Play variants run the real worklet on the
file (colour on, as heard); Render variants convolve the 3 s Render FDN IR. RMS-matched to Render-current (R_cur);
raw level differences in wav_ab.json."""
from common import *
import subprocess, wave
from scipy.signal import resample_poly, fftconvolve
d=np.load(B+'/roadmap/robotic_1240/real/dry_est_0.001.npy').astype(float)[2*44100:22*44100]
d=resample_poly(d,160,147); d=d/np.max(np.abs(d))*0.5
fin=R+'/data/tmp/guitar48_in.f32'; np.stack([d,d],1).astype(np.float32).tofile(fin)
def wav(p,y):
    pcm=(np.clip(y,-1,1)*32767).astype('<i2')
    with wave.open(p,'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000); w.writeframes(pcm.tobytes())
rms=lambda y: float(20*np.log10(np.sqrt(np.mean(y**2))))
res={}
for sc in ('default','hall_preset'):
    body=dict(SCENES[sc](),**FDN); pj=f'{R}/data/tmp/p48_{sc}.json'
    subprocess.run([PY,HAR+'/lib/dump_params.py',TREES['R_cur'],json.dumps(body),pj,'48000'],check=True,capture_output=True)
    outs={}
    for pv in ('P_old','P_f5'):
        f=f'{R}/data/tmp/wav_{sc}_{pv}.f32'
        r=subprocess.run(['node',B+'/roadmap/robotic_1240/wasm_run_file.js',TREES['R_cur'],pj,json.dumps(OVER),'file',fin,f],capture_output=True,text=True,env=dict(os.environ,WASM=WASM[pv])); assert r.returncode==0,r.stderr[-400:]
        outs[pv]=np.fromfile(f,np.float32).reshape(-1,2).astype(float)
    for rv in ('R_cur','R_z1'):
        h=np.fromfile(f'{R}/data/ir_{sc}_col_{rv}.f32',np.float32).reshape(-1,2).astype(float)
        outs[rv]=np.stack([fftconvolve(d,h[:,c]) for c in (0,1)],1)
    n=min(len(v) for v in outs.values()); ref=outs['R_cur'][:n]; k=0.7/max(np.max(np.abs(v[:n]))*10**((rms(ref)-rms(v[:n]))/20) for v in outs.values())
    names={'P_old':'Play_today_z1','P_f5':'Play_F5_same_sample','R_cur':'Render_today_same_sample','R_z1':'Render_new_z1_like_Play'}
    for v,y in outs.items():
        y=y[:n]; g=10**((rms(ref)-rms(y))/20); p=f'{R}/wav/{sc}__{names[v]}.wav'; wav(p,y*g*k)
        res[f'{sc}|{v}']=dict(file=os.path.basename(p),raw_minus_Rcur_db=round(rms(y)-rms(ref),2)); print(res[f'{sc}|{v}'],flush=True)
json.dump(res,open(R+'/data/wav_ab.json','w'),indent=1)
