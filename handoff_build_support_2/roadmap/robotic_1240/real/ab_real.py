"""A/B on Idle's real guitar (dry estimated by 2-channel Wiener deconvolution of his 13:31 render,
372-412 s; the re-convolved estimate nulls his render to -64 dB). 44.1 kHz like his file."""
import json, subprocess, os, numpy as np, wave, soundfile as sf
H=os.path.dirname(os.path.abspath(__file__)); R=os.path.dirname(H)
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
SW=B+'/snapshot_2026-10-02_1140/software'; FW=R+'/fixwasm/'; OUT=H+'/ab_real'; os.makedirs(OUT,exist_ok=True); SR=44100
d=np.load(H+'/dry_est_0.001.npy').astype(float)[2*SR:]           # drop the 2 s pre-roll -> 372..412 s
d=d/np.max(np.abs(d))*0.5
x,_=sf.read(H+'/play_robotic_tmpvf2xxu9a.wav'); real=x[372*SR:412*SR]
def wav(p,y):
    pcm=(np.clip(y,-1,1)*32767).astype('<i2')
    with wave.open(p,'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
def conv(sig,h):
    n=1<<int(np.ceil(np.log2(len(sig)+len(h))))
    return np.stack([np.fft.irfft(np.fft.rfft(sig,n)*np.fft.rfft(h[:,c],n),n)[:len(sig)] for c in range(2)],1)
def rms(y): return float(20*np.log10(np.sqrt(np.mean(y**2))))
def ac(y):
    o=[]
    for c in range(2):
        F=np.fft.rfft(y[:,c],1<<22); a=np.fft.irfft(np.abs(F)**2)[:int(.06*SR)]; a/=a[0]; l0=int(.002*SR)
        j=int(np.argmax(np.abs(a[l0:])))+l0; o.append((round(j/SR*1000,2),round(float(a[j]),3)))
    return o
res={}
# Render (offline): IRs from the 11:40 code, with/without output signs
hA=np.fromfile(H+'/w_exp_none.f32',np.float32).reshape(-1,2).astype(float)
hB=np.fromfile(H+'/w_exp_osign.f32',np.float32).reshape(-1,2).astype(float)
hC=np.fromfile(H+'/w_exp_csign_44100.f32',np.float32).reshape(-1,2).astype(float)
yA=conv(d,hA); yB=conv(d,hB); yC=conv(d,hC)
k=0.7/max(np.max(np.abs(yA)),np.max(np.abs(yB))); kB=10**((rms(yA)-rms(yB))/20)
wav(OUT+'/R0_idle_real_render_372-412s.wav',real/np.max(np.abs(real))*0.7)
wav(OUT+'/R1_render_default_fdn_only__A_today.wav',yA*k)
wav(OUT+'/R1_render_default_fdn_only__B_fix_output_signs.wav',yB*k*kB)
kC=10**((rms(yA)-rms(yC))/20); wav(OUT+'/R1_render_default_fdn_only__C_fix_column_signs.wav',yC*k*kC)
res['render']=dict(A_ac=ac(yA),B_ac=ac(yB),B_minus_A_raw_db=round(rms(yB)-rms(yA),2),C_minus_A_raw_db=round(rms(yC)-rms(yA),2),B_level_matched=True,real_ac=ac(real))
# Play (wasm): same body at 44.1 kHz, dual-mono dry
body=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); body.update(direct_wet=0,early_wet=0,fdn_wet=1,dry_gain=0)
pj=H+'/w_pab_real.json'; fin=H+'/w_real_in.f32'; np.stack([d,d],1).astype(np.float32).tofile(fin)
subprocess.run([P,LIB+'/dump_params.py',SW,json.dumps(body),pj,str(SR)],check=True,capture_output=True)
outs={}
for name,wf in (('A_today',FW+'ship.wasm'),('B_fix_output_signs_plus_DC',FW+'osign.wasm'),('C_fix_column_signs_plus_DC',FW+'csign.wasm')):
    f=H+f'/w_play_real_{name}.f32'
    r=subprocess.run(['node',R+'/wasm_run_file.js',SW,pj,'{}','file',fin,f],capture_output=True,text=True,env=dict(os.environ,WASM=wf)); assert r.returncode==0,r.stderr
    outs[name]=np.fromfile(f,np.float32).reshape(-1,2).astype(float)
a,b=outs['A_today'],outs['B_fix_output_signs_plus_DC']; k=0.7/max(np.max(np.abs(a)),np.max(np.abs(b))); kB=10**((rms(a)-rms(b))/20)
wav(OUT+'/P1_play_default_fdn_only__A_today.wav',a*k); wav(OUT+'/P1_play_default_fdn_only__B_fix_output_signs_plus_DC.wav',b*k*kB)
cc_=outs['C_fix_column_signs_plus_DC']; kC=10**((rms(a)-rms(cc_))/20); wav(OUT+'/P1_play_default_fdn_only__C_fix_column_signs_plus_DC.wav',cc_*k*kC)
res['play']=dict(A_ac=ac(a),B_ac=ac(b),B_minus_A_raw_db=round(rms(b)-rms(a),2),C_minus_A_raw_db=round(rms(cc_)-rms(a),2),B_level_matched=True,
                 A_vs_idle_render_corr=[round(float(np.corrcoef(a[:len(real),c]*0+a[:len(real),c],real[:len(a),c])[0,1]),3) for c in range(2)])
print(json.dumps(res,indent=1)); json.dump(res,open(H+'/ab_real.json','w'),indent=1)
