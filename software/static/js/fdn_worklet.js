/* 2011 Room Reverb — Play block.
 * The room loop and the mic colour (FIR or SOS) run in live_stereo (one C call).
 * This processor copies a block in, calls that function, and copies left
 * and right out. Nothing here is a ConvolverNode.
 * The page loads the wasm and passes the bytes in processorOptions.
 * This thread has no fetch.
 */

/* Packing lives in pack_room.js and runs on the main thread.
 * This processor only copies the posted Float32Array into wasm.
 */
/* v2 blob length is the directory total. Reject only an empty or huge blob. */
var MAX_BLOB = 16384;
var ROUTE_LEN = 326;
var MAX_AUDIO = 2048;
var MAX_IRS = 192;
var MAX_IR_FLOATS = MAX_IRS * 8192;


class RoomFDNProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.ready = false;
    this.snap = true;
    this.pending = null;
    this.api = null;
    this.st = 0;
    this._failText = "";
    this._failAt = -1;
    this._buf = null;
    /* Reused every 100 ms. process() must not allocate a new message. */
    this._limMsg = { type: "limiter", db: 0, n: 0 };
    this._limLeft = 4800;
    var po = options && options.processorOptions;
    this._wasm = po && po.wasm;
    this.port.onmessage = (ev) => this._msg(ev.data);
    this._boot();
  }

  _fail(msg) {
    /* Each distinct error, at most once a second. currentTime is the worklet clock. */
    var text = String(msg || "error");
    var now = (typeof currentTime === "number") ? currentTime : 0;
    if (text === this._failText && (now - this._failAt) < 1) return;
    this._failText = text;
    this._failAt = now;
    try { this.port.postMessage({ type: "error", message: text }); } catch (e) {}
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
    /* Harness blob dump. process() and _apply() use _ensureViews instead. */
    return new Float32Array(this.api.memory.buffer, ptr, n);
  }

  _viewI(ptr, n) {
    return new Int32Array(this.api.memory.buffer, ptr, n);
  }

  _ensureViews() {
    var buf = this.api.memory.buffer;
    if (this._buf === buf && this._vInL) return;
    var api = this.api;
    var st = this.st;
    this._buf = buf;
    this._vBlob = new Float32Array(buf, api.live_blob_ptr(st), MAX_BLOB);
    this._vInL = new Float32Array(buf, api.live_in_l(st), MAX_AUDIO);
    this._vInR = new Float32Array(buf, api.live_in_r(st), MAX_AUDIO);
    this._vOutL = new Float32Array(buf, api.live_out_l(st), MAX_AUDIO);
    this._vOutR = new Float32Array(buf, api.live_out_r(st), MAX_AUDIO);
    this._vIr = new Float32Array(buf, api.live_ir_ptr(st), MAX_IR_FLOATS);
    this._vIc = new Float32Array(buf, api.live_ic_ptr(st), 1026);
    this._vRoute = new Int32Array(buf, api.live_route_ptr(st), ROUTE_LEN);
    this._vLen = new Int32Array(buf, api.live_len_ptr(st), MAX_IRS);
  }

  _apply(data) {
    var blob, route, irs, lens, nIrs, i, over, nIc;
    irs = data.irs;
    lens = data.ir_len;
    nIrs = data.n_irs | 0;
    over = !!(irs && lens && nIrs > 0 && (irs.length > MAX_IR_FLOATS || nIrs > MAX_IRS));
    if (!over && (data.colour_over | 0) > MAX_IRS) {
      over = true;
      nIrs = data.colour_over | 0;
    }
    blob = data.blob;
    if (!blob || blob.length < 16 || blob.length > MAX_BLOB) {
      this._fail("Live room blob is " + (blob ? blob.length : 0) + " floats.");
      return;
    }
    this._ensureViews();
    this._vBlob.set(blob);
    this.api.live_load_room(this.st, blob.length);
    this.snap = false;
    if (over) {
      this.port.postMessage({ type: "colour_cap", n: nIrs, cap: MAX_IRS });
    } else if (irs && lens && nIrs > 0) {
      this._vIr.set(irs);
      for (i = 0; i < nIrs; i++) this._vLen[i] = lens[i] | 0;
      this.api.live_load_irs(this.st, nIrs);
    }
    route = data.route;
    if (route && route.length >= ROUTE_LEN) {
      for (i = 0; i < ROUTE_LEN; i++) this._vRoute[i] = route[i] | 0;
      this.api.live_load_route(this.st);
    }
    if (data.ic_hp && data.ic_hm && this.api.live_load_ic
        && data.ic_hp.length === data.ic_hm.length && (data.ic_hp.length & 1) === 1) {
      nIc = data.ic_hp.length;
      this._vIc.set(data.ic_hp, 0);
      this._vIc.set(data.ic_hm, nIc);
      this.api.live_load_ic(this.st, nIc);
    }
    /* SL3. Sections are a Float64 side buffer. A fresh view each apply: grow detaches the old one.
       Flat (no surf_sos) turns the path off and does not post a status. */
    if (data.surf_on && data.surf_sos && data.surf_sos.length === 1440
        && data.surf_peaks && data.surf_peaks.length === 15
        && data.surf_keep && data.surf_keep.length === 3
        && this.api.live_surf_ptr && this.api.live_surf_peak_ptr
        && this.api.live_surf_keep && this.api.live_load_surf) {
      var mem = this.api.memory.buffer;
      new Float64Array(mem, this.api.live_surf_ptr(this.st), 1440).set(data.surf_sos);
      if (this.api.live_surf_ptr_b) {
        var sosB = (data.surf_sos_b && data.surf_sos_b.length === 1440) ? data.surf_sos_b : data.surf_sos;
        new Float64Array(this.api.memory.buffer, this.api.live_surf_ptr_b(this.st), 1440).set(sosB);
      }
      new Float64Array(this.api.memory.buffer, this.api.live_surf_peak_ptr(this.st), 15).set(data.surf_peaks);
      this.api.live_surf_keep(this.st, data.surf_keep[0] | 0, data.surf_keep[1] | 0, data.surf_keep[2] | 0);
      if ((this.api.live_load_surf(this.st, 1) | 0) === 0) {
        this.port.postMessage({ type: "surf", on: 0 });
      }
    } else if (this.api.live_load_surf) {
      this.api.live_load_surf(this.st, 0);
    }
    /* D-PROX. Side buffer, not a room section. Snap is the worklet flag, not Python's. */
    if (data.prox && data.prox.length === 199
        && this.api.live_prox_ptr && this.api.live_set_prox) {
      var dst = new Float64Array(this.api.memory.buffer, this.api.live_prox_ptr(this.st), 199);
      dst.set(data.prox);
      dst[0] = data.snap ? 1 : 0;
      this.api.live_set_prox(this.st, 199);
    } else if (this.api.live_set_prox) {
      this.api.live_set_prox(this.st, 0);
    }
    /* ROOMTONE. Side buffer. A missing key is the 30 Hz size-gate bypass. */
    if (data.harm && data.harm.length === 243
        && this.api.live_harm_ptr && this.api.live_load_harm) {
      new Float64Array(this.api.memory.buffer, this.api.live_harm_ptr(this.st), 243).set(data.harm);
      this.api.live_load_harm(this.st, 1);
    } else if (this.api.live_load_harm) {
      this.api.live_load_harm(this.st, 0);
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
      this._ensureViews();
      off = 0;
      while (off < frames) {
        k = frames - off;
        if (k > MAX_AUDIO) k = MAX_AUDIO;
        ptrL = api.live_in_l(st);
        ptrR = api.live_in_r(st);
        ptrOL = api.live_out_l(st);
        ptrOR = api.live_out_r(st);
        if (inL) this._vInL.set(inL.subarray(off, off + k));
        else this._silence(this._vInL, k);
        if (inR) this._vInR.set(inR.subarray(off, off + k));
        else this._silence(this._vInR, k);
        api.live_stereo(st, ptrL, ptrR, ptrOL, ptrOR, k);
        lch.set(this._vOutL.subarray(0, k), off);
        if (rch !== lch) rch.set(this._vOutR.subarray(0, k), off);
        off += k;
      }
      if (api.live_limiter_n) {
        this._limLeft -= frames;
        if (this._limLeft <= 0) {
          var nLim = api.live_limiter_n(st) | 0;
          if (nLim > 0) {
            var pk = api.live_limiter_peak(st);
            var op = api.live_limiter_out(st);
            this._limMsg.db = (op > 1e-12 && pk > op) ? (20 * Math.log10(pk / op)) : 0;
            this._limMsg.n = nLim;
            this.port.postMessage(this._limMsg);
          }
          api.live_limiter_reset(st);
          this._limLeft += 4800;
        }
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
