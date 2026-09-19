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
          (Math.log(hzList[i + 1]) - Math.log(hzList[i]));
        return absorb[i] + t * (absorb[i + 1] - absorb[i]);
      }
    }
    return absorb[absorb.length - 1];
  }

  /** ASSUMED: per-bounce transmission ≈ (1−α) × EQ linear gain → dB */
  function surfaceInfluenceDb(surf, f) {
    var eq = surf.eq || {};
    var alpha = interpAbsorb(surf.absorb_hz || ABSORB_HZ, surf.absorb || [], f);
    alpha = Math.max(0, Math.min(0.999, alpha));
    var m = (1 - alpha) *
      shelfLow(f, eq.low_shelf_hz || 200, eq.low_shelf_db || 0) *
      peakResp(f, eq.peak_hz || 1000, eq.peak_db || 0, eq.peak_q || 1) *
      shelfHigh(f, eq.high_shelf_hz || 5000, eq.high_shelf_db || 0);
    return 20 * Math.log(Math.max(m, 1e-6)) / Math.LN10;
  }

  function surfaceEqDb(surf, f) {
    var eq = surf.eq || {};
    var m = shelfLow(f, eq.low_shelf_hz || 200, eq.low_shelf_db || 0) *
      peakResp(f, eq.peak_hz || 1000, eq.peak_db || 0, eq.peak_q || 1) *
      shelfHigh(f, eq.high_shelf_hz || 5000, eq.high_shelf_db || 0);
    return 20 * Math.log(Math.max(m, 1e-6)) / Math.LN10;
  }

  function ColourSurfaces(opts) {
    this.getState = opts.getState;
    this.onChange = opts.onChange || function () {};
    this.selected = "A";
    this.colour = null;       // Now
    this.ghost = null;        // Last (previous Now after re-Render)
    this.holdA = null;
    this.holdB = null;
    this.refMode = "peak";    // "peak" | "1khz" — peak band or 1 kHz = 0 dB
    this.hoverIndex = -1;
    this._plotGeom = null;
    this.els = {
      cards: document.getElementById("surfaceCards"),
      title: document.getElementById("surfaceDetailTitle"),
      hint: document.getElementById("surfaceDetailHint"),
      absorbSliders: document.getElementById("absorbSliders"),
      eqControls: document.getElementById("eqControls"),
      diffusion: document.getElementById("diffusionSlider"),
      diffusionOut: document.getElementById("diffusionOut"),
      colourCanvas: document.getElementById("colourCanvas"),
      sparkCanvas: document.getElementById("colourSparkCanvas"),
      absorbCanvas: document.getElementById("absorbCanvas"),
      eqCanvas: document.getElementById("eqCanvas"),
      colourMeta: document.getElementById("colourMeta"),
      colourHover: document.getElementById("colourHover"),
      colourTooltip: document.getElementById("colourTooltip"),
      colourRefMode: document.getElementById("colourRefMode"),
      colourHoldA: document.getElementById("colourHoldA"),
      colourHoldB: document.getElementById("colourHoldB"),
      colourClear: document.getElementById("colourClearCompare"),
      colourLegend: document.getElementById("colourLegend"),
      sparkLabel: document.getElementById("colourSparkLabel"),
      surfacesPanel: document.getElementById("surfacesPanel"),
      roomNet: document.getElementById("roomNet"),
      faceBadge: document.getElementById("colourFaceBadge"),
      faceArrow: document.getElementById("colourFaceArrow"),
      faceName: document.getElementById("colourFaceName"),
      faceAxis: document.getElementById("colourFaceAxis"),
      // aliases for HTML id variants
      colourMeta: document.getElementById("colourMeta") || document.getElementById("colourMeta"),
      colourHover: document.getElementById("colourHover") || document.getElementById("colourHover")
    };
    // Prefer explicit meta/hover if present
    if (document.getElementById("colourMeta")) this.els.colourMeta = document.getElementById("colourMeta");
    if (document.getElementById("colourHover")) this.els.colourHover = document.getElementById("colourHover");
    this._buildRoomNet();
    this._buildCards();
    this._bindDiffusion();
    this._bindColourTools();
    this.select("A");
    this.drawColour();
  }

  ColourSurfaces.prototype.surfaces = function () {
    var st = this.getState();
    if (!st.surfaces) st.surfaces = defaultSurfaces();
    return st.surfaces;
  };

  ColourSurfaces.prototype._current = function () {
    return this.surfaces()[this.selected];
  };

  ColourSurfaces.prototype._buildRoomNet = function () {
    var self = this;
    var host = this.els.roomNet;
    if (!host) return;
    host.innerHTML = "";
    NET_LAYOUT.forEach(function (item) {
      var L = item.letter;
      var m = META[L];
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "rn-face rn-" + item.slot;
      btn.setAttribute("data-letter", L);
      btn.setAttribute("role", "option");
      btn.setAttribute("aria-label", L + " " + m.label + " faces " + m.facing);
      btn.title = m.label + " · faces " + m.facing + " · " + m.compass + " (ASSUMED)";
      btn.innerHTML =
        '<span class="rn-arrow" style="color:' + m.color + '">' + m.arrow + "</span>" +
        '<span class="rn-letter">' + L + "</span>" +
        '<span class="rn-name">' + m.short + "</span>" +
        '<span class="rn-facing">faces ' + m.facing + "</span>" +
        '<canvas class="rn-spark" width="120" height="28" aria-hidden="true"></canvas>';
      btn.addEventListener("click", function () { self.select(L); });
      host.appendChild(btn);
    });
    var compass = document.createElement("div");
    compass.className = "rn-compass";
    compass.innerHTML = "<span>N = Front (+Z)</span><span>ASSUMED net</span>";
    host.appendChild(compass);
  };

  ColourSurfaces.prototype._paintRoomNetSparks = function () {
    var host = this.els.roomNet;
    if (!host) return;
    var self = this;
    host.querySelectorAll(".rn-face").forEach(function (btn) {
      var L = btn.getAttribute("data-letter");
      var canvas = btn.querySelector("canvas.rn-spark");
      if (!canvas) return;
      var ctx = canvas.getContext("2d");
      var W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = "rgba(8,9,12,0.5)";
      ctx.fillRect(0, 0, W, H);
      var surf = self.surfaces()[L];
      var n = 32;
      var vals = [];
      for (var i = 0; i < n; i++) {
        var f = 40 * Math.pow(16000 / 40, i / (n - 1));
        vals.push(surfaceInfluenceDb(surf, f));
      }
      var vmin = Math.min.apply(null, vals), vmax = Math.max.apply(null, vals);
      var span = Math.max(1e-6, vmax - vmin);
      ctx.beginPath();
      ctx.strokeStyle = META[L].color;
      ctx.lineWidth = 1.4;
      for (var j = 0; j < n; j++) {
        var x = (W - 4) * j / (n - 1) + 2;
        var y = H - 3 - ((vals[j] - vmin) / span) * (H - 6);
        if (j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
    });
  };

  ColourSurfaces.prototype._syncOrientationUI = function (letter) {
    var m = META[letter];
    if (!m) return;
    if (this.els.faceArrow) this.els.faceArrow.textContent = m.arrow;
    if (this.els.faceArrow) this.els.faceArrow.style.color = m.color;
    if (this.els.faceName) this.els.faceName.textContent = letter + " \u00b7 " + m.short;
    if (this.els.faceAxis) {
      this.els.faceAxis.textContent = "faces " + m.facing + " \u00b7 " + m.compass + " \u00b7 ASSUMED";
    }
    if (this.els.faceBadge) {
      this.els.faceBadge.style.borderColor = m.color;
      this.els.faceBadge.dataset.letter = letter;
      this.els.faceBadge.dataset.face = m.face;
    }
    var net = this.els.roomNet;
    if (net) {
      net.querySelectorAll(".rn-face").forEach(function (b) {
        var on = b.getAttribute("data-letter") === letter;
        b.classList.toggle("active", on);
        b.setAttribute("aria-selected", on ? "true" : "false");
      });
    }
    if (this.els.sparkLabel) {
      this.els.sparkLabel.textContent =
        letter + " \u00b7 " + m.short + " \u00b7 faces " + m.facing + " \u00b7 absorb\u00d7EQ ASSUMED";
    }
    this._paintRoomNetSparks();
  };

  ColourSurfaces.prototype._buildCards = function () {
    var self = this;
    var host = this.els.cards;
    if (!host) return;
    host.innerHTML = "";
    LETTERS.forEach(function (L) {
      var m = META[L];
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "surface-card";
      btn.setAttribute("data-letter", L);
      btn.innerHTML =
        '<span class="sc-letter" style="color:' + m.color + '">' + L + "</span>" +
        '<span class="sc-label">' + m.short + "</span>" +
        '<span class="sc-facing">' + m.arrow + " " + m.facing + "</span>" +
        '<span class="sc-tag">ASSUMED</span>';
      btn.title = m.label + " · faces " + m.facing + " (" + m.compass + ")";
      btn.addEventListener("click", function () { self.select(L); });
      host.appendChild(btn);
    });
  };

  ColourSurfaces.prototype.select = function (letter) {
    this.selected = letter;
    var cards = this.els.cards ? this.els.cards.querySelectorAll(".surface-card") : [];
    cards.forEach(function (c) {
      c.classList.toggle("active", c.getAttribute("data-letter") === letter);
    });
    this._syncOrientationUI(letter);
    this._buildAbsorbSliders();
    this._buildEqControls();
    this._syncDiffusion();
    this.drawSurfaceGraphs();
    this.drawColour();
  };

  ColourSurfaces.prototype._buildAbsorbSliders = function () {
    var self = this;
    var host = this.els.absorbSliders;
    if (!host) return;
    host.innerHTML = "";
    var s = this._current();
    ABSORB_HZ.forEach(function (hz, i) {
      var row = document.createElement("label");
      row.className = "absorb-row";
      var val = s.absorb[i] != null ? s.absorb[i] : 0.1;
      row.innerHTML =
        '<span class="ab-hz">' + (hz >= 1000 ? (hz / 1000) + "k" : hz) + "</span>" +
        '<input type="range" min="0" max="1" step="0.01" value="' + val + '" />' +
        "<output>" + Number(val).toFixed(2) + "</output>";
      var input = row.querySelector("input");
      var out = row.querySelector("output");
      input.addEventListener("input", function () {
        var v = parseFloat(input.value);
        self._current().absorb[i] = v;
        out.textContent = v.toFixed(2);
        self.drawSurfaceGraphs();
        self._paintRoomNetSparks();
        self.drawColour();
        self.onChange();
      });
      host.appendChild(row);
    });
  };

  ColourSurfaces.prototype._buildEqControls = function () {
    var self = this;
    var host = this.els.eqControls;
    if (!host) return;
    host.innerHTML = "";
    var eq = this._current().eq;
    var specs = [
      { key: "low_shelf_db", label: "Low shelf dB", min: -18, max: 18, step: 0.5 },
      { key: "low_shelf_hz", label: "Low shelf Hz", min: 40, max: 800, step: 1 },
      { key: "peak_db", label: "Peak dB", min: -18, max: 18, step: 0.5 },
      { key: "peak_hz", label: "Peak Hz", min: 100, max: 8000, step: 1 },
      { key: "peak_q", label: "Peak Q", min: 0.3, max: 6, step: 0.05 },
      { key: "high_shelf_db", label: "High shelf dB", min: -18, max: 18, step: 0.5 },
      { key: "high_shelf_hz", label: "High shelf Hz", min: 1000, max: 16000, step: 10 }
    ];
    specs.forEach(function (sp) {
      var row = document.createElement("label");
      row.className = "eq-row";
      var val = eq[sp.key];
      row.innerHTML =
        "<span>" + sp.label + "</span>" +
        '<input type="range" min="' + sp.min + '" max="' + sp.max +
        '" step="' + sp.step + '" value="' + val + '" />' +
        "<output>" + (sp.key.indexOf("hz") >= 0 ? Math.round(val) : Number(val).toFixed(1)) +
        "</output>";
      var input = row.querySelector("input");
      var out = row.querySelector("output");
      input.addEventListener("input", function () {
        var v = parseFloat(input.value);
        eq[sp.key] = v;
        out.textContent = sp.key.indexOf("hz") >= 0 ? String(Math.round(v)) : v.toFixed(1);
        self.drawSurfaceGraphs();
        self._paintRoomNetSparks();
        self.drawColour();
        self.onChange();
      });
      host.appendChild(row);
    });
  };

  ColourSurfaces.prototype._bindDiffusion = function () {
    var self = this;
    var el = this.els.diffusion;
    if (!el || el._bound) return;
    el._bound = true;
    el.addEventListener("input", function () {
      var v = parseFloat(el.value);
      self._current().diffusion = v;
      if (self.els.diffusionOut) self.els.diffusionOut.textContent = v.toFixed(2);
      self.onChange();
    });
  };

  ColourSurfaces.prototype._syncDiffusion = function () {
    var v = this._current().diffusion;
    if (this.els.diffusion) this.els.diffusion.value = v;
    if (this.els.diffusionOut) this.els.diffusionOut.textContent = Number(v).toFixed(2);
  };

  ColourSurfaces.prototype._bindColourTools = function () {
    var self = this;
    var ref = this.els.colourRefMode;
    if (ref && !ref._bound) {
      ref._bound = true;
      ref.value = this.refMode;
      ref.addEventListener("change", function () {
        self.refMode = ref.value === "1khz" ? "1khz" : "peak";
        self.drawColour();
      });
    }
    if (this.els.colourHoldA && !this.els.colourHoldA._bound) {
      this.els.colourHoldA._bound = true;
      this.els.colourHoldA.addEventListener("click", function () {
        if (!self.colour) return;
        self.holdA = cloneColour(self.colour);
        self._updateLegend();
        self.drawColour();
      });
    }
    if (this.els.colourHoldB && !this.els.colourHoldB._bound) {
      this.els.colourHoldB._bound = true;
      this.els.colourHoldB.addEventListener("click", function () {
        if (!self.colour) return;
        self.holdB = cloneColour(self.colour);
        self._updateLegend();
        self.drawColour();
      });
    }
    if (this.els.colourClear && !this.els.colourClear._bound) {
      this.els.colourClear._bound = true;
      this.els.colourClear.addEventListener("click", function () {
        self.ghost = null;
        self.holdA = null;
        self.holdB = null;
        self._updateLegend();
        self.drawColour();
      });
    }
    var canvas = this.els.colourCanvas;
    if (canvas && !canvas._colourBound) {
      canvas._colourBound = true;
      canvas.addEventListener("mousemove", function (ev) { self._onColourMove(ev); });
      canvas.addEventListener("mouseleave", function () { self._onColourLeave(); });
    }
  };

  ColourSurfaces.prototype._updateLegend = function () {
    var leg = this.els.colourLegend;
    if (!leg) return;
    var last = leg.querySelector(".cleg.last");
    var ha = leg.querySelector(".cleg.holda");
    var hb = leg.querySelector(".cleg.holdb");
    if (last) last.classList.toggle("active", !!this.ghost);
    if (ha) ha.classList.toggle("active", !!this.holdA);
    if (hb) hb.classList.toggle("active", !!this.holdB);
  };

  /** Resolve relative levels for a colour payload under current refMode. */
  ColourSurfaces.prototype._levelsFor = function (col) {
    if (!col) return null;
    var hz = col.centres_hz || col.centers_hz;
    if (!hz) return null;
    if (this.refMode === "1khz") {
      if (col.levels_db_1khz) return { hz: hz, db: col.levels_db_1khz, ref: "1 kHz = 0 dB" };
      if (col.levels_db_abs) {
        var i1 = 0, best = Infinity;
        for (var i = 0; i < hz.length; i++) {
          var d = Math.abs(hz[i] - 1000);
          if (d < best) { best = d; i1 = i; }
        }
        var r = col.levels_db_abs[i1];
        return {
          hz: hz,
          db: col.levels_db_abs.map(function (v) { return v - r; }),
          ref: "1 kHz = 0 dB"
        };
      }
    }
    // peak (default)
    if (col.levels_db_peak) return { hz: hz, db: col.levels_db_peak, ref: "peak band = 0 dB" };
    if (col.levels_db) return { hz: hz, db: col.levels_db, ref: "peak band = 0 dB" };
    return null;
  };

  ColourSurfaces.prototype.setColour = function (colour) {
    // Promote previous Now → Last ghost when a new render arrives
    if (this.colour && colour) {
      this.ghost = cloneColour(this.colour);
    }
    this.colour = colour;
    this._updateLegend();
    this.drawColour();
  };

  ColourSurfaces.prototype._onColourMove = function (ev) {
    var canvas = this.els.colourCanvas;
    var geom = this._plotGeom;
    if (!canvas || !geom || !geom.n) return;
    var rect = canvas.getBoundingClientRect();
    var sx = canvas.width / rect.width;
    var sy = canvas.height / rect.height;
    var mx = (ev.clientX - rect.left) * sx;
    var my = (ev.clientY - rect.top) * sy;
    var best = -1, bestD = Infinity;
    for (var i = 0; i < geom.n; i++) {
      var dx = mx - geom.xAt(i);
      if (Math.abs(dx) < bestD) { bestD = Math.abs(dx); best = i; }
    }
    if (best < 0) return;
    this.hoverIndex = best;
    var hz = geom.hz[best];
    var db = geom.db[best];
    var txt = fmtHz(hz) + " Hz  \u00b7  " +
      (db >= 0 ? "+" : "") + Number(db).toFixed(1) + " dB";
    if (this.els.colourHover) {
      this.els.colourHover.hidden = false;
      this.els.colourHover.textContent = txt + "  \u00b7  " + geom.refLabel;
    }
    var tip = this.els.colourTooltip;
    if (tip) {
      tip.hidden = false;
      tip.textContent = txt;
      var left = ((geom.xAt(best) / canvas.width) * 100);
      tip.style.left = Math.max(4, Math.min(90, left)) + "%";
      tip.style.top = Math.max(8, (my / canvas.height) * 100 - 8) + "%";
    }
    this.drawColour();
  };

  ColourSurfaces.prototype._onColourLeave = function () {
    this.hoverIndex = -1;
    if (this.els.colourHover) this.els.colourHover.hidden = true;
    if (this.els.colourTooltip) this.els.colourTooltip.hidden = true;
    this.drawColour();
  };

  ColourSurfaces.prototype._drawRoomNetInset = function (ctx, W, padR, padT) {
    /* Tiny unfolded net in the Colour plot corner — selected face lit */
    var cell = 22, gap = 3;
    var netW = cell * 4 + gap * 3;
    var netH = cell * 3 + gap * 2;
    var ox = W - padR - netW - 4;
    var oy = padT + 4;
    ctx.save();
    ctx.globalAlpha = 0.92;
    ctx.fillStyle = "rgba(8,9,12,0.72)";
    ctx.strokeStyle = "#252a38";
    ctx.lineWidth = 1;
    roundRect(ctx, ox - 6, oy - 6, netW + 12, netH + 22, 6);
    ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#6b7388";
    ctx.font = "9px system-ui,sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("Room net", ox, oy - 1);
    var slots = {
      ceil:  [1, 0], left: [0, 1], front: [1, 1],
      right: [2, 1], back: [3, 1], floor: [1, 2]
    };
    var self = this;
    LETTERS.forEach(function (L) {
      var m = META[L];
      var rc = slots[m.netSlot];
      if (!rc) return;
      var x = ox + rc[0] * (cell + gap);
      var y = oy + 10 + rc[1] * (cell + gap);
      var on = L === self.selected;
      ctx.fillStyle = on ? m.color : "#1a1f2b";
      ctx.globalAlpha = on ? 0.95 : 0.55;
      ctx.fillRect(x, y, cell, cell);
      ctx.strokeStyle = on ? m.color : "#2a3144";
      ctx.globalAlpha = 1;
      ctx.strokeRect(x + 0.5, y + 0.5, cell - 1, cell - 1);
      ctx.fillStyle = on ? "#0a0b0e" : "#8b92a5";
      ctx.font = "bold 10px system-ui,sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(L, x + cell / 2, y + cell / 2 + 3);
    });
    ctx.restore();
  };

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  ColourSurfaces.prototype.drawColour = function () {
    var canvas = this.els.colourCanvas;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var W = canvas.width, H = canvas.height;
    ctx.fillStyle = "#0a0b0e";
    ctx.fillRect(0, 0, W, H);

    var nowL = this._levelsFor(this.colour);
    if (!nowL) {
      this._plotGeom = null;
      ctx.fillStyle = "#a8b0c4";
      ctx.font = "600 15px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Render to see Colour", W / 2, H / 2 - 6);
      ctx.font = "12px Segoe UI, system-ui, sans-serif";
      ctx.fillStyle = "#6b7388";
      ctx.fillText("1/3-octave magnitude of the wet IR", W / 2, H / 2 + 14);
      ctx.textAlign = "start";
      if (this.els.colourMeta) this.els.colourMeta.textContent = "Render to see Colour";
      this._drawSparkline();
      return;
    }

    var hz = nowL.hz;
    var db = nowL.db;
    var n = hz.length;
    var padL = 56, padR = 18, padT = 28, padB = 40;
    var plotW = W - padL - padR, plotH = H - padT - padB;
    var vmin = -48, vmax = 6;
    // Autoscale a touch from Now + overlays
    function collect(levels) {
      if (!levels) return;
      for (var i = 0; i < levels.db.length; i++) {
        var v = levels.db[i];
        if (v > vmax) vmax = Math.min(12, v + 1);
        if (v < vmin) vmin = Math.max(-72, v - 2);
      }
    }
    collect(nowL);
    collect(this._levelsFor(this.ghost));
    collect(this._levelsFor(this.holdA));
    collect(this._levelsFor(this.holdB));

    function xAt(i) { return padL + (plotW * i) / Math.max(1, n - 1); }
    function yAt(v) {
      var t = (v - vmax) / (vmin - vmax);
      t = Math.max(0, Math.min(1, t));
      return padT + t * plotH;
    }
    this._plotGeom = {
      n: n, hz: hz, db: db, xAt: xAt, yAt: yAt,
      padL: padL, padT: padT, plotW: plotW, plotH: plotH,
      refLabel: nowL.ref
    };

    // Grid
    ctx.strokeStyle = "#1e2230";
    ctx.lineWidth = 1;
    var dbMarks = [];
    for (var g = Math.ceil(vmin / 6) * 6; g <= vmax; g += 6) dbMarks.push(g);
    if (dbMarks.indexOf(0) < 0) dbMarks.push(0);
    dbMarks.sort(function (a, b) { return a - b; });
    dbMarks.forEach(function (g) {
      var y = yAt(g);
      ctx.beginPath();
      ctx.strokeStyle = g === 0 ? "#2a3144" : "#1e2230";
      ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
    });

    // Engineer frequency marks at octave centres
    ctx.fillStyle = "#6b7388";
    ctx.font = "11px system-ui,sans-serif";
    ctx.textAlign = "center";
    MARK_HZ.forEach(function (f) {
      var best = 0, bd = Infinity;
      for (var i = 0; i < n; i++) {
        var d = Math.abs(hz[i] - f);
        if (d < bd) { bd = d; best = i; }
      }
      if (bd > f * 0.2) return;
      var x = xAt(best);
      ctx.strokeStyle = "#252a38";
      ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, padT + plotH); ctx.stroke();
      ctx.fillStyle = "#8b92a5";
      ctx.fillText(fmtHz(f), x, H - 14);
    });
    ctx.textAlign = "start";

    // dB labels
    ctx.fillStyle = "#8b92a5";
    ctx.font = "11px system-ui,sans-serif";
    dbMarks.forEach(function (g) {
      if (g % 12 !== 0 && g !== 0) return;
      var lab = (g > 0 ? "+" : "") + g;
      ctx.fillText(lab, 8, yAt(g) + 4);
    });
    ctx.fillStyle = "#6b7388";
    ctx.font = "10px system-ui,sans-serif";
    ctx.fillText("dB", 10, padT - 10);

    // Surface influence: dim bars where selected surface absorbs more;
    // overlay influence curve (ASSUMED absorb×EQ transmission)
    var surf = this._current();
    var barW = Math.max(2, plotW / n - 2);
    var influence = [];
    for (var ii = 0; ii < n; ii++) {
      influence.push(surfaceInfluenceDb(surf, hz[ii]));
    }
    var iMin = Math.min.apply(null, influence);
    var iMax = Math.max.apply(null, influence);
    var iSpan = Math.max(1e-6, iMax - iMin);

    for (var i = 0; i < n; i++) {
      var x = xAt(i), y = yAt(db[i]), y0 = yAt(0);
      // Dim strength from absorption (higher α → dimmer teal)
      var alpha = interpAbsorb(surf.absorb_hz || ABSORB_HZ, surf.absorb || [], hz[i]);
      var dim = 0.22 + 0.28 * (1 - Math.max(0, Math.min(1, alpha)));
      ctx.fillStyle = "rgba(45, 212, 191, " + dim.toFixed(3) + ")";
      ctx.fillRect(x - barW / 2, Math.min(y, y0), barW, Math.abs(y0 - y) + 1);
      // Warm highlight strip proportional to relative influence
      var warm = (influence[i] - iMin) / iSpan;
      if (warm > 0.55) {
        ctx.fillStyle = "rgba(251, 191, 36, " + (0.12 + 0.25 * (warm - 0.55)).toFixed(3) + ")";
        ctx.fillRect(x - barW / 2, padT, barW, plotH);
      }
    }

    function strokeCurve(levels, style, width, dash) {
      if (!levels) return;
      ctx.save();
      ctx.strokeStyle = style;
      ctx.lineWidth = width;
      ctx.setLineDash(dash || []);
      ctx.beginPath();
      for (var j = 0; j < levels.db.length; j++) {
        var xx = xAt(j), yy = yAt(levels.db[j]);
        if (j === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
      }
      ctx.stroke();
      ctx.restore();
    }

    // Overlays first (under Now)
    strokeCurve(this._levelsFor(this.holdA), "rgba(251, 191, 36, 0.85)", 1.6, [5, 4]);
    strokeCurve(this._levelsFor(this.holdB), "rgba(167, 139, 250, 0.9)", 1.6, [5, 4]);
    strokeCurve(this._levelsFor(this.ghost), "rgba(148, 163, 184, 0.75)", 1.8, [3, 4]);

    // Now curve
    strokeCurve(nowL, "#2dd4bf", 2.4, null);

    // Surface influence curve (secondary, amber) — scaled into dB plot as relative shape
    // Map influence into a thin overlay near bottom of plot for readability
    ctx.save();
    ctx.strokeStyle = "rgba(251, 191, 36, 0.55)";
    ctx.lineWidth = 1.4;
    ctx.setLineDash([2, 3]);
    ctx.beginPath();
    for (var k = 0; k < n; k++) {
      // Place influence as offset from 0 using a gentle scale (±12 dB visual)
      var idb = influence[k];
      // show absolute transmission dB clamped into plot
      var yy = yAt(Math.max(vmin + 2, Math.min(vmax - 1, idb)));
      var xx = xAt(k);
      if (k === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
    }
    ctx.stroke();
    ctx.restore();

    // Hover crosshair + marker
    if (this.hoverIndex >= 0 && this.hoverIndex < n) {
      var hi = this.hoverIndex;
      var hx = xAt(hi), hy = yAt(db[hi]);
      ctx.strokeStyle = "rgba(232, 236, 245, 0.35)";
      ctx.setLineDash([2, 3]);
      ctx.beginPath(); ctx.moveTo(hx, padT); ctx.lineTo(hx, padT + plotH); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = "#e8ecf5";
      ctx.beginPath(); ctx.arc(hx, hy, 4.2, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#2dd4bf";
      ctx.beginPath(); ctx.arc(hx, hy, 2.2, 0, Math.PI * 2); ctx.fill();
    }

    // Meta
    if (this.els.colourMeta) {
      var refTxt = this.refMode === "1khz" ? "1 kHz = 0 dB" : "peak band = 0 dB";
      var bits = [
        "1/3-octave",
        n + " bands",
        refTxt,
        "Now vs Last" + (this.ghost ? "" : " (no Last yet)"),
        "Surface " + this.selected + " influence ASSUMED"
      ];
      if (this.holdA) bits.push("Hold A");
      if (this.holdB) bits.push("Hold B");
      this.els.colourMeta.textContent = bits.join(" \u00b7 ");
    }

        this._drawRoomNetInset(ctx, W, padR, padT);
    this._drawSparkline();
  };

  ColourSurfaces.prototype._drawSparkline = function () {
    var canvas = this.els.sparkCanvas;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var W = canvas.width, H = canvas.height;
    ctx.fillStyle = "#08090c";
    ctx.fillRect(0, 0, W, H);
    var surf = this._current();
    var padL = 56, padR = 18, padT = 10, padB = 14;
    var plotW = W - padL - padR, plotH = H - padT - padB;
    var freqs = [];
    for (var i = 0; i < 96; i++) freqs.push(40 * Math.pow(20000 / 40, i / 95));
    var eqDbs = freqs.map(function (f) { return surfaceEqDb(surf, f); });
    var absDbs = freqs.map(function (f) {
      var a = interpAbsorb(surf.absorb_hz || ABSORB_HZ, surf.absorb || [], f);
      return 20 * Math.log(Math.max(1 - a, 1e-6)) / Math.LN10;
    });
    var all = eqDbs.concat(absDbs);
    var vmax = Math.max(6, Math.max.apply(null, all) + 1);
    var vmin = Math.min(-18, Math.min.apply(null, all) - 1);
    function xAt(i) { return padL + (plotW * i) / (freqs.length - 1); }
    function yAt(v) {
      var t = (v - vmax) / (vmin - vmax);
      return padT + Math.max(0, Math.min(1, t)) * plotH;
    }
    // zero line
    ctx.strokeStyle = "#1e2230";
    ctx.beginPath(); ctx.moveTo(padL, yAt(0)); ctx.lineTo(W - padR, yAt(0)); ctx.stroke();
    // absorb transmission (dim)
    ctx.strokeStyle = "rgba(148, 163, 184, 0.55)";
    ctx.lineWidth = 1.2;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    for (var j = 0; j < absDbs.length; j++) {
      var x = xAt(j), y = yAt(absDbs[j]);
      if (j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.setLineDash([]);
    // EQ
    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    for (var k = 0; k < eqDbs.length; k++) {
      var xx = xAt(k), yy = yAt(eqDbs[k]);
      if (k === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
    }
    ctx.stroke();
    // octave ticks shared with main plot
    ctx.fillStyle = "#6b7388";
    ctx.font = "9px system-ui";
    ctx.textAlign = "center";
    MARK_HZ.forEach(function (f) {
      var best = 0, bd = Infinity;
      for (var i = 0; i < freqs.length; i++) {
        var d = Math.abs(freqs[i] - f);
        if (d < bd) { bd = d; best = i; }
      }
      ctx.fillText(fmtHz(f), xAt(best), H - 3);
    });
    ctx.textAlign = "start";
    ctx.fillStyle = "#8b92a5";
    ctx.font = "9px system-ui";
    ctx.fillText("EQ", 8, 12);
    ctx.fillStyle = "#6b7388";
    ctx.fillText("1\u2212\u03b1", 8, 24);
  };

  ColourSurfaces.prototype.drawSurfaceGraphs = function () {
    this._drawAbsorb();
    this._drawEq();
  };

  ColourSurfaces.prototype._drawAbsorb = function () {
    var canvas = this.els.absorbCanvas;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var W = canvas.width, H = canvas.height, pad = 16;
    var s = this._current();
    ctx.fillStyle = "#0a0b0e";
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#1e2230";
    for (var g = 0; g <= 4; g++) {
      var gy = pad + ((H - 2 * pad) * g) / 4;
      ctx.beginPath(); ctx.moveTo(pad, gy); ctx.lineTo(W - pad, gy); ctx.stroke();
    }
    ctx.beginPath();
    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 2;
    for (var j = 0; j < ABSORB_HZ.length; j++) {
      var xx = pad + ((W - 2 * pad) * j) / (ABSORB_HZ.length - 1);
      var yy = pad + (H - 2 * pad) * (1 - s.absorb[j]);
      if (j === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
    }
    ctx.stroke();
    for (var k = 0; k < ABSORB_HZ.length; k++) {
      var px = pad + ((W - 2 * pad) * k) / (ABSORB_HZ.length - 1);
      var py = pad + (H - 2 * pad) * (1 - s.absorb[k]);
      ctx.fillStyle = "#fbbf24";
      ctx.beginPath(); ctx.arc(px, py, 3.5, 0, Math.PI * 2); ctx.fill();
    }
    ctx.fillStyle = "#8b92a5";
    ctx.font = "10px system-ui";
    ctx.fillText("\u03b1 0\u21921", 8, 12);
  };

  ColourSurfaces.prototype._drawEq = function () {
    var canvas = this.els.eqCanvas;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var W = canvas.width, H = canvas.height, pad = 16;
    var eq = this._current().eq;
    ctx.fillStyle = "#0a0b0e";
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#1e2230";
    for (var g = 0; g <= 4; g++) {
      var gy = pad + ((H - 2 * pad) * g) / 4;
      ctx.beginPath(); ctx.moveTo(pad, gy); ctx.lineTo(W - pad, gy); ctx.stroke();
    }
    var freqs = [];
    for (var i = 0; i < 64; i++) freqs.push(40 * Math.pow(16000 / 40, i / 63));
    var dbs = freqs.map(function (f) { return surfaceEqDb({ eq: eq }, f); });
    ctx.beginPath();
    ctx.strokeStyle = "#60a5fa";
    ctx.lineWidth = 2;
    for (var j = 0; j < dbs.length; j++) {
      var x = pad + ((W - 2 * pad) * j) / (dbs.length - 1);
      var t = Math.max(0, Math.min(1, (dbs[j] + 18) / 36));
      var y = pad + (H - 2 * pad) * (1 - t);
      if (j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.fillStyle = "#8b92a5";
    ctx.font = "10px system-ui";
    ctx.fillText("dB", 8, 12);
  };

  ColourSurfaces.prototype.setMode = function (mode) {
    if (this.els.surfacesPanel) {
      this.els.surfacesPanel.classList.toggle("dimmed", mode === "colour");
    }
  };

  global.ColourSurfaces = ColourSurfaces;
  global.ColourSurfacesDefaults = {
    defaultSurfaces: defaultSurfaces,
    LETTERS: LETTERS,
    META: META
  };
})(window);
