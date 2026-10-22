# r3: real excerpts (read-only sources, inputs stay on this PC) + aliasing / pre stair inputs + job list.
import numpy as np, soundfile as sf, json, os
from scipy.signal import resample_poly
import units as U, siglib as S
SR=48000; I="inputs/"
D=r"D:\Demos and Tutorials\Songs"; NZ=D+r"\Neil Zaza - Turn the World Around\Media\%s.ogg"
def load(f):
    x,sr=sf.read(f,always_2d=True); x=x.mean(1)
    return resample_poly(x,160,147) if sr==44100 else x
def best(x,T=6.0,hop=0.5,act_db=-30):
    n=int(T*SR); h=int(hop*SR); best=(-1,0)
    for a in range(0,len(x)-n,h):
        s=x[a:a+n]; w=s[:n//4800*4800].reshape(-1,4800); r=np.sqrt((w**2).mean(1)+1e-20)
        score=np.mean(20*np.log10(r/r.max())>act_db)*np.sqrt((s**2).mean())
        if score>best[0]: best=(score,a)
    return best[1]
src={}
dr=sum(load(NZ%k) for k in ["Kick Freeze","Snare Freeze","OH Freeze","Hat .01"])
src["drums"]=(dr,"NZ Kick+Snare+OH+Hat freeze")
src["bass"]=(load(NZ%"Bass"),"NZ Bass")
src["guitar"]=(load(NZ%"Clean GTR 1 U"),"NZ Clean GTR 1 U")
src["vocal"]=(load(D+r"\Emmavie - Electro Genie\Media\Main vocal.ogg"),"Emmavie Main vocal")
src["mix"]=(load(r"C:\Users\IdleHanz\Documents\Studio Pro\Songs\2026-08-20 Test Arranger\Mixdown\For Suno.wav"),"Idle 2026-08-20 Test Arranger mixdown (For Suno.wav)")
meta={}
for k,(x,d) in src.items():
    a=best(x); s=x[a:a+6*SR]; fd=int(0.01*SR); s[:fd]*=np.linspace(0,1,fd); s[-fd:]*=np.linspace(1,0,fd)
    s=(s/np.abs(s).max()).astype(np.float32); np.save(I+"real_%s.npy"%k,s); meta[k]={"src":d,"start_s":a/SR,"rms_dbfs":float(20*np.log10(np.sqrt((s**2).mean())))}
    print(k,meta[k])
json.dump(meta,open("real_meta.json","w"),indent=1)
# aliasing stairs: tones 7/9/13/17 kHz, 1 s per level; and 2-20 kHz log sweep
def tone_stair(f,levels,step=1.0): return S.stair(f,levels,step)
CL=[-24.0,-12.0,-6.0,0.0]
for f in (7000,9000,13000,17000): np.save(I+"al_%d.npy"%f,tone_stair(f,[0.0]*1).astype(np.float32))
t=np.arange(int(4*SR))/SR; f1,f2=2000.,20000.; L=4/np.log(f2/f1); sw=np.sin(2*np.pi*f1*L*(np.exp(t/L)-1)); np.save(I+"al_sweep.npy",sw.astype(np.float32))
# pre stairs 40/100/1k/5k: 20 levels, 0.5 s each
PL=list(np.arange(-30,12.1,2.0))  # relative to drive point
for f in (40,100,1000,5000): np.save(I+"pst3_%d.npy"%f,S.stair(f,[0.0]*1,0.1).astype(np.float32)*0)  # placeholder unused
def st(f,lv,step=0.5): return S.stair(f,lv,step)
jobs=[]
COMPS={"la2as_pr50":U.COMP["la2as_pr50"],"ssl_4_auto":U.COMP["ssl_4_auto"],"fet_all":U.COMP["fet_all"],"fc_t5":U.COMP["fc_t5"]}
NUKE=json.load(open(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb\handoff_build_support_2\roadmap\bloom\uad\round2\data\pass2_cal.json"))
LV=NUKE["prog_levels"]
COMPS["dis_nuke_room"]=(U.DIS,NUKE["NUKE_ROOM"],1.5,"P")
for u,(pl,pr,_,_) in COMPS.items():
    for k in src:
        for ab,g in (("a",LV[u]),("b",LV[u]+8)):
            jobs.append({"id":"rprog_%s_%s_%s"%(u,k,ab),"plugin":pl,"params":pr,"input":"real_%s.npy"%k,"gain_db":round(g,3)})
    for f in (7000,9000,13000,17000):
        for L in CL: jobs.append({"id":"al_%s_%d_%+d"%(u,f,L),"plugin":pl,"params":pr,"input":"al_%d.npy"%f,"gain_db":L})
    for L in (-12.0,0.0): jobs.append({"id":"alsw_%s_%+d"%(u,L),"plugin":pl,"params":pr,"input":"al_sweep.npy","gain_db":L})
PG={"neve":-36.0,"u610a":-57.0}
for p,g0 in PG.items():
    pl,pr=U.PRES[p][0],U.PRES[p][1]
    for k in src:
        for ab,d in (("+0",0.0),("-6",-6.0)):
            jobs.append({"id":"rpprog_%s_%s_%s"%(p,k,ab),"plugin":pl,"params":pr,"input":"real_%s.npy"%k,"gain_db":g0+d})
    for f in (7000,9000,13000,17000):
        for d in (-12.0,-6.0,0.0,6.0): jobs.append({"id":"al_%s_%d_%+d"%(p,f,d),"plugin":pl,"params":pr,"input":"al_%d.npy"%f,"gain_db":g0+d})
    for d in (0.0,6.0): jobs.append({"id":"alsw_%s_%+d"%(p,d),"plugin":pl,"params":pr,"input":"al_sweep.npy","gain_db":g0+d})
    for f in (40,100,1000,5000):
        lv=[g0+v for v in PL]; np.save(I+"pst3_%d.npy"%f,st(f,[0.0]*len(lv)).astype(np.float32))
        n=int(0.5*SR); keep=[[i*n+n//2,(i+1)*n] for i in range(len(lv))]
        # per-step gain: bake level into input (stair() uses dB peak); write a dedicated input per pre
        x=S.stair(f,lv,0.5).astype(np.float32); np.save(I+"pst3_%s_%d.npy"%(p,f),x)
        jobs.append({"id":"pst3_%s_%d"%(p,f),"plugin":pl,"params":pr,"input":"pst3_%s_%d.npy"%(p,f),"keep":keep,"levels":lv})
json.dump(jobs,open("jobs_r3.json","w"),indent=0); print(len(jobs),"jobs")
