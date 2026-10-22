import sys; sys.argv=['x','neve','poly3']
exec(open('pre_fit.py').read().split("results = {}")[0])
for kind,id_,x,keep,ts,rms in PREP:
    c=[float(np.sum((ti/ri)**2)/len(ti)) for ti,ri in zip(ts,rms) if ri>10**(-70/20)]
    print(id_, len(ts), 'steps used', len(c), 'max rel resid power %.3g'%max(c) if c else '', 'median %.3g'%np.median(c) if c else '')
