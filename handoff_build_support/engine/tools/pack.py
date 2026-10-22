"""Pack a live_fdn_params JSON into the exact float blob / int route / IR arrays that
fdn_worklet.js (packRoom) + live_fdn.js (buildRoute/takeColour) hand to live_stereo.
Port is line-for-line; BLOB_LEN must be 1981 (checked).
Usage: python pack.py params.json out_prefix [json overrides e.g. '{"early_wet":1,"colour_on":false}']
Writes out_prefix.blob (f32), .route (i32 x230), .irs (f32), .lens (i32)."""
import sys, json, math, base64, struct
import numpy as np

BLOB_LEN, ROUTE_LEN = 1981, 230

def num(v, d):
    try:
        n = float(v)
        return n if math.isfinite(n) else d
    except (TypeError, ValueError):
        return d

def push_arr(a, src, n, d):
    for i in range(n):
        v = src[i] if (src is not None and i < len(src)) else None
        a.append(v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else d)

def push_shelf(a, sh):
    if sh and sh.get('on'):
        a += [1, num(sh.get('b0'), 1), num(sh.get('b1'), 0), num(sh.get('b2'), 0), num(sh.get('a1'), 0), num(sh.get('a2'), 0)]
    else:
        a += [0, 1, 0, 0, 0, 0]

def push_side(a, bus, di):
    src = bus or {}
    shelf = src.get('shelf') or []
    push_arr(a, src.get('delay_ms'), 32, 20)
    push_arr(a, src.get('inject'), 32, 0)
    push_arr(a, src.get('dffs'), 32, 0)
    push_arr(a, src.get('air_g'), 32, 0)
    a.append(num(src.get('air_lp'), 0))
    for i in range(32):
        push_shelf(a, shelf[i] if i < len(shelf) else None)
    dl = src.get('delay_ms')
    dms = dl[di] if dl and isinstance(dl[di], (int, float)) else 20
    a += [dms, num(src.get('direct_gain'), 1)]

def pack_room(d):
    a = [1]
    di = int(num(d.get('direct_index'), 2))
    di = max(0, min(31, di))
    a += [num(d.get('g'), 0.03), num(d.get('fdn_wet'), 1), num(d.get('direct_wet'), 1), num(d.get('early_wet'), 0),
          num(d.get('dry_gain'), 0), num(d.get('makeup'), 1), num(d.get('gain_a'), 1), num(d.get('gain_b'), 1)]
    a += [1 if d.get('two_sources') else 0, 1 if d.get('colour_on') else 0, 1 if d.get('mono') else 0,
          di, num(d.get('max_delay_ms'), 1000), 1 if d.get('snap', True) else 0, 0]
    for i, k in enumerate('lcr'):
        a += [num(d.get('mic_gain_' + k), 1), num(d.get('mic_pan_' + k), [-1, 0, 1][i]), num(d.get('mic_phase_' + k), 1)]
    for i in range(3):
        pk = (d.get('peaking') or [None] * 3)[i]
        if pk and pk.get('on'):
            a += [1, num(pk['b0'], 1), num(pk['b1'], 0), num(pk['b2'], 0), num(pk['a1'], 0), num(pk['a2'], 0)]
        else:
            a += [0, 1, 0, 0, 0, 0]
    for k in 'lcr':
        bus = (d.get('buses') or {}).get(k)
        push_side(a, bus, di)
        push_side(a, bus.get('b') if bus else None, di)
    assert len(a) == BLOB_LEN, len(a)  # 1981 today; the fix appends line_t60 after this
    return np.asarray(a, dtype=np.float32)

def _at(v, d):
    try:
        n = float(v)
        return int(n) if math.isfinite(n) else d
    except (TypeError, ValueError):
        return d

def build_route(b):
    r = []
    for c in 'lcr':
        row = (b.get('fdn') or {}).get(c)
        r += [_at(row[i] if row and i < len(row) else None, -1) for i in range(32)]
    for key in ('early', 'early_b'):
        for c in 'lr':
            row = (b.get(key) or {}).get(c) if b.get(key) else None
            r += [_at(row[i] if row and i < len(row) else None, -2) for i in range(32)]
    for key in ('direct', 'direct_b'):
        for c in 'lcr':
            r.append(_at((b.get(key) or {}).get(c), -1))
    assert len(r) == ROUTE_LEN
    return np.asarray(r, dtype=np.int32)

def pack(params, over=None, sr=48000):
    over = dict(over or {})
    c = params.get('colour') or {}
    want_colour = over.pop('colour_on', True)
    on = bool(c.get('on') and c.get('sr') == sr and want_colour)
    d = dict(params)
    d.update({'colour_on': on, 'mono': False, 'snap': True})
    d.update(over)
    blob = pack_room(d)
    if d.get('line_t60') is not None:  # proposed fix: optional trailing float (BLOB_LEN 1982)
        blob = np.concatenate([blob, np.asarray([float(d['line_t60'])], np.float32)])
    if on:
        irs = [np.frombuffer(base64.b64decode(s), dtype=np.float32) for s in c['irs']]
        lens = np.asarray([len(x) for x in irs], dtype=np.int32)
        packed = np.concatenate(irs).astype(np.float32)
        route = build_route(c)
    else:
        lens = np.zeros(0, np.int32); packed = np.zeros(0, np.float32); route = np.full(ROUTE_LEN, -1, np.int32)
        # colour off: early route defaults would be -2 in JS only when colour on; blob colour_on=0 ignores route.
    return blob, route, packed, lens

if __name__ == '__main__':
    P = json.load(open(sys.argv[1]))
    over = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    blob, route, irs, lens = pack(P, over)
    pre = sys.argv[2]
    blob.tofile(pre + '.blob'); route.tofile(pre + '.route'); irs.tofile(pre + '.irs'); lens.tofile(pre + '.lens')
    print(pre, 'blob', len(blob), 'n_irs', len(lens), 'colour_on', int(blob[10]))
