_orig=_RP.fdn_delays_from_taps
_E=os.environ.get('EXP','none')
def _wrap(taps, sr=48000, c=343.0, n=32, channel='mean', **k):
    d=list(_orig(taps, sr=sr, c=c, n=n, channel=channel, **k))
    nt=len(taps)
    if _E=='direct_x1.1':
        for i in range(n):
            if tuple(taps[i%nt].n)==(0,0,0): d[i]=int(round(d[i]*1.1))
    elif _E=='l0_plus37':
        d[0]+=37
    elif _E=='jit03':
        for i in range(n):
            h=((i*2654435761+1*40503)&0xffffffff)/2**32*2-1
            d[i]=max(2,int(round(d[i]+h*0.0003*sr)))
    elif _E.endswith('uniq'):
        seen={}
        for i in range(n):
            while d[i] in seen.values(): d[i]+=17
            seen[i]=d[i]
    return d
_RP.fdn_delays_from_taps=_wrap
if _E.startswith('osign'):
    pass
if 'osign' in _E:
    import json as _j, numpy as _np
    _S=_np.array(_j.load(open(os.path.join(os.path.dirname(os.environ['DLYMOD']),'out_signs.json')))['s'],float)
    import fdn as _F
    _pbp=_F.FDN.process_block_poly
    def _pbp2(self, inject):
        y=_pbp(self, inject)
        return y*_S[None,:y.shape[1]]
    _F.FDN.process_block_poly=_pbp2
if 'nodirect' in _E:
    _rfi=_RP.render_fdn_ir
    def _rfi2(*a, **k):
        k['omit_direct_inject']=True
        return _rfi(*a, **k)
    _RP.render_fdn_ir=_rfi2
if 'rsign' in _E:
    import json as _j, numpy as _np, fdn as _F
    _D=_np.array(_j.load(open(os.path.join(os.path.dirname(os.environ['DLYMOD']),'out_signs.json')))['s'],float)
    _uhm=_F.unscaled_hadamard_matrix
    def _uhm2(n):
        H=_uhm(n)
        return (_D[:n,None]*H) if n==32 else H
    _F.unscaled_hadamard_matrix=_uhm2
if 'csign' in _E:
    import json as _j, numpy as _np, fdn as _F
    _D2=_np.array(_j.load(open(os.path.join(os.path.dirname(os.environ['DLYMOD']),'out_signs.json')))['s'],float)
    _uhm_c=_F.unscaled_hadamard_matrix
    def _uhm3(n):
        H=_uhm_c(n)
        return (H*_D2[None,:n]) if n==32 else H
    _F.unscaled_hadamard_matrix=_uhm3
