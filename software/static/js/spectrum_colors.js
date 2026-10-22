/* One frequency palette. 20 Hz is deep red. 16 kHz is violet.
   Low goes red, orange, yellow, green, cyan, blue, then violet. */
(function (global) {
  "use strict";

  var STOPS = [
    [0, 0],
    [1 / 7, 28],
    [2 / 7, 52],
    [3 / 7, 120],
    [4 / 7, 185],
    [5 / 7, 220],
    [6 / 7, 255],
    [1, 278]
  ];
  var SAT = 0.78;
  var LIT = 0.58;

  function clamp01(t) {
    t = Number(t);
    if (!isFinite(t)) return 0;
    if (t < 0) return 0;
    if (t > 1) return 1;
    return t;
  }

  function hueOf(t) {
    t = clamp01(t);
    var i;
    for (i = 1; i < STOPS.length; i++) {
      if (t <= STOPS[i][0]) {
        var a = STOPS[i - 1];
        var b = STOPS[i];
        var u = (t - a[0]) / (b[0] - a[0]);
        return a[1] + (b[1] - a[1]) * u;
      }
    }
    return 278;
  }

  function tHz(hz, lo, hi) {
    lo = lo || 20;
    hi = hi || 16000;
    hz = Number(hz);
    if (!isFinite(hz)) hz = lo;
    if (hz < lo) hz = lo;
    if (hz > hi) hz = hi;
    var a = Math.log(lo);
    var b = Math.log(hi);
    if (!(b > a)) return 0;
    return (Math.log(hz) - a) / (b - a);
  }

  function rgbOf(t) {
    var H = hueOf(t) / 360;
    var q = LIT < 0.5 ? LIT * (1 + SAT) : LIT + SAT - LIT * SAT;
    var p = 2 * LIT - q;
    function chan(tt) {
      if (tt < 0) tt += 1;
      if (tt > 1) tt -= 1;
      if (tt < 1 / 6) return p + (q - p) * 6 * tt;
      if (tt < 1 / 2) return q;
      if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6;
      return p;
    }
    return {
      r: Math.round(chan(H + 1 / 3) * 255),
      g: Math.round(chan(H) * 255),
      b: Math.round(chan(H - 1 / 3) * 255)
    };
  }

  function cssOf(t) {
    var c = rgbOf(t);
    return "rgb(" + c.r + "," + c.g + "," + c.b + ")";
  }

  function pack(t) {
    return { t: t, hue: hueOf(t), css: cssOf(t), rgb: rgbOf(t) };
  }

  function forHz(hz) {
    return pack(tHz(hz));
  }

  function forIndex(i, n) {
    n = n | 0;
    var t = n <= 1 ? 0 : Number(i) / (n - 1);
    return pack(clamp01(t));
  }

  global.SpectrumColors = {
    forHz: forHz,
    forIndex: forIndex,
    hueOf: hueOf,
    tHz: tHz,
    cssT: cssOf,
    rgbT: rgbOf
  };
})(typeof window !== "undefined" ? window : globalThis);
