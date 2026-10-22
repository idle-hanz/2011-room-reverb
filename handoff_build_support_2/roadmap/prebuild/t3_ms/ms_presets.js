/* ms_presets.js — T3 prebuild (D-UI29): MS presets a/b/c and the decode maths.
   Browser: window.RRMS; node: module.exports. No DOM.
   Conventions copied from app.js MIC_PRESETS (lines 5-60) and loadDeskPreset (368-420):
   omni = pattern "omni", family "cardioid", polar 0; cardioid = polar 0.5; fig-8 = family "bi".
   Side axis follows today's ms_classic (S on L strip, yaw +90, route "s" = +L −R).
   M level (D18, locked 4 Oct 16:43): unity decode (S:M = 1) with a -3 dB trim on both, so
   M gain = S gain = 10^(-3/20). T3 ships MS_LEVEL = "legacy" (M x 1.5, S 0 dB = today, no reference moves);
   T3b flips MS_LEVEL to "unity_trim" and regenerates the MS references. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RRMS = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var M_GAIN = 1.5;           /* legacy Mid gain (+3.5 dB, today's gain_exact_c) */
  var TRIM_DB = -3;           /* D18 output trim */
  var LEVELS = {
    legacy:     { m: M_GAIN, s_db: 0 },                                  /* today: +-53 deg */
    unity_trim: { m: Math.pow(10, TRIM_DB / 20), s_db: TRIM_DB }          /* D18: +-63 deg, -3 dB */
  };
  var MS_LEVEL = "legacy";    /* T3 = "legacy"; T3b (D18) sets "unity_trim" */

  function base() {
    return { space: 0.05, toe_half_deg: 90, car_omni: 1, polar: ["L", "C", "R"],
      yaw_l_deg: 90, yaw_c_deg: 0, yaw_r_deg: 90 };
  }
  function deskBase(mGain, sDb) {
    return { pair_mode: "ms", ms_s: "l", ms_m: "c", ms_decode: true,
      mic_route_l: "s", mic_route_c: "both", mic_route_r: "pan",
      width_l: sDb, width_r: sDb, gain_exact_c: mGain, mute_r: true,
      phase_l: 1, phase_c: 1, phase_r: 1 };
  }
  /* level: a LEVELS key, a number (Mid gain, S 0 dB: old API), or omitted (MS_LEVEL). */
  function build(id, level) {
    var lv = typeof level === "number" ? { m: level, s_db: 0 }
      : LEVELS[level == null ? MS_LEVEL : level];
    if (!lv) return null;
    var mic = base(), desk = deskBase(lv.m, lv.s_db), mics;
    if (id === "ms_a") {          /* (a) fig-8 S + omni M */
      mic.pattern_l = "fig8"; mic.family_l = "bi"; mic.polar_l = 0.5;
      mic.pattern_c = "omni"; mic.family_c = "cardioid"; mic.polar_c = 0;
      mic.pattern_r = "fig8"; mic.family_r = "bi"; mic.polar_r = 0.5;
      mics = { l: "NeumannU87AiBidirect", c: "NeumannU87AiOmni", r: "NeumannU87AiBidirect" };
    } else if (id === "ms_b") {   /* (b) fig-8 S + cardioid M — DEFAULT */
      mic.pattern_l = "fig8"; mic.family_l = "bi"; mic.polar_l = 0.5;
      mic.pattern_c = "cardioid"; mic.family_c = "cardioid"; mic.polar_c = 0.5;
      mic.pattern_r = "fig8"; mic.family_r = "bi"; mic.polar_r = 0.5;
      mics = { l: "NeumannU87AiBidirect", c: "NeumannU87AiCardioid", r: "NeumannU87AiBidirect" };
    } else if (id === "ms_c") {   /* (c) back-to-back cardioids as S (L faces +90, R faces −90, R in Ø) + cardioid M */
      mic.pattern_l = "cardioid"; mic.family_l = "cardioid"; mic.polar_l = 0.5; mic.yaw_l_deg = 90;
      mic.pattern_c = "cardioid"; mic.family_c = "cardioid"; mic.polar_c = 0.5;
      mic.pattern_r = "cardioid"; mic.family_r = "cardioid"; mic.polar_r = 0.5; mic.yaw_r_deg = -90;
      desk.mic_route_r = "s"; desk.phase_r = -1; desk.mute_r = false; desk.ms_s = "l"; /* S = L − R strip */
      mics = { l: "NeumannU87AiCardioid", c: "NeumannU87AiCardioid", r: "NeumannU87AiCardioid" };
    } else return null;
    return { id: id, mic: mic, desk: desk, mics: mics };
  }
  var PRESETS = {
    ms_a: { label: "MS \u00b7 omni Mid + fig\u20118 Side", short: "MS omni" },
    ms_b: { label: "MS \u00b7 cardioid Mid + fig\u20118 Side", short: "MS cardioid", isDefault: true },
    ms_c: { label: "MS \u00b7 cardioid Mid + two back\u2011to\u2011back cardioids", short: "MS 3\u2011mic" }
  };
  /* Old scenes: ms_classic == ms_b with SM57 mics; keep the id as an alias so recall works. */
  var ALIASES = { ms_classic: "ms_b" };

  /* ---------- decode maths (Schoeps MS page; Sound On Sound) ---------- */
  var D2R = Math.PI / 180;
  /* First-order pattern: g(beta) = (1 - a) + a cos(beta). */
  function pat(a, betaDeg) { return (1 - a) + a * Math.cos(betaDeg * D2R); }
  /* Decoded outputs at source angle beta (0 = front, +90 = left). k = S gain / M gain. */
  function decode(a, k, betaDeg) {
    var M = pat(a, betaDeg), S = Math.cos((betaDeg - 90) * D2R);
    return { L: M + k * S, R: M - k * S };
  }
  /* The equivalent virtual pair: axis angle off front, main-axis level and gradient share. */
  function virtualPair(a, k) {
    var theta = Math.atan2(k, a) / D2R;
    var level = (1 - a) + Math.sqrt(k * k + a * a);
    var grad = Math.sqrt(k * k + a * a) / level;   /* 0 omni, 0.5 cardioid, 1 fig-8 */
    return { thetaDeg: theta, level: level, gradient: grad, name: patternName(grad) };
  }
  function patternName(m) {
    if (m < 0.12) return "omni";
    if (m < 0.45) return "wide cardioid";
    if (m < 0.58) return "cardioid";
    if (m < 0.68) return "supercardioid";
    if (m < 0.8) return "hypercardioid";
    return "fig-8";
  }
  /* App fields -> k. route s gain = 10^(width_dB/20); Mid gain = gain_exact_c. */
  function kFromDesk(widthDb, mGain) { return Math.pow(10, (widthDb || 0) / 20) / (mGain || 1); }
  /* Back-to-back cardioids with gain mismatch d dB: omni leak relative to the fig-8. */
  function b2bLeakDb(mismatchDb) {
    var g = Math.pow(10, -Math.abs(mismatchDb) / 20);
    var leak = (1 - g) / (1 + g);
    return leak <= 0 ? -Infinity : 20 * Math.log10(leak);
  }
  function db(x) { return 20 * Math.log10(x); }

  return { M_GAIN: M_GAIN, TRIM_DB: TRIM_DB, LEVELS: LEVELS, MS_LEVEL: MS_LEVEL, PRESETS: PRESETS, ALIASES: ALIASES, build: build, pat: pat, decode: decode,
           virtualPair: virtualPair, kFromDesk: kFromDesk, b2bLeakDb: b2bLeakDb, db: db, patternName: patternName };
});
