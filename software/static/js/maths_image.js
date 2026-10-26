/* Shoebox image positions. Twin of engine/maths_image.py.
   Corner origin is the live path. Full room size R (W, H, or L). No half-W.
   First-order marks use k in −1, 0, 1. Higher |k| is the same algebra the
   engine uses, including the PROPOSAL extension past the named macros.

   k: 0→S, −1→−S, 1→2R−S, 2→2R+S, −2→S−(2R).
   -2W+X = X − (2·W). VERIFIED shot 402. Do not invent a half-W form.
   n==(0,0,2) → 4L−Z only when zFace4l (macro exists, not in the live 32). */
(function (root) {
  "use strict";
  function cornerAxis(s, R, k) {
    if (k === 0) return s;
    if (k === -1) return -s;
    if (k === 1) return 2 * R - s;
    if (k === 2) return 2 * R + s;
    if (k === -2) return s - 2 * R;
    if (k % 2 === 0) return k * R + s;
    return k > 0 ? k * R + (R - s) : k * R - s;
  }
  function num(obj, key, index) {
    if (obj && obj[key] != null) return Number(obj[key]);
    return Number(obj[index]);
  }
  function imagePoint(source, room, n, zFace4l) {
    var sx = num(source, "x", 0);
    var sy = num(source, "y", 1);
    var sz = num(source, "z", 2);
    var W = num(room, "W", 0);
    var H = num(room, "H", 1);
    var L = num(room, "L", 2);
    var nx = n[0];
    var ny = n[1];
    var nz = n[2];
    var iz = (zFace4l && nx === 0 && ny === 0 && nz === 2)
      ? (4 * L - sz)
      : cornerAxis(sz, L, nz);
    return {
      x: cornerAxis(sx, W, nx),
      y: cornerAxis(sy, H, ny),
      z: iz
    };
  }
  var api = { cornerAxis: cornerAxis, imagePoint: imagePoint };
  root.RRImage = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
