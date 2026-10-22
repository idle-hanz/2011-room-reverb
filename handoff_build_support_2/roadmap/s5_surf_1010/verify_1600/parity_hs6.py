"""All-faces HS+6 move, new tree: |(Play hs6 - Play default) - (Render hs6 - Render default)|, third-octave, L/R mean."""
import numpy as np, json
SR=48000; FC=[125,160,200,250,315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300,8000,10000,12500,16000]
def bands(x):
    X=np.abs(np.fft.rfft(x))**2; f=np.fft.rfftfreq(len(x),1/SR); return np.array([X[(f>=c*2**-(1/6))&(f<c*2**(1/6))].sum()+1e-30 for c in FC])
def ld(n): return np.fromfile(f'new_9b7cdf/{n}.f32',np.float32).reshape(-1,2).astype(np.float64)
out={}
for bus in ('mix','early','fdn'):
    for w,(a,b) in {'0-80ms':(0,int(.08*SR)),'80ms+':(int(.08*SR),None),'full':(0,None)}.items():
        m=lambda e,c: np.mean([10*np.log10(bands(ld(f'{e}_hs6_all_{bus}')[a:b,ch])/bands(ld(f'{e}_default_{bus}')[a:b,ch])) for ch in (0,1)],axis=0)
        d=np.abs(m('play',0)-m('render',0)); i=int(np.argmax(d)); out[f'{bus}|{w}']={'max_abs_db':round(float(d.max()),3),'at_hz':FC[i]}
        print(bus,w,out[f'{bus}|{w}'])
json.dump(out,open('parity_hs6_all.json','w'),indent=1)
