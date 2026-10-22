/* 2011 Room Reverb — browser live player.
 * The desk stays here. The room loop, the 80 ms mic filters, and the
 * left/right sum run in one C function inside the worklet. There is no
 * ConvolverNode bank.
 */
(function (global) {
  "use strict";

  var ctx = null;
  var node = null;
  var analyser = null;
  var source = null;
  var buffer = null;
  var running = false;
  var loading = false;
  var monoFile = false;
  var colourRev = "";
  var bank = null;
  var lastCapLine = "";
  var WORKLET_VER = 60;
  var COLOUR_CAP = 192;
  var ROUTE_LEN = 326;
  var RMS_QUIET = 1e-5;
  var decayS = 1.8;
  var snapRoom = true;
  var holdAudio = false;
  var suspendTimer = null;
  var rmsBuf = null;
  var limiterTimer = null;

  function showLimiter(db, n) {
    var el = document.getElementById("limiterLed");
    var shown;
    if (!el) return;
    shown = Math.round(Number(db) * 10) / 10;
    if (!isFinite(shown) || shown < 0) shown = 0;
    el.textContent = "Limiter: peak reduced by " + shown.toFixed(1) + " dB (" + (n | 0) + " samples)";
    el.hidden = false;
    if (limiterTimer) clearTimeout(limiterTimer);
    limiterTimer = setTimeout(function () {
      el.hidden = true;
      limiterTimer = null;
    }, 2000);
  }

  function noteDecay(s) {
    var n = Number(s);
    if (isFinite(n) && n > 0) decayS = n;
  }

  function cancelSuspend() {
    if (suspendTimer) {
      clearTimeout(suspendTimer);
      suspendTimer = null;
    }
  }

  function outputRms() {
    var n, i, acc;
    if (!analyser) return 0;
    n = analyser.fftSize || 2048;
    if (!rmsBuf || rmsBuf.length !== n) rmsBuf = new Float32Array(n);
    analyser.getFloatTimeDomainData(rmsBuf);
    acc = 0;
    for (i = 0; i < n; i++) acc += rmsBuf[i] * rmsBuf[i];
    return Math.sqrt(acc / n);
  }

  function armTailSuspend() {
    var t0, quietAt;
    cancelSuspend();
    if (!ctx || ctx.state !== "running") return;
    t0 = (global.performance && performance.now) ? performance.now() : Date.now();
    quietAt = 0;
    function tick() {
      var rms, now, quiet, quietFor, waited;
      suspendTimer = null;
      if (running || holdAudio || !ctx || ctx.state !== "running") return;
      rms = outputRms();
      now = (global.performance && performance.now) ? performance.now() : Date.now();
      quiet = rms < RMS_QUIET;
      if (quiet) {
        if (!quietAt) quietAt = now;
      } else {
        quietAt = 0;
      }
      quietFor = quietAt ? (now - quietAt) : 0;
      waited = now - t0;
      /* Quiet for 0.5 s, or the decay wait has elapsed and the tail is already quiet.
         A tail still above −100 dBFS is never cut. */
      if (quiet && (quietFor >= 500 || waited >= decayS * 1500)) {
        ctx.suspend().catch(function () {});
        return;
      }
      suspendTimer = setTimeout(tick, 50);
    }
    suspendTimer = setTimeout(tick, 50);
  }

  function attachOutput(work) {
    if (!analyser || analyser.context !== ctx) {
      if (analyser) dropNode(analyser);
      analyser = ctx.createAnalyser();
      analyser.fftSize = 2048;
      analyser.connect(ctx.destination);
    }
    work.connect(analyser);
  }

  function status(msg) {
    var el = document.getElementById("status");
    var head = document.getElementById("headerStatus");
    var text = msg == null ? "" : String(msg);
    if (el) el.textContent = text;
    if (head) head.textContent = text.replace(/\s+/g, " ").trim();
  }

  function num(v, dflt) {
    var n = Number(v);
    return isFinite(n) ? n : dflt;
  }

  function rate() {
    return ctx && ctx.sampleRate ? ctx.sampleRate : 0;
  }

  async function prepare() {
    var AC = global.AudioContext || global.webkitAudioContext;
    if (!AC) return 0;
    if (!ctx) ctx = new AC({ latencyHint: "interactive" });
    if (ctx.state === "suspended") {
      try { await ctx.resume(); } catch (e) {}
    }
    return ctx.sampleRate || 0;
  }

  function colourRevNow() {
    return colourRev || "";
  }

  function dropNode(n) {
    if (!n) return;
    try { n.disconnect(); } catch (e) {}
  }

  async function ensure() {
    if (ctx && node && node._ver === WORKLET_VER) return true;
    if (source) {
      try { source.onended = null; } catch (e) {}
      try { source.stop(); } catch (e2) {}
      try { source.disconnect(); } catch (e3) {}
      source = null;
    }
    dropNode(node);
    node = null;
    snapRoom = true;
    bank = null;
    colourRev = "";
    lastCapLine = "";
    var AC = global.AudioContext || global.webkitAudioContext;
    if (!AC) {
      status("Web Audio is not available in this browser.");
      return false;
    }
    if (!ctx) ctx = new AC({ latencyHint: "interactive" });
    if (ctx.state === "suspended") {
      try { await ctx.resume(); } catch (e) {}
    }
    if (!ctx._liveState) {
      ctx._liveState = true;
      ctx.onstatechange = function () {
        if (!running) return;
        if (ctx.state === "suspended" || ctx.state === "interrupted") {
          status("Live play stalled. Click the page once to bring it back.");
          try { ctx.resume(); } catch (e) {}
        }
      };
    }
    var wasmBytes;
    try {
      var wasmRes = await fetch("/static/wasm/live_stereo.wasm?v=" + WORKLET_VER);
      if (!wasmRes.ok) throw new Error("wasm " + wasmRes.status);
      wasmBytes = await wasmRes.arrayBuffer();
      await ctx.audioWorklet.addModule("/static/js/fdn_worklet.js?v=" + WORKLET_VER);
    } catch (err) {
      status("Live FDN worklet failed to load: " + (err && err.message ? err.message : err));
      return false;
    }
    try {
      node = new AudioWorkletNode(ctx, "room-fdn", {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [2],
        channelCount: 2,
        channelCountMode: "explicit",
        channelInterpretation: "discrete",
        processorOptions: { wasm: wasmBytes }
      });
    } catch (err) {
      status("Live FDN graph failed: " + (err && err.message ? err.message : err));
      return false;
    }
    node._ver = WORKLET_VER;
    attachOutput(node);
    node.port.onmessage = function (ev) {
      var d = ev && ev.data;
      var line;
      if (!d) return;
      if (d.type === "colour_cap") {
        line = "Mic colour is OFF: " + d.n + " entries, cap " + d.cap + ".";
        if (line !== lastCapLine) status(line);
        lastCapLine = line;
        return;
      }
      if (d.type === "limiter") {
        showLimiter(d.db, d.n);
        return;
      }
      if (d.type !== "error") return;
      status("Live FDN: " + (d.message || "error"));
    };
    node.onprocessorerror = function (ev) {
      status("Live play stopped: the audio processor died"
        + (ev && ev.message ? " (" + ev.message + ")" : "") + ".");
    };
    return true;
  }

  function decodeIr(s) {
    if (!s) return null;
    var bin = atob(s);
    var n = bin.length;
    var bytes, i;
    if (n < 4 || (n & 3)) return null;
    bytes = new Uint8Array(n);
    for (i = 0; i < n; i++) bytes[i] = bin.charCodeAt(i) & 255;
    return new Float32Array(bytes.buffer);
  }

  function at(v, dflt) {
    return (v == null || !isFinite(Number(v))) ? dflt : (Number(v) | 0);
  }

  function buildRoute(b) {
    var r = new Int32Array(ROUTE_LEN);
    var names = ["l", "c", "r"];
    var o = 0;
    var i, c, row;
    for (c = 0; c < 3; c++) {
      row = b.fdn && b.fdn[names[c]];
      for (i = 0; i < 32; i++) r[o++] = at(row && row[i], -1);
    }
    for (c = 0; c < 2; c++) {
      row = b.early && b.early[c === 0 ? "l" : "r"];
      for (i = 0; i < 32; i++) r[o++] = at(row && row[i], -2);
    }
    for (c = 0; c < 2; c++) {
      row = b.early_b && b.early_b[c === 0 ? "l" : "r"];
      for (i = 0; i < 32; i++) r[o++] = at(row && row[i], -2);
    }
    for (c = 0; c < 3; c++) r[o++] = at(b.direct && b.direct[names[c]], -1);
    for (c = 0; c < 3; c++) r[o++] = at(b.direct_b && b.direct_b[names[c]], -1);
    for (c = 0; c < 3; c++) {
      row = b.fdn_b && b.fdn_b[names[c]];
      for (i = 0; i < 32; i++) r[o++] = at(row && row[i], -1);
    }
    return r;
  }

  var lastColourNotice = "";

  function colourNotice(colour) {
    var msg = "";
    if (colour.notice) msg = String(colour.notice);
    else if (colour.on && ctx && colour.sr !== ctx.sampleRate) {
      msg = "Mic colour is OFF: the bank is for " + colour.sr
        + " Hz and the device is running at " + ctx.sampleRate + " Hz.";
    }
    if (msg && msg !== lastColourNotice) status(msg);
    lastColourNotice = msg;
  }

  function takeColour(p) {
    var colour = p.colour || {};
    colourNotice(colour);
    var on = !!(colour.on && ctx && colour.sr === ctx.sampleRate);
    var packed = null;
    var lengths = null;
    var i, ir, o, n, irs;
    if (!on) return { on: false };
    if (colour.same && colour.rev && colour.rev === colourRev && bank) {
      if (bank.over) return { on: false, route: buildRoute(bank), over: bank.n };
      return { on: true, route: buildRoute(bank) };
    }
    if (!colour.irs || !colour.direct || !colour.fdn) return { on: false, hold: true };
    irs = [];
    n = 0;
    for (i = 0; i < colour.irs.length; i++) {
      ir = decodeIr(colour.irs[i]);
      if (!ir) ir = new Float32Array(0);
      irs.push(ir);
      n += ir.length;
    }
    packed = new Float32Array(n);
    lengths = new Int32Array(irs.length);
    o = 0;
    for (i = 0; i < irs.length; i++) {
      packed.set(irs[i], o);
      lengths[i] = irs[i].length;
      o += irs[i].length;
    }
    bank = {
      rev: colour.rev || "",
      direct: colour.direct,
      direct_b: colour.direct_b || null,
      fdn: colour.fdn,
      fdn_b: colour.fdn_b || null,
      early: colour.early || null,
      early_b: colour.early_b || null,
      over: irs.length > COLOUR_CAP || n > COLOUR_CAP * 8192,
      n: irs.length
    };
    colourRev = bank.rev;
    if (bank.over) return { on: false, route: buildRoute(bank), over: bank.n };
    if (lastCapLine) {
      status("Live FDN running — drag Src / Mic. This is the room, not a baked IR.");
    }
    lastCapLine = "";
    return { on: true, route: buildRoute(bank), irs: packed, ir_len: lengths, n_irs: irs.length };
  }

  function fadeLoopSeam(audioBuf, fadeSec) {
    var nFade = Math.min((audioBuf.length / 2) | 0, Math.round((fadeSec || 0.02) * audioBuf.sampleRate));
    var c, i, d, n, a, wIn, wOut;
    if (nFade < 16) return audioBuf;
    for (c = 0; c < audioBuf.numberOfChannels; c++) {
      d = audioBuf.getChannelData(c);
      n = d.length;
      for (i = 0; i < nFade; i++) {
        a = i / nFade;
        wIn = 0.5 - 0.5 * Math.cos(Math.PI * a);
        wOut = 1 - wIn;
        d[i] *= wIn;
        d[n - nFade + i] *= wOut;
      }
    }
    return audioBuf;
  }

  async function decodeFile(file) {
    var AC = global.AudioContext || global.webkitAudioContext;
    var ab, decodedFile;
    if (!AC) return null;
    if (!ctx) ctx = new AC({ latencyHint: "interactive" });
    ab = await file.arrayBuffer();
    decodedFile = await ctx.decodeAudioData(ab.slice(0));
    return fadeLoopSeam(decodedFile, 0.02);
  }

  function pushParams(params) {
    var colour, msg;
    if (!node || !params || !params.ok) return;
    colour = takeColour(params);
    msg = {
      type: "params",
      g: params.g,
      fdn_wet: params.fdn_wet,
      direct_wet: params.direct_wet,
      early_wet: params.early_wet,
      dry_gain: params.dry_gain,
      mic_gain_l: params.mic_gain_l,
      mic_gain_c: params.mic_gain_c,
      mic_gain_r: params.mic_gain_r,
      mic_pan_l: params.mic_pan_l,
      mic_pan_c: params.mic_pan_c,
      mic_pan_r: params.mic_pan_r,
      mic_phase_l: params.mic_phase_l,
      mic_phase_c: params.mic_phase_c,
      mic_phase_r: params.mic_phase_r,
      makeup: params.makeup,
      direct_index: params.direct_index,
      max_delay_ms: params.max_delay_ms,
      line_t60: params.line_t60 || 0,
      ic_hp: params.ic_hp || null,
      ic_hm: params.ic_hm || null,
      src_rad: params.src_rad || null,
      early_gate: params.early_gate || null,
      surf_cascade: params.surf_cascade || null,
      hadamard_n: params.hadamard_n != null ? params.hadamard_n : params.n,
      loop_semantics: params.loop_semantics || 0,
      solo_mute: params.solo_mute || null,
      shared_tail: !!params.shared_tail,
      desk_w: (params.desk_w && params.desk_w.length === 6) ? params.desk_w : null,
      movement_ms: (params.movement_ms > 0) ? params.movement_ms : 0,
      surf_on: (params.surf_on && params.surf_sos && params.surf_sos.length === 1440) ? 1 : 0,
      surf_sos: (params.surf_on && params.surf_sos && params.surf_sos.length === 1440) ? Float64Array.from(params.surf_sos) : null,
      surf_sos_b: (params.surf_sos_b && params.surf_sos_b.length === 1440) ? Float64Array.from(params.surf_sos_b) : null,
      surf_keep: (params.surf_keep && params.surf_keep.length === 3) ? params.surf_keep : null,
      surf_peaks: (params.surf_peaks && params.surf_peaks.length === 15) ? Float64Array.from(params.surf_peaks) : null,
      prox: (params.prox && params.prox.length === 199) ? Float64Array.from(params.prox) : null,
      harm: (params.harm && params.harm.length === 243) ? Float64Array.from(params.harm) : null,
      sub_hp: (params.sub_hp && params.sub_hp.length === 5) ? params.sub_hp : null,
      peaking: params.peaking,
      two_sources: !!params.two_sources && !monoFile,
      gain_a: params.gain_a,
      gain_b: params.gain_b,
      buses: params.buses,
      colour_on: !!colour.on,
      mono: !!monoFile
    };
    if (colour.route) msg.route = colour.route;
    if (colour.over) msg.colour_over = colour.over;
    if (colour.irs) {
      msg.irs = colour.irs;
      msg.ir_len = colour.ir_len;
      msg.n_irs = colour.n_irs;
    }
    msg.snap = snapRoom;
    var nIrs = msg.n_irs | 0;
    var overCap = !!(msg.irs && msg.ir_len && nIrs > 0 && (msg.irs.length > 192 * 8192 || nIrs > 192));
    if (!overCap && (msg.colour_over | 0) > 192) overCap = true;
    if (overCap) msg.colour_on = 0;
    if (typeof packRoom !== "function") {
      status("Room packer is missing.");
      return;
    }
    var blob = packRoom(msg);
    msg.blob = blob;
    snapRoom = false;
    node.port.postMessage(msg, blob && blob.buffer ? [blob.buffer] : []);
  }

  async function start(file, params) {
    holdAudio = true;
    cancelSuspend();
    if (loading) {
      holdAudio = false;
      return false;
    }
    if (!file) {
      status("Load a WAV, then Play live.");
      holdAudio = false;
      return false;
    }
    loading = true;
    try {
      if (!(await ensure())) {
        loading = false;
        holdAudio = false;
        return false;
      }
      if (ctx.state === "suspended") await ctx.resume();
      buffer = await decodeFile(file);
      monoFile = !buffer || buffer.numberOfChannels < 2;
      if (source) {
        try { source.onended = null; } catch (e0) {}
        try { source.stop(); } catch (e) {}
        try { source.disconnect(); } catch (e2) {}
        source = null;
      }
      if (params) pushParams(params);
      running = true;
      holdAudio = false;
      attachSource();
      status("Live FDN running — drag Src / Mic. This is the room, not a baked IR.");
      return true;
    } catch (err) {
      status("Live FDN failed: " + (err && err.message ? err.message : err));
      running = false;
      holdAudio = false;
      return false;
    } finally {
      loading = false;
      if (!running) holdAudio = false;
    }
  }

  var lastRestart = 0;

  function attachSource() {
    var next, prev, now;
    if (!ctx || !buffer || !node) return;
    next = ctx.createBufferSource();
    next.buffer = buffer;
    next.loop = true;
    next.onended = function () {
      if (!running || source !== next || !buffer) return;
      now = Date.now();
      if (now - lastRestart < 250) return;
      lastRestart = now;
      attachSource();
    };
    next.connect(node);
    if (source) {
      prev = source;
      source = next;
      try { prev.onended = null; } catch (e) {}
      try { prev.stop(); } catch (e2) {}
      try { prev.disconnect(); } catch (e3) {}
    } else {
      source = next;
    }
    next.start();
  }

  function stop() {
    running = false;
    holdAudio = false;
    if (source) {
      try { source.onended = null; } catch (e) {}
      try { source.stop(); } catch (e2) {}
      try { source.disconnect(); } catch (e3) {}
      source = null;
    }
    armTailSuspend();
  }

  function isRunning() { return running; }

  function audioState() {
    return ctx ? ctx.state : "none";
  }

  global.LiveFDN = {
    start: start,
    stop: stop,
    update: pushParams,
    isRunning: isRunning,
    prepare: prepare,
    rate: rate,
    colourRev: colourRevNow,
    noteDecay: noteDecay,
    audioState: audioState
  };
})(window);
