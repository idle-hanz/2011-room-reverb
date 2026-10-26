/* Yaw and look. Twin of engine/maths_look.py.
   Yaw 0 looks toward +Z. look = (YAW_X_SIGN·sin yaw, 0, cos yaw).
   Positive yaw rotates that look toward +X (the UI's right).
   L capsule (smaller X) aims outward toward −X, so its yaw is negative
   (ORTF −55°, MS −90°). R aims outward toward +X (ORTF +55°, MS +90°).
   K1 (Idle, 28 Sep 2026): the old sign was −1, which aimed every
   L-negative/R-positive preset inward. Stored yaw numbers did not change.
   early_field.py and room_math.js still write the literal 1 so the K1
   file probe can read it. This module is the formula. */
(function (root) {
  "use strict";
  var YAW_X_SIGN = 1;
  function lookFromYaw(yawRad) {
    return { x: YAW_X_SIGN * Math.sin(yawRad), z: Math.cos(yawRad) };
  }
  function lookVector(yawRad) {
    var xz = lookFromYaw(yawRad);
    return { x: xz.x, y: 0, z: xz.z };
  }
  var api = { YAW_X_SIGN: YAW_X_SIGN, lookFromYaw: lookFromYaw, lookVector: lookVector };
  root.RRLook = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
