"""Box-only prototype for D-AUD-6 (per-capsule heights). Monkeypatches early_field so that
L/R/C capsules sit at body my_l/my_r/my_c (absolute metres, default = my). Not for the real tree.
Rules: coincident M/S (ms_decode) and binaural ignore per-capsule heights. Heights clamp to [0.02, H-0.02]."""
import early_field as ef
H = {}
_orig_from_prepare = ef.MicStand.from_prepare.__func__
def apply(body):
    H.clear()
    my = float(body.get('my', 1.5)); Hm = float(body.get('H', 3.0))
    cl = lambda v: max(0.02, min(Hm - 0.02, float(my if v is None else v)))
    H.update(l=cl(body.get('my_l')), r=cl(body.get('my_r')), c=cl(body.get('my_c')))
def _from_prepare(cls, prep, *a, **k):
    st = _orig_from_prepare(cls, prep, *a, **k)
    if H and not st.ms_decode:
        st.y_l, st.y_r = H['l'], H['r']
        st.cy = H['c']
    return st
ef.MicStand.from_prepare = classmethod(_from_prepare)
_orig_mp = ef.mic_positions
def mic_positions(stand):
    l, r = _orig_mp(stand)
    if getattr(stand, 'is_binaural', False) or not hasattr(stand, 'y_l'):
        return l, r
    return (l[0], stand.y_l, l[2]), (r[0], stand.y_r, r[2])
ef.mic_positions = mic_positions

# ---- Option H-1 (env HMODE=early): FDN line lengths, line diffusers and line air keep the stand
# reference height (my); only early taps, direct and per-bus inject levels follow per-capsule heights.
import os as _os, copy as _copy
_MY = {}
_orig_apply = apply
def apply(body):  # noqa: F811
    _orig_apply(body); _MY['my'] = max(0.02, min(float(body.get('H', 3.0)) - 0.02, float(body.get('my', 1.5))))
if _os.environ.get('HMODE') == 'early':
    import fdn as _fdn
    _orig_ct = ef.compute_taps
    def compute_taps(room, source, stand, *a, **k):
        taps = _orig_ct(room, source, stand, *a, **k)
        if hasattr(stand, 'y_l') and not getattr(stand, 'is_binaural', False):
            fs = _copy.copy(stand); fs.y_l = fs.y_r = fs.cy = _MY['my']
            flat = _orig_ct(room, source, fs, *a, **k)
            for t, f in zip(taps, flat):
                t._dfl, t._dfr, t._dfc = f.distance_l, f.distance_r, f.distance_c
        return taps
    ef.compute_taps = compute_taps
    _orig_td = _fdn._tap_distance
    def _tap_distance(t, channel):
        if hasattr(t, '_dfl'):
            ch = str(channel).lower()
            if ch == 'l': return float(t._dfl)
            if ch == 'r': return float(t._dfr)
            if ch == 'c': return float(t._dfc)
            return 0.5 * (float(t._dfl) + float(t._dfr))
        return _orig_td(t, channel)
    _fdn._tap_distance = _tap_distance
