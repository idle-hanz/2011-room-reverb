import json, subprocess, os, numpy as np
B='/workspace/build_support_2'; NEW=B+'/snapshot_2026-10-02_0615/software'; OLD=B+'/snapshot_2026-10-01_2210/software'
L=B+'/3_phase_acceptance_tests/harness/lib'; PY='/workspace/scratch_er_dropout/venv/bin/python'
def dump(sw,over,tag):
    pj=os.path.abspath(tag+'.json'); subprocess.run([PY,L+'/dump_params.py',sw,json.dumps(over),pj,'48000'],check=True,capture_output=True); return pj
def play(sw,pj,over,secs,tag):
    out=os.path.abspath(tag+'.f32'); subprocess.run(['node',L+'/wasm_run.js',sw,pj,json.dumps(over),'ir',str(secs),out],check=True,capture_output=True,env=dict(os.environ,WASM=sw+'/static/wasm/live_stereo.wasm'))
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float)
N=1<<17; fr=np.fft.rfftfreq(N,1/48000)
def band(x,lo,hi):
    X=np.abs(np.fft.rfft(x[:,0],N))**2+np.abs(np.fft.rfft(x[:,1],N))**2; m=(fr>=lo)&(fr<hi); return float(10*np.log10(X[m].mean()+1e-30))
def rms(x): return float(10*np.log10(np.mean(x**2)+1e-30))
base={"decay_lock":True,"decay_s":1.8,"early_wet":1.0,"air_lp":0.0}
res={}
# sweep (early+fdn, direct off so only air-affected paths)
sweep={}
H=[0.0,0.02,0.05,0.1,0.2,0.3,0.35,0.4,0.5,0.65,0.8,0.9,1.0]
for h in H:
    pj=dump(NEW,dict(base,humidity=h),f'n_h{h}')
    x=play(NEW,pj,{"direct_wet":0},1.0,f'n_h{h}')
    sweep[h]={'hf8_16k_db':round(band(x,8000,16000),3),'b4_8k_db':round(band(x,4000,8000),3),'b2_4k_db':round(band(x,2000,4000),3),'rms_db':round(rms(x),3)}
res['play_sweep_new_direct_off_1s']=sweep
v=[sweep[h]['hf8_16k_db'] for h in H[1:]]
res['play_sweep_hf_increasing_steps(h>0)']=int(np.sum(np.diff(v)>1e-3))
# bit-exact h0 new vs old, and default 0.35 vs old
for h in (0.0,0.35,0.5):
    pn=dump(NEW,dict(base,humidity=h),f'cmpn_{h}'); po=dump(OLD,dict(base,humidity=h),f'cmpo_{h}')
    r={}
    for nm,ov in (('mix',{}),('direct',{"early_wet":0,"fdn_wet":0}),('early',{"direct_wet":0,"fdn_wet":0}),('fdn',{"direct_wet":0,"early_wet":0})):
        a=play(NEW,pn,ov,1.5,f'cn_{h}_{nm}'); b=play(OLD,po,ov,1.5,f'co_{h}_{nm}')
        X=10*np.log10(np.abs(np.fft.rfft(a[:,0],N))**2+1e-30); Y=10*np.log10(np.abs(np.fft.rfft(b[:,0],N))**2+1e-30)
        # 1/3-oct smoothed difference 100-16k
        cs=[]; 
        for fc in 1000*2**(np.arange(-10,5)/3):
            m=(fr>=fc/2**(1/6))&(fr<fc*2**(1/6))
            cs.append(10*np.log10(np.mean(10**(X[m]/10))/np.mean(10**(Y[m]/10))))
        r[nm]={'maxabs':float(np.max(np.abs(a-b))),'rms_new_db':round(rms(a),3),'rms_old_db':round(rms(b),3),'third_oct_max_absdiff_db_100_16k':round(float(np.max(np.abs(cs))),3),'hf_new':round(band(a,8000,16000),3),'hf_old':round(band(b,8000,16000),3)}
    res[f'new_vs_2210_h{h}']=r
# direct air-free in Play
pdz=play(NEW,dump(NEW,dict(base,humidity=0.0),'d0'),{"early_wet":0,"fdn_wet":0},0.2,'pd0')
for h in (0.35,1.0):
    p=play(NEW,dump(NEW,dict(base,humidity=h),f'd{h}'),{"early_wet":0,"fdn_wet":0},0.2,f'pd{h}')
    res[f'play_direct_h{h}_vs_h0_maxabs']=float(np.max(np.abs(p-pdz)))
json.dump(res,open('play_checks.json','w'),indent=1)
print(json.dumps(res,indent=1))
