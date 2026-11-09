/* dB and linear amplitude. Twin of engine/maths_db.py.
   20 log10, so 6.0206 dB is about ×2. Callers that clamp, mute, or format
   a fader stay in the caller. polarRadius is the shared polar drawing scale. */
(function (root) {
  "use strict";
  var POLAR_DB_FLOOR = -30;
  var POLAR_DB_RINGS = [0, -6, -12, -18, -24, -30];
  function dbToLin(db) {
    return Math.pow(10, Number(db) / 20);
  }
  function linToDb(lin) {
    return 20 * Math.log10(Number(lin));
  }
  /* 0 dB on the outer edge, −30 dB at the centre, linear in dB. */
  function polarRadius(db, outer) {
    var v = Number(db);
    if (!(v > POLAR_DB_FLOOR)) v = POLAR_DB_FLOOR;
    if (v > 0) v = 0;
    return outer * (v - POLAR_DB_FLOOR) / (0 - POLAR_DB_FLOOR);
  }
  function polarLinRadius(lin, outer) {
    var g = Number(lin);
    var db = g > 1e-6 ? linToDb(g) : POLAR_DB_FLOOR;
    return polarRadius(db, outer);
  }
  var api = {
    dbToLin: dbToLin,
    linToDb: linToDb,
    POLAR_DB_FLOOR: POLAR_DB_FLOOR,
    POLAR_DB_RINGS: POLAR_DB_RINGS,
    polarRadius: polarRadius,
    polarLinRadius: polarLinRadius
  };
  root.RRDb = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
