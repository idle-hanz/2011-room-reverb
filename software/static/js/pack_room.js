/* Room blob packer. Shared by the page (main thread) and the harness.
 * fdn_worklet.js does not pack. The page posts one Float32Array.
 */
function num(v, dflt) {
  var n = Number(v);
  return isFinite(n) ? n : dflt;
}

function pushArr(a, src, n, dflt) {
  var i, v;
  for (i = 0; i < n; i++) {
    v = src && src[i];
    a.push(typeof v === "number" && isFinite(v) ? v : dflt);
  }
}

function pushShelf(a, sh) {
  if (sh && sh.on) {
    a.push(1, num(sh.b0, 1), num(sh.b1, 0), num(sh.b2, 0), num(sh.a1, 0), num(sh.a2, 0));
  } else {
    a.push(0, 1, 0, 0, 0, 0);
  }
}

function pushSide(a, bus, di) {
  var src = bus || {};
  var shelf = src.shelf || [];
  var i, dms;
  pushArr(a, src.delay_ms, 32, 20);
  pushArr(a, src.inject, 32, 0);
  pushArr(a, src.dffs, 32, 0);
  pushArr(a, src.air_g, 32, 0);
  a.push(num(src.air_lp, 0));
  for (i = 0; i < 32; i++) pushShelf(a, shelf[i]);
  dms = src.delay_ms && typeof src.delay_ms[di] === "number" ? src.delay_ms[di] : 20;
  a.push(dms, num(src.direct_gain, 1));
}

function packCore(data) {
  var a = [];
  var names = ["l", "c", "r"];
  var di = num(data.direct_index, 10) | 0;
  var i, bus, pk, key, sm, hn;
  if (di < 0) di = 0;
  if (di > 31) di = 31;
  a.push(num(data.g, 0.03), num(data.fdn_wet, 1), num(data.direct_wet, 1),
    num(data.early_wet, 0), num(data.dry_gain, 0), num(data.makeup, 1),
    num(data.gain_a, 1), num(data.gain_b, 1));
  a.push(data.two_sources ? 1 : 0, data.colour_on ? 1 : 0, data.mono ? 1 : 0,
    di, num(data.max_delay_ms, 1000), data.snap ? 1 : 0, 0);
  for (i = 0; i < 3; i++) {
    key = names[i];
    a.push(num(data["mic_gain_" + key], 1), num(data["mic_pan_" + key], i === 0 ? -1 : (i === 2 ? 1 : 0)),
      num(data["mic_phase_" + key], 1));
  }
  for (i = 0; i < 3; i++) {
    pk = data.peaking && data.peaking[i];
    if (pk && pk.on) {
      a.push(1, num(pk.b0, 1), num(pk.b1, 0), num(pk.b2, 0), num(pk.a1, 0), num(pk.a2, 0));
    } else {
      a.push(0, 1, 0, 0, 0, 0);
    }
  }
  for (i = 0; i < 3; i++) {
    bus = data.buses && data.buses[names[i]];
    pushSide(a, bus, di);
    pushSide(a, bus && bus.b, di);
  }
  a.push(num(data.line_t60, 0));
  sm = data.solo_mute || [];
  hn = data.hadamard_n != null ? data.hadamard_n : data.n;
  a.push(num(hn, 32), num(data.loop_semantics, 0));
  for (i = 0; i < 6; i++) a.push(num(sm[i], 1));
  return a;
}

function shelf2Live(data) {
  var names = ["l", "c", "r"];
  var i, k, src, shelf, j;
  for (i = 0; i < 3; i++) {
    src = data.buses && data.buses[names[i]];
    for (k = 0; k < 2 && src; k++) {
      shelf = src.shelf2;
      if (shelf) {
        for (j = 0; j < shelf.length; j++) {
          if (shelf[j] && shelf[j].on) return true;
        }
      }
      src = src.b;
    }
  }
  return false;
}

function packAir(data) {
  var a = [];
  var names = ["l", "c", "r"];
  var i, bus, shelf, j;
  if (!shelf2Live(data)) return a;
  for (i = 0; i < 3; i++) {
    bus = (data.buses && data.buses[names[i]]) || {};
    shelf = bus.shelf2 || [];
    for (j = 0; j < 32; j++) pushShelf(a, shelf[j]);
    shelf = (bus.b && bus.b.shelf2) || [];
    for (j = 0; j < 32; j++) pushShelf(a, shelf[j]);
  }
  return a;
}

function packSurf(data) {
  var g = data && data.early_gate;
  var cas = data && data.surf_cascade;
  var a = [];
  var i;
  var gates = [];
  var tail = [];
  if (g && g.length === 192) {
    for (i = 0; i < 192; i++) gates.push(num(g[i], 1));
  }
  if (cas && cas.length >= 2) {
    for (i = 0; i < cas.length; i++) tail.push(num(cas[i], 0));
  }
  if (tail.length) {
    if (!gates.length) {
      for (i = 0; i < 192; i++) gates.push(1);
    }
    return gates.concat(tail);
  }
  return gates;
}

function packSrc(data) {
  var src = data && data.src_rad;
  var a = [];
  var i, n;
  if (!src || src.length !== 716) return a;
  for (i = 0; i < 716; i++) {
    n = Number(src[i]);
    a.push(isFinite(n) ? n : 0);
  }
  return a;
}

function packRoom(data) {
  var parts = [[1, packCore(data)], [2, packAir(data)], [3, packSurf(data)], [4, []], [5, packSrc(data)]];
  if (data && data.shared_tail) parts.push([6, [1]]);
  if (data && data.desk_w && data.desk_w.length === 6) {
    var dw = [], diw;
    for (diw = 0; diw < 6; diw++) dw.push(num(data.desk_w[diw], 0));
    parts.push([7, dw]);
  }
  if (data && Number(data.movement_ms) > 0) parts.push([8, [num(data.movement_ms, 0)]]);
  if (data && data.sub_hp && data.sub_hp.length === 5) {
    var hp = [], hi;
    for (hi = 0; hi < 5; hi++) hp.push(num(data.sub_hp[hi], 0));
    parts.push([9, hp]);
  }
  if (data && data.bloom && data.bloom.length >= 26) {
    var bl = [], bi, bn = data.bloom.length > 96 ? 96 : data.bloom.length;
    for (bi = 0; bi < bn; bi++) bl.push(num(data.bloom[bi], 0));
    parts.push([10, bl]);
  }
  if (data && Number(data.predelay_n) > 0) {
    var pdn = Number(data.predelay_n);
    if (pdn > 4799) pdn = 4799;
    parts.push([11, [pdn]]);
  }
  if (data && data.pre_colour && data.pre_colour.length >= 16) {
    var pc = [], pi, pn = data.pre_colour.length > 32 ? 32 : data.pre_colour.length;
    for (pi = 0; pi < pn; pi++) pc.push(num(data.pre_colour[pi], 0));
    parts.push([12, pc]);
  }
  if (data && data.side && data.side.length >= 217) {
    var sd = [], si;
    for (si = 0; si < 217; si++) sd.push(num(data.side[si], 0));
    parts.push([13, sd]);
  }
  var nsec = parts.length;
  var off = 5 + 4 * nsec;
  var dir = [];
  var body = [];
  var s, payload, ln;
  for (s = 0; s < nsec; s++) {
    payload = parts[s][1];
    ln = payload.length;
    dir.push(parts[s][0], off, ln, 1);
    if (ln) {
      body = body.concat(payload);
      off += ln;
    }
  }
  var a = [2, 2, 0, nsec, 0].concat(dir, body);
  a[4] = a.length;
  return new Float32Array(a);
}

if (typeof globalThis !== "undefined") globalThis.packRoom = packRoom;
