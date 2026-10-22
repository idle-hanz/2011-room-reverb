import os, sys, json, numpy as np, wave
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import hall_b as HB
SR=44100; H=os.path.dirname(os.path.abspath(__file__)); OUT=H+'/ab_wav_d14'; os.makedirs(OUT,exist_ok=True)
d=np.load(HB.R+'/real/dry_est_0.001.npy').astype(float)[2*SR:22*SR]; d=d/np.max(np.abs(d))*0.5
fin=H+'/w/real20_in.f32'; np.stack([d,d],1).astype(np.float32).tofile(fin)
def wav(p,y):
    pcm=(np.clip(y,-1,1)*32767).astype('<i2')
    with wave.open(p,'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
rms=lambda y: float(20*np.log10(np.sqrt(np.mean(y**2))))
res={}
# D14 A/B inside Build's Fix2 band (hall median |dffs| 0.35-0.70); all with column signs
VAR={'hall_preset_parity':(('A_today',None,'ship'),('D_column_signs',None,'csign'),('F_cap130_column_signs_med036',130,'csign'),('G_cap90_column_signs_med052',90,'csign')),
     'bigroom_default_surfaces':(('A_today',None,'ship'),('D_column_signs',None,'csign'),('H_cap18_column_signs_med049',18,'csign'))}
for sc,b in HB.SC.items():
    outs=[]
    for name,cap,wn in VAR[sc]:
        y,_=HB.run(sc,b,cap,HB.FW+wn+'.wasm',sr=SR,mode='file',args=(fin,),tag=f'{sc}_{name}_44k')
        outs.append((name,y))
    a=outs[0][1]; k=0.7/max(np.max(np.abs(y)) for _,y in outs)
    for name,y in outs:
        g=10**((rms(a)-rms(y))/20); p=f'{OUT}/{sc}__{name}.wav'; wav(p,y*k*g)
        res[f'{sc}|{name}']=dict(path=p,raw_minus_A_db=round(rms(y)-rms(a),2))
        print(sc,name,res[f'{sc}|{name}'],flush=True)
json.dump(res,open(H+'/hall_wav_d14.json','w'),indent=1)
