import sys,json,glob,os,csv; sys.path.insert(0,'/workspace/uad')
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from alib import *; from ess import fr
R="/workspace/uad/report/uad"
def wcsv(fn,hdr,rows):
    with open(f"{R}/{fn}","w",newline="") as f: w=csv.writer(f); w.writerow(hdr); [w.writerow(r) for r in rows]
# ---- static curves
stairs={"fairchild670_t5":"st_fc670_t5","fairchild670_t1":"st0_fc670","sslg_2to1":"st_sslg_21","sslg_4to1":"st0_sslg","sslg_10to1":"st_sslg_101",
 "la2a_silver_comp":"st0_la2a_s","la2a_silver_limit":"st_la2a_s_lim","la2a_gray_comp":"st0_la2a_g","la2_comp":"st0_la2","la3a_comp":"st0_la3a",
 "1176ln_4to1_in-40":"st_ln_in40","1176revA_4to1_in-40":"st_ra_in40","1176ln_20to1_in-20":"st_u1176ln_201","1176_ALL_in-20":"st_u1176_ALL",
 "dbx160_4to1":"st0_dbx160","manleyVM_comp":"st0_mvm","manleyVM_limit":"st_mvm_lim","manleyVM_limit_hot":"st_mvm_hot"}
for r in ['21','31','41','61','101','201','NUKE']: stairs["distressor_"+r.replace("1","to1") if r!="NUKE" else "distressor_nuke"]="st_dist_"+r
rows=[]; fig,ax=plt.subplots(1,3,figsize=(16,5))
for nm,i in stairs.items():
    m,rw=stair(i); L=rw[:,0]; gr=rw[:,2]-rw[0,2]
    for k in range(len(L)):
        lr="" if k==0 else "%.3f"%((L[k]-L[k-1])/max(1e-6,(L[k]+gr[k])-(L[k-1]+gr[k-1])))
        rows.append([nm,m["plugin"],json.dumps(m["set"]),L[k],"%.3f"%gr[k],lr])
    a=ax[0] if nm.startswith(("fair","ssl","manley","dbx")) else ax[1] if nm.startswith(("la","1176")) else ax[2]
    a.plot(L,gr,label=nm)
for a in ax: a.set_xlabel("input (dBFS peak, 1 kHz)"); a.set_ylabel("gain reduction (dB)"); a.grid(alpha=.3); a.legend(fontsize=7)
fig.suptitle("UAD static curves (1 kHz staircase, 1-4 s per step)"); fig.tight_layout(); fig.savefig(f"{R}/static_curves.png",dpi=110); plt.close()
wcsv("static_curves.csv",["curve","plugin","params","in_dbfs","gr_db","local_ratio_from_prev"],rows)
# ---- release metrics
rel_ids=sorted([os.path.basename(f)[:-5] for f in glob.glob("out/b_*.json")])
rows=[]
for i in rel_ids:
    m,o,t,r=rel_metrics(i)
    rows.append([i,m["plugin"],json.dumps(m["set"]),m["sig"]["probe_db"],m["sig"]["burst_db"],m["sig"]["burst_s"],"%.2f"%o["GR0"]]+["" if o[k] is None else "%.4f"%o[k] for k in ["t_half","t63","t_3dB","t_1dB","t_0p5dB"]])
wcsv("release_metrics.csv",["id","plugin","params","probe_dbfs","burst_dbfs","burst_s","gr_at_burst_end_db","t_half_s","t63_s","t_to_3dB_s","t_to_1dB_s","t_to_0p5dB_s"],rows)
rows=[]
for i in sorted([os.path.basename(f)[:-5] for f in glob.glob("out/a_*.json")]+[x for x in rel_ids]):
    m,o,t,x=att_metrics(i)
    rows.append([i,m["plugin"],json.dumps(m["set"]),m["sig"]["burst_db"],"%.2f"%o["GRf"]]+["" if o[k] is None else "%.4f"%o[k] for k in ["t10","t63","t90"]])
wcsv("attack_metrics.csv",["id","plugin","params","step_to_dbfs","gr_final_db","t10_s","t63_s","t90_s"],rows)
# ---- plots: Fairchild
sp=json.load(open("/workspace/compressors/spice/raw/fairchild_summary.json"))["results"]
fig,ax=plt.subplots(1,2,figsize=(14,5))
for a,pos,ds,T in [(ax[0],5,[0.01,0.05,0.3,1,3,10],12),(ax[1],6,[0.01,0.3,1,3,10,20],30)]:
    for d in ds:
        m,o,t,r=rel_metrics(f"b_fc{pos}_{d}"); a.plot(t,r,label=f"UAD burst {d}s")
    for b,v in sp[str(pos)].items():
        if v["t_to_1dB"]: a.plot(v["t_to_1dB"],-1,"kx")
    a.axhline(-1,color="grey",lw=.5); a.set_xlim(0,T); a.set_title(f"Fairchild 670 pos {pos}: UAD release (lines); x = our SPICE time to 1 dB"); a.set_xlabel("s after burst"); a.set_ylabel("GR dB"); a.grid(alpha=.3); a.legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{R}/fairchild_release_pos5_pos6.png",dpi=110); plt.close()
# SSL auto overlay
fig,ax=plt.subplots(figsize=(8,5))
for d,c in zip([0.05,0.3,1,3,8],"bgrcm"):
    m,o,t,r=rel_metrics(f"b_sgA_{d}"); ax.plot(t,r/(-o["GR0"]),c,label=f"UAD {d}s")
    f=f"/workspace/compressors/spice/raw/ssl_auto_release_{float(d)}.csv"
    if os.path.exists(f):
        s=np.loadtxt(f,delimiter=",",comments="#"); ax.plot(s[:,0],-s[:,1]/s[0,1],c+"--",lw=1,label=f"SPICE {d}s")
ax.set_xscale("log"); ax.set_xlim(0.005,20); ax.set_xlabel("s after burst"); ax.set_ylabel("GR / GR at release start"); ax.set_title("SSL G Auto release: UAD (solid) vs our SPICE (dashed)"); ax.grid(alpha=.3); ax.legend(fontsize=7,ncol=2)
fig.tight_layout(); fig.savefig(f"{R}/ssl_auto_release.png",dpi=110); plt.close()
# LA-2A
fig,ax=plt.subplots(figsize=(8,5)); bl=[0.05,0.3,1,5,20]
for nm,lab in [("la2as","UAD LA-2A Silver"),("la2ag","UAD LA-2A Gray"),("la2","UAD LA-2"),("la3a","UAD LA-3A")]:
    v=[]
    for d in bl:
        m,o,t,r=rel_metrics(f"b_{nm}_{d}"); u=10**(-r/20)-1; u0=u[16]; k=first_cross(u,u0*0.3679,above=False); v.append(k/4000)
    ax.plot(bl,v,"o-",label=lab+" (conductance t63)")
ax.plot([0.3,1,5],[0.14,0.57,1.51],"ks--",label="our fitted model (0.06+1.53*M2)"); ax.plot([0.3,1,5],[0.09,0.58,1.56],"k^:",label="Stroe measured cell")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("burst length s"); ax.set_ylabel("release time constant s"); ax.set_title("Opto release memory: UAD vs our model"); ax.grid(alpha=.3); ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{R}/la2a_release_memory.png",dpi=110); plt.close()
# 1176
fig,ax=plt.subplots(figsize=(7,5))
for nm,lab in [("ln","UAD 1176LN Rev E"),("ra","UAD 1176 Rev A")]:
    ax.plot(range(1,8),[rel_metrics(f"b_{nm}_r{k}")[1]["t63"] for k in range(1,8)],"o-",label=lab+" t63")
ax.axhline(1.16,color="k",ls="--",lw=.8,label="circuit 1.16 s (knob 1)"); ax.axhline(0.059,color="k",ls=":",lw=.8,label="circuit 59 ms (knob 7)")
ax.set_yscale("log"); ax.set_xlabel("release knob"); ax.set_ylabel("s"); ax.set_title("1176 release (63% recovery) vs knob"); ax.grid(alpha=.3); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(f"{R}/u1176_release_knob.png",dpi=110); plt.close()
# Distressor tapers
fig,ax=plt.subplots(1,2,figsize=(12,4.5))
ka=[0,1,2,3,3.5,4,5,6,7,8,9,10]; ax[0].plot(ka,[1000*att_metrics(f"a_dsA_{a}")[1]["t63"] for a in ka],"o-",label="UAD t63")
ax[0].plot([0,3.5,4,5,6,10],[0.05,0.8,1.06,1.85,3.2,30],"ks--",label="our manual-anchored taper"); ax[0].set_yscale("log"); ax[0].set_xlabel("attack knob"); ax[0].set_ylabel("ms"); ax[0].legend(); ax[0].grid(alpha=.3); ax[0].set_title("Distressor attack (6:1)")
kr=[0,1,2,3,4,5,6,7,8,9,10,10.5]; ax[1].plot(kr,[rel_metrics(f"b_dsR_{k}")[1]["t63"] for k in kr],"o-",label="UAD t63"); ax[1].plot(kr,[rel_metrics(f"b_dsR_{k}")[1]["t_1dB"] for k in kr],"o-",label="UAD to 1 dB")
ax[1].plot(kr,[0.05*70**(k/10) for k in kr],"k--",label="our estimate 0.05*70^(k/10)"); ax[1].set_yscale("log"); ax[1].set_xlabel("release knob"); ax[1].set_ylabel("s"); ax[1].legend(); ax[1].grid(alpha=.3); ax[1].set_title("Distressor release (6:1)")
fig.tight_layout(); fig.savefig(f"{R}/distressor_tapers.png",dpi=110); plt.close()
# ---- pres
rows=[]; fig,ax=plt.subplots(1,2,figsize=(14,5))
for f in sorted(glob.glob("out/ts_*.json")):
    m=json.load(open(f)); nm=os.path.basename(f)[3:-5]
    for s in m["steps"]: rows.append([nm,m["plugin"],json.dumps(m["set"]),m["sig"].get("f"),s["in_db"],"%.2f"%s["fund_db"],"%.5f"%s["thd_pct"],"%.1f"%s["h_db_rel"][0],"%.1f"%s["h_db_rel"][1],"%.1f"%s["h_db_rel"][2]])
    if m["sig"].get("f")==1000.0 and any(nm.startswith(p) for p in ["neve_Mm50","api_45","sslE_40","manley_50","u610a_Hi","u610b_0","u610a_lvl"]):
        x=[s["fund_db"] for s in m["steps"]]; y=[s["thd_pct"] for s in m["steps"]]; ax[0].plot(x,y,label=nm)
ax[0].set_yscale("log"); ax[0].set_xlim(-50,15); ax[0].set_xlabel("output fundamental (dBFS peak)"); ax[0].set_ylabel("THD % (H2-H10)"); ax[0].axhline(0.1,color="k",ls=":",lw=.8); ax[0].grid(alpha=.3); ax[0].legend(fontsize=7); ax[0].set_title("UAD mic pres: THD vs output, 1 kHz, Mic input")
frows=[]
for k in ["neve","api","sslE","manley","u610a","u610b"]:
    for tag in ["vlow","nom","hot"]:
        m,F,A,ref=fr(f"ess_{k}_{tag}")
        for fq in [10,15,20,25,31.5,40,50,63,80,100,200,500,1000,2000,5000,8000,10000,12500,15000,16000,18000,20000,22000]:
            frows.append([k,tag,m["sig"]["level_db"],"%.2f"%ref,fq,"%.3f"%np.interp(fq,F,A)])
        if tag=="nom": ax[1].semilogx(F[(F>10)&(F<23000)],A[(F>10)&(F<23000)],label=k)
ax[1].set_ylim(-6,2); ax[1].set_xlabel("Hz"); ax[1].set_ylabel("dB re 1 kHz"); ax[1].grid(alpha=.3,which="both"); ax[1].legend(fontsize=8); ax[1].set_title("UAD mic pres: frequency response (nominal drive, EQ out)")
fig.tight_layout(); fig.savefig(f"{R}/pre/pre_thd_fr.png",dpi=110); plt.close()
wcsv("pre/pre_thd_steps.csv",["run","plugin","params","freq_hz","in_dbfs","out_fund_dbfs","thd_pct_h2_h10","h2_dbc","h3_dbc","h4_dbc"],rows)
wcsv("pre/pre_freq_response.csv",["pre","drive","sweep_level_dbfs","gain_1k_db","freq_hz","db_re_1k"],frows)
print("done")
