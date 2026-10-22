import numpy as np, glob, json, os
sr=48000
def ned_curve(m, t0=0.05, t1=0.8, w=0.02):
    out=[]
    for c in np.arange(t0,t1,0.01):
        a=m[int((c-w/2)*sr):int((c+w/2)*sr)]; a=a-a.mean(); s=a.std()
        out.append(float(np.mean(np.abs(a)>s)/0.3173) if s>0 else 0)
    return np.array(out)
if __name__=='__main__':
    res={}
    if __name__!="__main__": pass
    for f in sorted(glob.glob('w/ir_*_48000.f32')):
        x=np.fromfile(f,np.float32).reshape(-1,2).astype(float); m=x.mean(1)
        n=ned_curve(m); tag=os.path.basename(f)[3:-4]
        res[tag]=dict(ned_0p05_0p2=round(float(n[:15].mean()),2), ned_0p2_0p4=round(float(n[15:35].mean()),2), ned_0p4_0p8=round(float(n[35:].mean()),2),
                      t_ned_0p8=(round(0.05+0.01*int(np.argmax(n>0.8)),2) if np.any(n>0.8) else None))
        print(tag,res[tag])
    json.dump(res,open('hall_b_density.json','w'),indent=1)
