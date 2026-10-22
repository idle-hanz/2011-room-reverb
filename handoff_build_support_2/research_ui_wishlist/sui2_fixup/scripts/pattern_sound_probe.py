"""Does the (hidden) family/polar change the sound in Measured? Render + Play IR energy/null, default client body.
Cases: Measured with preset_owns_pattern False (as after a Mic-setup load or a User-defined edit) and True."""
import sys, os, json, types, copy, numpy as np
B='/workspace/build_support_2'; HAR=B+'/3_phase_acceptance_tests/harness'
sys.path[:0]=[HAR, HAR+'/lib']; import run_all as RA
SW=B+'/snapshot_2026-10-03_0818/software'; OUT=B+'/research_ui_wishlist/sui2_fixup/'
a=types.SimpleNamespace(sw=SW,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir='/tmp')
c=RA.Ctx(a)
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
base.update({"mic_preset_l":"ShureSM57","mic_preset_c":"ShureSM57","mic_preset_r":"ShureSM57","direct_wet":1.0,"early_wet":1.0,"fdn_wet":1.0})
CARD={"family_l":"cardioid","family_r":"cardioid","polar_l":0.5,"polar_r":0.5,"pattern_l":"cardioid","pattern_r":"cardioid"}
BI={"family_l":"bi","family_r":"bi","polar_l":0.5,"polar_r":0.5,"pattern_l":"fig8","pattern_r":"fig8"}
OMNI={"family_l":"cardioid","family_r":"cardioid","polar_l":0.0,"polar_r":0.0,"pattern_l":"omni","pattern_r":"omni"}
def edb(x): return round(10*np.log10(float(np.sum(x**2))+1e-300),2)
res={}
for mode in ("MEASURED_SHELF","BYPASS","ASSUMED_TOYS"):
    for owns in (False, True):
        R={}; P={}
        for name,pat in (("card",CARD),("bi",BI),("omni",OMNI)):
            body=dict(copy.deepcopy(base),colour_mode=mode,preset_owns_pattern=owns,**pat)
            R[name]=c.render_ir(body,800); P[name]=c.play_ir(body,{},0.8)
        k=f'{mode}|owns={owns}'
        res[k]={'render_db':{n:[edb(R[n][:,0]),edb(R[n][:,1])] for n in R},'play_db':{n:[edb(P[n][:,0]),edb(P[n][:,1])] for n in P},
                'render_null_bi_vs_card':[round(RA.null_db(R['bi'][:,ch],R['card'][:,ch]),1) for ch in (0,1)],
                'render_null_omni_vs_card':[round(RA.null_db(R['omni'][:,ch],R['card'][:,ch]),1) for ch in (0,1)],
                'play_null_bi_vs_card':[round(RA.null_db(P['bi'][:,ch],P['card'][:,ch]),1) for ch in (0,1)],
                'play_null_omni_vs_card':[round(RA.null_db(P['omni'][:,ch],P['card'][:,ch]),1) for ch in (0,1)]}
        print(k, json.dumps(res[k]), flush=True)
json.dump(res,open(OUT+'data/pattern_sound_probe.json','w'),indent=1)
