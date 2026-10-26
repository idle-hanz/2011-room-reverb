/* dB and linear amplitude. Twin of engine/maths_db.py.
   20 log10, so 6.0206 dB is about ×2. Callers that clamp, mute, or format
   a fader stay in the caller. This module is only the conversion. */
(function (root) {
  "use strict";
  function dbToLin(db) {
    return Math.pow(10, Number(db) / 20);
  }
  function linToDb(lin) {
    return 20 * Math.log10(Number(lin));
  }
  var api = { dbToLin: dbToLin, linToDb: linToDb };
  root.RRDb = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
