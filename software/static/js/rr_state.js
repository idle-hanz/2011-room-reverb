/* Shared page state. The other app scripts use these names.
   RR.state is this same object. */
"use strict";
var RR = window.RR = window.RR || {};


var BINAURAL_SPACE_M = { SADIE2_KU100: 0.18, SADIE2_KEMAR: 0.18, THK_KU100_FF: 0.175 };

function S(name) {
  /* Page boot value from the shared settings table. `page` wins over `default`. */
  var table = window.RR_SETTINGS;
  var row = table && table.by_name && table.by_name[name];
  if (!row) throw new Error("missing setting " + name);
  var v = Object.prototype.hasOwnProperty.call(row, "page") ? row.page : row.default;
  if (v && typeof v === "object") return JSON.parse(JSON.stringify(v));
  return v;
}

/* D-UI38. Idle 2026-10-23. L, C, and R boot on the U87 Ai cardioid. */
var DEFAULT_MIC = S("mic_preset_l");

var state = {
  W: S("W"), H: S("H"), L: S("L"),
  /* K3 (locked 28 Sep 2026): source x 2.6 m, height 1.2 m → 29 distinct delays per bus. */
  sx: S("sx"), sz: S("sz"), mcx: S("mcx"), mcz: S("mcz"), my: S("my"), sy: S("sy"),
  link_heights: S("link_heights"),
  /* Table default matches an empty /api body. Boot calls applyMicPreset("ortf") so the page still opens at 17 cm, ±55°. */
  space: S("space"), diverg: S("diverg"), toe_half_deg: S("toe_half_deg"), car_omni: S("car_omni"),
  pattern_l: S("pattern_l"), pattern_c: S("pattern_c"), pattern_r: S("pattern_r"),
  family_l: S("family_l"), family_c: S("family_c"), family_r: S("family_r"),
  polar_l: S("polar_l"), polar_c: S("polar_c"), polar_r: S("polar_r"),
  yaw_l_deg: S("yaw_l_deg"), yaw_c_deg: S("yaw_c_deg"), yaw_r_deg: S("yaw_r_deg"),
  centre_dz: S("centre_dz"), align_horizontal: S("align_horizontal"), link_lr_yaw: S("link_lr_yaw"),
  pair_mode: S("pair_mode"), pan_law: S("pan_law"),
  mic_route_l: S("mic_route_l"), mic_route_c: S("mic_route_c"), mic_route_r: S("mic_route_r"),
  /* D20. Boot preset is ORTF, so the centre mic starts off. */
  third_mic: S("third_mic"), ms_s: S("ms_s"), ms_m: S("ms_m"), s_detached: S("s_detached"),
  width_l: S("width_l"), width_c: S("width_c"), width_r: S("width_r"),
  gain_exact_l: S("gain_exact_l"), gain_exact_c: S("gain_exact_c"), gain_exact_r: S("gain_exact_r"),
  link_mode: S("link_mode"), polar_radius: S("polar_radius"), desk_touched: S("desk_touched"),
  place_l: S("place_l"), place_c: S("place_c"), place_r: S("place_r"),
  room_slot: S("room_slot"), room_x: S("room_x"), room_z: S("room_z"), room_y: S("room_y"), room_yaw: S("room_yaw"),
  mic_hp_on: S("mic_hp_on"), mic_hp_hz: S("mic_hp_hz"), mic_response_hz: S("mic_response_hz"), mic_proximity: S("mic_proximity"),
  prox_l: S("prox_l"), prox_c: S("prox_c"), prox_r: S("prox_r"),
  capsule_mm: S("capsule_mm"), ms_decode: S("ms_decode"),
  colour_mode: S("colour_mode"),
  colour_impl: S("colour_impl"),
  mic_preset_l: S("mic_preset_l"), mic_preset_c: S("mic_preset_c"), mic_preset_r: S("mic_preset_r"),
  mic_hpf_engaged: S("mic_hpf_engaged"),
  mic_hpf_sides: S("mic_hpf_sides"),
  mic_hpf_centre: S("mic_hpf_centre"),
  preset_owns_pattern: S("preset_owns_pattern"),
  mic_setup: S("mic_setup"),
  head_yaw_deg: S("head_yaw_deg"),
  binaural_preset: S("binaural_preset"),
  /* K4 (locked): early_wet is the early-bus enable (×fader). 1.0 so raising the early fader works at once. */
  early_wet: S("early_wet"), fdn_wet: S("fdn_wet"), direct_wet: S("direct_wet"), dry_gain: S("dry_gain"), fdn_g: S("fdn_g"), ir_length_ms: S("ir_length_ms"),
  decay_s: S("decay_s"), decay_lock: S("decay_lock"), smooth: S("smooth"), movement: S("movement"), phys_ceiling: S("phys_ceiling"),
  sub_hp: S("sub_hp"), offaxis_tail: S("offaxis_tail"),
  /* Box posts the key. The server keeps the shoebox bytes. */
  room_shape: S("room_shape"),
  /* Box only. On links left and right. A symmetric polygon stays paired and has no switch. */
  mirror_lr: S("mirror_lr"),
  /* Routing. UI names are not engine keys. Off posts nothing. */
  route_array_pre: S("route_array_pre"), route_array_drive: S("route_array_drive"), route_array_comp: S("route_array_comp"), route_array_amount: S("route_array_amount"),
  route_room_pre: S("route_room_pre"), route_room_drive: S("route_room_drive"), route_room_comp: S("route_room_comp"), route_room_amount: S("route_room_amount"),
  route_master_pre: S("route_master_pre"), route_master_drive: S("route_master_drive"), route_master_comp: S("route_master_comp"), route_master_amount: S("route_master_amount"),
  solo_direct: S("solo_direct"), solo_fdn: S("solo_fdn"), solo_early: S("solo_early"), solo_dry: S("solo_dry"),
  solo_l: S("solo_l"), solo_c: S("solo_c"), solo_r: S("solo_r"),
  stereo_mic: S("stereo_mic"), natural_bus: S("natural_bus"),
  fader_l: S("fader_l"), fader_c: S("fader_c"), fader_r: S("fader_r"),
  /* K4 (locked): FDN-first mixing. FDN fader on (0 dB), direct and early faders down. */
  fader_direct: S("fader_direct"), fader_fdn: S("fader_fdn"), fader_early: S("fader_early"), fader_dry: S("fader_dry"),
  trim_l: S("trim_l"), trim_c: S("trim_c"), trim_r: S("trim_r"),
  trim_direct: S("trim_direct"), trim_fdn: S("trim_fdn"), trim_early: S("trim_early"), trim_dry: S("trim_dry"),
  pan_l: S("pan_l"), pan_c: S("pan_c"), pan_r: S("pan_r"),
  mute_l: S("mute_l"), mute_c: S("mute_c"), mute_r: S("mute_r"),
  mute_direct: S("mute_direct"), mute_fdn: S("mute_fdn"), mute_early: S("mute_early"), mute_dry: S("mute_dry"),
  phase_l: S("phase_l"), phase_c: S("phase_c"), phase_r: S("phase_r"),
  /* ISO shelf still gives HF loss. diffusion_master −0.25 (Structure), clamp [−0.5, 0]. */
  humidity: S("humidity"), air_shelf: S("air_shelf"), air_climate: S("air_climate"), diffusion_master: S("diffusion_master"),
  live_drag_render: S("live_drag_render"), shared_tail: S("shared_tail"),
  two_sources: S("two_sources"), mirror_b: S("mirror_b"), source_balance: S("source_balance"),
  /* A is omni, so the source stage is not called. B null follows A. */
  source_radiation: S("source_radiation"), source_yaw: S("source_yaw"), source_pitch: S("source_pitch"),
  source_radiation_b: S("source_radiation_b"), source_yaw_b: S("source_yaw_b"), source_pitch_b: S("source_pitch_b"),
  sx_b: S("sx_b"), sy_b: S("sy_b"), sz_b: S("sz_b"), /* K3: mirror of the default source (W − 2.6, 1.2) */
  path_on: S("path_on"), path_preset: S("path_preset"),
  ellipse_rate: S("ellipse_rate"), ellipse_rx: S("ellipse_rx"), ellipse_rz: S("ellipse_rz"),
  hadamard_n: S("hadamard_n"),
  diffusion_seed: S("diffusion_seed"),
  lambda_ref: S("lambda_ref"),
  surfaces_solo: S("surfaces_solo"),
  surfaces_mute: S("surfaces_mute"),
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
var wetBypass = S("wetBypass");

var FADER_KNOTS = [
  [0.02, -60], [0.20, -24], [0.35, -12], [0.42, -6],
  [0.50, 0], [0.58, 3], [0.70, 6], [1, 12]
];

var msMicStash = null;
var pairStash = null;

var physTimer = null;
var physText = "";

var DESK_FADERS = ["l", "c", "r", "direct", "fdn", "early"];

function faderBoot(key) {
  return S("fader_" + key);
}

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

/* Page after ORTF + /api/settings?part=defaults. applyPlace clones this, then overlays the place. */
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
