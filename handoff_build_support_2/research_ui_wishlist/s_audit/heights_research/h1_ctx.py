import json, subprocess, os, numpy as np
from scipy.signal import resample_poly, fftconvolve
from scipy.io import wavfile
PY='/workspace/scratch_er_dropout/venv/bin/python'; SW='/workspace/audit_1852/software'; HERE='/workspace/audit_1852/heights'
LIB='/workspace/build_support_2/3_phase_acceptance_tests/harness/lib'; B='/workspace/build_support_2'; SR=48000; MS=3000
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); base.update(direct_wet=1.0,early_wet=1.0,fdn_wet=1.0)
FC=[125,250,500,1000,2000,3150,4000,5000,6300,8000,10000,12500,16000]
def bands(x):
    X=np.abs(np.fft.rfft(x,1<<18))**2; f=np.fft.rfftfreq(1<<18,1/SR)
    return np.array([10*np.log10(X[(f>=c*2**-(1/6))&(f<c*2**(1/6))].sum()+1e-30) for c in FC])
def rir(script,body,tag,env=None):
    out=f'{HERE}/guitar/rir_{tag}.f32'
    if not os.path.exists(out):
        r=subprocess.run([PY,script,SW,json.dumps(body),out,str(MS),str(SR)],capture_output=True,text=True,env=dict(os.environ,**(env or {})))
        if r.returncode: raise SystemExit(r.stderr[-800:])
    return np.fromfile(out,np.float32).reshape(-1,2).astype(np.float64)
irB=rir(LIB+'/render_ir.py',base,'before'); d0=int(np.argmax(np.abs(irB).sum(1)[:int(0.05*SR)]))
w_e=slice(0,d0+int(0.08*SR)); w_t=slice(d0+int(0.08*SR),None)
runs={'H1_pair_up_0p5':(HERE+'/render_ir_h.py',dict(base,my_l=2.0,my_r=2.0,my_c=1.5),{'HMODE':'early'}),
      'H1_tilt_lr_0p6':(HERE+'/render_ir_h.py',dict(base,my_l=1.2,my_r=1.8,my_c=1.5),{'HMODE':'early'}),
      'ref_stand_up_0p5':(LIB+'/render_ir.py',dict(base,my=2.0),None)}
log={}
for n,(s,b,e) in runs.items():
    ir=rir(s,b,n,e); m={}
    for ch,nm in ((0,'L'),(1,'R')):
        dB=lambda x,w: 10*np.log10(np.sum(x[w,ch]**2)+1e-30)
        m[f'early_level_delta_db_{nm}']=round(dB(ir,w_e)-dB(irB,w_e),2); m[f'tail_level_delta_db_{nm}']=round(dB(ir,w_t)-dB(irB,w_t),2)
        m[f'early_3oct_delta_{nm}']=[round(x,2) for x in bands(ir[w_e,ch])-bands(irB[w_e,ch])]
        m[f'tail_3oct_delta_{nm}']=[round(x,2) for x in bands(ir[w_t,ch])-bands(irB[w_t,ch])]
    m['tail_worst_abs_band_db']=max(max(abs(x) for x in m['tail_3oct_delta_L']),max(abs(x) for x in m['tail_3oct_delta_R']))
    log[n]=m; print(n,json.dumps(m),flush=True)
    if n=='H1_pair_up_0p5':
        dry=resample_poly(np.load(B+'/roadmap/robotic_1240/real/dry_est_0.001.npy').astype(np.float64).ravel(),160,147)[:20*SR]
        yB=np.stack([fftconvolve(dry,irB[:,c]) for c in (0,1)],1); yA=np.stack([fftconvolve(dry,ir[:,c]) for c in (0,1)],1)
        g=np.sqrt(np.mean(yB**2)/np.mean(yA**2)); pk=max(np.abs(yB).max(),np.abs(yA*g).max()); norm=0.5/pk
        wavfile.write(f'{HERE}/guitar/pair_up_0p5_after_H1.wav',SR,np.round(np.clip(yA*g*norm,-1,1)*32767).astype(np.int16))
        m['after_trim_to_match_db']=round(20*np.log10(g),3); m['shared_norm_db']=round(20*np.log10(norm),2)
json.dump(log,open(HERE+'/guitar/h1_ctx.json','w'),indent=1)
