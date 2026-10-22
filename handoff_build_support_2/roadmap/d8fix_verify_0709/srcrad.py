import sys, json, os, subprocess, numpy as np
B='/workspace/build_support_2'; sw=B+'/snapshot_2026-10-02_0709/software'; L=B+'/3_phase_acceptance_tests/harness/lib'; PY='/workspace/scratch_er_dropout/venv/bin/python'
sys.path[:0]=[sw,sw+'/engine']; here=os.getcwd(); os.chdir(sw)
import app_server as A
from render_pipeline import render
N=1<<16; fr=np.fft.rfftfreq(N,1/48000)
def thirds(x):
    X=np.abs(np.fft.rfft(x[:,0],N))**2+np.abs(np.fft.rfft(x[:,1],N))**2
    return np.array([X[(fr>=fc/2**(1/6))&(fr<fc*2**(1/6))].mean() for fc in FC])
FC=[250,500,1000,2000,4000,8000]
def rend(over):
    b=dict(A.DEFAULTS); b.update({"sample_rate":48000,"ir_length_ms":100,"early_wet":0.0,"fdn_wet":0.0,"dry_gain":0.0,"humidity":0.0,"colour_mode":"BYPASS"}); b.update(over)
    p=A.params_from_body(b); kw={k:v for k,v in p.items() if k in render.__code__.co_varnames}
    for k in ('source_radiation','source_yaw','source_pitch'):
        if k in b: kw[k]=b[k]
    d=np.zeros(4800); d[0]=1; Lc,Rc,info=render(d,48000,**kw); return np.stack([Lc,Rc],1)
def play(over,tag):
    pj=os.path.join(here,'tmp_'+tag+'.json'); subprocess.run([PY,L+'/dump_params.py',sw,json.dumps(dict(over,humidity=0.0,colour_on=False)),pj,'48000'],check=True,capture_output=True)
    o=os.path.join(here,'tmp_'+tag+'.f32'); subprocess.run(['node',L+'/wasm_run.js',sw,pj,json.dumps({"early_wet":0,"fdn_wet":0,"colour_on":False}),'ir','0.1',o],check=True,capture_output=True,env=dict(os.environ,WASM=sw+'/static/wasm/live_stereo.wasm'))
    return np.fromfile(o,np.float32).reshape(-1,2).astype(float)
res={}
for yaw in (0.0,90.0,180.0):
    sc={"source_radiation":"talking_head","source_yaw":yaw}
    r=10*np.log10(thirds(rend(sc))/thirds(rend({"source_radiation":"omni"})))
    p=10*np.log10(thirds(play(sc,'p'))/thirds(play({"source_radiation":"omni"},'o')))
    res[f'yaw{yaw:g}']={'render_direct_vs_omni_db':dict(zip(map(str,FC),np.round(r,2).tolist())),'play_direct_vs_omni_db':dict(zip(map(str,FC),np.round(p,2).tolist())),'play_minus_render_max_db':round(float(np.max(np.abs(p-r))),2)}
os.chdir(here); [os.remove(f) for f in os.listdir('.') if f.startswith('tmp_')]
json.dump(res,open('srcrad_direct.json','w'),indent=1); print(json.dumps(res,indent=1))
