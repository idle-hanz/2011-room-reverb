import json, subprocess, numpy as np, os
LIB=os.path.abspath('render_ir_compat.py')
PY='/workspace/scratch_er_dropout/venv/bin/python'
body=json.load(open('../../s4_verify_1140/measure/client_body_1140.json'))
body.update(direct_wet=0,early_wet=0,fdn_wet=1,dry_gain=0)
sr=44100; res={}; ref=None
def acm(h):
    o=[]
    for ch in range(2):
        F=np.fft.rfft(h[:,ch],1<<18); ac=np.fft.irfft(np.abs(F)**2); ac/=ac[0]
        o.append({lag:round(float(np.max(ac[int((lag-0.1)*sr/1000):int((lag+0.1)*sr/1000)])),3) for lag in (9.67,19.34,29.0,38.68)})
    return o
for s in ['2026-10-01_0736','2026-10-01_1550','2026-10-01_2210','2026-10-02_0615','2026-10-02_0709','2026-10-02_0830','2026-10-02_1140']:
    sw=f'/workspace/build_support_2/snapshot_{s}/software'; out=os.path.abspath(f'w_bis_{s}.f32')
    if not os.path.exists(out):
        r=subprocess.run([PY,LIB,sw,json.dumps(body),out,'1500',str(sr)],capture_output=True,text=True)
        if r.returncode: res[s]={'error':r.stderr[-300:]}; print(s,'ERR',r.stderr[-300:]); continue
    h=np.fromfile(out,np.float32).reshape(-1,2).astype(float)
    res[s]={'ac':acm(h)}
    print(s,res[s],flush=True)
h1=np.fromfile(os.path.abspath('w_bis_2026-10-02_1140.f32'),np.float32).reshape(-1,2)
for s in res:
    if 'ac' in res[s]:
        h=np.fromfile(os.path.abspath(f'w_bis_{s}.f32'),np.float32).reshape(-1,2); n=min(len(h),len(h1))
        res[s]['maxdiff_vs_1140_rel']=float(np.max(np.abs(h[:n]-h1[:n]))/np.max(np.abs(h1)))
        print(s,'diff',res[s]['maxdiff_vs_1140_rel'])
json.dump(res,open('bisect_render.json','w'),indent=1)
