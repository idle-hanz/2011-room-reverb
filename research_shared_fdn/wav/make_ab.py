# A/B WAVs: dry test file convolved with each variant's stereo IR (rendered by the same wasm through the Play driver).
# Loudness matched per scene to -20 LUFS (BS.1770-4 integrated, own implementation), common trim if any peak > -1 dBFS.
import json, subprocess, os, math
import numpy as np, soundfile as sf
from scipy import signal
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
SW=B+'/snapshot_2026-10-02_0830/software'; H=os.path.dirname(os.path.abspath(__file__)); PRO=B+'/research_shared_fdn/proto'; SR=48000
V={'A_today':PRO+'/v3/m0.wasm','B_shared':PRO+'/v3/cand.wasm','C_shared_nojitter':PRO+'/v3/m1.wasm','D_shared_fixeddecor':PRO+'/v3/fx.wasm'}
base=dict(toe_half_deg=55, space=0.17, decay_lock=True, decay_s=1.8, humidity=0.5, early_wet=1.0, mirror_b=True, source_radiation='violin_byu', source_yaw=180.0)
big=dict(W=57.0,H=34.2,L=97.0, sx=24.0, sz=60.0, mcx=28.5, mcz=30.0, decay_s=4.0)
S={'1_default_ortf':(base,4,['A_today','B_shared','C_shared_nojitter']),
   '2_big_room_ortf':({**base,**big},8,['A_today','B_shared','C_shared_nojitter']),
   '3_binaural_default':({**base,'mic_setup':'binaural'},4,['A_today','B_shared']),
   '4_binaural_big':({**base,**big,'mic_setup':'binaural'},8,['A_today','B_shared']),
   '5_symmetric_hall_mono_tail':({**base,'decay_s':4.0,'W':20,'H':10,'L':30,'sx':10,'sz':18,'mcx':10,'mcz':6},6,['A_today','B_shared','D_shared_fixeddecor'])}
TAIL={'early_wet':0,'direct_wet':0,'dry_gain':0}
def kw(x):
    # BS.1770 K-weighting at 48 kHz (published coefficients)
    x=signal.lfilter([1.53512485958697,-2.69169618940638,1.19839281085285],[1,-1.69065929318241,0.73248077421585],x,axis=0)
    return signal.lfilter([1.0,-2.0,1.0],[1,-1.99004745483398,0.99007225036621],x,axis=0)
def lufs(y):
    z=kw(y); n=int(0.4*SR); hop=n//4; bl=[]
    for s in range(0,len(z)-n,hop): bl.append(np.sum(np.mean(z[s:s+n]**2,axis=0)))
    bl=np.array(bl); L=-0.691+10*np.log10(bl+1e-30); g=bl[L>-70]
    rel=-0.691+10*np.log10(np.mean(g))-10; g2=bl[(L>-70)&(L>rel)]
    return -0.691+10*np.log10(np.mean(g2))
dry,_=sf.read(H+'/dry_test_48k.wav'); rep={}
for k,(body,secs,vs) in S.items():
    pj=f'{H}/p_{k}.json'
    if not os.path.exists(pj): subprocess.run([P,LIB+'/dump_params.py',SW,json.dumps(body),pj,str(SR)],check=True,capture_output=True)
    outs={}
    for v in vs:
        for tag,ov in (('full',{}),('tailonly',TAIL)):
            f=f'{H}/ir_{k}_{v}_{tag}.f32'
            if not os.path.exists(f):
                r=subprocess.run(['node',LIB+'/wasm_run.js',SW,pj,json.dumps(ov),'ir',str(secs),f],capture_output=True,text=True,env=dict(os.environ,WASM=V[v]))
                if r.returncode: raise SystemExit(r.stderr[-400:])
            h=np.fromfile(f,np.float32).reshape(-1,2).astype(float)
            outs[(v,tag)]=np.stack([signal.fftconvolve(dry,h[:,0]),signal.fftconvolve(dry,h[:,1])],1)
    for tag in ('full','tailonly'):
        g={v:10**((-20.0-lufs(outs[(v,tag)]))/20) for v in vs}
        pk=max(np.max(np.abs(outs[(v,tag)]*g[v])) for v in vs); trim=min(1.0,10**(-1/20)/pk)
        for v in vs:
            y=outs[(v,tag)]*g[v]*trim; fn=f'{k}__{tag}__{v}.wav'; sf.write(H+'/'+fn,y.astype(np.float32),SR,subtype='PCM_24')
            rep[fn]={'gain_applied_db':round(20*math.log10(g[v]*trim),2),'raw_lufs':round(lufs(outs[(v,tag)]),2),'final_lufs':round(lufs(y),2),'peak_dbfs':round(20*math.log10(np.max(np.abs(y))),2)}
    print(k,flush=True)
sf.write(H+'/dry_test_48k_stereo_ref.wav',np.stack([dry,dry],1).astype(np.float32),SR,subtype='PCM_24')
json.dump(rep,open(H+'/ab_loudness.json','w'),indent=1)
for f,r in rep.items(): print(f,r)
