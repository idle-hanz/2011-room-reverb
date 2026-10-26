/* First-order polar a and the desk slider map. Twin of engine/maths_pattern.py.
   a=1 omni, a=0.5 cardioid, a=SUPER_A supercardioid. ASSUMED continuum.
   A hypercardioid name is HYPER_A (0.25), so 0° / 90° / 180° read 1 / 0.25 / −0.5.
   polar 1 with no hyper name stays SUPER_A (0.37).
   Family "bi" is the desk short-circuit (gain becomes cos). The Python slider
   does not take a family; that branch stays here so RoomMath.polarA can delegate. */
(function (root) {
  "use strict";
  var SUPER_A = 0.37;
  var HYPER_A = 0.25;
  function isHyper(pattern) {
    if (pattern == null) return false;
    var p = String(pattern).toLowerCase().replace(/[\s_-]/g, "");
    return p === "hypercardioid" || p === "hyper";
  }
  function polarA(family, polar, pattern) {
    if (String(family || "cardioid") === "bi") return 0;
    if (isHyper(pattern)) return HYPER_A;
    var d = Math.max(0, Math.min(1, Number(polar) || 0));
    if (d <= 0.5) return 1 - d;
    return 0.5 - (d - 0.5) * (0.5 - SUPER_A) / 0.5;
  }
  function firstOrderGain(theta, a) {
    return Number(a) + (1 - Number(a)) * Math.cos(theta);
  }
  function polarGain(theta, family, polar, pattern) {
    var a = polarA(family, polar, pattern);
    return firstOrderGain(theta, a);
  }
  var api = {
    SUPER_A: SUPER_A,
    HYPER_A: HYPER_A,
    isHyper: isHyper,
    polarA: polarA,
    polarGain: polarGain,
    firstOrderGain: firstOrderGain
  };
  root.RRPattern = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
