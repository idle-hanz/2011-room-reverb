import os, sys, json, numpy as np, wave
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import hall_b as HB
SR=44100; H=os.path.dirname(os.path.abspath(__file__)); OUT=H+'/ab_wav'; os.makedirs(OUT,exist_ok=True)
d=np.load(HB.R+'/real/dry_est_0.001.npy').astype(float)[2*SR:22*SR]; d=d/np.max(np.abs(d))*0.5
fin=H+'/w/real20_in.f32'; np.stack([d,d],1).astype(np.float32).tofile(fin)
def wav(p,y):
    pcm=(np.clip(y,-1,1)*32767).astype('<i2')
    with wave.open(p,'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
rms=lambda y: float(20*np.log10(np.sqrt(np.mean(y**2))))
res={}
for sc,b in HB.SC.items():
    outs=[]
    for name,cap,wn in (('A_today',None,'ship'),('B_output_signs',None,'osign'),('C_cap50_plus_output_signs',50,'osign'),('D_column_signs',None,'csign'),('E_cap50_plus_column_signs',50,'csign')):
        y,_=HB.run(sc,b,cap,HB.FW+wn+'.wasm',sr=SR,mode='file',args=(fin,),tag=f'{sc}_{name}_44k')
        outs.append((name,y))
    a=outs[0][1]; k=0.7/max(np.max(np.abs(y)) for _,y in outs)
    for name,y in outs:
        g=10**((rms(a)-rms(y))/20); p=f'{OUT}/{sc}__{name}.wav'; wav(p,y*k*g)
        res[f'{sc}|{name}']=dict(path=p,raw_minus_A_db=round(rms(y)-rms(a),2))
        print(sc,name,res[f'{sc}|{name}'],flush=True)
json.dump(res,open(H+'/hall_wav.json','w'),indent=1)
