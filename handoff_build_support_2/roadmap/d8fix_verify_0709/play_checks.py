import json, subprocess, os, numpy as np
B='/workspace/build_support_2'; NEW=B+'/snapshot_2026-10-02_0709/software'; OLD=B+'/snapshot_2026-10-02_0615/software'
L=B+'/3_phase_acceptance_tests/harness/lib'; PY='/workspace/scratch_er_dropout/venv/bin/python'
def dump(sw,over,tag):
    pj=os.path.abspath('tmp_'+tag+'.json'); subprocess.run([PY,L+'/dump_params.py',sw,json.dumps(over),pj,'48000'],check=True,capture_output=True); return pj
def play(sw,pj,over,secs,tag):
    out=os.path.abspath('tmp_'+tag+'.f32'); subprocess.run(['node',L+'/wasm_run.js',sw,pj,json.dumps(over),'ir',str(secs),out],check=True,capture_output=True,env=dict(os.environ,WASM=sw+'/static/wasm/live_stereo.wasm'))
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float)
N=1<<18; fr=np.fft.rfftfreq(N,1/48000)
def spec(x): return sum(np.abs(np.fft.rfft(x[:,i],N))**2 for i in (0,1))
def third(X,fc): m=(fr>=fc/2**(1/6))&(fr<fc*2**(1/6)); return X[m].mean()
def band(x,lo,hi):
    X=spec(x); m=(fr>=lo)&(fr<hi); return float(10*np.log10(X[m].mean()+1e-30))
def rms(x): return float(10*np.log10(np.mean(x**2)+1e-30))
SC={'std_lock18 (page default room)':{"decay_lock":True,"decay_s":1.8,"humidity":0.35,"early_wet":1.0},
    'hall_lock40 (20x10x30 m)':{"decay_lock":True,"decay_s":4.0,"humidity":0.35,"W":20,"H":10,"L":30,"sx":10,"sz":18,"mcx":10,"mcz":6},
    'reaktor_snapshot (57x34x97, parity, humidity 0.5, air_lp 0.25)':{"W":57,"H":34.241,"L":97,"sx":24.925,"sz":72.083,"sy":1.88,"my":1.9,"mcz":24.25,"space":0.25,"reaktor_parity":True,"car_omni":0.764,"early_wet":1.0,"fdn_wet":1,"direct_wet":1,"dry_gain":0,"fdn_g":1,"decay_lock":False,"ir_length_ms":1500,"humidity":0.5,"air_lp":0.25,"air_shelf":1,"diffusion_master":-0.5}}
res={'darker':{}}
for name,sc in SC.items():
    r={}
    secs=3.0 if 'hall' in name or 'reaktor' in name else 1.5
    pn=dump(NEW,sc,'dn'); po=dump(OLD,sc,'do')
    for comp,ov in (('mix',{}),('early',{"direct_wet":0,"fdn_wet":0}),('fdn',{"direct_wet":0,"early_wet":0}),('direct',{"early_wet":0,"fdn_wet":0,"_d":1})):
        ov2={k:v for k,v in ov.items() if k!='_d'}
        if comp=='direct': ov2={"early_wet":0,"fdn_wet":0}
        a=play(NEW,pn,ov2,secs,'a'); b=play(OLD,po,ov2,secs,'b')
        if comp=='early' and np.max(np.abs(b))==0: r[comp]='silent'; continue
        A=spec(a); Bs=spec(b)
        r[comp]={f'{fc//1000}k_db':round(float(10*np.log10(third(A,fc)/third(Bs,fc))),2) for fc in (1000,2000,4000,8000,16000)}
        r[comp]['rms_db']=round(rms(a)-rms(b),2)
    res['darker'][name]=r
# sweep + bit-exact + direct
H=[0.0,0.02,0.1,0.2,0.35,0.5,0.65,0.8,1.0]; sw={}
base={"decay_lock":True,"decay_s":1.8,"early_wet":1.0,"air_lp":0.0}
for h in H:
    x=play(NEW,dump(NEW,dict(base,humidity=h),'s'),{"direct_wet":0},1.0,'s'); sw[h]=round(band(x,8000,16000),3)
res['play_sweep_8_16k_db_direct_off']=sw
v=[sw[h] for h in H[1:]]; res['play_sweep_steps_up']=int(np.sum(np.diff(v)>1e-3))
for sc in ('lock','unl'):
    b2=base if sc=='lock' else {"decay_lock":False,"fdn_g":0.8,"early_wet":1.0}
    a=play(NEW,dump(NEW,dict(b2,humidity=0.0),'z1'),{},1.5,'z1'); b=play(OLD,dump(OLD,dict(b2,humidity=0.0),'z2'),{},1.5,'z2')
    res[f'h0_new_vs_0615_{sc}_maxabs']=float(np.max(np.abs(a-b)))
pz=play(NEW,dump(NEW,dict(base,humidity=0.0),'d0'),{"early_wet":0,"fdn_wet":0},0.3,'d0')
for h in (0.35,1.0):
    p=play(NEW,dump(NEW,dict(base,humidity=h),'dh'),{"early_wet":0,"fdn_wet":0},0.3,'dh'); res[f'play_direct_h{h}_vs_h0_maxabs']=float(np.max(np.abs(p-pz)))
# parity at humidity 0 bit-exact vs 0615
rs=dict(SC['reaktor_snapshot (57x34x97, parity, humidity 0.5, air_lp 0.25)'],humidity=0.0)
a=play(NEW,dump(NEW,rs,'p1'),{},1.5,'p1'); b=play(OLD,dump(OLD,rs,'p2'),{},1.5,'p2'); res['parity_h0_new_vs_0615_maxabs']=float(np.max(np.abs(a-b)))
json.dump(res,open('play_checks.json','w'),indent=1); print(json.dumps(res,indent=1))
for f in os.listdir('.'):
    if f.startswith('tmp_'): os.remove(f)
