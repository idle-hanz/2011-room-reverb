/* Mic setup, presets, binaural, and capsule controls. */
"use strict";


function rrMsBuilt(id) {
  var api = window.RRMS;
  if (!api || !api.build) return null;
  var key = (api.ALIASES && api.ALIASES[id]) || id;
  if (String(key).indexOf("ms_") !== 0) return null;
  return api.build(key);
}

function rrMsMic(id) {
  var built = rrMsBuilt(id);
  return built && built.mic ? built.mic : null;
}

function divergFromToe(toeHalfDeg) {
  /* Hidden diverg only. Reaktor: MLALR = 0.5·d − 0.25. */
  var th = -Math.abs((Number(toeHalfDeg) * Math.PI) / 180);
  return 2 * (th + 0.25);
}

function sidesDiffer() {
  if (state.family_l !== state.family_r) return true;
  if (Math.abs(Number(state.polar_l) - Number(state.polar_r)) > 0.001) return true;
  if ((state.mic_preset_l || "") !== (state.mic_preset_r || "")) return true;
  return false;
}

function msSetup() {
  return /^ms_/.test(state.mic_setup) || !!state.ms_decode;
}

function splitOn() {
  if (sideSplitUser == null) return sidesDiffer();
  return !!sideSplitUser;
}

function patternFromPreset(mode) {
  mode = mode || state.colour_mode || "MEASURED_SHELF";
  return mode === "MEASURED_SHELF" || mode === "BYPASS";
}

function patternControlsLocked() {
  return patternFromPreset();
}

function capsuleOf(id) {
  var row = micCatalogue[id || DEFAULT_MIC];
  return row && row.capsule ? row.capsule : null;
}

function catalogueReady() {
  for (var k in micCatalogue) return true;
  return false;
}

/* B4: a figure-8 Side in Measured must not stay on a cardioid model. */
function ensureFig8Model(slot) {
  if (state["family_" + slot] !== "bi") return;
  var id = state["mic_preset_" + slot] || DEFAULT_MIC;
  var row = micCatalogue[id];
  var fam = row && row.capsule ? row.capsule.family : "";
  if (fam === "bi") return;
  if (!catalogueReady() && id !== "ShureSM57" && id !== "ShureSM58") return;
  state["mic_preset_" + slot] = "NeumannU87AiBidirect";
}

function ensureFig8Side() {
  ensureFig8Model("l");
  ensureFig8Model("r");
}

function applyPresetLaw() {
  if (state.mic_setup === "binaural") return;
  ensureFig8Side();
  var ready = catalogueReady();
  ["l", "c", "r"].forEach(function (slot) {
    var id = state["mic_preset_" + slot] || DEFAULT_MIC;
    var law = capsuleOf(id);
    if (!law) {
      if (!ready) return;
      law = { pattern: "cardioid", family: "cardioid", polar: 0.5 };
    }
    state["pattern_" + slot] = law.pattern;
    state["family_" + slot] = law.family;
    state["polar_" + slot] = law.polar;
  });
  var lo = state.pattern_l === "omni" ? 0 : 1;
  var ro = state.pattern_r === "omni" ? 0 : 1;
  state.car_omni = 0.5 * (lo + ro);
  state.preset_owns_pattern = true;
}

function deriveCaps(caps) {
  if (!window.RoomMath || !RoomMath.derivePattern) return;
  caps.forEach(function (cap) {
    state["pattern_" + cap] = RoomMath.derivePattern(state["family_" + cap], state["polar_" + cap], state["pattern_" + cap]);
  });
}

function writeFamily(cap, value) {
  if (patternControlsLocked() || state.mic_setup === "binaural") return;
  if (state.pair_mode === "stereo" && (cap === "l" || cap === "r" || cap === "side")) {
    state.family_l = value;
    state.family_r = value;
    deriveCaps(["l", "r"]);
    state.preset_owns_pattern = false;
    markCustomIfDrifted();
    syncUI();
    return;
  }
  if (cap === "side" && splitOn()) return;
  if (cap === "side" || ((cap === "l" || cap === "r") && !splitOn())) {
    state.family_l = value;
    state.family_r = value;
    deriveCaps(["l", "r"]);
  } else {
    state["family_" + cap] = value;
    deriveCaps([cap]);
  }
  state.preset_owns_pattern = false;
  markCustomIfDrifted();
  syncUI();
}

function writePolar(cap, value) {
  if (patternControlsLocked() || state.mic_setup === "binaural") return;
  var v = Math.max(0, Math.min(1, Number(value)));
  if (!isFinite(v)) return;
  if (state.pair_mode === "stereo" && (cap === "l" || cap === "r" || cap === "side")) {
    if (state.family_l === "bi" && state.family_r === "bi") return;
    state.polar_l = v;
    state.polar_r = v;
    deriveCaps(["l", "r"]);
    state.preset_owns_pattern = false;
    markCustomIfDrifted();
    syncUI();
    return;
  }
  if (cap === "side" && splitOn()) return;
  if (cap === "side" || ((cap === "l" || cap === "r") && !splitOn())) {
    if (state.family_l === "bi" && state.family_r === "bi") return;
    state.polar_l = v;
    state.polar_r = v;
    deriveCaps(["l", "r"]);
  } else {
    if (state["family_" + cap] === "bi") return;
    state["polar_" + cap] = v;
    deriveCaps([cap]);
  }
  state.preset_owns_pattern = false;
  markCustomIfDrifted();
  syncUI();
}

function presetShort(id) {
  var row = micCatalogue[id || DEFAULT_MIC];
  var name = row && row.display_name ? String(row.display_name) : "Neumann U87 Ai Cardioid";
  var cut = name.split("\u2014")[0].split("\u2013")[0].split(" - ")[0].trim();
  return cut || "Neumann U87 Ai Cardioid";
}

function presetLawPhrase(id) {
  var law = capsuleOf(id) || { family: "cardioid", polar: 0.5 };
  var label = (window.RoomMath && RoomMath.polarLabel)
    ? RoomMath.polarLabel(law.family, law.polar, law.pattern)
    : "Cardioid";
  return presetShort(id) + " = " + String(label).toLowerCase();
}

function presetOwnPhrase() {
  var l = state.mic_preset_l || DEFAULT_MIC;
  var r = state.mic_preset_r || l;
  var bits = [presetLawPhrase(l)];
  if (splitOn() && r !== l) bits.push(presetLawPhrase(r));
  return bits.join(", ");
}

function sideLockText() {
  return "Pattern comes from the preset (" + presetOwnPhrase() +
    "). Switch Colour to User defined to shape it.";
}

function micEachFootText() {
  var mode = state.colour_mode || "MEASURED_SHELF";
  var msNote = msSetup()
    ? " M/S: S is a fixed figure-8 (S-MIX makes it a real mic)."
    : "";
  if (mode === "ASSUMED_TOYS") {
    return "Drag the amber front to aim. Drag the rim to set the pattern." + msNote;
  }
  var own = presetOwnPhrase();
  if (mode === "BYPASS") {
    return "Bypass: preset pattern, no measured colour (" + own +
      "). Drag the amber front to aim. Switch Colour to User defined to shape the pattern." + msNote;
  }
  return "Measured: the preset owns the pattern (" + own +
    "). Drag the amber front to aim. Switch Colour to User defined to shape the pattern." + msNote;
}

function syncMicEach() {
  var el = document.getElementById("micEach");
  if (!el) return;
  var binaural = state.mic_setup === "binaural";
  el.hidden = !!binaural;
  var mono = state.mic_setup === "mono_c";
  var trio = document.getElementById("micPolarTrio");
  if (trio) {
    trio.querySelectorAll(".mic-polar-col").forEach(function (col) {
      var cap = col.getAttribute("data-cap");
      var unused = mono && (cap === "L" || cap === "R");
      col.classList.toggle("is-unused", unused);
      var note = col.querySelector(".mic-unused");
      if (note) note.hidden = !unused;
    });
  }
  var lock = document.getElementById("micEachLock");
  if (lock) lock.hidden = binaural || !patternFromPreset();
  var foot = document.getElementById("micEachFoot");
  if (foot) foot.textContent = micEachFootText();
}

function placeProxR() {
  var row = document.getElementById("proxRRow");
  if (!row) return;
  if (splitOn()) {
    var hint = document.getElementById("micHpfRHint");
    if (hint && hint.parentElement) {
      if (hint.nextSibling !== row) hint.parentElement.insertBefore(row, hint.nextSibling);
      return;
    }
    var splitHost = document.getElementById("sideSplitR");
    if (splitHost) splitHost.appendChild(row);
    return;
  }
  var left = document.getElementById("proxLRow");
  if (left && left.parentElement && left.nextSibling !== row) {
    left.parentElement.insertBefore(row, left.nextSibling);
  }
}

function capsuleHearMetres(cap) {
  if (!window.RoomMath || !RoomMath.compute) return 99;
  var g = RoomMath.compute(state);
  var mic;
  if (stripIsRoom(cap, state)) {
    var spot = roomSpotOf(state, cap);
    mic = { x: Number(spot.x), y: Number(spot.y), z: Number(spot.z) };
  } else if (cap === "l") {
    mic = g.mic_left;
  } else if (cap === "r") {
    mic = g.mic_right;
  } else {
    mic = g.mic_centre;
  }
  function dist(src) {
    if (!src || !mic) return 99;
    return Math.hypot(Number(src.x) - mic.x, Number(src.y) - mic.y, Number(src.z) - mic.z);
  }
  var d = dist(g.source);
  if (g.source_b) {
    var other = dist(g.source_b);
    if (other < d) d = other;
  }
  return d;
}

function syncProxRows() {
  var ids = { l: "proxLRow", c: "proxCRow", r: "proxRRow" };
  ["l", "c", "r"].forEach(function (cap) {
    var row = document.getElementById(ids[cap]);
    var box = document.getElementById("prox_" + cap);
    var on = state["prox_" + cap] == null ? true : !!state["prox_" + cap];
    if (box && document.activeElement !== box) box.checked = on;
    if (row) row.hidden = !(capsuleHearMetres(cap) < 0.5);
  });
}

function syncPatternChrome() {
  var binaural = state.mic_setup === "binaural";
  var mono = state.mic_setup === "mono_c";
  var ms = msSetup();
  var split = splitOn();
  var sideChoice = document.getElementById("sideMicChoice");
  var sideBlock = document.getElementById("sidePatternBlock");
  var centreBlock = document.getElementById("centrePatternBlock");
  if (sideChoice) sideChoice.hidden = !!mono;
  if (sideBlock) sideBlock.hidden = !!binaural;
  if (centreBlock) centreBlock.hidden = !!binaural;
  var tick = document.getElementById("side_split");
  var hint = document.getElementById("sideSplitHint");
  var shared = document.getElementById("sidePatternShared");
  var sharedPreset = document.getElementById("sidePresetShared");
  var splitBox = document.getElementById("sidePatternSplit");
  if (tick) {
    tick.checked = split;
    tick.disabled = !!binaural;
  }
  if (hint) hint.textContent = "";
  var sHint = document.getElementById("sRouteHint");
  if (sHint) {
    var want = "";
    if ((state.colour_mode || "") === "MEASURED_SHELF") {
      ["l", "c", "r"].forEach(function (cap) {
        if (state["mic_route_" + cap] === "s" && state["family_" + cap] !== "bi") {
          want = "S wants a figure-8 preset";
        }
      });
    }
    sHint.textContent = want;
  }
  var mode = state.colour_mode || "MEASURED_SHELF";
  var user = mode === "ASSUMED_TOYS";
  var measured = mode === "MEASURED_SHELF";
  var showPreset = !user;
  var showPattern = user && !binaural;
  document.querySelectorAll("#panelMics .js-preset").forEach(function (el) {
    el.hidden = !showPreset;
  });
  document.querySelectorAll("#panelMics .js-pattern").forEach(function (el) {
    el.hidden = !showPattern;
  });
  function hideId(id, on) {
    var node = document.getElementById(id);
    if (node) node.hidden = !!on;
  }
  hideId("micHpfSidesRow", !measured);
  hideId("micHpfSidesHint", !measured);
  hideId("micHpfCentreRow", !measured);
  hideId("micHpfCentreHint", !measured);
  hideId("capsuleColour", !user);
  if (shared) shared.hidden = !showPattern || split;
  if (sharedPreset) sharedPreset.hidden = !showPreset || split;
  if (splitBox) splitBox.hidden = !split;
  function setFam(id, value) {
    var el = document.getElementById(id);
    if (el && document.activeElement !== el) el.value = value;
    return el;
  }
  function setPol(id, value) {
    var el = document.getElementById(id);
    if (el && document.activeElement !== el && value != null) el.value = value;
    return el;
  }
  var famS = setFam("family_side", state.family_l || "cardioid");
  var polS = setPol("polar_side", state.polar_l);
  var polSOut = document.getElementById("polar_side_out");
  if (polSOut && window.RoomMath && RoomMath.polarLabel) {
    polSOut.textContent = RoomMath.polarLabel(state.family_l, state.polar_l, state.pattern_l);
  }
  ["l", "c", "r"].forEach(function (cap) {
    var fam = document.getElementById("family_" + cap);
    var pol = document.getElementById("polar_" + cap);
    if (fam) fam.disabled = binaural;
    if (pol) pol.disabled = binaural || state["family_" + cap] === "bi";
  });
  if (famS) famS.disabled = binaural;
  if (polS) polS.disabled = binaural || state.family_l === "bi";
  var lockSide = document.getElementById("patternLockSide");
  if (lockSide) {
    var showLock = !user && !binaural;
    lockSide.hidden = !showLock;
    if (showLock) {
      lockSide.textContent = mode === "BYPASS"
        ? "Bypass: preset pattern, no measured colour"
        : sideLockText();
    }
  }
  placeRoomControls();
  syncProxRows();
  /* A4: binaural keeps only the controls that change the sound.
       B6 hides the third-mic row and the Mic-page link-heights label.
       B7 hides the link row and the third-mic row in Mono centre, and
       disables Off. It does not write space or align_horizontal. */
  hideId("colourModeRow", binaural);
  hideId("alignHorizontalRow", binaural);
  hideId("linkModeRow", binaural || mono);
  hideId("thirdMicRow", binaural || mono);
  hideId("centreMicChoice", binaural || stripIsRoom("c"));
  var linkMic = document.getElementById("link_heights_mic");
  if (linkMic && linkMic.parentElement && linkMic.parentElement.tagName === "LABEL") {
    linkMic.parentElement.hidden = !!binaural;
  }
  var thirdOff = document.querySelector('#thirdMicRow button[data-third="off"]');
  if (thirdOff) thirdOff.disabled = !!mono;
  if (binaural && sideChoice) sideChoice.hidden = true;
  var cCol = document.querySelector('#micPolarTrio .mic-polar-col[data-cap="C"]');
  if (cCol) cCol.hidden = !!binaural;
  var cRow = document.querySelector("#capsuleStackListen .capsule-row[data-cap='C']");
  if (cRow) cRow.hidden = !!binaural;
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
    if (!p || id === "binaural") continue;
    if (!near(state.space, p.space, 0.015)) continue;
    if (!near(state.toe_half_deg, p.toe_half_deg, 0.6)) continue;
    if (p.family_l && state.family_l !== p.family_l) continue;
    if (p.family_c && state.family_c !== p.family_c) continue;
    if (p.family_r && state.family_r !== p.family_r) continue;
    if (p.polar_l != null && !near(state.polar_l, p.polar_l, 0.08)) continue;
    if (p.polar_c != null && !near(state.polar_c, p.polar_c, 0.08)) continue;
    if (p.polar_r != null && !near(state.polar_r, p.polar_r, 0.08)) continue;
    if (p.yaw_l_deg != null && !near(state.yaw_l_deg, p.yaw_l_deg, 0.8)) continue;
    if (p.yaw_c_deg != null && !near(state.yaw_c_deg, p.yaw_c_deg, 0.8)) continue;
    if (p.yaw_r_deg != null && !near(state.yaw_r_deg, p.yaw_r_deg, 0.8)) continue;
    if (!!state.ms_decode !== (id.indexOf("ms_") === 0)) continue;
    /* MS (2 mics) shares the ms_b pair. The spare flag keeps the menu on ms_2. */
    if (id === "ms_2" && state.spare_off !== "r") continue;
    if (id !== "ms_2" && state.spare_off === "r") continue;
    /* D20. ortf and ortf_c share the pair. C off is ORTF; C on is ORTF + C. */
    if (id === "ortf" || id === "ortf_c") {
      var cOn = state.third_mic !== "off";
      if ((id === "ortf") === cOn) continue;
    }
    return id;
  }
  return "custom";
}

function binauralEarSpace(presetId) {
  var s = BINAURAL_SPACE_M[presetId];
  return s != null ? s : 0.18;
}

function stashMicArray() {
  return {
    mic_setup: state.mic_setup,
    space: state.space,
    toe_half_deg: state.toe_half_deg,
    car_omni: state.car_omni,
    diverg: state.diverg,
    pattern_l: state.pattern_l, pattern_c: state.pattern_c, pattern_r: state.pattern_r,
    family_l: state.family_l, family_c: state.family_c, family_r: state.family_r,
    polar_l: state.polar_l, polar_c: state.polar_c, polar_r: state.polar_r,
    yaw_l_deg: state.yaw_l_deg, yaw_c_deg: state.yaw_c_deg, yaw_r_deg: state.yaw_r_deg,
    ms_decode: state.ms_decode,
    preset_owns_pattern: state.preset_owns_pattern,
    fader_c: state.fader_c, trim_c: state.trim_c, mute_c: state.mute_c, phase_c: state.phase_c
  };
}

function leaveBinaural() {
  if (state.mic_setup !== "binaural") return;
  if (_binauralStash) {
    Object.assign(state, _binauralStash);
    _binauralStash = null;
    return;
  }
  state.mute_c = false;
}

function enterBinaural() {
  if (state.mic_setup !== "binaural") _binauralStash = stashMicArray();
  var p = MIC_PRESETS.binaural;
  _applyingPreset = true;
  state.mic_setup = "binaural";
  if (!BINAURAL_SPACE_M[state.binaural_preset]) state.binaural_preset = "SADIE2_KU100";
  state.space = binauralEarSpace(state.binaural_preset);
  state.toe_half_deg = p.toe_half_deg;
  state.car_omni = p.car_omni;
  state.diverg = divergFromToe(p.toe_half_deg);
  state.pattern_l = p.pattern_l;
  state.pattern_c = p.pattern_c;
  state.pattern_r = p.pattern_r;
  state.family_l = p.family_l;
  state.family_c = p.family_c;
  state.family_r = p.family_r;
  state.polar_l = p.polar_l;
  state.polar_c = p.polar_c;
  state.polar_r = p.polar_r;
  state.yaw_l_deg = p.yaw_l_deg;
  state.yaw_c_deg = p.yaw_c_deg;
  state.yaw_r_deg = p.yaw_r_deg;
  state.ms_decode = false;
  state.preset_owns_pattern = false;
  sideSplitUser = false;
  state.mute_c = true;
  if (state.head_yaw_deg == null || !isFinite(Number(state.head_yaw_deg))) state.head_yaw_deg = 0;
  setPolarMics(p.polar);
  applyImageMicTicks();
  Object.assign(state, RoomMath.clampRoom(state));
  syncUI();
  _applyingPreset = false;
}

function applyMicPreset(id, fromUser) {
  if (id === "binaural") {
    enterBinaural();
    return;
  }
  if (state.mic_setup === "binaural") leaveBinaural();
  if (id === "custom" || !MIC_PRESETS[id]) {
    state.mic_setup = "custom";
    var sel = document.getElementById("mic_setup");
    if (sel) sel.value = "custom";
    syncUI();
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
  if (p.family_l) state.family_l = p.family_l;
  if (p.family_c) state.family_c = p.family_c;
  if (p.family_r) state.family_r = p.family_r;
  if (p.polar_l != null) state.polar_l = p.polar_l;
  if (p.polar_c != null) state.polar_c = p.polar_c;
  if (p.polar_r != null) state.polar_r = p.polar_r;
  if (p.yaw_l_deg != null) state.yaw_l_deg = p.yaw_l_deg;
  if (p.yaw_c_deg != null) state.yaw_c_deg = p.yaw_c_deg;
  if (p.yaw_r_deg != null) state.yaw_r_deg = p.yaw_r_deg;
  state.ms_decode = false;
  var replaceDesk = true;
  if (fromUser && state.desk_touched) {
    replaceDesk = window.confirm("Replace the desk with this setup's mix? Cancel keeps your routes.");
  }
  if (replaceDesk) {
    loadDeskPreset(id);
    state.desk_touched = false;
  }
  state.preset_owns_pattern = false;
  sideSplitUser = false;
  if (state.colour_mode === "MEASURED_SHELF" && (id === "ab_omni" || id === "ms")) {
    state.colour_mode = "ASSUMED_TOYS";
    var switched = id === "ab_omni" ? "AB omni" : "MS";
    showToast(switched + " is not the measured preset pattern. Colour is now User defined.");
  } else if (state.colour_mode === "MEASURED_SHELF" || state.colour_mode === "BYPASS") {
    applyPresetLaw();
  }
  var divergEl = document.getElementById("diverg");
  if (divergEl) divergEl.value = String(state.diverg);
  setPolarMics(p.polar);
  applyImageMicTicks();
  Object.assign(state, RoomMath.clampRoom(state));
  syncUI();
  _applyingPreset = false;
}

function markCustomIfDrifted() {
  if (_applyingPreset) return;
  if (state.mic_setup === "binaural") return;
  var matched = matchPresetId();
  state.mic_setup = matched;
  var sel = document.getElementById("mic_setup");
  if (sel && sel.value !== matched) sel.value = matched;
}

function presetHz(id) {
  var row = micCatalogue[id];
  var hz = row && row.hpf_hz != null ? Number(row.hpf_hz) : null;
  return hz != null && isFinite(hz) && hz > 0 ? hz : null;
}

function binauralHeadName(st) {
  var id = (st && st.binaural_preset) || "SADIE2_KU100";
  var sel = document.getElementById("binaural_preset");
  if (sel) {
    var opt = sel.querySelector("option[value='" + id + "']");
    if (opt && opt.textContent) return String(opt.textContent).trim();
  }
  if (id === "SADIE2_KEMAR") return "SADIE II KEMAR";
  if (id === "THK_KU100_FF") return "TH Köln KU100";
  return "SADIE II KU100";
}

function paintMicModel() {
  ensureFig8Side();
  var sideSel = document.getElementById("mic_preset_side");
  var centreSel = document.getElementById("mic_preset_centre");
  var mode = document.getElementById("colour_mode");
  var badge = document.getElementById("micHonestyBadge");
  var sideId = state.mic_preset_l || DEFAULT_MIC;
  var centreId = state.mic_preset_c || sideId;
  function setSel(sel, id) {
    if (!sel || document.activeElement === sel) return;
    if (sel.querySelector("option[value='" + id + "']")) sel.value = id;
  }
  setSel(sideSel, sideId);
  setSel(centreSel, centreId);
  setSel(document.getElementById("mic_preset_l"), sideId);
  setSel(document.getElementById("mic_preset_r"), state.mic_preset_r || sideId);
  if (mode && document.activeElement !== mode) mode.value = state.colour_mode || "MEASURED_SHELF";
  function paintHpf(boxId, rowId, labelId, hintId, hz, flag) {
    var box = document.getElementById(boxId);
    var row = document.getElementById(rowId);
    var label = document.getElementById(labelId);
    var hint = document.getElementById(hintId);
    var can = hz != null;
    if (!can) state[flag] = false;
    if (box) {
      box.disabled = !can;
      box.checked = !!state[flag] && can;
    }
    if (row) row.classList.toggle("is-disabled", !can);
    if (label) label.textContent = can ? ("High-pass " + Math.round(hz) + " Hz") : "No high-pass";
    if (hint) hint.textContent = can ? "Off until engaged." : "This microphone has none.";
  }
  paintHpf("mic_hpf_sides", "micHpfSidesRow", "micHpfSidesLabel", "micHpfSidesHint", presetHz(sideId), "mic_hpf_sides");
  paintHpf("mic_hpf_centre", "micHpfCentreRow", "micHpfCentreLabel", "micHpfCentreHint", presetHz(centreId), "mic_hpf_centre");
  /* R's box shows its own flag, or the shared side flag until the user sets one. Do not write the key here. */
  (function () {
    var hz = presetHz(state.mic_preset_r || sideId);
    var can = hz != null;
    var on = state.mic_hpf_r != null ? !!state.mic_hpf_r : !!state.mic_hpf_sides;
    var box = document.getElementById("mic_hpf_r");
    var row = document.getElementById("micHpfRRow");
    var label = document.getElementById("micHpfRLabel");
    var hint = document.getElementById("micHpfRHint");
    if (box) {
      box.disabled = !can;
      box.checked = !!on && can;
    }
    if (row) row.classList.toggle("is-disabled", !can);
    if (label) label.textContent = can ? ("High-pass " + Math.round(hz) + " Hz") : "No high-pass";
    if (hint) hint.textContent = can ? "Off until engaged." : "This microphone has none.";
  })();
  state.mic_hpf_engaged = !!(state.mic_hpf_sides || state.mic_hpf_centre || state.mic_hpf_r);
  var sideRow = micCatalogue[sideId];
  var centreRow = micCatalogue[centreId];
  var modeName = state.colour_mode || "MEASURED_SHELF";
  var badgeText = "user defined";
  var badgeKind = "assumed";
  if (state.mic_setup === "binaural") {
    badgeText = "Head: " + binauralHeadName(state);
    badgeKind = "measured";
  } else if (modeName !== "ASSUMED_TOYS") {
    var assumed = (sideRow && String(sideRow.honesty).toUpperCase() === "ASSUMED")
      || (centreRow && String(centreRow.honesty).toUpperCase() === "ASSUMED");
    badgeText = assumed ? "preset data: assumed" : "preset data: measured";
    badgeKind = assumed ? "assumed" : "measured";
  }
  var halo = document.getElementById("micHaloHint");
  if (halo && state.mic_setup === "binaural") {
    halo.textContent = "Head: " + binauralHeadName(state) + ". Left and right ears.";
  }
  if (badge) {
    badge.textContent = badgeText;
    badge.className = "honesty-badge honesty-" + badgeKind;
    badge.title = "This badge is the data source for the drawing, not the Colour sound mode.";
  }
}

function applyCapsulePreset(slots, id) {
  var row = micCatalogue[id];
  if (state.pair_mode === "stereo") {
    slots = slots.slice();
    if (slots.indexOf("l") >= 0 && slots.indexOf("r") < 0) slots.push("r");
    if (slots.indexOf("r") >= 0 && slots.indexOf("l") < 0) slots.push("l");
  }
  slots.forEach(function (slot) {
    state["mic_preset_" + slot] = id;
    if (row && row.capsule) {
      state["pattern_" + slot] = row.capsule.pattern;
      state["family_" + slot] = row.capsule.family;
      state["polar_" + slot] = row.capsule.polar;
    }
  });
  if (row && row.capsule) state.preset_owns_pattern = true;
  if (presetHz(state.mic_preset_l) == null) state.mic_hpf_sides = false;
  if (presetHz(state.mic_preset_c) == null) state.mic_hpf_centre = false;
  if (presetHz(state.mic_preset_r) == null) state.mic_hpf_r = false;
  state.mic_hpf_engaged = !!(state.mic_hpf_sides || state.mic_hpf_centre || state.mic_hpf_r);
  syncUI();
}
function syncBinauralChrome() {
  var on = state.mic_setup === "binaural";
  var note = document.getElementById("binauralNote");
  var yawRow = document.getElementById("headYawRow");
  var headRow = document.getElementById("headPresetRow");
  var hint = document.getElementById("micSetupHint");
  if (note) note.hidden = !on;
  if (yawRow) yawRow.hidden = !on;
  if (headRow) headRow.hidden = !on;
  if (hint) hint.hidden = on;
  var spaceEl = document.getElementById("space");
  var spaceLabel = document.getElementById("spaceLabel");
  if (spaceEl) spaceEl.disabled = on;
  if (spaceLabel) {
    spaceLabel.innerHTML = on ? "Ear spacing <em>m</em>" : "Capsule space <em>m</em>";
  }
  var yawEl = document.getElementById("head_yaw");
  var yawOut = document.getElementById("head_yaw_out");
  var yaw = Math.max(-180, Math.min(180, Math.round(Number(state.head_yaw_deg) || 0)));
  if (yawEl && document.activeElement !== yawEl) yawEl.value = String(yaw);
  if (yawOut) yawOut.textContent = (yaw > 0 ? "+" : "") + yaw;
  var headSel = document.getElementById("binaural_preset");
  if (headSel && document.activeElement !== headSel) {
    headSel.value = BINAURAL_SPACE_M[state.binaural_preset] ? state.binaural_preset : "SADIE2_KU100";
  }
  var stack = document.getElementById("capsuleStackListen");
  if (stack) stack.classList.toggle("is-binaural-locked", on);
  var sharedTail = document.getElementById("shared_tail");
  if (sharedTail) {
    sharedTail.checked = !!state.shared_tail;
    sharedTail.disabled = on;
  }
  ["l", "c", "r"].forEach(function (cap) {
    var fam = document.getElementById("family_" + cap);
    var pol = document.getElementById("polar_" + cap);
    if (fam) fam.disabled = on;
    if (pol) pol.disabled = on || state["family_" + cap] === "bi";
  });
  var cRow = document.querySelector("#capsuleStackListen .capsule-row[data-cap='C']");
  if (cRow) cRow.classList.toggle("is-binaural-off", on);
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
    syncUI();
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
function bindCheck(id, key) {
  var el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("change", function (e) {
    state[key] = !!e.target.checked;
    if (key === "align_horizontal" && state.align_horizontal) {
      state.centre_dz = 0;
      var yPair = state.my_l != null ? state.my_l : state.my;
      state.my_l = yPair;
      state.my_r = yPair;
    }
    Object.assign(state, RoomMath.clampRoom(state));
    syncUI();
  });
}
function bindHpf(id, flag) {
  var box = document.getElementById(id);
  if (!box) return;
  box.addEventListener("change", function (e) {
    if (e.target.disabled) {
      state[flag] = false;
      e.target.checked = false;
      return;
    }
    state[flag] = !!e.target.checked;
    state.mic_hpf_engaged = !!(state.mic_hpf_sides || state.mic_hpf_centre || state.mic_hpf_r);
    syncUI();
  });
}
function bindProx(id, flag) {
  var box = document.getElementById(id);
  if (!box) return;
  box.addEventListener("change", function (e) {
    state[flag] = !!e.target.checked;
    syncUI();
  });
}