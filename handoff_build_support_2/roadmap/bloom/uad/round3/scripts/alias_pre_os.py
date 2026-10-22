import sys; sys.path.insert(0,'/workspace/uad3'); import alias_proto as A, alias as AL, csv, numpy as np
U={(r['unit'],r['f'],r['in_db']):r for r in csv.DictReader(open('/workspace/uad3/alias_uad_tones.csv'))}
A.pre_y.__globals__  # noqa
def pre_os(p,x,os_):
    import json, prelib
    from scipy.signal import resample_poly
    ch=json.load(open('/workspace/uad3/pre_choice.json'))[p]; m=prelib.Pre(p,ch['cfg']); prelib.SR=48000*os_
    try: d=resample_poly(m.nl(resample_poly(x,os_,1),ch['th']),1,os_)[:len(x)]
    finally: prelib.SR=48000
    return prelib.lin(x,m.k)+prelib.lin(d,m.kn)
out=open('/workspace/uad3/alias_pre_os.txt','w')
for p in ('neve','u610a'):
  for os_ in (4,8,16):
    worst=-999; worstm=-999
    for f in (7000,9000,13000,17000):
      for L in ('-12','-6','+0','+6'):
        x=A.xin('al_%s_%d_%s'%(p,f,L)); a=AL.tone_alias(pre_os(p,x,os_),f)
        u=U.get((p,str(f),L)) or U.get((p,str(f),L.replace('+','')))
        ua=float(u['m1_worst_alias_dbfs']) if u else np.nan
        worst=max(worst,a['m1_worst_alias_dbfs']); worstm=max(worstm,a['m1_worst_alias_dbfs']-ua)
        s='%s %dx f%d L%s proto M1 %.1f M2<16k %.1f | UAD %.1f | margin %.1f'%(p,os_,f,L,a['m1_worst_alias_dbfs'],a['m2_peak_below16k_dbfs'],ua,a['m1_worst_alias_dbfs']-ua); print(s,flush=True); out.write(s+'\n')
    s='== %s %dx worst %.1f dBFS, worst margin vs UAD %+.1f dB'%(p,os_,worst,worstm); print(s,flush=True); out.write(s+'\n')
