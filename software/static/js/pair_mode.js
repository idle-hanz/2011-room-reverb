/* pair_mode.js — Stereo / M/S / Independent on the mic desk.
   Browser: window.RRPair. Node: module.exports. No DOM.
   One step() call is one Play post. The caller posts once. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RRPair = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var STASH_KEYS = [
    "pair_mode", "stereo_mic", "ms_decode", "ms_s", "ms_m", "s_detached",
    "third_mic", "place_l", "place_c", "place_r",
    "mic_route_l", "mic_route_c", "mic_route_r",
    "width_l", "width_c", "width_r",
    "gain_exact_l", "gain_exact_c", "gain_exact_r",
    "mute_l", "mute_c", "mute_r",
    "phase_l", "phase_c", "phase_r",
    "pan_l", "pan_c", "pan_r",
    "yaw_l_deg", "yaw_c_deg", "yaw_r_deg",
    "pattern_l", "pattern_c", "pattern_r",
    "family_l", "family_c", "family_r",
    "polar_l", "polar_c", "polar_r",
    "mic_preset_l", "mic_preset_c", "mic_preset_r",
    "fader_l", "fader_r", "trim_l", "trim_r"
  ];

  function snapshot(state) {
    var o = {};
    var i;
    for (i = 0; i < STASH_KEYS.length; i++) o[STASH_KEYS[i]] = state[STASH_KEYS[i]];
    return o;
  }

  function restore(state, stash) {
    var keys = Object.keys(stash);
    var i;
    for (i = 0; i < keys.length; i++) state[keys[i]] = stash[keys[i]];
  }

  /* Shared pattern and gain. Aim is mirrored. Routes stay. */
  function applyGang(state) {
    state.pair_mode = "stereo";
    state.stereo_mic = false;
    state.fader_r = state.fader_l;
    state.trim_r = state.trim_l;
    state.pattern_r = state.pattern_l;
    state.family_r = state.family_l;
    state.polar_r = state.polar_l;
    state.mic_preset_r = state.mic_preset_l;
    var yl = Number(state.yaw_l_deg);
    if (isFinite(yl)) state.yaw_r_deg = -yl;
  }

  function applyMs(state, built) {
    var desk = built.desk;
    var mic = built.mic || {};
    var s = desk.ms_s || "l";
    state.pair_mode = "ms";
    state.stereo_mic = false;
    state.ms_decode = false;
    state.ms_s = s;
    state.ms_m = desk.ms_m || "c";
    state.s_detached = false;
    state.third_mic = "centre";
    state.place_l = "array";
    state.place_c = "array";
    state.mic_route_l = desk.mic_route_l;
    state.mic_route_c = desk.mic_route_c;
    state.mic_route_r = desk.mic_route_r;
    state.width_l = desk.width_l;
    state.width_r = desk.width_r;
    state.gain_exact_c = desk.gain_exact_c;
    state.phase_l = desk.phase_l;
    state.phase_c = desk.phase_c;
    state.phase_r = desk.phase_r;
    state.mute_l = false;
    state.mute_c = false;
    state.mute_r = !!desk.mute_r;
    state["yaw_" + s + "_deg"] = 90;
    state.yaw_c_deg = 0;
    if (mic.pattern_l) state.pattern_l = mic.pattern_l;
    if (mic.family_l) state.family_l = mic.family_l;
    if (mic.polar_l != null) state.polar_l = mic.polar_l;
    if (mic.pattern_c) state.pattern_c = mic.pattern_c;
    if (mic.family_c) state.family_c = mic.family_c;
    if (mic.polar_c != null) state.polar_c = mic.polar_c;
    if (built.mics) {
      state.mic_preset_l = built.mics.l;
      state.mic_preset_c = built.mics.c;
    }
  }

  function alreadyMs(state) {
    var s = state.ms_s || "l";
    return state.pair_mode === "ms"
      && state.mic_route_l === "s"
      && state.mic_route_c === "both"
      && !!state.mute_r
      && Number(state["yaw_" + s + "_deg"]) === 90
      && String(state.third_mic || "") !== "off";
  }

  /* Returns how many Play posts the caller should make. */
  function step(state, mode, stash, built) {
    if (mode !== "stereo" && mode !== "ms" && mode !== "independent") {
      return { stash: stash || null, posts: 0 };
    }
    if (mode === "ms") {
      if (!built || !built.desk) return { stash: stash || null, posts: 0 };
      if (alreadyMs(state)) return { stash: stash || null, posts: 0 };
      if (state.pair_mode !== "ms" || !stash) stash = snapshot(state);
      applyMs(state, built);
      return { stash: stash, posts: 1 };
    }
    if (mode === "stereo") {
      if (stash) {
        restore(state, stash);
        stash = null;
      }
      applyGang(state);
      return { stash: null, posts: 1 };
    }
    if (state.pair_mode === "independent" && !state.stereo_mic) {
      return { stash: stash || null, posts: 0 };
    }
    state.pair_mode = "independent";
    state.stereo_mic = false;
    return { stash: stash || null, posts: 1 };
  }

  /* Moving one side copies gain, pattern, and the mirrored aim while Stereo is on. */
  function follow(state, cap, patch) {
    if (!state || (cap !== "l" && cap !== "r") || !patch) return state;
    var other = cap === "l" ? "r" : "l";
    if (patch.fader != null) state["fader_" + cap] = patch.fader;
    if (patch.trim != null) state["trim_" + cap] = patch.trim;
    if (patch.family != null) state["family_" + cap] = patch.family;
    if (patch.polar != null) state["polar_" + cap] = patch.polar;
    if (patch.pattern != null) state["pattern_" + cap] = patch.pattern;
    if (patch.preset != null) state["mic_preset_" + cap] = patch.preset;
    if (patch.yaw != null) state["yaw_" + cap + "_deg"] = patch.yaw;
    if (state.pair_mode !== "stereo") return state;
    if (patch.fader != null) state["fader_" + other] = patch.fader;
    if (patch.trim != null) state["trim_" + other] = patch.trim;
    if (patch.family != null) state["family_" + other] = patch.family;
    if (patch.polar != null) state["polar_" + other] = patch.polar;
    if (patch.pattern != null) state["pattern_" + other] = patch.pattern;
    if (patch.preset != null) state["mic_preset_" + other] = patch.preset;
    if (patch.yaw != null) state["yaw_" + other + "_deg"] = -Number(patch.yaw);
    return state;
  }

  return {
    STASH_KEYS: STASH_KEYS,
    snapshot: snapshot,
    applyGang: applyGang,
    applyMs: applyMs,
    step: step,
    follow: follow
  };
});
