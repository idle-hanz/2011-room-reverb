# Bit-exactness checks for S4b (box, 2 Oct 16:3x). Play via harness wasm_run.js; Render via render_ir.py.
import json, subprocess, os, sys
import numpy as np
B='/workspace/build_support_2'; PY='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
S16=B+'/snapshot_2026-10-02_1630/software'; S11=B+'/snapshot_2026-10-02_1140/software'; W=B+'/work/s4b_1630/w'; H=os.path.dirname(os.path.abspath(__file__))
WA={'ship1630':S16+'/static/wasm/live_stereo.wasm','ship1140':S11+'/static/wasm/live_stereo.wasm','s':W+'/s.wasm','nocsign':W+'/nocsign.wasm','noskip':W+'/noskip.wasm'}
big=dict(W=57.0,H=34.2,L=97.0,sx=24.0,sz=60.0,mcx=28.5,mcz=30.0)
SC={'def_1src':{}, 'def_2src':{'two_sources':True}, 'def_decay8':{'decay_lock':True,'decay_s':8.0}, 'def_2src_decay8':{'two_sources':True,'decay_lock':True,'decay_s':8.0},
    'bin_def_1src':{'mic_setup':'binaural'}, 'bin_def_2src':{'mic_setup':'binaural','two_sources':True}, 'bin_big':{**big,'mic_setup':'binaural'},
    'parity_1src':{'reaktor_parity':True}, 'parity_2src':{'reaktor_parity':True,'two_sources':True}}
OV={'page':{}, 'allon':{'early_wet':1.0,'direct_wet':1.0}, 'allon_nocol':{'early_wet':1.0,'direct_wet':1.0,'colour_on':False}}
def params(sw,k,sr=48000):
    out=f'{H}/p_{os.path.basename(os.path.dirname(sw))}_{k}_{sr}.json'
    if not os.path.exists(out): subprocess.run([PY,LIB+'/dump_params.py',sw,json.dumps(SC[k]),out,str(sr)],check=True,capture_output=True)
    return out
def play(w,sw,k,ov,secs=2.5):
    out=f'/tmp/bx_{w}_{os.path.basename(os.path.dirname(sw))}_{k}_{ov}.f32'
    subprocess.run(['node',LIB+'/wasm_run.js',sw,params(sw,k),json.dumps(OV[ov]),'ir',str(secs),out],check=True,capture_output=True,env=dict(os.environ,WASM=WA[w]))
    return np.fromfile(out,np.float32)
def md(a,b):
    if a.size!=b.size: return 'size'
    return float(np.max(np.abs(a.astype(float)-b.astype(float))))
res={}
def rec(name,a,b):
    res[name]={'max_abs_diff':md(a,b),'peak':float(np.max(np.abs(a)))}; print(name,res[name],flush=True)
for k in SC:
    for ov in OV:
        sec=4.0 if 'decay8' in k else 2.5
        A=play('ship1630',S16,k,ov,sec); Bs=play('s',S16,k,ov,sec)
        rec(f'shipped1630_vs_boxbuild|{k}|{ov}',A,Bs)
        if k.startswith('parity'):
            rec(f'parity_1630_vs_1140|{k}|{ov}',A,play('ship1140',S11,k,ov,sec))
        else:
            rec(f'nocsign1630_vs_1140|{k}|{ov}',play('nocsign',S16,k,ov,sec),play('ship1140',S11,k,ov,sec))
        if k.startswith('bin'):
            rec(f'skipc_vs_noskip|{k}|{ov}',A,play('noskip',S16,k,ov,sec))
json.dump(res,open(H+'/bitexact.json','w'),indent=1)
