import json, numpy as np, soundfile as sf, os
from scipy.signal import butter, sosfiltfilt
from scipy.ndimage import median_filter
fs=48000; V=['before','rot5','rot10']; OUT='/workspace/build_support_2/roadmap/eq_plan/proto_rot'
os.makedirs(OUT,exist_ok=True)
def ld(n): return np.fromfile(n,np.float32).reshape(-1,2).astype(float)
res={'setup':{'room':'default (app DEFAULTS), FDN only: early_wet 0, direct_wet 0, colour BYPASS, 48 kHz, Render path (box scratch copy of the 18:29 audit tree)',
 'rotation':'one FWHT butterfly stage (distance 16, the outer stage) uses Ref(theta), theta = pi/4 + eps*pi*sin(2*pi*f*t), t from sample 0; H·D column signs kept; orthogonal at every sample (checked 7e-15)',
 'variants':{'before':'eps 0 (bit-exact engine path)','rot5':'eps 0.05 pi (9 deg), 0.3 Hz','rot10':'eps 0.10 pi (18 deg), 0.5 Hz'},
 'tail_window':'0.3-1.3 s of the IR, L+R mean, 1.8 s decay removed, Hann, 1 Hz bins, 100 Hz-8 kHz, residual vs 301-bin running median',
 'guitar':'test_guitar_dualmono.wav (12 s, mono) run THROUGH the time-varying FDN (inject convolved with guitar before the loop), not IR convolution'}}
ref=ld('/workspace/build_support_2/roadmap/eq_plan/measure/def_fdn.f32')
for v in V:
    x=ld(f'out/ir_{v}.f32'); m=x.mean(1); r={}
    if v=='before':
        n=min(len(ref),len(x)); res['setup']['before_vs_v2_def_fdn_maxabs']=float(np.max(np.abs(ref[:n]-x[:n])))
    seg=m[int(.3*fs):int(1.3*fs)]; t=np.arange(len(seg))/fs; seg=seg*10**(3*t/1.8)
    X=np.abs(np.fft.rfft(seg*np.hanning(len(seg)))); f=np.fft.rfftfreq(len(seg),1/fs)
    k=(f>100)&(f<8000); L=20*np.log10(X[k]+1e-20); rr=L-median_filter(L,301); fk=f[k]
    r['peakiness_std_db']=round(float(np.std(rr)),2)
    r['peaks_db_over_median']={str(p):round(float(rr[(fk>p-2.5)&(fk<p+2.5)].max()),1) for p in (724,781,1285,2008)}
    r['top5_now']=[(round(float(fk[i]),0),round(float(rr[i]),1)) for i in np.argsort(rr)[::-1][:5]]
    mw={'std':[],724:[],781:[],1285:[],2008:[]}
    for a in (0.3,0.8,1.3,2.0):
        i0=int(round(a*fs)); sg=m[i0:i0+len(seg)]; tt=np.arange(len(sg))/fs+a; sg=sg*10**(3*tt/1.8)
        XX=np.abs(np.fft.rfft(sg*np.hanning(len(sg)))); q=20*np.log10(XX[k]+1e-20); q=q-median_filter(q,301)
        mw['std'].append(np.std(q))
        for p in (724,781,1285,2008): mw[p].append(q[(fk>p-2.5)&(fk<p+2.5)].max())
    r['four_windows_0.3_0.8_1.3_2.0s']={'peakiness_mean_db':round(float(np.mean(mw['std'])),2),'peakiness_range_db':[round(float(min(mw['std'])),2),round(float(max(mw['std'])),2)],
        'peak_mean_db':{str(p):round(float(np.mean(mw[p])),1) for p in (724,781,1285,2008)}}
    t30={}
    for fc in (63,125,250,500,1000,2000,4000,8000):
        sos=butter(4,[fc/2**.5,min(fc*2**.5,23000)],btype='band',fs=fs,output='sos'); vals=[]
        for ch in range(2):
            y=sosfiltfilt(sos,x[:,ch])**2; e=np.cumsum(y[::-1])[::-1]; e=10*np.log10(e/e[0]+1e-30)
            i5=np.argmax(e<=-5); i35=np.argmax(e<=-35); tt=np.arange(i5,i35)/fs
            sl=np.polyfit(tt,e[i5:i35],1)[0]; vals.append(-60/sl)
        t30[str(fc)]=round(float(np.mean(vals)),3)
    r['T30_s']=t30; res[v]=r
for v in ('rot5','rot10'):
    res[v]['T30_change_pct']={b:round(100*(res[v]['T30_s'][b]/res['before']['T30_s'][b]-1),1) for b in res['before']['T30_s']}
    res[v]['peak_reduction_4win_db']={p:round(res['before']['four_windows_0.3_0.8_1.3_2.0s']['peak_mean_db'][p]-res[v]['four_windows_0.3_0.8_1.3_2.0s']['peak_mean_db'][p],1) for p in ('724','781','1285','2008')}
    res[v]['peak_reduction_db']={p:round(res['before']['peaks_db_over_median'][p]-res[v]['peaks_db_over_median'][p],1) for p in res['before']['peaks_db_over_median']}
if os.environ.get("SKIP_G"): print(json.dumps(res,indent=1)); raise SystemExit
# guitar: level-match by RMS to 'before', then one common gain to -1 dBFS peak
G={v:ld(f'out/gtr_{v}.f32') for v in V}
rms={v:np.sqrt(np.mean(G[v]**2)) for v in V}
for v in V: G[v]*=rms['before']/rms[v]
pk=max(np.max(np.abs(G[v])) for v in V); g=10**(-1/20)/pk
res['guitar_level_match']={'method':'equal RMS over the whole file, then one shared gain to -1 dBFS peak; 24-bit WAV',
  'match_gain_db':{v:round(20*np.log10(rms['before']/rms[v]),2) for v in V},'shared_gain_db':round(20*np.log10(g),2)}
for v in V: sf.write(f'{OUT}/default_guitar_{v}.wav',G[v]*g,fs,subtype='PCM_24')
json.dump(res,open(f'{OUT}/proto_rot.json','w'),indent=1); print(json.dumps(res,indent=1))
