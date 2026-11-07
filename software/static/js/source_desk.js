/* 2011 Room Reverb — Source desk. Omni is the default and draws no lobe. */
(function (global) {
  "use strict";

  var FREQS = [250, 500, 1000, 2000, 4000, 8000];
  function freqColor(i) {
    var S = global.SpectrumColors;
    if (S) return S.forHz(FREQS[i] || FREQS[FREQS.length - 1]).css;
    var P = global.FreqPalette;
    if (P) return P.hexAt(i, FREQS.length);
    return "#e11d48";
  }
  var GROUPS = [
    ["voice", "Voice"],
    ["brass", "Brass"],
    ["strings", "Strings"],
    ["woodwind", "Woodwinds"],
    ["guitar_amp", "Guitar amps & cabs"],
    ["keys", "Keys"],
    ["reference", "Reference"]
  ];

  var envStack = [];
  function enter(env, fn) {
    var args = [];
    var i;
    for (i = 2; i < arguments.length; i++) args.push(arguments[i]);
    envStack.push(env);
    try {
      return fn.apply(null, args);
    } finally {
      envStack.pop();
    }
  }
  function bindPass(env, fn) {
    return function () {
      envStack.push(env);
      try {
        return fn.apply(null, arguments);
      } finally {
        envStack.pop();
      }
    };
  }
  function create(opts) {
    var env = {};
    env.opts = opts;
    env.opts = env.opts || {};
    env.getState = env.opts.getState;
    env.setState = env.opts.setState;
    env.onChange = env.opts.onChange || function () {};
    env.onDragEnd = env.opts.onDragEnd || function () {};
    env.RoomMath = env.opts.RoomMath || global.RoomMath;
    env.vis = env.opts.vis || { a: null, b: null };

    env.which = "a";
    env.plane = "h";
    env.freq = 1000;
    env.catalog = [];
    env.curveKey = "";
    env.curveReq = 0;
    env.hearReq = 0;
    env.hearTimer = 0;
    env.editor = null;

    env.presetSel = document.getElementById("sourcePreset");
    env.yawRange = document.getElementById("sourceYaw");
    env.pitchRange = document.getElementById("sourcePitch");
    env.sizeRange = document.getElementById("sourceSize");
    env.yawNum = document.getElementById("sourceYawNum");
    env.pitchNum = document.getElementById("sourcePitchNum");
    env.sizeNum = document.getElementById("sourceSizeNum");
    env.onsetEl = document.getElementById("sourceOnset");
    env.offEl = document.getElementById("sourceOffMic");
    env.hearEl = document.getElementById("sourceHear");
    env.diffuseEl = document.getElementById("sourceDiffuse");
    env.aimEl = document.getElementById("sourceAim");
    env.badgeEl = document.getElementById("sourceBadge");
    env.polarCanvas = document.getElementById("sourcePolar");
    env.chipA = document.getElementById("sourceChipA");
    env.chipB = document.getElementById("sourceChipB");
    env.polarPanel = document.getElementById("sourcePolarPanel");

    enter(env, bindRange, env.yawRange, env.yawNum, function (v) {
      var st = Object.assign({}, enter(env, stNow));
      enter(env, writePose, st, v, null);
      enter(env, commit, st);
    });
    enter(env, bindRange, env.pitchRange, env.pitchNum, function (v) {
      var st = Object.assign({}, enter(env, stNow));
      enter(env, writePose, st, null, v);
      enter(env, commit, st);
    });
    enter(env, bindRange, env.sizeRange, env.sizeNum, function (v) {
      var st = Object.assign({}, enter(env, stNow));
      st.source_size_m = Math.max(0.005, Math.min(0.6, v));
      env.curveKey = "";
      enter(env, commit, st);
    });
    if (env.presetSel) env.presetSel.addEventListener("change", function () { enter(env, applyPreset, env.presetSel.value); });

    enter(env, chip, "sourceFaceMic", function () {
      var st = Object.assign({}, enter(env, stNow));
      var f = enter(env, faceOf, st);
      enter(env, writePose, st, f.yaw, f.pitch);
      enter(env, commit, st);
    });
    enter(env, chip, "sourceFaceAway", function () {
      var st = Object.assign({}, enter(env, stNow));
      var f = enter(env, faceOf, st);
      enter(env, writePose, st, f.yaw + 180, -f.pitch);
      enter(env, commit, st);
    });
    enter(env, chip, "sourceOmni", function () { enter(env, applyPreset, "omni"); });
    if (env.chipA) env.chipA.addEventListener("click", function () {
      env.which = "a"; env.curveKey = ""; enter(env, fillPresets, env.catalog); enter(env, redraw);
    });
    if (env.chipB) env.chipB.addEventListener("click", function () {
      env.which = "b"; env.curveKey = ""; enter(env, fillPresets, env.catalog); enter(env, redraw);
    });

    document.querySelectorAll("[data-src-freq]").forEach(function (btn) {
      var fi = FREQS.indexOf(Number(btn.getAttribute("data-src-freq")));
      if (fi >= 0) btn.style.boxShadow = "inset 0 -3px 0 " + freqColor(fi);
      btn.addEventListener("click", function () {
        env.freq = Number(btn.getAttribute("data-src-freq")) || 1000;
        document.querySelectorAll("[data-src-freq]").forEach(function (b) {
          b.classList.toggle("active", b === btn);
        });
        enter(env, scheduleHear);
        enter(env, drawPolar);
      });
    });
    document.querySelectorAll("[data-src-plane]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        env.plane = btn.getAttribute("data-src-plane") === "v" ? "v" : "h";
        document.querySelectorAll("[data-src-plane]").forEach(function (b) {
          b.classList.toggle("active", b === btn);
        });
        enter(env, drawPolar);
      });
    });

    if (global.RoomEditor && document.getElementById("srcFloorCanvas")) {
      env.editor = global.RoomEditor.create({
        floorCanvas: document.getElementById("srcFloorCanvas"),
        elevCanvas: document.getElementById("srcElevCanvas"),
        getState: env.getState,
        setState: env.setState,
        onChange: env.onChange,
        onDragEnd: env.onDragEnd,
        sourceMeta: function (w) { return env.vis[w] || null; }
      });
    }

    fetch("/api/catalogue/sources").then(function (r) { return r.json(); }).then(function (data) {
      enter(env, fillPresets, (data && data.presets) || []);
      enter(env, syncWidgets);
    }).catch(function () {});

    return { redraw: bindPass(env, redraw), editor: env.editor };
  }
  function stNow() { var env = envStack[envStack.length - 1]; return env.getState(); }
  function isB() { var env = envStack[envStack.length - 1]; return env.which === "b" && stNow().two_sources; }
  function poseNow(st) { var env = envStack[envStack.length - 1];
      if (!isB()) {
        return {
          preset: String(st.source_radiation || "omni"),
          yaw: Number(st.source_yaw) || 0,
          pitch: Number(st.source_pitch) || 0,
          follow: false
        };
      }
      var pose = env.RoomMath.effectiveBPose(st);
      var raw = st.source_radiation_b;
      pose.follow = raw == null || raw === "";
      return pose;
    }
  function presetOf(st) { var env = envStack[envStack.length - 1]; return poseNow(st).preset; }
  function yawOf(st) { var env = envStack[envStack.length - 1]; return poseNow(st).yaw; }
  function pitchOf(st) { var env = envStack[envStack.length - 1]; return poseNow(st).pitch; }
  function faceOf(st) { var env = envStack[envStack.length - 1];
      var geo = env.RoomMath.compute(st);
      var src = isB() && geo.source_b ? geo.source_b : geo.source;
      var mic = geo.mic_centre;
      var dx = mic.x - src.x, dy = mic.y - src.y, dz = mic.z - src.z;
      return {
        yaw: Math.atan2(dx, dz) * 180 / Math.PI,
        pitch: Math.atan2(dy, Math.hypot(dx, dz)) * 180 / Math.PI
      };
    }
  function wrap(d) { var env = envStack[envStack.length - 1]; return ((Number(d) + 540) % 360) - 180; }
  function writePose(st, yaw, pitch) { var env = envStack[envStack.length - 1];
      if (isB()) {
        if (yaw != null) st.source_yaw_b = wrap(yaw);
        if (pitch != null) st.source_pitch_b = Math.max(-89, Math.min(89, pitch));
      } else {
        if (yaw != null) st.source_yaw = wrap(yaw);
        if (pitch != null) st.source_pitch = Math.max(-89, Math.min(89, pitch));
      }
    }
  function commit(st) { var env = envStack[envStack.length - 1];
      env.setState(env.RoomMath.clampRoom(st));
      env.onChange();
    }
  function pack() { var env = envStack[envStack.length - 1]; return env.vis[isB() ? "b" : "a"]; }
  function tagLabel(tag) { var env = envStack[envStack.length - 1];
      var t = String(tag || "");
      if (t.indexOf("MEASURED") >= 0) return "measured fit";
      if (t.indexOf("EXACT") >= 0) return "exact";
      return "assumed";
    }
  function fillPresets(rows) { var env = envStack[envStack.length - 1];
      env.catalog = rows || [];
      if (!env.presetSel) return;
      var prev = env.presetSel.value;
      env.presetSel.innerHTML = "";
      var by = {};
      env.catalog.forEach(function (row) {
        var c = row.category || "reference";
        if (!by[c]) by[c] = [];
        by[c].push(row);
      });
      if (isB()) {
        var same = document.createElement("option");
        same.value = "";
        same.textContent = "Same as A";
        env.presetSel.insertBefore(same, env.presetSel.firstChild);
      }
      GROUPS.forEach(function (g) {
        var list = by[g[0]];
        if (!list || !list.length) return;
        var og = document.createElement("optgroup");
        og.label = g[1];
        list.forEach(function (row) {
          var opt = document.createElement("option");
          opt.value = row.id;
          opt.textContent = row.label || row.id;
          var rmse = row.rmse_holdout_db;
          opt.title = (row.dataset || "") + (rmse != null ? (" · hold-out " + Number(rmse).toFixed(2) + " dB") : "");
          og.appendChild(opt);
        });
        env.presetSel.appendChild(og);
      });
      if (prev) env.presetSel.value = prev;
    }
  function applyPreset(id) { var env = envStack[envStack.length - 1];
      var st = Object.assign({}, stNow());
      if (isB() && (id == null || id === "")) {
        st.source_radiation_b = null;
        st.source_yaw_b = null;
        st.source_pitch_b = null;
        commit(st);
        return;
      }
      if (isB()) st.source_radiation_b = id;
      else st.source_radiation = id;
      if (String(id).toLowerCase() !== "omni") {
        var f = faceOf(st);
        writePose(st, f.yaw, f.pitch);
      }
      commit(st);
    }
  function setNum(el, value) { var env = envStack[envStack.length - 1];
      if (!el || document.activeElement === el) return;
      el.value = String(value);
    }
  function syncWidgets() { var env = envStack[envStack.length - 1];
      var st = stNow();
      var pose = poseNow(st);
      var id = pose.preset;
      if (env.presetSel && document.activeElement !== env.presetSel) {
        env.presetSel.value = pose.follow ? "" : id;
      }
      var yaw = Math.round(yawOf(st));
      var pitch = Math.round(pitchOf(st));
      setNum(env.yawRange, yaw);
      setNum(env.pitchRange, pitch);
      setNum(env.yawNum, yaw);
      setNum(env.pitchNum, pitch);
      var meta = pack();
      var size = st.source_size_m;
      if (size == null || size === "" || !isFinite(Number(size))) {
        size = meta && meta.a_eq_m ? meta.a_eq_m : 0.02;
      }
      setNum(env.sizeRange, Number(size).toFixed(3));
      setNum(env.sizeNum, Number(size).toFixed(3));
      if (env.chipA) env.chipA.classList.toggle("active", !isB());
      if (env.chipB) {
        env.chipB.hidden = !st.two_sources;
        env.chipB.classList.toggle("active", isB());
      }
      if (!st.two_sources) env.which = "a";
      var row = null;
      for (var i = 0; i < env.catalog.length; i++) if (env.catalog[i].id === id) row = env.catalog[i];
      if (env.badgeEl) {
        var tag = row ? tagLabel(row.tag) : (id === "omni" ? "exact" : "");
        env.badgeEl.textContent = tag;
        env.badgeEl.className = "honesty-badge " + (tag === "measured fit" ? "honesty-measured" : "honesty-assumed");
        env.badgeEl.hidden = !tag;
      }
      var omni = id.toLowerCase() === "omni";
      if (env.polarPanel) env.polarPanel.classList.toggle("source-omni", omni);
      var face = faceOf(st);
      var off = ((yawOf(st) - face.yaw + 540) % 360) - 180;
      if (env.offEl) {
        env.offEl.textContent = omni
          ? "Omni. No facing."
          : (Math.round(yawOf(st)) + "° yaw · " + Math.round(pitchOf(st)) + "° pitch · " +
             (off >= 0 ? "+" : "") + Math.round(off) + "° off the mic");
      }
      if (env.onsetEl) {
        if (omni) {
          env.onsetEl.hidden = true;
        } else {
          env.onsetEl.hidden = false;
          var onset = meta && meta.onset_hz ? Math.round(meta.onset_hz) : 0;
          env.onsetEl.textContent = onset ? ("Beaming onset ≈ " + onset + " Hz  (c / 2πa)") : "Size uses the preset radius until you move this.";
        }
      }
      if (env.aimEl) {
        var az = meta && meta.aim_az != null ? Number(meta.aim_az).toFixed(1) : "0";
        var el = meta && meta.aim_el != null ? Number(meta.aim_el).toFixed(1) : "0";
        env.aimEl.textContent = "Aim offset " + az + "° az, " + el + "° el (from the preset).";
      }
      if (env.diffuseEl && meta && meta.diffuse_text) env.diffuseEl.textContent = meta.diffuse_text;
    }
  function drawPolar() { var env = envStack[envStack.length - 1];
      if (!env.polarCanvas) return;
      var ctx = env.polarCanvas.getContext("2d");
      var w = env.polarCanvas.width, h = env.polarCanvas.height;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#0a0b0e";
      ctx.fillRect(0, 0, w, h);
      var cx = w * 0.5, cy = h * 0.52, R = Math.min(w, h) * 0.36;
      ctx.strokeStyle = "rgba(255,255,255,0.08)";
      ctx.fillStyle = "#8b92a5";
      ctx.font = "11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      [0, -10, -20, -30].forEach(function (db) {
        var r = ((db + 30) / 30) * R;
        ctx.beginPath();
        ctx.arc(cx, cy, Math.max(1, r), 0, Math.PI * 2);
        ctx.stroke();
        if (db < 0) ctx.fillText(db + " dB", cx + 4, cy - r + 12);
      });
      var meta = pack();
      if (!meta || meta.omni) {
        ctx.beginPath();
        ctx.arc(cx, cy, R, 0, Math.PI * 2);
        ctx.strokeStyle = "#2dd4bf";
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = "#8b92a5";
        ctx.textAlign = "center";
        ctx.fillText("Omni", cx, cy);
        return;
      }
      var table = env.plane === "v" ? meta.vertical : meta.horizontal;
      var st = stNow();
      var spin = env.plane === "v" ? pitchOf(st) : yawOf(st);
      if (!table) return;
      FREQS.forEach(function (f, fi) {
        var curve = table[String(f)] || table[f];
        if (!curve) return;
        var angles = meta.angles || [];
        ctx.beginPath();
        for (var i = 0; i < curve.length; i++) {
          var ang = ((angles.length === curve.length ? angles[i] : (-180 + i * 5)) + spin) * Math.PI / 180;
          var db = Number(curve[i]);
          var r = Math.max(0, Math.min(1, (db + 30) / 30)) * R;
          var x, y;
          if (env.plane === "v") {
            x = cx + r * Math.cos(ang);
            y = cy - r * Math.sin(ang);
          } else {
            x = cx + r * Math.sin(ang);
            y = cy - r * Math.cos(ang);
          }
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.strokeStyle = freqColor(fi);
        ctx.lineWidth = f === env.freq ? 2.6 : 1.15;
        ctx.globalAlpha = f === env.freq ? 1 : 0.75;
        ctx.stroke();
        ctx.globalAlpha = 1;
      });
    }
  function curvesBody() { var env = envStack[envStack.length - 1];
      var st = Object.assign({}, stNow());
      st.which = isB() ? "b" : "a";
      st.freq = env.freq;
      return st;
    }
  function takePattern(data) { var env = envStack[envStack.length - 1];
      if (!data || data.ok === false) return;
      var key = (isB() ? "b" : "a");
      env.vis[key] = data;
      if (env.hearEl && data.direct_db != null) {
        env.hearEl.textContent = Number(data.direct_db).toFixed(1) + " dB at " +
          Math.round(data.freq || env.freq) + " Hz on the direct to the mic.";
      }
      if (env.diffuseEl && data.diffuse_text) env.diffuseEl.textContent = data.diffuse_text;
      syncWidgets();
      drawPolar();
      if (env.editor) env.editor.redraw();
    }
  function fetchCurves() { var env = envStack[envStack.length - 1];
      var st = stNow();
      var id = presetOf(st);
      var size = st.source_size_m == null ? "" : String(st.source_size_m);
      var key = (isB() ? "b:" : "a:") + id + ":" + size;
      if (key === env.curveKey && pack() && pack().horizontal) {
        scheduleHear();
        drawPolar();
        return;
      }
      env.curveKey = key;
      var req = ++env.curveReq;
      fetch("/api/params/source", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(curvesBody())
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (req !== env.curveReq) return;
        enter(env, takePattern, data);
      }).catch(function () {});
    }
  function scheduleHear() { var env = envStack[envStack.length - 1];
      clearTimeout(env.hearTimer);
      env.hearTimer = setTimeout(function () {
        var req = ++env.hearReq;
        fetch("/api/params/source", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(enter(env, curvesBody))
        }).then(function (r) { return r.json(); }).then(function (data) {
          if (req !== env.hearReq) return;
          if (!data || data.ok === false) return;
          var cur = enter(env, pack);
          if (cur && data.direct_db != null) {
            cur.direct_db = data.direct_db;
            cur.diffuse_text = data.diffuse_text || cur.diffuse_text;
            cur.off_mic_deg = data.off_mic_deg;
          } else {
            env.vis[enter(env, isB) ? "b" : "a"] = data;
          }
          if (env.hearEl && data.direct_db != null) {
            env.hearEl.textContent = Number(data.direct_db).toFixed(1) + " dB at " +
              Math.round(data.freq || env.freq) + " Hz on the direct to the mic.";
          }
          if (env.diffuseEl && data.diffuse_text) env.diffuseEl.textContent = data.diffuse_text;
        }).catch(function () {});
      }, 30);
    }
  function bindRange(range, num, apply) { var env = envStack[envStack.length - 1];
      function from(el) {
        var v = Number(el.value);
        if (!isFinite(v)) return;
        apply(v);
      }
      if (range) range.addEventListener("input", function () { from(range); });
      if (num) num.addEventListener("change", function () { from(num); });
    }
  function chip(id, fn) { var env = envStack[envStack.length - 1];
      var el = document.getElementById(id);
      if (el) el.addEventListener("click", fn);
    }
  function redraw() { var env = envStack[envStack.length - 1];
      syncWidgets();
      drawPolar();
      fetchCurves();
      if (env.editor) env.editor.redraw();
    }

  global.SourceDesk = { create: create };
})(window);
