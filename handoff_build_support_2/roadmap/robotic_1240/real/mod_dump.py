_orig=_RP.fdn_delays_from_taps
def _wrap(taps, sr=48000, c=343.0, n=32, channel='mean', **k):
    d=_orig(taps, sr=sr, c=c, n=n, channel=channel, **k)
    if channel=='c':
        import json as _j
        print('DLY', _j.dumps([(i, list(taps[i%len(taps)].n), d[i], round(d[i]/sr*1000,3)) for i in range(n)]), file=sys.stderr)
    return d
_RP.fdn_delays_from_taps=_wrap
