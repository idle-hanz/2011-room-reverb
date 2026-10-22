"""Benchmark + accuracy: Build's loop apply_sos vs apply_sos_numpy vs scipy.signal.sosfilt.
Usage: python bench_apply_sos.py <software_dir> [seconds]"""
import sys, os, time, json
import numpy as np
sw = os.path.abspath(sys.argv[1]); secs = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
sys.path[:0] = [sw, os.path.join(sw, 'engine'), os.path.dirname(os.path.abspath(__file__))]
from mic_colour.preset_store import get_store
from mic_colour.sos_table import pack_for
from mic_colour.sos_fit import apply_sos, unpack_record
from apply_sos_fast import apply_sos_numpy
try:
    from scipy.signal import sosfilt
except Exception:
    sosfilt = None
st = get_store(); sr = 48000
rng = np.random.default_rng(1); x = rng.standard_normal(int(secs * sr)) * 0.3
res = {'signal_s': secs, 'sr': sr, 'cases': []}
for mic, deg, hpf in (('ShureSM57', 90.0, False), ('NeumannU87AiOmni', 180.0, False), ('AKGC414Cardioid', 120.0, True)):
    rec = pack_for(mic, st.model_for(mic), deg, sr, hpf=st.hpf_of(mic), hpf_engaged=hpf)
    sos = np.asarray(unpack_record(rec), float).reshape(-1, 5)
    t = time.perf_counter(); y0 = apply_sos(x, sos); tl = time.perf_counter() - t
    t = time.perf_counter(); y1 = apply_sos_numpy(x, sos); tn = time.perf_counter() - t
    row = {'mic': mic, 'deg': deg, 'hpf': hpf, 'sections': len(sos), 'loop_s': round(tl, 3), 'numpy_s': round(tn, 4),
           'numpy_max_abs_err': float(np.max(np.abs(y1 - y0))), 'numpy_rel_err_db': round(20 * np.log10(np.max(np.abs(y1 - y0)) / np.max(np.abs(y0)) + 1e-300), 1)}
    if sosfilt is not None:
        t = time.perf_counter(); y2 = sosfilt(np.c_[sos[:, :3], np.ones(len(sos)), sos[:, 3:]], x); ts = time.perf_counter() - t
        row.update(scipy_s=round(ts, 4), scipy_max_abs_err=float(np.max(np.abs(y2 - y0))))
    res['cases'].append(row); print(row, flush=True)
print(json.dumps(res))
