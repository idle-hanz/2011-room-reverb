import json, subprocess, os, copy, numpy as np, sys
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
HERE=os.path.dirname(os.path.abspath(__file__)); W=HERE+'/w'; SR=48000
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
big=dict(W=57.0,H=34.2,L=97.0,sx=24.0,sz=60.0,mcx=28.5,mcz=30.0,sx_b=33.0,sz_b=60.0,two_sources=True,mirror_b=True)
CASES=[(sn,'big2_d8',dict(big,decay_s=8.0)) for sn in os.environ.get('SNAPS','2026-10-01_1550,2026-10-02_0709,2026-10-02_1140').split(',')]
if os.environ.get('EXTRA'):
    CASES+=[('2026-10-02_1140','big2_d4',dict(big,decay_s=4.0)),('2026-10-02_1140','big2_d1.8',dict(big,decay_s=1.8)),
            ('2026-10-02_1140','big2_d8_violin',dict(big,decay_s=8.0,source_radiation='violin_byu',source_yaw=168.0)),
            ('2026-10-02_1140','def_d8',dict(decay_s=8.0)),('2026-10-02_1140','big1_d8',dict(big,two_sources=False,decay_s=8.0))]
res={}
for sn,name,ov in CASES:
    sw=f'{B}/snapshot_{sn}/software'; b=dict(copy.deepcopy(base),**ov); tag=f'{name}_{sn}'; pj=f'{W}/pr_{tag}.json'; f=f'{W}/irr_{tag}.f32'
    subprocess.run([P,LIB+'/dump_params.py',sw,json.dumps(b),pj,'48000'],check=True,capture_output=True)
    r=subprocess.run(['node',LIB+'/wasm_run.js',sw,pj,json.dumps({"direct_wet":0,"early_wet":0}),'ir','25',f],capture_output=True,text=True); assert r.returncode==0,r.stderr
    x=np.fromfile(f,np.float32).reshape(-1,2).astype(float); m=x.mean(1)
    lev=[round(20*np.log10(np.sqrt(np.mean(m[i*SR:(i+1)*SR]**2))+1e-30),1) for i in range(0,25)]
    res[tag]=dict(level_db_per_s=lev, dc_last_s=round(float(np.mean(m[-SR:])),5), peak_last_s=round(float(np.max(np.abs(m[-SR:]))),4))
    print(tag, 'levels 0..24 s:', lev[::2], 'DC', res[tag]['dc_last_s'], 'peak', res[tag]['peak_last_s'], flush=True)
json.dump(res,open(HERE+f'/runaway_{os.environ.get("TAG","a")}.json','w'),indent=1)
