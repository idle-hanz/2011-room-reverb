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
      if (statusEl) statusEl.textContent = "Images: 