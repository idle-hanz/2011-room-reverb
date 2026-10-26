/* Software distance law. Twin of engine/maths_distance.py.
   Software amplitude is 1/r (Idle, 2026-10-10). The Structure Air Abs graph
   is still 1/r² (shot 256: Dis×Dis then 1/x). Idle chose 1/r for the whole
   software path, Play and Render: AGC balance, close mics too loud, and the
   physical pressure law (about 6 dB per doubling). Distances 1/x stays 1/340
   (delay), not this gain. No page caller used a second copy; this module is
   the twin the parity test checks. */
(function (root) {
  "use strict";
  function geometricLevel(distance) {
    if (!(distance > 1e-9)) return 0;
    return 1 / distance;
  }
  var api = { geometricLevel: geometricLevel };
  root.RRDistance = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
