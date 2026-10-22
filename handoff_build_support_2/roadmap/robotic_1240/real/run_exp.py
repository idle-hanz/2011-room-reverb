import json, subprocess, numpy as np, os, sys
PY='/workspace/scratch_er_dropout/venv/bin/python'
SW='/workspace/build_support_2/snapshot_2026-10-02_1140/software'
body=json.load(open('../../s4_verify_1140/measure/client_body_1140.json'))
body.update(direct_wet=0,early_wet=0,fdn_wet=1,dry_gain=0)
sr=int(os.environ.get('SR','44100'))
def top(h):
    o=[]
    for ch in range(2):
        F=np.fft.rfft(h[:,ch],1<<18); ac=np.fft.irfft(np.abs(F)**2)[:int(0.06*sr)]; ac/=ac[0]
        l0=int(0.002*sr); i=np.argsort(np.abs(ac[l0:]))[::-1]+l0
        # distinct peaks
        pk=[]
        for j in i:
            if all(abs(j-q)>20 for q in pk): pk.append(j)
            if len(pk)==4: break
        o.append([(round(j/sr*1000,2),round(float(ac[j]),3)) for j in sorted(pk)])
    return o
res={}
for e in sys.argv[1:]:
    out=os.path.abspath(f'w_exp_{e}_{sr}.f32')
    env=dict(os.environ,EXP=e,DLYMOD=os.path.abspath('mod_exp.py'))
    r=subprocess.run([PY,'render_ir_mod.py',SW,json.dumps(body),out,'1500',str(sr)],capture_output=True,text=True,env=env)
    if r.returncode: print(e,r.stderr[-500:]); continue
    h=np.fromfile(out,np.float32).reshape(-1,2).astype(float)
    m=h.mean(1); sch=np.cumsum((m**2)[::-1])[::-1]; sch=10*np.log10(sch/sch[0]+1e-30)
    def t(a,b):
        i=np.argmax(sch<=a); j=np.argmax(sch<=b); return round((j-i)/sr*60/(a-b),3)
    rms=round(float(10*np.log10(np.mean(h[int(.05*sr):]**2))),2)
    lr=round(float(np.corrcoef(h[int(.05*sr):,0],h[int(.05*sr):,1])[0,1]),3)
    res[e]=dict(ac=top(h),T20=t(-5,-25),rms_db=rms,lr_corr=lr); print(e,res[e],flush=True)
json.dump(res,open('exp_'+'_'.join(sys.argv[1:])+'.json','w'),indent=1)
