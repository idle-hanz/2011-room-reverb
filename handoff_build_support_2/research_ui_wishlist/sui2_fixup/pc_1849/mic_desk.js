/* 2011 Room Reverb — Mic desk: zoomed Top / Side / 3D + L/C/R polars */
(function (global) {
  "use strict";

  var COLORS = {
    bg: "#0a0b0e",
    room: "rgba(58,65,85,0.45)",
    grid: "rgba(255,255,255,0.05)",
    stand: "#60a5fa",
    L: "#a78bfa",
    C: "#2dd4bf",
    R: "#34d399",
    src: "#fbbf24",
    yaw: "#f59e0b",
    text: "#8b92a5",
    ink: "#e8eaef"
  };

  /* Larger deliberate hit targets (body vs yaw ring). */
  var HIT_BODY = 40;
  var HIT_STAND = 44;
  var HIT_SIDE = 40;
  var HIT_YAW = 28;
  var YAW_RING_M = 0.42;
  var DRAG_THRESH = 5;

  function ringColor(i, n) {
    var P = global.FreqPalette;
    if (P) return P.hexAt(i, n || 8);
    return "#e11d48";
  }

  function patternGain(theta, family, polar) {
    var RM = global.RoomMath;
    if (RM && RM.polarGain) return RM.polarGain(theta, family, polar);
    var p = String(family || "cardioid").toLowerCase();
    if (p === "bi" || p === "fig8") return Math.cos(theta);
    var d = Math.max(0, Math.min(1, Number(polar) || 0));
    var a = d <= 0.5 ? 1 - d : 0.5 - (d - 0.5) * 0.26;
    return a + (1 - a) * Math.cos(theta);
  }

  function familyOf(s, cap) {
    var k = "family_" + cap;
    if (s[k]) return s[k];
    var pat = s["pattern_" + cap] || "cardioid";
    return (pat === "fig8") ? "bi" : "cardioid";
  }

  function polarOf(s, cap) {
    var k = "polar_" + cap;
    if (s[k] != null && isFinite(Number(s[k]))) return Number(s[k]);
    var pat = s["pattern_" + cap] || "cardioid";
    if (pat === "omni") return 0;
    if (pat === "supercardioid") return 1;
    return 0.5;
  }

  function fmtYaw(deg) {
    var n = Math.round(Number(deg) || 0);
    if (n > 0) return "+" + n + "\u00b0";
    if (n < 0) return "\u2212" + Math.abs(n) + "\u00b0";
    return "0\u00b0";
  }

  function hexRgba(hex, a) {
    var r = parseInt(hex.slice(1, 3), 16);
    var g = parseInt(hex.slice(3, 5), 16);
    var b = parseInt(hex.slice(5, 7), 16);
    return "rgba(" + r + "," + g + "," + b + "," + a + ")";
  }

  function create(opts) {
    opts = opts || {};
    var topCanvas = opts.topCanvas;
    var sideCanvas = opts.sideCanvas;
    var view3dCanvas = opts.view3dCanvas || null;
    var polarL = opts.polarL || null;
    var polarC = opts.polarC || null;
    var polarR = opts.polarR || null;
    var getState = opts.getState;
    var setState = opts.setState;
    var onChange = opts.onChange || function () {};
    var onPolar = opts.onPolar || null;
    var RoomMath = opts.RoomMath || global.RoomMath;

    var tctx = topCanvas.getContext("2d");
    var drag = null;
    var hover = null;
    var selected = null;
    var planeMode = "top";
    var viewZoom = 1;
    var sideAz = 0;

    function dpr() {
      return Math.min(window.devicePixelRatio || 1, 2);
    }
    function uiPx(n) {
      return n * dpr();
    }
    function fitCanvas(canvas) {
      if (!canvas) return;
      var rect = canvas.getBoundingClientRect();
      if (rect.width < 2 || rect.height < 2) return;
      var w = Math.max(2, Math.floor(rect.width * dpr()));
      var h = Math.max(2, Math.floor(rect.height * dpr()));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
    }
    var topLay = null;
    var sideLay = null;
    var view3d = null;
    var liveReadout = "";
    var polarField = null;

    function ensureView3d() {
      if (view3d || !view3dCanvas || !global.Room3D) return view3d;
      var rect = view3dCanvas.getBoundingClientRect();
      if (rect.width < 2 || rect.height < 2) return null;
      view3d = global.Room3D.create({
        canvas: view3dCanvas,
        getState: getState,
        setState: setState,
        onChange: onChange,
        RoomMath: RoomMath,
        focusMic: true
      });
      return view3d;
    }

    function canvasPos(canvas, evt) {
      var r = canvas.getBoundingClientRect();
      return {
        x: (evt.clientX - r.left) * (canvas.width / r.width),
        y: (evt.clientY - r.top) * (canvas.height / r.height)
      };
    }

    function geoOf() {
      return RoomMath.compute(getState());
    }

    function setCursor(canvas, kind) {
      if (!kind) {
        canvas.style.cursor = "grab";
        return;
      }
      if (String(kind).indexOf("yaw") === 0) canvas.style.cursor = "crosshair";
      else canvas.style.cursor = drag ? "grabbing" : "grab";
    }

    function topFrame(geo) {
      var s = geo.state;
      var half = Math.max(s.space * 0.5, 0.05);
      var padM = Math.max(0.55, half + 0.35, 0.9);
      var cx = s.mcx;
      var cz = s.mcz;
      var x0 = cx - padM;
      var x1 = cx + padM;
      var z0 = cz - padM;
      var z1 = cz + padM;
      if (geo.source) {
        var dx = Math.abs(geo.source.x - cx);
        var dz = Math.abs(geo.source.z - cz);
        if (dx < padM * 2.2 && dz < padM * 2.2) {
          x0 = Math.min(x0, geo.source.x - 0.25);
          x1 = Math.max(x1, geo.source.x + 0.25);
          z0 = Math.min(z0, geo.source.z - 0.25);
          z1 = Math.max(z1, geo.source.z + 0.25);
        }
      }
      var zoom = Math.max(0.55, Math.min(8, viewZoom || 1));
      var spanX = Math.max(0.32, (x1 - x0) / zoom);
      var spanZ = Math.max(0.32, (z1 - z0) / zoom);
      x0 = cx - spanX * 0.5;
      z0 = cz - spanZ * 0.5;
      var cw = topCanvas.width;
      var ch = topCanvas.height;
      var margin = 36;
      var scale = Math.min((cw - margin * 2) / spanX, (ch - margin * 2) / spanZ);
      var rw = spanX * scale;
      var rh = spanZ * scale;
      return {
        x0: x0, z0: z0, spanX: spanX, spanZ: spanZ, scale: scale,
        ox: (cw - rw) / 2, oy: (ch - rh) / 2 + 2, rw: rw, rh: rh
      };
    }

    function alongOf(x, z, geo) {
      var dx = x - geo.state.mcx;
      var dz = z - geo.state.mcz;
      return dx * Math.sin(sideAz) + dz * Math.cos(sideAz);
    }

    function sideFrame(geo) {
      var s = geo.state;
      var canvas = topCanvas;
      var alongs = [
        alongOf(geo.mic_left.x, geo.mic_left.z, geo),
        alongOf(geo.mic_right.x, geo.mic_right.z, geo),
        alongOf(geo.mic_centre.x, geo.mic_centre.z, geo),
        alongOf(geo.source.x, geo.source.z, geo),
        -0.7, 0.7
      ];
      var a0 = Math.min.apply(null, alongs);
      var a1 = Math.max.apply(null, alongs);
      var pad = Math.max(0.45, s.space * 0.55 + 0.25);
      a0 -= pad;
      a1 += pad;
      var ys = [geo.mic_left.y, geo.mic_right.y, geo.mic_centre.y, geo.source.y, 0];
      var yLo0 = Math.min.apply(null, ys);
      var yHi0 = Math.max.apply(null, ys);
      var yPad = Math.max(0.45, Math.min(s.H * 0.35, 0.8));
      var yLo = Math.max(0, yLo0 - yPad);
      var yHi = Math.min(s.H, yHi0 + yPad);
      if (yHi - yLo < 1.0) {
        var midY = 0.5 * (yLo + yHi);
        yLo = Math.max(0, midY - 0.55);
        yHi = Math.min(s.H, midY + 0.55);
      }
      var zoom = Math.max(0.55, Math.min(8, viewZoom || 1));
      var spanZ = Math.max(0.4, (a1 - a0) / zoom);
      var spanY = Math.max(0.4, (yHi - yLo) / zoom);
      var midA = 0;
      var z0 = midA - spanZ * 0.5;
      yLo = Math.max(0, ((yLo + yHi) * 0.5) - spanY * 0.5);
      var cw = canvas.width;
      var ch = canvas.height;
      var marginX = 44;
      var marginY = 28;
      var scale = Math.min((cw - marginX * 2) / spanZ, (ch - marginY * 2) / spanY);
      var rw = spanZ * scale;
      var rh = spanY * scale;
      return {
        z0: z0, y0: yLo, spanZ: spanZ, spanY: spanY, scale: scale,
        ox: (cw - rw) / 2, oy: (ch - rh) / 2, rw: rw, rh: rh
      };
    }

    function topToPx(x, z, lay) {
      return {
        px: lay.ox + (x - lay.x0) * lay.scale,
        py: lay.oy + (lay.spanZ - (z - lay.z0)) * lay.scale
      };
    }
    function topToM(px, py, lay) {
      return {
        x: lay.x0 + (px - lay.ox) / lay.scale,
        z: lay.z0 + lay.spanZ - (py - lay.oy) / lay.scale
      };
    }
    function sideToPx(z, y, lay) {
      return {
        px: lay.ox + (z - lay.z0) * lay.scale,
        py: lay.oy + (lay.spanY - (y - lay.y0)) * lay.scale
      };
    }
    function sideToM(px, py, lay) {
      return {
        z: lay.z0 + (px - lay.ox) / lay.scale,
        y: lay.y0 + lay.spanY - (py - lay.oy) / lay.scale
      };
    }

    function drawHandle(ctx, px, py, color, label, active, hovered, radius) {
      var r = radius || (active ? 13 : hovered ? 12 : 10);
      ctx.beginPath();
      ctx.arc(px, py, r + 6, 0, Math.PI * 2);
      ctx.fillStyle = active || hovered ? "rgba(255,255,255,0.16)" : "rgba(255,255,255,0.04)";
      ctx.fill();
      if (active || hovered) {
        ctx.beginPath();
        ctx.arc(px, py, r + 3, 0, Math.PI * 2);
        ctx.strokeStyle = active ? "rgba(255,255,255,0.55)" : "rgba(255,255,255,0.28)";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.lineWidth = 2.2;
      ctx.strokeStyle = "#0a0b0e";
      ctx.stroke();
      if (label) {
        ctx.fillStyle = COLORS.ink;
        ctx.font = "600 11px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(label, px, py - r - 7);
      }
    }

    function yawRingPx(lay) {
      return Math.max(36, Math.min(88, YAW_RING_M * lay.scale));
    }

    function yawKnobOf(geo, which, lay) {
      var look = which === "L" ? geo.look_l : which === "R" ? geo.look_r : geo.look_c;
      var mic = which === "L" ? geo.mic_left : which === "R" ? geo.mic_right : geo.mic_centre;
      var p = topToPx(mic.x, mic.z, lay);
      var rr = yawRingPx(lay);
      return {
        ox: p.px, oy: p.py,
        px: p.px + look.x * rr,
        py: p.py - look.z * rr,
        r: rr,
        look: look
      };
    }

    function drawFrontDot(ctx, geo, which, color, kind) {
      var lay = topLay;
      var k = yawKnobOf(geo, which, lay);
      var active = selected === kind || (drag && drag.kind === kind);
      var hovered = hover === kind;
      ctx.beginPath();
      ctx.moveTo(k.ox, k.oy);
      ctx.lineTo(k.px, k.py);
      ctx.strokeStyle = hexRgba(color, active || hovered ? 0.95 : 0.7);
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(k.px, k.py, active || hovered ? uiPx(12) : uiPx(10), 0, Math.PI * 2);
      ctx.fillStyle = COLORS.yaw;
      ctx.fill();
      ctx.strokeStyle = "#0a0b0e";
      ctx.lineWidth = 1.4;
      ctx.stroke();
    }

    function drawLookCone(ctx, px, py, look, color, scale, soft) {
      var len = soft ? 0.38 : 0.48;
      var spread = soft ? 0.55 : 0.72;
      var tipX = px + look.x * len * scale;
      var tipY = py - look.z * len * scale;
      var lx = look.x * Math.cos(spread) - look.z * Math.sin(spread);
      var lz = look.z * Math.cos(spread) + look.x * Math.sin(spread);
      var rx = look.x * Math.cos(-spread) - look.z * Math.sin(-spread);
      var rz = look.z * Math.cos(-spread) + look.x * Math.sin(-spread);
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(px + lx * len * 0.85 * scale, py - lz * len * 0.85 * scale);
      ctx.lineTo(tipX, tipY);
      ctx.lineTo(px + rx * len * 0.85 * scale, py - rz * len * 0.85 * scale);
      ctx.closePath();
      ctx.fillStyle = hexRgba(color, 0.14);
      ctx.strokeStyle = hexRgba(color, 0.45);
      ctx.lineWidth = 1;
      ctx.fill();
      ctx.stroke();
    }

    function drawLiveReadout(ctx, cw) {
      if (!liveReadout) return;
      ctx.font = "700 12px Segoe UI, system-ui, sans-serif";
      var tw = ctx.measureText(liveReadout).width;
      var x = Math.max(10, (cw - tw) / 2 - 10);
      var y = 36;
      ctx.fillStyle = "rgba(10,11,14,0.82)";
      ctx.strokeStyle = "rgba(245,158,11,0.55)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(x, y - 14, tw + 20, 22, 6);
      else ctx.rect(x, y - 14, tw + 20, 22);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = COLORS.yaw;
      ctx.textAlign = "left";
      ctx.fillText(liveReadout, x + 10, y + 2);
    }

    function drawTop(geo) {
      fitCanvas(topCanvas);
      var ctx = tctx;
      var cw = topCanvas.width;
      var ch = topCanvas.height;
      topLay = topFrame(geo);
      var lay = topLay;
      ctx.clearRect(0, 0, cw, ch);
      ctx.fillStyle = COLORS.bg;
      ctx.fillRect(0, 0, cw, ch);

      var roomTL = topToPx(0, geo.state.L, lay);
      var roomBR = topToPx(geo.state.W, 0, lay);
      ctx.strokeStyle = COLORS.room;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(
        Math.min(roomTL.px, roomBR.px),
        Math.min(roomTL.py, roomBR.py),
        Math.abs(roomBR.px - roomTL.px),
        Math.abs(roomBR.py - roomTL.py)
      );
      ctx.setLineDash([]);

      ctx.fillStyle = "#12141a";
      ctx.strokeStyle = "#3a4155";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.rect(lay.ox, lay.oy, lay.rw, lay.rh);
      ctx.fill();
      ctx.stroke();

      ctx.strokeStyle = COLORS.grid;
      ctx.lineWidth = 1;
      var step = 0.1, gx, gz, a, b;
      for (gx = Math.ceil(lay.x0 / step) * step; gx <= lay.x0 + lay.spanX + 1e-9; gx += step) {
        a = topToPx(gx, lay.z0, lay);
        b = topToPx(gx, lay.z0 + lay.spanZ, lay);
        ctx.beginPath(); ctx.moveTo(a.px, a.py); ctx.lineTo(b.px, b.py); ctx.stroke();
      }
      for (gz = Math.ceil(lay.z0 / step) * step; gz <= lay.z0 + lay.spanZ + 1e-9; gz += step) {
        a = topToPx(lay.x0, gz, lay);
        b = topToPx(lay.x0 + lay.spanX, gz, lay);
        ctx.beginPath(); ctx.moveTo(a.px, a.py); ctx.lineTo(b.px, b.py); ctx.stroke();
      }

      drawPlaneHalo(ctx, polarField && polarField.halo_xz, function (phi, rad) {
        return topToPx(
          geo.mic_centre.x - Math.sin(phi) * rad,
          geo.mic_centre.z + Math.cos(phi) * rad,
          lay
        );
      });

      var Cp = topToPx(geo.mic_centre.x, geo.mic_centre.z, lay);
      var Lp = topToPx(geo.mic_left.x, geo.mic_left.z, lay);
      var Rp = topToPx(geo.mic_right.x, geo.mic_right.z, lay);

      ctx.strokeStyle = "rgba(96,165,250,0.45)";
      ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(Lp.px, Lp.py); ctx.lineTo(Rp.px, Rp.py); ctx.stroke();
      if (Math.abs(geo.state.centre_dz || 0) > 1e-4) {
        ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(Cp.px, Cp.py); ctx.lineTo((Lp.px + Rp.px) * 0.5, Lp.py); ctx.stroke();
        ctx.setLineDash([]);
      }

      drawLookCone(ctx, Lp.px, Lp.py, geo.look_l, COLORS.L, lay.scale, false);
      drawLookCone(ctx, Cp.px, Cp.py, geo.look_c || { x: 0, z: 1 }, COLORS.C, lay.scale, true);
      drawLookCone(ctx, Rp.px, Rp.py, geo.look_r, COLORS.R, lay.scale, false);

      drawHandle(ctx, Lp.px, Lp.py, COLORS.L, "L",
        selected === "capL" || !!(drag && drag.kind === "capL"), hover === "capL", uiPx(16));
      drawHandle(ctx, Rp.px, Rp.py, COLORS.R, "R",
        selected === "capR" || !!(drag && drag.kind === "capR"), hover === "capR", uiPx(16));
      drawHandle(ctx, Cp.px, Cp.py, COLORS.C, "C",
        selected === "capC" || !!(drag && drag.kind === "capC"), hover === "capC", uiPx(18));

      drawFrontDot(ctx, geo, "L", COLORS.L, "yawL");
      drawFrontDot(ctx, geo, "C", COLORS.C, "yawC");
      drawFrontDot(ctx, geo, "R", COLORS.R, "yawR");

      ctx.fillStyle = COLORS.text;
      ctx.font = "600 11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(
        "space " + geo.state.space.toFixed(2) + " m \u00b7 C setback " +
        ((geo.state.centre_dz || 0) * 100).toFixed(0) + " cm" +
        (selected ? " \u00b7 " + selected : ""),
        12, 18
      );
      ctx.textAlign = "center";
      ctx.fillText("X \u2192", lay.ox + lay.rw / 2, lay.oy + lay.rh + 16);
      drawLiveReadout(ctx, cw);
    }

    function drawSide(geo) {
      fitCanvas(topCanvas);
      var ctx = tctx;
      var cw = topCanvas.width;
      var ch = topCanvas.height;
      sideLay = sideFrame(geo);
      var lay = sideLay;
      ctx.clearRect(0, 0, cw, ch);
      ctx.fillStyle = COLORS.bg;
      ctx.fillRect(0, 0, cw, ch);

      ctx.strokeStyle = COLORS.room;
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1;
      ctx.beginPath();
      var fl = sideToPx(lay.z0, 0, lay);
      var fr = sideToPx(lay.z0 + lay.spanZ, 0, lay);
      ctx.moveTo(fl.px, fl.py); ctx.lineTo(fr.px, fr.py);
      var cl = sideToPx(lay.z0, geo.state.H, lay);
      var cr = sideToPx(lay.z0 + lay.spanZ, geo.state.H, lay);
      ctx.moveTo(cl.px, cl.py); ctx.lineTo(cr.px, cr.py);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = "#12141a";
      ctx.strokeStyle = "#3a4155";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.rect(lay.ox, lay.oy, lay.rw, lay.rh);
      ctx.fill();
      ctx.stroke();

      drawPlaneHalo(ctx, sideSlice(geo), function (phi, rad) {
        return sideToPx(Math.cos(phi) * rad, geo.mic_centre.y + Math.sin(phi) * rad, lay);
      });

      function at(obj) {
        return sideToPx(alongOf(obj.x, obj.z, geo), obj.y, lay);
      }
      var Sp = at(geo.source);
      var Cp = at(geo.mic_centre);
      var Lp = at(geo.mic_left);
      var Rp = at(geo.mic_right);
      var floorMic = sideToPx(alongOf(geo.mic_centre.x, geo.mic_centre.z, geo), 0, lay);
      var floorSrc = sideToPx(alongOf(geo.source.x, geo.source.z, geo), 0, lay);

      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = "rgba(251,191,36,0.35)";
      ctx.beginPath(); ctx.moveTo(floorSrc.px, floorSrc.py); ctx.lineTo(Sp.px, Sp.py); ctx.stroke();
      ctx.strokeStyle = "rgba(96,165,250,0.45)";
      ctx.beginPath(); ctx.moveTo(floorMic.px, floorMic.py); ctx.lineTo(Cp.px, Cp.py); ctx.stroke();
      ctx.setLineDash([]);

      ctx.strokeStyle = "rgba(96,165,250,0.35)";
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(Lp.px, Lp.py); ctx.lineTo(Rp.px, Rp.py); ctx.stroke();

      drawHandle(ctx, Lp.px, Lp.py, COLORS.L, "L",
        selected === "capL" || !!(drag && drag.kind === "capL"), hover === "capL", uiPx(16));
      drawHandle(ctx, Rp.px, Rp.py, COLORS.R, "R",
        selected === "capR" || !!(drag && drag.kind === "capR"), hover === "capR", uiPx(16));
      drawHandle(ctx, Cp.px, Cp.py, COLORS.C, "C",
        selected === "capC" || !!(drag && drag.kind === "capC"), hover === "capC", uiPx(18));
      drawHandle(ctx, Sp.px, Sp.py, COLORS.src, "Source",
        selected === "src" || !!(drag && drag.kind === "src"), hover === "src", uiPx(16));

      ctx.fillStyle = COLORS.text;
      ctx.font = "11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText("Floor", lay.ox + 6, Math.min(ch - 8, fl.py + 12));
      ctx.textAlign = "right";
      ctx.fillStyle = COLORS.src;
      ctx.fillText("Src " + (geo.state.sy != null ? geo.state.sy : geo.state.my).toFixed(2) + " m", cw - 10, Sp.py + 4);
      ctx.fillStyle = COLORS.stand;
      ctx.fillText(
        "L " + geo.mic_left.y.toFixed(2) + "  C " + geo.mic_centre.y.toFixed(2) +
        "  R " + geo.mic_right.y.toFixed(2) + " m",
        cw - 10, Cp.py + 4
      );
      ctx.textAlign = "center";
      ctx.fillStyle = COLORS.text;
      ctx.fillText("drag left / right to turn the view  \u00b7  drag a mic up / down", lay.ox + lay.rw / 2, ch - 6);
      drawLiveReadout(ctx, cw);
    }

    function polarLayout(canvas) {
      var w = canvas.width, h = canvas.height;
      return { cx: w * 0.5, cy: h * 0.52, R: Math.min(w, h) * 0.38, w: w, h: h };
    }

    function polarFrontPx(canvas, yawDeg) {
      var lay = polarLayout(canvas);
      var yaw = ((Number(yawDeg) || 0) * Math.PI) / 180;
      /* Match lookFromYaw: screen ( S·sin yaw, −cos yaw ) so +Z is up, S = RoomMath.YAW_X_SIGN. */
      var S = (typeof RoomMath !== "undefined" && RoomMath.YAW_X_SIGN) ? RoomMath.YAW_X_SIGN : 1;
      return {
        px: lay.cx + S * lay.R * Math.sin(yaw),
        py: lay.cy - lay.R * Math.cos(yaw),
        cx: lay.cx, cy: lay.cy, R: lay.R
      };
    }

    function sampleRow(row, theta) {
      var n = row.length;
      var ang = Math.abs(theta);
      var x = ((ang / (Math.PI * 2)) % 1) * n;
      if (x < 0) x += n;
      var i0 = Math.floor(x) % n;
      var i1 = (i0 + 1) % n;
      var f = x - Math.floor(x);
      var a = Number(row[i0]);
      var b = Number(row[i1]);
      if (!isFinite(a)) a = 0;
      if (!isFinite(b)) b = 0;
      return a * (1 - f) + b * f;
    }

    function sideSlice(geo) {
      if (!polarField || !polarField.L || !polarField.centres_hz) {
        return polarField && polarField.halo_yz;
      }
      var freqs = polarField.centres_hz;
      var grids = [polarField.L, polarField.C, polarField.R];
      var poss = [geo.mic_left, geo.mic_centre, geo.mic_right];
      var looks = [geo.look_l, geo.look_c || { x: 0, z: 1 }, geo.look_r];
      var fams = [geo.state.family_l, geo.state.family_c, geo.state.family_r];
      var pols = [geo.state.polar_l, geo.state.polar_c, geo.state.polar_r];
      var rx = Math.sin(sideAz);
      var rz = Math.cos(sideAz);
      var nB = Math.min(freqs.length, grids[0].length);
      var nAz = (grids[0][0] || []).length || 72;
      var c = geo.mic_centre;
      var out = [];
      var bi, ai, mi;
      for (bi = 0; bi < nB; bi++) out.push(new Array(nAz));
      for (ai = 0; ai < nAz; ai++) {
        var phi = (ai / nAz) * Math.PI * 2;
        var ux = Math.cos(phi) * rx;
        var uy = Math.sin(phi);
        var uz = Math.cos(phi) * rz;
        for (bi = 0; bi < nB; bi++) {
          var re = 0, im = 0;
          var freq = Number(freqs[bi]) || 0;
          for (mi = 0; mi < 3; mi++) {
            var look = looks[mi];
            var cosT = look.x * ux + look.z * uz;
            if (cosT > 1) cosT = 1;
            if (cosT < -1) cosT = -1;
            var theta = Math.acos(cosT);
            var mag = sampleRow(grids[mi][bi] || grids[mi][0], theta);
            var signed = mag;
            if (RoomMath && RoomMath.polarGain) {
              var g = RoomMath.polarGain(theta, fams[mi], pols[mi]);
              signed = g < 0 ? -mag : (g === 0 ? 0 : mag);
            }
            var phase = (((poss[mi].x - c.x) * ux + (poss[mi].y - c.y) * uy + (poss[mi].z - c.z) * uz) / 340) * Math.PI * 2 * freq;
            re += signed * Math.cos(phase);
            im += signed * Math.sin(phase);
          }
          out[bi][ai] = Math.sqrt(re * re + im * im);
        }
      }
      return out;
    }

    function drawPlaneHalo(ctx, grid, project) {
      if (!grid || !grid.length || !grid[0] || !grid[0].length || !project) return;
      var nB = grid.length;
      var nAz = grid[0].length;
      var peak = 1e-6;
      var bi, ai, v;
      for (bi = 0; bi < nB; bi++) {
        for (ai = 0; ai < nAz; ai++) {
          v = Number(grid[bi][ai]);
          if (isFinite(v) && v > peak) peak = v;
        }
      }
      var reach = 0.62;
      for (bi = 0; bi < nB; bi++) {
        ctx.beginPath();
        for (ai = 0; ai <= nAz; ai++) {
          var k = ai % nAz;
          var phi = (k / nAz) * Math.PI * 2;
          var rad = Math.max(0, Number(grid[bi][k]) || 0) / peak * reach;
          var p = project(phi, rad);
          if (ai === 0) ctx.moveTo(p.px, p.py);
          else ctx.lineTo(p.px, p.py);
        }
        ctx.strokeStyle = ringColor(bi, nB);
        ctx.lineWidth = bi === nB - 1 ? 2 : 1.25;
        ctx.stroke();
      }
    }

    function ringRadius(grid, bi, ai) {
      if (!grid || !grid[bi]) return 0;
      var v = Number(grid[bi][ai]);
      return isFinite(v) ? Math.max(0, v) : 0;
    }

    function gridPeak(grid) {
      var peak = 1;
      if (!grid) return peak;
      var bi, ai;
      for (bi = 0; bi < grid.length; bi++) {
        var row = grid[bi] || [];
        for (ai = 0; ai < row.length; ai++) {
          var v = Number(row[ai]);
          if (isFinite(v) && v > peak) peak = v;
        }
      }
      return peak;
    }

    function paintRingLegend(labels) {
      var host = document.getElementById("micRingLegend");
      if (!host) return;
      var text = (labels || ["20", "63", "125", "250", "1k", "4k", "8k", "16k"]).join("|");
      if (host.getAttribute("data-key") === text) return;
      host.setAttribute("data-key", text);
      host.innerHTML = "";
      (labels || []).forEach(function (lab, i) {
        var span = document.createElement("span");
        var sw = document.createElement("i");
        sw.className = "mic-ring-swatch";
        sw.style.background = ringColor(i, (labels || []).length || 8);
        span.appendChild(sw);
        span.appendChild(document.createTextNode(lab));
        host.appendChild(span);
      });
    }

    function drawPolar2d(canvas, family, polar, yawDeg, color, label, grid, captionTail) {
      if (!canvas) return;
      fitCanvas(canvas);
      var ctx = canvas.getContext("2d");
      var lay = polarLayout(canvas);
      var cx = lay.cx, cy = lay.cy, R = lay.R;
      ctx.clearRect(0, 0, lay.w, lay.h);
      ctx.fillStyle = "#0c0e14";
      ctx.fillRect(0, 0, lay.w, lay.h);

      var peak = grid ? gridPeak(grid) : 1;
      var scale = R / peak;
      ctx.strokeStyle = "rgba(255,255,255,0.08)";
      ctx.lineWidth = 1;
      [0.25, 0.5, 0.75, 1].forEach(function (f) {
        ctx.beginPath(); ctx.arc(cx, cy, scale * peak * f, 0, Math.PI * 2); ctx.stroke();
      });
      ctx.beginPath();
      ctx.moveTo(cx - R, cy); ctx.lineTo(cx + R, cy);
      ctx.moveTo(cx, cy - R); ctx.lineTo(cx, cy + R);
      ctx.stroke();

      var yaw = ((Number(yawDeg) || 0) * Math.PI) / 180;
      if (grid && grid.length && grid[0] && grid[0].length) {
        var nAz = grid[0].length;
        var bi, ai, theta, screen, g, sx, sy;
        for (bi = 0; bi < grid.length; bi++) {
          ctx.beginPath();
          for (ai = 0; ai <= nAz; ai++) {
            var k = ai % nAz;
            theta = (k / nAz) * Math.PI * 2;
            screen = theta + yaw;
            g = ringRadius(grid, bi, k);
            sx = cx + scale * g * Math.sin(screen);
            sy = cy - scale * g * Math.cos(screen);
            if (ai === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
          }
          ctx.strokeStyle = ringColor(bi, grid.length);
          ctx.lineWidth = bi === grid.length - 1 ? 2 : 1.25;
          ctx.stroke();
        }
      } else {
        var n = 128, i, th;
        ctx.beginPath();
        for (i = 0; i <= n; i++) {
          th = (i / n) * Math.PI * 2;
          g = Math.abs(patternGain(th - yaw, family, polar));
          sx = cx + R * g * Math.sin(th);
          sy = cy - R * g * Math.cos(th);
          if (i === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
        }
        ctx.closePath();
        ctx.fillStyle = hexRgba(color, 0.28);
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.fill();
        ctx.stroke();
      }

      var front = polarFrontPx(canvas, yawDeg);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(front.px, front.py);
      ctx.strokeStyle = hexRgba(COLORS.yaw, 0.9);
      ctx.lineWidth = 1.6;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(front.px, front.py, uiPx(11), 0, Math.PI * 2);
      ctx.fillStyle = COLORS.yaw;
      ctx.fill();
      ctx.strokeStyle = "#0a0b0e";
      ctx.lineWidth = 1.4;
      ctx.stroke();

      canvas.dataset.drawnFamily = String(family || "");
      canvas.dataset.drawnPolar = String(Number(polar));
      canvas.dataset.drawnYaw = String(Math.round(Number(yawDeg) || 0));
      var lab = (RoomMath && RoomMath.polarLabel) ? RoomMath.polarLabel(family, polar) : String(family);
      ctx.fillStyle = COLORS.ink;
      ctx.font = "700 12px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(label, cx, 14);
      ctx.fillStyle = COLORS.text;
      ctx.font = "10px Segoe UI, system-ui, sans-serif";
      var tail = captionTail || "drag front or the rim";
      ctx.fillText(lab + " \u00b7 " + fmtYaw(yawDeg) + "  \u00b7 " + tail, cx, lay.h - 8);
    }

    function msDraw(st) {
      return !!(st && (st.mic_setup === "ms_classic" || st.ms_decode));
    }

    function drawPolars(geo) {
      var s = geo.state;
      var yL = s.yaw_l_deg != null ? s.yaw_l_deg : geo.toe_l_deg;
      var yC = s.yaw_c_deg != null ? s.yaw_c_deg : (geo.toe_c_deg || 0);
      var yR = s.yaw_r_deg != null ? s.yaw_r_deg : geo.toe_r_deg;
      var famL = familyOf(s, "l");
      var famC = familyOf(s, "c");
      var famR = familyOf(s, "r");
      var polL = polarOf(s, "l");
      var polC = polarOf(s, "c");
      var polR = polarOf(s, "r");
      var gL = polarField && polarField.L;
      var gC = polarField && polarField.C;
      var gR = polarField && polarField.R;
      var mode = s.colour_mode || "MEASURED_SHELF";
      var locked = mode === "MEASURED_SHELF" || mode === "BYPASS";
      var tail = locked ? "preset law \u00b7 drag front to aim" : "drag front or the rim";
      if (msDraw(s)) {
        /* Engine S is one figure-8 at the mid yaw + 90°. L and R both show that S.
           Do not paint the server grids: those follow stored family_l/r. */
        famL = "bi";
        famR = "bi";
        polL = 0.5;
        polR = 0.5;
        gL = null;
        gR = null;
        yL = yC + 90;
        yR = yC + 90;
      }
      drawPolar2d(polarL, famL, polL, yL, COLORS.L, "L", gL, tail);
      drawPolar2d(polarC, famC, polC, yC, COLORS.C, "C", gC, tail);
      drawPolar2d(polarR, famR, polR, yR, COLORS.R, "R", gR, tail);
    }

    function syncPlaneButtons() {
      var topBtn = document.getElementById("micPlaneTop");
      var sideBtn = document.getElementById("micPlaneSide");
      var title = document.getElementById("micPlaneTitle");
      var hint = document.getElementById("micPlaneHint");
      if (topBtn) topBtn.classList.toggle("active", planeMode !== "side");
      if (sideBtn) sideBtn.classList.toggle("active", planeMode === "side");
      if (title) title.textContent = planeMode === "side" ? "Side" : "Top";
      if (hint) {
        hint.textContent = planeMode === "side"
          ? "The stand, from the side. Drag left or right to turn the view. Drag a mic up or down."
          : "The stand, from above. Scroll to zoom. Drag a capsule in or out, and the amber front to aim.";
      }
    }

    function redraw() {
      var geo = geoOf();
      if (planeMode === "side") drawSide(geo);
      else drawTop(geo);
      drawPolars(geo);
      ensureView3d();
      if (view3d) view3d.redraw();
      return geo;
    }

    function hitYaw(px, py, geo, which, kind) {
      var k = yawKnobOf(geo, which, topLay || topFrame(geo));
      if (Math.hypot(px - k.px, py - k.py) <= uiPx(16)) return kind;
      return null;
    }

    function hitTop(px, py, geo) {
      var lay = topLay || topFrame(geo);
      topLay = lay;
      var Lp = topToPx(geo.mic_left.x, geo.mic_left.z, lay);
      var Rp = topToPx(geo.mic_right.x, geo.mic_right.z, lay);
      var Cp = topToPx(geo.mic_centre.x, geo.mic_centre.z, lay);

      var bodies = [
        { k: "capC", d: Math.hypot(px - Cp.px, py - Cp.py), lim: uiPx(26) },
        { k: "capL", d: Math.hypot(px - Lp.px, py - Lp.py), lim: uiPx(24) },
        { k: "capR", d: Math.hypot(px - Rp.px, py - Rp.py), lim: uiPx(24) }
      ];
      bodies.sort(function (a, b) { return a.d - b.d; });
      if (bodies[0].d <= bodies[0].lim) return bodies[0].k;
      var y;
      y = hitYaw(px, py, geo, "L", "yawL"); if (y) return y;
      y = hitYaw(px, py, geo, "C", "yawC"); if (y) return y;
      y = hitYaw(px, py, geo, "R", "yawR"); if (y) return y;
      return null;
    }

    function hitSide(px, py, geo) {
      var lay = sideLay || sideFrame(geo);
      function at(obj) {
        return sideToPx(alongOf(obj.x, obj.z, geo), obj.y, lay);
      }
      var spots = [
        { k: "capC", p: at(geo.mic_centre), lim: uiPx(26) },
        { k: "capL", p: at(geo.mic_left), lim: uiPx(24) },
        { k: "capR", p: at(geo.mic_right), lim: uiPx(24) },
        { k: "src", p: at(geo.source), lim: uiPx(24) }
      ];
      spots.sort(function (a, b) {
        return Math.hypot(px - a.p.px, py - a.p.py) - Math.hypot(px - b.p.px, py - b.p.py);
      });
      var best = spots[0];
      if (Math.hypot(px - best.p.px, py - best.p.py) <= best.lim) return best.k;
      return "orbit";
    }

    function applyYawFromPointer(kind, px, py, originPx) {
      /* Aim on screen is (S·sin yaw, −cos yaw), so +Z is up (S = RoomMath.YAW_X_SIGN).
         atan2(S·dx, −dy) keeps the handle under the pointer.
         Dragging right moves the handle right. */
      var S = (typeof RoomMath !== "undefined" && RoomMath.YAW_X_SIGN) ? RoomMath.YAW_X_SIGN : 1;
      var dx = px - originPx.px;
      var dy = py - originPx.py;
      var deg = Math.atan2(S * dx, -dy) * 180 / Math.PI;
      var st = Object.assign({}, getState());
      var link = !!st.link_lr_yaw;
      if (kind === "yawL" || kind === "polarL") {
        st.yaw_l_deg = deg;
        if (link) st.yaw_r_deg = -deg;
      } else if (kind === "yawR" || kind === "polarR") {
        st.yaw_r_deg = deg;
        if (link) st.yaw_l_deg = -deg;
      } else {
        st.yaw_c_deg = deg;
      }
      if (st.yaw_l_deg != null && st.yaw_r_deg != null) {
        st.toe_half_deg = 0.5 * (Math.abs(Number(st.yaw_r_deg)) + Math.abs(Number(st.yaw_l_deg)));
      }
      setState(RoomMath.clampRoom(st));
      liveReadout = "Front " + fmtYaw(deg);
      onChange();
    }

    function maxSpace(W, mcx) {
      if (RoomMath.maxSpace) return RoomMath.maxSpace(W, mcx);
      return Math.max(0, 2 * Math.min(mcx, W - mcx));
    }

    function applyTopDrag(kind, px, py) {
      var st = Object.assign({}, getState());
      var m = topToM(px, py, topLay);
      var geo = geoOf();
      if (kind === "capC") {
        st.align_horizontal = false;
        var dzMax = RoomMath.CENTRE_DZ_MAX != null ? RoomMath.CENTRE_DZ_MAX : 0.20;
        st.centre_dz = RoomMath.clamp(m.z - st.mcz, -dzMax, dzMax);
        setState(RoomMath.clampRoom(st));
        liveReadout = "C setback " + (st.centre_dz * 100).toFixed(0) + " cm";
        onChange();
      } else if (kind === "capL" || kind === "capR") {
        var halfWant = Math.abs(m.x - st.mcx);
        st.space = RoomMath.clamp(halfWant * 2, 0, maxSpace(st.W, st.mcx));
        setState(RoomMath.clampRoom(st));
        liveReadout = "Space " + st.space.toFixed(2) + " m";
        onChange();
      } else if (kind.indexOf("yaw") === 0) {
        var origin;
        if (kind === "yawL") origin = topToPx(geo.mic_left.x, geo.mic_left.z, topLay);
        else if (kind === "yawR") origin = topToPx(geo.mic_right.x, geo.mic_right.z, topLay);
        else origin = topToPx(geo.mic_centre.x, geo.mic_centre.z, topLay);
        applyYawFromPointer(kind, px, py, origin);
      }
    }

    function applySideDrag(kind, px, py) {
      if (kind === "orbit") return;
      var m = sideToM(px, py, sideLay);
      var st = Object.assign({}, getState());
      var y = RoomMath.clamp(m.y, 0, st.H);
      if (kind === "src") {
        st.sy = y;
        if (st.link_heights) st.my = y;
        liveReadout = "Source " + y.toFixed(2) + " m";
      } else if (kind === "capC") {
        st.my_c = y;
        st.my = y;
        liveReadout = "Centre " + y.toFixed(2) + " m";
      } else if (kind === "capL" || kind === "capR") {
        if (st.align_horizontal) {
          st.my_l = y;
          st.my_r = y;
          liveReadout = "L and R " + y.toFixed(2) + " m";
        } else if (kind === "capL") {
          st.my_l = y;
          liveReadout = "Left " + y.toFixed(2) + " m";
        } else {
          st.my_r = y;
          liveReadout = "Right " + y.toFixed(2) + " m";
        }
      }
      setState(RoomMath.clampRoom(st));
      onChange();
    }

    function endDrag() {
      if (!drag) return;
      drag = null;
      liveReadout = "";
      topCanvas.classList.remove("dragging");
      setCursor(topCanvas, hover);
      redraw();
    }

    function hitPlane(px, py, geo) {
      if (planeMode === "side") {
        sideLay = sideFrame(geo);
        return hitSide(px, py, geo);
      }
      topLay = topFrame(geo);
      return hitTop(px, py, geo);
    }

    topCanvas.addEventListener("pointerdown", function (evt) {
      var geo = geoOf();
      var p = canvasPos(topCanvas, evt);
      var kind = hitPlane(p.x, p.y, geo);
      if (!kind) {
        selected = null;
        liveReadout = "";
        redraw();
        return;
      }
      selected = kind;
      drag = {
        kind: kind,
        canvas: planeMode === "side" ? "side" : "top",
        x0: p.x,
        y0: p.y,
        moved: false,
        armed: true,
        lastX: p.x
      };
      topCanvas.classList.add("dragging");
      setCursor(topCanvas, kind);
      try { topCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
      if (kind.indexOf("yaw") === 0) {
        drag.moved = true;
        var origin;
        if (kind === "yawL") origin = topToPx(geo.mic_left.x, geo.mic_left.z, topLay);
        else if (kind === "yawR") origin = topToPx(geo.mic_right.x, geo.mic_right.z, topLay);
        else origin = topToPx(geo.mic_centre.x, geo.mic_centre.z, topLay);
        applyYawFromPointer(kind, p.x, p.y, origin);
      }
      redraw();
      evt.preventDefault();
    });

    topCanvas.addEventListener("pointermove", function (evt) {
      var geo = geoOf();
      var p = canvasPos(topCanvas, evt);
      if (drag && (drag.canvas === "top" || drag.canvas === "side")) {
        var dist = Math.hypot(p.x - drag.x0, p.y - drag.y0);
        if (!drag.moved && dist < DRAG_THRESH && drag.kind.indexOf("yaw") !== 0) {
          return;
        }
        drag.moved = true;
        if (drag.canvas === "side") {
          var turn = p.x - (drag.lastX != null ? drag.lastX : p.x);
          drag.lastX = p.x;
          sideAz -= turn * 0.007;
          sideLay = sideFrame(geo);
          applySideDrag(drag.kind, p.x, p.y);
        } else {
          topLay = topFrame(geo);
          applyTopDrag(drag.kind, p.x, p.y);
        }
        redraw();
        return;
      }
      var h = hitPlane(p.x, p.y, geo);
      if (h !== hover) {
        hover = h;
        setCursor(topCanvas, h);
        redraw();
      } else {
        setCursor(topCanvas, h);
      }
    });

    topCanvas.addEventListener("wheel", function (evt) {
      evt.preventDefault();
      var factor = evt.deltaY > 0 ? (1 / 1.12) : 1.12;
      viewZoom = Math.max(0.55, Math.min(8, (viewZoom || 1) * factor));
      redraw();
    }, { passive: false });

    topCanvas.addEventListener("pointerup", endDrag);
    topCanvas.addEventListener("pointercancel", endDrag);
    window.addEventListener("pointerup", endDrag);
    topCanvas.addEventListener("pointerleave", function () {
      if (drag) return;
      if (hover) { hover = null; setCursor(topCanvas, null); redraw(); }
    });
    setCursor(topCanvas, null);

    document.querySelectorAll("#micPlaneRow [data-plane]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        planeMode = btn.getAttribute("data-plane") === "side" ? "side" : "top";
        syncPlaneButtons();
        redraw();
        ensureView3d();
        if (view3d && view3d.setHaloPlane) view3d.setHaloPlane(planeMode, true);
        if (view3d && view3d.setHalo) view3d.setHalo(polarField, planeMode);
      });
    });
    syncPlaneButtons();

    function wrapPi(a) {
      while (a > Math.PI) a -= Math.PI * 2;
      while (a < -Math.PI) a += Math.PI * 2;
      return a;
    }

    function capOfPolarKind(kind) {
      if (kind === "polarL") return "l";
      if (kind === "polarR") return "r";
      return "c";
    }

    function yawDegOf(cap) {
      var geo = geoOf();
      var s = geo.state;
      if (cap === "l") return s.yaw_l_deg != null ? s.yaw_l_deg : geo.toe_l_deg;
      if (cap === "r") return s.yaw_r_deg != null ? s.yaw_r_deg : geo.toe_r_deg;
      return s.yaw_c_deg != null ? s.yaw_c_deg : (geo.toe_c_deg || 0);
    }

    function polarWritable(cap) {
      var st = getState();
      var mode = st.colour_mode || "MEASURED_SHELF";
      if (mode === "MEASURED_SHELF" || mode === "BYPASS") return false;
      if (st.mic_setup === "binaural") return false;
      if (familyOf(st, cap) === "bi") return false;
      return true;
    }

    /* Screen angle matches the +sin lobe: front is up, +yaw is to the right. */
    function screenTheta(canvas, px, py, cap) {
      var lay = polarLayout(canvas);
      var th = Math.atan2(px - lay.cx, -(py - lay.cy));
      var yaw = ((Number(yawDegOf(cap)) || 0) * Math.PI) / 180;
      return { lay: lay, theta: wrapPi(th - yaw), rad: Math.hypot(px - lay.cx, py - lay.cy) };
    }

    function polarHitMode(canvas, px, py, cap) {
      var front = polarFrontPx(canvas, yawDegOf(cap));
      if (Math.hypot(px - front.px, py - front.py) <= uiPx(14)) return "yaw";
      if (!polarWritable(cap)) return "yaw";
      var hit = screenTheta(canvas, px, py, cap);
      if (Math.abs(hit.theta) < 0.45) return "yaw";
      var st = getState();
      var outline = Math.abs(patternGain(hit.theta, familyOf(st, cap), polarOf(st, cap))) * hit.lay.R;
      if (Math.abs(hit.rad - outline) <= uiPx(18)) return "rim";
      return "yaw";
    }

    function polarFromRim(canvas, px, py, cap) {
      var hit = screenTheta(canvas, px, py, cap);
      if (Math.abs(hit.theta) < 0.45) return null;
      if (!(hit.lay.R > 0)) return null;
      var target = hit.rad / hit.lay.R;
      if (target > 1.35) return null;
      target = Math.max(0, Math.min(1, target));
      var fam = familyOf(getState(), cap);
      var best = 0.5;
      var bestErr = 1e9;
      var d, err;
      for (d = 0; d <= 1.0001; d += 0.01) {
        err = Math.abs(Math.abs(patternGain(hit.theta, fam, Math.min(1, d))) - target);
        if (err < bestErr) {
          bestErr = err;
          best = Math.min(1, d);
        }
      }
      return Math.round(best * 100) / 100;
    }

    function applyPolarValue(cap, value) {
      if (value == null || !isFinite(value)) return;
      if (!polarWritable(cap)) return;
      if (onPolar) {
        onPolar(cap, value);
        return;
      }
      var st = Object.assign({}, getState());
      st["polar_" + cap] = value;
      st.preset_owns_pattern = false;
      setState(st);
      onChange();
    }

    function bindPolar(canvas, kind) {
      if (!canvas) return;
      canvas.style.cursor = "crosshair";
      function act(p) {
        var cap = capOfPolarKind(kind);
        if (drag && drag.polarMode === "rim") {
          applyPolarValue(cap, polarFromRim(canvas, p.x, p.y, cap));
          return;
        }
        var lay = polarLayout(canvas);
        applyYawFromPointer(kind, p.x, p.y, { px: lay.cx, py: lay.cy });
      }
      canvas.addEventListener("pointerdown", function (evt) {
        var p = canvasPos(canvas, evt);
        var cap = capOfPolarKind(kind);
        var mode = polarHitMode(canvas, p.x, p.y, cap);
        drag = { kind: kind, canvas: "polar", polarMode: mode, x0: p.x, y0: p.y, moved: true };
        selected = kind;
        act(p);
        redraw();
        try { canvas.setPointerCapture(evt.pointerId); } catch (e) {}
        evt.preventDefault();
      });
      canvas.addEventListener("pointermove", function (evt) {
        if (!drag || drag.kind !== kind) return;
        act(canvasPos(canvas, evt));
        redraw();
      });
      canvas.addEventListener("pointerup", endDrag);
      canvas.addEventListener("pointercancel", endDrag);
    }
    bindPolar(polarL, "polarL");
    bindPolar(polarC, "polarC");
    bindPolar(polarR, "polarR");

    function setPolar(data) {
      polarField = data || null;
      if (polarField) paintRingLegend(polarField.ring_labels || null);
      var note = document.getElementById("micHaloHint");
      if (note && polarField && polarField.halo_note) note.textContent = polarField.halo_note;
      redraw();
      ensureView3d();
      if (view3d && view3d.setHalo) view3d.setHalo(polarField, planeMode);
    }

    return {
      redraw: redraw,
      setPolar: setPolar,
      get view3d() { return view3d; },
      dispose: function () {
        if (view3d && view3d.dispose) view3d.dispose();
      }
    };
  }

  global.MicDesk = { create: create, patternGain: patternGain };
})(window);
