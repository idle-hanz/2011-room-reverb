/* Shared page state. The other app scripts use these names.
   RR.state is this same object. */
"use strict";
var RR = window.RR = window.RR || {};


var BINAURAL_SPACE_M = { SADIE2_KU100: 0.18, SADIE2_KEMAR: 0.18, THK_KU100_FF: 0.175 };
/* D-UI38. Idle 2026-10-23. L, C, and R boot on the U87 Ai cardioid. */
var DEFAULT_MIC = "NeumannU87AiCardioid";

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
  mic_preset_l: DEFAULT_MIC, mic_preset_c: DEFAULT_MIC, mic_preset_r: DEFAULT_MIC,
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
  sub_hp: true, offaxis_tail: false,
  /* Box posts the key. The server keeps the shoebox bytes. */
  room_shape: "box",
  /* Box only. On links left and right. A symmetric polygon stays paired and has no switch. */
  mirror_lr: true,
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
  /* ISO shelf still gives HF loss. diffusion_master −0.25 (Structure), clamp [−0.5, 0]. */
  humidity: 0.35, air_shelf: 1, air_climate: "studio_20C_50RH", diffusion_master: -0.25,
  live_drag_render: false, shared_tail: false,
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
var polarPage = "each"; /* each | combined | speakers */
var sideSplitUser = null; /* null derives from L vs R. Not posted. */
var splitHold = null; /* Split flag put aside while Stereo pair is ganged. */
/* third_mic C had at the moment it became Room. Client only. Not a state key. */
var cThirdBeforeRoom = null;
var hallSnapshot = false;
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

var liveParamsTimer = null;
var liveBusy = false;
var decayFromUser = false;

var SOLO_BUSES = [
  ["solo_direct", "direct_wet", "direct"],
  ["solo_fdn", "fdn_wet", "fdn"],
  ["solo_early", "early_wet", "early"]
];
/* Page flag. Not a server key. Off is today's dry_gain 0. */
var wetBypass = false;

var FADER_KNOTS = [
  [0.02, -60], [0.20, -24], [0.35, -12], [0.42, -6],
  [0.50, 0], [0.58, 3], [0.70, 6], [1, 12]
];

var msMicStash = null;
var pairStash = null;

var physTimer = null;
var physText = "";

var DESK_FADERS = ["l", "c", "r", "direct", "fdn", "early"];
var FADER_BOOT = { l: 0.5, c: 0.5, r: 0.5, direct: 0, fdn: 0.5, early: 0 };

var decayPreviewTimer = null;

var colourSurfacesViews = document.getElementById("colourSurfacesViews");
var colourSurfaces = null;

var polarView = null;
var micCatalogue = {};

var imagesReq = 0;

var polarSolo = null;

var polarCache = null;


var micDesk = null;

var toastTimer = null;

var _binauralStash = null;

var polarLinkBtn = document.getElementById("micPolarLink");

var polarTimer = null;
var polarReq = 0;

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

var slRoomRefreshTimer = 0;
var climatePick = document.getElementById("air_climate");
var decayEl = document.getElementById("decay_s");
var toeSlider = document.getElementById("toe_half_deg");

var micSetupEl = document.getElementById("mic_setup");
var headYawEl = document.getElementById("head_yaw");
var headPresetEl = document.getElementById("binaural_preset");
var implSel = document.getElementById("colour_impl");
var lamEl = document.getElementById("lambda_ref");
var familySide = document.getElementById("family_side");
var polarSide = document.getElementById("polar_side");
var sideSplitEl = document.getElementById("side_split");
var sidePreset = document.getElementById("mic_preset_side");
var centrePreset = document.getElementById("mic_preset_centre");
var presetL = document.getElementById("mic_preset_l");
var presetR = document.getElementById("mic_preset_r");
var modeSel = document.getElementById("colour_mode");
var spaceZoomOut = document.getElementById("spaceZoomOut");
var spaceZoomIn = document.getElementById("spaceZoomIn");
var spaceFit = document.getElementById("spaceFit");
var viewSwitch = document.querySelector(".view-switch");
var roomSizeChip = document.getElementById("roomSizeChip");
var micAll = document.getElementById("micAll");

var wavInput = document.getElementById("wavInput");
var oneSourceBtn = document.getElementById("oneSourceBtn");
var twoSourceBtn = document.getElementById("twoSourceBtn");
var mirrorB = document.getElementById("mirrorB");
var sourceBalance = document.getElementById("sourceBalance");
var snapBtn = document.getElementById("reaktorSnapshotBtn");
var movementSlider = document.getElementById("movement");

var PLACES = {
  studio: {
    W: 5.6, H: 2.8, L: 7.2,
    sx: 2.8, sz: 4.6, sy: 1.2, my: 1.2, mcx: 2.8, mcz: 1.55,
    space: 0.17, humidity: 0.35,
    /* Fresh Studio click is the boot decay. Measured 1.80 s, lock on. */
    decay_lock: true, decay_s: 1.8
  },
  club: {
    W: 14, H: 5.2, L: 22,
    sx: 7, sz: 14.5, sy: 1.6, my: 1.6, mcx: 7, mcz: 3.4,
    space: 0.25, humidity: 0.4,
    /* Fresh Club does not set decay. Boot stays 1.80 s, lock on. Printed, not retuned. */
    decay_lock: true, decay_s: 1.8
  }
};

/* Page after ORTF + /api/defaults. applyPlace clones this, then overlays the place. */
var bootState = null;
var placeChosen = false;
var lastPlace = "";

var mirrorLr = document.getElementById("mirrorLr");

var liveBtn = document.getElementById("liveBtn");

var SETUP_KEY = "rr2011.setup.v1";
var setupSaveArmed = false;
var setupBaseline = "";
var setupSaveTimer = null;

// Default Mic setup = ORTF ±55°. Colour preset is the U87 Ai cardioid and does not move yaw.
var saveSetupBtn = document.getElementById("saveSetupBtn");
var loadSetupFile = document.getElementById("loadSetupFile");
var roomMicSetupLink = document.getElementById("roomMicSetupLink");
var wetBypassBtn = document.getElementById("wetBypass");
RR.state = state;
