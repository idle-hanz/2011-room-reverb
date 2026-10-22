import json, subprocess, os, numpy as np
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
HERE=os.path.dirname(os.path.abspath(__file__)); W=HERE+'/w'
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
big=dict(W=57.0,H=34.2,L=97.0,sx=24.0,sz=60.0,mcx=28.5,mcz=30.0,sx_b=33.0,sz_b=60.0)
SW=B+'/snapshot_2026-10-02_1140/software'; SR=48000
def ir(name, ov, run_ov, secs=3):
    body=dict(base); body.update(ov); pj=f'{W}/pm_{name}.json'; f=f'{W}/irm_{name}.f32'
    subprocess.run([P,LIB+'/dump_params.py',SW,json.dumps(body),pj,'48000'],check=True,capture_output=True)
    r=subprocess.run(['node',LIB+'/wasm_run.js',SW,pj,json.dumps(run_ov),'ir',str(secs),f],capture_output=True,text=True); assert r.returncode==0,r.stderr
    return np.fromfile(f,np.float32).reshape(-1,2).astype(float)
def cep_peak(x):
    seg=x[int(.1*SR):int(1.5*SR)]; N=len(seg); S=np.abs(np.fft.rfft(seg*np.hanning(N)))+1e-12
    c=np.fft.irfft(np.log(S)); lo=int(0.0003*SR); hi=int(0.03*SR); k=np.argmax(np.abs(c[lo:hi]))+lo
    return round(float(np.abs(c[k])/np.std(c[lo:hi])),1), round(k/SR*1e3,3)
def xcorr(a,b):
    a=a[int(.1*SR):int(1.5*SR)]; b=b[int(.1*SR):int(1.5*SR)]; n=len(a)
    c=np.fft.irfft(np.fft.rfft(a,2*n)*np.conj(np.fft.rfft(b,2*n))); c/=np.sqrt(np.dot(a,a)*np.dot(b,b))
    c=np.concatenate([c[-int(.05*SR):],c[:int(.05*SR)]]); k=np.argmax(np.abs(c)); return round(float(c[k]),3), round((k-int(.05*SR))/SR*1e3,3)
FD={"direct_wet":0,"early_wet":0}
out={}
for room,rov in (('def',{}),('big',big)):
    v=dict(rov,source_radiation='violin_byu',source_yaw=173.0 if room=='def' else 168.0,source_pitch=5.0)
    one=ir(f'{room}_1src',v,FD)
    out[f'{room}_1src_xcorr_L_R']=xcorr(one[:,0],one[:,1])
    for tag,ov in (('mirror_follow',dict(v,two_sources=True,mirror_b=True)),('mirror_B_omni',dict(v,two_sources=True,mirror_b=True,source_radiation_b='omni'))):
        for mode,ro in (('fdn',FD),('full',{})):
            x=ir(f'{room}_{tag}_{mode}',ov,ro)
            L,R=x[:,0],x[:,1]
            out[f'{room}|{tag}|{mode}']=dict(L_eq_R_maxdiff=float(np.max(np.abs(L-R))), lr_corr=round(float(np.dot(L,R)/np.sqrt(np.dot(L,L)*np.dot(R,R))),4), cep_L=cep_peak(L), xcorr_LR=xcorr(L,R))
for k,v in out.items(): print(k,v)
json.dump(out,open(HERE+'/mono.json','w'),indent=1)
