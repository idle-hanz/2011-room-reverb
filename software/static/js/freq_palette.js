/* One frequency palette for every band-coloured graph.
   t = 0 is the lowest frequency (red). t = 1 is the highest (violet).
   Eight equal steps land on red, orange, yellow, green, cyan, blue, indigo, violet. */
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
    if (global.SpectrumColors && global.SpectrumColors.hueOf) {
      return global.SpectrumColors.hueOf(t);
    }
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

  function rgb(t) {
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

  function byte(n) {
    var s = n.toString(16);
    return s.length < 2 ? "0" + s : s;
  }

  function css(t) {
    var c = rgb(t);
    return "rgb(" + c.r + "," + c.g + "," + c.b + ")";
  }

  function hex(t) {
    var c = rgb(t);
    return "#" + byte(c.r) + byte(c.g) + byte(c.b);
  }

  function intColor(t) {
    var c = rgb(t);
    return (c.r << 16) | (c.g << 8) | c.b;
  }

  function at(i, n) {
    n = n | 0;
    if (n <= 1) return 0;
    var t = Number(i) / (n - 1);
    return clamp01(t);
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

  global.FreqPalette = {
    css: css,
    hex: hex,
    int: intColor,
    rgb: rgb,
    at: at,
    cssAt: function (i, n) { return css(at(i, n)); },
    hexAt: function (i, n) { return hex(at(i, n)); },
    intAt: function (i, n) { return intColor(at(i, n)); },
    tHz: tHz
  };
})(window);
