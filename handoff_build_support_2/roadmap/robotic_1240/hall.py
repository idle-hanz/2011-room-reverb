import json, subprocess, os, copy, numpy as np, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from bisect_lib import metrics
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
HERE=os.path.dirname(os.path.abspath(__file__)); W=HERE+'/w'
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
hall=dict(W=57,H=34.241,L=97,sx=24.925,sz=72.083,sy=1.88,my=1.9,mcz=24.25,space=0.25,reaktor_parity=True,car_omni=0.764,fader_early=0,fader_dry=0,fader_direct=0.5,fader_fdn=0.5,
  early_wet=1.0,fdn_wet=1,direct_wet=1,dry_gain=0,fdn_g=1,decay_lock=False,ir_length_ms=1500,hadamard_n=32,humidity=0.5,air_lp=0.25,air_shelf=1,diffusion_master=-0.5,mic_response_hz=10000,link_heights=False)
dif={'A':0.16,'B':0.25,'C':0.16,'D':0.33,'E':0.27,'F':0.65}
def body(snap, extra, three=True):
    b=copy.deepcopy(base); b.update(hall); b['mcx']=b['W']/2 if 'mcx' not in extra else extra['mcx']
    for L,v in dif.items():
        b['surfaces'][L]['diffusion']=v
        if three: b['surfaces'][L]['jitter_D']=v; b['surfaces'][L]['structure_dif']=v
        else: b['surfaces'][L].pop('jitter_D',None); b['surfaces'][L].pop('structure_dif',None)
    b.update(extra); return b
if __name__=="__main__":
    SC={'hall1':{}, 'hall2':dict(two_sources=True,mirror_b=True,sx_b=57-24.925,sz_b=72.083),
        'hall2v':dict(two_sources=True,mirror_b=True,sx_b=57-24.925,sz_b=72.083,source_radiation='violin_byu',source_yaw=168.0)}
    SN=os.environ.get('SNAPS','2026-10-01_1550,2026-10-02_0709,2026-10-02_0830,2026-10-02_1140').split(',')
    res={}
    for sc,ex in SC.items():
      for sn in SN:
        for three in ((False,True) if sn.endswith('1140') else (False,)):
            sw=f'{B}/snapshot_{sn}/software'; tag=f'{sc}_{sn}_{"3keys" if three else "difonly"}'
            pj=f'{W}/ph_{tag}.json'; f=f'{W}/irh_{tag}.f32'
            subprocess.run([P,LIB+'/dump_params.py',sw,json.dumps(body(sn,ex,three)),pj,'48000'],check=True,capture_output=True)
            r=subprocess.run(['node',LIB+'/wasm_run.js',sw,pj,json.dumps({"direct_wet":0,"early_wet":0}),'ir','6',f],capture_output=True,text=True); assert r.returncode==0,r.stderr
            x=np.fromfile(f,np.float32).reshape(-1,2).astype(float); p=json.load(open(pj))
            m=metrics(x); m.update(g=p['g'],decay=p.get('decay_s'),line_t60=(p.get('line_t60') if not isinstance(p.get('line_t60'),list) else p['line_t60'][:3]),dffs_c=[round(v,3) for v in p['buses']['c']['dffs']][:8])
            res[tag]=m; print(tag,json.dumps(m),flush=True)
    json.dump(res,open(HERE+'/hall.json','w'),indent=1)
