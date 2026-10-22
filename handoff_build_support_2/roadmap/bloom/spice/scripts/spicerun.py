import subprocess, numpy as np, os, tempfile
ROOT='/workspace/compressors/spice'
def run(name, body, vecs, tran=None, dc=None):
    """Write netlist, run ngspice batch, return dict of arrays (first col = sweep/time)."""
    raw=f'{ROOT}/raw/{name}.txt'
    ctl = '.control\nset wr_singlescale\nset wr_vecnames\noption numdgt=7\n'
    if tran: ctl += f'tran {tran}\n'
    if dc: ctl += f'dc {dc}\n'
    ctl += f'wrdata {raw} ' + ' '.join(vecs) + '\nquit\n.endc\n'
    net = f'* {name}\n.include {ROOT}/models/devices.lib\n' + body + '\n' + ctl + '.end\n'
    p=f'{ROOT}/netlists/{name}.cir'; open(p,'w').write(net)
    r=subprocess.run(['ngspice','-b',p],capture_output=True,text=True,timeout=900)
    open(f'{ROOT}/raw/{name}.log','w').write(r.stdout+r.stderr)
    d=np.genfromtxt(raw,names=True)
    return d
