"""Per-face Solo: early-field direction in Play and Render (direct off, FDN off), default room, source centred."""
import json, subprocess, os, copy, math, numpy as np, sys
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
HERE=os.path.dirname(os.path.abspath(__file__)); W=HERE+'/w'; os.makedirs(W,exist_ok=True)
SW=os.environ.get('SW',B+'/snapshot_2026-10-02_1140/software'); TAG=os.environ.get('TAG','1140')
RIR=B+'/roadmap/s4_verify_1140/measure/render_ir3.py'; SR=48000
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); base.pop('mics',None)
base.update(sx=3.0, fdn_wet=0, direct_wet=0, early_wet=1, fader_early=0.5)   # source on the centreline, early bus only
def play(b,key):
    pj=f'{W}/p_{TAG}_{key}.json'; f=f'{W}/play_{TAG}_{key}.f32'
    subprocess.run([P,LIB+'/dump_params.py',SW,json.dumps(b),pj,str(SR)],check=True,capture_output=True)
    subprocess.run(['node',LIB+'/wasm_run.js',SW,pj,'{}','ir','0.25',f],check=True,capture_output=True)
    return np.fromfile(f,np.float32).reshape(-1,2).astype(float), json.load(open(pj))
def render(b,key):
    f=f'{W}/rend_{TAG}_{key}.f32'
    r=subprocess.run([P,RIR,SW,json.dumps(b),f,'250',str(SR)],capture_output=True,text=True); assert r.returncode==0,r.stderr[-800:]
    return np.fromfile(f,np.float32).reshape(-1,2).astype(float)
def db(e): return 10*math.log10(e+1e-30)
def itd_ms(x):
    L,R=x[:,0],x[:,1]; n=len(L); c=np.fft.irfft(np.fft.rfft(L,2*n)*np.conj(np.fft.rfft(R,2*n))); m=int(0.0015*SR)
    c=np.concatenate([c[-m:],c[:m+1]]); k=int(np.argmax(c))-m; return round(k/SR*1e3,3)  # >0: L lags R (sound from right)
N0={}
res={}
faces={'A':'Left wall (-X)','B':'Front (+Z)','C':'Right wall (+X)','D':'Back (-Z)','E':'Floor','F':'Ceiling'}
for mode in ('none',)+tuple(faces):
    b=copy.deepcopy(base)
    if mode!='none': b['surfaces_solo']=mode
    row={}
    for eng in ('play','render'):
        if eng=='play': x,p=play(b,mode)
        else: x=render(b,mode)
        n0=N0.setdefault(eng,int(np.argmax(np.abs(x).sum(1))))
        x=x[n0+int(0.0015*SR):n0+int(0.060*SR)]
        eL=float(np.sum(x[:,0]**2)); eR=float(np.sum(x[:,1]**2))
        row[eng]=dict(total_db=round(db(eL+eR),2), ild_L_minus_R_db=round(db(eL)-db(eR),2), itd_ms=itd_ms(x))
    res[mode]=row; print(mode, faces.get(mode,''), json.dumps(row), flush=True)
# per-mic (L/C/R capsules) for Play: mute two of three mics
for mode in ('A','C'):
    for mic in 'lcr':
        b=copy.deepcopy(base); b['surfaces_solo']=mode
        for m in 'lcr':
            if m!=mic: b['mute_'+m]=True
        x,p=play(b,f'{mode}_{mic}only'); x=x[N0['play']+int(0.0015*SR):N0['play']+int(0.060*SR)]; res.setdefault('per_mic_play',{})[f'{mode}_{mic}']=round(db(float(np.sum(x**2))),2)
print('per mic', res['per_mic_play'])
json.dump(res,open(f'{HERE}/solo_dir_{TAG}.json','w'),indent=1)
