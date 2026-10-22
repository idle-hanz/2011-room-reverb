import sys; sys.path.insert(0,'/workspace/uad3'); import targets as T, dyn3, numpy as np, time
for p in dyn3.DEF:
    t=time.time(); P=dict(dyn3.DEF[p]); P['T']=T.FIT[p]['T'] if p!='swell' and p!='nuke' else T.FIT[p]['T']
    s=T.static(p,P); e=s-T.UAD_STATIC[p]; a=T.attack(p,P)
    print(p,'static rms %.2f max %.2f'%(np.sqrt(np.mean(e**2)),np.abs(e).max()),'t63',a['t63_ms'],'t90',a['t90_ms'], '%.1fs'%(time.time()-t))
    for dep,bs,mu,m in T.bursts(p,P): print('   ',dep,bs,'att90 %s/%s rel63 %s/%s rel90 %s/%s'%(mu['att90'],m['att90'],mu['rel63'],m['rel63'],mu['rel90'],m['rel90']))
