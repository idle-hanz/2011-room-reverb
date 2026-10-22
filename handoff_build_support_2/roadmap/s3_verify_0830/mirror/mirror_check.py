import json, subprocess, sys, os, math
import numpy as np
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'
LIB=B+'/3_phase_acceptance_tests/harness/lib'; HERE=os.path.dirname(os.path.abspath(__file__))
SW=sys.argv[1] if len(sys.argv)>1 else B+'/snapshot_2026-10-02_0830/software'
tag=sys.argv[2] if len(sys.argv)>2 else '0830'
room=json.loads(sys.argv[3]) if len(sys.argv)>3 else {}
sys.path[:0]=[SW,SW+'/engine']; os.chdir(SW)
import app_server as A
base=dict(decay_lock=True, decay_s=1.8, humidity=0.5, early_wet=1.0, two_sources=True, mirror_b=True,
          source_radiation='violin_byu')
base.update(room)
p=A.params_from_body(dict(A.DEFAULTS, **base)); geo=A.geometry_payload(p)
s,m=geo['source'],geo['mic_centre']
yaw=math.degrees(math.atan2(m['x']-s['x'], m['z']-s['z'])); pitch=math.degrees(math.atan2(m['y']-s['y'], math.hypot(m['x']-s['x'], m['z']-s['z'])))
base.update(source_yaw=round(yaw,2), source_pitch=round(pitch,2))
print(tag,'A at',s,'B at',geo.get('source_b'),'mic',m,'face yaw/pitch',round(yaw,2),round(pitch,2), flush=True)
V={'ui_0830': dict(source_radiation_b='omni', source_yaw_b=None, source_pitch_b=0),   # what the 0830 client sends
   'intended': {},                                                                     # B inherits A preset, mirrored yaw
   'explicit_b': dict(source_radiation_b='violin_byu', source_yaw_b=round(-yaw,2), source_pitch_b=round(pitch,2)),
   'all_omni': dict(source_radiation='omni', source_radiation_b='omni')}
SR=48000; WIN=int(float(os.environ.get('WINMS','60'))*SR/1000)
def play(body, bal, key):
    pj=f'{HERE}/p_{tag}_{key}_{bal}.json'; out=f'{HERE}/play_{tag}_{key}_{bal}.f32'
    subprocess.run([P,LIB+'/dump_params.py',SW,json.dumps(dict(body,source_balance=bal)),pj,str(SR)],check=True,capture_output=True)
    subprocess.run(['node',LIB+'/wasm_run.js',SW,pj,'{}','ir','0.5',out],check=True,capture_output=True)
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float)
def render(body, bal, key):
    out=f'{HERE}/rend_{tag}_{key}_{bal}.f32'
    subprocess.run([P,HERE+'/render_ir2.py',SW,json.dumps(dict(body,source_balance=bal)),out,'500',str(SR)],check=True,capture_output=True)
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float)
def bands(x):
    X=np.abs(np.fft.rfft(x[:WIN]*np.hanning(WIN),8192)); f=np.fft.rfftfreq(8192,1/SR)
    return {fc: round(10*math.log10(np.sum(X[(f>=fc/2**.5)&(f<fc*2**.5)]**2)+1e-30),2) for fc in (500,1000,2000,4000,8000)}
res={}
for eng,fn in (('play',play),('render',render)):
    irs={}
    for k,ov in V.items():
        body=dict(base,**ov)
        irs[k,'A']=fn(body,-1.0,k); irs[k,'B']=fn(body,1.0,k)
    for k in V:
        a,b=irs[k,'A'],irs[k,'B']; n0=int(np.argmax(np.abs(a[:,0])+np.abs(a[:,1])))
        st=max(0,n0-int(0.002*SR))
        aw,bw=a[st:st+WIN],b[st:st+WIN]
        swap_null=20*math.log10(np.max(np.abs(bw[:,0]-aw[:,1]))/np.max(np.abs(aw))+1e-30)
        bo=irs['all_omni','B'][st:st+WIN]
        diff_omni=20*math.log10(np.max(np.abs(bw-bo))/np.max(np.abs(bo))+1e-30)
        bA_R=bands(aw[:,1]); bB_L=bands(bw[:,0]); bBo=bands(bo[:,0])
        res[f'{eng}|{k}']={'swap_null_db(B.L-A.R, 60ms)':round(swap_null,1),'B_vs_allomniB_db':round(diff_omni,1),
            'bands_B.L_minus_A.R':{f:round(bB_L[f]-bA_R[f],2) for f in bA_R},'bands_B.L_minus_omniB.L':{f:round(bB_L[f]-bBo[f],2) for f in bA_R}}
        print(eng,k,json.dumps(res[f'{eng}|{k}']),flush=True)
json.dump(dict(base=base,variants=V,results=res),open(f'{HERE}/mirror_{tag}.json','w'),indent=1)
