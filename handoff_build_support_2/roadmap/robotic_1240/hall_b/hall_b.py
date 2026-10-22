import json, subprocess, os, sys, copy, numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); R=os.path.dirname(HERE); sys.path.insert(0,R)
from bisect_lib import metrics
import hall as HL
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
SW=B+'/snapshot_2026-10-02_1140/software'; FW=R+'/fixwasm/'; W=HERE+'/w'; os.makedirs(W,exist_ok=True)
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
big=dict(copy.deepcopy(base),W=57.0,H=34.241,L=97.0,sx=24.925,sz=72.083,mcx=28.5,mcz=24.25)
hallp=HL.body('1140',{},True)
SC={'bigroom_default_surfaces':big,'hall_preset_parity':hallp}
FDN={"direct_wet":0,"early_wet":0}
res={}
def run(sc,b,cap,wasm,sr=48000,mode='ir',args=('6',),tag=None):
    tag=tag or f'{sc}_cap{cap}_{os.path.basename(wasm)[:-5]}_{sr}'
    pj=f'{W}/p_{sc}_cap{cap}_{sr}.json'
    env=dict(os.environ); 
    if cap: env['DIFCAP']=str(cap)
    else: env.pop('DIFCAP',None)
    if not os.path.exists(pj):
        r=subprocess.run([P,HERE+'/dump_params_cap.py',SW,json.dumps(b),pj,str(sr)],capture_output=True,text=True,env=env); assert r.returncode==0,r.stderr[-500:]
    f=f'{W}/{mode}_{tag}.f32'
    r=subprocess.run(['node',R+'/wasm_run_file.js' if mode=='file' else LIB+'/wasm_run.js',SW,pj,json.dumps(FDN),mode,*args,f],capture_output=True,text=True,env=dict(os.environ,WASM=wasm)); assert r.returncode==0,r.stderr[-500:]
    return np.fromfile(f,np.float32).reshape(-1,2).astype(float), json.load(open(pj))
if __name__=='__main__':
    for sc,b in SC.items():
        for cap in (None,50,18):
            for wn in ('ship','osign'):
                x,p=run(sc,b,cap,FW+wn+'.wasm')
                m=metrics(x); d=np.abs(np.array(p['buses']['c']['dffs']))
                m.update(dffs_abs_median=round(float(np.median(d)),3),dffs_abs_max=round(float(d.max()),3),rms_db=round(float(10*np.log10(np.mean(x[int(.05*48000):]**2))),2))
                res[f'{sc}|cap{cap}|{wn}']=m; print(sc,cap,wn,json.dumps(m),flush=True)
    json.dump(res,open(HERE+'/hall_b.json','w'),indent=1)
