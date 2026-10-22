import sys, json, subprocess, numpy as np, os
SW='/workspace/build_support_2/snapshot_2026-10-02_1140/software'
LIB='/workspace/build_support_2/3_phase_acceptance_tests/harness/lib/render_ir.py'
PY='/workspace/scratch_er_dropout/venv/bin/python'
body=json.load(open('../../s4_verify_1140/measure/client_body_1140.json'))
def rir(over, name, ms=1500, sr=44100):
    b=dict(body); b.update(over); out=os.path.abspath(f'w_{name}.f32')
    if not os.path.exists(out):
        r=subprocess.run([PY,LIB,SW,json.dumps(b),out,str(ms),str(sr)],capture_output=True,text=True)
        if r.returncode: print(r.stderr[-800:]); return None
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float)
def acpeaks(h,sr=44100,skip_ms=0):
    h=h[int(skip_ms*sr/1000):]
    out=[]
    for ch in range(2):
        F=np.fft.rfft(h[:,ch],1<<18); ac=np.fft.irfft(np.abs(F)**2)[:int(0.06*sr)]; ac/=ac[0]
        l0=int(0.002*sr); i=np.argsort(np.abs(ac[l0:]))[::-1][:6]+l0
        out.append([(round(j/sr*1000,2),round(float(ac[j]),3)) for j in sorted(i)])
    return out
if __name__=='__main__':
    scenes=json.loads(sys.argv[1])
    for name,over in scenes.items():
        h=rir(over,name)
        if h is None: continue
        print(name,'full',acpeaks(h)); print(name,'after50ms',acpeaks(h,skip_ms=50))
