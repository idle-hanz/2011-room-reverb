"""Runs INSIDE one software tree (read-only import) and emits either a Render IR or the
live_fdn_params JSON that Play receives.  Called by compare_ref.py as a subprocess so each
tree (current / F1-F3 / F1-F3+F5) is imported in its own interpreter.

Usage:
  python rr_tree_driver.py <software_dir> render '<job json>' <out.f32>
  python rr_tree_driver.py <software_dir> params '<job json>' <out.json>
job json: {"body": {...app body...}, "ir_ms": 8000, "sr": 48000, "dffs_knob": null|float}
Nothing in software/ is written.  dffs_knob (optional) overrides the Room-Dimension
"Diffusion" knob constant (fdn.DFFS_KNOB_DEFAULT = 0.0333, from the 2011 live dump) by
wrapping diffusion_scale_from_room in-process only.
"""
import sys, os, json, time
import numpy as np

sw = os.path.abspath(sys.argv[1]); mode = sys.argv[2]; job = json.loads(sys.argv[3]); out = sys.argv[4]
sys.path[:0] = [sw, os.path.join(sw, 'engine')]
os.chdir(sw)
import app_server as A
import render_pipeline as RP

knob = job.get('dffs_knob')
if knob is not None:
    _orig = RP.diffusion_scale_from_room
    def _patched(room, knob_=None, _k=float(knob)):
        return _orig(room, _k)
    RP.diffusion_scale_from_room = _patched

sr = int(job.get('sr', 48000))
body = dict(A.DEFAULTS); body.update(job['body'])

if mode == 'params':
    body['sample_rate'] = sr
    p = A.params_from_body(body)
    P = A.live_fdn_params(p)
    json.dump(P, open(out, 'w'))
    print(json.dumps({'g': P.get('g'), 'makeup': P.get('makeup'), 'decay_s': P.get('decay_s'),
                      'line_t60': P.get('line_t60'),
                      'dffs_c_min_max': [min(P['buses']['c']['dffs']), max(P['buses']['c']['dffs'])]}))
    sys.exit(0)

body['ir_length_ms'] = float(job.get('ir_ms', 8000))
p = A.params_from_body(body)
dry = np.zeros(1); dry[0] = 1.0
t0 = time.time()
kw = dict(
    W=p["W"], H=p["H"], L=p["L"], sox=p["sox"], soz=p["soz"], mz=p["mz"], my=p["my"], sy=p.get("sy"),
    sx=p["sx"], sz=p["sz"], mcz=p["mcz"], space=p["space"], diverg=p["diverg"], car_omni=p["car_omni"],
    early_wet=p["early_wet"], fdn_wet=p["fdn_wet"], dry_gain=p["dry_gain"], direct_wet=p.get("direct_wet", 1.0),
    fdn_g=p["fdn_g"], ir_length_ms=p["ir_length_ms"], path_on=p["path_on"], path_preset=p["path_preset"],
    ellipse_rate=p["ellipse_rate"], ellipse_rx=p["ellipse_rx"], ellipse_rz=p["ellipse_rz"],
    mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"), hadamard_n=p["hadamard_n"],
    pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"),
    yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"),
    family_l=p.get("family_l"), family_c=p.get("family_c"), family_r=p.get("family_r"),
    polar_l=p.get("polar_l"), polar_c=p.get("polar_c"), polar_r=p.get("polar_r"),
    centre_dz=p.get("centre_dz") or 0.0, mic_hp_on=p.get("mic_hp_on") or False, mic_hp_hz=p.get("mic_hp_hz") or 40.0,
    mic_response_hz=p.get("mic_response_hz") or 10000.0, mic_proximity=p.get("mic_proximity") or 0.0,
    ms_decode=bool(p.get("ms_decode")), capsule_mm=p.get("capsule_mm") or 17.0, surfaces=p.get("surfaces"),
    diffusion_seed=p["diffusion_seed"], lambda_ref=p["lambda_ref"], humidity=p.get("humidity") or 0.0,
    air_lp=p.get("air_lp") if p.get("air_lp") is not None else 0.25,
    air_shelf=p.get("air_shelf") if p.get("air_shelf") is not None else 1.0,
    diffusion_master=p.get("diffusion_master") if p.get("diffusion_master") is not None else -0.5,
    decay_s=p.get("decay_s") or 0.0, decay_lock=bool(p.get("decay_lock")),
    mic_gain_l=p.get("mic_gain_l", 1.0), mic_gain_c=p.get("mic_gain_c", 1.0), mic_gain_r=p.get("mic_gain_r", 1.0),
    mic_pan_l=p.get("mic_pan_l", -1.0), mic_pan_c=p.get("mic_pan_c", 0.0), mic_pan_r=p.get("mic_pan_r", 1.0),
    mic_phase_l=p.get("mic_phase_l", 1.0), mic_phase_c=p.get("mic_phase_c", 1.0), mic_phase_r=p.get("mic_phase_r", 1.0),
    two_sources=False, source_balance=p.get("source_balance") or 0.0, mirror_b=bool(p.get("mirror_b")),
    sx_b=p.get("sx_b"), sy_b=p.get("sy_b"), sz_b=p.get("sz_b"), dry_l=None, dry_r=None,
    colour_mode=p.get("colour_mode") or "MEASURED_SHELF",
    mic_preset_l=p.get("mic_preset_l") or "ShureSM57", mic_preset_c=p.get("mic_preset_c") or "ShureSM57",
    mic_preset_r=p.get("mic_preset_r") or "ShureSM57", mic_hpf_engaged=bool(p.get("mic_hpf_engaged")),
    mic_hpf_sides=p.get("mic_hpf_sides"), mic_hpf_centre=p.get("mic_hpf_centre"),
)
import inspect
sig = inspect.signature(RP.render).parameters
kw = {k: v for k, v in kw.items() if k in sig}   # tolerate trees with fewer kwargs
L, R, info = RP.render(dry, sr, **kw)
sc = float(info.get('norm_scale') or 1.0)
L = np.asarray(L) / sc; R = np.asarray(R) / sc
np.stack([L, R], 1).astype(np.float32).tofile(out)
print(json.dumps({'secs': round(time.time() - t0, 1), 'n': len(L), 'norm_scale': sc}))
