(function () {
  "use strict";

  /* Canonical stereo mic presets (space m, toe_half_deg = L/R from forward). */
  var MIC_PRESETS = {
    ab_omni: { space: 0.80, toe_half_deg: 0, car_omni: 0, polar: ["L", "R"],
      pattern_l: "omni", pattern_c: "omni", pattern_r: "omni",
      yaw_l_deg: 0, yaw_c_deg: 0, yaw_r_deg: 0 },
    ab_card: { space: 0.80, toe_half_deg: 5, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -5, yaw_c_deg: 0, yaw_r_deg: 5 },
    xy_90:   { space: 0.01, toe_half_deg: 45, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -45, yaw_c_deg: 0, yaw_r_deg: 45 },
    xy_120:  { space: 0.01, toe_half_deg: 60, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -60, yaw_c_deg: 0, yaw_r_deg: 60 },
    ortf:    { space: 0.17, toe_half_deg: 55, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -55, yaw_c_deg: 0, yaw_r_deg: 55 },
    nos:     { space: 0.30, toe_half_deg: 45, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -45, yaw_c_deg: 0, yaw_r_deg: 45 },
    din:     { space: 0.20, toe_half_deg: 45, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -45, yaw_c_deg: 0, yaw_r_deg: 45 },
    /* ASSUMED: Mid cardioid + inward side cardioids (no engine fig-8 decode) */
    ms:      { space: 0.05, toe_half_deg: 90, car_omni: 1, polar: ["L", "C", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -90, yaw_c_deg: 0, yaw_r_deg: 90 },
    /* ASSUMED: Mid cardioid + Side fig-8 */
    ms_classic: { space: 0.05, toe_half_deg: 90, car_omni: 1, polar: ["L", "C", "R"],
      pattern_l: "fig8", pattern_c: "cardioid", pattern_r: "fig8",
      yaw_l_deg: -90, yaw_c_deg: 0, yaw_r_deg: 90 },
    mono_c:  { space: 0.00, toe_half_deg: 0, car_omni: 1, polar: ["C"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: 0, yaw_c_deg: 0, yaw_r_deg: 0 },
    custom:  null
  };

  function divergFromToe(toeHalfDeg) {
    return Math.abs((Number(toeHalfDeg) * Math.PI) / 180) / 0.075;
  }

  var state = {
    W: 6, H: 3, L: 8,
    sx: 3, sz: 4.75, mcx: 3, mcz: 1.5, my: 1.5, sy: 1.5,
    link_heights: false,
    space: 0.17, diverg: 1, toe_half_deg: 55, car_omni: 1,
    pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
    yaw_l_deg: -55, yaw_c_deg: 0, yaw_r_deg: 55,
    mic_setup: "ortf",
    early_wet: 1, fdn_wet: 0.12, dry_gain: 0.1, fdn_g: 0.08, ir_length_ms: 400,
    reaktor_parity: false,
    path_on: false, path_preset: "still",
    ellipse_rate: 1, ellipse_rx: 0.42, ellipse_rz: 0.35,
    hadamard_n: 32,
    diffusion_seed: 0,
    lambda_ref: 0.02,
    surfaces: (window.ColourSurfacesDefaults && ColourSurfacesDefaults.defaultSurfaces)
      ? ColourSurfacesDefaults.defaultSurfaces()
      : null
  };
  var _applyingPreset = false;
  var wavFile = null;
  var currentView = "edit";
  var pathsMode = "paths"; /* paths | legs — Paths tab submode */
  var selectedMics = ["C"];
  var imagesCache = null;
  var imagesFetchTimer = null;

  var liveMetres = document.getElementById("liveMetres");
  var liveMetres3d = document.getElementById("liveMetres3d");
  var liveMetresImg = document.getElementById("liveMetresImg");
  var fileName = document.getElementById("fileName");
  var statusEl = document.getElementById("status");
  var outPathEl = document.getElementById("outPath");
  var previewAudio = document.getElementById("previewAudio");
  var renderBtn = document.getElementById("renderBtn");
  var editViews = document.getElementById("editViews");
  var micViews = document.getElementById("micViews");
  var liveMetresMic = document.getElementById("liveMetresMic");
  var imageViewsEl = document.getElementById("imageViews");
  var micToggles = document.getElementById("micToggles");
  var imageViewTitle = document.getElementById("imageViewTitle");
  var imageViewHint = document.getElementById("imageViewHint");

  var editor = RoomEditor.create({
    floorCanvas: document.getElementById("floorCanvas"),
    elevCanvas: document.getElementById("elevCanvas"),
    view3dCanvas: document.getElementById("view3dCanvas"),
    getState: function () { return state; },
    setState: function (s) { Object.assign(state, s); },
    onChange: syncUI
  });

  var imageView = null;
  var imageViewInitFailed = false;
  var syncRaf = 0;
  var imagesFetchDelayMs = 280; /* defer fetch while dragging (~drag-end) */

  function ensureImageView() {
    if (imageView || imageViewInitFailed) return imageView;
    if (!window.ImageViews) {
      imageViewInitFailed = true;
      if (statusEl) statusEl.textContent = "Images: ImageViews module missing";
      return null;
    }
    var canvas = document.getElementById("imageCanvas");
    if (!canvas) {
      imageViewInitFailed = true;
      if (statusEl) statusEl.textContent = "Images: #imageCanvas missing";
      return null;
    }
    /* Do not create WebGL while layout is still 0×0 (hidden/settling). */
    var rect = canvas.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) return null;
    try {
      imageView = ImageViews.create({ canvas: canvas });
      if (!imageView) {
        imageViewInitFailed = true;
        if (statusEl) statusEl.textContent = "Images: WebGL init failed (Three.js / GPU)";
        return null;
      }
    } catch (err) {
      imageViewInitFailed = true;
      imageView = null;
      if (statusEl) {
        statusEl.textContent = "Images WebGL: " + String(err && err.message ? err.message : err);
      }
      return null;
    }
    return imageView;
  }

  /** After #imageViews is unhidden: double-rAF → init → resize; optional size retry. */
  function paintImageViewsSoon() {
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        if (currentView !== "lattice" && currentView !== "paths") return;
        ensureImageView();
        if (imageView) {
          imageView.resize();
          if (imagesCache) applyImageView();
        }
        var canvas = document.getElementById("imageCanvas");
        if (!canvas) return;
        var rect = canvas.getBoundingClientRect();
        if (rect.width >= 2 && rect.height >= 2) return;
        /* Optional: layout still settling — one short retry */
        setTimeout(function () {
          if (currentView !== "lattice" && currentView !== "paths") return;
          ensureImageView();
          if (imageView) {
            imageView.resize();
            if (imagesCache) applyImageView();
          }
        }, 80);
      });
    });
  }

  var colourSurfacesViews = document.getElementById("colourSurfacesViews");
  var colourSurfaces = null;
  if (window.ColourSurfaces) {
    if (!state.surfaces) state.surfaces = ColourSurfacesDefaults.defaultSurfaces();
    colourSurfaces = new ColourSurfaces({
      getState: function () { return state; },
      onChange: function () { /* client state only until Render */ }
    });
  }

  var polarView = null;
  if (window.PolarFieldView) {
    polarView = new PolarFieldView({
      getState: function () { return state; }
    });
  }


  function fmt(n, d) {
    if (d === undefined) d = 2;
    return Number(n).toFixed(d);
  }

  function selectedMicsFromUI() {
    var boxes = document.querySelectorAll("#micToggles input[data-mic]");
    var out = [];
    boxes.forEach(function (b) {
      if (b.checked) out.push(b.getAttribute("data-mic"));
    });
    if (!out.length) {
      var c = document.querySelector('#micToggles input[data-mic="C"]');
      if (c) { c.checked = true; out = ["C"]; }
    }
    return out;
  }

  function scheduleImagesFetch(delayMs) {
    if (currentView !== "lattice" && currentView !== "paths") return;
    if (imagesFetchTimer) clearTimeout(imagesFetchTimer);
    var ms = delayMs == null ? imagesFetchDelayMs : delayMs;
    imagesFetchTimer = setTimeout(fetchImages, ms);
  }

  async function fetchImages() {
    selectedMics = selectedMicsFromUI();
    var body = Object.assign({}, state, { mics: selectedMics });
    try {
      var res = await fetch("/api/images", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      imagesCache = await res.json();
      ensureImageView();
      applyImageView();
      /* Layout may still settle after fetch — resize+apply again next frames */
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          if (currentView !== "lattice" && currentView !== "paths") return;
          if (imageView) {
            imageView.resize();
            applyImageView();
          }
        });
      });
      if (statusEl && (statusEl.textContent.indexOf("Images:") === 0 || statusEl.textContent.indexOf("Images WebGL:") === 0)) {
        statusEl.textContent = "";
      }
    } catch (err) {
      if (statusEl) statusEl.textContent = "Images: " + String(err && err.message ? err.message : err);
    }
  }

  function applyImageView() {
    if (!imagesCache) return;
    if (currentView !== "lattice" && currentView !== "paths") return;
    if (!imageView) ensureImageView();
    if (!imageView) return;
    var mode = currentView === "lattice" ? "lattice" : pathsMode;
    try {
      imageView.setMode(mode);
      imageView.setData(imagesCache);
    } catch (err) {
      if (statusEl) {
        statusEl.textContent = "Images rebuild: " + String(err && err.message ? err.message : err);
      }
      return;
    }
    var n = imagesCache.count || (imagesCache.lattice && imagesCache.lattice.length) || 0;
    var mics = (imagesCache.selected_mics || []).join("+") || "C";
    if (liveMetresImg) {
      var hn = imagesCache.hadamard_n || n;
      liveMetresImg.textContent =
        n + " images · " + hn + " FDN lines · mics " + mics +
        " · c=" + (imagesCache.c || 340) + " m/s";
    }
  }

  function syncPathsModeUI() {
    document.querySelectorAll(".paths-mode-chip").forEach(function (btn) {
      var on = btn.getAttribute("data-paths-mode") === pathsMode;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (pathsMode === "legs") {
      if (imageViewTitle) imageViewTitle.textContent = "Last legs into the mic";
      if (imageViewHint) imageViewHint.textContent =
        "Final arrival segment at the listener · where early energy comes from";
    } else {
      if (imageViewTitle) imageViewTitle.textContent = "In-room specular paths";
      if (imageViewHint) imageViewHint.textContent =
        "Folded bounce paths inside the real room · one polyline per image×mic";
    }
  }


  var micDesk = null;
  (function () {
    var top = document.getElementById("micFloorCanvas");
    var side = document.getElementById("micElevCanvas");
    var v3d = document.getElementById("mic3dCanvas");
    if (!top || !side || !window.MicDesk) return;
    micDesk = MicDesk.create({
      topCanvas: top,
      sideCanvas: side,
      view3dCanvas: v3d,
      polarL: document.getElementById("micPolarL"),
      polarC: document.getElementById("micPolarC"),
      polarR: document.getElementById("micPolarR"),
      getState: function () { return state; },
      setState: function (s) { Object.assign(state, s); },
      onChange: syncUI,
      RoomMath: window.RoomMath
    });
  })();



  /* Pattern+yaw IDs live in #capsuleStackListen; on Mic tab relocate under polar plots. */
  function placeCapsuleControls(view) {
    var stack = document.getElementById("capsuleStackListen");
    var yawHint = document.querySelector("#panelListen .yaw-hint");
    var map = { L: "micCapSlotL", C: "micCapSlotC", R: "micCapSlotR" };
    ["L", "C", "R"].forEach(function (cap) {
      var row = document.querySelector('.capsule-row[data-cap="' + cap + '"]');
      if (!row) return;
      var slot = document.getElementById(map[cap]);
      if (view === "mic" && slot) {
        if (row.parentElement !== slot) slot.appendChild(row);
      } else if (stack) {
        if (row.parentElement !== stack) stack.appendChild(row);
      }
    });
    if (stack) stack.hidden = view === "mic";
    if (yawHint) yawHint.hidden = view === "mic";
  }

  /* Sidebar relevance by view — same control may appear on several tabs if useful. */
  function syncSidebar(view) {
    var show = {
      room: true,
      listen: view === "mic" || view === "polar" || view === "lattice" || view === "paths",
      mix: view === "lattice" || view === "paths" || view === "colour" || view === "surfaces" || view === "polar",
      preview: view !== "mic",
      advanced: true
    };
    var map = {
      room: document.getElementById("panelRoom"),
      listen: document.getElementById("panelListen"),
      mix: document.getElementById("panelMix"),
      preview: document.getElementById("panelPreview"),
      advanced: document.getElementById("panelAdvanced")
    };
    Object.keys(map).forEach(function (key) {
      if (map[key]) map[key].hidden = !show[key];
    });
  }

  function setView(view) {
    currentView = view;

    document.querySelectorAll(".view-tab").forEach(function (tab) {
      var on = tab.getAttribute("data-view") === view;
      tab.classList.toggle("active", on);
      tab.setAttribute("aria-selected", on ? "true" : "false");
    });

    var isEdit = view === "edit";
    var isMic = view === "mic";
    var isImage = view === "lattice" || view === "paths";
    var isCS = view === "colour" || view === "surfaces" || view === "polar";
    if (editViews) editViews.hidden = !isEdit;
    if (micViews) micViews.hidden = !isMic;
    if (imageViewsEl) imageViewsEl.hidden = !isImage;
    if (colourSurfacesViews) colourSurfacesViews.hidden = !isCS;
    if (micToggles) micToggles.hidden = !isImage;

    /* Per-tab sidebar: only show controls relevant to the current view. */
    syncSidebar(view);
    placeCapsuleControls(view);

    var pathsModeRow = document.getElementById("pathsModeRow");
    if (pathsModeRow) pathsModeRow.hidden = view !== "paths";

    if (view === "lattice") {
      if (imageViewTitle) imageViewTitle.textContent = "Mirrored-room lattice";
      if (imageViewHint) imageViewHint.textContent =
        "Wireframe image rooms · home room gold · ± polarity colour · orbit Alt/RMB";
    } else if (view === "paths") {
      syncPathsModeUI();
    }

    if (isEdit) {
      editor.redraw();
    } else if (isMic) {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          if (currentView !== "mic") return;
          if (micDesk) {
            if (micDesk.view3d && micDesk.view3d.resize) micDesk.view3d.resize();
            micDesk.redraw();
          }
        });
      });
    } else if (isImage) {
      /* Lazy-init WebGL only after panel is unhidden (avoid 0×0 canvas context). */
      scheduleImagesFetch(80);
      paintImageViewsSoon();
    } else if (isCS && colourSurfaces) {
      colourSurfaces.setMode(view === "polar" ? "colour" : view);
      colourSurfaces.drawColour();
      colourSurfaces.drawSurfaceGraphs();
      if (view === "polar" && polarView) {
        polarView.resize();
        polarView.refresh();
      }
    }
  }

  function syncHadamardUI() {
    var n = state.hadamard_n || 32;
    document.querySelectorAll(".hadamard-chip").forEach(function (btn) {
      var bn = parseInt(btn.getAttribute("data-n"), 10);
      btn.classList.toggle("active", bn === n);
    });
    var ro = document.getElementById("hadamardReadout");
    if (ro) ro.textContent = n + " images · " + n + " FDN lines";
  }

  function setHadamardN(n) {
    var allowed = [8, 16, 32, 64, 128];
    if (allowed.indexOf(n) < 0) n = 32;
    state.hadamard_n = n;
    syncHadamardUI();
    if (currentView === "lattice" || currentView === "paths") scheduleImagesFetch(120);
  }

  function setPolarMics(ids) {
    var want = {};
    (ids || []).forEach(function (id) { want[id] = true; });
    document.querySelectorAll("#polarToggles input[data-polar]").forEach(function (box) {
      var id = box.getAttribute("data-polar");
      if (id === "sum") {
        box.checked = !ids || !ids.length;
        return;
      }
      box.checked = !!want[id];
    });
    // If L/C/R selected, uncheck sum; if none, keep sum
    var any = false;
    document.querySelectorAll("#polarToggles input[data-polar]").forEach(function (box) {
      var id = box.getAttribute("data-polar");
      if (id !== "sum" && box.checked) any = true;
    });
    var sumBox = document.querySelector("#polarToggles input[data-polar=\"sum\"]");
    if (sumBox) sumBox.checked = !any;
  }

  function near(a, b, eps) {
    return Math.abs(Number(a) - Number(b)) <= (eps != null ? eps : 0.02);
  }

  function matchPresetId() {
    var ids = Object.keys(MIC_PRESETS);
    for (var i = 0; i < ids.length; i++) {
      var id = ids[i];
      var p = MIC_PRESETS[id];
      if (!p) continue;
      if (
        near(state.space, p.space, 0.015) &&
        near(state.toe_half_deg, p.toe_half_deg, 0.6) &&
        near(state.car_omni, p.car_omni, 0.05)
      ) {
        return id;
      }
    }
    return "custom";
  }

  function applyMicPreset(id, fromUser) {
    if (id === "custom" || !MIC_PRESETS[id]) {
      state.mic_setup = "custom";
      var sel = document.getElementById("mic_setup");
      if (sel) sel.value = "custom";
      return;
    }
    var p = MIC_PRESETS[id];
    _applyingPreset = true;
    state.mic_setup = id;
    state.space = p.space;
    state.toe_half_deg = p.toe_half_deg;
    state.car_omni = p.car_omni;
    state.diverg = divergFromToe(p.toe_half_deg);
    if (p.pattern_l) state.pattern_l = p.pattern_l;
    if (p.pattern_c) state.pattern_c = p.pattern_c;
    if (p.pattern_r) state.pattern_r = p.pattern_r;
    if (p.yaw_l_deg != null) state.yaw_l_deg = p.yaw_l_deg;
    if (p.yaw_c_deg != null) state.yaw_c_deg = p.yaw_c_deg;
    if (p.yaw_r_deg != null) state.yaw_r_deg = p.yaw_r_deg;
    var divergEl = document.getElementById("diverg");
    if (divergEl) divergEl.value = String(state.diverg);
    setPolarMics(p.polar);
    Object.assign(state, RoomMath.clampRoom(state));
    syncUI();
    _applyingPreset = false;
    if (fromUser && polarView && currentView === "polar") {
      polarView.refresh();
    }
  }

  function markCustomIfDrifted() {
    if (_applyingPreset) return;
    var matched = matchPresetId();
    state.mic_setup = matched;
    var sel = document.getElementById("mic_setup");
    if (sel && sel.value !== matched) sel.value = matched;
  }

  function syncUI() {
    if (syncRaf) return;
    syncRaf = requestAnimationFrame(function () {
      syncRaf = 0;
      syncUINow();
    });
  }

  function syncUINow() {
    var geo = RoomMath.compute(state);
    Object.assign(state, geo.state);
    var spaceEl = document.getElementById("space");
    if (spaceEl) spaceEl.max = Math.max(0.01, geo.max_space);

    var numeric = ["W","H","L","space","car_omni","early_wet","fdn_wet","dry_gain","fdn_g","ir_length_ms"];
    for (var i = 0; i < numeric.length; i++) {
      var id = numeric[i];
      var el = document.getElementById(id);
      var out = document.getElementById(id + "_out");
      if (!el || !out) continue;
      el.value = state[id];
      if (id === "car_omni") {
        var v = state[id];
        out.textContent = v >= 0.66 ? "Cardioid" : (v <= 0.33 ? "Omni" : "Blend");
      } else if (id === "ir_length_ms") {
        out.textContent = String(Math.round(state[id]));
      } else {
        out.textContent = fmt(state[id], (id === "W" || id === "H" || id === "L") ? 1 : 2);
      }
    }
    var toeEl = document.getElementById("toe_half_deg");
    var toeOut = document.getElementById("toe_half_deg_out");
    if (toeEl && state.toe_half_deg != null) {
      toeEl.value = state.toe_half_deg;
      if (toeOut) toeOut.textContent = "±" + fmt(state.toe_half_deg, 1) + "°";
    }
    var divergEl = document.getElementById("diverg");
    if (divergEl) divergEl.value = state.diverg != null ? state.diverg : 1;
    var setupEl = document.getElementById("mic_setup");
    if (setupEl && state.mic_setup) setupEl.value = state.mic_setup;
    var parity = document.getElementById("reaktor_parity");
    if (parity) parity.checked = !!state.reaktor_parity;
    syncHadamardUI();
    var seedEl = document.getElementById("diffusion_seed");
    var seedMix = document.getElementById("diffusion_seed_mix");
    if (seedEl) seedEl.value = String(state.diffusion_seed != null ? state.diffusion_seed : 0);
    if (seedMix) seedMix.value = String(state.diffusion_seed != null ? state.diffusion_seed : 0);
    var lamEl = document.getElementById("lambda_ref");
    if (lamEl) lamEl.value = String(state.lambda_ref != null ? state.lambda_ref : 0.02);
    var linkEl = document.getElementById("link_heights");
    if (linkEl) linkEl.checked = !!state.link_heights;
    var linkElMic = document.getElementById("link_heights_mic");
    if (linkElMic) linkElMic.checked = !!state.link_heights;
    var readout =
      "Src " + fmt(state.sx) + "," + fmt(state.sz) +
      " @ " + fmt(state.sy != null ? state.sy : state.my) + " m  ·  Mic " +
      fmt(state.mcx) + "," + fmt(state.mcz) +
      " @ " + fmt(state.my) + " m  ·  |S−C| " + fmt(geo.distances.sc) + " m";
    if (liveMetres) liveMetres.textContent = readout;
    if (liveMetres3d) liveMetres3d.textContent = readout;

    (function () {
      function setM(id, val, digits) {
        var el = document.getElementById(id);
        var out = document.getElementById(id + "_out");
        if (el) el.value = val;
        if (out) {
          if (digits == null) digits = 2;
          out.textContent = Number(val).toFixed(digits);
        }
      }
      setM("mcx", state.mcx);
      setM("mcz", state.mcz);
      setM("my", state.my);
      setM("sy", state.sy != null ? state.sy : state.my);
      ["l", "c", "r"].forEach(function (cap) {
        var pat = document.getElementById("pattern_" + cap);
        var yaw = document.getElementById("yaw_" + cap + "_deg");
        var yawOut = document.getElementById("yaw_" + cap + "_deg_out");
        var keyP = "pattern_" + cap;
        var keyY = "yaw_" + cap + "_deg";
        if (pat && state[keyP]) pat.value = state[keyP];
        if (yaw && state[keyY] != null) yaw.value = state[keyY];
        if (yawOut && state[keyY] != null) {
          var n = Math.round(Number(state[keyY]));
          yawOut.textContent = (n > 0 ? "+" : n < 0 ? "−" : "") + (n < 0 ? Math.abs(n) : n) + "°";
          if (n === 0) yawOut.textContent = "0°";
          if (n < 0) yawOut.textContent = "−" + Math.abs(n) + "°";
          else if (n > 0) yawOut.textContent = "+" + n + "°";
          else yawOut.textContent = "0°";
        }
      });
      if (typeof liveMetresMic !== "undefined" && liveMetresMic) {
        liveMetresMic.textContent =
          "Src @" + fmt(state.sy != null ? state.sy : state.my) +
          " · Stand " + fmt(state.mcx) + "," + fmt(state.mcz) +
          " @ " + fmt(state.my) + " m · space " + fmt(state.space) + " m";
      }
      if (micDesk) micDesk.redraw();
    })();

    editor.redraw();
    if (currentView === "lattice" || currentView === "paths") scheduleImagesFetch();
  }

  function onRoomDim(key, val) {
    // Absolute metres stay put when room size changes (clamp only).
    state[key] = val;
    Object.assign(state, RoomMath.clampRoom(state));
    syncUI();
  }

  ["W","H","L"].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("input", function (e) {
      onRoomDim(id, parseFloat(e.target.value));
    });
  });
  ["space","car_omni","early_wet","fdn_wet","dry_gain","fdn_g","ir_length_ms"].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("input", function (e) {
      state[id] = parseFloat(e.target.value);
      Object.assign(state, RoomMath.clampRoom(state));
      if (id === "space" || id === "car_omni") markCustomIfDrifted();
      syncUI();
      if ((id === "space" || id === "car_omni") && polarView && currentView === "polar") {
        polarView.refresh();
      }
    });
  });
  var toeSlider = document.getElementById("toe_half_deg");
  if (toeSlider) {
    toeSlider.addEventListener("input", function (e) {
      state.toe_half_deg = parseFloat(e.target.value);
      state.diverg = divergFromToe(state.toe_half_deg);
      var divergEl = document.getElementById("diverg");
      if (divergEl) divergEl.value = String(state.diverg);
      Object.assign(state, RoomMath.clampRoom(state));
      markCustomIfDrifted();
      syncUI();
      if (polarView && currentView === "polar") polarView.refresh();
    });
  }
  var micSetupEl = document.getElementById("mic_setup");
  if (micSetupEl) {
    micSetupEl.addEventListener("change", function (e) {
      applyMicPreset(e.target.value, true);
    });
  }
  var parityEl = document.getElementById("reaktor_parity");
  if (parityEl) {
    parityEl.addEventListener("change", function (e) {
      state.reaktor_parity = e.target.checked;
      Object.assign(state, RoomMath.clampRoom(state));
      syncUI();
    });
  }

  function bindSeed(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("input", function (e) {
      var v = parseInt(e.target.value, 10);
      if (!isFinite(v)) v = 0;
      state.diffusion_seed = v;
      var a = document.getElementById("diffusion_seed");
      var b = document.getElementById("diffusion_seed_mix");
      if (a && a !== e.target) a.value = String(v);
      if (b && b !== e.target) b.value = String(v);
    });
  }
  bindSeed("diffusion_seed");
  bindSeed("diffusion_seed_mix");
  var lamEl = document.getElementById("lambda_ref");
  if (lamEl) {
    lamEl.addEventListener("input", function (e) {
      var v = parseFloat(e.target.value);
      if (!isFinite(v)) v = 0.02;
      state.lambda_ref = Math.max(0, Math.min(1, v));
    });
  }

  function bindLinkHeights(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("change", function (e) {
      state.link_heights = !!e.target.checked;
      var a = document.getElementById("link_heights");
      var b = document.getElementById("link_heights_mic");
      if (a && a !== e.target) a.checked = state.link_heights;
      if (b && b !== e.target) b.checked = state.link_heights;
      syncUI();
    });
  }
  bindLinkHeights("link_heights");
  bindLinkHeights("link_heights_mic");

  ["mcx", "mcz", "my", "sy"].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("input", function (e) {
      var v = parseFloat(e.target.value);
      if (!isFinite(v)) return;
      state[id] = v;
      if (id === "my" && state.link_heights) state.sy = v;
      if (id === "sy" && state.link_heights) state.my = v;
      if (window.RoomMath && RoomMath.clampRoom) Object.assign(state, RoomMath.clampRoom(state));
      markCustomIfDrifted();
      syncUI();
    });
  });

  ["l", "c", "r"].forEach(function (cap) {
    var pat = document.getElementById("pattern_" + cap);
    var yaw = document.getElementById("yaw_" + cap + "_deg");
    if (pat) {
      pat.addEventListener("change", function (e) {
        state["pattern_" + cap] = e.target.value;
        markCustomIfDrifted();
        syncUI();
        if (polarView && currentView === "polar") polarView.refresh();
      });
    }
    if (yaw) {
      yaw.addEventListener("input", function (e) {
        var v = parseFloat(e.target.value);
        if (!isFinite(v)) return;
        state["yaw_" + cap + "_deg"] = v;
        if (