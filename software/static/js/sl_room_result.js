/* SL1 + SL5 + SL6 prebuild: Surfaces "Room result" panel, Decay mode selector, per-face Treatment rows,
   Auto-treat suggestions (Accept / Discard). Standalone; talks to /api/room_result, /api/auto_treat,
   /api/make_panel. Needs window.RRState (app.js state) and window.RRColourSurfaces (the Surfaces tab
   instance): in the box copy one hook line in app.js syncUINow() sets both.
   State it owns: state.decay_mode ("flat" | "surfaces"), state.surf_treatment (rows, suggested:false),
   state.surf_suggestions (rows, suggested:true, never posted as treatment). */
(function () {
  "use strict";
  var LETTERS = ["A", "B", "C", "D", "E", "F"];
  var FACE_NAME = { A: "Left wall", B: "Front wall", C: "Right wall", D: "Rear wall", E: "Floor", F: "Ceiling" };
  var POROUS = [
    ["absorber_panel_1in_gap1in", "1\u2033 panel + 1\u2033 gap"], ["absorber_panel_2in", "2\u2033 panel"],
    ["absorber_panel_2in_gap2in", "2\u2033 panel + 2\u2033 gap"], ["absorber_panel_4in_gap4in", "4\u2033 panel + 4\u2033 gap"]
  ];
  var MAX_COVER = 0.9;
  /* Build stage: 1 = SL1 (Surfaces chip greyed "coming", no Treatment / Auto-treat), 2-4 = Surfaces chip live,
     5 = + Treatment list, 6 = + Auto-treat (all, as proved on the box). Set window.RR_SL_STAGE before this file loads. */
  var SL_STAGE = Number(window.RR_SL_STAGE) || 6;
  var view = { band: true, ebu: false, last: null, busy: false, timer: 0, plan: null };

  function st() { return window.RRState || null; }
  function cs() { return window.RRColourSurfaces || null; }
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
  function rows() { var s = st(); if (!s) return []; if (!Array.isArray(s.surf_treatment)) s.surf_treatment = []; return s.surf_treatment; }
  function sugg() { var s = st(); if (!s) return []; if (!Array.isArray(s.surf_suggestions)) s.surf_suggestions = []; return s.surf_suggestions; }
  function face() { var c = cs(); return (c && c.selected) || "A"; }
  function faceCover(k, list) { return (list || rows()).filter(function (r) { return r.face === k && r.on !== false; }).reduce(function (a, r) { return a + Number(r.coverage || 0); }, 0); }
  function areas() { var s = st() || { W: 6, H: 3, L: 8 }; return { A: s.L * s.H, C: s.L * s.H, B: s.W * s.H, D: s.W * s.H, E: s.W * s.L, F: s.W * s.L }; }
  function uid(p) { return p + "_" + Math.random().toString(36).slice(2, 8); }

  function post(url, extra) {
    var s = st(); var body = JSON.parse(JSON.stringify(s || {}));
    if (extra) Object.keys(extra).forEach(function (k) { body[k] = extra[k]; });
    body.surf_treatment = rows();
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) throw new Error(url + " " + r.status); return r.json(); });
  }

  /* ---------------------------------------------------------------- build DOM */
  function build() {
    var host = document.getElementById("surfacesPanel");
    if (!host || document.getElementById("slRoomResult")) return !!host;
    var panel = el("div", "panel sl-rr"); panel.id = "slRoomResult";
    var head = el("div", "panel-head");
    head.appendChild(el("h2", null, "Room result"));
    head.appendChild(el("span", "hint", "Eyring/Arau from the faces, treatment and air \u00b7 target = M\u00e4kivirta (EQ_PLAN) \u00b7 dots = last Render T20"));
    panel.appendChild(head);
    var mode = el("div", "sl-mode"); mode.id = "slDecayMode";
    mode.appendChild(el("span", "sl-label", "Decay"));
    [["flat", "Flat (2011)"], ["surfaces", "Surfaces"], ["natural", "Natural (air)"]].forEach(function (m) {
      var b = el("button", "chip", m[1]); b.type = "button"; b.dataset.mode = m[0]; b.id = "slMode_" + m[0];
      if (m[0] === "natural") { b.disabled = true; b.title = "Built in SL7a (ST-1/ST-2)"; }
      if (m[0] === "surfaces" && SL_STAGE < 2) { b.disabled = true; b.title = "coming (SL2)"; }
      if (m[0] === "surfaces" && SL_STAGE >= 3) b.title = "Surfaces in Play";
      b.addEventListener("click", function () {
        var s = st(); if (!s || b.disabled) return;
        s.decay_mode = m[0]; paintMode(); schedule();
        if (window.RRPushLive) window.RRPushLive();
      });
      mode.appendChild(b);
    });
    mode.appendChild(el("span", "hint", SL_STAGE < 3
      ? "Surfaces = the materials and treatment set the decay per band. Render only. Play: Render only until SL3."
      : "Surfaces = the materials and treatment set the decay per band. Surfaces in Play."));
    panel.appendChild(mode);
    var cv = el("canvas"); cv.id = "slRtCanvas"; cv.width = 760; cv.height = 230; cv.setAttribute("aria-label", "Decay time per third octave");
    panel.appendChild(cv);
    var tog = el("div", "sl-toggles");
    [["slTogBand", "\u00b110 % band", "band"], ["slTogEbu", "EBU control-room tolerance", "ebu"]].forEach(function (t) {
      var b = el("button", "chip", t[1]); b.type = "button"; b.id = t[0];
      b.addEventListener("click", function () { view[t[2]] = !view[t[2]]; paintToggles(); draw(); });
      tog.appendChild(b);
    });
    var ro = el("span", "sl-readout"); ro.id = "slReadout"; tog.appendChild(ro);
    panel.appendChild(tog);
    // Auto-treat
    var at = el("div", "sl-autotreat"); at.id = "slAutoTreat";
    var btn = el("button", "chip sl-primary", "Auto-treat to"); btn.type = "button"; btn.id = "slAutoBtn";
    var tm = el("input"); tm.type = "number"; tm.id = "slAutoTmid"; tm.min = "0.15"; tm.max = "6"; tm.step = "0.05"; tm.value = dialS().toFixed(2);
    tm.title = "Defaults to the decay dial (SURFACES_IN_LOOP: Auto-treat to target T_mid = [dial])";
    tm.addEventListener("input", function () { tm.dataset.user = "1"; });
    var ebu = el("button", "chip", "EBU control room"); ebu.type = "button"; ebu.id = "slAutoEbu";
    at.appendChild(btn); at.appendChild(tm); at.appendChild(el("span", "sl-unit", "s T_mid")); at.appendChild(ebu);
    at.appendChild(el("span", "hint", "Suggests rows only. Nothing changes until you Accept."));
    btn.addEventListener("click", function () { autoTreat(Number(tm.value)); });
    ebu.addEventListener("click", function () { autoTreat("ebu"); });
    if (SL_STAGE < 6) at.hidden = true;
    panel.appendChild(at);
    var ln = el("p", "hint sl-locknote"); ln.id = "slLockNote"; ln.hidden = true; panel.appendChild(ln);
    var sg = el("div", "sl-suggest"); sg.id = "slSuggest"; panel.appendChild(sg);
    // insert after the room net
    var net = host.querySelector(".room-net-wrap");
    if (net && net.nextSibling) host.insertBefore(panel, net.nextSibling); else host.appendChild(panel);
    // Treatment list inside the selected-face detail
    var det = document.getElementById("surfaceDetail");
    var tr = el("div", "sl-treat"); tr.id = "slTreatment";
    if (SL_STAGE < 5) tr.hidden = true;
    (det || host).insertBefore(tr, det ? det.querySelector(".surfaces-advanced") : null);
    hookSelect();
    paintMode(); paintToggles(); paintRows(); paintSuggest();
    return true;
  }

  function hookSelect() {
    var c = cs(); if (!c || c._slHooked) return;
    var orig = c.select;
    if (typeof orig === "function") {
      c.select = function () { var r = orig.apply(this, arguments); paintRows(); return r; };
      c._slHooked = true;
    }
    var orig2 = c.setSurfaces;
    if (typeof orig2 === "function") c.setSurfaces = function () { var r = orig2.apply(this, arguments); schedule(); return r; };
  }

  function paintMode() {
    var s = st(); var m = (s && s.decay_mode) || "flat";
    Array.prototype.forEach.call(document.querySelectorAll("#slDecayMode button"), function (b) {
      b.setAttribute("aria-pressed", b.dataset.mode === m ? "true" : "false"); b.classList.toggle("on", b.dataset.mode === m);
    });
    var p = document.getElementById("slRoomResult"); if (p) p.classList.toggle("sl-flat", m === "flat");
  }
  function paintToggles() {
    var a = document.getElementById("slTogBand"), b = document.getElementById("slTogEbu");
    if (a) { a.setAttribute("aria-pressed", view.band ? "true" : "false"); a.classList.toggle("on", view.band); }
    if (b) { b.setAttribute("aria-pressed", view.ebu ? "true" : "false"); b.classList.toggle("on", view.ebu); }
  }

  /* ---------------------------------------------------------------- Treatment rows */
  function rowLabel(r) {
    if (r.type === "porous") { var p = POROUS.filter(function (x) { return x[0] === r.material; })[0]; return "Porous \u00b7 " + (p ? p[1] : r.material); }
    if (r.type === "shell") return "Room shell \u00b7 " + Math.round(r.f0) + " Hz (ASSUMED)";
    return (r.type === "membrane" ? "Membrane" : "Helmholtz") + " \u00b7 " + Math.round(r.f0) + " Hz";
  }
  function rowLine(r, list, suggested) {
    var A = areas()[r.face] || 0;
    var line = el("div", "sl-row" + (suggested ? " sl-row-sug" : "") + (r.on === false ? " sl-row-off" : ""));
    line.dataset.id = r.id;
    if (!suggested) {
      var on = el("input"); on.type = "checkbox"; on.checked = r.on !== false; on.title = "On / off"; on.className = "sl-on";
      on.addEventListener("change", function () { r.on = on.checked; paintRows(); schedule(); });
      line.appendChild(on);
    } else line.appendChild(el("span", "sl-face", r.face));
    line.appendChild(el("span", "sl-kind", rowLabel(r)));
    line.appendChild(el("span", "sl-build", r.build || ""));
    var cov = el("input"); cov.type = "number"; cov.min = "0"; cov.max = "90"; cov.step = "1"; cov.value = String(Math.round(Number(r.coverage) * 1000) / 10); cov.className = "sl-cov";
    cov.disabled = !!suggested;
    cov.addEventListener("change", function () {
      var want = Math.max(0, Math.min(90, Number(cov.value) || 0)) / 100;
      var other = faceCover(r.face, list) - Number(r.coverage || 0);
      var lim = Math.max(0, MAX_COVER - other);
      r.coverage = Math.round(Math.min(want, lim) * 1000) / 1000;
      if (want > lim + 1e-9) flash("Face " + r.face + " can hold at most 90 % treatment.");
      paintRows(); schedule();
    });
    line.appendChild(cov); line.appendChild(el("span", "sl-unit", "%"));
    line.appendChild(el("span", "sl-area", (Number(r.coverage) * A).toFixed(1) + " m\u00b2"));
    if (!suggested) {
      var x = el("button", "chip sl-x", "\u00d7"); x.type = "button"; x.title = "Remove row";
      x.addEventListener("click", function () { var L = rows(); var i = L.indexOf(r); if (i >= 0) L.splice(i, 1); paintRows(); schedule(); });
      line.appendChild(x);
    } else {
      var acc = el("button", "chip", "Accept"); acc.type = "button";
      acc.addEventListener("click", function () { accept([r]); });
      var dis = el("button", "chip", "Discard"); dis.type = "button";
      dis.addEventListener("click", function () { var L = sugg(); L.splice(L.indexOf(r), 1); paintSuggest(); });
      line.appendChild(acc); line.appendChild(dis);
    }
    return line;
  }

  function paintRows() {
    var box = document.getElementById("slTreatment"); if (!box) return;
    box.innerHTML = "";
    var k = face();
    var h = el("div", "sl-treat-head");
    h.appendChild(el("h3", null, "Treatment \u00b7 " + k + " " + (FACE_NAME[k] || "")));
    var used = faceCover(k);
    h.appendChild(el("span", "hint", Math.round(used * 100) + " % of " + areas()[k].toFixed(1) + " m\u00b2 treated (max 90 %)"));
    box.appendChild(h);
    var mine = rows().filter(function (r) { return r.face === k; });
    if (!mine.length) box.appendChild(el("p", "hint", "No treatment on this face. Add a panel, or use Auto-treat."));
    mine.forEach(function (r) { box.appendChild(rowLine(r, rows(), false)); });
    var add = el("div", "sl-add");
    var sel = el("select"); sel.id = "slPorousSel";
    POROUS.forEach(function (p) { var o = el("option", null, p[1]); o.value = p[0]; sel.appendChild(o); });
    sel.value = "absorber_panel_4in_gap4in";
    var bp = el("button", "chip", "+ Porous"); bp.type = "button"; bp.id = "slAddPorous";
    bp.addEventListener("click", function () {
      if (k === "E") { flash("Porous panels are wall and ceiling only (library rule)."); return; }
      var room = MAX_COVER - faceCover(k); if (room < 0.01) { flash("Face " + k + " is full (90 %)."); return; }
      rows().push({ id: uid("por"), face: k, type: "porous", material: sel.value, coverage: Math.round(Math.min(0.25, room) * 1000) / 1000, on: true, build: sel.options[sel.selectedIndex].text });
      paintRows(); schedule();
    });
    var f0 = el("input"); f0.type = "number"; f0.min = "30"; f0.max = "299"; f0.step = "1"; f0.value = "125"; f0.id = "slPanelF0";
    var bt = el("button", "chip", "+ Tuned panel"); bt.type = "button"; bt.id = "slAddPanel";
    bt.title = "Membrane below 180 Hz, Helmholtz above (Cox & D'Antonio ch. 7)";
    bt.addEventListener("click", function () {
      post("/api/make_panel", { f0: Number(f0.value) }).then(function (d) {
        if (!d.row) { flash("No practical panel for that frequency (< 300 Hz only)."); return; }
        var r = d.row; r.face = k; r.suggested = false; r.id = uid("pan");
        var room = MAX_COVER - faceCover(k); r.coverage = Math.round(Math.min(r.coverage, room) * 1000) / 1000;
        if (r.coverage <= 0) { flash("Face " + k + " is full (90 %)."); return; }
        rows().push(r); paintRows(); schedule();
      }).catch(function (e) { flash(String(e)); });
    });
    var bs = el("button", "chip", "+ Room shell (walls)"); bs.type = "button"; bs.id = "slAddShell";
    bs.title = "D-SL6: doors, glazing, stud walls as a 90 Hz membrane on 30 % of each wall (ASSUMED)";
    bs.addEventListener("click", function () {
      ["A", "B", "C", "D"].forEach(function (w) {
        if (rows().some(function (r) { return r.type === "shell" && r.face === w; })) return;
        var room = MAX_COVER - faceCover(w); if (room < 0.05) return;
        rows().push({ id: "shell_" + w, face: w, type: "shell", f0: 90, q: 1, amax: 0.35, coverage: Math.min(0.3, room), on: true, assumed: true, build: "room shell (doors, glazing, stud walls)" });
      });
      paintRows(); schedule();
    });
    add.appendChild(sel); add.appendChild(bp); add.appendChild(f0); add.appendChild(el("span", "sl-unit", "Hz")); add.appendChild(bt); add.appendChild(bs);
    box.appendChild(add);
  }

  /* ---------------------------------------------------------------- Auto-treat */
  function autoTreat(tmid) {
    var s = st(); if (!s) return;
    flash("Auto-treat\u2026");
    post("/api/auto_treat", { t_mid: tmid }).then(function (d) {
      view.plan = d;
      var L = sugg(); L.length = 0;
      (d.suggested || []).forEach(function (r) { L.push(r); });
      if (tmid === "ebu") { var t = document.getElementById("slAutoTmid"); if (t) { t.value = String(d.t_mid); t.dataset.user = "1"; } }
      paintSuggest(); flash("");
    }).catch(function (e) { flash(String(e)); });
  }
  function accept(list) {
    var L = sugg();
    list.forEach(function (r) {
      var room = MAX_COVER - faceCover(r.face);
      var c = Math.min(Number(r.coverage), room);
      if (c > 0) { var rr = JSON.parse(JSON.stringify(r)); rr.suggested = false; rr.coverage = Math.round(c * 1000) / 1000; rr.id = uid("acc"); rows().push(rr); }
      var i = L.indexOf(r); if (i >= 0) L.splice(i, 1);
    });
    paintSuggest(); paintRows(); schedule();
  }
  function paintSuggest() {
    var box = document.getElementById("slSuggest"); if (!box) return;
    box.innerHTML = "";
    var L = sugg(); if (!L.length) return;
    var d = view.plan || {};
    var h = el("div", "sl-sug-head");
    h.appendChild(el("strong", null, "Suggested treatment (" + L.length + " rows, target " + (d.t_mid || "?") + " s)"));
    // the plan count is in absolute seconds at the Auto-treat target; the readout below counts against the dial target
    h.appendChild(el("span", "hint", "model at " + (d.t_mid || "?") + " s: " + (d.n_within_10pct != null ? d.n_within_10pct : "?") + "/" + (d.n_bands || 24) +
      " third-octaves within \u00b110 % \u00b7 Schroeder " + (d.schroeder_before || "?") + " \u2192 " + (d.schroeder_after || "?") + " Hz"));
    var all = el("button", "chip sl-primary", "Accept all"); all.type = "button"; all.id = "slAcceptAll";
    all.addEventListener("click", function () { accept(sugg().slice()); });
    var none = el("button", "chip", "Discard all"); none.type = "button"; none.id = "slDiscardAll";
    none.addEventListener("click", function () { sugg().length = 0; paintSuggest(); });
    h.appendChild(all); h.appendChild(none);
    box.appendChild(h);
    if (d.shape_only) box.appendChild(el("p", "hint", "The room is already shorter than " + d.t_mid + " s at mid, and treatment can only shorten it. " +
      "These rows fix the shape at the room's own " + d.t_fit + " s; Decay lock sets the length."));
    L.forEach(function (r) { box.appendChild(rowLine(r, L, true)); });
  }

  /* ---------------------------------------------------------------- Room result */
  function schedule() {
    clearTimeout(view.timer);
    view.timer = setTimeout(refresh, 120);
  }
  function refresh() {
    if (!st() || !document.getElementById("slRtCanvas")) return;
    post("/api/room_result").then(function (d) { view.last = d; followDial(); draw(); readout(); lockNote(); }).catch(function (e) { flash(String(e)); });
  }
  function dialS() { var s = st() || {}; var v = Number(s.decay_s); return isFinite(v) && v > 0.05 ? v : 1.8; }
  function followDial() { var t = document.getElementById("slAutoTmid"); if (t && !t.dataset.user) t.value = dialS().toFixed(2); }
  function lockNote() {
    var n = document.getElementById("slLockNote"), s = st() || {}, d = view.plan;
    if (!n) return;
    var tgt = d && Number(d.t_mid);
    if (s.decay_lock && tgt && Math.abs(tgt - dialS()) > 0.05 && rows().some(function (r) { return /^acc_/.test(r.id || ""); })) {
      n.textContent = "Decay lock is on, so the length stays at the dial (" + dialS().toFixed(2) + " s) and the treatment sets the shape. Set the dial to " + tgt.toFixed(2) + " s, or turn the lock off, to hear the " + tgt.toFixed(2) + " s room.";
      n.hidden = false;
    } else { n.textContent = ""; n.hidden = true; }
  }
  function readout() {
    var d = view.last, ro = document.getElementById("slReadout"); if (!d || !ro) return;
    var s = st() || {};
    var mid = d.f.map(function (f, i) { return f >= 500 && f <= 1000 ? d.T_faces_air[i] : null; }).filter(function (x) { return x != null; });
    var tm = mid.reduce(function (a, b) { return a + b; }, 0) / Math.max(mid.length, 1);
    ro.textContent = "T(500\u20131k) " + tm.toFixed(2) + " s" + (d.anchor_s ? " (dial)" : " (materials)") +
      " \u00b7 absolute " + d.T_absolute_mid.toFixed(2) + " s \u00b7 Schroeder " + Math.round(d.schroeder_hz) + " Hz \u00b7 EBU Tm " +
      d.ebu_tm.toFixed(2) + " s \u00b7 " + d.n_within_10pct + "/" + d.f.length + " within \u00b110 % \u00b7 mode " + ((s.decay_mode) || "flat");
  }
  function bandColour(f) { // red (low) to violet (high), as Figure 1 / the app palette order
    var t = Math.max(0, Math.min(1, Math.log(f / 40) / Math.log(10000 / 40)));
    return "hsl(" + Math.round(0 + t * 280) + ",80%,55%)";
  }
  function draw() {
    var cv = document.getElementById("slRtCanvas"), d = view.last; if (!cv || !d) return;
    var g = cv.getContext("2d"), W = cv.width, H = cv.height, l = 56, r = 12, t = 12, b = 30;
    var css = getComputedStyle(document.body);
    var ink = css.getPropertyValue("--text") || "#ddd", mut = css.getPropertyValue("--muted") || "#888";
    g.clearRect(0, 0, W, H);
    var f0 = 40, f1 = 10000;
    var ys = [].concat(d.T_faces_air, d.target, d.T_faces).filter(function (x) { return isFinite(x); });
    var ymax = Math.min(8, Math.max(1, Math.max.apply(null, ys) * 1.1));
    if (view.ebu) ymax = Math.max(ymax, d.ebu_tm + 0.4);
    var X = function (f) { return l + (W - l - r) * Math.log(f / f0) / Math.log(f1 / f0); };
    var Y = function (v) { return t + (H - t - b) * (1 - v / ymax); };
    g.font = "11px system-ui, sans-serif"; g.fillStyle = mut; g.strokeStyle = "rgba(128,128,128,.25)"; g.lineWidth = 1;
    [63, 125, 250, 500, 1000, 2000, 4000, 8000].forEach(function (f) { g.beginPath(); g.moveTo(X(f), t); g.lineTo(X(f), H - b); g.stroke(); g.fillText(f >= 1000 ? (f / 1000) + "k" : String(f), X(f) - 8, H - b + 14); });
    var step = ymax > 4 ? 1 : ymax > 2 ? 0.5 : 0.25;
    for (var v = 0; v <= ymax + 1e-9; v += step) { g.beginPath(); g.moveTo(l, Y(v)); g.lineTo(W - r, Y(v)); g.stroke(); g.fillText(v.toFixed(2), 22, Y(v) + 4); }
    g.save(); g.translate(12, H / 2 + 14); g.rotate(-Math.PI / 2); g.fillText("T (s)", 0, 0); g.restore();
    g.fillText("Hz", W - r - 16, H - 4);
    // Schroeder + axial modes
    g.strokeStyle = "rgba(250,180,60,.8)"; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(X(d.schroeder_hz), t); g.lineTo(X(d.schroeder_hz), H - b); g.stroke(); g.setLineDash([]);
    g.fillStyle = "rgba(250,180,60,.9)"; g.fillText("Schroeder", X(d.schroeder_hz) + 3, t + 10);
    (d.modes || []).forEach(function (m) { if (m.f >= f0) { g.fillRect(X(m.f) - 0.5, H - b - 6, 1.5, 6); } });
    // tolerance band around the target
    if (view.band) {
      g.fillStyle = "rgba(120,200,255,.13)"; g.beginPath();
      d.f.forEach(function (f, i) { var y = Y(d.target[i] * 1.1); if (i) g.lineTo(X(f), y); else g.moveTo(X(f), y); });
      for (var i = d.f.length - 1; i >= 0; i--) g.lineTo(X(d.f[i]), Y(d.target[i] * 0.9));
      g.closePath(); g.fill();
    }
    if (view.ebu) {
      g.strokeStyle = "rgba(160,255,160,.7)"; g.setLineDash([6, 3]);
      [d.ebu_tm - 0.05, d.ebu_tm + 0.05].forEach(function (v) { g.beginPath(); g.moveTo(X(200), Y(v)); g.lineTo(X(4000), Y(v)); g.stroke(); });
      g.setLineDash([]); g.fillStyle = "rgba(160,255,160,.9)"; g.fillText("EBU Tm \u00b1 0.05 s", X(220), Y(d.ebu_tm + 0.05) - 4);
    }
    function line(arr, colour, w, dash) {
      g.strokeStyle = colour; g.lineWidth = w; g.setLineDash(dash || []); g.beginPath();
      d.f.forEach(function (f, i) { var y = Y(Math.min(arr[i], ymax)); if (i) g.lineTo(X(f), y); else g.moveTo(X(f), y); });
      g.stroke(); g.setLineDash([]); g.lineWidth = 1;
    }
    line(d.target, "rgba(120,200,255,.95)", 1.5, [5, 4]);
    line(d.T_faces, "rgba(200,200,200,.55)", 1);
    line(d.T_faces_air, (ink || "#eee").trim() || "#eee", 2);
    d.f.forEach(function (f, i) { g.fillStyle = bandColour(f); g.beginPath(); g.arc(X(f), Y(Math.min(d.T_faces_air[i], ymax)), 2.6, 0, 7); g.fill(); });
    var rt = d.rendered_t20 || (st() && st().surf_rendered_t20);
    if (rt && rt.f && rt.t20) rt.f.forEach(function (f, i) { g.strokeStyle = bandColour(f); g.lineWidth = 2; g.beginPath(); g.arc(X(f), Y(rt.t20[i]), 5, 0, 7); g.stroke(); g.lineWidth = 1; });
    // legend
    var lx = W - r - 290, ly = t + 4;
    g.fillStyle = "rgba(0,0,0,.35)"; g.fillRect(lx - 6, ly - 2, 292, 44);
    g.fillStyle = (ink || "#eee").trim() || "#eee"; g.fillText("\u2014 faces + treatment + air (model)", lx, ly + 10);
    g.fillStyle = "rgba(200,200,200,.8)"; g.fillText("\u2014 faces only", lx, ly + 23);
    g.fillStyle = "rgba(120,200,255,.95)"; g.fillText("- - target (M\u00e4kivirta) \u00b7 shaded \u00b110 %", lx, ly + 36);
  }
  function flash(msg) {
    var ro = document.getElementById("slReadout"); if (!ro) return;
    if (msg) { ro.dataset.msg = msg; ro.textContent = msg; } else { delete ro.dataset.msg; readout(); }
  }

  /* ---------------------------------------------------------------- boot */
  function boot() {
    if (!build()) return false;
    schedule();
    return true;
  }
  window.SLRoomResult = { boot: boot, refresh: refresh, paintRows: paintRows, accept: accept, autoTreat: autoTreat, view: view };
  var tries = 0;
  (function wait() { if (st() && cs() && boot()) return; if (++tries < 100) setTimeout(wait, 100); })();
})();
