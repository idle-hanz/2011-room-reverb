/* Save, load, and the boot snapshot. */
"use strict";


function applyReaktorSnapshot() {
  /* Locked dump 394–399 / Distances 420–435 / Humidity 486. */
  hallSnapshot = true;
  state.W = 57;
  state.H = 34.241;
  state.L = 97;
  state.sx = 24.925;
  state.sz = 72.083;
  state.sy = 1.88;
  state.my = 1.9;
  state.mcz = 24.25;
  state.space = 0.25;
  state.car_omni = 0.764;
  state.fader_early = 0;
  state.fader_dry = 0;
  state.fader_direct = 0.5;
  state.fader_fdn = 0.5;
  state.trim_direct = 0;
  state.trim_fdn = 0;
  state.trim_early = 0;
  state.trim_dry = 0;
  state.mute_direct = false;
  state.mute_fdn = false;
  state.mute_early = false;
  state.mute_dry = false;
  state.early_wet = 1.0; /* K4: bus enable; early fader (0) keeps it silent */
  state.fdn_wet = 1;
  state.direct_wet = 1;
  state.dry_gain = 0;
  state.fdn_g = 1;
  state.decay_lock = false;
  decayFromUser = false;
  state.ir_length_ms = 1500;
  state.hadamard_n = 32;
  state.humidity = 0.5;
  state.air_shelf = 1;
  state.diffusion_master = -0.5;
  state.mic_response_hz = 10000;
  state.link_heights = false;
  var surfs = (window.ColourSurfacesDefaults && ColourSurfacesDefaults.defaultSurfaces)
    ? ColourSurfacesDefaults.defaultSurfaces()
    : state.surfaces;
  if (surfs) {
    var dif = { A: 0.16, B: 0.25, C: 0.16, D: 0.33, E: 0.27, F: 0.65 };
    Object.keys(dif).forEach(function (L) {
      if (!surfs[L]) return;
      surfs[L].diffusion = dif[L];
      surfs[L].jitter_D = dif[L];
      surfs[L].structure_dif = dif[L];
    });
    state.surfaces = surfs;
    state.surfaces_solo = null;
    state.surfaces_mute = { A: false, B: false, C: false, D: false, E: false, F: false };
  }
  if (colourSurfaces && colourSurfaces.setSurfaces) {
    colourSurfaces.setSurfaces(state.surfaces);
  }
  syncHadamardUI();
  syncUI();
  if (statusEl) {
    statusEl.textContent = "2011 snapshot loaded. Upload a WAV, then Play live or Render. Gain=1 → g=1/32, Humidity 400, hall 57×34×97.";
  }
}

function snapshotBoot() {
  bootState = JSON.parse(JSON.stringify(state));
}

function resetToFresh() {
  if (!bootState) snapshotBoot();
  var fresh = JSON.parse(JSON.stringify(bootState));
  Object.keys(state).forEach(function (k) {
    if (!Object.prototype.hasOwnProperty.call(fresh, k)) delete state[k];
  });
  Object.keys(fresh).forEach(function (k) { state[k] = fresh[k]; });
  migrateRoomState(state);
  hallSnapshot = false;
  decayFromUser = false;
  if (colourSurfaces && colourSurfaces.setSurfaces && state.surfaces) {
    colourSurfaces.setSurfaces(state.surfaces);
  }
}

function applyDefaultsObject(target, d) {
  var skip = {
    space: 1, yaw_l_deg: 1, yaw_c_deg: 1, yaw_r_deg: 1,
    toe_half_deg: 1, diverg: 1, early_wet: 1, surfaces: 1,
    source_radiation_b: 1, source_yaw_b: 1, source_pitch_b: 1
  };
  Object.keys(d).forEach(function (k) {
    if (skip[k] || d[k] == null) return;
    if (Object.prototype.hasOwnProperty.call(target, k)) target[k] = d[k];
  });
}

function scheduleSetupSave() {
  if (!setupSaveArmed) return;
  if (setupSaveTimer) clearTimeout(setupSaveTimer);
  setupSaveTimer = setTimeout(function () {
    setupSaveTimer = null;
    var raw;
    try { raw = JSON.stringify(state); } catch (e) { return; }
    if (raw === setupBaseline) return;
    try {
      localStorage.setItem(SETUP_KEY, raw);
      setupBaseline = raw;
    } catch (err) {
      showToast("Could not save setup");
    }
  }, 400);
}

function applySetupObject(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return false;
  Object.keys(state).forEach(function (k) {
    if (!Object.prototype.hasOwnProperty.call(data, k)) delete state[k];
  });
  Object.keys(data).forEach(function (k) { state[k] = data[k]; });
  if (!state.room_shape) state.room_shape = "box";
  if (state.mirror_lr == null) state.mirror_lr = true;
  if (window.RRPair && RRPair.mapSaved) RRPair.mapSaved(state);
  migrateRoomState(state);
  if (state.surfaces && colourSurfaces && colourSurfaces.setSurfaces) {
    colourSurfaces.setSurfaces(state.surfaces);
  }
  if (window.RoomMath && RoomMath.clampRoom) Object.assign(state, RoomMath.clampRoom(state));
  syncUI();
  return true;
}

function armSetupSave() {
  setupSaveArmed = true;
  try { setupBaseline = JSON.stringify(state); } catch (e) { setupBaseline = ""; }
}

function offerSetupRestore() {
  var raw = null;
  try { raw = localStorage.getItem(SETUP_KEY); } catch (e) { raw = null; }
  if (raw && !placeChosen) {
    var data = null;
    try { data = JSON.parse(raw); } catch (e) { data = null; }
    if (data && window.confirm("Restore the saved setup?")) {
      applySetupObject(data);
      showToast("Setup restored");
    }
  }
  armSetupSave();
}

function downloadSetup() {
  var raw;
  try { raw = JSON.stringify(state, null, 2); } catch (e) {
    showToast("Save failed");
    return;
  }
  var blob = new Blob([raw], { type: "application/json" });
  var a = document.createElement("a");
  var url = URL.createObjectURL(blob);
  a.href = url;
  a.download = "rr2011-setup.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
  try {
    localStorage.setItem(SETUP_KEY, JSON.stringify(state));
    setupBaseline = JSON.stringify(state);
  } catch (err) {}
}

function loadServerDefaults() {
  fetch("/api/defaults").then(function (r) {
    noteHttp(r);
    return r.json();
  }).then(function (data) {
    toastWarnings(data);
    var d = data && data.defaults;
    if (!d) {
      if (!bootState) snapshotBoot();
      offerSetupRestore();
      return;
    }
    if (placeChosen) {
      /* A click landed before defaults. Keep the live place; fold defaults into the boot snapshot. */
      var scratch = JSON.parse(JSON.stringify(bootState || state));
      applyDefaultsObject(scratch, d);
      bootState = scratch;
      offerSetupRestore();
      return;
    }
    applyDefaultsObject(state, d);
    if (state.mic_setup && state.mic_setup !== "custom") applyMicPreset(state.mic_setup, false);
    else syncUI();
    migrateRoomState(state);
    snapshotBoot();
    offerSetupRestore();
  }).catch(function () {
    if (!bootState) snapshotBoot();
    showToast("Defaults failed");
    offerSetupRestore();
  });
}