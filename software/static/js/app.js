/* Wires the controls after the area scripts. */
"use strict";

/* Canonical stereo mic presets (space m, toe_half_deg = L/R from forward). */
var MIC_PRESETS = {
  ab_omni: { space: 0.80, toe_half_deg: 0, car_omni: 0, polar: ["L", "R"],
    pattern_l: "omni", pattern_c: "omni", pattern_r: "omni",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0, polar_c: 0, polar_r: 0,
    yaw_l_deg: 0, yaw_c_deg: 0, yaw_r_deg: 0 },
  ab_card: { space: 0.80, toe_half_deg: 5, car_omni: 1, polar: ["L", "R"],
    pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0.5, polar_c: 0.5, polar_r: 0.5,
    yaw_l_deg: -5, yaw_c_deg: 0, yaw_r_deg: 5 },
  xy_90:   { space: 0.01, toe_half_deg: 45, car_omni: 1, polar: ["L", "R"],
    pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0.5, polar_c: 0.5, polar_r: 0.5,
    yaw_l_deg: -45, yaw_c_deg: 0, yaw_r_deg: 45 },
  xy_120:  { space: 0.01, toe_half_deg: 60, car_omni: 1, polar: ["L", "R"],
    pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0.5, polar_c: 0.5, polar_r: 0.5,
    yaw_l_deg: -60, yaw_c_deg: 0, yaw_r_deg: 60 },
  ortf:    { space: 0.17, toe_half_deg: 55, car_omni: 1, polar: ["L", "R"],
    pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0.5, polar_c: 0.5, polar_r: 0.5,
    yaw_l_deg: -55, yaw_c_deg: 0, yaw_r_deg: 55 },
  /* D20. Same pair as ortf. loadDeskPreset turns the centre mic on. */
  ortf_c:  { space: 0.17, toe_half_deg: 55, car_omni: 1, polar: ["L", "R"],
    pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0.5, polar_c: 0.5, polar_r: 0.5,
    yaw_l_deg: -55, yaw_c_deg: 0, yaw_r_deg: 55 },
  nos:     { space: 0.30, toe_half_deg: 45, car_omni: 1, polar: ["L", "R"],
    pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0.5, polar_c: 0.5, polar_r: 0.5,
    yaw_l_deg: -45, yaw_c_deg: 0, yaw_r_deg: 45 },
  din:     { space: 0.20, toe_half_deg: 45, car_omni: 1, polar: ["L", "R"],
    pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0.5, polar_c: 0.5, polar_r: 0.5,
    yaw_l_deg: -45, yaw_c_deg: 0, yaw_r_deg: 45 },
  ms:      { space: 0.05, toe_half_deg: 90, car_omni: 1, polar: ["L", "C", "R"],
    pattern_l: "cardioid", pattern_c: "omni", pattern_r: "cardioid",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0.5, polar_c: 0, polar_r: 0.5,
    yaw_l_deg: -90, yaw_c_deg: 0, yaw_r_deg: 90 },
  /* D-UI29. Geometry comes from ms_presets.js. ms_classic is ms_b so old scenes recall. */
  ms_a: rrMsMic("ms_a"),
  ms_b: rrMsMic("ms_b"),
  ms_c: rrMsMic("ms_c"),
  ms_classic: rrMsMic("ms_b"),
  /* Two heard mics. Same desk as ms_b. The Right strip is muted and shown off. */
  ms_2: rrMsMic("ms_2"),
  mono_c:  { space: 0.00, toe_half_deg: 0, car_omni: 1, polar: ["C"],
    pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0.5, polar_c: 0.5, polar_r: 0.5,
    yaw_l_deg: 0, yaw_c_deg: 0, yaw_r_deg: 0 },
  /* Display spacing for KU100. The server uses the preset's ear_spacing_m. */
  binaural: { space: 0.18, toe_half_deg: 90, car_omni: 0, polar: ["L", "R"],
    pattern_l: "omni", pattern_c: "omni", pattern_r: "omni",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0, polar_c: 0, polar_r: 0,
    yaw_l_deg: -90, yaw_c_deg: 0, yaw_r_deg: 90 },
  custom:  null
}; /* 2011 / Hall snapshot loaded. Not posted. */
/* Developer only. ?dev=1 or window.RR_DEV shows the snapshot and the colour filter. */
(function () {
  var on = false;
  try {
    on = window.RR_DEV === true || /(?:^|[?&])dev=1(?:&|$)/.test(String(location.search || ""));
  } catch (e) { on = false; }
  if (!on) return;
  var impl = document.getElementById("colourImplRow");
  var snap = document.getElementById("reaktorSnapshotBtn");
  var hint = document.getElementById("reaktorSnapshotHint");
  if (impl) impl.hidden = false;
  if (snap) snap.hidden = false;
  if (hint) hint.hidden = false;
})();
window.RRPaintDecay = paintDecayControls;
window.RRNoteDecayUser = function (on) { decayFromUser = !!on; };
window.RRPushLive = scheduleLiveParams;
if (window.ColourSurfaces) {
  if (!state.surfaces) state.surfaces = ColourSurfacesDefaults.defaultSurfaces();
  colourSurfaces = new ColourSurfaces({
    getState: function () { return state; },
    onChange: function () { syncUI(); scheduleLiveParams(); }
  });
}
if (window.PolarFieldView) {
  polarView = new PolarFieldView({
    getState: function () { return state; },
    onRefresh: function () { schedulePolar(); }
  });
}
(function () {
  var top = document.getElementById("micFloorCanvas");
  var v3d = document.getElementById("mic3dCanvas");
  if (!top || !window.MicDesk) return;
  micDesk = MicDesk.create({
    topCanvas: top,
    sideCanvas: null,
    view3dCanvas: v3d,
    polarL: document.getElementById("micPolarL"),
    polarC: document.getElementById("micPolarC"),
    polarR: document.getElementById("micPolarR"),
    getState: function () { return state; },
    setState: function (s) { Object.assign(state, s); },
    onChange: function () { syncUI(); scheduleLiveParams(); },
    onPolar: function (cap, value) { writePolar(cap, value); },
    RoomMath: window.RoomMath
  });
  window.micDesk = micDesk;
})();

(function () {
  var host = document.querySelector("main.layout");
  if (!host || typeof ResizeObserver === "undefined") return;
  var pending = 0;
  var ro = new ResizeObserver(function () {
    if (currentView !== "mic") return;
    if (pending) return;
    pending = requestAnimationFrame(function () {
      pending = 0;
      if (currentView !== "mic") return;
      if (micDesk && micDesk.redraw) micDesk.redraw();
      if (micDesk && micDesk.view3d && micDesk.view3d.resize) micDesk.view3d.resize();
    });
  });
  ro.observe(host);
  var grid = document.querySelector(".mic-desk-grid");
  if (grid) ro.observe(grid);
  var wide = document.getElementById("stageWide");
  if (wide) ro.observe(wide);
})();

if (!window.__rrFetchWrapped) {
  window.__rrFetchWrapped = true;
  var rrFetch = window.fetch;
  window.fetch = function (input) {
    var watched = input;
    return rrFetch.apply(this, arguments).then(function (res) {
      try {
        var u = typeof watched === "string" ? watched : (watched && watched.url) || "";
        if (res && res.status === 500 && String(u).indexOf("/api/") !== -1) showBackendBanner();
      } catch (e) {}
      return res;
    });
  };
}
if (polarLinkBtn) {
  polarLinkBtn.addEventListener("click", function () { setView("polar"); });
}

["W","H","L"].forEach(function (id) {
  var el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("input", function (e) {
    onRoomDim(id, parseFloat(e.target.value));
  });
});
if (climatePick) {
  climatePick.addEventListener("change", function (e) {
    state.air_climate = e.target.value || "studio_20C_50RH";
    syncUI();
  });
}
["space","car_omni","fdn_g","ir_length_ms","humidity","air_shelf"].forEach(function (id) {
  var el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("input", function (e) {
    state[id] = parseFloat(e.target.value);
    Object.assign(state, RoomMath.clampRoom(state));
    if (id === "space" || id === "car_omni") markCustomIfDrifted();
    if (id === "fdn_g") { decayFromUser = false; state.decay_lock = false; }
    syncUI();
  });
});
if (decayEl) {
  decayEl.addEventListener("input", function (e) {
    if (state.treat_sets_decay && state.decay_mode === "surfaces") {
      decayFromUser = false;
      state.decay_lock = false;
      syncUI();
      return;
    }
    decayFromUser = true;
    state.decay_lock = true;
    state.decay_s = parseFloat(e.target.value);
    Object.assign(state, RoomMath.clampRoom(state));
    syncUI();
  });
}
document.querySelectorAll(".solo-btn").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var bus = btn.getAttribute("data-solo");
    var i;
    if (bus === "l" || bus === "c" || bus === "r") {
      if (monoStripLocked(bus)) return;
      state["solo_" + bus] = !state["solo_" + bus];
      state.desk_touched = true;
      syncUI();
      return;
    }
    for (i = 0; i < SOLO_BUSES.length; i++) {
      if (SOLO_BUSES[i][2] === bus) state[SOLO_BUSES[i][0]] = !state[SOLO_BUSES[i][0]];
    }
    syncUI();
  });
});
if (toeSlider) {
  toeSlider.addEventListener("input", function (e) {
    state.toe_half_deg = parseFloat(e.target.value);
    state.diverg = divergFromToe(state.toe_half_deg);
    var divergEl = document.getElementById("diverg");
    if (divergEl) divergEl.value = String(state.diverg);
    Object.assign(state, RoomMath.clampRoom(state));
    markCustomIfDrifted();
    syncUI();
  });
}
if (micSetupEl) {
  micSetupEl.addEventListener("change", function (e) {
    applyMicPreset(e.target.value, true);
  });
}
if (headYawEl) {
  headYawEl.addEventListener("input", function (e) {
    var v = parseFloat(e.target.value);
    if (!isFinite(v)) v = 0;
    state.head_yaw_deg = Math.max(-180, Math.min(180, v));
    syncUI();
  });
}
if (headPresetEl) {
  headPresetEl.addEventListener("change", function (e) {
    var id = e.target.value;
    if (!BINAURAL_SPACE_M[id]) id = "SADIE2_KU100";
    state.binaural_preset = id;
    if (state.mic_setup === "binaural") state.space = binauralEarSpace(id);
    syncUI();
  });
}
if (implSel) {
  implSel.addEventListener("change", function (e) {
    state.colour_impl = e.target.value === "fir" ? "fir" : "sos";
    scheduleLiveParams();
  });
}
bindSeed("diffusion_seed");
bindSeed("diffusion_seed_mix");
if (lamEl) {
  lamEl.addEventListener("input", function (e) {
    var v = parseFloat(e.target.value);
    if (!isFinite(v)) v = 0.02;
    state.lambda_ref = Math.max(0, Math.min(1, v));
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
    if (id === "my") {
      state.my_l = v;
      state.my_c = v;
      state.my_r = v;
    }
    if (id === "my" && state.link_heights) state.sy = v;
    if (id === "sy" && state.link_heights) state.my = v;
    if (window.RoomMath && RoomMath.clampRoom) Object.assign(state, RoomMath.clampRoom(state));
    syncUI();
  });
});

["l", "c", "r"].forEach(function (cap) {
  var fam = document.getElementById("family_" + cap);
  var pol = document.getElementById("polar_" + cap);
  if (fam) {
    fam.addEventListener("change", function (e) {
      writeFamily(cap, e.target.value);
    });
  }
  if (pol) {
    pol.addEventListener("input", function (e) {
      var v = parseFloat(e.target.value);
      if (!isFinite(v)) return;
      writePolar(cap, v);
    });
  }
});
if (familySide) {
  familySide.addEventListener("change", function (e) {
    writeFamily("side", e.target.value);
  });
}
if (polarSide) {
  polarSide.addEventListener("input", function (e) {
    var v = parseFloat(e.target.value);
    if (!isFinite(v)) return;
    writePolar("side", v);
  });
}
if (sideSplitEl) {
  sideSplitEl.addEventListener("change", function (e) {
    if (msSetup()) {
      e.target.checked = false;
      sideSplitUser = false;
      syncUI();
      return;
    }
    if (e.target.checked) {
      sideSplitUser = true;
    } else {
      state.family_r = state.family_l;
      state.polar_r = state.polar_l;
      state.pattern_r = state.pattern_l;
      state.mic_preset_r = state.mic_preset_l;
      sideSplitUser = false;
      showToast("Right now matches Left");
    }
    syncUI();
  });
}
bindCheck("align_horizontal", "align_horizontal");
bindCheck("link_lr_yaw", "link_lr_yaw");
bindCheck("mic_hp_on", "mic_hp_on");
if (sidePreset) {
  sidePreset.addEventListener("change", function (e) {
    applyCapsulePreset(["l", "r"], e.target.value);
  });
}
if (centrePreset) {
  centrePreset.addEventListener("change", function (e) {
    applyCapsulePreset(["c"], e.target.value);
  });
}
if (presetL) {
  presetL.addEventListener("change", function (e) {
    applyCapsulePreset(["l"], e.target.value);
  });
}
if (presetR) {
  presetR.addEventListener("change", function (e) {
    applyCapsulePreset(["r"], e.target.value);
  });
}
document.querySelectorAll(".diagram-expand").forEach(function (btn) {
  btn.addEventListener("click", function (evt) {
    evt.preventDefault();
    evt.stopPropagation();
    var frame = btn.closest(".diagram-frame");
    if (!frame) return;
    var open = document.querySelector(".diagram-frame.is-enlarged");
    if (open && open !== frame) {
      open.classList.remove("is-enlarged");
      var other = open.querySelector(".diagram-expand");
      if (other) {
        other.textContent = "Enlarge";
        other.setAttribute("aria-pressed", "false");
      }
    }
    var on = frame.classList.toggle("is-enlarged");
    btn.textContent = on ? "Close" : "Enlarge";
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    refitDiagrams();
  });
});
document.addEventListener("keydown", function (evt) {
  if (evt.key !== "Escape") return;
  var open = document.querySelector(".diagram-frame.is-enlarged");
  if (!open) return;
  open.classList.remove("is-enlarged");
  var btn = open.querySelector(".diagram-expand");
  if (btn) {
    btn.textContent = "Enlarge";
    btn.setAttribute("aria-pressed", "false");
  }
  refitDiagrams();
});
if (modeSel) {
  modeSel.addEventListener("change", function (e) {
    state.colour_mode = e.target.value || "MEASURED_SHELF";
    if (patternFromPreset(state.colour_mode)) applyPresetLaw();
    syncUI();
  });
}
bindHpf("mic_hpf_sides", "mic_hpf_sides");
bindHpf("mic_hpf_centre", "mic_hpf_centre");
bindHpf("mic_hpf_r", "mic_hpf_r");
bindProx("prox_l", "prox_l");
bindProx("prox_c", "prox_c");
bindProx("prox_r", "prox_r");
["mic_hp_hz", "mic_response_hz", "capsule_mm"].forEach(function (id) {
  var el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("input", function (e) {
    var v = parseFloat(e.target.value);
    if (!isFinite(v)) return;
    state[id] = v;
    syncUI();
  });
});
if (spaceZoomOut) spaceZoomOut.addEventListener("click", function () {
  withImageView(function (v) { v.zoom(-1); });
});
if (spaceZoomIn) spaceZoomIn.addEventListener("click", function () {
  withImageView(function (v) { v.zoom(1); });
});
if (spaceFit) spaceFit.addEventListener("click", function () {
  withImageView(function (v) { v.resetCamera(); });
});

document.querySelectorAll(".space-mode-chip").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var m = btn.getAttribute("data-space-mode");
    spaceMode = (m === "legs" || m === "paths") ? m : "lattice";
    syncSpaceModeUI();
    if (currentView === "space") {
      if (imagesCache) applyImageView();
      else scheduleImagesFetch(80);
    }
  });
});
document.querySelectorAll("[data-polar-page]").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var m = btn.getAttribute("data-polar-page");
    polarPage = (m === "each" || m === "speakers") ? m : "combined";
    if (currentView !== "polar") setView("polar");
    syncPolarPageUI();
    requestAnimationFrame(function () {
      if (polarPage === "combined" && polarView && polarView.resize) polarView.resize();
      if (polarPage === "speakers") drawSpeakerPolar(polarCache);
      if (micDesk) micDesk.redraw();
      schedulePolar();
    });
  });
});

document.querySelectorAll(".view-tab").forEach(function (tab) {
  tab.addEventListener("click", function () {
    setView(tab.getAttribute("data-view"));
  });
});
if (viewSwitch) {
  viewSwitch.addEventListener("keydown", function (evt) {
    var key = evt.key;
    if (key !== "ArrowRight" && key !== "ArrowLeft" && key !== "ArrowDown" && key !== "ArrowUp" && key !== "Home" && key !== "End") return;
    var tabs = Array.prototype.slice.call(document.querySelectorAll(".view-tab"));
    if (!tabs.length) return;
    var i, ix = 0;
    for (i = 0; i < tabs.length; i++) {
      if (tabs[i].getAttribute("data-view") === currentView) ix = i;
    }
    if (key === "ArrowRight" || key === "ArrowDown") ix = (ix + 1) % tabs.length;
    else if (key === "ArrowLeft" || key === "ArrowUp") ix = (ix - 1 + tabs.length) % tabs.length;
    else if (key === "Home") ix = 0;
    else ix = tabs.length - 1;
    evt.preventDefault();
    setView(tabs[ix].getAttribute("data-view"));
    tabs[ix].focus();
  });
}
if (roomSizeChip) {
  roomSizeChip.addEventListener("click", function () {
    setView("edit");
  });
}

document.querySelectorAll("#micToggles input[data-mic]").forEach(function (box) {
  box.addEventListener("change", function () {
    selectedMics = selectedMicsFromUI();
    scheduleImagesFetch(120);
  });
});
if (micAll) {
  micAll.addEventListener("click", function () {
    applyImageMicTicks();
    scheduleImagesFetch(120);
  });
}


document.querySelectorAll(".hadamard-chip").forEach(function (btn) {
  btn.addEventListener("click", function () {
    setHadamardN(parseInt(btn.getAttribute("data-n"), 10));
  });
});
if (wavInput) {
  wavInput.addEventListener("change", function (e) {
    wavFile = (e.target.files && e.target.files[0]) || null;
    wavChannels = 0;
    if (fileName) fileName.textContent = wavFile ? wavFile.name : "No file loaded";
    if (!wavFile) {
      state.two_sources = false;
      syncUI();
      return;
    }
    wavChannelCount(wavFile).then(function (nch) {
      if (wavFile !== (e.target.files && e.target.files[0])) return;
      wavChannels = nch >= 2 ? nch : 1;
      if (wavChannels < 2) state.two_sources = false;
      syncUI();
    }).catch(function () {
      wavChannels = 1;
      state.two_sources = false;
      syncUI();
    });
  });
}
if (oneSourceBtn) {
  oneSourceBtn.addEventListener("click", function () {
    state.two_sources = false;
    syncUI();
  });
}
if (twoSourceBtn) {
  twoSourceBtn.addEventListener("click", function () {
    if (wavChannels < 2) return;
    state.two_sources = true;
    Object.assign(state, RoomMath.clampRoom(state));
    syncUI();
  });
}
if (mirrorB) {
  mirrorB.addEventListener("change", function (e) {
    state.mirror_b = !!e.target.checked;
    Object.assign(state, RoomMath.clampRoom(state));
    syncUI();
  });
}
if (sourceBalance) {
  sourceBalance.addEventListener("input", function (e) {
    var v = parseFloat(e.target.value);
    if (!isFinite(v)) v = 0;
    if (Math.abs(v) < 0.04) v = 0;
    state.source_balance = Math.max(-1, Math.min(1, v));
    e.target.value = String(state.source_balance);
    var balOut = document.getElementById("sourceBalanceOut");
    if (balOut) balOut.textContent = balanceLabel(state.source_balance);
    scheduleLiveParams();
  });
}

if (renderBtn) {
  renderBtn.addEventListener("click", function () { doRender(); });
}
if (snapBtn) {
  snapBtn.addEventListener("click", function () { applyReaktorSnapshot(); });
}
bindCheck("live_drag_render", "live_drag_render");
bindCheck("shared_tail", "shared_tail");
bindCheck("smooth", "smooth");
bindCheck("phys_ceiling", "phys_ceiling");
bindCheck("sub_hp", "sub_hp");
bindCheck("offaxis_tail", "offaxis_tail");
if (movementSlider) {
  movementSlider.addEventListener("input", function (e) {
    var v = Math.round(Number(e.target.value));
    if (!isFinite(v)) v = 0;
    if (v < 0) v = 0;
    if (v > 100) v = 100;
    state.movement = v;
    var out = document.getElementById("movement_out");
    if (out) out.textContent = v <= 0 ? "Off" : (v + "%");
    scheduleLiveParams();
  });
}
paintRoomShape._shown = "box";
if (mirrorLr) {
  mirrorLr.addEventListener("change", function (e) {
    state.mirror_lr = !!e.target.checked;
    if (colourSurfaces && colourSurfaces.syncWallList) colourSurfaces.syncWallList();
    syncUI();
    scheduleLiveParams();
  });
}

if (window.RoomShape && RoomShape.bindShapeRows) {
  RoomShape.bindShapeRows(roomShapeRows(), applyRoomShape);
}

document.querySelectorAll("#placeRow [data-place]").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var name = btn.getAttribute("data-place");
    var label = name ? name.charAt(0).toUpperCase() + name.slice(1) : "place";
    if (!window.confirm("Load " + label + "? This resets mics, mix and surfaces.")) return;
    applyPlace(name);
  });
});
if (liveBtn) {
  liveBtn.addEventListener("click", async function () {
    if (window.LiveFDN && LiveFDN.isRunning()) {
      if (LiveFDN.noteDecay) LiveFDN.noteDecay(state.decay_s);
      LiveFDN.stop();
      liveBtn.classList.remove("live-on");
      liveBtn.textContent = "Play live";
      syncHadamardUI();
      if (currentView === "space") applyImageView();
      if (statusEl) statusEl.textContent = "Live FDN stopped.";
      return;
    }
    if (!wavFile) {
      if (statusEl) statusEl.textContent = "Load a WAV, then Play live.";
      return;
    }
    liveBtn.disabled = true;
    if (statusEl) statusEl.textContent = "Starting live FDN…";
    try {
      if (window.LiveFDN && LiveFDN.prepare) await LiveFDN.prepare();
      var res = await fetch("/api/params/live", {
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
      if (previewAudio) {
        try { previewAudio.pause(); } catch (e) {}
      }
      var ok = await LiveFDN.start(wavFile, data);
      if (ok) {
        liveBtn.classList.add("live-on");
        liveBtn.textContent = "Stop live";
        syncHadamardUI();
        if (currentView === "space") applyImageView();
      }
    } catch (err) {
      if (statusEl) statusEl.textContent = String(err);
    } finally {
      liveBtn.disabled = false;
    }
  });
}
if (saveSetupBtn) saveSetupBtn.addEventListener("click", downloadSetup);
if (loadSetupFile) {
  loadSetupFile.addEventListener("change", function (e) {
    var file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      var data = null;
      try { data = JSON.parse(String(reader.result || "")); } catch (err) { data = null; }
      if (!applySetupObject(data)) {
        showToast("Load failed");
        return;
      }
      showToast("Setup loaded");
      try {
        localStorage.setItem(SETUP_KEY, JSON.stringify(state));
        setupBaseline = JSON.stringify(state);
      } catch (err2) {}
    };
    reader.onerror = function () { showToast("Load failed"); };
    reader.readAsText(file);
  });
}
if (roomMicSetupLink) {
  roomMicSetupLink.addEventListener("click", function () { setView("mic"); });
}

bindDesk();
if (wetBypassBtn) {
  wetBypassBtn.addEventListener("click", function () {
    wetBypass = !wetBypass;
    syncUI();
  });
}
applyMicPreset(state.mic_setup || "ortf", false);
migrateRoomState(state);
snapshotBoot();
loadServerDefaults();
loadMicCatalogue();
setView("edit");
