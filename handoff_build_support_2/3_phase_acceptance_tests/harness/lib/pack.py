"""Pack a live_fdn_params JSON into the exact float blob / int route / IR arrays that
fdn_worklet.js (packRoom) + live_fdn.js (buildRoute/takeColour) hand to live_stereo.
Blob v2 matches packRoom: directory plus CORE (v1 body without magic, plus 8 reserves).
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

def _shelf2_live(d):
    buses = d.get('buses') or {}
    for k in 'lcr':
        src = buses.get(k)
        for _ in range(2):
            if not src:
                break
            for sh in (src.get('shelf2') or []):
                if sh and sh.get('on'):
                    return True
            src = src.get('b')
    return False

def pack_air(d):
    if not _shelf2_live(d):
        return []
    a = []
    buses = d.get('buses') or {}
    for k in 'lcr':
        bus = buses.get(k) or {}
        shelf = bus.get('shelf2') or []
        for i in range(32):
            push_shelf(a, shelf[i] if i < len(shelf) else None)
        b = bus.get('b') or {}
        shelf = b.get('shelf2') or []
        for i in range(32):
            push_shelf(a, shelf[i] if i < len(shelf) else None)
    return a

def pack_core(d):
    a = []
    di = int(num(d.get('direct_index'), 10))
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
    assert len(a) == BLOB_LEN - 1, len(a)  # v1 body without magic and without line_t60
    a.append(num(d.get('line_t60'), 0))
    sm = d.get('solo_mute') or []
    hn = d.get('hadamard_n')
    if hn is None:
        hn = d.get('n')
    a.append(num(hn, 32))
    a.append(num(d.get('loop_semantics'), 0))
    for i in range(6):
        a.append(num(sm[i] if i < len(sm) else 1, 1))
    return a

def pack_surf(d):
    g = d.get('early_gate')
    gates = [num(v, 1) for v in g] if isinstance(g, (list, tuple)) and len(g) == 192 else []
    cas = d.get('surf_cascade')
    tail = [num(v, 0) for v in cas] if isinstance(cas, (list, tuple)) and len(cas) >= 2 else []
    if tail:
        if not gates:
            gates = [1.0] * 192
        return gates + tail
    return gates

def pack_src(d):
    src = d.get('src_rad')
    if not isinstance(src, (list, tuple)) or len(src) != 716:
        return []
    return [num(v, 0) for v in src]

def pack_room(d):
    parts = [(1, pack_core(d)), (2, pack_air(d)), (3, pack_surf(d)), (4, []), (5, pack_src(d))]
    if d.get('shared_tail'):
        parts.append((6, [1.0]))
    desk_w = d.get('desk_w')
    if isinstance(desk_w, (list, tuple)) and len(desk_w) == 6:
        parts.append((7, [num(v, 0) for v in desk_w]))
    move = num(d.get('movement_ms'), 0)
    if move > 0:
        parts.append((8, [move]))
    hp = d.get('sub_hp')
    if isinstance(hp, (list, tuple)) and len(hp) == 5:
        parts.append((9, [num(v, 0) for v in hp]))
    bloom = d.get('bloom')
    if isinstance(bloom, (list, tuple)) and len(bloom) >= 26:
        parts.append((10, [num(v, 0) for v in list(bloom)[:96]]))
    pdn = num(d.get('predelay_n'), 0)
    if pdn > 0:
        if pdn > 4799:
            pdn = 4799
        parts.append((11, [pdn]))
    pre_c = d.get('pre_colour')
    if isinstance(pre_c, (list, tuple)) and len(pre_c) >= 16:
        parts.append((12, [num(v, 0) for v in list(pre_c)[:32]]))
    side = d.get('side')
    if isinstance(side, (list, tuple)) and len(side) >= 217:
        parts.append((13, [num(v, 0) for v in list(side)[:217]]))
    nsec = len(parts)
    off = 5 + 4 * nsec
    directory = []
    body = []
    for sid, payload in parts:
        ln = len(payload)
        directory += [sid, off, ln, 1]
        if ln:
            body += payload
            off += ln
    a = [2, 2, 0, nsec, 0] + directory + body
    a[4] = len(a)
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
