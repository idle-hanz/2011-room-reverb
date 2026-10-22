"""S4b item 1: passivity of the in-loop axial peaking biquads as Play sees them (float32-packed b0,b1,a1,a2; b2 restored in double
exactly like live_stereo.c load_core_body), 0 Hz..Nyquist (0, 0.001-20 Hz step 0.001 Hz, 20 Hz-Nyquist log 20000 pts)."""
import json, subprocess, numpy as np, copy
P='/workspace/scratch_er_dropout/venv/bin/python'; B='/workspace/build_support_2'; SW=B+'/snapshot_2026-10-02_1630/software'
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
hallp=dict(W=57,H=34.241,L=97,sx=24.925,sz=72.083,sy=1.88,my=1.9,mcz=24.25,space=0.25,reaktor_parity=True,car_omni=0.764,early_wet=1.0,fdn_wet=1,direct_wet=1,dry_gain=0,fdn_g=1,decay_lock=False,hadamard_n=32,humidity=0.5,mcx=28.5)
rooms={'default_6x3x8':{},'hall_57x34.2x97':dict(W=57.0,H=34.2,L=97.0,sx=24.0,sz=60.0,mcx=28.5,mcz=30.0),'hall_57x34.2x97_decay8':dict(W=57.0,H=34.2,L=97.0,sx=24.0,sz=60.0,mcx=28.5,mcz=30.0,decay_lock=True,decay_s=8.0),
       'Hall_preset':hallp,'default_binaural':{'mic_setup':'binaural'},'hall_binaural':dict(W=57.0,H=34.2,L=97.0,sx=24.0,sz=60.0,mcx=28.5,mcz=30.0,mic_setup='binaural')}
def Hf(c,f,sr):
    z=np.exp(-2j*np.pi*f/sr); return (c[0]+c[1]*z+c[2]*z*z)/(1+c[3]*z+c[4]*z*z)
res={}; worst=0.0
for rn,ov in rooms.items():
  for sr in (44100,48000):
    b=copy.deepcopy(base); b.update(ov)
    subprocess.run([P,B+'/3_phase_acceptance_tests/harness/lib/dump_params.py',SW,json.dumps(b),'/tmp/pk16.json',str(sr)],check=True,capture_output=True)
    pk=json.load(open('/tmp/pk16.json'))['peaking']
    f=np.concatenate([[0.0],np.arange(0.001,20.0,0.001),np.geomspace(20,sr/2,20000)])
    for ax,q in zip('XYZ',pk):
        if not q.get('on'): res[f'{rn}|{sr}|{ax}']='off'; continue
        c32=np.array([q['b0'],q['b1'],q['b2'],q['a1'],q['a2']],dtype=np.float32).astype(np.float64)
        cr=c32.copy(); cr[2]=1.0+cr[3]+cr[4]-cr[0]-cr[1]
        h=np.abs(Hf(cr,f,sr)); h0=np.abs(Hf(c32,f,sr))
        row=dict(max_restored=float(h.max()),f_at_max=float(f[np.argmax(h)]),dc_restored=float(h[0]),max_without_restore=float(h0.max()),dc_without_restore=float(h0[0]),pass_1e9=bool(h.max()<=1+1e-9))
        worst=max(worst,row['max_restored']); res[f'{rn}|{sr}|{ax}']=row; print(rn,sr,ax,{k:(round(v,9) if isinstance(v,float) else v) for k,v in row.items()},flush=True)
res['_worst_max_restored']=worst; print('worst',worst)
json.dump(res,open('passivity.json','w'),indent=1)
