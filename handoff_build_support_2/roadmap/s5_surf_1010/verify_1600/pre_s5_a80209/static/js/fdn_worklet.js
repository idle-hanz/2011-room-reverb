/* 2011 Room Reverb — Play block.
 * The room loop and the mic colour (FIR or SOS) run in live_stereo (one C call).
 * This processor copies a block in, calls that function, and copies left
 * and right out. Nothing here is a ConvolverNode.
 * The page loads the wasm and passes the bytes in processorOptions.
 * This thread has no fetch.
 */

/* v2 blob length is the directory total. Reject only an empty or huge blob. */
var MAX_BLOB = 16384;
var ROUTE_LEN = 326;
var MAX_AUDIO = 2048;
var MAX_IRS = 192;
var MAX_IR_FLOATS = MAX_IRS * 8192;

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
  var a = [];
  var i;
  if (!g || g.length !== 192) return a;
  for (i = 0; i < 192; i++) a.push(num(g[i], 1));
  return a;
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
  return a;
}

class RoomFDNProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.ready = false;
    this.snap = true;
    this.pending = null;
    this.api = null;
    this.st = 0;
    this._reported = false;
    var po = options && options.processorOptions;
    this._wasm = po && po.wasm;
    this.port.onmessage = (ev) => this._msg(ev.data);
    this._boot();
  }

  _fail(msg) {
    if (this._reported) return;
    this._reported = true;
    try { this.port.postMessage({ type: "error", message: msg }); } catch (e) {}
  }

  async _boot() {
    var sr = sampleRate || 48000;
    var mod, heap, need, pages;
    try {
      if (!this._wasm) {
        this._fail("Live stereo wasm was not passed in.");
        return;
      }
      mod = await WebAssembly.instantiate(this._wasm, {});
      this.api = mod.instance.exports;
      heap = this.api.memory.buffer.byteLength;
      need = this.api.live_bytes(sr | 0);
      pages = Math.ceil(need / 65536);
      if (pages > 0) this.api.memory.grow(pages);
      this.st = this.api.live_bind(heap, need, sr | 0);
      if (!this.st) {
        this._fail("Live stereo could not reserve the delay memory.");
        return;
      }
      this.ready = true;
      if (this.pending) this._apply(this.pending);
    } catch (err) {
      this._fail("Live stereo failed to load: " + (err && err.message ? err.message : err));
    }
  }

  _msg(data) {
    if (!data || data.type !== "params") return;
    this.pending = data;
    if (this.ready) this._apply(data);
  }

  _viewF(ptr, n) {
    return new Float32Array(this.api.memory.buffer, ptr, n);
  }

  _viewI(ptr, n) {
    return new Int32Array(this.api.memory.buffer, ptr, n);
  }

  _apply(data) {
    var blob, dst, route, irs, lens, nIrs, i, over;
    irs = data.irs;
    lens = data.ir_len;
    nIrs = data.n_irs | 0;
    over = !!(irs && lens && nIrs > 0 && (irs.length > MAX_IR_FLOATS || nIrs > MAX_IRS));
    if (!over && (data.colour_over | 0) > MAX_IRS) {
      over = true;
      nIrs = data.colour_over | 0;
    }
    if (over) data.colour_on = 0;
    data.snap = this.snap;
    blob = packRoom(data);
    if (blob.length < 16 || blob.length > MAX_BLOB) {
      this._fail("Live room blob is " + blob.length + " floats.");
      return;
    }
    this._viewF(this.api.live_blob_ptr(this.st), blob.length).set(blob);
    this.api.live_load_room(this.st, blob.length);
    this.snap = false;
    if (over) {
      this.port.postMessage({ type: "colour_cap", n: nIrs, cap: MAX_IRS });
    } else if (irs && lens && nIrs > 0) {
      this._viewF(this.api.live_ir_ptr(this.st), irs.length).set(irs);
      dst = this._viewI(this.api.live_len_ptr(this.st), nIrs);
      for (i = 0; i < nIrs; i++) dst[i] = lens[i] | 0;
      this.api.live_load_irs(this.st, nIrs);
    }
    route = data.route;
    if (route && route.length >= ROUTE_LEN) {
      this._viewI(this.api.live_route_ptr(this.st), ROUTE_LEN).set(route.subarray(0, ROUTE_LEN));
      this.api.live_load_route(this.st);
    }
    if (data.ic_hp && data.ic_hm && this.api.live_load_ic
        && data.ic_hp.length === data.ic_hm.length && (data.ic_hp.length & 1) === 1) {
      var nIc = data.ic_hp.length;
      var ic = this._viewF(this.api.live_ic_ptr(this.st), nIc * 2);
      ic.set(data.ic_hp, 0);
      ic.set(data.ic_hm, nIc);
      this.api.live_load_ic(this.st, nIc);
    }
  }

  _silence(out, n) {
    var i;
    for (i = 0; i < n; i++) out[i] = 0;
  }

  process(inputs, outputs) {
    var output, lch, rch, inch, inL, inR, frames, api, st, off, k, ptrL, ptrR, ptrOL, ptrOR;
    try {
      output = outputs && outputs[0];
      if (!output || !output[0]) return true;
      lch = output[0];
      rch = output.length > 1 && output[1] ? output[1] : lch;
      frames = lch.length;
      if (!this.ready || !this.st) {
        this._silence(lch, frames);
        if (rch !== lch) this._silence(rch, frames);
        return true;
      }
      inch = inputs && inputs[0];
      inL = inch && inch[0] ? inch[0] : null;
      inR = inch && inch.length > 1 && inch[1] ? inch[1] : null;
      api = this.api;
      st = this.st;
      off = 0;
      while (off < frames) {
        k = frames - off;
        if (k > MAX_AUDIO) k = MAX_AUDIO;
        ptrL = api.live_in_l(st);
        ptrR = api.live_in_r(st);
        ptrOL = api.live_out_l(st);
        ptrOR = api.live_out_r(st);
        if (inL) this._viewF(ptrL, k).set(inL.subarray(off, off + k));
        else this._silence(this._viewF(ptrL, k), k);
        if (inR) this._viewF(ptrR, k).set(inR.subarray(off, off + k));
        else this._silence(this._viewF(ptrR, k), k);
        api.live_stereo(st, ptrL, ptrR, ptrOL, ptrOR, k);
        lch.set(this._viewF(ptrOL, k), off);
        if (rch !== lch) rch.set(this._viewF(ptrOR, k), off);
        off += k;
      }
    } catch (err) {
      this._fail(String(err && err.message ? err.message : err));
      if (lch && frames) {
        this._silence(lch, frames);
        if (rch && rch !== lch) this._silence(rch, frames);
      }
    }
    return true;
  }
}

registerProcessor("room-fdn", RoomFDNProcessor);
