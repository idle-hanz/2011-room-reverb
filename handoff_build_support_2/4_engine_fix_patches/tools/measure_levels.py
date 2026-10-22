"""Bus-level measurement (build_support_2, headroom decision 6).
For each tree x scene x bus: Play IR energy (real worklet+wasm in node) and Render IR energy
(render_pipeline.render, clip_guard undone). Energy dB = 10log10(sum over both channels of h^2),
i.e. the steady white-noise level change. Also the t14 noise run (peak, RMS first 3 s).
Usage: python measure_levels.py out.json name=/path/to/software [name=/path ...] [--no-render]
Source position pinned (sy given per scene) so K3 default moves do not enter the F2+F3 comparison."""
import sys, json, argparse
from pathlib import Path
import numpy as np
H = Path(__file__).resolve().parents[2] / '3_phase_acceptance_tests' / 'harness'
sys.path[:0] = [str(H), str(H / 'lib')]
import run_all as RA

SCN = {
    'std_lock18':   dict(RA.SCENES['std_lock18'], sx=3.0, sy=1.5),
    'small_lock08': dict(RA.SCENES['small_lock08'], sy=1.5),
    'hall_lock40':  dict(RA.SCENES['hall_lock40'], sy=1.5),
}
BUS = {
    'fdn':    dict(fdn_wet=1.0, direct_wet=0.0, early_wet=0.0),
    'direct': dict(fdn_wet=0.0, direct_wet=1.0, early_wet=0.0),
    'early':  dict(fdn_wet=0.0, direct_wet=0.0, early_wet=1.0),
    'all':    dict(fdn_wet=1.0, direct_wet=1.0, early_wet=1.0),
}
def edb(x): return round(10 * np.log10(max(float(np.sum(x * x)), 1e-30)), 2)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('trees', nargs='+')
    ap.add_argument('--no-render', action='store_true'); ap.add_argument('--dm', type=float, default=None,
                    help='pin diffusion_master (e.g. -0.5 to isolate F2+F3 from the -0.25 default)')
    ap.add_argument('--extra', default='{}', help='JSON merged into every scene body (e.g. {"air_lp": 0.25})')
    ap.add_argument('--buses', default='fdn,direct,early,all')
    a = ap.parse_args()
    res = {}
    for spec in a.trees:
        name, sw = spec.split('=', 1)
        ns = argparse.Namespace(sw=sw, python=sys.executable, node='node', golden=str(H / 'golden'), regen_golden=False,
                                quick=True, perf_scale=1.0, workdir='/tmp')
        c = RA.Ctx(ns); r = res[name] = {}
        for sn, sc in SCN.items():
            for bn, bv in BUS.items():
                if bn not in a.buses.split(','): continue
                body = dict(sc, **bv); body.update(json.loads(a.extra))
                if a.dm is not None: body['diffusion_master'] = a.dm
                secs = 6.0 if sn == 'hall_lock40' else 3.0
                ir = c.play_ir(body, {}, secs)
                row = r.setdefault(sn, {}).setdefault(bn, {})
                row['play_db'] = edb(ir)
                if not a.no_render and bn in ('fdn', 'all', 'direct'):
                    rir = c.render_ir(body, secs * 1000)
                    row['render_db'] = edb(rir)
                print(name, sn, bn, row, flush=True)
        # t14 exactly (std_lock18 as run_all has it, tree defaults)
        p = c.params('std_lock18'); out = c.work / 'lvl.f32'
        c.play(p, {}, 'noise', 3, 4, out)
        x = np.fromfile(out, np.float32).reshape(-1, 2)
        r['t14'] = {'play_peak': round(float(np.max(np.abs(x))), 4), 'play_rms_db': round(RA.rms_db(x[:3 * RA.SR]), 2)}
        p = c.params(dict(SCN['std_lock18'], **json.loads(a.extra), **({'diffusion_master': a.dm} if a.dm is not None else {}))); c.play(p, {}, 'noise', 3, 4, out)
        x = np.fromfile(out, np.float32).reshape(-1, 2)
        r['t14_pinned_src'] = {'play_peak': round(float(np.max(np.abs(x))), 4), 'play_rms_db': round(RA.rms_db(x[:3 * RA.SR]), 2)}
        print(name, 't14', r['t14'], r['t14_pinned_src'], flush=True)
    json.dump(res, open(a.out, 'w'), indent=1)
main()
