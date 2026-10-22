"""D-AUD-6 research: per-capsule heights, Render only, box only. before = current tree (heights ignored),
after = hpatch prototype (heights in early + direct + per-bus FDN delays). Dry = robotic_1240 dry_est (44.1k->48k), first 20 s."""
import json, subprocess, os, sys, numpy as np
from scipy.signal import resample_poly, fftconvolve
from scipy.io import wavfile
PY='/workspace/scratch_er_dropout/venv/bin/python'; SW='/workspace/audit_1852/software'; HERE='/workspace/audit_1852/heights'
LIB='/workspace/build_support_2/3_phase_acceptance_tests/harness/lib'; B='/workspace/build_support_2'
SR=48000; MS=3000
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); base.update(direct_wet=1.0,early_wet=1.0,fdn_wet=1.0)
CASES={'flat':{}, 'pair_up_0p5':dict(my_l=2.0,my_r=2.0,my_c=1.5), 'tilt_lr_0p6':dict(my_l=1.2,my_r=1.8,my_c=1.5), 'pair_up_1p0':dict(my_l=2.5,my_r=2.5,my_c=1.5)}
def rir(script,body,tag):
    out=f'{HERE}/guitar/rir_{tag}.f32'
    if not os.path.exists(out):
        r=subprocess.run([PY,script,SW,json.dumps(body),out,str(MS),str(SR)],capture_output=True,text=True)
        if r.returncode: raise SystemExit(r.stderr[-800:])
    return np.fromfile(out,np.float32).reshape(-1,2).astype(np.float64)
def null_db(a,b):
    n=min(len(a),len(b)); a,b=a[:n],b[:n]; return 10*np.log10(max(np.sum((a-b)**2),1e-300)/max(np.sum(a**2),1e-300))
FC=[125,250,500,1000,2000,3150,4000,5000,6300,8000,10000,12500,16000]
def bands(x):
    X=np.abs(np.fft.rfft(x,1<<18))**2; f=np.fft.rfftfreq(1<<18,1/SR)
    return np.array([10*np.log10(X[(f>=c*2**-(1/6))&(f<c*2**(1/6))].sum()+1e-30) for c in FC])
irB=rir(LIB+'/render_ir.py',base,'before')
d0=int(np.argmax(np.abs(irB).sum(1)[:int(0.05*SR)]))  # direct sample (either channel)
w_e=slice(0,d0+int(0.08*SR)); w_t=slice(d0+int(0.08*SR),None)
dry=resample_poly(np.load(B+'/roadmap/robotic_1240/real/dry_est_0.001.npy').astype(np.float64).ravel(),160,147)[:20*SR]
yB=np.stack([fftconvolve(dry,irB[:,c]) for c in (0,1)],1)
log={}
for cn,o in CASES.items():
    b=dict(base,**o); irA=rir(HERE+'/render_ir_h.py',b,'after_'+cn)
    m={'heights_m':{'L':o.get('my_l',1.5),'R':o.get('my_r',1.5),'C':o.get('my_c',1.5)},
       'ir_max_abs_vs_before':float(np.max(np.abs(irA[:len(irB)]-irB[:len(irA)]))),'ir_null_db':round(null_db(irB,irA),1)}
    for ch,nm in ((0,'L'),(1,'R')):
        dB=lambda ir,w: 10*np.log10(np.sum(ir[w,ch]**2)+1e-30)
        m[f'early_level_delta_db_{nm}']=round(dB(irA,w_e)-dB(irB,w_e),2); m[f'tail_level_delta_db_{nm}']=round(dB(irA,w_t)-dB(irB,w_t),2)
        m[f'early_3oct_delta_{nm}']=[round(x,2) for x in bands(irA[w_e,ch])-bands(irB[w_e,ch])]
        m[f'tail_3oct_delta_{nm}']=[round(x,2) for x in bands(irA[w_t,ch])-bands(irB[w_t,ch])]
        m[f'direct_sample_{nm}']=[int(np.argmax(np.abs(irB[:int(0.05*SR),ch]))),int(np.argmax(np.abs(irA[:int(0.05*SR),ch])))]
    ec=lambda ir: float(np.corrcoef(ir[w_e,0],ir[w_e,1])[0,1])
    m['early_LR_corr']=[round(ec(irB),3),round(ec(irA),3)]
    if cn!='flat':
        yA=np.stack([fftconvolve(dry,irA[:,c]) for c in (0,1)],1)
        rms=lambda y: float(np.sqrt(np.mean(y**2))); g=rms(yB)/rms(yA)
        pk=max(np.abs(yB).max(),np.abs(yA*g).max()); norm=0.5/pk
        wavfile.write(f'{HERE}/guitar/{cn}_before.wav',SR,np.round(np.clip(yB*norm,-1,1)*32767).astype(np.int16))
        wavfile.write(f'{HERE}/guitar/{cn}_after.wav',SR,np.round(np.clip(yA*g*norm,-1,1)*32767).astype(np.int16))
        m['after_trim_to_match_db']=round(20*np.log10(g),3); m['shared_norm_db']=round(20*np.log10(norm),2)
        m['null_after_vs_before_db']=round(null_db(yB,yA*g),1)
    log[cn]=m; print(cn,json.dumps(m),flush=True)
log['_bands_hz']=FC; log['_windows']={'direct_sample':d0,'early':'0..direct+80ms','tail':'direct+80ms..3s'}
json.dump(log,open(HERE+'/guitar/guitar_heights.json','w'),indent=1)
