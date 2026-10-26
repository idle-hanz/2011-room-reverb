/* Polar tab extras. Display only. Nothing here is posted.
   Ben: SWITCHES is the only on/off. Set a flag false to drop that view. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.RRPolarViews = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var SWITCHES = {
    slice: true,
    angle: true,
    readouts: true,
    compare: true,
    arrivals: true,
    balloon: true
  };

  var SWITCH_LABEL = {
    slice: "One mic at a band",
    angle: "Response at an angle",
    readouts: "Readouts",
    compare: "Compare",
    arrivals: "Arrivals",
    balloon: "Balloon"
  };

  var ANGLE_DEG = [0, 45, 90, 135, 180];
  var DB_FLOOR = -30;
  var PRIMARY = "#2dd4bf";
  var COMPARE = "#f472b6";
  var U87 = "NeumannU87AiCardioid";
  var C414 = "AKGC414Cardioid";

  var pick = { mic: U87, compare: C414, band: 4, angle: 0 };
  var catalogue = [];
  var cache = {};
  var cacheMode = "";
  var roomState = null;
  var balloonView = null;
  var fetchGen = 0;

  function dbRadius(db, outer) {
    if (!(db > DB_FLOOR)) db = DB_FLOOR;
    if (db > 0) db = 0;
    return outer * (db - DB_FLOOR) / (0 - DB_FLOOR);
  }

  function linOf(db) {
    var dbApi = (typeof window !== "undefined" && window.RRDb) || globalThis.RRDb;
    var v = dbApi.dbToLin(Number(db));
    if (!isFinite(v) || v < 0) return 0;
    return v > 1 ? 1 : v;
  }

  function directivityIndexDb(row) {
    var n = row.length;
    var half = Math.floor(n / 2);
    var power = 0;
    var wsum = 0;
    var i, th, w, db;
    for (i = 0; i <= half; i++) {
      th = (i / n) * Math.PI * 2;
      w = Math.sin(th);
      if (i === 0 || i === half) w *= 0.5;
      db = Number(row[i]);
      if (!isFinite(db)) db = -300;
      power += w * Math.pow(10, db / 10);
      wsum += w;
    }
    if (!(wsum > 0)) return 0;
    return -10 * Math.log10(Math.max(power / wsum, 1e-20));
  }

  function frontBackDb(row) {
    var n = row.length;
    var back = row[Math.floor(n / 2)];
    var front = row[0];
    if (!isFinite(front) || !isFinite(back)) return null;
    return front - back;
  }

  function level90Db(row) {
    var n = row.length;
    var v = row[Math.floor(n / 4)];
    return isFinite(v) ? v : null;
  }

  function logX(hz, x0, x1) {
    var lo = Math.log(20);
    var hi = Math.log(16000);
    var t = (Math.log(Math.max(20, hz)) - lo) / (hi - lo);
    if (t < 0) t = 0;
    if (t > 1) t = 1;
    return x0 + t * (x1 - x0);
  }

  function imagePoint(source, room, n) {
    /* FIRST marks use k in −1, 0, 1. Those three match the old local axis.
       |k| > 1 now follows maths_image, which no current mark asks for. */
    var im = (typeof window !== "undefined" && window.RRImage) || globalThis.RRImage;
    return im.imagePoint(source, room, n);
  }

  function arrivalAzimuth(mic, look, point) {
    var dx = point.x - mic.x;
    var dz = point.z - mic.z;
    var len = Math.hypot(dx, dz);
    if (!(len > 1e-9)) return 0;
    var fwd = (dx * look.x + dz * look.z) / len;
    var right = (dx * look.z - dz * look.x) / len;
    return Math.atan2(right, fwd);
  }

  var FIRST = [
    ["Direct", [0, 0, 0], true],
    ["+X", [1, 0, 0], false],
    ["\u2212X", [-1, 0, 0], false],
    ["Ceiling", [0, 1, 0], false],
    ["Floor", [0, -1, 0], false],
    ["+Z", [0, 0, 1], false],
    ["\u2212Z", [0, 0, -1], false]
  ];

  function arrivalMarks(room, source, mic, look) {
    var out = [];
    FIRST.forEach(function (row) {
      var point = row[2] ? source : imagePoint(source, room, row[1]);
      out.push({ name: row[0], azimuth: arrivalAzimuth(mic, look, point), direct: row[2] });
    });
    return out;
  }

  function idealGain(theta, law) {
    var P = window.RRPattern;
    var a = P.polarA(law.family, law.polar);
    return Math.abs(P.firstOrderGain(theta, a));
  }

  function cardioidDbRow(n) {
    var row = [];
    var i, g;
    for (i = 0; i < n; i++) {
      g = Math.abs(0.5 + 0.5 * Math.cos((i / n) * Math.PI * 2));
      row.push(g > 1e-8 ? 20 * Math.log(g) / Math.LN10 : -300);
    }
    return row;
  }

  function el(id) { return document.getElementById(id); }

  function fit(canvas, cssH) {
    if (!canvas) return null;
    var rect = canvas.getBoundingClientRect();
    var ratio = Math.min((typeof window !== "undefined" && window.devicePixelRatio) || 1, 2);
    var cssW = rect.width > 2 ? rect.width : 640;
    var hCss = rect.height > 2 ? rect.height : (cssH || 320);
    var w = Math.max(2, Math.floor(cssW * ratio));
    var h = Math.max(2, Math.floor(hCss * ratio));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    return { w: w, h: h, ratio: ratio };
  }

  function cacheKey(id, hpf) {
    return cacheMode + "|" + id + "|" + (hpf ? "1" : "0");
  }

  function modeOf(state) {
    return (state && state.colour_mode) || "MEASURED_SHELF";
  }

  function hpfFor(state, slot) {
    if (!state) return false;
    if (slot === "c") return !!state.mic_hpf_centre;
    if (slot === "r") return !!(state.mic_hpf_r || state.mic_hpf_sides);
    return !!state.mic_hpf_sides;
  }

  function wanted(state) {
    var rows = [];
    ["l", "c", "r"].forEach(function (slot) {
      var id = (state && state["mic_preset_" + slot]) || U87;
      rows.push({ id: id, hpf_on: hpfFor(state, slot), slot: slot });
    });
    if (SWITCHES.slice || SWITCHES.angle || SWITCHES.balloon) {
      rows.push({ id: pick.mic || U87, hpf_on: false, slot: "slice" });
    }
    if (SWITCHES.compare) {
      rows.push({ id: pick.compare || C414, hpf_on: false, slot: "compare" });
    }
    return rows;
  }

  function recordFor(row) {
    return cache[cacheKey(row.id, row.hpf_on)] || null;
  }

  function ensure(state, done) {
    var nextMode = modeOf(state);
    if (nextMode !== cacheMode) {
      cache = {};
      cacheMode = nextMode;
    }
    var rows = wanted(state);
    var missing = [];
    var seen = {};
    rows.forEach(function (row) {
      var key = cacheKey(row.id, row.hpf_on);
      if (seen[key] || cache[key]) return;
      seen[key] = true;
      missing.push(row);
    });
    if (!missing.length) { done(); return; }
    var gen = ++fetchGen;
    var body = JSON.stringify({
      colour_mode: cacheMode,
      mics: missing.map(function (row) { return { id: row.id, hpf_on: !!row.hpf_on }; })
    });
    fetch("/api/display/field", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body
    }).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    }).then(function (data) {
      if (gen !== fetchGen) return;
      (data.mics || []).forEach(function (mic, i) {
        var row = missing[i];
        if (row && mic) cache[cacheKey(row.id, row.hpf_on)] = mic;
      });
      done();
    }).catch(function () { done(); });
  }

  function lawOf(rec) {
    return {
      family: rec.family || "cardioid",
      polar: rec.polar,
      pattern: rec.pattern || "cardioid"
    };
  }

  function drawDbCurve(ctx, cx, cy, R, row, color, width) {
    var n = row.length;
    ctx.beginPath();
    var i, db, rad, th;
    for (i = 0; i <= n; i++) {
      db = Number(row[i % n]);
      rad = dbRadius(db, R);
      th = (i % n) / n * Math.PI * 2;
      var x = cx + rad * Math.sin(th);
      var y = cy - rad * Math.cos(th);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
  }

  function drawIdeal(ctx, cx, cy, R, law) {
    ctx.save();
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    var i, th, g, db, rad;
    for (i = 0; i <= 128; i++) {
      th = (i / 128) * Math.PI * 2;
      g = idealGain(th, law);
      db = g > 1e-6 ? (20 * Math.log(g) / Math.LN10) : -120;
      rad = dbRadius(db, R);
      var x = cx + rad * Math.sin(th);
      var y = cy - rad * Math.cos(th);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = "rgba(232,234,239,0.92)";
    ctx.lineWidth = 1.25;
    ctx.stroke();
    ctx.restore();
  }

  function paintMarks(ctx, cx, cy, R, yawRad, marks) {
    if (!marks) return;
    ctx.save();
    var fontPx = Math.max(11, Math.round(R * 0.065));
    ctx.font = fontPx + "px Segoe UI, system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    var used = [];
    marks.forEach(function (mark) {
      var screen = mark.azimuth + yawRad;
      var slot = 0;
      var u, da;
      for (u = 0; u < used.length; u++) {
        da = Math.atan2(Math.sin(screen - used[u]), Math.cos(screen - used[u]));
        if (Math.abs(da) < 0.45) slot += 1;
      }
      used.push(screen);
      var rad = R * (mark.direct ? 1.0 : 0.46 + slot * 0.14);
      var x = cx + rad * Math.sin(screen);
      var y = cy - rad * Math.cos(screen);
      ctx.fillStyle = mark.direct ? "#f59e0b" : "#93c5fd";
      ctx.beginPath();
      ctx.arc(x, y, mark.direct ? Math.max(4, R * 0.028) : Math.max(3, R * 0.02), 0, Math.PI * 2);
      ctx.fill();
      var ox = Math.sin(screen);
      var oy = -Math.cos(screen);
      var tx = Math.cos(screen);
      var ty = Math.sin(screen);
      var lx = x + ox * (fontPx + 2) + tx * slot * (fontPx * 3.4);
      var ly = y + oy * (fontPx + 2) + ty * slot * (fontPx * 0.3);
      var pad = fontPx + 4;
      var w = ctx.canvas.width;
      var h = ctx.canvas.height;
      if (lx < pad) lx = pad;
      if (lx > w - pad) lx = w - pad;
      if (ly < pad) ly = pad;
      if (ly > h - pad) ly = h - pad;
      ctx.fillStyle = mark.direct ? "#f59e0b" : "#cbd5e1";
      ctx.fillText(mark.name, lx, ly);
    });
    ctx.restore();
  }

  function poseOf(state, cap) {
    var RM = window.RoomMath;
    if (!RM || !state) return null;
    var geo = RM.compute(state);
    var key = cap;
    var placed = state["place_" + key] === "room" || (key === "c" && state.third_mic === "room");
    if (!placed && state.pair_mode === "ms" && !state.s_detached && String(state.ms_s || "l") === key) {
      var mid = String(state.ms_m || "c");
      if (mid === key) mid = key === "c" ? "l" : "c";
      var host = mid === "l" ? geo.mic_left : (mid === "r" ? geo.mic_right : geo.mic_centre);
      var yawMs = Number(state["yaw_" + key + "_deg"]) || 0;
      return {
        x: host.x, y: host.y, z: host.z, yawDeg: yawMs,
        look: window.RRLook.lookFromYaw(yawMs * Math.PI / 180)
      };
    }
    if (!placed) {
      var mic = key === "l" ? geo.mic_left : (key === "r" ? geo.mic_right : geo.mic_centre);
      var look = key === "l" ? geo.look_l : (key === "r" ? geo.look_r : geo.look_c);
      var yawDeg = key === "l" ? geo.toe_l_deg : (key === "r" ? geo.toe_r_deg : geo.toe_c_deg);
      return { x: mic.x, y: mic.y, z: mic.z, yawDeg: yawDeg, look: look };
    }
    function num(k) {
      var v = state["room_" + key + "_" + k];
      if (v == null || v === "" || !isFinite(Number(v))) v = state["room_" + k];
      var n = Number(v);
      return isFinite(n) ? n : 0;
    }
    var yaw = num("yaw");
    return {
      x: num("x"), y: num("y"), z: num("z"), yawDeg: yaw,
      look: window.RRLook.lookFromYaw(yaw * Math.PI / 180)
    };
  }

  function marksFor(state, cap) {
    if (!SWITCHES.arrivals || !state) return null;
    var pose = poseOf(state, cap);
    if (!pose) return null;
    var RM = window.RoomMath;
    var geo = RM.compute(state);
    return arrivalMarks(
      { W: Number(state.W), H: Number(state.H), L: Number(state.L) },
      geo.source,
      pose,
      pose.look
    );
  }

  function drawSlice() {
    var canvas = el("polarSliceCanvas");
    var rec = cache[cacheKey(pick.mic, false)];
    var cmp = SWITCHES.compare ? cache[cacheKey(pick.compare, false)] : null;
    if (!canvas) return;
    var box = fit(canvas, 320);
    if (!box) return;
    var ctx = canvas.getContext("2d");
    ctx.fillStyle = "#0c0e14";
    ctx.fillRect(0, 0, box.w, box.h);
    var cx = box.w * 0.5;
    var cy = box.h * 0.54;
    var R = Math.min(box.w, box.h) * 0.36;
    if (window.MicDesk && MicDesk.drawPolarChartFrame) {
      MicDesk.drawPolarChartFrame(ctx, cx, cy, R, 0, {
        useDb: true,
        fontPx: Math.max(11, Math.min(14, R * 0.08)),
        lineWidth: 1
      });
    }
    if (!rec || !rec.h_rings || !rec.h_rings.length) {
      ctx.fillStyle = "#8b92a5";
      ctx.font = "13px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Updating\u2026", cx, cy);
      return;
    }
    var band = Math.max(0, Math.min(rec.h_rings.length - 1, pick.band | 0));
    drawIdeal(ctx, cx, cy, R, lawOf(rec));
    drawDbCurve(ctx, cx, cy, R, rec.h_rings[band], PRIMARY, 2.25);
    if (cmp && cmp.h_rings && cmp.h_rings[band]) {
      drawDbCurve(ctx, cx, cy, R, cmp.h_rings[band], COMPARE, 2);
    }
    if (SWITCHES.arrivals && roomState) {
      var pose = poseOf(roomState, "c");
      if (pose) paintMarks(ctx, cx, cy, R, 0, marksFor(roomState, "c"));
    }
    var lab = (rec.ring_labels && rec.ring_labels[band]) || "";
    ctx.fillStyle = "#e8eaef";
    ctx.font = "700 13px Segoe UI, system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText((rec.display_name || rec.id) + "  \u00b7  " + lab, cx, 18);
    if (cmp) {
      ctx.fillStyle = COMPARE;
      ctx.font = "12px Segoe UI, system-ui, sans-serif";
      ctx.fillText(cmp.display_name || cmp.id, cx, 36);
    }
  }

  function drawAngle() {
    var canvas = el("polarAngleCanvas");
    var rec = cache[cacheKey(pick.mic, false)];
    var cmp = SWITCHES.compare ? cache[cacheKey(pick.compare, false)] : null;
    if (!canvas) return;
    var box = fit(canvas, 260);
    if (!box) return;
    var ctx = canvas.getContext("2d");
    ctx.fillStyle = "#0c0e14";
    ctx.fillRect(0, 0, box.w, box.h);
    var left = 46;
    var right = box.w - 16;
    var top = 28;
    var bottom = box.h - 28;
    ctx.strokeStyle = "rgba(255,255,255,0.18)";
    ctx.fillStyle = "#8b92a5";
    ctx.font = "11px Segoe UI, system-ui, sans-serif";
    ctx.textAlign = "right";
    [0, -6, -12, -18, -24].forEach(function (db) {
      var y = top + (0 - db) / 36 * (bottom - top);
      ctx.beginPath();
      ctx.moveTo(left, y);
      ctx.lineTo(right, y);
      ctx.stroke();
      ctx.fillText((db === 0 ? "0" : String(db)) + " dB", left - 6, y + 3);
    });
    ctx.textAlign = "center";
    [20, 100, 1000, 10000, 16000].forEach(function (hz) {
      var x = logX(hz, left, right);
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, bottom);
      ctx.stroke();
      var lab = hz >= 1000 ? (hz / 1000) + "k" : String(hz);
      ctx.fillText(lab, x, bottom + 14);
    });
    function column(recRow) {
      if (!recRow || !recRow.h_angles || !recRow.freqs_hz) return -1;
      var angles = recRow.angles_deg || ANGLE_DEG;
      var want = pick.angle;
      var best = 0;
      var bi, d, bestD = 1e9;
      for (bi = 0; bi < angles.length; bi++) {
        d = Math.abs(Number(angles[bi]) - want);
        if (d < bestD) { bestD = d; best = bi; }
      }
      return best;
    }
    function stroke(recRow, color) {
      var col = column(recRow);
      if (col < 0) return;
      ctx.beginPath();
      var i, db, x, y, moved = false;
      for (i = 0; i < recRow.freqs_hz.length; i++) {
        db = Number(recRow.h_angles[i][col]);
        if (!isFinite(db)) continue;
        if (db > 6) db = 6;
        if (db < -36) db = -36;
        x = logX(recRow.freqs_hz[i], left, right);
        y = top + (0 - db) / 36 * (bottom - top);
        if (!moved) { ctx.moveTo(x, y); moved = true; }
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    stroke(rec, PRIMARY);
    if (cmp) stroke(cmp, COMPARE);
    ctx.fillStyle = "#e8eaef";
    ctx.font = "700 13px Segoe UI, system-ui, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(pick.angle + "\u00b0", left, 16);
  }

  function fmt(v) {
    if (v == null || !isFinite(v)) return "\u2014";
    return (v >= 0 ? "+" : "") + v.toFixed(1);
  }

  function drawReadouts() {
    var body = el("polarReadoutBody");
    if (!body || !roomState) return;
    var html = "";
    ["l", "c", "r"].forEach(function (slot) {
      var id = roomState["mic_preset_" + slot] || U87;
      var rec = cache[cacheKey(id, hpfFor(roomState, slot))];
      var name = slot.toUpperCase();
      if (!rec || !rec.h_rings) {
        html += "<tr><td>" + name + "</td><td colspan=\"4\">Updating\u2026</td></tr>";
        return;
      }
      rec.h_rings.forEach(function (row, bi) {
        var lab = (rec.ring_labels && rec.ring_labels[bi]) || "";
        html += "<tr><td>" + name + "</td><td>" + lab + "</td><td>" +
          fmt(frontBackDb(row)) + "</td><td>" + fmt(level90Db(row)) + "</td><td>" +
          fmt(directivityIndexDb(row)) + "</td></tr>";
      });
    });
    if (body.getAttribute("data-html") === html) return;
    body.setAttribute("data-html", html);
    body.innerHTML = html;
  }

  function drawBalloon() {
    var canvas = el("polarBalloonCanvas");
    var rec = cache[cacheKey(pick.mic, false)];
    var host = el("polarViews");
    if (host && host.hidden) return;
    if (!canvas || typeof window.PolarFieldView === "undefined") return;
    if (!balloonView) {
      balloonView = new window.PolarFieldView({
        canvas: canvas,
        wrap: el("polarBalloonWrap"),
        isolated: true,
        skipHidden: true,
        enabled: {},
        getState: function () { return roomState || {}; }
      });
    }
    if (!rec || !rec.h_rings) return;
    var band = Math.max(0, Math.min(rec.h_rings.length - 1, pick.band | 0));
    var law = lawOf(rec);
    balloonView.showBalloon({
      db: rec.h_rings[band],
      ideal: function (theta) { return idealGain(theta, law); }
    });
    if (balloonView.resize) balloonView.resize();
  }

  function syncVisibility() {
    Object.keys(SWITCHES).forEach(function (key) {
      var box = document.querySelector('[data-polar-view="' + key + '"]');
      if (box) box.checked = !!SWITCHES[key];
      var panel = el("polarExtra-" + key);
      if (!panel) return;
      if (key === "compare") {
        panel.hidden = true;
        return;
      }
      panel.hidden = !SWITCHES[key];
    });
    document.querySelectorAll("[data-polar-compare]").forEach(function (node) {
      node.hidden = !SWITCHES.compare;
    });
  }

  function fillSelect(sel, id) {
    if (!sel) return;
    var html = "";
    catalogue.forEach(function (row) {
      html += '<option value="' + row.mic_id + '">' +
        (row.display_name || row.mic_id) + "</option>";
    });
    if (sel.getAttribute("data-opts") !== html) {
      sel.setAttribute("data-opts", html);
      sel.innerHTML = html;
    }
    if (id && sel.querySelector('option[value="' + id + '"]')) sel.value = id;
  }

  function redraw() {
    if (!SWITCHES.slice && !SWITCHES.angle && !SWITCHES.readouts && !SWITCHES.balloon && !SWITCHES.arrivals) {
      return;
    }
    if (SWITCHES.slice) drawSlice();
    if (SWITCHES.angle) drawAngle();
    if (SWITCHES.readouts) drawReadouts();
    if (SWITCHES.balloon) drawBalloon();
    if (SWITCHES.arrivals) paintArrivals();
  }

  function loadCatalogue(done) {
    fetch("/api/catalogue/mics").then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    }).then(function (data) {
      catalogue = (data.presets || []).filter(function (row) { return row && row.mic_id; });
      fillSelect(el("polarSliceMic"), pick.mic);
      fillSelect(el("polarCompareMic"), pick.compare);
      if (done) done();
    }).catch(function () { if (done) done(); });
  }

  function onRoom(state) {
    roomState = state || roomState;
    if (!roomState) return;
    var host = el("polarViews");
    if (host && host.hidden) return;
    var any = false;
    Object.keys(SWITCHES).forEach(function (key) { if (SWITCHES[key]) any = true; });
    if (!any) return;
    ensure(roomState, redraw);
  }

  function paintArrivals() {
    if (!SWITCHES.arrivals || !roomState) return;
    [["l", "micPolarL"], ["c", "micPolarC"], ["r", "micPolarR"]].forEach(function (pair) {
      var canvas = el(pair[1]);
      var pose = poseOf(roomState, pair[0]);
      if (!canvas || !pose || canvas.width < 2) return;
      var cx = canvas.width * 0.5;
      var cy = canvas.height * 0.52;
      var R = Math.min(canvas.width, canvas.height) * 0.38;
      paintMarks(canvas.getContext("2d"), cx, cy, R, pose.yawDeg * Math.PI / 180, marksFor(roomState, pair[0]));
    });
  }

  function mount() {
    var host = el("polarExtras");
    if (!host || host.getAttribute("data-mounted")) return;
    host.setAttribute("data-mounted", "1");
    var switches = document.createElement("div");
    switches.className = "polar-view-switches";
    switches.id = "polarViewSwitches";
    switches.setAttribute("role", "group");
    switches.setAttribute("aria-label", "Polar views");
    Object.keys(SWITCHES).forEach(function (key) {
      var label = document.createElement("label");
      label.className = "polar-chip";
      var box = document.createElement("input");
      box.type = "checkbox";
      box.checked = !!SWITCHES[key];
      box.setAttribute("data-polar-view", key);
      box.id = "polarView-" + key;
      box.addEventListener("change", function () {
        SWITCHES[key] = !!box.checked;
        syncVisibility();
        onRoom(roomState);
        if (key === "arrivals" && window.micDesk && window.micDesk.redraw) window.micDesk.redraw();
      });
      label.appendChild(box);
      label.appendChild(document.createTextNode(" " + SWITCH_LABEL[key]));
      switches.appendChild(label);
    });
    host.appendChild(switches);

    host.insertAdjacentHTML("beforeend",
      '<div class="polar-extra" id="polarExtra-slice">' +
        '<h3>One mic at a band</h3>' +
        '<p class="hint">One catalogue mic at one frequency. Rings are 0 to \u221224 dB. The dashed line is the ideal pattern.</p>' +
        '<div class="polar-extra-row">' +
          '<label>Mic <select id="polarSliceMic" aria-label="Mic for the single polar"></select></label>' +
          '<label data-polar-compare>Compare <select id="polarCompareMic" aria-label="Second mic"></select></label>' +
          '<label>Frequency <input type="range" id="polarSliceFreq" min="0" max="7" step="1" value="4" aria-label="Frequency band" />' +
          '<span id="polarSliceFreqOut">1k</span></label>' +
        '</div>' +
        '<canvas class="polar-slice-canvas" id="polarSliceCanvas" width="640" height="320" aria-label="Single mic polar"></canvas>' +
      '</div>' +
      '<div class="polar-extra" id="polarExtra-angle">' +
        '<h3>Response at an angle</h3>' +
        '<p class="hint">That mic from 20 Hz to 16 kHz. The curve is the measured grid.</p>' +
        '<div class="polar-extra-row" id="polarAngleChips" role="group" aria-label="Angle"></div>' +
        '<canvas class="polar-angle-canvas" id="polarAngleCanvas" width="720" height="260" aria-label="Frequency response at an angle"></canvas>' +
      '</div>' +
      '<div class="polar-extra" id="polarExtra-readouts">' +
        '<h3>Readouts</h3>' +
        '<p class="hint">Front-to-back is on-axis minus 180\u00b0. Directivity index is the sin-weighted power of that band.</p>' +
        '<table class="polar-readout"><thead><tr><th>Mic</th><th>Band</th><th>Front-to-back dB</th><th>90\u00b0 dB</th><th>Directivity index dB</th></tr></thead>' +
        '<tbody id="polarReadoutBody"></tbody></table>' +
      '</div>' +
      '<div class="polar-extra" id="polarExtra-balloon">' +
        '<h3>Balloon</h3>' +
        '<p class="hint">One mic at the same band, spun with the polar orbit. Drag to turn it.</p>' +
        '<div class="polar-balloon-wrap" id="polarBalloonWrap">' +
          '<canvas id="polarBalloonCanvas" width="900" height="420" aria-label="Polar balloon"></canvas>' +
        '</div>' +
      '</div>'
    );

    var chips = el("polarAngleChips");
    ANGLE_DEG.forEach(function (deg) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip" + (deg === pick.angle ? " active" : "");
      btn.setAttribute("data-polar-angle", String(deg));
      btn.textContent = deg + "\u00b0";
      btn.addEventListener("click", function () {
        pick.angle = deg;
        chips.querySelectorAll("[data-polar-angle]").forEach(function (node) {
          var on = Number(node.getAttribute("data-polar-angle")) === deg;
          node.classList.toggle("active", on);
          node.setAttribute("aria-pressed", on ? "true" : "false");
        });
        drawAngle();
      });
      chips.appendChild(btn);
    });

    var micSel = el("polarSliceMic");
    var cmpSel = el("polarCompareMic");
    var freq = el("polarSliceFreq");
    if (micSel) micSel.addEventListener("change", function () {
      pick.mic = micSel.value;
      onRoom(roomState);
    });
    if (cmpSel) cmpSel.addEventListener("change", function () {
      pick.compare = cmpSel.value;
      onRoom(roomState);
    });
    if (freq) freq.addEventListener("input", function () {
      pick.band = Number(freq.value) || 0;
      var rec = cache[cacheKey(pick.mic, false)];
      var out = el("polarSliceFreqOut");
      if (out) out.textContent = (rec && rec.ring_labels && rec.ring_labels[pick.band]) || "";
      redraw();
    });
    syncVisibility();
    loadCatalogue(function () { if (roomState) onRoom(roomState); });
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", mount);
    } else {
      mount();
    }
  }

  return {
    SWITCHES: SWITCHES,
    ANGLE_DEG: ANGLE_DEG,
    dbRadius: dbRadius,
    directivityIndexDb: directivityIndexDb,
    frontBackDb: frontBackDb,
    level90Db: level90Db,
    logX: logX,
    arrivalMarks: arrivalMarks,
    imagePoint: imagePoint,
    cardioidDbRow: cardioidDbRow,
    onRoom: onRoom,
    paintArrivals: paintArrivals,
    mount: mount,
    redraw: redraw
  };
});
