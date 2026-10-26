/* Play, Render, toasts, and which tab is showing. */
"use strict";


function scheduleLiveRender() {
  if (!state.live_drag_render || !wavFile) return;
  if (renderTimer) clearTimeout(renderTimer);
  renderTimer = setTimeout(function () { doRender(); }, 420);
}

async function pushLiveParams() {
  if (liveBusy) {
    scheduleLiveParams();
    return;
  }
  liveBusy = true;
  try {
    var res = await fetch("/api/live_params", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(liveRequestBody())
    });
    noteHttp(res);
    var data = await res.json();
    toastWarnings(data);
    if (!data.ok) {
      if (statusEl) statusEl.textContent = data.error || "live_params failed";
      return;
    }
    if (data.mean_delay_ms) state._mean_delay_ms = data.mean_delay_ms;
    if (!state.decay_lock && !decayFromUser && data.decay_s > 0.05) {
      applyDecayReadout(data.decay_s);
    }
    if (LiveFDN.noteDecay) {
      LiveFDN.noteDecay(state.decay_lock ? state.decay_s : (data.decay_s || state.decay_s));
    }
    LiveFDN.update(data);
  } catch (err) {
    if (statusEl) statusEl.textContent = String(err);
  } finally {
    liveBusy = false;
  }
}



/* Sidebar: each tab shows only its own panels. Advanced stays on every tab. */
function syncSidebar(view) {
  var show = {
    room: view === "edit",
    listen: view === "mic" || view === "polar",
    mics: view === "mic",
    preview: view === "edit" || view === "mix" || view === "surfaces",
    advanced: true,
    hadamard: view === "space"
  };
  var map = {
    room: document.getElementById("panelRoom"),
    listen: document.getElementById("panelListen"),
    mics: document.getElementById("panelMics"),
    preview: document.getElementById("panelPreview"),
    advanced: document.getElementById("panelAdvanced"),
    hadamard: document.getElementById("panelHadamard")
  };
  Object.keys(map).forEach(function (key) {
    if (map[key]) map[key].hidden = !show[key];
  });
  var roomChip = document.getElementById("roomSizeChip");
  if (roomChip) roomChip.hidden = view === "edit";
}

function showEl(id, on) {
  var el = document.getElementById(id);
  if (el) el.hidden = !on;
}

function setView(view) {
  if (view === "lattice" || view === "paths") view = "space";
  if (view === "colour") view = "surfaces";
  currentView = view;

  document.querySelectorAll(".view-tab").forEach(function (tab) {
    var on = tab.getAttribute("data-view") === view;
    tab.classList.toggle("active", on);
    tab.setAttribute("aria-selected", on ? "true" : "false");
    tab.tabIndex = on ? 0 : -1;
  });

  var isEdit = view === "edit";
  var isMic = view === "mic";
  var isSource = view === "source";
  var isSpace = view === "space";
  var isSurfaces = view === "surfaces";
  var isPolar = view === "polar";
  if (editViews) editViews.hidden = !isEdit;
  if (sourceViews) sourceViews.hidden = !isSource;
  if (micViews) micViews.hidden = !isMic;
  if (mixViews) mixViews.hidden = view !== "mix";
  if (imageViewsEl) imageViewsEl.hidden = !isSpace;
  showEl("surfacesViews", isSurfaces);
  showEl("polarViews", isPolar);
  var layout = document.querySelector("main.layout");
  if (layout) {
    layout.classList.toggle("mic-wide", isMic);
    layout.classList.toggle("source-wide", isSource);
  }
  var stageWide = document.getElementById("stageWide");
  if (stageWide) stageWide.hidden = !isMic;
  if (micToggles) micToggles.hidden = !isSpace;

  syncSidebar(view);
  syncMicEach();
  syncPatternChrome();
  syncFeedbackRow();
  if (isSpace) syncSpaceModeUI();
  if (isPolar) syncPolarPageUI();
  else placePolarTrio();

  if (isEdit) {
    editor.redraw();
  } else if (isSource && sourceDesk) {
    requestAnimationFrame(function () {
      if (currentView !== "source") return;
      sourceDesk.redraw();
    });
  } else if (isMic || isPolar) {
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        if (currentView !== "mic" && currentView !== "polar") return;
        placePolarTrio();
        if (micDesk) {
          if (currentView === "mic" && micDesk.view3d && micDesk.view3d.resize) micDesk.view3d.resize();
          micDesk.redraw();
        }
        if (currentView === "polar" && polarPage === "combined" && polarView && polarView.resize) {
          polarView.resize();
        }
        if (currentView === "polar" && window.RRPolarViews && RRPolarViews.onRoom) RRPolarViews.onRoom(state);
        schedulePolar();
      });
    });
  } else if (isSpace) {
    scheduleImagesFetch(80);
    paintImageViewsSoon();
  } else if (isSurfaces && colourSurfaces) {
    colourSurfaces.setMode("surfaces");
    colourSurfaces.drawSurfaceGraphs();
    colourSurfaces.drawColour();
  }
}
function showToast(text) {
  var el = document.getElementById("toast");
  if (!el) return;
  el.textContent = text;
  el.hidden = false;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(function () { el.hidden = true; }, 2400);
}

function showBackendBanner() {
  var el = document.getElementById("backendBanner");
  if (!el) return;
  el.hidden = false;
  el.textContent = "backend files not found";
}

function noteHttp(res) {
  if (res && res.status === 500) showBackendBanner();
}

function toastWarnings(data) {
  var w = data && data.warnings;
  if (!w || !w.length) return;
  var keys = [];
  var i;
  for (i = 0; i < w.length && keys.length < 3; i++) keys.push(String(w[i]));
  showToast("Clamped: " + keys.join(", "));
}

function syncUI() {
  if (syncRaf) return;
  syncRaf = requestAnimationFrame(function () {
    syncRaf = 0;
    syncUINow();
  });
}

function syncUINow() {
  if (wavChannels < 2) state.two_sources = false;
  var geo = RoomMath.compute(state);
  Object.assign(state, geo.state);
  var spaceEl = document.getElementById("space");
  if (spaceEl) spaceEl.max = Math.max(0.01, geo.max_space);
  (function () {
    function setAxisMax(id, hi) {
      var el = document.getElementById(id);
      if (!el) return;
      var cap = Math.max(0.01, Number(hi) || 0);
      el.max = String(cap);
    }
    setAxisMax("mcx", state.W);
    setAxisMax("sx", state.W);
    setAxisMax("mcz", state.L);
    setAxisMax("sz", state.L);
    setAxisMax("my", state.H);
    setAxisMax("sy", state.H);
  })();

  var numeric = ["W","H","L","space","car_omni","fdn_g","ir_length_ms","humidity","air_shelf","decay_s"];
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
    } else if (id === "humidity") {
      paintHumidityReadout(el, out);
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
  if (!_applyingPreset) markCustomIfDrifted();
  var setupEl = document.getElementById("mic_setup");
  if (setupEl && state.mic_setup && document.activeElement !== setupEl) {
    setupEl.value = state.mic_setup;
  }
  var smoothEl = document.getElementById("smooth");
  if (smoothEl) smoothEl.checked = state.smooth === true;
  var movementEl = document.getElementById("movement");
  var movementOut = document.getElementById("movement_out");
  if (state.movement == null || !isFinite(Number(state.movement))) state.movement = 0;
  state.movement = Math.max(0, Math.min(100, Math.round(Number(state.movement))));
  if (movementEl && document.activeElement !== movementEl) movementEl.value = String(state.movement);
  if (movementOut) movementOut.textContent = state.movement <= 0 ? "Off" : (state.movement + "%");
  var climateEl = document.getElementById("air_climate");
  if (climateEl && document.activeElement !== climateEl) {
    climateEl.value = state.air_climate || "studio_20C_50RH";
  }
  var implEl = document.getElementById("colour_impl");
  if (implEl && document.activeElement !== implEl) implEl.value = state.colour_impl || "sos";
  var liveDrag = document.getElementById("live_drag_render");
  if (liveDrag) liveDrag.checked = !!state.live_drag_render;
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
    (geo.source_b ? "A " : "Src ") + fmt(state.sx) + "," + fmt(state.sz) +
    " @ " + fmt(state.sy != null ? state.sy : state.my) + " m  ·  Mic " +
    fmt(state.mcx) + "," + fmt(state.mcz) +
    " @ " + fmt(state.my) + " m  ·  |S−C| " + fmt(geo.distances.sc) + " m";
  if (geo.source_b) {
    readout += "  ·  B " + fmt(geo.source_b.x) + "," + fmt(geo.source_b.z) +
      " @ " + fmt(geo.source_b.y) + " m";
  }
  if (liveMetres) liveMetres.textContent = readout;
  if (liveMetres3d) liveMetres3d.textContent = readout;
  var roomChip = document.getElementById("roomSizeChip");
  if (roomChip) {
    roomChip.textContent = fmt(state.W, 1) + " x " + fmt(state.L, 1) + " x " + fmt(state.H, 1) + " m";
  }

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
      var fam = document.getElementById("family_" + cap);
      var pol = document.getElementById("polar_" + cap);
      var polOut = document.getElementById("polar_" + cap + "_out");
      var keyF = "family_" + cap;
      var keyP = "polar_" + cap;
      if (fam && state[keyF]) fam.value = state[keyF];
      if (pol && state[keyP] != null) pol.value = state[keyP];
      if (polOut) {
        polOut.textContent = (window.RoomMath && RoomMath.polarLabel)
          ? RoomMath.polarLabel(state[keyF], state[keyP], state["pattern_" + cap])
          : Number(state[keyP] || 0).toFixed(2);
      }
      if (fam) fam.disabled = state.mic_setup === "binaural";
      if (pol) pol.disabled = state.mic_setup === "binaural" || state[keyF] === "bi";
      if (window.RoomMath && RoomMath.derivePattern) {
        state["pattern_" + cap] = RoomMath.derivePattern(state[keyF], state[keyP], state["pattern_" + cap]);
      }
    });
    var ah = document.getElementById("align_horizontal");
    if (ah) ah.checked = !!state.align_horizontal;
    var lr = document.getElementById("link_lr_yaw");
    if (lr) lr.checked = state.link_lr_yaw !== false;
    var hpOn = document.getElementById("mic_hp_on");
    if (hpOn) hpOn.checked = !!state.mic_hp_on;
    setM("mic_hp_hz", state.mic_hp_hz, 0);
    setM("mic_response_hz", state.mic_response_hz, 0);
    setM("capsule_mm", state.capsule_mm != null ? state.capsule_mm : 17, 1);
    if (typeof liveMetresMic !== "undefined" && liveMetresMic) {
      liveMetresMic.textContent = RRViewPose.metresMic(state, roomSpotOf(state, "c"));
    }
    if (micDesk) micDesk.redraw();
  })();

  paintSourceSplit();
  editor.redraw();
  if (sourceDesk && currentView === "source") sourceDesk.redraw();
  if (currentView === "space") scheduleImagesFetch();
  paintMicModel();
  paintSolos();
  paintDesk();
  paintRoomReads(geo);
  paintDecayHint();
  syncBinauralChrome();
  syncPatternChrome();
  syncMicEach();
  syncFeedbackRow();
  paintPolarBanner();
  scheduleLiveParams();
  scheduleDecayPreview();
  schedulePolar();
  if (window.RRControls) window.RRControls.refreshAll();
  if (micDesk) micDesk.redraw();
  window.RRState = state;
  window.RRColourSurfaces = colourSurfaces;
  if (window.SLRoomResult && typeof SLRoomResult.refresh === "function") {
    clearTimeout(slRoomRefreshTimer);
    slRoomRefreshTimer = setTimeout(function () {
      if (window.SLRoomResult && typeof SLRoomResult.refresh === "function") SLRoomResult.refresh();
    }, 120);
  }
  paintPlaceChips();
  paintRoomShape();
  paintMicSetupLink();
  scheduleSetupSave();
  if (window.RRPolarViews && RRPolarViews.onRoom) RRPolarViews.onRoom(state);
}

async function doRender() {
  if (!wavFile) {
    if (statusEl) statusEl.textContent = "Load an input WAV first.";
    return;
  }
  if (renderBusy) {
    if (statusEl) statusEl.textContent = "render busy";
    return;
  }
  renderBusy = true;
  if (renderBtn) renderBtn.disabled = true;
  var t60 = Number(state.decay_s);
  if (!isFinite(t60) || t60 < 0) t60 = 0;
  var irMin = Number(state.ir_length_ms);
  if (!isFinite(irMin)) irMin = 1500;
  var earlyMs = Math.min(90, irMin);
  var fdnMs = Math.min(12500, Math.max(irMin, earlyMs, earlyMs + 1500 * t60));
  if (statusEl) statusEl.textContent = "Rendering… FDN " + (fdnMs / 1000).toFixed(2) + " s";
  var fd = new FormData();
  fd.append("file", wavFile, wavFile.name);
  var mix = heardMix(state);
  if (state.room_shape) mix.room_shape = String(state.room_shape);
  mix.mirror_lr = !!state.mirror_lr;
  if (window.RRRouting && RRRouting.renderScene) Object.assign(mix, RRRouting.renderScene(state));
  fd.append("params_json", JSON.stringify(mix));
  try {
    var res = await fetch("/api/render", { method: "POST", body: fd });
    noteHttp(res);
    var raw = await res.text();
    var data;
    try {
      data = JSON.parse(raw);
    } catch (parseErr) {
      if (statusEl) {
        statusEl.textContent = "Render server error (HTTP " + res.status + "): " +
          raw.replace(/\s+/g, " ").slice(0, 240);
      }
      return;
    }
    toastWarnings(data);
    if (!data.ok) {
      if (statusEl) statusEl.textContent = data.error || ("Render failed (HTTP " + res.status + ")");
      return;
    }
    if (statusEl) statusEl.textContent = data.status || "Done";
    if (outPathEl) outPathEl.textContent = data.out_path || "";
    if (previewAudio) {
      previewAudio.src = (data.preview_url || "") + "&t=" + Date.now();
      previewAudio.play().catch(function () {});
    }
    if (data.geometry && data.geometry.params) {
      Object.assign(state, data.geometry.params);
      syncUI();
    }
    if (data.colour && colourSurfaces) {
      colourSurfaces.setColour(data.colour);
      colourSurfaces.drawColour();
    }
    if (currentView === "polar" || currentView === "mic") schedulePolar();
  } catch (err) {
    if (statusEl) statusEl.textContent = String(err);
  } finally {
    renderBusy = false;
    if (renderBtn) renderBtn.disabled = false;
  }
}