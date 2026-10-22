import json, subprocess, os, copy, numpy as np, wave, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hall import hall, dif
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
HERE=os.path.dirname(os.path.abspath(__file__)); W=HERE+'/w'; OUT=HERE+'/ab_wav'; os.makedirs(OUT,exist_ok=True); SR=48000
g=np.load(W+'/guitar.npy')[:int(9*SR)].astype(np.float32); fin=W+'/guitar_in.f32'; np.stack([g,g],1).astype(np.float32).tofile(fin)
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
S={'1140':B+'/snapshot_2026-10-02_1140/software','0830':B+'/snapshot_2026-10-02_0830/software'}
def hb():
    b=copy.deepcopy(base); b.update(hall); b['mcx']=28.5
    for L,v in dif.items(): b['surfaces'][L].update(diffusion=v,jitter_D=v,structure_dif=v)
    return b
two=dict(two_sources=True,mirror_b=True,sx_b=57-24.925,sz_b=72.083,source_radiation='violin_byu',source_yaw=168.0)
HEARD_DEF=dict(direct_wet=0.0,early_wet=0.0,fdn_wet=1.0)      # page defaults (K4): direct and early faders down, FDN 0 dB
HEARD_HALL=dict(direct_wet=1.0,early_wet=0.0,fdn_wet=1.0)     # Hall button: direct 0 dB, FDN 0 dB, early fader 0
EARLY_UP=dict(direct_wet=0.0,early_wet=1.0,fdn_wet=0.0)       # early fader at 0 dB, direct and FDN off
PAIRS={
 '1_hall_mirror_violin_as_heard': [('A_0830_B_omni','0830',hb(),dict(two,source_radiation_b='omni',source_pitch_b=0,**HEARD_HALL),{}), ('B_1140_B_follows_A','1140',hb(),dict(two,**HEARD_HALL),{})],
 '2_hall_solo_left_wall_as_heard': [('A_no_solo','1140',hb(),HEARD_HALL,{}), ('B_solo_A_left','1140',hb(),dict(HEARD_HALL,surfaces_solo='A'),{})],
 '3_default_room_solo_left_wall_as_heard': [('A_no_solo','1140',base,HEARD_DEF,{}), ('B_solo_A_left','1140',base,dict(HEARD_DEF,surfaces_solo='A'),{})],
 '4_default_room_early_fader_up_solo_left_wall': [('A_no_solo','1140',base,EARLY_UP,{}), ('B_solo_A_left','1140',base,dict(EARLY_UP,surfaces_solo='A'),{})],
}
def wav(path,x):
    pcm=(np.clip(x,-1,1)*32767).astype('<i2')
    with wave.open(path,'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
res={}
for pair,items in PAIRS.items():
    outs=[]
    for name,sn,b0,ov,run_ov in items:
        b=dict(copy.deepcopy(b0),**ov); pj=f'{W}/pab_{pair}_{name}.json'; f=f'{W}/ab_{pair}_{name}.f32'
        subprocess.run([P,LIB+'/dump_params.py',S[sn],json.dumps(b),pj,'48000'],check=True,capture_output=True)
        r=subprocess.run(['node',HERE+'/wasm_run_file.js',S[sn],pj,json.dumps(run_ov),'file',fin,f],capture_output=True,text=True); assert r.returncode==0,r.stderr
        outs.append((name,np.fromfile(f,np.float32).reshape(-1,2).astype(float)))
    gmax=max(np.max(np.abs(x)) for _,x in outs); k=0.7/gmax
    for name,x in outs:
        pth=f'{OUT}/{pair}__{name}.wav'; wav(pth,x*k)
        L,R=x[:,0],x[:,1]; res[f'{pair}|{name}']=dict(path=pth, gain_applied_db=round(20*np.log10(k),2), lr_corr=round(float(np.corrcoef(L,R)[0,1]),4), rms_db=round(20*np.log10(np.sqrt(np.mean(x**2))),2))
        print(pair,name,res[f'{pair}|{name}'],flush=True)
json.dump(res,open(HERE+'/ab_wavs.json','w'),indent=1)
