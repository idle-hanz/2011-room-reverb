import numpy as np, json, os
O = '/workspace/uad2/out/'; I = '/workspace/uad2/inputs/'
_J = {}
for f in ('jobs_pass1.json', 'jobs_pass2.json'):
    p = '/workspace/uad2/jobs/' + f
    if os.path.exists(p):
        for j in json.load(open(p)): _J[j['id']] = j
def job(id_): return _J[id_]
def rec(id_, both=False):
    """(x, y) exactly as rendered: input float32 scaled by gain_db in float32."""
    j = _J[id_]; d = np.load(O + id_ + '.npz'); y = d['y'].astype(float)
    if 'spec' in j:
        import siglib2; x = siglib2.make(j['spec']).astype(np.float32)
    else:
        x = np.load(I + j['input']).astype(np.float32)
    if 'gain_db' in j: x = (x * np.float32(10 ** (j['gain_db'] / 20.0))).astype(np.float32)
    x = x.astype(float)
    if x.ndim == 2: x = x[0] if not both else x
    n = min(x.shape[-1], y.shape[-1])
    return (x[..., :n], y[..., :n]) if both else (x[:n], y[0, :n])
def xin(id_):
    j = _J[id_]
    if 'spec' in j:
        import siglib2; x = siglib2.make(j['spec']).astype(np.float32)
    else:
        x = np.load(I + j['input']).astype(np.float32)
    if 'gain_db' in j: x = (x * np.float32(10 ** (j['gain_db'] / 20.0))).astype(np.float32)
    return x.astype(float)
def env_rec(id_):
    d = np.load(O + id_ + '.npz'); return d['env_in'][0].astype(float), d['env'].astype(float), int(d['dec'])
