import json, numpy as np, soundfile as sf, os
from scipy.signal import butter, sosfiltfilt, hilbert
from scipy.ndimage import median_filter, uniform_filter1d
fs=48000; OUT='/workspace/build_support_2/roadmap/eq_plan/proto_mod'; os.makedirs(OUT,exist_ok=True)
V=['before','mod10','mod15','dcap','mod10dcap']; PK=(157,261,724,781,1285,2008)
def path(kind,v): return f'out/{kind}_before.f32' if (v=='before' and kind!='tone') else f'out2/{kind}_{v}.f32'
def ld(n): return np.fromfile(n,np.float32).reshape(-1,2).astype(float)
res={'setup':{'room':'default (app DEFAULTS), FDN only (early_wet 0, direct_wet 0, colour BYPASS), 48 kHz, Render path, box scratch copy of the 18:29 audit tree',
 'mod':'Frenette: sine, peak depth 0.10 ms (4.8 samples) or 0.15 ms (7.2 samples), base 0.7 Hz x 0.6..1.4 per line (golden-ratio spread), phase k*112.5 deg, 16 of 32 lines (every other line by sorted length, per bus), 1st-order allpass interpolation (N=floor(D-0.5), eta=(1-d)/(1+d)), coefficient update every sample, mean delay unchanged',
 'dcap':'|Dffs| clipped to 0.7 on every line (default room: 5 of 32 lines were at 0.98)',
 'variants':{'before':'today','mod10':'mod 0.10 ms','mod15':'mod 0.15 ms','dcap':'Dffs cap 0.7 only','mod10dcap':'mod 0.10 ms + Dffs cap 0.7'},
 'zero_depth_check':'MOD_MS=1e-9 vs off: max abs diff 3.7e-9 (float32 rounding)',
 'tail_metrics':'IR, L+R mean, 1.8 s decay removed, 1 s Hann windows at 0.3/0.8/1.3/2.0 s, 1 Hz bins, 100 Hz-8 kHz, residual vs 301-bin running median; values are the mean over the 4 windows',
 'wobble':'440 Hz sine (3.5 s) run through the loop; wet output band-passed 380-500 Hz, Hilbert instantaneous frequency, 20 ms smoothing, 1.5-3.4 s; cents vs 440',
 'guitar':'test_guitar_dualmono.wav run THROUGH the loop; equal RMS, then one shared gain to -1 dBFS peak, 24-bit'}}
for v in V:
    x=ld(path('ir',v)); m=x.mean(1); r={}
    stds=[]; pk={p:[] for p in PK}
    for a in (0.3,0.8,1.3,2.0):
        i0=int(round(a*fs)); sg=m[i0:i0+fs]; tt=np.arange(fs)/fs+a; sg=sg*10**(3*tt/1.8)
        X=np.abs(np.fft.rfft(sg*np.hanning(fs))); f=np.fft.rfftfreq(fs,1/fs); k=(f>100)&(f<8000)
        q=20*np.log10(X[k]+1e-20); q=q-median_filter(q,301); fk=f[k]; stds.append(np.std(q))
        for p in PK: pk[p].append(q[(fk>p-2.5)&(fk<p+2.5)].max())
    r['peakiness_db']=round(float(np.mean(stds)),2); r['peakiness_range']=[round(float(min(stds)),2),round(float(max(stds)),2)]
    r['peaks_db_over_median']={str(p):round(float(np.mean(pk[p])),1) for p in PK}
    t30={}
    for fc in (63,125,250,500,1000,2000,4000,8000):
        sos=butter(4,[fc/2**.5,min(fc*2**.5,23000)],btype='band',fs=fs,output='sos'); vals=[]
        for ch in range(2):
            y=sosfiltfilt(sos,x[:,ch])**2; e=np.cumsum(y[::-1])[::-1]; e=10*np.log10(e/e[0]+1e-30)
            i5=np.argmax(e<=-5); i35=np.argmax(e<=-35); vals.append(-60/np.polyfit(np.arange(i5,i35)/fs,e[i5:i35],1)[0])
        t30[str(fc)]=round(float(np.mean(vals)),3)
    r['T30_s']=t30
    w=ld(path('tone',v)).mean(1); sos=butter(4,[380,500],btype='band',fs=fs,output='sos'); b=sosfiltfilt(sos,w)
    ph=np.unwrap(np.angle(hilbert(b))); fi=np.diff(ph)*fs/(2*np.pi); fi=uniform_filter1d(fi,int(0.02*fs))[int(1.5*fs):int(3.4*fs)]
    c=1200*np.log2(np.maximum(fi,1)/440.0); c=c-np.median(c)
    r['wobble_cents']={'rms':round(float(np.sqrt(np.mean(c**2))),2),'p95_abs':round(float(np.percentile(np.abs(c),95)),2),'max_abs':round(float(np.max(np.abs(c))),2)}
    res[v]=r
B=res['before']
for v in V[1:]:
    res[v]['peak_reduction_db']={p:round(B['peaks_db_over_median'][p]-res[v]['peaks_db_over_median'][p],1) for p in B['peaks_db_over_median']}
    res[v]['T30_change_pct']={b:round(100*(res[v]['T30_s'][b]/B['T30_s'][b]-1),1) for b in B['T30_s']}
if os.environ.get("SKIP_G"):
    [print(v, res[v]["peakiness_db"], res[v]["peaks_db_over_median"], res[v].get("peak_reduction_db"), res[v].get("T30_change_pct"), res[v]["wobble_cents"]) for v in V]; raise SystemExit
G={v:ld(path('gtr',v)) for v in V}; rms={v:np.sqrt(np.mean(G[v]**2)) for v in V}
for v in V: G[v]*=rms['before']/rms[v]
g=10**(-1/20)/max(np.max(np.abs(G[v])) for v in V)
res['guitar_level_match']={'match_gain_db':{v:round(20*np.log10(rms['before']/rms[v]),2) for v in V},'shared_gain_db':round(20*np.log10(g),2)}
for v in V: sf.write(f'{OUT}/default_guitar_{v}.wav',G[v]*g,fs,subtype='PCM_24')
json.dump(res,open(f'{OUT}/proto_mod.json','w'),indent=1)
for v in V: print(v, res[v]['peakiness_db'], res[v]['peaks_db_over_median'], res[v].get('peak_reduction_db'), res[v].get('T30_change_pct'), res[v]['wobble_cents'])
print(res['guitar_level_match'])
