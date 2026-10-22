import json, subprocess, os, copy, numpy as np
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
HERE=os.path.dirname(os.path.abspath(__file__)); W=HERE+'/w'; os.makedirs(W,exist_ok=True); SR=48000
SW=B+'/snapshot_2026-10-02_1140/software'; SHIPPED=SW+'/static/wasm/live_stereo.wasm'
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
big=dict(W=57.0,H=34.2,L=97.0,sx=24.0,sz=60.0,mcx=28.5,mcz=30.0,sx_b=33.0,sz_b=60.0,two_sources=True,mirror_b=True)
SC={'def1':({},2),'def2':(dict(two_sources=True),2),'big2_d1.8':(big,3),'big2_d8':(dict(big,decay_s=8.0),25),'big2_d4':(dict(big,decay_s=4.0),25),
    'bin_big_d4':(dict(big,decay_s=4.0,mic_setup='binaural'),25),'bin_big_d8':(dict(big,decay_s=8.0,mic_setup='binaural'),25),'def_d8':(dict(decay_s=8.0),25)}
V={'shipped':SHIPPED,'ship_rebuilt':HERE+'/ship.wasm','fix':HERE+'/fix.wasm','fixcond':HERE+'/fixcond.wasm'}
res={}
for sc,(ov,secs) in SC.items():
    pj=f'{W}/p_{sc}.json'; subprocess.run([P,LIB+'/dump_params.py',SW,json.dumps(dict(copy.deepcopy(base),**ov)),pj,'48000'],check=True,capture_output=True)
    irs={}
    for vn,w in V.items():
        if vn=='ship_rebuilt' and secs>3: continue
        f=f'{W}/ir_{sc}_{vn}.f32'
        r=subprocess.run(['node',LIB+'/wasm_run.js',SW,pj,'{}','ir',str(secs),f],env=dict(os.environ,WASM=w),capture_output=True,text=True); assert r.returncode==0,r.stderr
        irs[vn]=np.fromfile(f,np.float32).reshape(-1,2).astype(float)
    row={}
    for vn,x in irs.items():
        m=x.mean(1); lev=[round(20*np.log10(np.sqrt(np.mean(m[i*SR:(i+1)*SR]**2))+1e-30),1) for i in range(int(len(m)/SR))]
        row[vn]=dict(maxdiff_vs_shipped=float(np.max(np.abs(x-irs['shipped']))), level_db_s=lev[::2] if len(lev)>3 else lev, dc_last=round(float(np.mean(m[-SR:])),6), finite=bool(np.all(np.isfinite(x))))
    res[sc]=row; print(sc,json.dumps(row),flush=True)
json.dump(res,open(HERE+'/test_fix.json','w'),indent=1)
