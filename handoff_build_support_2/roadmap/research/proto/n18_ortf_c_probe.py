import sys,os,json; sys.path.insert(0,'/workspace/build_support_2/roadmap/prebuild/tests_py')
os.environ['RR_SOFTWARE']='/workspace/build_support_2/prebuild_app/software'
import _harness as H, numpy as np
b=json.load(open('/workspace/build_support_2/roadmap/prebuild/tests_py/fixtures/ui_body_ortf.json')); b.update(colour_mode="BYPASS", ir_length_ms=80, fdn_wet=0.0, early_wet=1.0, direct_wet=1.0)
a=H.render_body(dict(b,mic_gain_c=1.0)); z=H.render_body(dict(b,mic_gain_c=0.0)); off=H.render_body(dict(b,third_mic="off"))
print("C gain 1 vs 0 (desk idle): null %.1f dB"%H.null_db(a,z)); print("C gain 1 vs third_mic off: null %.1f dB"%H.null_db(a,off))
print("energy dB: C on %.2f, C off %.2f"%(10*np.log10(np.sum(a**2)),10*np.log10(np.sum(off**2))))
print("LR corr 0-80ms: C on %.3f, C off %.3f"%(np.corrcoef(a[:,0],a[:,1])[0,1],np.corrcoef(off[:,0],off[:,1])[0,1]))
