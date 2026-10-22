import json, sys, wave, time, io, numpy as np, requests
U='http://127.0.0.1:7860'; D='/workspace/audit_1852/'
BASE=dict(W=6,H=3,L=8,sx=2.6,sz=4.75,mcx=3,mcz=1.5,my=1.5,sy=1.2,space=0.17,diverg=1,toe_half_deg=55,car_omni=1,
 pattern_l='cardioid',pattern_c='cardioid',pattern_r='cardioid',family_l='cardioid',family_c='cardioid',family_r='cardioid',
 polar_l=0.5,polar_c=0.5,polar_r=0.5,yaw_l_deg=-55,yaw_c_deg=0,yaw_r_deg=55,mic_setup='ortf',colour_mode='MEASURED_SHELF',colour_impl='sos',
 mic_preset_l='ShureSM57',mic_preset_c='ShureSM57',mic_preset_r='ShureSM57',early_wet=0.0,fdn_wet=1.0,direct_wet=0.0,dry_gain=0.0,fdn_g=1,
 ir_length_ms=1500,decay_s=1.8,decay_lock=True,humidity=0.35,air_lp=0,air_shelf=1,air_climate='studio_20C_50RH',diffusion_master=-0.25,
 hadamard_n=32,diffusion_seed=0,lambda_ref=0.02,mic_gain_l=1,mic_gain_c=1,mic_gain_r=1,mic_pan_l=-1,mic_pan_c=0,mic_pan_r=1,
 mic_phase_l=1,mic_phase_c=1,mic_phase_r=1,source_radiation='omni',capsule_mm=17,mic_response_hz=10000)
CASES={
 'default':{},
 'default_direct_early':dict(direct_wet=1.0,early_wet=1.0),
 'decay_4s':dict(decay_s=4.0),
 'decay_8s':dict(decay_s=8.0),
 'decay_8s_ir2000':dict(decay_s=8.0,ir_length_ms=2000),
 'decay_0p3':dict(decay_s=0.3),
 'studio':dict(W=5.6,H=2.8,L=7.2,sx=2.8,sz=4.6,sy=1.2,my=1.2,mcx=2.8,mcz=1.55),
 'club':dict(W=14,H=5.2,L=22,sx=7,sz=14.5,sy=1.6,my=1.6,mcx=7,mcz=3.4,space=0.25,humidity=0.4),
 'hall_2011':dict(W=57,H=34.241,L=97,sx=24.925,sz=72.083,sy=1.88,my=1.9,mcz=24.25,space=0.25,reaktor_parity=True,car_omni=0.764,direct_wet=1.0,decay_lock=False,humidity=0.5,air_lp=0.25,diffusion_master=-0.5),
 'mono_c':dict(mic_setup='mono_c',space=0,yaw_l_deg=0,yaw_r_deg=0,toe_half_deg=0),
 'ms_classic':dict(mic_setup='ms_classic',space=0.05,family_l='bi',family_r='bi',pattern_l='fig8',pattern_r='fig8',yaw_l_deg=-90,yaw_r_deg=90,toe_half_deg=90,ms_decode=False),
 'binaural':dict(mic_setup='binaural',pattern_l='omni',pattern_r='omni',polar_l=0,polar_r=0,yaw_l_deg=-90,yaw_r_deg=90,space=0.18,car_omni=0),
 'bypass':dict(colour_mode='BYPASS'),
 'hot_faders':dict(fdn_wet=3.98,direct_wet=3.98,early_wet=3.98),
 'had8':dict(hadamard_n=8),'had128':dict(hadamard_n=128),
}
def render(params, wav):
    t=time.time()
    r=requests.post(U+'/api/render',files={'file':('in.wav',open(wav,'rb'),'audio/wav')},data={'params_json':json.dumps(params)},timeout=280)
    j=r.json(); dt=time.time()-t
    if not j.get('ok'): return None, j, dt
    a=requests.get(U+j['preview_url']).content
    with wave.open(io.BytesIO(a)) as w: x=np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,2).astype(float)/32767; sr=w.getframerate()
    return (x,sr), j, dt
def t30(x,sr):
    e=(x**2).sum(1); sch=np.cumsum(e[::-1])[::-1]; sch=10*np.log10(sch/sch[0]+1e-30)
    t=np.arange(len(sch))/sr
    i5=np.argmax(sch<=-5); i35=np.argmax(sch<=-35); i25=np.argmax(sch<=-25)
    out={}
    if i35>i5>0:
        p=np.polyfit(t[i5:i35],sch[i5:i35],1); out['T30']=-60/p[0]
    if i25>i5>0:
        p=np.polyfit(t[i5:i25],sch[i5:i25],1); out['T20']=-60/p[0]
    return out
def main():
  pass
res={}
only=sys.argv[1:] or list(CASES)
if __name__!='__main__': only=[]
for name in only:
    P=dict(BASE); P.update(CASES[name])
    row={}
    for kind,wav in (('impulse',D+'data/impulse_mono.wav'),('burst',D+'data/burst_mono.wav')):
        out,j,dt=render(P,wav)
        if out is None: row[kind]={'error':j.get('error'),'secs':round(dt,1)}; continue
        x,sr=out
        np.save(D+'data/wav_%s_%s.npy'%(name,kind), x.astype(np.float32))
        L,R=x[:,0],x[:,1]
        rms=lambda v: np.sqrt(np.mean(v**2))+1e-20
        tail=x[-int(0.05*sr):]
        d={'secs':round(dt,1),'len_s':round(len(x)/sr,3),'peak':round(float(np.abs(x).max()),4),'clip_n':int((np.abs(x)>=0.99997).sum()),
           'dc_L':float(L.mean()),'dc_R':float(R.mean()),'LR_db':round(20*np.log10(rms(L)/rms(R)),2),
           'corr':round(float(np.corrcoef(L,R)[0,1]),3) if rms(L)>1e-9 and rms(R)>1e-9 else None,
           'last50ms_dbfs':round(20*np.log10(rms(tail)),1),'rms_dbfs':round(20*np.log10(rms(x)),1)}
        # peak level in last 50 ms relative to overall peak
        d['last50ms_rel_peak_db']=round(20*np.log10(rms(tail)/(np.abs(x).max()+1e-20)),1)
        st=j.get('status','')
        import re
        m=re.search(r'norm_scale=([0-9.]+)',st); d['norm_scale']=float(m.group(1)) if m else None
        if kind=='impulse': d.update({k:round(v,3) for k,v in t30(x,sr).items()})
        row[kind]=d
    res[name]=row; print(name, json.dumps(row), flush=True)
if only: json.dump(res,open(D+'data/engine_sanity_%s.json'%('_'.join(only)[:40]),'w'),indent=1)
