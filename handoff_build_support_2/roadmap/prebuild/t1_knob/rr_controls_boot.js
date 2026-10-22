/* rr_controls_boot.js — T1 glue: which knob gets which behaviour. Load after app.js.
   Kept separate so Build can paste the table into app.js bindDesk() instead if preferred. */
(function () {
  "use strict";
  if (!window.RRControls) return;
  var C = window.RRControls;
  function dbFmt(v) { var s = Math.abs(v) < 0.05 ? "0.0" : v.toFixed(1); return (v > 0.05 ? "+" : "") + s + " dB"; }
  var KINDS = {
    trim:  { kind: "db",  detents: [0], pxFull: 180, format: dbFmt, unitLabel: "dB" },
    width: { kind: "db",  detents: [0], pxFull: 240, format: dbFmt, unitLabel: "dB" },
    pan:   { kind: "pan", detents: [0], pxFull: 200 }
  };
  function boot() {
    var n = 0;
    document.querySelectorAll(".knob input[type=range]").forEach(function (inp) {
      var kind = (inp.id || "").split("_")[0];
      if (KINDS[kind]) { C.attachKnob(inp, KINDS[kind]); n++; }
    });
    var t = C.attachAllTyping(document);
    C.refreshAll();
    window.__rrControlsBooted = { knobs: n, typing: t };
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
