/* Mix desk, faders, and the live post.
   pairRoomMic and the treatment posters stay here so the post reads in one piece. */
"use strict";


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
  var g = window.RRDb.dbToLin(db);
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
  var route = String(src["mic_route_" + key] || S("mic_route_" + key));
  var fader = gainFromDb(dbFromTravel(src["fader_" + key]), 0);
  var g;
  if (route === "s") {
    g = window.RRDb.dbToLin(Number(src["width_" + key] || S("width_" + key))) * fader;
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

/* XY, NOS, DIN, and both AB setups. The centre strip is a room mic, not the stand.
     Spot (4, 1.5, 2) m, yaw 0, then the same 0.10 m wall inset as a room drag.
     Fader stays 0.5, which is 0 dB. ORTF, ORTF + C, mono, binaural, and ms_* return null. */
function pairRoomMic(id, room, drag) {
  if (id !== "ab_omni" && id !== "ab_card" && id !== "xy_90" && id !== "xy_120" && id !== "nos" && id !== "din") {
    return null;
  }
  var box = {
    W: Number(room && room.W) > 0 ? Number(room.W) : 6,
    H: Number(room && room.H) > 0 ? Number(room.H) : 3,
    L: Number(room && room.L) > 0 ? Number(room.L) : 8
  };
  var x = S("room_x");
  var y = S("room_y");
  var z = S("room_z");
  var yaw = S("room_yaw");
  var margin = 0.10;
  if (drag && drag.roomFloorDragTo && drag.roomHeightDragTo && drag.roomAimDragTo) {
    var floor = drag.roomFloorDragTo(box, "c", x, z);
    var height = drag.roomHeightDragTo(box, "c", y);
    var aim = drag.roomAimDragTo(box, "c", yaw);
    x = floor.room_c_x;
    z = floor.room_c_z;
    y = height.room_c_y;
    yaw = aim.room_c_yaw;
  } else {
    if (x < margin) x = margin;
    if (x > box.W - margin) x = box.W - margin;
    if (y < margin) y = margin;
    if (y > box.H - margin) y = box.H - margin;
    if (z < margin) z = margin;
    if (z > box.L - margin) z = box.L - margin;
  }
  return {
    third_mic: "room",
    place_c: "room",
    room_slot: "c",
    mute_c: S("mute_c"),
    fader_c: S("fader_c"),
    gain_exact_c: S("gain_exact_c"),
    width_c: S("width_c"),
    room_c_x: x,
    room_c_y: y,
    room_c_z: z,
    room_c_yaw: yaw
  };
}

function loadDeskPreset(id) {
  /* Does not mark the desk touched. Boot and a confirmed setup change call this. */
  state.pair_mode = S("pair_mode");
  state.pan_law = S("pan_law");
  state.mic_route_l = S("mic_route_l");
  state.mic_route_c = S("mic_route_c");
  state.mic_route_r = S("mic_route_r");
  /* D20. ORTF is C off. ORTF + C and the other setups start with C in the centre.
       The six pair ids below then move that strip to its room spot. */
  state.third_mic = (id === "ortf") ? "off" : "centre";
  cThirdBeforeRoom = null;
  state.ms_s = S("ms_s");
  state.ms_m = S("ms_m");
  state.s_detached = S("s_detached");
  state.width_l = S("width_l");
  state.width_c = S("width_c");
  state.width_r = S("width_r");
  state.gain_exact_l = S("gain_exact_l");
  state.gain_exact_c = S("gain_exact_c");
  state.gain_exact_r = S("gain_exact_r");
  state.place_l = S("place_l");
  state.place_c = S("place_c");
  state.place_r = S("place_r");
  state.mute_l = S("mute_l");
  state.mute_c = S("mute_c");
  state.mute_r = S("mute_r");
  state.solo_l = S("solo_l");
  state.solo_c = S("solo_c");
  state.solo_r = S("solo_r");
  state.pan_l = S("pan_l");
  state.pan_c = S("pan_c");
  state.pan_r = S("pan_r");
  state.trim_l = S("trim_l");
  state.trim_c = S("trim_c");
  state.trim_r = S("trim_r");
  state.fader_l = S("fader_l");
  state.fader_c = S("fader_c");
  state.fader_r = S("fader_r");
  state.phase_l = S("phase_l");
  state.phase_c = S("phase_c");
  state.phase_r = S("phase_r");
  delete state.spare_off;
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
    state.link_mode = "split";
    state.link_lr_yaw = false;
    state.mic_route_c = "centre";
    state.mute_l = true;
    state.mute_r = true;
  } else if (id === "binaural") {
    state.mute_c = true;
  } else if (id === "ms") {
    state.mic_route_c = "centre";
  }
  pairStash = null;
  splitHold = null;
  if (state.pair_mode === "stereo" && window.RRPair && RRPair.applyGang) RRPair.applyGang(state);
  else state.stereo_mic = false;
  var roomPatch = pairRoomMic(id, state, window.RRDrag);
  if (roomPatch) {
    cThirdBeforeRoom = "centre";
    Object.assign(state, roomPatch);
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
    route = String(route || S("mic_route_l"));
    if (route === "centre") return [a * 0.5, a * 0.5];
    if (route === "both") return [a, a];
    if (route === "l") return [a, 0];
    if (route === "r") return [0, a];
    if (route === "s") return [a, -a];
    var t = (Number(pan) + 1) * 0.5;
    if (t < 0) t = 0;
    if (t > 1) t = 1;
    if (String(src.pan_law || S("pan_law")) === "power") {
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

/* Host fader is gone. Off keeps dry_gain at 0. On hears the input and zeros the three wet sends. */
function applyWetBypass(o, on) {
  if (!o) return o;
  if (!on) {
    o.dry_gain = 0;
    return o;
  }
  o.dry_gain = 1;
  o.direct_wet = 0;
  o.fdn_wet = 0;
  o.early_wet = 0;
  return o;
}

function heardMix(src) {
  var o = Object.assign({}, src);
  /* Client flag for the MS (2 mics) spare strip. Not a server key. */
  delete o.spare_off;
  var buses = ["direct", "fdn", "early"];
  var i;
  o.direct_wet = stripLinear(src, "direct");
  o.fdn_wet = stripLinear(src, "fdn");
  /* K4: early send = bus enable (early_wet, default 1) × early fader. */
  var ewEnable = (src.early_wet == null || !isFinite(Number(src.early_wet))) ? 1 : Math.max(0, Math.min(1, Number(src.early_wet)));
  o.early_wet = ewEnable * stripLinear(src, "early");
  o.dry_gain = 0;
  var any = false;
  for (i = 0; i < SOLO_BUSES.length; i++) {
    if (src[SOLO_BUSES[i][0]]) any = true;
  }
  if (any) {
    for (i = 0; i < buses.length; i++) {
      if (!src["solo_" + buses[i]]) o[buses[i] + "_wet"] = 0;
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
  /* Play posts the master strip, and an array or room strip only while it is on. */
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
  if (window.RRRouting && RRRouting.renderScene) Object.assign(o, RRRouting.renderScene(src));
  applyTreatAmount(o);
  applyTreatDecay(o);
  applyWetBypass(o, wetBypass);
  return o;
}

/* SL6 Amount. Scale accepted coverage on this copy only. A shell row and a
     suggested row keep their coverage. A missing amount is 100. Below 100 the
     stored surf_cal is left off this post and is not rewritten on the scene. */
function applyTreatAmount(o) {
  if (!o || typeof o !== "object") return o;
  var v = Number(o.surf_amount);
  if (!isFinite(v)) v = 100;
  if (v < 0) v = 0;
  if (v > 100) v = 100;
  if (Array.isArray(o.surf_treatment)) {
    var frac = v / 100;
    o.surf_treatment = o.surf_treatment.map(function (r) {
      if (!r || typeof r !== "object") return r;
      var c = Object.assign({}, r);
      if (c.suggested || c.type === "shell") return c;
      c.coverage = Number(c.coverage || 0) * frac;
      return c;
    });
  }
  if (v < 100) delete o.surf_cal;
  return o;
}
window.RRApplyTreatAmount = applyTreatAmount;

/* SL6. On, and only in Surfaces, the post copy turns the decay lock off.
     Flat keeps the lock, so the default scene stays bit-exact. */
function applyTreatDecay(o) {
  if (!o || typeof o !== "object") return o;
  if (!o.treat_sets_decay) return o;
  if (String(o.decay_mode || "flat") !== "surfaces") return o;
  o.decay_lock = false;
  return o;
}
window.RRApplyTreatDecay = applyTreatDecay;

function liveRequestBody() {
  var o = heardMix(state);
  /* Boolean. On, the server packs the same 45 floats Play already forwards. */
  o.offaxis_tail = !!state.offaxis_tail;
  /* Polygon preset. Box is posted and stays the shoebox. */
  if (state.room_shape) o.room_shape = String(state.room_shape);
  /* Surfaces mirror. On copies left onto right. Off posts false and leaves them apart. */
  o.mirror_lr = !!state.mirror_lr;
  if (window.LiveFDN) {
    var rate = LiveFDN.rate ? LiveFDN.rate() : 0;
    var rev = LiveFDN.colourRev ? LiveFDN.colourRev() : "";
    if (rate) o.sample_rate = rate;
    if (rev) o.colour_rev = rev;
    /* Hold the gain from when this letter started. A new letter omits it and is measured. */
    var soloNow = o.surfaces_solo ? String(o.surfaces_solo).toUpperCase() : "";
    if (soloNow && LiveFDN.soloHold) {
      var hold = LiveFDN.soloHold();
      if (hold && String(hold.letter).toUpperCase() === soloNow && Number(hold.gain) > 0) {
        o.solo_match_letter = hold.letter;
        o.solo_match_gain = hold.gain;
      }
    }
  }
  return o;
}

function feedbackLawOn() {
  return !!hallSnapshot;
}

function paintDecayHint() {
  var el = document.getElementById("decayHint");
  if (!el) return;
  var sec = Number(state.decay_s).toFixed(2);
  if (state.treat_sets_decay && state.decay_mode === "surfaces") {
    el.textContent = "Treatment sets the length (" + sec + " s). Amount moves it.";
  } else if (state.decay_lock) {
    el.textContent = "Decay is armed at " + sec + " s. Play live and Render use that length.";
  } else {
    el.textContent = "2011 law (Structure Gain) is in charge (" + sec +
      " s). Move Decay to arm a fixed length again.";
  }
  paintPhysReadout();
  var subBox = document.getElementById("sub_hp");
  if (subBox) subBox.checked = !!state.sub_hp;
  var tailBox = document.getElementById("offaxis_tail");
  if (tailBox) tailBox.checked = !!state.offaxis_tail;
}
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
    var res = await fetch("/api/params/phys", {
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
      physText = "";
      el.hidden = true;
      el.textContent = "";
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

function setFader(key, u, fromLink) {
  u = Math.max(0, Math.min(1, Number(u)));
  if (!fromLink) {
    var db = dbFromTravel(u);
    if (isFinite(db) && Math.abs(db) <= 0.25) u = 0.5;
  }
  state["fader_" + key] = u;
  if (fromLink) return;
  if ((state.pair_mode === "stereo" || state.stereo_mic) && (key === "l" || key === "r")) {
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
  if (state.pair_mode === "stereo" && (key === "l" || key === "r")) {
    setTrim(key === "l" ? "r" : "l", db, true);
  }
  if (state.natural_bus && (key === "direct" || key === "fdn")) {
    setTrim(key === "direct" ? "fdn" : "direct", db, true);
  }
}

/* Buttons for one strip. Does not write the route back: centre stays centre until a click. */
function lrView(cap) {
  var route = String(state["mic_route_" + cap] || S("mic_route_" + cap));
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
    if (row) row.classList.toggle("is-linked", state.pair_mode === "stereo" && cap !== "c");
    if (row) row.classList.toggle("is-pan-locked", !!locked);
    if (cap === "c" && row) {
      row.classList.toggle("is-binaural-off", state.mic_setup === "binaural");
      var deskName = row.querySelector(".desk-name");
      if (deskName) deskName.textContent = stripIsRoom("c") ? "Room mic" : "Centre";
    }
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
  var spareR = state.spare_off === "r";
  ["l", "r"].forEach(function (cap) {
    var row = document.querySelector('.desk-strip[data-cap="' + cap + '"]');
    if (!row) return;
    var off = monoDesk || (spareR && cap === "r");
    row.classList.toggle("is-mono-off", off);
    row.title = monoDesk ? "Mono centre uses only C" : (off ? "Off" : "");
    row.querySelectorAll("input, button").forEach(function (el) {
      var panLock = !off && state.stereo_mic && el.id === ("pan_" + cap);
      el.disabled = !!off || !!panLock;
      if (monoDesk) el.title = "Mono centre uses only C";
      else if (off) el.title = "Off";
      else if (el.title === "Mono centre uses only C" || el.title === "Off") el.title = "";
    });
  });
  if (spareR) {
    var rRead = document.getElementById("read_r");
    if (rRead) rRead.textContent = "off";
  }
  paintDeskRoutes();
}

function paintDeskRoutes() {
  var pan;
  ["l", "c", "r"].forEach(function (cap) {
    var view = lrView(cap);
    var route = view.route;
    var monoLock = state.mic_setup === "mono_c" && (cap === "l" || cap === "r");
    var stereoLock = state.stereo_mic && cap !== "c";
    var binLock = state.mic_setup === "binaural" && cap === "c";
    var spareLock = state.spare_off === "r" && cap === "r";
    document.querySelectorAll('.lr-btn[data-lr="' + cap + '"]').forEach(function (btn) {
      var side = btn.getAttribute("data-side") === "r" ? "r" : "l";
      var v = view.shown[side] || 0;
      var lab = window.RRLR ? RRLR.buttonLabel(side, v) : { text: side.toUpperCase(), title: "" };
      btn.setAttribute("data-v", String(v));
      btn.textContent = lab.text;
      btn.setAttribute("aria-pressed", v === 0 ? "false" : "true");
      if (!monoLock && !spareLock) {
        btn.title = lab.title;
        btn.setAttribute("aria-label", lab.title);
      }
    });
    pan = document.getElementById("pan_" + cap);
    var panBox = document.getElementById("panBox_" + cap);
    var panLabel = document.getElementById("panLabel_" + cap);
    if (pan) pan.disabled = !view.panLive || stereoLock || monoLock || binLock || spareLock;
    if (pan && !monoLock && !spareLock) pan.title = view.panLive ? "Pan between the speakers" : "This pan is not in the send";
    if (panBox) panBox.classList.toggle("is-pot-off", !view.panLive || binLock || stereoLock);
    if (panLabel && window.RRLR) panLabel.textContent = RRLR.potLabel(view.panLive ? "balance" : "none");
    var trimBox = document.getElementById("trimBox_" + cap);
    var widthBox = document.getElementById("widthBox_" + cap);
    var sOn = route === "s";
    if (trimBox) trimBox.hidden = sOn;
    if (widthBox) widthBox.hidden = !sOn;
    var width = document.getElementById("width_" + cap);
    if (width && document.activeElement !== width) width.value = state["width_" + cap] || S("width_" + cap);
    if (!monoLock && !spareLock) {
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
    btn.setAttribute("aria-current", on ? "true" : "false");
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
    var on = btn.getAttribute("data-radius") === (state.polar_radius || S("polar_radius"));
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  });
  var linkBox = document.getElementById("link_lr_yaw");
  if (linkBox) linkBox.checked = (state.link_mode || S("link_mode")) === "mirror";
  var naturalBtn = document.getElementById("naturalBtn");
  if (naturalBtn) naturalBtn.setAttribute("aria-pressed", state.natural_bus ? "true" : "false");
  var bypassBtn = document.getElementById("wetBypass");
  if (bypassBtn) bypassBtn.setAttribute("aria-pressed", wetBypass ? "true" : "false");
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
        var boot = faderBoot(key);
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
  bindDeskRest();
}

function bindDeskRest() {
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
      if (!window.RRPair || !RRPair.step) return;
      var out = RRPair.step(state, mode, pairStash, rrMsBuilt("ms_b"));
      pairStash = out.stash;
      if (!out.posts) return;
      if (mode === "stereo") sideSplitUser = false;
      else if (mode === "independent") sideSplitUser = true;
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
function paintDecayControls() {
  paintDecayHint();
  var dEl = document.getElementById("decay_s");
  var dOut = document.getElementById("decay_s_out");
  if (dEl && document.activeElement !== dEl) dEl.value = state.decay_s;
  if (dOut) dOut.textContent = Number(state.decay_s).toFixed(2);
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
    var res = await fetch("/api/params/live", {
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

function balanceLabel(v) {
  v = Number(v) || 0;
  if (Math.abs(v) < 0.001) return "Centre";
  if (v <= -0.995) return "A";
  if (v >= 0.995) return "B";
  return (v > 0 ? "+" : "") + v.toFixed(2);
}