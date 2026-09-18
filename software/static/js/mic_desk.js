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
  var HIT_BODY = 26;
  var HIT_STAND = 30;
  var HIT_SIDE = 28;
  var HIT_YAW = 16;
  var YAW_RING_M = 0.22;
  var DRAG_THRESH = 5;

  function patternGain(theta, pattern) {
    var p = String(pattern || "cardioid").toLowerCase();
    if (p === "omni" || p === "o") return 1;
    if (p === "fig8" || p === "figure8" || p === "bi") return Math.abs(Math.cos(theta));
    return 0.5 * (1 + Math.cos(theta));
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
    var RoomMath = opts.RoomMath || global.RoomMath;

    var tctx = topCanvas.getContext("2d");
    var sctx = sideCanvas.getContext("2d");
    var drag = null;
    var hover = null;
    var selected = null;
    var topLay = null;
    var sideLay = null;
    var view3d = null;
    var liveReadout = "";

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
      var spanX = Math.max(0.8, x1 - x0);
      var spanZ = Math.max(0.8, z1 - z0);
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

    function sideFrame(geo) {
      var s = geo.state;
      var zPad = Math.max(0.7, s.space * 0.5 + 0.45);
      var z0 = s.mcz - zPad;
      var z1 = s.mcz + zPad;
      if (geo.source) {
        var dz = Math.abs(geo.source.z - s.mcz);
        if (dz < zPad * 2.5) {
          z0 = Math.min(z0, geo.source.z - 0.3);
          z1 = Math.max(z1, geo.source.z + 0.3);
        }
      }
      var yLo0 = Math.min(s.my, s.sy != null ? s.sy : s.my);
      var yHi0 = Math.max(s.my, s.sy != null ? s.sy : s.my);
      var yPad = Math.max(0.55, Math.min(s.H * 0.45, yHi0 * 0.65 + 0.4));
      var yLo = Math.max(0, yLo0 - yPad);
      var yHi = Math.min(s.H, yHi0 + yPad);
      if (yHi - yLo < 1.0) {
        var mid = 0.5 * (yLo + yHi);
        yLo = Math.max(0, mid - 0.5);
        yHi = Math.min(s.H, mid + 0.5);
      }
      var spanZ = Math.max(0.8, z1 - z0);
      var spanY = Math.max(0.6, yHi - yLo);
      var cw = sideCanvas.width;
      var ch = sideCanvas.height;
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
      return Math.max(18, Math.min(42, YAW_RING_M * lay.scale));
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

    function drawYawArc(ctx, geo, which, color, kind) {
      var lay = topLay;
      var k = yawKnobOf(geo, which, lay);
      var active = selected === kind || (drag && drag.kind === kind);
      var hovered = hover === kind;
      var ang = Math.atan2(k.look.x, k.look.z);
      /* Screen: +x right, +y down; look z forward is up on canvas → atan2(look.x, look.z) maps to canvas angle from -Y. */
      var start = -ang - 0.95;
      var end = -ang + 0.95;

      ctx.beginPath();
      ctx.arc(k.ox, k.oy, k.r, start, end);
      ctx.strokeStyle = hexRgba(COLORS.yaw, active || hovered ? 0.95 : 0.55);
      ctx.lineWidth = active || hovered ? 3.5 : 2.5;
      ctx.lineCap = "round";
      ctx.stroke();

      /* Distinct diamond/tip handle — not a body disc */
      var s = active || hovered ? 7 : 5.5;
      ctx.save();
      ctx.translate(k.px, k.py);
      ctx.rotate(-ang);
      ctx.beginPath();
      ctx.moveTo(0, -s);
      ctx.lineTo(s * 0.75, 0);
      ctx.lineTo(0, s);
      ctx.lineTo(-s * 0.75, 0);
      ctx.closePath();
      ctx.fillStyle = COLORS.yaw;
      ctx.fill();
      ctx.strokeStyle = "#0a0b0e";
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.restore();

      if (active || hovered) {
        ctx.beginPath();
        ctx.arc(k.px, k.py, s + 5, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(245,158,11,0.45)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
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

      var Sp = topToPx(geo.source.x, geo.source.z, lay);
      var Cp = topToPx(geo.mic_centre.x, geo.mic_centre.z, lay);
      var Lp = topToPx(geo.mic_left.x, geo.mic_left.z, lay);
      var Rp = topToPx(geo.mic_right.x, geo.mic_right.z, lay);

      if (Sp.px > lay.ox - 20 && Sp.px < lay.ox + lay.rw + 20 &&
          Sp.py > lay.oy - 20 && Sp.py < lay.oy + lay.rh + 20) {
        ctx.globalAlpha = 0.55;
        drawHandle(ctx, Sp.px, Sp.py, COLORS.src, "Src",
          selected === "source" || !!(drag && drag.kind === "source"),
          hover === "source", 9);
        ctx.globalAlpha = 1;
      }

      ctx.strokeStyle = "rgba(96,165,250,0.45)";
      ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(Lp.px, Lp.py); ctx.lineTo(Rp.px, Rp.py); ctx.stroke();

      drawLookCone(ctx, Lp.px, Lp.py, geo.look_l, COLORS.L, lay.scale, false);
      drawLookCone(ctx, Cp.px, Cp.py, geo.look_c || { x: 0, z: 1 }, COLORS.C, lay.scale, true);
      drawLookCone(ctx, Rp.px, Rp.py, geo.look_r, COLORS.R, lay.scale, false);

      /* Bodies first (placement), then amber yaw arcs (rotation only). */
      drawHandle(ctx, Lp.px, Lp.py, COLORS.L, "L",
        selected === "capL" || !!(drag && drag.kind === "capL"), hover === "capL", 11);
      drawHandle(ctx, Rp.px, Rp.py, COLORS.R, "R",
        selected === "capR" || !!(drag && drag.kind === "capR"), hover === "capR", 11);
      drawHandle(ctx, Cp.px, Cp.py, COLORS.stand, "Stand",
        selected === "stand" || !!(drag && drag.kind === "stand"), hover === "stand", 14);

      drawYawArc(ctx, geo, "L", COLORS.L, "yawL");
      drawYawArc(ctx, geo, "C", COLORS.C, "yawC");
      drawYawArc(ctx, geo, "R", COLORS.R, "yawR");

      ctx.fillStyle = COLORS.text;
      ctx.font = "600 11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(
        "Stand " + geo.state.mcx.toFixed(2) + "," + geo.state.mcz.toFixed(2) +
        " \u00b7 space " + geo.state.space.toFixed(2) + " m" +
        (selected ? " \u00b7 sel " + selected : ""),
        12, 18
      );
      ctx.textAlign = "center";
      ctx.fillText("X \u2192", lay.ox + lay.rw / 2, lay.oy + lay.rh + 16);
      drawLiveReadout(ctx, cw);
    }

    function drawSide(geo) {
      var ctx = sctx;
      var cw = sideCanvas.width;
      var ch = sideCanvas.height;
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

      var Sp = sideToPx(geo.source.z, geo.source.y, lay);
      var Cp = sideToPx(geo.mic_centre.z, geo.mic_centre.y, lay);
      var Lp = sideToPx(geo.mic_left.z, geo.mic_left.y, lay);
      var Rp = sideToPx(geo.mic_right.z, geo.mic_right.y, lay);
      var floorMic = sideToPx(geo.mic_centre.z, 0, lay);
      var floorSrc = sideToPx(geo.source.z, 0, lay);

      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = "rgba(251,191,36,0.35)";
      ctx.beginPath(); ctx.moveTo(floorSrc.px, floorSrc.py); ctx.lineTo(Sp.px, Sp.py); ctx.stroke();
      ctx.strokeStyle = "rgba(96,165,250,0.45)";
      ctx.beginPath(); ctx.moveTo(floorMic.px, floorMic.py); ctx.lineTo(Cp.px, Cp.py); ctx.stroke();
      ctx.setLineDash([]);

      ctx.strokeStyle = "rgba(96,165,250,0.35)";
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(Lp.px, Lp.py); ctx.lineTo(Rp.px, Rp.py); ctx.stroke();

      drawHandle(ctx, Lp.px, Lp.py, COLORS.L, "L", false, false, 6);
      drawHandle(ctx, Rp.px, Rp.py, COLORS.R, "R", false, false, 6);
      drawHandle(ctx, Sp.px, Sp.py, COLORS.src, "Src H",
        selected === "srcH" || !!(drag && drag.kind === "srcH"), hover === "srcH", 12);
      drawHandle(ctx, Cp.px, Cp.py, COLORS.stand, "Mic H",
        selected === "micH" || !!(drag && drag.kind === "micH"), hover === "micH", 13);

      ctx.fillStyle = COLORS.text;
      ctx.font = "11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText("Floor", lay.ox + 6, Math.min(ch - 8, fl.py + 12));
      ctx.textAlign = "right";
      ctx.fillStyle = COLORS.src;
      ctx.fillText("Src " + (geo.state.sy != null ? geo.state.sy : geo.state.my).toFixed(2) + " m", cw - 10, Sp.py + 4);
      ctx.fillStyle = COLORS.stand;
      ctx.fillText("Mic " + geo.state.my.toFixed(2) + " m", cw - 10, Cp.py + 4);
      ctx.textAlign = "center";
      ctx.fillStyle = COLORS.text;
      ctx.fillText("Z \u2192  (height only)", lay.ox + lay.rw / 2, ch - 6);
      drawLiveReadout(ctx, cw);
    }

    function drawPolar2d(canvas, pattern, yawDeg, color, label) {
      if (!canvas) return;
      var ctx = canvas.getContext("2d");
      var w = canvas.width, h = canvas.height;
      var cx = w * 0.5, cy = h * 0.52;
      var R = Math.min(w, h) * 0.38;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#0c0e14";
      ctx.fillRect(0, 0, w, h);

      ctx.strokeStyle = "rgba(255,255,255,0.08)";
      ctx.lineWidth = 1;
      [0.25, 0.5, 0.75, 1].forEach(function (f) {
        ctx.beginPath(); ctx.arc(cx, cy, R * f, 0, Math.PI * 2); ctx.stroke();
      });
      ctx.beginPath();
      ctx.moveTo(cx - R, cy); ctx.lineTo(cx + R, cy);
      ctx.moveTo(cx, cy - R); ctx.lineTo(cx, cy + R);
      ctx.stroke();

      var yaw = ((Number(yawDeg) || 0) * Math.PI) / 180;
      var n = 128, i, th, g, sx, sy;
      ctx.beginPath();
      for (i = 0; i <= n; i++) {
        th = (i / n) * Math.PI * 2;
        g = patternGain(th - yaw, pattern);
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

      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + R * 1.05 * Math.sin(yaw), cy - R * 1.05 * Math.cos(yaw));
      ctx.stroke();

      ctx.fillStyle = COLORS.ink;
      ctx.font = "700 12px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(label, cx, 14);
      ctx.fillStyle = COLORS.text;
      ctx.font = "10px Segoe UI, system-ui, sans-serif";
      ctx.fillText(String(pattern || "cardioid") + " \u00b7 " + fmtYaw(yawDeg), cx, h - 8);
    }

    function drawPolars(geo) {
      var s = geo.state;
      var yL = s.yaw_l_deg != null ? s.yaw_l_deg : geo.toe_l_deg;
      var yC = s.yaw_c_deg != null ? s.yaw_c_deg : (geo.toe_c_deg || 0);
      var yR = s.yaw_r_deg != null ? s.yaw_r_deg : geo.toe_r_deg;
      drawPolar2d(polarL, s.pattern_l || "cardioid", yL, COLORS.L, "L");
      drawPolar2d(polarC, s.pattern_c || "cardioid", yC, COLORS.C, "C");
      drawPolar2d(polarR, s.pattern_r || "cardioid", yR, COLORS.R, "R");
    }

    function redraw() {
      var geo = geoOf();
      drawTop(geo);
      drawSide(geo);
      drawPolars(geo);
      ensureView3d();
      if (view3d) view3d.redraw();
      return geo;
    }

    function hitYaw(px, py, geo, which, kind) {
      var k = yawKnobOf(geo, which, topLay || topFrame(geo));
      /* Prefer knob tip */
      if (Math.hypot(px - k.px, py - k.py) <= HIT_YAW) return kind;
      /* Or near the arc ring (away from body centre) */
      var d = Math.hypot(px - k.ox, py - k.oy);
      if (Math.abs(d - k.r) <= HIT_YAW * 0.85 && d > HIT_BODY * 0.55) {
        var angPtr = Math.atan2(px - k.ox, -(py - k.oy));
        var angLook = Math.atan2(k.look.x, k.look.z);
        var diff = Math.abs(Math.atan2(Math.sin(angPtr - angLook), Math.cos(angPtr - angLook)));
        if (diff < 1.05) return kind;
      }
      return null;
    }

    function hitTop(px, py, geo) {
      var lay = topLay || topFrame(geo);
      topLay = lay;
      var Lp = topToPx(geo.mic_left.x, geo.mic_left.z, lay);
      var Rp = topToPx(geo.mic_right.x, geo.mic_right.z, lay);
      var Cp = topToPx(geo.mic_centre.x, geo.mic_centre.z, lay);
      var Sp = topToPx(geo.source.x, geo.source.z, lay);

      /* Bodies first — avoids accidental yaw when grabbing stand/capsules */
      var bodies = [
        { k: "stand", d: Math.hypot(px - Cp.px, py - Cp.py), lim: HIT_STAND },
        { k: "capL", d: Math.hypot(px - Lp.px, py - Lp.py), lim: HIT_BODY },
        { k: "capR", d: Math.hypot(px - Rp.px, py - Rp.py), lim: HIT_BODY },
        { k: "source", d: Math.hypot(px - Sp.px, py - Sp.py), lim: HIT_BODY }
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
      var Sp = sideToPx(geo.source.z, geo.source.y, lay);
      var Cp = sideToPx(geo.mic_centre.z, geo.mic_centre.y, lay);
      var ds = Math.hypot(px - Sp.px, py - Sp.py);
      var dc = Math.hypot(px - Cp.px, py - Cp.py);
      if (ds <= HIT_SIDE && ds <= dc) return "srcH";
      if (dc <= HIT_SIDE) return "micH";
      return null;
    }

    function applyYawFromPointer(kind, px, py) {
      var lay = topLay;
      var geo = geoOf();
      var origin;
      if (kind === "yawL") origin = topToPx(geo.mic_left.x, geo.mic_left.z, lay);
      else if (kind === "yawR") origin = topToPx(geo.mic_right.x, geo.mic_right.z, lay);
      else origin = topToPx(geo.mic_centre.x, geo.mic_centre.z, lay);
      var ang = Math.atan2(px - origin.px, -(py - origin.py));
      var deg = (ang * 180) / Math.PI;
      var st = Object.assign({}, getState());
      if (kind === "yawL") st.yaw_l_deg = deg;
      else if (kind === "yawR") st.yaw_r_deg = deg;
      else st.yaw_c_deg = deg;
      if (st.yaw_l_deg != null && st.yaw_r_deg != null) {
        st.toe_half_deg = 0.5 * (Math.abs(Number(st.yaw_r_deg)) + Math.abs(Number(st.yaw_l_deg)));
      }
      setState(RoomMath.clampRoom(st));
      liveReadout = "Yaw " + fmtYaw(deg);
      onChange();
    }

    function maxSpace(W, mcx) {
      if (RoomMath.maxSpace) return RoomMath.maxSpace(W, mcx);
      return Math.max(0, 2 * Math.min(mcx, W - mcx));
    }

    function applyTopDrag(kind, px, py) {
      var st = Object.assign({}, getState());
      var m = topToM(px, py, topLay);
      if (kind === "stand") {
        if (!st.reaktor_parity) st.mcx = RoomMath.clamp(m.x, 0, st.W);
        st.mcz = RoomMath.clamp(m.z, 0, st.L);
        setState(RoomMath.clampRoom(st));
        liveReadout = "Stand " + st.mcx.toFixed(2) + ", " + st.mcz.toFixed(2) + " m";
        onChange();
      } else if (kind === "source") {
        st.sx = RoomMath.clamp(m.x, 0, st.W);
        st.sz = RoomMath.clamp(m.z, 0, st.L);
        setState(RoomMath.clampRoom(st));
        liveReadout = "Src " + st.sx.toFixed(2) + ", " + st.sz.toFixed(2) + " m";
        onChange();
      } else if (kind === "capL" || kind === "capR") {
        /* L/R drag along array axis (X) adjusts space symmetrically; no stand Z. */
        var halfWant = Math.abs(m.x - st.mcx);
        st.space = RoomMath.clamp(halfWant * 2, 0, maxSpace(st.W, st.mcx));
        setState(RoomMath.clampRoom(st));
        liveReadout = "Space " + st.space.toFixed(2) + " m";
        onChange();
      } else if (kind.indexOf("yaw") === 0) {
        applyYawFromPointer(kind, px, py);
      }
    }

    function applySideDrag(kind, px, py) {
      var m = sideToM(px, py, sideLay);
      var st = Object.assign({}, getState());
      var y = RoomMath.clamp(m.y, 0, st.H);
      /* Height only — never write xz from Side. */
      if (kind === "srcH") {
        st.sy = y;
        if (st.link_heights) st.my = y;
        liveReadout = "Src H " + y.toFixed(2) + " m";
      } else {
        st.my = y;
        if (st.link_heights) st.sy = y;
        liveReadout = "Mic H " + y.toFixed(2) + " m";
      }
      setState(RoomMath.clampRoom(st));
      onChange();
    }

    function endDrag() {
      if (!drag) return;
      drag = null;
      liveReadout = "";
      topCanvas.classList.remove("dragging");
      sideCanvas.classList.remove("dragging");
      setCursor(topCanvas, hover);
      setCursor(sideCanvas, hover);
      redraw();
    }

    topCanvas.addEventListener("pointerdown", function (evt) {
      var geo = geoOf();
      topLay = topFrame(geo);
      var p = canvasPos(topCanvas, evt);
      var kind = hitTop(p.x, p.y, geo);
      if (!kind) {
        /* Empty click: deselect only — no accidental stand jump. */
        selected = null;
        liveReadout = "";
        redraw();
        return;
      }
      selected = kind;
      drag = {
        kind: kind,
        canvas: "top",
        x0: p.x,
        y0: p.y,
        moved: false,
        armed: true
      };
      topCanvas.classList.add("dragging");
      setCursor(topCanvas, kind);
      try { topCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
      /* Yaw: apply immediately so tip feels responsive */
      if (kind.indexOf("yaw") === 0) {
        drag.moved = true;
        applyYawFromPointer(kind, p.x, p.y);
      }
      redraw();
      evt.preventDefault();
    });

    topCanvas.addEventListener("pointermove", function (evt) {
      var geo = geoOf();
      topLay = topFrame(geo);
      var p = canvasPos(topCanvas, evt);
      if (drag && drag.canvas === "top") {
        var dist = Math.hypot(p.x - drag.x0, p.y - drag.y0);
        if (!drag.moved && dist < DRAG_THRESH && drag.kind.indexOf("yaw") !== 0) {
          return;
        }
        drag.moved = true;
        applyTopDrag(drag.kind, p.x, p.y);
        redraw();
        return;
      }
      var h = hitTop(p.x, p.y, geo);
      if (h !== hover) {
        hover = h;
        setCursor(topCanvas, h);
        redraw();
      } else {
        setCursor(topCanvas, h);
      }
    });

    sideCanvas.addEventListener("pointerdown", function (evt) {
      var geo = geoOf();
      sideLay = sideFrame(geo);
      var p = canvasPos(sideCanvas, evt);
      var kind = hitSide(p.x, p.y, geo);
      if (!kind) {
        selected = null;
        liveReadout = "";
        redraw();
        return;
      }
      selected = kind;
      drag = {
        kind: kind,
        canvas: "side",
        x0: p.x,
        y0: p.y,
        moved: false
      };
      sideCanvas.classList.add("dragging");
      setCursor(sideCanvas, kind);
      try { sideCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
      redraw();
      evt.preventDefault();
    });

    sideCanvas.addEventListener("pointermove", function (evt) {
      var geo = geoOf();
      sideLay = sideFrame(geo);
      var p = canvasPos(sideCanvas, evt);
      if (drag && drag.canvas === "side") {
        var dist = Math.hypot(p.x - drag.x0, p.y - drag.y0);
        if (!drag.moved && dist < DRAG_THRESH) return;
        drag.moved = true;
        applySideDrag(drag.kind, p.x, p.y);
        redraw();
        return;
      }
      var h = hitSide(p.x, p.y, geo);
      if (h !== hover) {
        hover = h;
        setCursor(sideCanvas, h);
        redraw();
      } else {
        setCursor(sideCanvas, h);
      }
    });

    topCanvas.addEventListener("pointerup", endDrag);
    sideCanvas.addEventListener("pointerup", endDrag);
    topCanvas.addEventListener("pointercancel", endDrag);
    sideCanvas.addEventListener("pointercancel", endDrag);
    window.addEventListener("pointerup", endDrag);

    topCanvas.addEventListener("pointerleave", function () {
      if (drag) return;
      if (hover) { hover = null; setCursor(topCanvas, null); redraw(); }
    });
    sideCanvas.addEventListener("pointerleave", function () {
      if (drag) return;
      if (hover) { hover = null; setCursor(sideCanvas, null); redraw(); }
    });

    setCursor(topCanvas, null);
    setCursor(sideCanvas, null);

    return {
      redraw: redraw,
      get view3d() { return view3d; },
      dispose: function () {
        if (view3d && view3d.dispose) view3d.dispose();
      }
    };
  }

  global.MicDesk = { create: create, patternGain: patternGain };
})(window);
