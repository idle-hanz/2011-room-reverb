import json, subprocess, os, numpy as np, time
PY='/workspace/scratch_er_dropout/venv/bin/python'; SW='/workspace/audit_1852/software'; HERE='/workspace/audit_1852/decisions'
LIB='/workspace/build_support_2/3_phase_acceptance_tests/harness/lib'; B='/workspace/build_support_2'; SR=48000
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); base.update(direct_wet=1.0,early_wet=1.0,fdn_wet=1.0)
FC=[125,250,500,1000,2000,3150,4000,5000,6300,8000,10000,12500,16000]
def bands(x):
    X=np.abs(np.fft.rfft(x,1<<19))**2; f=np.fft.rfftfreq(1<<19,1/SR)
    return np.array([10*np.log10(X[(f>=c*2**-(1/6))&(f<c*2**(1/6))].sum()+1e-30) for c in FC])
def rir(body,ms,tag):
    out=f'{HERE}/rir_{tag}.f32'; t=time.time()
    if not os.path.exists(out):
        r=subprocess.run([PY,LIB+'/render_ir.py',SW,json.dumps(body),out,str(ms),str(SR)],capture_output=True,text=True)
        if r.returncode: raise SystemExit(r.stderr[-800:])
    return np.fromfile(out,np.float32).reshape(-1,2).astype(np.float64), round(time.time()-t,1)
def edc_t30(x):
    e=np.cumsum((x**2).sum(1)[::-1])[::-1]; e=10*np.log10(e/e[0]+1e-30); t=np.arange(len(e))/SR
    i5=np.argmax(e<=-5); i35=np.argmax(e<=-35)
    if i35==0: return None
    p=np.polyfit(t[i5:i35],e[i5:i35],1); return round(-60/p[0],3)
L={}
mono=dict(base,mic_setup='mono_c',space=0,yaw_l_deg=0,yaw_r_deg=0,toe_half_deg=0)
a,ta=rir(mono,2000,'mono_base'); b,tb=rir(dict(mono,mic_gain_l=0.0,mic_gain_r=0.0),2000,'mono_conly')
E=lambda x: 10*np.log10(np.sum(x**2)+1e-30)
d0=int(np.argmax(np.abs(a).sum(1)[:int(0.05*SR)])); we=slice(0,d0+int(0.08*SR)); wt=slice(d0+int(0.08*SR),None)
L['mono_c']={'total_db':round(E(b)-E(a),2),'early_db':round(E(b[we])-E(a[we]),2),'tail_db':round(E(b[wt])-E(a[wt]),2),
  'peak_db':round(20*np.log10(np.abs(b).max()/np.abs(a).max()),2),'corr_LR_after':round(float(np.corrcoef(b[:,0],b[:,1])[0,1]),4),
  'early_3oct_delta':[round(x,2) for x in bands(b[we,0])-bands(a[we,0])],'tail_3oct_delta':[round(x,2) for x in bands(b[wt,0])-bands(a[wt,0])]}
print('mono_c',json.dumps(L['mono_c']),flush=True)
for nm,over,ms_new in (('default_1p8',{},int(1.5*1800+100)),('decay_4',dict(decay_s=4.0,decay_lock=True),int(1.5*4000+100))):
    x,t1=rir(dict(base,**over),1500,nm+'_1500'); y,t2=rir(dict(base,**over),ms_new,f'{nm}_{ms_new}')
    n=len(x); pk=np.abs(y).max()
    cut=np.sqrt(np.mean((y[n-int(0.05*SR):n]**2)))  # rms level just before old cut
    L[nm]={'old_ms':1500,'new_ms':ms_new,'render_s_old_new':[t1,t2],'added_energy_db_of_total':round(10*np.log10(np.sum(y[n:]**2)/np.sum(y**2)+1e-30),2),
      'total_level_change_db':round(E(y)-E(x),3),'level_at_old_cut_rel_peak_db':round(20*np.log10(cut/pk),1),
      'level_last50ms_new_rel_peak_db':round(20*np.log10(np.sqrt(np.mean(y[-int(0.05*SR):]**2))/pk+1e-30),1),
      'T30_old':edc_t30(x),'T30_new':edc_t30(y),'set_decay':over.get('decay_s',1.8),
      'first_1500ms_max_abs_diff':float(np.max(np.abs(y[:n]-x)))}
    print(nm,json.dumps(L[nm]),flush=True)
json.dump(L,open(HERE+'/len_mono.json','w'),indent=1)
