/* Exact third-octave centres, 1000 * 2^(k/3). Twin of engine/maths_bands.py.
   ISO preferred names (31.5, 63, …) stay in surface_colour.THIRD_OCTAVE_HZ.
   Those are rounded labels, not this generator. */
(function (root) {
  "use strict";
  function exactThirdCentres(i0, i1) {
    var out = [];
    var k;
    for (k = i0; k < i1; k++) out.push(1000 * Math.pow(2, k / 3));
    return out;
  }
  var api = { exactThirdCentres: exactThirdCentres };
  root.RRBands = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
