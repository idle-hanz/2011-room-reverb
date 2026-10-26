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

  function create(opts) {
    opts = opts || {};
    var getState = opts.getState;
    var setState = opts.setState;
    var onChange = opts.onChange || function () {};
    var onDragEnd = opts.onDragEnd || function () {};
    var RoomMath = opts.RoomMath || global.RoomMath;
    var vis = opts.vis || { a: null, b: null };

    var which = "a";
    var plane = "h";
    var freq = 1000;
    var catalog = [];
    var curveKey = "";
    var curveReq = 0;
    var hearReq = 0;
    var hearTimer = 0;
    var editor = null;

    var presetSel = document.getElementById("sourcePreset");
    var yawRange = document.getElementById("sourceYaw");
    var pitchRange = document.getElementById("sourcePitch");
    var sizeRange = document.getElementById("sourceSize");
    var yawNum = document.getElementById("sourceYawNum");
    var pitchNum = document.getElementById("sourcePitchNum");
    var sizeNum = document.getElementById("sourceSizeNum");
    var onsetEl = document.getElementById("sourceOnset");
    var offEl = document.getElementById("sourceOffMic");
    var hearEl = document.getElementById("sourceHear");
    var diffuseEl = document.getElementById("sourceDiffuse");
    var aimEl = document.getElementById("sourceAim");
    var badgeEl = document.getElementById("sourceBadge");
    var polarCanvas = document.getElementById("sourcePolar");
    var chipA = document.getElementById("sourceChipA");
    var chipB = document.getElementById("sourceChipB");
    var polarPanel = document.getElementById("sourcePolarPanel");

    function stNow() { return getState(); }
    function isB() { return which === "b" && stNow().two_sources; }

    function poseNow(st) {
      if (!isB()) {
        return {
          preset: String(st.source_radiation || "omni"),
          yaw: Number(st.source_yaw) || 0,
          pitch: Number(st.source_pitch) || 0,
          follow: false
        };
      }
      var pose = RoomMath.effectiveBPose(st);
      var raw = st.source_radiation_b;
      pose.follow = raw == null || raw === "";
      return pose;
    }
    function presetOf(st) { return poseNow(st).preset; }
    function yawOf(st) { return poseNow(st).yaw; }
    function pitchOf(st) { return poseNow(st).pitch; }
    function faceOf(st) {
      var geo = RoomMath.compute(st);
      var src = isB() && geo.source_b ? geo.source_b : geo.source;
      var mic = geo.mic_centre;
      var dx = mic.x - src.x, dy = mic.y - src.y, dz = mic.z - src.z;
      return {
        yaw: Math.atan2(dx, dz) * 180 / Math.PI,
        pitch: Math.atan2(dy, Math.hypot(dx, dz)) * 180 / Math.PI
      };
    }
    function wrap(d) { return ((Number(d) + 540) % 360) - 180; }
    function writePose(st, yaw, pitch) {
      if (isB()) {
        if (yaw != null) st.source_yaw_b = wrap(yaw);
        if (pitch != null) st.source_pitch_b = Math.max(-89, Math.min(89, pitch));
      } else {
        if (yaw != null) st.source_yaw = wrap(yaw);
        if (pitch != null) st.source_pitch = Math.max(-89, Math.min(89, pitch));
      }
    }
    function commit(st) {
      setState(RoomMath.clampRoom(st));
      onChange();
    }
    function pack() { return vis[isB() ? "b" : "a"]; }

    function tagLabel(tag) {
      var t = String(tag || "");
      if (t.indexOf("MEASURED") >= 0) return "measured fit";
      if (t.indexOf("EXACT") >= 0) return "exact";
      return "assumed";
    }

    function fillPresets(rows) {
      catalog = rows || [];
      if (!presetSel) return;
      var prev = presetSel.value;
      presetSel.innerHTML = "";
      var by = {};
      catalog.forEach(function (row) {
        var c = row.category || "reference";
        if (!by[c]) by[c] = [];
        by[c].push(row);
      });
      if (isB()) {
        var same = document.createElement("option");
        same.value = "";
        same.textContent = "Same as A";
        presetSel.insertBefore(same, presetSel.firstChild);
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
        presetSel.appendChild(og);
      });
      if (prev) presetSel.value = prev;
    }

    function applyPreset(id) {
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

    function setNum(el, value) {
      if (!el || document.activeElement === el) return;
      el.value = String(value);
    }

    function syncWidgets() {
      var st = stNow();
      var pose = poseNow(st);
      var id = pose.preset;
      if (presetSel && document.activeElement !== presetSel) {
        presetSel.value = pose.follow ? "" : id;
      }
      var yaw = Math.round(yawOf(st));
      var pitch = Math.round(pitchOf(st));
      setNum(yawRange, yaw);
      setNum(pitchRange, pitch);
      setNum(yawNum, yaw);
      setNum(pitchNum, pitch);
      var meta = pack();
      var size = st.source_size_m;
      if (size == null || size === "" || !isFinite(Number(size))) {
        size = meta && meta.a_eq_m ? meta.a_eq_m : 0.02;
      }
      setNum(sizeRange, Number(size).toFixed(3));
      setNum(sizeNum, Number(size).toFixed(3));
      if (chipA) chipA.classList.toggle("active", !isB());
      if (chipB) {
        chipB.hidden = !st.two_sources;
        chipB.classList.toggle("active", isB());
      }
      if (!st.two_sources) which = "a";
      var row = null;
      for (var i = 0; i < catalog.length; i++) if (catalog[i].id === id) row = catalog[i];
      if (badgeEl) {
        var tag = row ? tagLabel(row.tag) : (id === "omni" ? "exact" : "");
        badgeEl.textContent = tag;
        badgeEl.className = "honesty-badge " + (tag === "measured fit" ? "honesty-measured" : "honesty-assumed");
        badgeEl.hidden = !tag;
      }
      var omni = id.toLowerCase() === "omni";
      if (polarPanel) polarPanel.classList.toggle("source-omni", omni);
      var face = faceOf(st);
      var off = ((yawOf(st) - face.yaw + 540) % 360) - 180;
      if (offEl) {
        offEl.textContent = omni
          ? "Omni. No facing."
          : (Math.round(yawOf(st)) + "° yaw · " + Math.round(pitchOf(st)) + "° pitch · " +
             (off >= 0 ? "+" : "") + Math.round(off) + "° off the mic");
      }
      if (onsetEl) {
        if (omni) {
          onsetEl.hidden = true;
        } else {
          onsetEl.hidden = false;
          var onset = meta && meta.onset_hz ? Math.round(meta.onset_hz) : 0;
          onsetEl.textContent = onset ? ("Beaming onset ≈ " + onset + " Hz  (c / 2πa)") : "Size uses the preset radius until you move this.";
        }
      }
      if (aimEl) {
        var az = meta && meta.aim_az != null ? Number(meta.aim_az).toFixed(1) : "0";
        var el = meta && meta.aim_el != null ? Number(meta.aim_el).toFixed(1) : "0";
        aimEl.textContent = "Aim offset " + az + "° az, " + el + "° el (from the preset).";
      }
      if (diffuseEl && meta && meta.diffuse_text) diffuseEl.textContent = meta.diffuse_text;
    }

    function drawPolar() {
      if (!polarCanvas) return;
      var ctx = polarCanvas.getContext("2d");
      var w = polarCanvas.width, h = polarCanvas.height;
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
      var table = plane === "v" ? meta.vertical : meta.horizontal;
      var st = stNow();
      var spin = plane === "v" ? pitchOf(st) : yawOf(st);
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
          if (plane === "v") {
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
        ctx.lineWidth = f === freq ? 2.6 : 1.15;
        ctx.globalAlpha = f === freq ? 1 : 0.75;
        ctx.stroke();
        ctx.globalAlpha = 1;
      });
    }

    function curvesBody() {
      var st = Object.assign({}, stNow());
      st.which = isB() ? "b" : "a";
      st.freq = freq;
      return st;
    }
    function takePattern(data) {
      if (!data || data.ok === false) return;
      var key = (isB() ? "b" : "a");
      vis[key] = data;
      if (hearEl && data.direct_db != null) {
        hearEl.textContent = Number(data.direct_db).toFixed(1) + " dB at " +
          Math.round(data.freq || freq) + " Hz on the direct to the mic.";
      }
      if (diffuseEl && data.diffuse_text) diffuseEl.textContent = data.diffuse_text;
      syncWidgets();
      drawPolar();
      if (editor) editor.redraw();
    }
    function fetchCurves() {
      var st = stNow();
      var id = presetOf(st);
      var size = st.source_size_m == null ? "" : String(st.source_size_m);
      var key = (isB() ? "b:" : "a:") + id + ":" + size;
      if (key === curveKey && pack() && pack().horizontal) {
        scheduleHear();
        drawPolar();
        return;
      }
      curveKey = key;
      var req = ++curveReq;
      fetch("/api/params/source", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(curvesBody())
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (req !== curveReq) return;
        takePattern(data);
      }).catch(function () {});
    }
    function scheduleHear() {
      clearTimeout(hearTimer);
      hearTimer = setTimeout(function () {
        var req = ++hearReq;
        fetch("/api/params/source", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(curvesBody())
        }).then(function (r) { return r.json(); }).then(function (data) {
          if (req !== hearReq) return;
          if (!data || data.ok === false) return;
          var cur = pack();
          if (cur && data.direct_db != null) {
            cur.direct_db = data.direct_db;
            cur.diffuse_text = data.diffuse_text || cur.diffuse_text;
            cur.off_mic_deg = data.off_mic_deg;
          } else {
            vis[isB() ? "b" : "a"] = data;
          }
          if (hearEl && data.direct_db != null) {
            hearEl.textContent = Number(data.direct_db).toFixed(1) + " dB at " +
              Math.round(data.freq || freq) + " Hz on the direct to the mic.";
          }
          if (diffuseEl && data.diffuse_text) diffuseEl.textContent = data.diffuse_text;
        }).catch(function () {});
      }, 30);
    }

    function bindRange(range, num, apply) {
      function from(el) {
        var v = Number(el.value);
        if (!isFinite(v)) return;
        apply(v);
      }
      if (range) range.addEventListener("input", function () { from(range); });
      if (num) num.addEventListener("change", function () { from(num); });
    }
    bindRange(yawRange, yawNum, function (v) {
      var st = Object.assign({}, stNow());
      writePose(st, v, null);
      commit(st);
    });
    bindRange(pitchRange, pitchNum, function (v) {
      var st = Object.assign({}, stNow());
      writePose(st, null, v);
      commit(st);
    });
    bindRange(sizeRange, sizeNum, function (v) {
      var st = Object.assign({}, stNow());
      st.source_size_m = Math.max(0.005, Math.min(0.6, v));
      curveKey = "";
      commit(st);
    });
    if (presetSel) presetSel.addEventListener("change", function () { applyPreset(presetSel.value); });

    function chip(id, fn) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("click", fn);
    }
    chip("sourceFaceMic", function () {
      var st = Object.assign({}, stNow());
      var f = faceOf(st);
      writePose(st, f.yaw, f.pitch);
      commit(st);
    });
    chip("sourceFaceAway", function () {
      var st = Object.assign({}, stNow());
      var f = faceOf(st);
      writePose(st, f.yaw + 180, -f.pitch);
      commit(st);
    });
    chip("sourceOmni", function () { applyPreset("omni"); });
    if (chipA) chipA.addEventListener("click", function () {
      which = "a"; curveKey = ""; fillPresets(catalog); redraw();
    });
    if (chipB) chipB.addEventListener("click", function () {
      which = "b"; curveKey = ""; fillPresets(catalog); redraw();
    });

    document.querySelectorAll("[data-src-freq]").forEach(function (btn) {
      var fi = FREQS.indexOf(Number(btn.getAttribute("data-src-freq")));
      if (fi >= 0) btn.style.boxShadow = "inset 0 -3px 0 " + freqColor(fi);
      btn.addEventListener("click", function () {
        freq = Number(btn.getAttribute("data-src-freq")) || 1000;
        document.querySelectorAll("[data-src-freq]").forEach(function (b) {
          b.classList.toggle("active", b === btn);
        });
        scheduleHear();
        drawPolar();
      });
    });
    document.querySelectorAll("[data-src-plane]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        plane = btn.getAttribute("data-src-plane") === "v" ? "v" : "h";
        document.querySelectorAll("[data-src-plane]").forEach(function (b) {
          b.classList.toggle("active", b === btn);
        });
        drawPolar();
      });
    });

    if (global.RoomEditor && document.getElementById("srcFloorCanvas")) {
      editor = global.RoomEditor.create({
        floorCanvas: document.getElementById("srcFloorCanvas"),
        elevCanvas: document.getElementById("srcElevCanvas"),
        getState: getState,
        setState: setState,
        onChange: onChange,
        onDragEnd: onDragEnd,
        sourceMeta: function (w) { return vis[w] || null; }
      });
    }

    fetch("/api/catalogue/sources").then(function (r) { return r.json(); }).then(function (data) {
      fillPresets((data && data.presets) || []);
      syncWidgets();
    }).catch(function () {});

    function redraw() {
      syncWidgets();
      drawPolar();
      fetchCurves();
      if (editor) editor.redraw();
    }

    return { redraw: redraw, editor: editor };
  }

  global.SourceDesk = { create: create };
})(window);
