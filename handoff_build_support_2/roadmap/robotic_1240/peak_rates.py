"""float32 storage of the in-loop axial peaking biquads: DC gain and max|H| per axis, per rate, ship vs DC fix."""
import json, subprocess, numpy as np
P='/workspace/scratch_er_dropout/venv/bin/python'; B='/workspace/build_support_2'
rooms={'hall_57x34.2x97':dict(W=57.0,H=34.2,L=97.0,sx=24.0,sz=60.0,mcx=28.5,mcz=30.0),'default_6x3x8':{}}
def H(c,f,sr):
    z=np.exp(-2j*np.pi*f/sr); return (c[0]+c[1]*z+c[2]*z*z)/(1+c[3]*z+c[4]*z*z)
res={}
for rn,ov in rooms.items():
  for sr in (44100,48000):
    b=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); b.update(ov)
    subprocess.run([P,B+'/3_phase_acceptance_tests/harness/lib/dump_params.py',B+'/snapshot_2026-10-02_1140/software',json.dumps(b),'/tmp/pk.json',str(sr)],check=True,capture_output=True)
    pk=json.load(open('/tmp/pk.json'))['peaking']
    for ax,q in zip('XYZ',pk):
        c64=np.array([q['b0'],q['b1'],q['b2'],q['a1'],q['a2']]); c32=c64.astype(np.float32).astype(np.float64)
        cf=c32.copy(); cf[2]=1+cf[3]+cf[4]-cf[0]-cf[1]
        f=np.concatenate([np.linspace(0,20,20001),np.geomspace(20,20000,2000)])
        row={}
        for nm,c in (('f64',c64),('f32_ship',c32),('f32_dcfix',cf)):
            h=np.abs(H(c,f,sr)); row[nm]=dict(dc=round(float(abs(H(c,np.array([0.0]),sr)[0])),6),max=round(float(h.max()),6),f_at_max=round(float(f[np.argmax(h)]),2),at_1Hz=round(float(abs(H(c,np.array([1.0]),sr)[0])),6))
        res[f'{rn}|{sr}|{ax}']=row; print(rn,sr,ax,row)
json.dump(res,open('peak_rates.json','w'),indent=1)
