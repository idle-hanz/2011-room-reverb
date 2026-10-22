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
    ms_classic: { space: 0.05, toe_half_deg: 90, car_omni: 1, polar: ["L", "C", "R"],
      pattern_l: "fig8", pattern_c: "cardioid", pattern_r: "fig8",
      family_l: "bi", family_c: "cardioid", family_r: "bi",
      polar_l: 0.5, polar_c: 0.5, polar_r: 0.5,
      yaw_l_deg: -90, yaw_c_deg: 0, yaw_r_deg: 90 },
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
    mic_hp_on: false, mic_hp_hz: 40, mic_response_hz: 10000, mic_proximity: 0.25,
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
    decay_s: 1.8, decay_lock: true,
    solo_direct: false, solo_fdn: false, solo_early: false, solo_dry: false,
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
  var hallSnapshot = false; /* 2011 / Hall snapshot loaded. Not posted. */
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
  var renderQueued = false;

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
    return (sum > 0 ? "+" : "") + sum.toFixed(1);
  }

  function stripLinear(src, key) {
    if (src["mute_" + key]) return 0;
    return gainFromDb(dbFromTravel(src["fader_" + key]), src["trim_" + key]);
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
    o.mic_gain_l = stripLinear(src, "l");
    o.mic_gain_c = src.mic_setup === "binaural" ? 0 : stripLinear(src, "c");
    o.mic_gain_r = stripLinear(src, "r");
    o.mic_pan_l = src.stereo_mic ? -1 : src.pan_l;
    o.mic_pan_c = src.pan_c;
    o.mic_pan_r = src.stereo_mic ? 1 : src.pan_r;
    o.mic_phase_l = src.phase_l;
    o.mic_phase_c = src.phase_c;
    o.mic_phase_r = src.phase_r;
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
  }

  var DESK_FADERS = ["l", "c", "r", "direct", "fdn", "early", "dry"];

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

  function paintDesk() {
    var i, key, fader, trim, pan, read, phase, mute, knob, needle;
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
      phase = document.getElementById("phase_" + cap);
      var locked = state.stereo_mic && cap !== "c";
      if (pan) {
        pan.disabled = locked;
        if (document.activeElement !== pan) {
          pan.value = locked ? (cap === "l" ? -1 : 1) : state["pan_" + cap];
        }
        if (pan.parentElement) {
          var pv = Number(pan.value);
          pan.parentElement.style.setProperty("--needle", (-140 + ((pv + 1) / 2) * 280).toFixed(1) + "deg");
        }
      }
      if (phase) phase.setAttribute("aria-pressed", state["phase_" + cap] < 0 ? "true" : "false");
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
    var stereoBtn = document.getElementById("stereoMicBtn");
    if (stereoBtn) stereoBtn.setAttribute("aria-pressed", state.stereo_mic ? "true" : "false");
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
          setFader(key, fader.value, false);
          syncUI();
        });
      }
      if (trim) {
        trim.addEventListener("input", function () {
          setTrim(key, trim.value, false);
          syncUI();
        });
      }
      if (mute) {
        mute.addEventListener("click", function () {
          state["mute_" + key] = !state["mute_" + key];
          syncUI();
        });
      }
      if (read) {
        read.addEventListener("click", function () {
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
      var phase = document.getElementById("phase_" + cap);
      if (pan) {
        pan.addEventListener("input", function () {
          if (state.stereo_mic && cap !== "c") return;
          state["pan_" + cap] = Math.max(-1, Math.min(1, Number(pan.value)));
          syncUI();
        });
      }
      if (phase) {
        phase.addEventListener("click", function () {
          state["phase_" + cap] = state["phase_" + cap] < 0 ? 1 : -1;
          syncUI();
        });
      }
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
      var data = await res.json();
      if (!data.ok) return;
      if (window.LiveFDN && LiveFDN.isRunning()) return;
      if (data.mean_delay_ms) state._mean_delay_ms = data.mean_delay_ms;
      if (!state.decay_lock && !decayFromUser && data.decay_s > 0.05) {
        applyDecayReadout(data.decay_s);
      }
    } catch (err) {
      /* Feedback still drives the render. The number fills in on the next edit. */
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
      var data = await res.json();
      if (!data.ok) {
        if (statusEl) statusEl.textContent = data.error || "live_params failed";
        return;
      }
      if (data.mean_delay_ms) state._mean_delay_ms = data.mean_delay_ms;
      if (!state.decay_lock && !decayFromUser && data.decay_s > 0.05) {
        applyDecayReadout(data.decay_s);
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
    if (currentView !== "space") return;
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
      return;
    }
    var n = imagesCache.count || (imagesCache.lattice && imagesCache.lattice.length) || 0;
    var mics = (imagesCache.selected_mics || []).join("+") || "C";
    if (liveMetresImg) {
      var hn = imagesCache.hadamard_n || n;
      liveMetresImg.textContent =
        n + " images · " + hn + " FDN lines · mics " + mics +
        " · c=" + (imagesCache.c || 340) + " m/s" +
        (imagesCache.source_b ? " · two clouds" : "");
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
    if (combined) combined.hidden = polarPage !== "combined";
    if (host) host.hidden = polarPage !== "each";
    placePolarTrio();
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
      onChange: syncUI,
      onPolar: function (cap, value) { writePolar(cap, value); },
      RoomMath: window.RoomMath
    });
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
      room: view === "edit" || view === "source" || view === "space" || view === "surfaces",
      listen: view === "mic" || view === "polar",
      mics: view === "mic",
      preview: view === "edit" || view === "source" || view === "mix" || view === "surfaces",
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
    if (layout) layout.classList.toggle("mic-wide", isMic);
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
    if (currentView === "space") scheduleImagesFetch(120);
  }

  function sidesDiffer() {
    if (state.family_l !== state.family_r) return true;
    if (Math.abs(Number(state.polar_l) - Number(state.polar_r)) > 0.001) return true;
    if ((state.mic_preset_l || "") !== (state.mic_preset_r || "")) return true;
    return false;
  }

  function msSetup() {
    return state.mic_setup === "ms_classic" || !!state.ms_decode;
  }

  function splitOn() {
    if (msSetup()) return false;
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

  function applyPresetLaw() {
    if (state.mic_setup === "binaural") return;
    ["l", "c", "r"].forEach(function (slot) {
      var id = state["mic_preset_" + slot] || "ShureSM57";
      var law = capsuleOf(id) || { pattern: "cardioid", family: "cardioid", polar: 0.5 };
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
      tick.checked = split && !ms;
      tick.disabled = ms || binaural;
    }
    if (hint) hint.textContent = ms ? "Per-side jobs in M/S arrive with the S-MIX desk" : "";
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
    if (shared) shared.hidden = !showPattern || (split && !ms);
    if (sharedPreset) sharedPreset.hidden = !showPreset || (split && !ms);
    if (splitBox) splitBox.hidden = !split || ms;
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
      if (!!state.ms_decode !== (id === "ms_classic")) continue;
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
    state.ms_decode = id === "ms_classic";
    state.preset_owns_pattern = false;
    sideSplitUser = false;
    if (state.colour_mode === "MEASURED_SHELF" && (id === "ab_omni" || id === "ms" || id === "ms_classic")) {
      state.colour_mode = "ASSUMED_TOYS";
      var switched = id === "ab_omni" ? "AB omni" : (id === "ms" ? "MS" : "MS classic");
      showToast(switched + " is not the measured preset pattern. Colour is now User defined.");
    } else if (state.colour_mode === "MEASURED_SHELF" || state.colour_mode === "BYPASS") {
      applyPresetLaw();
    }
    var divergEl = document.getElementById("diverg");
    if (divergEl) divergEl.value = String(state.diverg);
    setPolarMics(p.polar);
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

  function paintMicModel() {
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
    state.mic_hpf_engaged = !!(state.mic_hpf_sides || state.mic_hpf_centre);
    var sideRow = micCatalogue[sideId];
    var centreRow = micCatalogue[centreId];
    var honesty = "MEASURED";
    if ((sideRow && String(sideRow.honesty).toUpperCase() === "ASSUMED")
      || (centreRow && String(centreRow.honesty).toUpperCase() === "ASSUMED")) {
      honesty = "ASSUMED";
    }
    if (badge) {
      badge.textContent = honesty;
      badge.className = "honesty-badge honesty-" + honesty.toLowerCase();
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
    state.mic_hpf_engaged = !!(state.mic_hpf_sides || state.mic_hpf_centre);
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
    try {
      var body = Object.assign({}, state);
      body.n_az = 72;
      if (body.sy == null && body.my != null) body.sy = body.my;
      var res = await fetch("/api/polar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      var data = await res.json();
      if (seq !== polarReq) return;
      if (!data.ok) throw new Error(data.error || "polar failed");
      if (micDesk && micDesk.setPolar) micDesk.setPolar(data);
      ensureMicHero();
      if (micHero) {
        micHero.enabled = { L: false, C: false, R: false, sum: false, base: true };
        micHero.setData(data);
      }
      if (polarView && polarView.setData) polarView.setData(data);
      var banner = document.getElementById("polarBanner");
      if (banner && data.assumed_note) banner.textContent = data.assumed_note;
    } catch (err) {
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
    }).catch(function () {});
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

  function syncUINow() {
    if (wavChannels < 2) state.two_sources = false;
    var geo = RoomMath.compute(state);
    Object.assign(state, geo.state);
    var spaceEl = document.getElementById("space");
    if (spaceEl) spaceEl.max = Math.max(0.01, geo.max_space);

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
        liveMetresMic.textContent =
          "space " + fmt(state.space) + " m · C " +
          ((state.centre_dz || 0) * 100).toFixed(0) + " cm · " +
          fmt(state.my) + " m high";
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
    paintDecayHint();
    syncBinauralChrome();
    syncPatternChrome();
    syncMicEach();
    syncFeedbackRow();
    scheduleLiveParams();
    scheduleDecayPreview();
    schedulePolar();
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
      state.mic_hpf_engaged = !!(state.mic_hpf_sides || state.mic_hpf_centre);
      syncUI();
    });
  }
  bindHpf("mic_hpf_sides", "mic_hpf_sides");
  bindHpf("mic_hpf_centre", "mic_hpf_centre");
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
      polarPage = m === "each" ? "each" : "combined";
      if (currentView !== "polar") setView("polar");
      syncPolarPageUI();
      requestAnimationFrame(function () {
        if (polarPage === "combined" && polarView && polarView.resize) polarView.resize();
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

  document.querySelectorAll("#micToggles input[data-mic]").forEach(function (box) {
    box.addEventListener("change", function () {
      selectedMics = selectedMicsFromUI();
      scheduleImagesFetch(120);
    });
  });
  var micAll = document.getElementById("micAll");
  if (micAll) {
    micAll.addEventListener("click", function () {
      document.querySelectorAll("#micToggles input[data-mic]").forEach(function (b) {
        b.checked = true;
      });
      selectedMics = ["L", "C", "R"];
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
      renderQueued = true;
      return;
    }
    renderBusy = true;
    if (renderBtn) renderBtn.disabled = true;
    if (statusEl) statusEl.textContent = "Rendering…";
    var fd = new FormData();
    fd.append("file", wavFile, wavFile.name);
    fd.append("params_json", JSON.stringify(heardMix(state)));
    try {
      var res = await fetch("/api/render", { method: "POST", body: fd });
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
      if (renderQueued) {
        renderQueued = false;
        doRender();
      }
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

  var PLACES = {
    studio: {
      W: 5.6, H: 2.8, L: 7.2,
      sx: 2.8, sz: 4.6, sy: 1.2, my: 1.2, mcx: 2.8, mcz: 1.55,
      space: 0.17, reaktor_parity: false, humidity: 0.35
    },
    club: {
      W: 14, H: 5.2, L: 22,
      sx: 7, sz: 14.5, sy: 1.6, my: 1.6, mcx: 7, mcz: 3.4,
      space: 0.25, reaktor_parity: false, humidity: 0.4
    }
  };

  function applyPlace(name) {
    if (name === "hall") {
      applyReaktorSnapshot();
      return;
    }
    var p = PLACES[name];
    if (!p) return;
    hallSnapshot = false;
    Object.keys(p).forEach(function (k) { state[k] = p[k]; });
    Object.assign(state, RoomMath.clampRoom(state));
    syncHadamardUI();
    syncUI();
    if (statusEl) statusEl.textContent = name.charAt(0).toUpperCase() + name.slice(1) + " loaded. Play live or Render.";
  }

  document.querySelectorAll("#placeRow [data-place]").forEach(function (btn) {
    btn.addEventListener("click", function () { applyPlace(btn.getAttribute("data-place")); });
  });

  var liveBtn = document.getElementById("liveBtn");
  if (liveBtn) {
    liveBtn.addEventListener("click", async function () {
      if (window.LiveFDN && LiveFDN.isRunning()) {
        LiveFDN.stop();
        liveBtn.classList.remove("live-on");
        liveBtn.textContent = "Play live";
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
        var data = await res.json();
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
        }
      } catch (err) {
        if (statusEl) statusEl.textContent = String(err);
      } finally {
        liveBtn.disabled = false;
      }
    });
  }

  function loadServerDefaults() {
    fetch("/api/defaults").then(function (r) { return r.json(); }).then(function (data) {
      var d = data && data.defaults;
      if (!d) return;
      var skip = {
        space: 1, yaw_l_deg: 1, yaw_c_deg: 1, yaw_r_deg: 1,
        toe_half_deg: 1, diverg: 1, early_wet: 1, surfaces: 1,
        source_radiation_b: 1, source_yaw_b: 1, source_pitch_b: 1
      };
      Object.keys(d).forEach(function (k) {
        if (skip[k] || d[k] == null) return;
        if (Object.prototype.hasOwnProperty.call(state, k)) state[k] = d[k];
      });
      if (state.mic_setup && state.mic_setup !== "custom") applyMicPreset(state.mic_setup, false);
      else syncUI();
    }).catch(function () {});
  }

  // Default Mic setup = ORTF ±55°. Colour preset is SM57 and does not move yaw.
  bindDesk();
  applyMicPreset(state.mic_setup || "ortf", false);
  loadServerDefaults();
  loadMicCatalogue();
  setView("edit");
})();
