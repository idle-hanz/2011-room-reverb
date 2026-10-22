import json, subprocess, os, sys, numpy as np, time
PY='/workspace/scratch_er_dropout/venv/bin/python'; SW='/workspace/audit_1852/software'; HERE='/workspace/audit_1852/heights'
JS='/workspace/build_support_2/roadmap/s7_verify_1905/t19/bench_blocks.js'
t19={"decay_lock": True, "decay_s": 1.8, "humidity": 0.5, "early_wet": 1.0,'source_radiation':'talking_head','source_radiation_b':'trumpet_byu','source_yaw':35.0,'source_yaw_b':-25.0,'two_sources':True}
V={}
for sh in (False,True):
    for hn,ho in (('flat',{}),('tilt',dict(my_l=1.2,my_r=1.8,my_c=1.5))):
        b=dict(t19,shared_tail=sh,**ho); f=f'{HERE}/b_{hn}_{"on" if sh else "off"}.json'
        r=subprocess.run([PY,HERE+'/dump_params_h.py',SW,json.dumps(b),f,'48000'],capture_output=True,text=True)
        if r.returncode: print(r.stderr[-600:]); sys.exit(1)
        V[f'{hn}_{"on" if sh else "off"}']=f
rounds=int(sys.argv[1]); R={k:[] for k in V}
def med(f):
    out=subprocess.run(['node',JS,SW,f,'{}','bench','4','10'],capture_output=True,text=True,env=dict(os.environ,WASM=SW+'/static/wasm/live_stereo.wasm')).stdout
    j=json.loads(out); return float(np.median(j['play_blocks'])), float(np.mean(j['play_blocks']))
for r in range(rounds):
    for sh in ('off','on'):
        pair=[f'flat_{sh}',f'tilt_{sh}']
        for n in (pair if r%2==0 else pair[::-1]): R[n].append(med(V[n]))
    print(r,{k:round(v[-1][0],4) for k,v in R.items()},flush=True)
S={}
for sh in ('off','on'):
    a=np.array([x[0] for x in R[f'flat_{sh}']]); b=np.array([x[0] for x in R[f'tilt_{sh}']])
    S[sh]={'flat_median_ms':round(float(np.median(a)),4),'tilt_median_ms':round(float(np.median(b)),4),'paired_pct_median':round(float(np.median(100*(b/a-1))),2),'paired_pct_all':[round(float(x),2) for x in 100*(b/a-1)]}
print(json.dumps(S,indent=1)); json.dump({'summary':S,'raw':R},open(HERE+'/bench_heights.json','w'),indent=1)
