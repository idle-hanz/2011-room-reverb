/* Colour (1/3-octave) + Surfaces A–F — ASSUMED tuning desk
 *
 * Colour as a tuning instrument:
 *  - Compare: Last ghost after re-Render; optional Hold A / Hold B
 *  - Engineer readout: peak or 1 kHz = 0 dB; octave marks; hover Hz+dB
 *  - Surfaces A–F selection dims/highlights Colour + EQ sparkline
 */
(function (global) {
  "use strict";

  var LETTERS = ["A", "B", "C", "D", "E", "F"];
  var ABSORB_HZ = [125, 250, 500, 1000, 2000, 4000, 8000];
  var MARK_HZ = [125, 250, 500, 1000, 2000, 4000, 8000];
  var META = {
    A: {
      label: "Left wall", short: "Left", role: "wall",
      face: "left", netSlot: "left", facing: "\u2212X", arrow: "\u2190",
      compass: "West", hint: "\u2212X crossings (ASSUMED)",
      color: "#38bdf8"
    },
    B: {
      label: "Front / Ahead", short: "Front", role: "wall",
      face: "front", netSlot: "front", facing: "+Z", arrow: "\u2191",
      compass: "North (+Z)", hint: "+Z crossings (ASSUMED)",
      color: "#2dd4bf"
    },
    C: {
      label: "Right wall", short: "Right", role: "wall",
      face: "right", netSlot: "right", facing: "+X", arrow: "\u2192",
      compass: "East", hint: "+X crossings (ASSUMED)",
      color: "#a78bfa"
    },
    D: {
      label: "Back / Behind", short: "Back", role: "wall",
      face: "back", netSlot: "back", facing: "\u2212Z", arrow: "\u2193",
      compass: "South", hint: "\u2212Z crossings (ASSUMED)",
      color: "#fb7185"
    },
    E: {
      label: "Floor", short: "Floor", role: "floor",
      face: "floor", netSlot: "floor", facing: "\u2212Y", arrow: "\u2193",
      compass: "Down", hint: "\u2212Y crossings (ASSUMED)",
      color: "#fbbf24"
    },
    F: {
      label: "Ceiling", short: "Ceiling", role: "ceiling",
      face: "ceiling", netSlot: "ceil", facing: "+Y", arrow: "\u2191",
      compass: "Up", hint: "+Y crossings (ASSUMED)",
      color: "#e2e8f0"
    }
  };

  /** Unfolded room net order (cross): Ceiling / Left-Front-Right-Back / Floor */
  var NET_LAYOUT = [
    { letter: "F", slot: "ceil" },
    { letter: "A", slot: "left" },
    { letter: "B", slot: "front" },
    { letter: "C", slot: "right" },
    { letter: "D", slot: "back" },
    { letter: "E", slot: "floor" }
  ];

  function defaultSurface(letter) {
    return {
      letter: letter,
      label: META[letter].label,
      hint: META[letter].hint,
      absorb_hz: ABSORB_HZ.slice(),
      absorb: [0.05, 0.06, 0.08, 0.10, 0.14, 0.18, 0.22],
      eq: {
        low_shelf_hz: 200, low_shelf_db: 0,
        high_shelf_hz: 5000, high_shelf_db: 0,
        peak_hz: 1000, peak_db: 0, peak_q: 1
      },
      diffusion: 0.15,
      assumed: true
    };
  }

  function defaultSurfaces() {
    var out = {};
    LETTERS.forEach(function (L) { out[L] = defaultSurface(L); });
    return out;
  }

  function cloneColour(col) {
    if (!col) return null;
    return JSON.parse(JSON.stringify(col));
  }

  function fmtHz(f) {
    if (f >= 1000) {
      var k = f / 1000;
      return (Math.abs(k - Math.round(k)) < 1e-6 ? String(Math.round(k)) : k.toFixed(1)) + "k";
    }
    return String(Math.round(f));
  }

  function shelfLow(f, f0, gdb) {
    var gain = Math.pow(10, gdb / 20), r = f / Math.max(f0, 1), t = 1 / (1 + r * r);
    return 1 + (gain - 1) * t;
  }
  function shelfHigh(f, f0, gdb) {
    var gain = Math.pow(10, gdb / 20), r = f0 / Math.max(f, 1), t = 1 / (1 + r * r);
    return 1 + (gain - 1) * t;
  }
  function peakResp(f, f0, gdb, q) {
    var gain = Math.pow(10, gdb / 20);
    var x = (f / Math.max(f0, 1) - f0 / Math.max(f, 1)) * q;
    var t = 1 / (1 + x * x);
    return 1 + (gain - 1) * t;
  }

  function interpAbsorb(hzList, absorb, f) {
    if (!hzList || !absorb || !hzList.length) return 0.1;
    if (f <= hzList[0]) return absorb[0];
    if (f >= hzList[hzList.length - 1]) return absorb[absorb.length - 1];
    for (var i = 0; i < hzList.length - 1; i++) {
      if (f >= hzList[i] && f <= hzList[i + 1]) {
        var t = (Math.log(f) - Math.log(hzList[i])) /
          (Mat