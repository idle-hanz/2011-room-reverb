from common import *
C=ctx('R_z1'); out={}
for tag,ex in (('all',{}),('c_off',{"mic_gain_c":0.0}),('lr_off',{"mic_gain_l":0.0,"mic_gain_r":0.0})):
    b=dict(base,**FDN,**ex,colour_mode="BYPASS"); P=C.play_ir(b,dict(OVER,colour_on=False),1.0,wasm=WASM['P_old']); Rr=C.render_ir(b,1000)
    n=min(len(P),len(Rr)); P,Rr=P[:n],Rr[:n]
    a=[float(np.dot(P[:,c],Rr[:,c])/max(np.dot(P[:,c],P[:,c]),1e-30)) for c in (0,1)]
    out[tag]=dict(gain_R_over_P=[round(v,4) for v in a],P_db=round(edb(P),2),R_db=round(edb(Rr),2)); print(tag,out[tag],flush=True)
json.dump(out,open(R+'/data/gainprobe.json','w'),indent=1)
