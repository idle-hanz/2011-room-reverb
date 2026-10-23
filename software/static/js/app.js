(function () {
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
  };

  var BINAURAL_SPACE_M = { SADIE2_KU100: 0.18, SADIE2_KEMAR: 0.18, THK_KU100_FF: 0.175 };

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

  var state = {
    W: 6, H: 3, L: 8,
    /* K3 (locked 28 Sep 2026): source x 2.6 m, height 1.2 m → 29 distinct delays per bus. */
    sx: 2.6, sz: 4.75, mcx: 3, mcz: 1.5, my: 1.5, sy: 1.2,
    link_heights: false,
    /* Literal matches an empty /api body. Boot calls applyMicPreset("ortf") so the page still opens at 17 cm, ±55°. */
    space: 0.25, diverg: 1, toe_half_deg: null, car_omni: 1,
    pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0.5, polar_c: 0.5, polar_r: 0.5,
    yaw_l_deg: null, yaw_c_deg: 0, yaw_r_deg: null,
    centre_dz: 0, align_horizontal: true, link_lr_yaw: true,
    pair_mode: "stereo", pan_law: "linear",
    mic_route_l: "pan", mic_route_c: "pan", mic_route_r: "pan",
    /* D20. Boot preset is ORTF, so the centre mic starts off. */
    third_mic: "off", ms_s: "l", ms_m: "c", s_detached: false,
    width_l: 0, width_c: 0, width_r: 0,
    gain_exact_l: null, gain_exact_c: null, gain_exact_r: null,
    link_mode: "mirror", polar_radius: "db", desk_touched: false,
    place_l: "array", place_c: "array", place_r: "array",
    room_slot: "r", room_x: 4, room_z: 2, room_y: 1.5, room_yaw: 0,
    mic_hp_on: false, mic_hp_hz: 40, mic_response_hz: 10000, mic_proximity: 0.25,
    prox_l: true, prox_c: true, prox_r: true,
    capsule_mm: 17, ms_decode: false,
    colour_mode: "MEASURED_SHELF",
    colour_impl: "sos",
    mic_preset_l: "ShureSM57", mic_preset_c: "ShureSM57", mic_preset_r: "ShureSM57",
    mic_hpf_engaged: false,
    mic_hpf_sides: false,
    mic_hpf_centre: false,
    preset_owns_pattern: true,
    mic_setup: "ortf",
    head_yaw_deg: 0,
    binaural_preset: "SADIE2_KU100",
    /* K4 (locked): early_wet is the early-bus enable (×fader). 1.0 so raising the early fader works at once. */
    early_wet: 1.0, fdn_wet: 1, direct_wet: 1, dry_gain: 0, fdn_g: 1, ir_length_ms: 1500,
    decay_s: 1.8, decay_lock: true, smooth: true, movement: 0, phys_ceiling: true,
    sub_hp: true,
    /* Routing. UI names are not engine keys. Off posts nothing. */
    route_array_pre: "none", route_array_drive: 0, route_array_comp: "off", route_array_amount: 0,
    route_room_pre: "none", route_room_drive: 0, route_room_comp: "off", route_room_amount: 0,
    route_master_pre: "none", route_master_drive: 0, route_master_comp: "off", route_master_amount: 0,
    solo_direct: false, solo_fdn: false, solo_early: false, solo_dry: false,
    solo_l: false, solo_c: false, solo_r: false,
    stereo_mic: false, natural_bus: false,
    fader_l: 0.5, fader_c: 0.5, fader_r: 0.5,
    /* K4 (locked): FDN-first mixing. FDN fader on (0 dB), direct and early faders down. */
    fader_direct: 0, fader_fdn: 0.5, fader_early: 0, fader_dry: 0,
    trim_l: 0, trim_c: 0, trim_r: 0,
    trim_direct: 0, trim_fdn: 0, trim_early: 0, trim_dry: 0,
    pan_l: -1, pan_c: 0, pan_r: 1,
    mute_l: false, mute_c: false, mute_r: false,
    mute_direct: false, mute_fdn: false, mute_early: false, mute_dry: false,
    phase_l: 1, phase_c: 1, phase_r: 1,
    /* K2 (locked): air 1-pole mix default 0 (shelf still gives HF loss). diffusion_master −0.25 (Structure), clamp [−0.5, 0]. */
    humidity: 0.35, air_lp: 0, air_shelf: 1, air_climate: "studio_20C_50RH", diffusion_master: -0.25,
    reaktor_parity: false, live_drag_render: false, shared_tail: false,
    two_sources: false, mirror_b: true, source_balance: 0,
    /* A is omni, so the source stage is not called. B null follows A. */
    source_radiation: "omni", source_yaw: 0, source_pitch: 0,
    source_radiation_b: null, source_yaw_b: null, source_pitch_b: null,
    sx_b: 3.4, sy_b: 1.2, sz_b: 4.75, /* K3: mirror of the default source (W − 2.6, 1.2) */
    path_on: false, path_preset: "still",
    ellipse_rate: 1, ellipse_rx: 0.42, ellipse_rz: 0.35,
    hadamard_n: 32,
    diffusion_seed: 0,
    lambda_ref: 0.02,
    surfaces_solo: null,
    surfaces_mute: { A: false, B: false, C: false, D: false, E: false, F: false },
    surfaces: (window.ColourSurfacesDefaults && ColourSurfacesDefaults.defaultSurfaces)
      ? ColourSurfacesDefaults.defaultSurfaces()
      : null
  };
  var _applyingPreset = false;
  var wavFile = null;
  var wavChannels = 0;
  var currentView = "edit";
  var spaceMode = "lattice"; /* lattice | paths | legs */
  var polarPage = "combined"; /* combined | each */
  var sideSplitUser = null; /* null derives from L vs R. Not posted. */
  /* third_mic C had at the moment it became Room. Client only. Not a state key. */
  var cThirdBeforeRoom = null;
  var hallSnapshot = false; /* 2011 / Hall snapshot loaded. Not posted. */
  var selectedMics = ["L", "R"];
  var imagesCache = null;
  var imagesFetchTimer = null;

  var liveMetres = document.getElementById("liveMetres");
  var liveMetres3d = document.getElementById("liveMetres3d");
  var liveMetresImg = document.getElementById("liveMetresImg");
  var fileName = document.getElementById("fileName");
  var _statusNode = document.getElementById("status");
  var _headerStatus = document.getElementById("headerStatus");
  var statusEl = {
    get textContent() { return _statusNode ? _statusNode.textContent : ""; },
    set textContent(v) {
      var text = v == null ? "" : String(v);
      if (_statusNode) _statusNode.textContent = text;
      if (_headerStatus) _headerStatus.textContent = text.replace(/\s+/g, " ").trim();
    }
  };
  var outPathEl = document.getElementById("outPath");
  var previewAudio = document.getElementById("previewAudio");
  var renderBtn = document.getElementById("renderBtn");
  var editViews = document.getElementById("editViews");
  var micViews = document.getElementById("micViews");
  var mixViews = document.getElementById("mixViews");
  var liveMetresMic = document.getElementById("liveMetresMic");
  var imageViewsEl = document.getElementById("imageViews");
  var micToggles = document.getElementById("micToggles");
  var imageViewTitle = document.getElementById("imageViewTitle");
  var imageViewHint = document.getElementById("imageViewHint");

  var sourceVis = { a: null, b: null };
  var editor = RoomEditor.create({
    floorCanvas: document.getElementById("floorCanvas"),
    elevCanvas: document.getElementById("elevCanvas"),
    view3dCanvas: document.getElementById("view3dCanvas"),
    getState: function () { return state; },
    setState: function (s) { Object.assign(state, s); },
    onChange: function () { syncUI(); scheduleLiveParams(); },
    onDragEnd: function () { scheduleLiveRender(); scheduleLiveParams(); },
    sourceMeta: function (which) { return sourceVis[which] || null; }
  });
  var sourceViews = document.getElementById("sourceViews");
  var sourceDesk = window.SourceDesk ? SourceDesk.create({
    getState: function () { return state; },
    setState: function (s) { Object.assign(state, s); },
    onChange: function () { syncUI(); scheduleLiveParams(); },
    onDragEnd: function () { scheduleLiveRender(); scheduleLiveParams(); },
    RoomMath: window.RoomMath,
    vis: sourceVis
  }) : null;

  var imageView = null;
  var imageViewInitFailed = false;
  var syncRaf = 0;
  var imagesFetchDelayMs = 280; /* defer fetch while dragging (~drag-end) */
  var renderTimer = null;
  var renderBusy = false;

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
    state.reaktor_parity = true;
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
    state.air_lp = 0.25;
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

  function scheduleLiveRender() {
    if (!state.live_drag_render || !wavFile) return;
    if (renderTimer) clearTimeout(renderTimer);
    renderTimer = setTimeout(function () { doRender(); }, 420);
  }

  var liveParamsTimer = null;
  var liveBusy = false;
  var decayFromUser = false;

  var SOLO_BUSES = [
    ["solo_direct", "direct_wet", "direct"],
    ["solo_fdn", "fdn_wet", "fdn"],
    ["solo_early", "early_wet", "early"],
    ["solo_dry", "dry_gain", "dry"]
  ];

  var FADER_KNOTS = [
    [0.02, -60], [0.20, -24], [0.35, -12], [0.42, -6],
    [0.50, 0], [0.58, 3], [0.70, 6], [1, 12]
  ];

  function dbFromTravel(u) {
    u = Number(u);
    if (!(u >= 0.02)) return -Infinity;
    if (u >= 1) return 12;
    var i, a, b, t;
    for (i = 1; i < FADER_KNOTS.length; i++) {
      b = FADER_KNOTS[i];
      a = FADER_KNOTS[i - 1];
      if (u <= b[0]) {
        t = (u - a[0]) / (b[0] - a[0]);
        return a[1] + t * (b[1] - a[1]);
      }
    }
    return 12;
  }

  function travelFromDb(db) {
    if (!isFinite(db) || db < -60) return 0;
    if (db <= -60) return 0.02;
    if (db >= 12) return 1;
    var i, a, b, t;
    for (i = 1; i < FADER_KNOTS.length; i++) {
      b = FADER_KNOTS[i];
      a = FADER_KNOTS[i - 1];
      if (db <= b[1]) {
        t = (db - a[1]) / (b[1] - a[1]);
        return a[0] + t * (b[0] - a[0]);
      }
    }
    return 1;
  }

  function gainFromDb(faderDb, trimDb) {
    if (!isFinite(faderDb)) return 0;
    var db = faderDb + Number(trimDb || 0);
    if (db < -120) return 0;
    var g = Math.pow(10, db / 20);
    if (g < 0) g = 0;
    if (g > 16) g = 16;
    return g;
  }

  function formatSend(travel, trim) {
    var db = dbFromTravel(travel);
    if (!isFinite(db)) return "−∞";
    var sum = Math.round((db + Number(trim || 0)) * 10) / 10;
    return (sum > 0 ? "+" : "") + sum.toFixed(1) + " dB";
  }

  function weightDb(v) {
    var n = Number(v) || 0;
    var a = Math.abs(n);
    if (a < 1e-6) return "−∞";
    var db = 20 * Math.log10(a);
    var t = Math.round(db * 10) / 10;
    var body = (t > 0 ? "+" : (t < 0 ? "−" : "")) + Math.abs(t).toFixed(1);
    if (n < -1e-8) return "Ø " + body;
    return body;
  }

  function stripLinear(src, key) {
    if (src["mute_" + key]) return 0;
    return gainFromDb(dbFromTravel(src["fader_" + key]), src["trim_" + key]);
  }

  function micLinear(src, key) {
    if (src["mute_" + key]) return 0;
    var route = String(src["mic_route_" + key] || "pan");
    var fader = gainFromDb(dbFromTravel(src["fader_" + key]), 0);
    var g;
    if (route === "s") {
      g = Math.pow(10, Number(src["width_" + key] || 0) / 20) * fader;
    } else if (src["gain_exact_" + key] != null && isFinite(Number(src["gain_exact_" + key]))) {
      g = Number(src["gain_exact_" + key]) * fader;
    } else {
      return stripLinear(src, key);
    }
    if (g < 0) g = 0;
    if (g > 16) g = 16;
    return g;
  }

  function monoStripLocked(cap) {
    /* D-AUD-1: Mono centre hears C only. The L/R strips stay on screen and do nothing. */
    return state.mic_setup === "mono_c" && (cap === "l" || cap === "r");
  }

  var msMicStash = null;

  function loadDeskPreset(id) {
    /* Does not mark the desk touched. Boot and a confirmed setup change call this. */
    state.pair_mode = "stereo";
    state.pan_law = "linear";
    state.mic_route_l = "pan";
    state.mic_route_c = "pan";
    state.mic_route_r = "pan";
    /* D20. ORTF is C off. ORTF + C and every other setup keep C in the centre. */
    state.third_mic = (id === "ortf") ? "off" : "centre";
    cThirdBeforeRoom = null;
    state.ms_s = "l";
    state.ms_m = "c";
    state.s_detached = false;
    state.width_l = 0;
    state.width_c = 0;
    state.width_r = 0;
    state.gain_exact_l = null;
    state.gain_exact_c = null;
    state.gain_exact_r = null;
    state.place_l = "array";
    state.place_c = "array";
    state.place_r = "array";
    state.mute_l = false;
    state.mute_c = false;
    state.mute_r = false;
    state.solo_l = false;
    state.solo_c = false;
    state.solo_r = false;
    state.pan_l = -1;
    state.pan_c = 0;
    state.pan_r = 1;
    state.trim_l = 0;
    state.trim_c = 0;
    state.trim_r = 0;
    state.fader_l = 0.5;
    state.fader_c = 0.5;
    state.fader_r = 0.5;
    state.phase_l = 1;
    state.phase_c = 1;
    state.phase_r = 1;
    var msBuilt = rrMsBuilt(id);
    if (msBuilt) {
      if (!msMicStash) {
        msMicStash = {
          l: state.mic_preset_l, c: state.mic_preset_c, r: state.mic_preset_r
        };
      }
      Object.assign(state, msBuilt.desk);
      state.mic_preset_l = msBuilt.mics.l;
      state.mic_preset_c = msBuilt.mics.c;
      state.mic_preset_r = msBuilt.mics.r;
    } else {
      if (msMicStash) {
        state.mic_preset_l = msMicStash.l;
        state.mic_preset_c = msMicStash.c;
        state.mic_preset_r = msMicStash.r;
        msMicStash = null;
      }
    }
    if (!msBuilt && id === "mono_c") {
      state.pair_mode = "independent";
      state.mic_route_c = "centre";
      state.mute_l = true;
      state.mute_r = true;
    } else if (id === "binaural") {
      state.mute_c = true;
    } else if (id === "ms") {
      state.mic_route_c = "centre";
    }
  }

  function deskWeights(src) {
    var o = {
      mic_gain_l: micLinear(src, "l"),
      mic_gain_c: (src.mic_setup === "binaural" || src.third_mic === "off") ? 0 : micLinear(src, "c"),
      mic_gain_r: micLinear(src, "r"),
      mic_pan_l: src.pan_l, mic_pan_c: src.pan_c, mic_pan_r: src.pan_r,
      mic_phase_l: src.phase_l, mic_phase_c: src.phase_c, mic_phase_r: src.phase_r
    };
    function amp(g, ph) {
      var sign = Number(ph) < 0 ? -1 : 1;
      g = Number(g) || 0;
      if (g < 0) g = 0;
      if (g > 16) g = 16;
      return g * sign;
    }
    function pair(route, g, pan, ph) {
      var a = amp(g, ph);
      route = String(route || "pan");
      if (route === "centre") return [a * 0.5, a * 0.5];
      if (route === "both") return [a, a];
      if (route === "l") return [a, 0];
      if (route === "r") return [0, a];
      if (route === "s") return [a, -a];
      var t = (Number(pan) + 1) * 0.5;
      if (t < 0) t = 0;
      if (t > 1) t = 1;
      if (String(src.pan_law || "linear") === "power") {
        return [a * Math.cos(t * Math.PI * 0.5), a * Math.sin(t * Math.PI * 0.5)];
      }
      return [a * (1 - t), a * t];
    }
    var L = pair(src.mic_route_l, o.mic_gain_l, o.mic_pan_l, o.mic_phase_l);
    var C = pair(src.mic_route_c, o.mic_gain_c, o.mic_pan_c, o.mic_phase_c);
    var R = pair(src.mic_route_r, o.mic_gain_r, o.mic_pan_r, o.mic_phase_r);
    return { ll: L[0], lr: L[1], cl: C[0], cr: C[1], rl: R[0], rr: R[1] };
  }

  function roomSpotOf(src, cap) {
    if (window.RRDrag && RRDrag.roomSpot) return RRDrag.roomSpot(src, cap);
    function pick(k) {
      var v = src["room_" + cap + "_" + k];
      if (v == null || v === "" || !isFinite(Number(v))) v = src["room_" + k];
      var n = Number(v);
      return isFinite(n) ? n : 0;
    }
    return { x: pick("x"), y: pick("y"), z: pick("z"), yaw: pick("yaw") };
  }

  /* Display only. The strings are not state and are not posted. */
  function paintRoomReads(geo) {
    var api = window.RRRoomWindow;
    if (!geo || !geo.source || !api) return;
    ["l", "c", "r"].forEach(function (cap) {
      var row = document.querySelector('[data-room-spot="' + cap + '"]');
      if (!row) return;
      var spot = roomSpotOf(state, cap);
      var srcEl = row.querySelector('[data-room-read="source"]');
      var wallEl = row.querySelector('[data-room-read="wall"]');
      if (srcEl) srcEl.textContent = "Source: " + api.sourceMetres(geo.source, spot).toFixed(1) + " m";
      if (wallEl) wallEl.textContent = "Nearest wall: " + api.nearestWallMetres(spot, state.W, state.L).toFixed(1) + " m";
    });
  }

  function stripIsRoom(cap, src) {
    src = src || state;
    return src["place_" + cap] === "room" || (cap === "c" && src.third_mic === "room");
  }

  /* D-ROOMMIC. Only a user switch onto Room mic copies the stand. Recall does not. */
  function snapRoomSpotToStand(cap) {
    if (!window.RoomMath || !RoomMath.compute) return;
    var g = RoomMath.compute(state);
    var pos = cap === "l" ? g.mic_left : (cap === "r" ? g.mic_right : g.mic_centre);
    var yaw = cap === "l" ? g.toe_l_deg : (cap === "r" ? g.toe_r_deg : g.toe_c_deg);
    if (!pos) return;
    state["room_" + cap + "_x"] = pos.x;
    state["room_" + cap + "_y"] = pos.y;
    state["room_" + cap + "_z"] = pos.z;
    state["room_" + cap + "_yaw"] = yaw;
  }

  function migrateRoomState(s) {
    if (window.RRRouting && RRRouting.migrate) RRRouting.migrate(s);
    if (!window.RRDrag || !RRDrag.migrateRoomSpots) return s;
    Object.assign(s, RRDrag.migrateRoomSpots(s));
    return s;
  }

  function heardMix(src) {
    var o = Object.assign({}, src);
    var buses = ["direct", "fdn", "early", "dry"];
    var i;
    o.direct_wet = stripLinear(src, "direct");
    o.fdn_wet = stripLinear(src, "fdn");
    /* K4: early send = bus enable (early_wet, default 1) × early fader. */
    var ewEnable = (src.early_wet == null || !isFinite(Number(src.early_wet))) ? 1 : Math.max(0, Math.min(1, Number(src.early_wet)));
    o.early_wet = ewEnable * stripLinear(src, "early");
    o.dry_gain = stripLinear(src, "dry");
    var any = false;
    for (i = 0; i < SOLO_BUSES.length; i++) {
      if (src[SOLO_BUSES[i][0]]) any = true;
    }
    if (any) {
      for (i = 0; i < buses.length; i++) {
        var soloKey = buses[i] === "dry" ? "solo_dry" : "solo_" + buses[i];
        if (!src[soloKey]) {
          if (buses[i] === "dry") o.dry_gain = 0;
          else o[buses[i] + "_wet"] = 0;
        }
      }
    }
    o.mic_gain_l = micLinear(src, "l");
    o.mic_gain_c = (src.mic_setup === "binaural" || src.third_mic === "off") ? 0 : micLinear(src, "c");
    o.mic_gain_r = micLinear(src, "r");
    /* D-UI36: mic Solo is solo-in-place. Bus solos stay independent, so Solo L plus Solo FDN is L's FDN only. */
    if (src.solo_l || src.solo_c || src.solo_r) {
      if (!src.solo_l) o.mic_gain_l = 0;
      if (!src.solo_c) o.mic_gain_c = 0;
      if (!src.solo_r) o.mic_gain_r = 0;
    }
    ["l", "c", "r"].forEach(function (cap) {
      var room = src["place_" + cap] === "room" || (cap === "c" && src.third_mic === "room");
      if (room) {
        /* Per-strip spot. A missing room_<cap>_* falls back to the shared room_*. */
        var spot = roomSpotOf(src, cap);
        o["mic_x_" + cap] = spot.x;
        o["mic_y_" + cap] = spot.y;
        o["mic_z_" + cap] = spot.z;
        if (cap === "l") o.yaw_l_deg = spot.yaw;
        if (cap === "c") o.yaw_c_deg = spot.yaw;
        if (cap === "r") o.yaw_r_deg = spot.yaw;
      } else {
        delete o["mic_x_" + cap];
        delete o["mic_y_" + cap];
        delete o["mic_z_" + cap];
        delete o["mic_pos_" + cap];
      }
    });
    if (!splitOn()) {
      delete o.mic_hpf_l;
      delete o.mic_hpf_r;
    } else {
      o.mic_hpf_l = src.mic_hpf_l != null ? !!src.mic_hpf_l : !!src.mic_hpf_sides;
      o.mic_hpf_r = src.mic_hpf_r != null ? !!src.mic_hpf_r : !!src.mic_hpf_sides;
    }
    o.mic_pan_l = src.stereo_mic ? -1 : src.pan_l;
    o.mic_pan_c = src.pan_c;
    o.mic_pan_r = src.stereo_mic ? 1 : src.pan_r;
    o.mic_phase_l = src.phase_l;
    o.mic_phase_c = src.phase_c;
    o.mic_phase_r = src.phase_r;
    /* A missing key stays on. Hiding the row does not clear the tick. */
    o.prox_l = src.prox_l == null ? true : !!src.prox_l;
    o.prox_c = src.prox_c == null ? true : !!src.prox_c;
    o.prox_r = src.prox_r == null ? true : !!src.prox_r;
    /* D12: a face solo listens to Early only. The Mix faders stay put, so
       Solo off and every save restore the previous Mix. */
    if (src.surfaces_solo) {
      var earlyFader = stripLinear(src, "early");
      var ewEnable = (src.early_wet == null || !isFinite(Number(src.early_wet))) ? 1 : Math.max(0, Math.min(1, Number(src.early_wet)));
      o.direct_wet = 0;
      o.fdn_wet = 0;
      o.dry_gain = 0;
      o.early_wet = ewEnable * (earlyFader > 0 ? earlyFader : 1);
    }
    /* Play posts the master strip only, on the Bloom keys. Array and room stay out. */
    var routeUi = [
      "bloom_on", "bloom_menu", "bloom_amount_ui", "bloom_colour_ui",
      "glue_colour_ui", "pre_drive_ui", "predelay_ui",
      "bloom_attack_ui", "bloom_release_ui",
      "bloom_preset", "bloom_amount", "bloom_colour", "glue_colour",
      "pre_colour", "pre_drive_db", "predelay_ms",
      "bloom_attack_scale", "bloom_release_scale",
      "route_array_pre", "route_array_drive", "route_array_comp", "route_array_amount",
      "route_room_pre", "route_room_drive", "route_room_comp", "route_room_amount",
      "route_master_pre", "route_master_drive", "route_master_comp", "route_master_amount",
      "array_preset", "array_amount", "array_pre", "array_drive_db",
      "room_preset", "room_amount", "room_pre", "room_drive_db"
    ];
    var bi;
    for (bi = 0; bi < routeUi.length; bi++) delete o[routeUi[bi]];
    if (window.RRRouting && RRRouting.masterScene) Object.assign(o, RRRouting.masterScene(src));
    return o;
  }

  function liveRequestBody() {
    var o = heardMix(state);
    if (window.LiveFDN) {
      var rate = LiveFDN.rate ? LiveFDN.rate() : 0;
      var rev = LiveFDN.colourRev ? LiveFDN.colourRev() : "";
      if (rate) o.sample_rate = rate;
      if (rev) o.colour_rev = rev;
    }
    return o;
  }

  function feedbackLawOn() {
    return !!state.reaktor_parity || !!hallSnapshot;
  }

  function paintDecayHint() {
    var el = document.getElementById("decayHint");
    if (!el) return;
    var sec = Number(state.decay_s).toFixed(2);
    if (state.decay_lock) {
      el.textContent = "Decay is armed at " + sec + " s. Play live and Render use that length.";
    } else {
      el.textContent = "2011 law (Structure Gain) is in charge (" + sec +
        " s). Move Decay to arm a fixed length again.";
    }
    paintPhysReadout();
    var subBox = document.getElementById("sub_hp");
    if (subBox) subBox.checked = !!state.sub_hp;
  }

  var physTimer = null;
  var physText = "";
  function paintPhysReadout() {
    var box = document.getElementById("phys_ceiling");
    var el = document.getElementById("physReadout");
    if (box) box.checked = !!state.phys_ceiling;
    if (!el) return;
    if (!state.phys_ceiling) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    el.textContent = physText || "Physical ceiling";
    schedulePhysPreview();
  }

  function schedulePhysPreview() {
    if (!state.phys_ceiling) return;
    if (physTimer) clearTimeout(physTimer);
    physTimer = setTimeout(pullPhysPreview, 80);
  }

  async function pullPhysPreview() {
    physTimer = null;
    if (!state.phys_ceiling) return;
    try {
      var res = await fetch("/api/phys_preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(heardMix(state))
      });
      noteHttp(res);
      var data = await res.json();
      toastWarnings(data);
      if (!data || !data.ok || !state.phys_ceiling) return;
      var el = document.getElementById("physReadout");
      var rowEl = document.getElementById("physCeilingRow");
      if (!el) return;
      if (data.on === false) {
        if (rowEl) rowEl.classList.add("is-off");
        if (state.two_sources) {
          physText = "off with two sources";
          el.hidden = false;
          el.textContent = physText;
        } else {
          physText = "";
          el.hidden = true;
          el.textContent = "";
        }
        return;
      }
      if (rowEl) rowEl.classList.remove("is-off");
      if (!data.armed) {
        physText = "Physical ceiling waits until Decay is armed.";
      } else {
        var bits = [];
        var row = data.bands || [];
        var i, tNum, midNum, kNum;
        for (i = 0; i < row.length; i++) {
          tNum = Number(row[i].t);
          if (!isFinite(tNum)) continue;
          bits.push(row[i].hz + " Hz " + tNum.toFixed(2) + " s");
        }
        midNum = Number(data.mean_500_1k);
        kNum = Number(data.k);
        physText = "Physical mid " + (isFinite(midNum) ? midNum.toFixed(2) : "—")
          + " s, k " + (isFinite(kNum) ? kNum.toFixed(3) : "—");
        if (bits.length) physText += ". " + bits.join(", ");
        if (data.reachable === false && isFinite(Number(data.reached_mid))) {
          physText += ". Room can reach ~" + Number(data.reached_mid).toFixed(2) + " s";
        }
      }
      el.hidden = false;
      el.textContent = physText;
    } catch (err) {
      showToast("Physical preview failed");
    }
  }

  function syncFeedbackRow() {
    var row = document.getElementById("feedbackRow");
    var slider = document.getElementById("fdn_g");
    var on = feedbackLawOn();
    if (row) row.hidden = !on;
    if (slider) slider.disabled = !on;
  }

  function paintSolos() {
    var any = false;
    var i;
    for (i = 0; i < SOLO_BUSES.length; i++) {
      if (state[SOLO_BUSES[i][0]]) any = true;
    }
    for (i = 0; i < SOLO_BUSES.length; i++) {
      var on = !!state[SOLO_BUSES[i][0]];
      var btn = document.querySelector('.solo-btn[data-solo="' + SOLO_BUSES[i][2] + '"]');
      var row = document.querySelector('.desk-strip[data-mix="' + SOLO_BUSES[i][2] + '"]');
      if (btn) btn.setAttribute("aria-pressed", on ? "true" : "false");
      if (row) row.classList.toggle("is-muted", any && !on);
    }
    var micAny = !!(state.solo_l || state.solo_c || state.solo_r);
    ["l", "c", "r"].forEach(function (cap) {
      var micOn = !!state["solo_" + cap];
      var micBtn = document.querySelector('.solo-btn[data-solo="' + cap + '"]');
      var micRow = document.querySelector('.desk-strip[data-cap="' + cap + '"]');
      if (micBtn) micBtn.setAttribute("aria-pressed", micOn ? "true" : "false");
      if (micRow) micRow.classList.toggle("is-muted", micAny && !micOn);
    });
  }

  var DESK_FADERS = ["l", "c", "r", "direct", "fdn", "early", "dry"];
  var FADER_BOOT = { l: 0.5, c: 0.5, r: 0.5, direct: 0, fdn: 0.5, early: 0, dry: 0 };

  function setFader(key, u, fromLink) {
    u = Math.max(0, Math.min(1, Number(u)));
    if (!fromLink) {
      var db = dbFromTravel(u);
      if (isFinite(db) && Math.abs(db) <= 0.25) u = 0.5;
    }
    state["fader_" + key] = u;
    if (fromLink) return;
    if (state.stereo_mic && (key === "l" || key === "r")) {
      setFader(key === "l" ? "r" : "l", u, true);
    }
    if (state.natural_bus && (key === "direct" || key === "fdn")) {
      setFader(key === "direct" ? "fdn" : "direct", u, true);
    }
  }

  function setTrim(key, db, fromLink) {
    db = Math.max(-12, Math.min(12, Number(db)));
    if (!isFinite(db)) db = 0;
    state["trim_" + key] = db;
    if (fromLink) return;
    if (state.natural_bus && (key === "direct" || key === "fdn")) {
      setTrim(key === "direct" ? "fdn" : "direct", db, true);
    }
  }

  /* Buttons for one strip. Does not write the route back: centre stays centre until a click. */
  function lrView(cap) {
    var route = String(state["mic_route_" + cap] || "pan");
    var muteOn = !!state["mute_" + cap];
    var msMid = !!(window.RRLR && RRLR.isMsMid(state, cap));
    if (!window.RRLR) {
      return { route: route, shown: { l: 0, r: 0 }, pot: "none", panLive: false };
    }
    var mapped = RRLR.fromRoute(route, state["phase_" + cap], muteOn, { msMid: msMid, pan: state["pan_" + cap] });
    var shown = muteOn ? (mapped.shownBtn || { l: 0, r: 0 }) : mapped.btn;
    var info = RRLR.toRoute(shown, { msMid: msMid, legacyBoth: mapped.legacyBoth, forcePan: mapped.forcePan });
    return { route: route, shown: shown, pot: info.pot, panLive: route === "pan" && info.pot === "balance" };
  }

  function paintDesk() {
    var i, key, fader, trim, pan, read, mute, knob, needle;
    for (i = 0; i < DESK_FADERS.length; i++) {
      key = DESK_FADERS[i];
      fader = document.getElementById("fader_" + key);
      trim = document.getElementById("trim_" + key);
      read = document.getElementById("read_" + key);
      mute = document.getElementById("mute_" + key);
      if (fader) fader.value = state["fader_" + key];
      if (trim) trim.value = state["trim_" + key];
      if (read && !read.querySelector("input")) {
        read.textContent = formatSend(state["fader_" + key], state["trim_" + key]);
      }
      if (mute) mute.setAttribute("aria-pressed", state["mute_" + key] ? "true" : "false");
      var strip = fader && fader.closest(".desk-strip");
      if (strip) strip.classList.toggle("is-silenced", !!state["mute_" + key]);
      if (trim && trim.parentElement) {
        needle = (-140 + ((Number(state["trim_" + key]) + 12) / 24) * 280).toFixed(1) + "deg";
        trim.parentElement.style.setProperty("--needle", needle);
      }
    }
    ["l", "c", "r"].forEach(function (cap) {
      pan = document.getElementById("pan_" + cap);
      var locked = state.stereo_mic && cap !== "c";
      if (pan) {
        if (document.activeElement !== pan) {
          pan.value = locked ? (cap === "l" ? -1 : 1) : state["pan_" + cap];
        }
        if (pan.parentElement) {
          var pv = Number(pan.value);
          pan.parentElement.style.setProperty("--needle", (-140 + ((pv + 1) / 2) * 280).toFixed(1) + "deg");
        }
      }
      var row = document.querySelector('.desk-strip[data-cap="' + cap + '"]');
      if (row) row.classList.toggle("is-linked", !!(state.stereo_mic && cap !== "c"));
      if (row) row.classList.toggle("is-pan-locked", !!locked);
      if (cap === "c" && row) row.classList.toggle("is-binaural-off", state.mic_setup === "binaural");
    });
    if (state.mic_setup === "binaural") {
      var cFader = document.getElementById("fader_c");
      var cRead = document.getElementById("read_c");
      var cPan = document.getElementById("pan_c");
      if (cFader) cFader.disabled = true;
      if (cPan) cPan.disabled = true;
      if (cRead) cRead.textContent = "off";
    } else {
      var cFaderOn = document.getElementById("fader_c");
      if (cFaderOn) cFaderOn.disabled = false;
    }
    var monoDesk = state.mic_setup === "mono_c";
    ["l", "r"].forEach(function (cap) {
      var row = document.querySelector('.desk-strip[data-cap="' + cap + '"]');
      if (!row) return;
      row.classList.toggle("is-mono-off", monoDesk);
      row.title = monoDesk ? "Mono centre uses only C" : "";
      row.querySelectorAll("input, button").forEach(function (el) {
        var panLock = !monoDesk && state.stereo_mic && el.id === ("pan_" + cap);
        el.disabled = !!monoDesk || !!panLock;
        if (monoDesk) el.title = "Mono centre uses only C";
        else if (el.title === "Mono centre uses only C") el.title = "";
      });
    });
    ["l", "c", "r"].forEach(function (cap) {
      var view = lrView(cap);
      var route = view.route;
      var monoLock = state.mic_setup === "mono_c" && (cap === "l" || cap === "r");
      var stereoLock = state.stereo_mic && cap !== "c";
      var binLock = state.mic_setup === "binaural" && cap === "c";
      document.querySelectorAll('.lr-btn[data-lr="' + cap + '"]').forEach(function (btn) {
        var side = btn.getAttribute("data-side") === "r" ? "r" : "l";
        var v = view.shown[side] || 0;
        var lab = window.RRLR ? RRLR.buttonLabel(side, v) : { text: side.toUpperCase(), title: "" };
        btn.setAttribute("data-v", String(v));
        btn.textContent = lab.text;
        btn.setAttribute("aria-pressed", v === 0 ? "false" : "true");
        if (!monoLock) {
          btn.title = lab.title;
          btn.setAttribute("aria-label", lab.title);
        }
      });
      pan = document.getElementById("pan_" + cap);
      var panBox = document.getElementById("panBox_" + cap);
      var panLabel = document.getElementById("panLabel_" + cap);
      if (pan) pan.disabled = !view.panLive || stereoLock || monoLock || binLock;
      if (pan && !monoLock) pan.title = view.panLive ? "Pan between the speakers" : "This pan is not in the send";
      if (panBox) panBox.classList.toggle("is-pot-off", !view.panLive || binLock || stereoLock);
      if (panLabel && window.RRLR) panLabel.textContent = RRLR.potLabel(view.panLive ? "balance" : "none");
      var trimBox = document.getElementById("trimBox_" + cap);
      var widthBox = document.getElementById("widthBox_" + cap);
      var sOn = route === "s";
      if (trimBox) trimBox.hidden = sOn;
      if (widthBox) widthBox.hidden = !sOn;
      var width = document.getElementById("width_" + cap);
      if (width && document.activeElement !== width) width.value = state["width_" + cap] || 0;
      if (!monoLock) {
        var trimIn = document.getElementById("trim_" + cap);
        if (trimIn) trimIn.title = "Trim in dB";
        if (width) width.title = "Side width in dB";
        var muteBtn = document.getElementById("mute_" + cap);
        if (muteBtn) muteBtn.title = "Silence this mic";
        var soloBtn = document.querySelector('.solo-btn[data-solo="' + cap + '"]');
        if (soloBtn) soloBtn.title = "Hear only this mic. The other mics go quiet.";
        var faderIn = document.getElementById("fader_" + cap);
        if (faderIn) faderIn.title = "Send level";
        var readIn = document.getElementById("read_" + cap);
        if (readIn) readIn.title = "Send level in dB. Click to type.";
      }
      document.querySelectorAll('[data-place="' + cap + '"]').forEach(function (btn) {
        var name = btn.getAttribute("data-name");
        var on = name === (state["place_" + cap] || "array");
        btn.setAttribute("aria-pressed", on ? "true" : "false");
        if (!monoLock) {
          btn.title = name === "room"
            ? "This mic is placed at its own spot in the room"
            : "This mic stays on the stand with the others";
        }
      });
    });
    document.querySelectorAll("[data-pair]").forEach(function (btn) {
      var on = btn.getAttribute("data-pair") === (state.pair_mode || "stereo");
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    document.querySelectorAll("[data-pan-law]").forEach(function (btn) {
      var on = btn.getAttribute("data-pan-law") === (state.pan_law || "linear");
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    document.querySelectorAll("[data-link]").forEach(function (btn) {
      var mode = state.link_mode || "mirror";
      if (mode === "independent") mode = "split";
      var on = btn.getAttribute("data-link") === mode;
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    document.querySelectorAll("[data-third]").forEach(function (btn) {
      var on = btn.getAttribute("data-third") === (state.third_mic || "centre");
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    var msPick = document.getElementById("msPickers");
    if (msPick) msPick.hidden = state.pair_mode !== "ms";
    var msS = document.getElementById("ms_s");
    var msM = document.getElementById("ms_m");
    if (msS && document.activeElement !== msS) msS.value = state.ms_s || "l";
    if (msM && document.activeElement !== msM) msM.value = state.ms_m || "c";
    var roomBox = document.getElementById("roomFields");
    var roomOn = stripIsRoom("l") || stripIsRoom("c") || stripIsRoom("r");
    if (roomBox) roomBox.hidden = !roomOn;
    ["l", "c", "r"].forEach(function (cap) {
      var row = document.querySelector('[data-room-spot="' + cap + '"]');
      if (row) row.hidden = !stripIsRoom(cap);
      ["x", "z", "y", "yaw"].forEach(function (k) {
        var el = document.getElementById("room_" + cap + "_" + k);
        if (!el || document.activeElement === el) return;
        var v = state["room_" + cap + "_" + k];
        if (v == null || v === "" || !isFinite(Number(v))) v = state["room_" + k];
        if (v != null && isFinite(Number(v))) el.value = v;
      });
    });
    var matrix = document.getElementById("deskMatrix");
    if (matrix) {
      var w = deskWeights(state);
      function n3(v) {
        var t = Math.round(v * 1000) / 1000;
        return (t >= 0 ? "+" : "") + t.toFixed(3);
      }
      matrix.textContent = "L " + weightDb(w.ll) + " / " + weightDb(w.lr)
        + "   C " + weightDb(w.cl) + " / " + weightDb(w.cr)
        + "   R " + weightDb(w.rl) + " / " + weightDb(w.rr) + " dB";
      matrix.title = "Linear gains  L " + n3(w.ll) + " " + n3(w.lr)
        + "   C " + n3(w.cl) + " " + n3(w.cr)
        + "   R " + n3(w.rl) + " " + n3(w.rr);
    }
    document.querySelectorAll("[data-radius]").forEach(function (btn) {
      var on = btn.getAttribute("data-radius") === (state.polar_radius || "db");
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    var linkBox = document.getElementById("link_lr_yaw");
    if (linkBox) linkBox.checked = (state.link_mode || "mirror") === "mirror";
    var naturalBtn = document.getElementById("naturalBtn");
    if (naturalBtn) naturalBtn.setAttribute("aria-pressed", state.natural_bus ? "true" : "false");
    ["direct", "fdn"].forEach(function (bus) {
      var row = document.querySelector('.desk-strip[data-mix="' + bus + '"]');
      if (row) row.classList.toggle("is-linked", !!state.natural_bus);
    });
  }

  function bindDesk() {
    DESK_FADERS.forEach(function (key) {
      var fader = document.getElementById("fader_" + key);
      var trim = document.getElementById("trim_" + key);
      var mute = document.getElementById("mute_" + key);
      var read = document.getElementById("read_" + key);
      if (fader) {
        fader.addEventListener("input", function () {
          if (monoStripLocked(key)) return;
          setFader(key, fader.value, false);
          if (key === "l" || key === "c" || key === "r") state.desk_touched = true;
          syncUI();
        });
        fader.addEventListener("dblclick", function (e) {
          e.preventDefault();
          e.stopPropagation();
          if (monoStripLocked(key)) return;
          var boot = Object.prototype.hasOwnProperty.call(FADER_BOOT, key) ? FADER_BOOT[key] : 0;
          setFader(key, boot, false);
          if (key === "l" || key === "c" || key === "r") state.desk_touched = true;
          syncUI();
        });
      }
      if (trim) {
        trim.addEventListener("input", function () {
          if (monoStripLocked(key)) return;
          setTrim(key, trim.value, false);
          if (key === "l" || key === "c" || key === "r") state.desk_touched = true;
          syncUI();
        });
      }
      if (mute) {
        mute.addEventListener("click", function () {
          if (monoStripLocked(key)) return;
          state["mute_" + key] = !state["mute_" + key];
          if (key === "l" || key === "c" || key === "r") state.desk_touched = true;
          syncUI();
        });
      }
      if (read) {
        read.addEventListener("click", function () {
          if (monoStripLocked(key)) return;
          if (read.querySelector("input")) return;
          var input = document.createElement("input");
          input.type = "number";
          input.step = "0.1";
          input.className = "desk-type";
          var db = dbFromTravel(state["fader_" + key]);
          input.value = isFinite(db) ? String(Math.round((db + Number(state["trim_" + key] || 0)) * 10) / 10) : "";
          read.textContent = "";
          read.appendChild(input);
          input.focus();
          input.select();
          var done = false;
          function commit(cancel) {
            if (done) return;
            done = true;
            if (input.parentNode) input.parentNode.removeChild(input);
            if (!cancel) {
              var raw = String(input.value || "").trim().toLowerCase();
              if (raw === "" || raw === "off" || raw === "-inf" || raw === "-oo") {
                setFader(key, 0, false);
              } else {
                var n = Number(raw);
                if (isFinite(n)) {
                  setFader(key, travelFromDb(n - Number(state["trim_" + key] || 0)), false);
                }
              }
              if (key === "l" || key === "c" || key === "r") state.desk_touched = true;
            }
            syncUI();
          }
          input.addEventListener("keydown", function (e) {
            if (e.key === "Enter") { e.preventDefault(); commit(false); }
            else if (e.key === "Escape") commit(true);
          });
          input.addEventListener("blur", function () { commit(false); });
        });
      }
    });
    ["l", "c", "r"].forEach(function (cap) {
      var pan = document.getElementById("pan_" + cap);
      if (pan) {
        pan.addEventListener("input", function () {
          if (monoStripLocked(cap)) return;
          if (state.stereo_mic && cap !== "c") return;
          state["pan_" + cap] = Math.max(-1, Math.min(1, Number(pan.value)));
          state.desk_touched = true;
          syncUI();
        });
      }
      var width = document.getElementById("width_" + cap);
      if (width) {
        width.addEventListener("input", function () {
          if (monoStripLocked(cap)) return;
          var wv = Number(width.value);
          if (!isFinite(wv)) wv = 0;
          state["width_" + cap] = Math.max(-24, Math.min(24, wv));
          state.desk_touched = true;
          syncUI();
        });
      }
    });
    document.querySelectorAll(".lr-btn[data-lr]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var cap = btn.getAttribute("data-lr");
        var side = btn.getAttribute("data-side");
        if (monoStripLocked(cap)) return;
        if (cap !== "l" && cap !== "c" && cap !== "r") return;
        if (side !== "l" && side !== "r") return;
        if (!window.RRLR) return;
        var hit = RRLR.clickPatch(state, cap, side);
        Object.assign(state, hit.patch);
        state.desk_touched = true;
        syncUI();
      });
    });
    document.querySelectorAll("[data-place][data-name]").forEach(function (btn) {
      var cap = btn.getAttribute("data-place");
      if (cap !== "l" && cap !== "c" && cap !== "r") return;
      btn.addEventListener("click", function () {
        var name = btn.getAttribute("data-name");
        if (monoStripLocked(cap)) return;
        if (name !== "array" && name !== "room") return;
        var wasRoom = stripIsRoom(cap);
        /* FIX-A. Room on C turns the centre mic on after the save.
           A second click does not replace cThirdBeforeRoom. L and R do not. */
        var step = RRViewPose.mixThird(state.third_mic, cap, name, wasRoom, cThirdBeforeRoom);
        cThirdBeforeRoom = step.saved;
        if (cap === "c") state.third_mic = step.third;
        state["place_" + cap] = name;
        if (name === "room") {
          state.room_slot = cap;
          if (!wasRoom) snapRoomSpotToStand(cap);
        }
        state.desk_touched = true;
        syncUI();
      });
    });
    function aimCoincidentS() {
      if (state.pair_mode !== "ms" || state.s_detached) return;
      var s = state.ms_s || "l";
      var m = state.ms_m || "c";
      if (s === m) m = s === "c" ? "l" : "c";
      var my = Number(state["yaw_" + m + "_deg"]) || 0;
      state["yaw_" + s + "_deg"] = my + 90;
    }
    document.querySelectorAll("[data-pair]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mode = btn.getAttribute("data-pair");
        if (mode !== "stereo" && mode !== "ms" && mode !== "independent") return;
        state.pair_mode = mode;
        aimCoincidentS();
        state.desk_touched = true;
        syncUI();
      });
    });
    document.querySelectorAll("[data-pan-law]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var law = btn.getAttribute("data-pan-law");
        if (law !== "linear" && law !== "power") return;
        state.pan_law = law;
        state.desk_touched = true;
        syncUI();
      });
    });
    ["ms_s", "ms_m"].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      el.addEventListener("change", function () {
        state[id] = el.value;
        if (state.ms_s === state.ms_m) state.ms_m = state.ms_s === "c" ? "l" : "c";
        aimCoincidentS();
        state.desk_touched = true;
        syncUI();
      });
    });
    document.querySelectorAll("[data-link]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mode = btn.getAttribute("data-link");
        if (mode !== "mirror" && mode !== "linked" && mode !== "split" && mode !== "independent") return;
        if (mode === "independent") mode = "split";
        state.link_mode = mode;
        state.link_lr_yaw = mode === "mirror";
        if (mode === "mirror") state.yaw_r_deg = -Number(state.yaw_l_deg || 0);
        /* Split opens R's own preset, pattern, HPF and yaw. Mirror and Linked close that. */
        sideSplitUser = mode === "split";
        syncUI();
      });
    });
    document.querySelectorAll("[data-third]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mode = btn.getAttribute("data-third");
        if (mode !== "off" && mode !== "centre" && mode !== "room") return;
        var wasRoom = stripIsRoom("c");
        if (mode === "room" && !wasRoom) cThirdBeforeRoom = state.third_mic;
        state.third_mic = mode;
        if (mode === "room") {
          state.place_c = "room";
          state.room_slot = "c";
          if (!wasRoom) snapRoomSpotToStand("c");
        } else if (state.place_c === "room") {
          state.place_c = "array";
        }
        state.desk_touched = true;
        syncUI();
      });
    });
    ["l", "c", "r"].forEach(function (cap) {
      ["x", "z", "y", "yaw"].forEach(function (k) {
        var el = document.getElementById("room_" + cap + "_" + k);
        if (!el) return;
        el.addEventListener("input", function () {
          var v = parseFloat(el.value);
          if (!isFinite(v)) return;
          state["room_" + cap + "_" + k] = v;
          state.desk_touched = true;
          syncUI();
        });
      });
    });
    document.querySelectorAll("[data-radius]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mode = btn.getAttribute("data-radius");
        if (mode !== "db" && mode !== "linear") return;
        state.polar_radius = mode;
        syncUI();
      });
    });
    var stereoBtn = document.getElementById("stereoMicBtn");
    if (stereoBtn) {
      stereoBtn.addEventListener("click", function () {
        state.stereo_mic = !state.stereo_mic;
        if (state.stereo_mic) {
          state.pan_l = -1;
          state.pan_r = 1;
          state.fader_r = state.fader_l;
        }
        syncUI();
      });
    }
    var naturalBtn = document.getElementById("naturalBtn");
    if (naturalBtn) {
      naturalBtn.addEventListener("click", function () {
        state.natural_bus = !state.natural_bus;
        if (state.natural_bus) {
          state.fader_direct = 0.5;
          state.fader_fdn = 0.5;
          state.trim_direct = 0;
          state.trim_fdn = 0;
        }
        syncUI();
      });
    }
  }

  function applyDecayReadout(seconds) {
    state.decay_s = seconds;
    var dEl = document.getElementById("decay_s");
    var dOut = document.getElementById("decay_s_out");
    if (dEl) dEl.value = seconds;
    if (dOut) dOut.textContent = Number(seconds).toFixed(2);
    paintDecayHint();
  }

  function gainFromDecay(decayS, meanMs, n) {
    n = n || 32;
    var meanT = (Number(meanMs) || 80) * 0.001;
    if (decayS <= 0.05 || meanT <= 1e-9) return 0;
    var loop = Math.pow(0.001, meanT / decayS);
    var g = loop / Math.sqrt(n);
    var lim = 0.99 / Math.sqrt(n);
    if (g > lim) g = lim;
    if (g < 0) g = 0;
    return Math.min(1, g * n);
  }

  function scheduleLiveParams() {
    if (!window.LiveFDN || !LiveFDN.isRunning()) return;
    if (liveParamsTimer) clearTimeout(liveParamsTimer);
    liveParamsTimer = setTimeout(pushLiveParams, 45);
  }
  window.RRPushLive = scheduleLiveParams;

  var decayPreviewTimer = null;
  function scheduleDecayPreview() {
    if (window.LiveFDN && LiveFDN.isRunning()) return;
    if (decayPreviewTimer) clearTimeout(decayPreviewTimer);
    if (state.decay_lock) return;
    decayPreviewTimer = setTimeout(pullDecayPreview, 200);
  }

  async function pullDecayPreview() {
    decayPreviewTimer = null;
    if (state.decay_lock || decayFromUser) return;
    if (window.LiveFDN && LiveFDN.isRunning()) return;
    if (liveBusy) {
      scheduleDecayPreview();
      return;
    }
    liveBusy = true;
    try {
      var res = await fetch("/api/live_params", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state)
      });
      noteHttp(res);
      var data = await res.json();
      toastWarnings(data);
      if (!data.ok) return;
      if (window.LiveFDN && LiveFDN.isRunning()) return;
      if (data.mean_delay_ms) state._mean_delay_ms = data.mean_delay_ms;
      if (!state.decay_lock && !decayFromUser && data.decay_s > 0.05) {
        applyDecayReadout(data.decay_s);
      }
    } catch (err) {
      showToast("Decay preview failed");
    } finally {
      liveBusy = false;
    }
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
        if (currentView !== "space") return;
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
          if (currentView !== "space") return;
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
      onChange: function () { syncUI(); scheduleLiveParams(); }
    });
  }

  var polarView = null;
  var micHero = null;
  var micCatalogue = {};
  if (window.PolarFieldView) {
    polarView = new PolarFieldView({
      getState: function () { return state; },
      onRefresh: function () { schedulePolar(); }
    });
  }


  function fmt(n, d) {
    if (d === undefined) d = 2;
    return Number(n).toFixed(d);
  }

  /* Picture ticks only. Does not write third_mic, mic_gain_c, or place_*. */
  function imageMicDefaults() {
    var id = state.mic_setup || "ortf";
    if (id === "ortf") return ["L", "R"];
    if (id === "mono_c") return ["C"];
    if (id === "binaural") return ["L", "R"];
    if (state.third_mic === "off") return ["L", "R"];
    return ["L", "C", "R"];
  }

  function applyImageMicTicks() {
    var want = {};
    var ids = imageMicDefaults();
    ids.forEach(function (id) { want[id] = true; });
    document.querySelectorAll("#micToggles input[data-mic]").forEach(function (box) {
      box.checked = !!want[box.getAttribute("data-mic")];
    });
    selectedMics = ids.slice();
  }

  function selectedMicsFromUI() {
    var boxes = document.querySelectorAll("#micToggles input[data-mic]");
    var out = [];
    boxes.forEach(function (b) {
      if (b.checked) out.push(b.getAttribute("data-mic"));
    });
    if (!out.length) {
      applyImageMicTicks();
      return imageMicDefaults().slice();
    }
    return out;
  }

  function scheduleImagesFetch(delayMs) {
    if (currentView !== "space") return;
    if (imagesFetchTimer) clearTimeout(imagesFetchTimer);
    var ms = delayMs == null ? imagesFetchDelayMs : delayMs;
    imagesFetchTimer = setTimeout(fetchImages, ms);
  }

  var imagesReq = 0;
  async function fetchImages() {
    selectedMics = selectedMicsFromUI();
    /* Room spots become mic_x_* the same way Play does. Stand scenes omit those keys. */
    var body = Object.assign({}, heardMix(state), { mics: selectedMics });
    var req = ++imagesReq;
    try {
      var res = await fetch("/api/images", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      if (req !== imagesReq) return;
      noteHttp(res);
      if (!res.ok) throw new Error("HTTP " + res.status);
      imagesCache = await res.json();
      toastWarnings(imagesCache);
      if (req !== imagesReq) return;
      ensureImageView();
      applyImageView();
      /* Layout may still settle after fetch — resize+apply again next frames */
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          if (currentView !== "space") return;
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
    if (currentView !== "space") return;
    var n = imagesCache.count || (imagesCache.lattice && imagesCache.lattice.length) || 0;
    var mics = (imagesCache.selected_mics || []).join("+") || "C";
    if (liveMetresImg) {
      var hn = imagesCache.hadamard_n || n;
      liveMetresImg.textContent =
        n + " images · " + hn + " FDN lines · mics " + mics +
        " · c=" + (imagesCache.c || 340) + " m/s" +
        (imagesCache.source_b ? " · two clouds" : "");
    }
    if (!imageView) ensureImageView();
    if (!imageView) return;
    var mode = spaceMode === "legs" ? "legs" : (spaceMode === "paths" ? "paths" : "lattice");
    try {
      imageView.setMode(mode);
      imageView.setData(imagesCache);
    } catch (err) {
      if (statusEl) {
        statusEl.textContent = "Images rebuild: " + String(err && err.message ? err.message : err);
      }
    }
  }

  function syncSpaceModeUI() {
    document.querySelectorAll(".space-mode-chip").forEach(function (btn) {
      var on = btn.getAttribute("data-space-mode") === spaceMode;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    var camHint = "Drag to orbit · right-drag or Shift to pan · scroll to zoom · double-click to reset";
    if (spaceMode === "legs") {
      if (imageViewTitle) imageViewTitle.textContent = "Last legs into the mic";
    } else if (spaceMode === "paths") {
      if (imageViewTitle) imageViewTitle.textContent = "In-room specular paths";
    } else {
      if (imageViewTitle) imageViewTitle.textContent = "Mirrored-room lattice";
    }
    if (imageViewHint) imageViewHint.textContent = camHint;
  }

  function syncPolarPageUI() {
    document.querySelectorAll("[data-polar-page]").forEach(function (btn) {
      var on = btn.getAttribute("data-polar-page") === polarPage;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    var combined = document.getElementById("polarCombined");
    var host = document.getElementById("polarEachHost");
    var speakers = document.getElementById("polarSpeakers");
    if (combined) combined.hidden = polarPage !== "combined";
    if (host) host.hidden = polarPage !== "each";
    if (speakers) speakers.hidden = polarPage !== "speakers";
    placePolarTrio();
    if (polarPage === "speakers") drawSpeakerPolar(polarCache);
  }

  var polarCache = null;
  function drawSpeakerPolar(data) {
    var canvas = document.getElementById("polarSpeakerCanvas");
    if (!canvas || !data || !data.speaker_l || !data.speaker_r) return;
    if (!data.speaker_l.length || !data.speaker_r.length) return;
    var ratio = Math.min(window.devicePixelRatio || 1, 2);
    var rect = canvas.getBoundingClientRect();
    var cssW = rect.width > 2 ? rect.width : 900;
    var cssH = rect.height > 2 ? rect.height : 420;
    var w = Math.max(2, Math.floor(cssW * ratio));
    var h = Math.max(2, Math.floor(cssH * ratio));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    var ctx = canvas.getContext("2d");
    ctx.fillStyle = "#0c0e14";
    ctx.fillRect(0, 0, w, h);
    var grids = [data.speaker_l, data.speaker_r];
    var names = ["Speaker L", "Speaker R"];
    var peak = 1e-12;
    grids.forEach(function (grid) {
      grid.forEach(function (row) {
        row.forEach(function (v) {
          if (v > peak) peak = v;
        });
      });
    });
    grids.forEach(function (grid, side) {
      var nB = grid.length;
      var nAz = grid[0].length;
      var cx = w * (side === 0 ? 0.27 : 0.73);
      var cy = h * 0.54;
      var R = Math.min(w * 0.2, h * 0.36);
      ctx.strokeStyle = "rgba(255,255,255,0.08)";
      ctx.lineWidth = 1;
      [0.25, 0.5, 0.75, 1].forEach(function (f) {
        ctx.beginPath();
        ctx.arc(cx, cy, R * f, 0, Math.PI * 2);
        ctx.stroke();
      });
      var bi, ai, k, theta, g, sx, sy;
      for (bi = 0; bi < nB; bi++) {
        ctx.beginPath();
        for (ai = 0; ai <= nAz; ai++) {
          k = ai % nAz;
          theta = (k / nAz) * Math.PI * 2;
          g = Math.max(0, Number(grid[bi][k]) / peak);
          sx = cx + R * g * Math.sin(theta);
          sy = cy - R * g * Math.cos(theta);
          if (ai === 0) ctx.moveTo(sx, sy);
          else ctx.lineTo(sx, sy);
        }
        if (window.SpectrumColors) ctx.strokeStyle = SpectrumColors.forIndex(bi, nB).css;
        else ctx.strokeStyle = "hsl(" + Math.round(255 * bi / Math.max(1, nB - 1)) + ",78%,58%)";
        ctx.lineWidth = bi === nB - 1 ? 2 : 1.25;
        ctx.stroke();
      }
      ctx.fillStyle = "#e8e6df";
      ctx.font = Math.round(13 * ratio) + "px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(names[side], cx, Math.round(22 * ratio));
    });
  }

  function placePolarTrio() {
    var trio = document.getElementById("micPolarTrio");
    if (!trio) return;
    var each = document.getElementById("micEach");
    var host = document.getElementById("polarEachHost");
    if (currentView === "polar" && polarPage === "each" && host) {
      if (trio.parentElement !== host) host.appendChild(trio);
    } else if (each) {
      var foot = document.getElementById("micEachFoot");
      if (foot && foot.parentElement === each) {
        if (trio.parentElement !== each || trio.nextElementSibling !== foot) {
          each.insertBefore(trio, foot);
        }
      } else if (trio.parentElement !== each) {
        each.appendChild(trio);
      }
    }
  }


  var micDesk = null;
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
        if (micHero && micHero.resize) micHero.resize();
      });
    });
    ro.observe(host);
    var grid = document.querySelector(".mic-desk-grid");
    if (grid) ro.observe(grid);
    var wide = document.getElementById("stageWide");
    if (wide) ro.observe(wide);
  })();



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
          if (currentView === "mic") {
            ensureMicHero();
            if (micHero && micHero.resize) micHero.resize();
          }
          if (currentView === "polar" && polarPage === "combined" && polarView && polarView.resize) {
            polarView.resize();
          }
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

  function syncHadamardUI() {
    var n = state.hadamard_n || 32;
    var live = !!(window.LiveFDN && LiveFDN.isRunning && LiveFDN.isRunning());
    document.querySelectorAll(".hadamard-chip").forEach(function (btn) {
      var bn = parseInt(btn.getAttribute("data-n"), 10);
      var renderOnly = bn === 64 || bn === 128;
      btn.classList.toggle("active", bn === n);
      btn.disabled = !!(live && renderOnly);
      if (renderOnly) btn.title = "Render only";
      else if (btn.title === "Render only") btn.title = "";
    });
    var ro = document.getElementById("hadamardReadout");
    if (ro) ro.textContent = n + " images · " + n + " FDN lines";
  }

  function setHadamardN(n) {
    var allowed = [8, 16, 32, 64, 128];
    if (allowed.indexOf(n) < 0) n = 32;
    state.hadamard_n = n;
    syncHadamardUI();
    syncUI();
    if (currentView === "space") scheduleImagesFetch(120);
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
    var row = micCatalogue[id || "ShureSM57"];
    return row && row.capsule ? row.capsule : null;
  }

  function catalogueReady() {
    for (var k in micCatalogue) return true;
    return false;
  }

  /* B4: a figure-8 Side in Measured must not stay on a cardioid model. */
  function ensureFig8Model(slot) {
    if (state["family_" + slot] !== "bi") return;
    var id = state["mic_preset_" + slot] || "ShureSM57";
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
      var id = state["mic_preset_" + slot] || "ShureSM57";
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
      state["pattern_" + cap] = RoomMath.derivePattern(state["family_" + cap], state["polar_" + cap]);
    });
  }

  function writeFamily(cap, value) {
    if (patternControlsLocked() || state.mic_setup === "binaural") return;
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
    var row = micCatalogue[id || "ShureSM57"];
    var name = row && row.display_name ? String(row.display_name) : "Shure SM57";
    var cut = name.split("\u2014")[0].split("\u2013")[0].split(" - ")[0].trim();
    return cut || "Shure SM57";
  }

  function presetLawPhrase(id) {
    var law = capsuleOf(id) || { family: "cardioid", polar: 0.5 };
    var label = (window.RoomMath && RoomMath.polarLabel)
      ? RoomMath.polarLabel(law.family, law.polar)
      : "Cardioid";
    return presetShort(id) + " = " + String(label).toLowerCase();
  }

  function presetOwnPhrase() {
    var l = state.mic_preset_l || "ShureSM57";
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

  var toastTimer = null;
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

  function placeRoomControls() {
    placeProxR();
    function nodes(ids) {
      var out = [];
      ids.forEach(function (id) {
        var el = document.getElementById(id);
        if (el) out.push(el);
      });
      return out;
    }
    function restore(list, parent) {
      if (!parent) return;
      list.forEach(function (el) { parent.appendChild(el); });
    }
    function into(list, cap) {
      var host = document.querySelector('[data-room-spot="' + cap + '"] [data-room-park]');
      if (!host) return;
      list.forEach(function (el) { host.appendChild(el); });
    }
    var centreNodes = nodes(["centrePresetRow", "micHpfCentreRow", "micHpfCentreHint", "proxCRow", "centrePatternBlock"]);
    if (stripIsRoom("c")) into(centreNodes, "c");
    else restore(centreNodes, document.getElementById("centreMicChoice"));
    var right = document.getElementById("sideSplitR");
    if (!right) return;
    if (stripIsRoom("r") && splitOn()) into([right], "r");
    else restore([right], document.getElementById("sidePatternSplit"));
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
      polSOut.textContent = RoomMath.polarLabel(state.family_l, state.polar_l);
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
      /* D20. ortf and ortf_c share the pair. C off is ORTF; C on is ORTF + C. */
      if (id === "ortf" || id === "ortf_c") {
        var cOn = state.third_mic !== "off";
        if ((id === "ortf") === cOn) continue;
      }
      return id;
    }
    return "custom";
  }

  var _binauralStash = null;

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
    var sideId = state.mic_preset_l || "ShureSM57";
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

  function heroEnabled() {
    var same = state.mic_preset_l === state.mic_preset_c
      && state.mic_preset_c === state.mic_preset_r
      && state.pattern_l === state.pattern_c
      && state.pattern_c === state.pattern_r
      && state.family_l === state.family_c
      && state.family_c === state.family_r;
    if (same) return { L: false, C: true, R: false, sum: false };
    return { L: true, C: true, R: true, sum: false };
  }

  function ensureMicHero() {
    if (micHero || !window.PolarFieldView) return micHero;
    var canvas = document.getElementById("micPolarHero");
    if (!canvas) return null;
    micHero = new PolarFieldView({
      canvas: canvas,
      wrap: document.getElementById("micHeroWrap"),
      meta: document.getElementById("micHeroMeta"),
      isolated: true,
      useBase: true,
      enabled: { L: false, C: false, R: false, sum: false, base: true },
      getState: function () { return state; }
    });
    return micHero;
  }

  var polarTimer = null;
  var polarReq = 0;
  function schedulePolar() {
    if (currentView !== "mic" && currentView !== "polar") return;
    if (polarTimer) clearTimeout(polarTimer);
    polarTimer = setTimeout(refreshPolar, 120);
  }
  async function refreshPolar() {
    polarTimer = null;
    var seq = ++polarReq;
    if (micDesk && micDesk.setPolarStatus) micDesk.setPolarStatus("pending");
    try {
      var body = Object.assign({}, state);
      body.n_az = 72;
      if (body.sy == null && body.my != null) body.sy = body.my;
      var res = await fetch("/api/polar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      noteHttp(res);
      if (!res.ok) throw new Error("HTTP " + res.status);
      var data = await res.json();
      toastWarnings(data);
      if (seq !== polarReq) return;
      if (!data.ok) throw new Error(data.error || "polar failed");
      polarCache = data;
      if (micDesk && micDesk.setPolar) micDesk.setPolar(data, "ok");
      if (polarPage === "speakers") drawSpeakerPolar(data);
      ensureMicHero();
      if (micHero) {
        micHero.enabled = { L: false, C: false, R: false, sum: false, base: true };
        micHero.setData(data);
      }
      if (polarView && polarView.setData) polarView.setData(data);
      var banner = document.getElementById("polarBanner");
      if (banner && data.assumed_note) banner.textContent = data.assumed_note;
    } catch (err) {
      if (seq === polarReq && micDesk && micDesk.setPolarStatus) micDesk.setPolarStatus("fail");
      var meta = document.getElementById("micHeroMeta");
      if (meta) meta.textContent = "Polar: " + String(err);
    }
  }

  function loadMicCatalogue() {
    fetch("/api/mic_presets").then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    }).then(function (data) {
      var groups = { MEASURED: [], ASSUMED: [] };
      micCatalogue = {};
      (data.presets || []).forEach(function (row) {
        if (!row || !row.mic_id) return;
        micCatalogue[row.mic_id] = row;
        var key = String(row.honesty || "").toUpperCase() === "MEASURED" ? "MEASURED" : "ASSUMED";
        groups[key].push(row);
      });
      function fill(sel, id) {
        if (!sel) return;
        sel.innerHTML = "";
        [["MEASURED", "Measured"], ["ASSUMED", "Assumed"]].forEach(function (pair) {
          if (!groups[pair[0]].length) return;
          var og = document.createElement("optgroup");
          og.label = pair[1];
          groups[pair[0]].forEach(function (row) {
            var opt = document.createElement("option");
            opt.value = row.mic_id;
            opt.textContent = row.display_name || row.mic_id;
            og.appendChild(opt);
          });
          sel.appendChild(og);
        });
        if (id && micCatalogue[id]) sel.value = id;
      }
      fill(document.getElementById("mic_preset_side"), state.mic_preset_l || "ShureSM57");
      fill(document.getElementById("mic_preset_l"), state.mic_preset_l || "ShureSM57");
      fill(document.getElementById("mic_preset_r"), state.mic_preset_r || state.mic_preset_l || "ShureSM57");
      fill(document.getElementById("mic_preset_centre"), state.mic_preset_c || "ShureSM57");
      if (patternFromPreset()) applyPresetLaw();
      paintMicModel();
      syncPatternChrome();
    }).catch(function () {
      showToast("Mic presets failed");
    });
  }

  function syncUI() {
    if (syncRaf) return;
    syncRaf = requestAnimationFrame(function () {
      syncRaf = 0;
      syncUINow();
    });
  }

  function balanceLabel(v) {
    v = Number(v) || 0;
    if (Math.abs(v) < 0.001) return "Centre";
    if (v <= -0.995) return "A";
    if (v >= 0.995) return "B";
    return (v > 0 ? "+" : "") + v.toFixed(2);
  }

  function paintSourceSplit() {
    var oneBtn = document.getElementById("oneSourceBtn");
    var twoBtn = document.getElementById("twoSourceBtn");
    var extra = document.getElementById("twoSourceExtra");
    var can = wavChannels >= 2;
    if (oneBtn) {
      oneBtn.classList.toggle("active", !state.two_sources);
      oneBtn.setAttribute("aria-pressed", state.two_sources ? "false" : "true");
    }
    if (twoBtn) {
      twoBtn.disabled = !can;
      twoBtn.classList.toggle("active", !!state.two_sources && can);
      twoBtn.setAttribute("aria-pressed", state.two_sources && can ? "true" : "false");
    }
    if (extra) extra.hidden = !state.two_sources;
    var mir = document.getElementById("mirrorB");
    if (mir) mir.checked = !!state.mirror_b;
    var bal = document.getElementById("sourceBalance");
    var balOut = document.getElementById("sourceBalanceOut");
    if (bal && document.activeElement !== bal) bal.value = String(state.source_balance || 0);
    if (balOut) balOut.textContent = balanceLabel(state.source_balance || 0);
  }

  function wavChannelCount(file) {
    return file.slice(0, 128).arrayBuffer().then(function (ab) {
      var u = new Uint8Array(ab);
      if (u.length < 24) return 1;
      if (u[0] !== 82 || u[1] !== 73 || u[2] !== 70 || u[3] !== 70) return 1;
      if (u[12] === 102 && u[13] === 109 && u[14] === 116 && u[15] === 32) {
        return u[22] | (u[23] << 8);
      }
      var i = 12;
      while (i + 8 <= u.length) {
        var id = String.fromCharCode(u[i], u[i + 1], u[i + 2], u[i + 3]);
        var sz = u[i + 4] | (u[i + 5] << 8) | (u[i + 6] << 16) | (u[i + 7] << 24);
        if (id === "fmt ") {
          var chOff = i + 10;
          if (chOff + 1 < u.length) return u[chOff] | (u[chOff + 1] << 8);
        }
        if (sz <= 0 || i + 8 + sz > u.length) break;
        i += 8 + sz + (sz & 1);
      }
      return 1;
    });
  }

  /* Keep in sync with air_iso.rh_pct_from_slider.
     Right is drier. 0.35 is the climate RH, clamped up to the treble peak.
     1.0 is that peak (8–16 kHz mean loss). Never drier than the peak. */
  var AIR_RH_NOMINAL = 0.35;
  var AIR_RH_WET = 90;
  var AIR_RH_PEAK = { 20: 21.7, 22: 19.2 };
  var AIR_PRESET_RH = {
    studio_20C_50RH: 50,
    dry_20C_20RH: 20,
    humid_20C_80RH: 80,
    warm_22C_40RH: 40
  };
  var AIR_PRESET_T = {
    studio_20C_50RH: 20,
    dry_20C_20RH: 20,
    humid_20C_80RH: 20,
    warm_22C_40RH: 22
  };
  function airPeakRh(climate) {
    var t = AIR_PRESET_T[climate];
    if (t == null) t = 20;
    var peak = AIR_RH_PEAK[t];
    return peak == null ? AIR_RH_PEAK[20] : peak;
  }
  function airRhPct(humidity, climate) {
    var h = Number(humidity);
    if (!(h > 0)) return null;
    if (h > 1) h = 1;
    var preset = AIR_PRESET_RH[climate];
    if (preset == null) preset = AIR_PRESET_RH.studio_20C_50RH;
    var peak = airPeakRh(climate);
    var anchor = Math.max(preset, peak);
    if (h <= AIR_RH_NOMINAL) {
      return AIR_RH_WET + (h / AIR_RH_NOMINAL) * (anchor - AIR_RH_WET);
    }
    return anchor + ((h - AIR_RH_NOMINAL) / (1 - AIR_RH_NOMINAL)) * (peak - anchor);
  }
  function fmtRh(rh) {
    var r = Math.round(rh * 10) / 10;
    if (Math.abs(r - Math.round(r)) < 0.05) return String(Math.round(r));
    return r.toFixed(1);
  }
  function paintHumidityReadout(el, out) {
    var rh = airRhPct(state.humidity, state.air_climate);
    var tip = rh == null ? "Air off" : ("Relative humidity " + fmtRh(rh) + "%");
    if (out) out.textContent = rh == null ? "off" : (fmtRh(rh) + "% RH");
    if (el) el.title = tip;
    var label = document.getElementById("humidity_label");
    if (label) label.title = tip;
  }

  var slRoomRefreshTimer = 0;

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

    var numeric = ["W","H","L","space","car_omni","fdn_g","ir_length_ms","humidity","air_lp","air_shelf","decay_s"];
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
    var parity = document.getElementById("reaktor_parity");
    if (parity) parity.checked = !!state.reaktor_parity;
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
            ? RoomMath.polarLabel(state[keyF], state[keyP])
            : Number(state[keyP] || 0).toFixed(2);
        }
        if (fam) fam.disabled = state.mic_setup === "binaural";
        if (pol) pol.disabled = state.mic_setup === "binaural" || state[keyF] === "bi";
        if (window.RoomMath && RoomMath.derivePattern) {
          state["pattern_" + cap] = RoomMath.derivePattern(state[keyF], state[keyP]);
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
      setM("mic_proximity", state.mic_proximity, 2);
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
    paintRouting();
    syncBinauralChrome();
    syncPatternChrome();
    syncMicEach();
    syncFeedbackRow();
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
    paintMicSetupLink();
    scheduleSetupSave();
  }

  function placeScaleMargin(axis) {
    return Math.max(0.3, 0.1 * axis);
  }

  function placeScaleInset(v, axis) {
    var lo = placeScaleMargin(axis);
    var hi = axis - lo;
    if (!(hi >= lo)) return v;
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
  }

  function placeScaleKey(st, key, ratio, axis) {
    var v = st[key];
    if (v == null || v === "" || !isFinite(Number(v))) return;
    st[key] = placeScaleInset(Number(v) * ratio, axis);
  }

  /* Positions on the axis that changed. Yaw stays. Unmirrored source B only. */
  function scaleRoomAxis(st, key, prev, next) {
    var ratio = next / prev;
    var keys = key === "W"
      ? ["sx", "mcx", "room_x", "room_l_x", "room_c_x", "room_r_x"]
      : key === "L"
        ? ["sz", "mcz", "room_z", "room_l_z", "room_c_z", "room_r_z"]
        : ["sy", "my", "room_y", "room_l_y", "room_c_y", "room_r_y", "my_l", "my_c", "my_r"];
    var i;
    for (i = 0; i < keys.length; i++) placeScaleKey(st, keys[i], ratio, next);
    if (!st.mirror_b) {
      placeScaleKey(st, key === "W" ? "sx_b" : key === "L" ? "sz_b" : "sy_b", ratio, next);
    }
  }

  function placeCapsuleXs(st, space) {
    var half = Number(space) * 0.5;
    var mcx = Number(st.mcx);
    if (st.mic_setup === "binaural") {
      var psi = ((Number(st.head_yaw_deg) || 0) * Math.PI) / 180;
      var rx = Math.cos(psi);
      return [mcx - half * rx, mcx + half * rx];
    }
    return [mcx - half, mcx + half];
  }

  /* Put Space back when the pair still sits inside (0, W).
     Slide the stand, then shorten Space, only when the pair is wider than the room.
     Parity keeps mcx at W/2. centre_dz is not touched. */
  function restoreSpaceAfterSize(st, spaceWant) {
    var want = Number(spaceWant);
    var W = Number(st.W);
    if (!isFinite(want) || want < 0 || !isFinite(W) || !(W > 0)) return;
    var xs = placeCapsuleXs(st, want);
    var a = Math.min(xs[0], xs[1]);
    var b = Math.max(xs[0], xs[1]);
    if (a > 0 && b < W) {
      st.space = want;
      return;
    }
    if (!(b - a > W)) return;
    if (!st.reaktor_parity) st.mcx = W * 0.5;
    st.space = Math.min(want, RoomMath.maxSpace(W, st.mcx));
  }

  function onRoomDim(key, val) {
    var prev = Number(state[key]);
    var next = Number(val);
    var spaceWant = state.space;
    state[key] = val;
    if (isFinite(prev) && prev > 0 && isFinite(next) && next > 0 && next !== prev) {
      scaleRoomAxis(state, key, prev, next);
    }
    Object.assign(state, RoomMath.clampRoom(state));
    restoreSpaceAfterSize(state, spaceWant);
    syncUI();
  }

  ["W","H","L"].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("input", function (e) {
      onRoomDim(id, parseFloat(e.target.value));
    });
  });
  var climatePick = document.getElementById("air_climate");
  if (climatePick) {
    climatePick.addEventListener("change", function (e) {
      state.air_climate = e.target.value || "studio_20C_50RH";
      syncUI();
    });
  }
  ["space","car_omni","fdn_g","ir_length_ms","humidity","air_lp","air_shelf"].forEach(function (id) {
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
  var decayEl = document.getElementById("decay_s");
  if (decayEl) {
    decayEl.addEventListener("input", function (e) {
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
    });
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

  var micSetupEl = document.getElementById("mic_setup");
  if (micSetupEl) {
    micSetupEl.addEventListener("change", function (e) {
      applyMicPreset(e.target.value, true);
    });
  }
  var headYawEl = document.getElementById("head_yaw");
  if (headYawEl) {
    headYawEl.addEventListener("input", function (e) {
      var v = parseFloat(e.target.value);
      if (!isFinite(v)) v = 0;
      state.head_yaw_deg = Math.max(-180, Math.min(180, v));
      syncUI();
    });
  }
  var headPresetEl = document.getElementById("binaural_preset");
  if (headPresetEl) {
    headPresetEl.addEventListener("change", function (e) {
      var id = e.target.value;
      if (!BINAURAL_SPACE_M[id]) id = "SADIE2_KU100";
      state.binaural_preset = id;
      if (state.mic_setup === "binaural") state.space = binauralEarSpace(id);
      syncUI();
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
  var implSel = document.getElementById("colour_impl");
  if (implSel) {
    implSel.addEventListener("change", function (e) {
      state.colour_impl = e.target.value === "fir" ? "fir" : "sos";
      scheduleLiveParams();
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
      syncUI();
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
  var familySide = document.getElementById("family_side");
  if (familySide) {
    familySide.addEventListener("change", function (e) {
      writeFamily("side", e.target.value);
    });
  }
  var polarSide = document.getElementById("polar_side");
  if (polarSide) {
    polarSide.addEventListener("input", function (e) {
      var v = parseFloat(e.target.value);
      if (!isFinite(v)) return;
      writePolar("side", v);
    });
  }
  var sideSplitEl = document.getElementById("side_split");
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
  function paintRouting() {
    ["array", "room", "master"].forEach(function (name) {
      var pre = document.getElementById("route_" + name + "_pre");
      var drive = document.getElementById("route_" + name + "_drive");
      var driveOut = document.getElementById("route_" + name + "_drive_out");
      var comp = document.getElementById("route_" + name + "_comp");
      var amt = document.getElementById("route_" + name + "_amount");
      var amtOut = document.getElementById("route_" + name + "_amount_out");
      var preVal = state["route_" + name + "_pre"] || "none";
      var compVal = state["route_" + name + "_comp"] || "off";
      if (pre && document.activeElement !== pre) pre.value = preVal;
      if (comp && document.activeElement !== comp) comp.value = compVal;
      if (drive) {
        if (document.activeElement !== drive) drive.value = String(state["route_" + name + "_drive"] || 0);
        drive.disabled = preVal === "none";
        if (driveOut) driveOut.textContent = Number(drive.value).toFixed(1);
      }
      if (amt) {
        if (document.activeElement !== amt) amt.value = String(state["route_" + name + "_amount"] || 0);
        amt.disabled = compVal === "off";
        if (amtOut) amtOut.textContent = String(Math.round(Number(amt.value)));
      }
    });
  }

  function bindRouting() {
    var panel = document.getElementById("routingPanel");
    if (!panel || panel._routeBound) return;
    panel._routeBound = true;
    function onRoute(e) {
      var id = e.target && e.target.id;
      if (!id || id.indexOf("route_") !== 0) return;
      var v = e.target.value;
      var prev = state[id];
      if (id.indexOf("_drive") > 0 || id.indexOf("_amount") > 0) state[id] = Number(v);
      else state[id] = v;
      if (id === "route_master_comp" && window.RRRouting && RRRouting.armMaster) {
        RRRouting.armMaster(state, prev);
      }
      syncUI();
      scheduleLiveParams();
    }
    panel.addEventListener("change", onRoute);
    panel.addEventListener("input", onRoute);
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
  bindCheck("align_horizontal", "align_horizontal");
  bindCheck("link_lr_yaw", "link_lr_yaw");
  bindCheck("mic_hp_on", "mic_hp_on");
  var sidePreset = document.getElementById("mic_preset_side");
  if (sidePreset) {
    sidePreset.addEventListener("change", function (e) {
      applyCapsulePreset(["l", "r"], e.target.value);
    });
  }
  var centrePreset = document.getElementById("mic_preset_centre");
  if (centrePreset) {
    centrePreset.addEventListener("change", function (e) {
      applyCapsulePreset(["c"], e.target.value);
    });
  }
  var presetL = document.getElementById("mic_preset_l");
  if (presetL) {
    presetL.addEventListener("change", function (e) {
      applyCapsulePreset(["l"], e.target.value);
    });
  }
  var presetR = document.getElementById("mic_preset_r");
  if (presetR) {
    presetR.addEventListener("change", function (e) {
      applyCapsulePreset(["r"], e.target.value);
    });
  }
  function refitDiagrams() {
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        if (micDesk && micDesk.redraw) micDesk.redraw();
        if (micDesk && micDesk.view3d && micDesk.view3d.resize) micDesk.view3d.resize();
        if (micHero && micHero.resize) micHero.resize();
        if (polarView && polarView.resize) polarView.resize();
      });
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
  var modeSel = document.getElementById("colour_mode");
  if (modeSel) {
    modeSel.addEventListener("change", function (e) {
      state.colour_mode = e.target.value || "MEASURED_SHELF";
      if (patternFromPreset(state.colour_mode)) applyPresetLaw();
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
  bindHpf("mic_hpf_sides", "mic_hpf_sides");
  bindHpf("mic_hpf_centre", "mic_hpf_centre");
  bindHpf("mic_hpf_r", "mic_hpf_r");
  function bindProx(id, flag) {
    var box = document.getElementById(id);
    if (!box) return;
    box.addEventListener("change", function (e) {
      state[flag] = !!e.target.checked;
      syncUI();
    });
  }
  bindProx("prox_l", "prox_l");
  bindProx("prox_c", "prox_c");
  bindProx("prox_r", "prox_r");
  ["mic_hp_hz", "mic_response_hz", "mic_proximity", "capsule_mm"].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("input", function (e) {
      var v = parseFloat(e.target.value);
      if (!isFinite(v)) return;
      state[id] = v;
      syncUI();
    });
  });

  function withImageView(fn) {
    ensureImageView();
    if (imageView) fn(imageView);
  }
  var spaceZoomOut = document.getElementById("spaceZoomOut");
  var spaceZoomIn = document.getElementById("spaceZoomIn");
  var spaceFit = document.getElementById("spaceFit");
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
  var viewSwitch = document.querySelector(".view-switch");
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
  var roomSizeChip = document.getElementById("roomSizeChip");
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
  var micAll = document.getElementById("micAll");
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

  var wavInput = document.getElementById("wavInput");
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
  var oneSourceBtn = document.getElementById("oneSourceBtn");
  var twoSourceBtn = document.getElementById("twoSourceBtn");
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
  var mirrorB = document.getElementById("mirrorB");
  if (mirrorB) {
    mirrorB.addEventListener("change", function (e) {
      state.mirror_b = !!e.target.checked;
      Object.assign(state, RoomMath.clampRoom(state));
      syncUI();
    });
  }
  var sourceBalance = document.getElementById("sourceBalance");
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

  if (renderBtn) {
    renderBtn.addEventListener("click", function () { doRender(); });
  }
  var snapBtn = document.getElementById("reaktorSnapshotBtn");
  if (snapBtn) {
    snapBtn.addEventListener("click", function () { applyReaktorSnapshot(); });
  }
  bindCheck("live_drag_render", "live_drag_render");
  bindCheck("shared_tail", "shared_tail");
  bindCheck("smooth", "smooth");
  bindCheck("phys_ceiling", "phys_ceiling");
  bindCheck("sub_hp", "sub_hp");
  var movementSlider = document.getElementById("movement");
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

  var PLACES = {
    studio: {
      W: 5.6, H: 2.8, L: 7.2,
      sx: 2.8, sz: 4.6, sy: 1.2, my: 1.2, mcx: 2.8, mcz: 1.55,
      space: 0.17, reaktor_parity: false, humidity: 0.35,
      /* Fresh Studio click is the boot decay. Measured 1.80 s, lock on. */
      decay_lock: true, decay_s: 1.8
    },
    club: {
      W: 14, H: 5.2, L: 22,
      sx: 7, sz: 14.5, sy: 1.6, my: 1.6, mcx: 7, mcz: 3.4,
      space: 0.25, reaktor_parity: false, humidity: 0.4,
      /* Fresh Club does not set decay. Boot stays 1.80 s, lock on. Printed, not retuned. */
      decay_lock: true, decay_s: 1.8
    }
  };

  /* Page after ORTF + /api/defaults. applyPlace clones this, then overlays the place. */
  var bootState = null;
  var placeChosen = false;
  var lastPlace = "";

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

  function paintPlaceChips() {
    var name = state._place || "";
    document.querySelectorAll("#placeRow [data-place]").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-place") === name);
    });
  }

  function paintMicSetupLink() {
    var link = document.getElementById("roomMicSetupLink");
    var setupEl = document.getElementById("mic_setup");
    if (!link || !setupEl) return;
    var opt = setupEl.options && setupEl.selectedIndex >= 0 ? setupEl.options[setupEl.selectedIndex] : null;
    var name = opt && opt.textContent ? opt.textContent : (state.mic_setup || "ORTF");
    link.textContent = "Mic setup: " + name + " ›";
  }

  function applyPlace(name) {
    placeChosen = true;
    resetToFresh();
    state._place = name;
    lastPlace = name;
    if (name === "hall") {
      applyReaktorSnapshot();
      return;
    }
    var p = PLACES[name];
    if (!p) return;
    Object.keys(p).forEach(function (k) { state[k] = p[k]; });
    Object.assign(state, RoomMath.clampRoom(state));
    syncHadamardUI();
    syncUI();
    if (statusEl) statusEl.textContent = name.charAt(0).toUpperCase() + name.slice(1) + " loaded. Play live or Render.";
  }

  document.querySelectorAll("#placeRow [data-place]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var name = btn.getAttribute("data-place");
      var label = name ? name.charAt(0).toUpperCase() + name.slice(1) : "place";
      if (!window.confirm("Load " + label + "? This resets mics, mix and surfaces.")) return;
      applyPlace(name);
    });
  });

  var liveBtn = document.getElementById("liveBtn");
  if (liveBtn) {
    liveBtn.addEventListener("click", async function () {
      if (window.LiveFDN && LiveFDN.isRunning()) {
        if (LiveFDN.noteDecay) LiveFDN.noteDecay(state.decay_s);
        LiveFDN.stop();
        liveBtn.classList.remove("live-on");
        liveBtn.textContent = "Play live";
        syncHadamardUI();
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
        if (previewAudio) {
          try { previewAudio.pause(); } catch (e) {}
        }
        var ok = await LiveFDN.start(wavFile, data);
        if (ok) {
          liveBtn.classList.add("live-on");
          liveBtn.textContent = "Stop live";
          syncHadamardUI();
        }
      } catch (err) {
        if (statusEl) statusEl.textContent = String(err);
      } finally {
        liveBtn.disabled = false;
      }
    });
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

  var SETUP_KEY = "rr2011.setup.v1";
  var setupSaveArmed = false;
  var setupBaseline = "";
  var setupSaveTimer = null;

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

  // Default Mic setup = ORTF ±55°. Colour preset is SM57 and does not move yaw.
  var saveSetupBtn = document.getElementById("saveSetupBtn");
  if (saveSetupBtn) saveSetupBtn.addEventListener("click", downloadSetup);
  var loadSetupFile = document.getElementById("loadSetupFile");
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
  var roomMicSetupLink = document.getElementById("roomMicSetupLink");
  if (roomMicSetupLink) {
    roomMicSetupLink.addEventListener("click", function () { setView("mic"); });
  }

  bindDesk();
  bindRouting();
  applyMicPreset(state.mic_setup || "ortf", false);
  migrateRoomState(state);
  snapshotBoot();
  loadServerDefaults();
  loadMicCatalogue();
  setView("edit");
})();
