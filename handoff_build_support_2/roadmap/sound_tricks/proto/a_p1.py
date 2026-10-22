import json, numpy as np, sys
sys.path.insert(0,'.')
from harness import *
import ana, freqdecay as FD
b = body(); p = A.params_from_body(dict(b))
W,H,L,T,hum = p["W"],p["H"],p["L"],float(p["decay_s"]),float(p["humidity"])
tg = {"A_today": None,
      "B1_air": FD.ratio_fn(W,H,L,T,hum,p["surfaces"],"air")[0],
      "B2_air_materials": FD.ratio_fn(W,H,L,T,hum,p["surfaces"],"air+materials_clamped")[0],
      "B3_air_materials_unclamped": FD.ratio_fn(W,H,L,T,hum,p["surfaces"],"air+materials")[0]}
files = {"A_today":"ir_ortf_noC.npy","B1_air":"ir_p1_air.npy","B2_air_materials":"ir_p1_airmatc.npy","B3_air_materials_unclamped":"ir_p1_airmat.npy"}
out = {}
for k,f in files.items():
    ir = np.load(f); m = ir.sum(1)
    pr = ana.params(m)
    tgt = [T]*7 if tg[k] is None else [float(x)*T for x in tg[k](FD.BANDS)]
    t30 = [pr[fc]["T30"] for fc in ana.OCT]
    err = [100*(a/b-1) for a,b in zip(t30,tgt)]
    out[k] = dict(target=tgt, T30=t30, err_pct=err, C50_1k=pr[1000]["C50"], C80_1k=pr[1000]["C80"], EDT_1k=pr[1000]["EDT"],
                  rms=float(np.sqrt(np.mean(ir**2))), len_s=len(ir)/48000)
    print(k, "T30", [round(x,2) for x in t30], "\n   tgt", [round(x,2) for x in tgt], "\n   err%", [round(x,1) for x in err], "C50", round(pr[1000]["C50"],1), "C80", round(pr[1000]["C80"],1))
json.dump(out, open("p1_results.json","w"), indent=1)
