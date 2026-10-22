# Synthetic, reproducible dry test file (mono 48 kHz, 24-bit): clicks, pink-noise bursts, plucked arpeggio, staccato chords, a sustained chord with hard stop.
import numpy as np, soundfile as sf
SR=48000; rng=np.random.default_rng(2011); out=[]
def sil(s): return np.zeros(int(s*SR))
def click():
    x=np.zeros(int(0.002*SR)); x[0]=1.0; x[1]=-0.5; return x
def pink(n):
    w=rng.standard_normal(n); X=np.fft.rfft(w); f=np.fft.rfftfreq(n,1/SR); X[1:]/=np.sqrt(f[1:]); X[0]=0; y=np.fft.irfft(X,n); return y/np.max(np.abs(y))
def ks(f0,dur,amp=0.8):
    n=int(dur*SR); p=int(SR/f0); buf=rng.uniform(-1,1,p); y=np.zeros(n)
    for i in range(n): y[i]=buf[i%p]; buf[i%p]=0.996*0.5*(buf[i%p]+buf[(i+1)%p])
    return amp*y
def saw_chord(fs,dur,att=0.01,rel=0.005):
    t=np.arange(int(dur*SR))/SR; y=sum(2*((f*t)%1)-1 for f in fs)/len(fs)
    env=np.minimum(1,t/att)*np.minimum(1,(dur-t)/rel); return 0.5*y*env
for _ in range(4): out+= [click(), sil(1.2)]
for _ in range(3):
    b=pink(int(0.2*SR)); env=np.minimum(1,np.arange(b.size)/240)*np.minimum(1,(b.size-np.arange(b.size))/240); out+=[0.5*b*env, sil(1.3)]
for f in [196,247,294,392,494,587,784]: out.append(ks(f,0.18))
out.append(sil(2.0))
for _ in range(4): out+=[saw_chord([220,277.2,329.6],0.12), sil(0.35)]
out.append(sil(1.5)); out+=[saw_chord([130.8,164.8,196,261.6],2.0), sil(3.5)]
x=np.concatenate(out); x=0.5*x/np.max(np.abs(x))
sf.write('dry_test_48k.wav',x.astype(np.float32),SR,subtype='PCM_24'); print(len(x)/SR,'s')
