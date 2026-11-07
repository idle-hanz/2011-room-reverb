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

  var RING_HZ = [20, 63, 125, 250, 1000, 4000, 8000, 16000];

  var POLAR_DB_RINGS = [0, -6, -12, -18, -24];
  var POLAR_DB_FLOOR = -30;

  function polarDbRadius(db, outer) {
    if (!(db > POLAR_DB_FLOOR)) db = POLAR_DB_FLOOR;
    if (db > 0) db = 0;
    return outer * (db - POLAR_DB_FLOOR) / (0 - POLAR_DB_FLOOR);
  }

  function polarAmpRadius(db, outer) {
    if (db > 0) db = 0;
    return outer * window.RRDb.dbToLin(db);
  }

  /* Concentric dB rings, 0/90/180 marks, and a front arrow.
     useDb maps radius in dB down to -30. Otherwise 0 dB is the outer ring. */
  function drawPolarChartFrame(ctx, cx, cy, outer, yawRad, opts) {
    opts = opts || {};
    var useDb = !!opts.useDb;
    function rr(db) {
      return useDb ? polarDbRadius(db, outer) : polarAmpRadius(db, outer);
    }
    var fontPx = opts.fontPx || Math.max(9, Math.min(13, outer * 0.11));
    ctx.save();
    ctx.lineWidth = opts.lineWidth || 1;
    ctx.strokeStyle = "rgba(255,255,255,0.2)";
    ctx.fillStyle = opts.labelColor || "#8b92a5";
    ctx.font = Math.round(fontPx) + "px Segoe UI, system-ui, sans-serif";
    POLAR_DB_RINGS.forEach(function (db) {
      var rad = rr(db);
      if (!(rad > 0.5)) return;
      ctx.beginPath();
      ctx.arc(cx, cy, rad, 0, Math.PI * 2);
      ctx.stroke();
      ctx.textAlign = "left";
      ctx.textBaseline = "bottom";
      ctx.fillText((db === 0 ? "0" : String(db)) + " dB", cx + fontPx * 0.3, cy - rad);
    });
    var edge = rr(0);
    [[0, "0\u00b0"], [Math.PI / 2, "90\u00b0"], [Math.PI, "180\u00b0"]].forEach(function (row) {
      var th = row[0] + yawRad;
      var s = Math.sin(th);
      var c = Math.cos(th);
      ctx.beginPath();
      ctx.moveTo(cx + edge * s, cy - edge * c);
      ctx.lineTo(cx + (edge + fontPx * 0.55) * s, cy - (edge + fontPx * 0.55) * c);
      ctx.stroke();
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(row[1], cx + (edge + fontPx * 1.45) * s, cy - (edge + fontPx * 1.45) * c);
    });
    if (opts.arrow !== false) {
      var dx = Math.sin(yawRad);
      var dy = -Math.cos(yawRad);
      var tip = edge * 0.92;
      var tx = cx + tip * dx;
      var ty = cy + tip * dy;
      ctx.strokeStyle = opts.arrowColor || "#f59e0b";
      ctx.fillStyle = opts.arrowColor || "#f59e0b";
      ctx.lineWidth = opts.arrowWidth || Math.max(1.4, fontPx * 0.14);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(tx, ty);
      ctx.stroke();
      var ah = fontPx * 0.9;
      var px = -dy;
      var py = dx;
      ctx.beginPath();
      ctx.moveTo(tx, ty);
      ctx.lineTo(tx - dx * ah + px * ah * 0.42, ty - dy * ah + py * ah * 0.42);
      ctx.lineTo(tx - dx * ah - px * ah * 0.42, ty - dy * ah - py * ah * 0.42);
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }

  function ringColor(i, n) {
    var P = global.FreqPalette;
    if (P) return P.hexAt(i, n || 8);
    var S = global.SpectrumColors;
    if (S) return S.forIndex(i, n || 8).css;
    return "#e11d48";
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

  var envStack = [];
  function enter(env, fn) {
    var args = [];
    var i;
    for (i = 2; i < arguments.length; i++) args.push(arguments[i]);
    envStack.push(env);
    try {
      return fn.apply(null, args);
    } finally {
      envStack.pop();
    }
  }
  function bindPass(env, fn) {
    return function () {
      envStack.push(env);
      try {
        return fn.apply(null, arguments);
      } finally {
        envStack.pop();
      }
    };
  }
  function create(opts) {
    var env = {};
    env.opts = opts;
    env.opts = env.opts || {};
    env.topCanvas = env.opts.topCanvas;
    env.sideCanvas = env.opts.sideCanvas;
    env.view3dCanvas = env.opts.view3dCanvas || null;
    env.polarL = env.opts.polarL || null;
    env.polarC = env.opts.polarC || null;
    env.polarR = env.opts.polarR || null;
    env.getState = env.opts.getState;
    env.setState = env.opts.setState;
    env.onChange = env.opts.onChange || function () {};
    env.onPolar = env.opts.onPolar || null;
    env.RoomMath = env.opts.RoomMath || global.RoomMath;

    env.tctx = env.topCanvas.getContext("2d");
    env.drag = null;
    env.hover = null;
    env.selected = null;
    env.planeMode = "top";
    env.viewZoom = 1;
    env.sideAz = 0;

    env.topLay = null;
    env.sideLay = null;
    env.view3d = null;
    env.liveReadout = "";
    env.polarField = null;
    env.polarStatus = "pending";
    env.soloBand = null;
    env.drawnDb = { L: null, C: null, R: null };
    env.drawnPts = { L: [], C: [], R: [] };

    /* Drawn point. On-stand keeps the stand pose. Room reads the room spot.
       An MS side is drawn on the mid, aimed the way the engine parks it. */

    /* Frame bounds use the drag-start spot so the view does not chase the pointer. */

    /* A room mic's aim is its own spot. A missing per-strip yaw falls back to the shared one. */

    env.topCanvas.addEventListener("pointerdown", function (evt) {
      var geo = enter(env, geoOf);
      var p = enter(env, canvasPos, env.topCanvas, evt);
      var kind = enter(env, hitPlane, p.x, p.y, geo);
      if (!kind) {
        env.selected = null;
        env.liveReadout = "";
        enter(env, redraw);
        return;
      }
      env.selected = kind;
      env.drag = {
        kind: kind,
        canvas: env.planeMode === "side" ? "side" : "top",
        x0: p.x,
        y0: p.y,
        moved: false,
        armed: true,
        lastX: p.x
      };
      env.topCanvas.classList.add("dragging");
      enter(env, setCursor, env.topCanvas, kind);
      try { env.topCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
      var hitSlot = enter(env, slotOfKind, kind);
      if (hitSlot && kind.indexOf("cap") === 0) {
        var hitPose = enter(env, viewMic, geo, hitSlot);
        env.drag.anchor = { cap: hitSlot, x: hitPose.x, y: hitPose.y, z: hitPose.z };
      }
      if (kind.indexOf("yaw") === 0) {
        env.drag.moved = true;
        var origin;
        if (enter(env, roomPlaced, geo.state, hitSlot)) {
          var yawPose = enter(env, viewMic, geo, hitSlot);
          origin = enter(env, topToPx, yawPose.x, yawPose.z, env.topLay);
        } else if (kind === "yawL") origin = enter(env, topToPx, geo.mic_left.x, geo.mic_left.z, env.topLay);
        else if (kind === "yawR") origin = enter(env, topToPx, geo.mic_right.x, geo.mic_right.z, env.topLay);
        else origin = enter(env, topToPx, geo.mic_centre.x, geo.mic_centre.z, env.topLay);
        enter(env, applyYawFromPointer, kind, p.x, p.y, origin);
      }
      enter(env, redraw);
      evt.preventDefault();
    });

    env.topCanvas.addEventListener("pointermove", function (evt) {
      var geo = enter(env, geoOf);
      var p = enter(env, canvasPos, env.topCanvas, evt);
      if (env.drag && (env.drag.canvas === "top" || env.drag.canvas === "side")) {
        var dist = Math.hypot(p.x - env.drag.x0, p.y - env.drag.y0);
        if (!env.drag.moved && dist < DRAG_THRESH && env.drag.kind.indexOf("yaw") !== 0) {
          return;
        }
        env.drag.moved = true;
        if (env.drag.canvas === "side") {
          var turn = p.x - (env.drag.lastX != null ? env.drag.lastX : p.x);
          env.drag.lastX = p.x;
          env.sideAz -= turn * 0.007;
          env.sideLay = enter(env, sideFrame, geo);
          enter(env, applySideDrag, env.drag.kind, p.x, p.y);
        } else {
          env.topLay = enter(env, topFrame, geo);
          enter(env, applyTopDrag, env.drag.kind, p.x, p.y);
        }
        enter(env, redraw);
        return;
      }
      var h = enter(env, hitPlane, p.x, p.y, geo);
      if (h !== env.hover) {
        env.hover = h;
        enter(env, setCursor, env.topCanvas, h);
        enter(env, redraw);
      } else {
        enter(env, setCursor, env.topCanvas, h);
      }
    });

    env.topCanvas.addEventListener("wheel", function (evt) {
      evt.preventDefault();
      var factor = evt.deltaY > 0 ? (1 / 1.12) : 1.12;
      env.viewZoom = Math.max(0.55, Math.min(8, (env.viewZoom || 1) * factor));
      enter(env, redraw);
    }, { passive: false });

    env.topCanvas.addEventListener("pointerup", bindPass(env, endDrag));
    env.topCanvas.addEventListener("pointercancel", bindPass(env, endDrag));
    window.addEventListener("pointerup", bindPass(env, endDrag));
    env.topCanvas.addEventListener("pointerleave", function () {
      if (env.drag) return;
      if (env.hover) { env.hover = null; enter(env, setCursor, env.topCanvas, null); enter(env, redraw); }
    });
    enter(env, setCursor, env.topCanvas, null);

    document.querySelectorAll("#micPlaneRow [data-plane]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        env.planeMode = btn.getAttribute("data-plane") === "side" ? "side" : "top";
        enter(env, syncPlaneButtons);
        enter(env, redraw);
        enter(env, ensureView3d);
        if (env.view3d && env.view3d.setHaloPlane) env.view3d.setHaloPlane(env.planeMode, true);
        if (env.view3d && env.view3d.setHalo) env.view3d.setHalo(env.polarField, env.planeMode);
      });
    });
    enter(env, syncPlaneButtons);

    /* Screen angle matches the +sin lobe: front is up, +yaw is to the right. */

    enter(env, bindPolar, env.polarL, "polarL");
    enter(env, bindPolar, env.polarC, "polarC");
    enter(env, bindPolar, env.polarR, "polarR");

    return {
      redraw: bindPass(env, redraw),
      probe: bindPass(env, probe),
      setPolar: bindPass(env, setPolar),
      setSoloBand: function (index) {
        env.soloBand = (index == null || index < 0) ? null : index;
        enter(env, redraw);
      },
      setPolarStatus: function (status) { env.polarStatus = status || "pending"; enter(env, redraw); },
      drawnGrid: bindPass(env, drawnGrid),
      drawnPoints: function (which) { return env.drawnPts[String(which || "L").toUpperCase()] || []; },
      get view3d() { return env.view3d; },
      dispose: function () {
        if (env.view3d && env.view3d.dispose) env.view3d.dispose();
      }
    };
  }
  function dpr() { var env = envStack[envStack.length - 1];
      return Math.min(window.devicePixelRatio || 1, 2);
    }
  function uiPx(n) { var env = envStack[envStack.length - 1];
      return n * dpr();
    }
  function fitCanvas(canvas) { var env = envStack[envStack.length - 1];
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
  function ensureView3d() { var env = envStack[envStack.length - 1];
      if (env.view3d || !env.view3dCanvas || !global.Room3D) return env.view3d;
      var rect = env.view3dCanvas.getBoundingClientRect();
      if (rect.width < 2 || rect.height < 2) return null;
      env.view3d = global.Room3D.create({
        canvas: env.view3dCanvas,
        getState: env.getState,
        setState: env.setState,
        onChange: env.onChange,
        RoomMath: env.RoomMath,
        focusMic: true
      });
      return env.view3d;
    }
  function canvasPos(canvas, evt) { var env = envStack[envStack.length - 1];
      var r = canvas.getBoundingClientRect();
      return {
        x: (evt.clientX - r.left) * (canvas.width / r.width),
        y: (evt.clientY - r.top) * (canvas.height / r.height)
      };
    }
  function geoOf() { var env = envStack[envStack.length - 1];
      return env.RoomMath.compute(env.getState());
    }
  function setCursor(canvas, kind) { var env = envStack[envStack.length - 1];
      if (!kind) {
        canvas.style.cursor = "grab";
        return;
      }
      if (String(kind).indexOf("yaw") === 0) canvas.style.cursor = "crosshair";
      else canvas.style.cursor = env.drag ? "grabbing" : "grab";
    }
  function topFrame(geo) { var env = envStack[envStack.length - 1];
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
      var zoom = Math.max(0.55, Math.min(8, env.viewZoom || 1));
      var spanX = Math.max(0.32, (x1 - x0) / zoom);
      var spanZ = Math.max(0.32, (z1 - z0) / zoom);
      x0 = cx - spanX * 0.5;
      z0 = cz - spanZ * 0.5;
      /* A room spot outside the stand window widens the frame. On-stand framing stays. */
      var rx0 = x0, rx1 = x0 + spanX, rz0 = z0, rz1 = z0 + spanZ, grew = false;
      ["l", "c", "r"].forEach(function (cap) {
        if (!enter(env, roomPlaced, s, cap)) return;
        if (cap === "c" && s.mic_setup === "binaural") return;
        var v = enter(env, framePoint, geo, cap);
        if (v.x < rx0 || v.x > rx1 || v.z < rz0 || v.z > rz1) {
          rx0 = Math.min(rx0, v.x - 0.35);
          rx1 = Math.max(rx1, v.x + 0.35);
          rz0 = Math.min(rz0, v.z - 0.35);
          rz1 = Math.max(rz1, v.z + 0.35);
          grew = true;
        }
      });
      if (grew) {
        spanX = Math.max(0.32, rx1 - rx0);
        spanZ = Math.max(0.32, rz1 - rz0);
        x0 = rx0;
        z0 = rz0;
      }
      var cw = env.topCanvas.width;
      var ch = env.topCanvas.height;
      var margin = 36;
      var scale = Math.min((cw - margin * 2) / spanX, (ch - margin * 2) / spanZ);
      var rw = spanX * scale;
      var rh = spanZ * scale;
      return {
        x0: x0, z0: z0, spanX: spanX, spanZ: spanZ, scale: scale,
        ox: (cw - rw) / 2, oy: (ch - rh) / 2 + 2, rw: rw, rh: rh
      };
    }
  function alongOf(x, z, geo) { var env = envStack[envStack.length - 1];
      var dx = x - geo.state.mcx;
      var dz = z - geo.state.mcz;
      return dx * Math.sin(env.sideAz) + dz * Math.cos(env.sideAz);
    }
  function sideFrame(geo) { var env = envStack[envStack.length - 1];
      var s = geo.state;
      var canvas = env.topCanvas;
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
      var zoom = Math.max(0.55, Math.min(8, env.viewZoom || 1));
      var spanZ = Math.max(0.4, (a1 - a0) / zoom);
      var spanY = Math.max(0.4, (yHi - yLo) / zoom);
      var midA = 0;
      var z0 = midA - spanZ * 0.5;
      yLo = Math.max(0, ((yLo + yHi) * 0.5) - spanY * 0.5);
      var aLo = z0, aHi = z0 + spanZ, yLoF = yLo, yHiF = yLo + spanY, grew = false;
      ["l", "c", "r"].forEach(function (cap) {
        if (!enter(env, roomPlaced, s, cap)) return;
        if (cap === "c" && s.mic_setup === "binaural") return;
        var v = enter(env, framePoint, geo, cap);
        var along = enter(env, alongOf, v.x, v.z, geo);
        if (along < aLo || along > aHi || v.y < yLoF || v.y > yHiF) {
          aLo = Math.min(aLo, along - 0.35);
          aHi = Math.max(aHi, along + 0.35);
          yLoF = Math.min(yLoF, Math.max(0, v.y - 0.35));
          yHiF = Math.max(yHiF, Math.min(s.H, v.y + 0.35));
          grew = true;
        }
      });
      if (grew) {
        z0 = aLo;
        spanZ = Math.max(0.4, aHi - aLo);
        yLo = yLoF;
        spanY = Math.max(0.4, yHiF - yLoF);
      }
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
  function topToPx(x, z, lay) { var env = envStack[envStack.length - 1];
      return {
        px: lay.ox + (x - lay.x0) * lay.scale,
        py: lay.oy + (lay.spanZ - (z - lay.z0)) * lay.scale
      };
    }
  function topToM(px, py, lay) { var env = envStack[envStack.length - 1];
      return {
        x: lay.x0 + (px - lay.ox) / lay.scale,
        z: lay.z0 + lay.spanZ - (py - lay.oy) / lay.scale
      };
    }
  function sideToPx(z, y, lay) { var env = envStack[envStack.length - 1];
      return {
        px: lay.ox + (z - lay.z0) * lay.scale,
        py: lay.oy + (lay.spanY - (y - lay.y0)) * lay.scale
      };
    }
  function sideToM(px, py, lay) { var env = envStack[envStack.length - 1];
      return {
        z: lay.z0 + (px - lay.ox) / lay.scale,
        y: lay.y0 + lay.spanY - (py - lay.oy) / lay.scale
      };
    }
  function drawHandle(ctx, px, py, color, label, active, hovered, radius) { var env = envStack[envStack.length - 1];
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
  function yawRingPx(lay) { var env = envStack[envStack.length - 1];
      return Math.max(36, Math.min(88, YAW_RING_M * lay.scale));
    }
  function yawKnobOf(geo, which, lay) { var env = envStack[envStack.length - 1];
      var cap = which === "L" ? "l" : (which === "R" ? "r" : "c");
      var mic = viewMic(geo, cap);
      var look = mic.look;
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
  function drawFrontDot(ctx, geo, which, color, kind) { var env = envStack[envStack.length - 1];
      var lay = env.topLay;
      var k = yawKnobOf(geo, which, lay);
      var active = env.selected === kind || (env.drag && env.drag.kind === kind);
      var hovered = env.hover === kind;
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
  function drawLookCone(ctx, px, py, look, color, scale, soft) { var env = envStack[envStack.length - 1];
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
  function drawLiveReadout(ctx, cw) { var env = envStack[envStack.length - 1];
      if (!env.liveReadout) return;
      ctx.font = "700 12px Segoe UI, system-ui, sans-serif";
      var tw = ctx.measureText(env.liveReadout).width;
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
      ctx.fillText(env.liveReadout, x + 10, y + 2);
    }
  function drawTop(geo) { var env = envStack[envStack.length - 1];
      fitCanvas(env.topCanvas);
      var ctx = env.tctx;
      var cw = env.topCanvas.width;
      var ch = env.topCanvas.height;
      env.topLay = topFrame(geo);
      var lay = env.topLay;
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

      drawPlaneHalo(ctx, env.polarField && env.polarField.halo_xz, function (phi, rad) {
        return enter(env, topToPx, 
          geo.mic_centre.x - Math.sin(phi) * rad,
          geo.mic_centre.z + Math.cos(phi) * rad,
          lay
        );
      });

      var vL = viewMic(geo, "l");
      var vC = viewMic(geo, "c");
      var vR = viewMic(geo, "r");
      var Lp = topToPx(vL.x, vL.z, lay);
      var Cp = topToPx(vC.x, vC.z, lay);
      var Rp = topToPx(vR.x, vR.z, lay);
      var standL = topToPx(geo.mic_left.x, geo.mic_left.z, lay);
      var standC = topToPx(geo.mic_centre.x, geo.mic_centre.z, lay);
      var standR = topToPx(geo.mic_right.x, geo.mic_right.z, lay);

      var ears = geo.state.mic_setup === "binaural";
      ctx.strokeStyle = "rgba(96,165,250,0.45)";
      ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(standL.px, standL.py); ctx.lineTo(standR.px, standR.py); ctx.stroke();
      if (!ears && !vC.room && Math.abs(geo.state.centre_dz || 0) > 1e-4) {
        ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(standC.px, standC.py); ctx.lineTo((standL.px + standR.px) * 0.5, standL.py); ctx.stroke();
        ctx.setLineDash([]);
      }

      drawLookCone(ctx, Lp.px, Lp.py, vL.look, COLORS.L, lay.scale, false);
      if (!ears) drawLookCone(ctx, Cp.px, Cp.py, vC.look, COLORS.C, lay.scale, true);
      drawLookCone(ctx, Rp.px, Rp.py, vR.look, COLORS.R, lay.scale, false);

      drawHandle(ctx, Lp.px, Lp.py, COLORS.L, "L",
        env.selected === "capL" || !!(env.drag && env.drag.kind === "capL"), env.hover === "capL", uiPx(16));
      drawHandle(ctx, Rp.px, Rp.py, COLORS.R, "R",
        env.selected === "capR" || !!(env.drag && env.drag.kind === "capR"), env.hover === "capR", uiPx(16));
      if (!ears) {
        drawHandle(ctx, Cp.px, Cp.py, COLORS.C, "C",
          env.selected === "capC" || !!(env.drag && env.drag.kind === "capC"), env.hover === "capC", uiPx(18));
      }

      drawFrontDot(ctx, geo, "L", COLORS.L, "yawL");
      if (!ears) drawFrontDot(ctx, geo, "C", COLORS.C, "yawC");
      drawFrontDot(ctx, geo, "R", COLORS.R, "yawR");

      ctx.fillStyle = COLORS.text;
      ctx.font = "600 11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      var setback = global.RRViewPose.topSetback(geo.state, roomSpotOf(geo.state, "c"));
      ctx.fillText(
        "space " + geo.state.space.toFixed(2) + " m" + setback +
        (env.selected ? " \u00b7 " + env.selected : ""),
        12, 18
      );
      ctx.textAlign = "center";
      ctx.fillText("X \u2192", lay.ox + lay.rw / 2, lay.oy + lay.rh + 16);
      drawLiveReadout(ctx, cw);
    }
  function drawSide(geo) { var env = envStack[envStack.length - 1];
      fitCanvas(env.topCanvas);
      var ctx = env.tctx;
      var cw = env.topCanvas.width;
      var ch = env.topCanvas.height;
      env.sideLay = sideFrame(geo);
      var lay = env.sideLay;
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
        return enter(env, sideToPx, Math.cos(phi) * rad, geo.mic_centre.y + Math.sin(phi) * rad, lay);
      });

      function at(obj) {
        return sideToPx(alongOf(obj.x, obj.z, geo), obj.y, lay);
      }
      var vL = viewMic(geo, "l");
      var vC = viewMic(geo, "c");
      var vR = viewMic(geo, "r");
      var Sp = at(geo.source);
      var Cp = at(vC);
      var Lp = at(vL);
      var Rp = at(vR);
      var standL = at(geo.mic_left);
      var standR = at(geo.mic_right);
      var floorMic = sideToPx(alongOf(vC.x, vC.z, geo), 0, lay);
      var floorSrc = sideToPx(alongOf(geo.source.x, geo.source.z, geo), 0, lay);

      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = "rgba(251,191,36,0.35)";
      ctx.beginPath(); ctx.moveTo(floorSrc.px, floorSrc.py); ctx.lineTo(Sp.px, Sp.py); ctx.stroke();
      ctx.strokeStyle = "rgba(96,165,250,0.45)";
      ctx.beginPath(); ctx.moveTo(floorMic.px, floorMic.py); ctx.lineTo(Cp.px, Cp.py); ctx.stroke();
      ctx.setLineDash([]);

      ctx.strokeStyle = "rgba(96,165,250,0.35)";
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(standL.px, standL.py); ctx.lineTo(standR.px, standR.py); ctx.stroke();

      drawHandle(ctx, Lp.px, Lp.py, COLORS.L, "L",
        env.selected === "capL" || !!(env.drag && env.drag.kind === "capL"), env.hover === "capL", uiPx(16));
      drawHandle(ctx, Rp.px, Rp.py, COLORS.R, "R",
        env.selected === "capR" || !!(env.drag && env.drag.kind === "capR"), env.hover === "capR", uiPx(16));
      drawHandle(ctx, Cp.px, Cp.py, COLORS.C, "C",
        env.selected === "capC" || !!(env.drag && env.drag.kind === "capC"), env.hover === "capC", uiPx(18));
      drawHandle(ctx, Sp.px, Sp.py, COLORS.src, "Source",
        env.selected === "src" || !!(env.drag && env.drag.kind === "src"), env.hover === "src", uiPx(16));

      ctx.fillStyle = COLORS.text;
      ctx.font = "11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText("Floor", lay.ox + 6, Math.min(ch - 8, fl.py + 12));
      ctx.textAlign = "right";
      ctx.fillStyle = COLORS.src;
      ctx.fillText("Src " + (geo.state.sy != null ? geo.state.sy : geo.state.my).toFixed(2) + " m", cw - 10, Sp.py + 4);
      ctx.fillStyle = COLORS.stand;
      ctx.fillText(
        global.RRViewPose.sideHeightLine(geo.state, {
          l: geo.mic_left, c: geo.mic_centre, r: geo.mic_right
        }, {
          l: roomSpotOf(geo.state, "l"),
          c: roomSpotOf(geo.state, "c"),
          r: roomSpotOf(geo.state, "r")
        }),
        cw - 10, Cp.py + 4
      );
      ctx.textAlign = "center";
      ctx.fillStyle = COLORS.text;
      ctx.fillText("drag left / right to turn the view  \u00b7  drag a mic up / down", lay.ox + lay.rw / 2, ch - 6);
      drawLiveReadout(ctx, cw);
    }
  function polarLayout(canvas) { var env = envStack[envStack.length - 1];
      var w = canvas.width, h = canvas.height;
      return { cx: w * 0.5, cy: h * 0.52, R: Math.min(w, h) * 0.38, w: w, h: h };
    }
  function polarFrontPx(canvas, yawDeg) { var env = envStack[envStack.length - 1];
      var lay = polarLayout(canvas);
      var yaw = ((Number(yawDeg) || 0) * Math.PI) / 180;
      /* Match RRLook: screen ( S·sin yaw, −cos yaw ) so +Z is up. */
      var S = global.RRLook.YAW_X_SIGN;
      return {
        px: lay.cx + S * lay.R * Math.sin(yaw),
        py: lay.cy - lay.R * Math.cos(yaw),
        cx: lay.cx, cy: lay.cy, R: lay.R
      };
    }
  function sampleRow(row, theta) { var env = envStack[envStack.length - 1];
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
  function sideSlice(geo) { var env = envStack[envStack.length - 1];
      if (!env.polarField || !env.polarField.L || !env.polarField.centres_hz) {
        return env.polarField && env.polarField.halo_yz;
      }
      var freqs = env.polarField.centres_hz;
      var grids = [env.polarField.L, env.polarField.C, env.polarField.R];
      var poss = [geo.mic_left, geo.mic_centre, geo.mic_right];
      var looks = [geo.look_l, geo.look_c || { x: 0, z: 1 }, geo.look_r];
      var fams = [geo.state.family_l, geo.state.family_c, geo.state.family_r];
      var pols = [geo.state.polar_l, geo.state.polar_c, geo.state.polar_r];
      var pats = [geo.state.pattern_l, geo.state.pattern_c, geo.state.pattern_r];
      var rx = Math.sin(env.sideAz);
      var rz = Math.cos(env.sideAz);
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
            var g = global.RRPattern.polarGain(theta, fams[mi], pols[mi], pats[mi]);
            signed = g < 0 ? -mag : (g === 0 ? 0 : mag);
            var phase = (((poss[mi].x - c.x) * ux + (poss[mi].y - c.y) * uy + (poss[mi].z - c.z) * uz) / 340) * Math.PI * 2 * freq;
            re += signed * Math.cos(phase);
            im += signed * Math.sin(phase);
          }
          out[bi][ai] = Math.sqrt(re * re + im * im);
        }
      }
      return out;
    }
  function drawPlaneHalo(ctx, grid, project) { var env = envStack[envStack.length - 1];
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
  function ringRadius(grid, bi, ai) { var env = envStack[envStack.length - 1];
      if (!grid || !grid[bi]) return 0;
      var v = Number(grid[bi][ai]);
      return isFinite(v) ? Math.max(0, v) : 0;
    }
  function gridPeak(grid) { var env = envStack[envStack.length - 1];
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
  function paintRingLegend(labels) { var env = envStack[envStack.length - 1];
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
  function drawPolar2d(canvas, family, polar, yawDeg, color, label, grid, captionTail) { var env = envStack[envStack.length - 1];
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
      var yaw = ((Number(yawDeg) || 0) * Math.PI) / 180;
      var optEarly = arguments[8] || {};
      var dbGridEarly = optEarly.db;
      var useDbEarly = !!optEarly.useDb && dbGridEarly && dbGridEarly.length;
      drawPolarChartFrame(ctx, cx, cy, R, yaw, {
        useDb: useDbEarly,
        arrow: false,
        fontPx: Math.max(uiPx(9), Math.min(uiPx(12), R * 0.1)),
        lineWidth: 1
      });
      var opt = arguments[8] || {};
      var dbGrid = opt.db;
      var useDb = !!opt.useDb && dbGrid && dbGrid.length;
      if (opt.note) {
        ctx.fillStyle = COLORS.text;
        ctx.font = "12px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(opt.note, cx, cy);
        ctx.fillStyle = COLORS.ink;
        ctx.font = "700 12px Segoe UI, system-ui, sans-serif";
        ctx.fillText(label, cx, 14);
        return;
      }
      if (useDb) {
        var nAzD = dbGrid[0].length;
        var floorDb = -30;
        function radDb(db) {
          if (!(db > floorDb)) db = floorDb;
          if (db > 0) db = 0;
          return (db - floorDb) / (0 - floorDb);
        }
        var pts = [];
        for (bi = 0; bi < dbGrid.length; bi++) {
          if (env.soloBand != null && bi !== env.soloBand) continue;
          ctx.beginPath();
          for (ai = 0; ai <= nAzD; ai++) {
            var kd = ai % nAzD;
            theta = (kd / nAzD) * Math.PI * 2;
            screen = theta + yaw;
            g = radDb(Number(dbGrid[bi][kd]));
            sx = cx + R * g * Math.sin(screen);
            sy = cy - R * g * Math.cos(screen);
            if (ai === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
            if (ai < nAzD && kd % Math.max(1, Math.round(nAzD / 8)) === 0) {
              pts.push({ band: bi, az: kd, x: sx, y: sy, db: Number(dbGrid[bi][kd]) });
            }
          }
          ctx.strokeStyle = ringColor(bi, dbGrid.length);
          ctx.lineWidth = bi === dbGrid.length - 1 ? 2 : 1.25;
          ctx.stroke();
        }
        ctx.save();
        ctx.setLineDash([uiPx(5), uiPx(4)]);
        ctx.beginPath();
        var nIdeal = 128;
        var ii, thI, gI, dbI, radI;
        for (ii = 0; ii <= nIdeal; ii++) {
          thI = (ii / nIdeal) * Math.PI * 2;
          gI = Math.abs(global.RRPattern.polarGain(thI - yaw, family, polar, opt.pattern));
          dbI = gI > 1e-6 ? (20 * Math.log(gI) / Math.LN10) : -120;
          radI = radDb(dbI);
          sx = cx + R * radI * Math.sin(thI);
          sy = cy - R * radI * Math.cos(thI);
          if (ii === 0) ctx.moveTo(sx, sy);
          else ctx.lineTo(sx, sy);
        }
        ctx.closePath();
        ctx.strokeStyle = "rgba(232,234,239,0.92)";
        ctx.lineWidth = Math.max(1, uiPx(1.25));
        ctx.stroke();
        ctx.restore();
        if (opt.cap) env.drawnPts[opt.cap] = pts;
      } else if (grid && grid.length && grid[0] && grid[0].length) {
        var nAz = grid[0].length;
        var bi, ai, theta, screen, g, sx, sy;
        for (bi = 0; bi < grid.length; bi++) {
          if (env.soloBand != null && bi !== env.soloBand) continue;
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
          g = Math.abs(global.RRPattern.polarGain(th - yaw, family, polar, opt.pattern));
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

      if (opt.fig8) {
        var frontMark = polarFrontPx(canvas, yawDeg);
        ctx.fillStyle = COLORS.ink;
        ctx.font = "700 13px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("+", frontMark.px, frontMark.py - 14);
        var backYaw = (Number(yawDeg) || 0) + 180;
        var back = polarFrontPx(canvas, backYaw);
        ctx.fillText(opt.minusLabel || "\u2212", back.px, back.py - 14);
      }
      if (opt.routeNote) {
        ctx.fillStyle = COLORS.text;
        ctx.font = "10px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "left";
        ctx.fillText(opt.routeNote, 8, 28);
      }

      var front = polarFrontPx(canvas, yawDeg);
      var fdx = front.px - cx;
      var fdy = front.py - cy;
      var flen = Math.hypot(fdx, fdy) || 1;
      var ux = fdx / flen;
      var uy = fdy / flen;
      var tipx = cx + ux * R * 0.92;
      var tipy = cy + uy * R * 0.92;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(tipx, tipy);
      ctx.strokeStyle = hexRgba(COLORS.yaw, 0.9);
      ctx.lineWidth = 1.6;
      ctx.stroke();
      var ah = uiPx(9);
      var pxv = -uy;
      var pyv = ux;
      ctx.beginPath();
      ctx.moveTo(tipx, tipy);
      ctx.lineTo(tipx - ux * ah + pxv * ah * 0.42, tipy - uy * ah + pyv * ah * 0.42);
      ctx.lineTo(tipx - ux * ah - pxv * ah * 0.42, tipy - uy * ah - pyv * ah * 0.42);
      ctx.closePath();
      ctx.fillStyle = COLORS.yaw;
      ctx.fill();
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
      var lab = (env.RoomMath && env.RoomMath.polarLabel) ? env.RoomMath.polarLabel(family, polar, opt.pattern) : String(family);
      ctx.fillStyle = COLORS.ink;
      ctx.font = "700 12px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(label, cx, 14);
      ctx.fillStyle = COLORS.text;
      ctx.font = "10px Segoe UI, system-ui, sans-serif";
      var tail = captionTail || "drag front or the rim";
      ctx.fillText(lab + " \u00b7 " + fmtYaw(yawDeg) + "  \u00b7 " + tail, cx, lay.h - 8);
    }
  function coincidentS(st, cap) { var env = envStack[envStack.length - 1];
      if (!st || st.pair_mode !== "ms" || st.s_detached) return false;
      return String(st.ms_s || "l") === String(cap || "").toLowerCase();
    }
  function roomPlaced(st, slot) { var env = envStack[envStack.length - 1];
      if (global.RRViewPose && RRViewPose.isRoom) return RRViewPose.isRoom(st, slot);
      if (!st) return false;
      var key = String(slot || "").toLowerCase();
      if (st["place_" + key] === "room") return true;
      return key === "c" && st.third_mic === "room";
    }
  function roomSpotOf(st, cap) { var env = envStack[envStack.length - 1];
      if (global.RRDrag && RRDrag.roomSpot) return RRDrag.roomSpot(st, cap);
      function pick(k) {
        var v = st["room_" + cap + "_" + k];
        if (v == null || v === "" || !isFinite(Number(v))) v = st["room_" + k];
        var n = Number(v);
        return isFinite(n) ? n : 0;
      }
      return { x: pick("x"), y: pick("y"), z: pick("z"), yaw: pick("yaw") };
    }
  function viewMic(geo, cap) { var env = envStack[envStack.length - 1];
      var stand = cap === "l" ? geo.mic_left : (cap === "r" ? geo.mic_right : geo.mic_centre);
      var look = cap === "l" ? geo.look_l : (cap === "r" ? geo.look_r : (geo.look_c || { x: 0, z: 1 }));
      if (!roomPlaced(geo.state, cap)) {
        if (coincidentS(geo.state, cap)) {
          var mid = String(geo.state.ms_m || "c");
          if (mid === cap) mid = cap === "c" ? "l" : "c";
          var host = mid === "l" ? geo.mic_left : (mid === "r" ? geo.mic_right : geo.mic_centre);
          var yaw = (Number(geo.state["yaw_" + cap + "_deg"]) || 0) * Math.PI / 180;
          var sideLook = global.RRLook.lookFromYaw(yaw);
          return { x: host.x, y: host.y, z: host.z, look: sideLook, room: false };
        }
        return { x: stand.x, y: stand.y, z: stand.z, look: look, room: false };
      }
      var spot = roomSpotOf(geo.state, cap);
      var yaw = (Number(spot.yaw) || 0) * Math.PI / 180;
      var roomLook = global.RRLook.lookFromYaw(yaw);
      return { x: spot.x, y: spot.y, z: spot.z, look: roomLook, room: true };
    }
  function framePoint(geo, cap) { var env = envStack[envStack.length - 1];
      var v = viewMic(geo, cap);
      if (env.drag && env.drag.anchor && env.drag.anchor.cap === cap) {
        return { x: env.drag.anchor.x, y: env.drag.anchor.y, z: env.drag.anchor.z };
      }
      return v;
    }
  function slotOfKind(kind) { var env = envStack[envStack.length - 1];
      if (kind === "capC" || kind === "yawC") return "c";
      if (kind === "capL" || kind === "yawL") return "l";
      if (kind === "capR" || kind === "yawR") return "r";
      return null;
    }
  function aimYaw(st, slot, fallback) { var env = envStack[envStack.length - 1];
      if (!roomPlaced(st, slot)) return fallback;
      var key = "room_" + String(slot || "").toLowerCase() + "_yaw";
      if (st[key] != null && st[key] !== "" && isFinite(Number(st[key]))) return Number(st[key]);
      if (isFinite(Number(st.room_yaw))) return Number(st.room_yaw);
      return fallback;
    }
  function drawPolars(geo) { var env = envStack[envStack.length - 1];
      var s = geo.state;
      var caps = [
        ["L", "l", env.polarL, s.yaw_l_deg != null ? s.yaw_l_deg : geo.toe_l_deg, COLORS.L],
        ["C", "c", env.polarC, s.yaw_c_deg != null ? s.yaw_c_deg : (geo.toe_c_deg || 0), COLORS.C],
        ["R", "r", env.polarR, s.yaw_r_deg != null ? s.yaw_r_deg : geo.toe_r_deg, COLORS.R]
      ];
      var mode = s.colour_mode || "MEASURED_SHELF";
      var toys = mode === "ASSUMED_TOYS";
      var useDb = !toys && (s.polar_radius || S("polar_radius")) !== "linear";
      var locked = mode === "MEASURED_SHELF" || mode === "BYPASS";
      caps.forEach(function (row) {
        var key = row[0];
        var slot = row[1];
        var fam = familyOf(s, slot);
        var pol = polarOf(s, slot);
        var yaw = enter(env, aimYaw, s, slot, row[3]);
        var fixed = enter(env, coincidentS, s, slot);
        var tail = fixed
          ? "coincident with M \u00b7 aim is M + 90\u00b0"
          : (locked ? "preset law \u00b7 drag front to aim" : "drag front or the rim");
        var db = env.polarField && env.polarField.each_db && env.polarField.each_db[key];
        var grid = env.polarField && env.polarField[key];
        var note = "";
        if (!toys && (env.polarStatus === "fail" || env.polarStatus !== "ok" || (useDb && !db))) {
          note = env.polarStatus === "fail" ? "polar data unavailable" : "updating\u2026";
        }
        if (db) env.drawnDb[key] = db;
        var route = String(s["mic_route_" + slot] || "pan");
        var fig8 = fam === "bi" || String(s["pattern_" + slot] || "") === "fig8";
        enter(env, drawPolar2d, row[2], fam, pol, yaw, row[4], key, toys ? grid : (useDb ? null : grid), tail, {
          db: db,
          useDb: useDb && !toys,
          note: note,
          cap: key,
          fig8: fig8,
          minusLabel: route === "s" ? "\u2212S" : "\u2212",
          routeNote: route === "s" ? "S \u2192 +L, \u2212R" : "",
          pattern: s["pattern_" + slot]
        });
      });
    }
  function syncPlaneButtons() { var env = envStack[envStack.length - 1];
      var topBtn = document.getElementById("micPlaneTop");
      var sideBtn = document.getElementById("micPlaneSide");
      var title = document.getElementById("micPlaneTitle");
      var hint = document.getElementById("micPlaneHint");
      if (topBtn) topBtn.classList.toggle("active", env.planeMode !== "side");
      if (sideBtn) sideBtn.classList.toggle("active", env.planeMode === "side");
      if (title) title.textContent = env.planeMode === "side" ? "Side" : "Top";
      if (hint) {
        var st = env.getState();
        var any = roomPlaced(st, "l") || roomPlaced(st, "c") || roomPlaced(st, "r");
        hint.textContent = global.RRViewPose.planeHint(env.planeMode === "side" ? "side" : "top", any);
      }
    }
  function redraw() { var env = envStack[envStack.length - 1];
      syncPlaneButtons();
      var geo = geoOf();
      if (env.planeMode === "side") drawSide(geo);
      else drawTop(geo);
      drawPolars(geo);
      drawRoomPolars(geo);
      if (global.RRPolarViews && RRPolarViews.paintArrivals) RRPolarViews.paintArrivals();
      ensureView3d();
      if (env.view3d) env.view3d.redraw();
      return geo;
    }
  function hitYaw(px, py, geo, which, kind) { var env = envStack[envStack.length - 1];
      var k = yawKnobOf(geo, which, env.topLay || topFrame(geo));
      if (Math.hypot(px - k.px, py - k.py) <= uiPx(16)) return kind;
      return null;
    }
  function hitTop(px, py, geo) { var env = envStack[envStack.length - 1];
      var lay = env.topLay || topFrame(geo);
      env.topLay = lay;
      var ears = geo.state.mic_setup === "binaural";
      var vL = viewMic(geo, "l");
      var vR = viewMic(geo, "r");
      var vC = viewMic(geo, "c");
      var Lp = topToPx(vL.x, vL.z, lay);
      var Rp = topToPx(vR.x, vR.z, lay);
      var Cp = topToPx(vC.x, vC.z, lay);

      var bodies = [
        { k: "capL", d: Math.hypot(px - Lp.px, py - Lp.py), lim: uiPx(24) },
        { k: "capR", d: Math.hypot(px - Rp.px, py - Rp.py), lim: uiPx(24) }
      ];
      if (!ears) bodies.push({ k: "capC", d: Math.hypot(px - Cp.px, py - Cp.py), lim: uiPx(26) });
      bodies.sort(function (a, b) { return a.d - b.d; });
      if (bodies[0].d <= bodies[0].lim) return bodies[0].k;
      var y;
      y = hitYaw(px, py, geo, "L", "yawL"); if (y) return y;
      if (!ears) { y = hitYaw(px, py, geo, "C", "yawC"); if (y) return y; }
      y = hitYaw(px, py, geo, "R", "yawR"); if (y) return y;
      return null;
    }
  function hitSide(px, py, geo) { var env = envStack[envStack.length - 1];
      var lay = env.sideLay || sideFrame(geo);
      function at(obj) {
        return sideToPx(alongOf(obj.x, obj.z, geo), obj.y, lay);
      }
      var ears = geo.state.mic_setup === "binaural";
      var spots = [
        { k: "capL", p: at(viewMic(geo, "l")), lim: uiPx(24) },
        { k: "capR", p: at(viewMic(geo, "r")), lim: uiPx(24) },
        { k: "src", p: at(geo.source), lim: uiPx(24) }
      ];
      if (!ears) spots.unshift({ k: "capC", p: at(viewMic(geo, "c")), lim: uiPx(26) });
      spots.sort(function (a, b) {
        return Math.hypot(px - a.p.px, py - a.p.py) - Math.hypot(px - b.p.px, py - b.p.py);
      });
      var best = spots[0];
      if (Math.hypot(px - best.p.px, py - best.p.py) <= best.lim) return best.k;
      return "orbit";
    }
  function applyYawFromPointer(kind, px, py, originPx) { var env = envStack[envStack.length - 1];
      /* Aim on screen is (S·sin yaw, −cos yaw), so +Z is up (S = RRLook.YAW_X_SIGN).
         atan2(S·dx, −dy) keeps the handle under the pointer.
         Dragging right moves the handle right. */
      var S = global.RRLook.YAW_X_SIGN;
      var dx = px - originPx.px;
      var dy = py - originPx.py;
      var deg = Math.atan2(S * dx, -dy) * 180 / Math.PI;
      var st = Object.assign({}, env.getState());
      var link = st.link_mode || (st.link_lr_yaw === false ? "independent" : "mirror");
      var slot = (kind === "yawL" || kind === "polarL") ? "l" : ((kind === "yawR" || kind === "polarR") ? "r" : "c");
      if (st.pair_mode === "ms" && !st.s_detached && slot === String(st.ms_s || "l")) {
        st.s_detached = true;
      }
      if (roomPlaced(st, slot)) {
        st["room_" + slot + "_yaw"] = deg;
        env.setState(env.RoomMath.clampRoom(st));
        env.liveReadout = "Front " + fmtYaw(deg);
        env.onChange();
        return;
      }
      if (st.pair_mode === "stereo" && (slot === "l" || slot === "r")) {
        if (slot === "l") {
          st.yaw_l_deg = deg;
          st.yaw_r_deg = -deg;
        } else {
          st.yaw_r_deg = deg;
          st.yaw_l_deg = -deg;
        }
        st.toe_half_deg = Math.abs(deg);
        env.setState(env.RoomMath.clampRoom(st));
        env.liveReadout = "Front " + fmtYaw(deg);
        env.onChange();
        return;
      }
      if (slot === "l") {
        var prevL = Number(st.yaw_l_deg);
        if (!isFinite(prevL)) prevL = deg;
        st.yaw_l_deg = deg;
        if (link === "mirror") st.yaw_r_deg = -deg;
        else if (link === "linked") st.yaw_r_deg = Number(st.yaw_r_deg || 0) + (deg - prevL);
      } else if (slot === "r") {
        var prevR = Number(st.yaw_r_deg);
        if (!isFinite(prevR)) prevR = deg;
        st.yaw_r_deg = deg;
        if (link === "mirror") st.yaw_l_deg = -deg;
        else if (link === "linked") st.yaw_l_deg = Number(st.yaw_l_deg || 0) + (deg - prevR);
      } else {
        st.yaw_c_deg = deg;
      }
      st.link_lr_yaw = link === "mirror";
      if (st.yaw_l_deg != null && st.yaw_r_deg != null) {
        st.toe_half_deg = 0.5 * (Math.abs(Number(st.yaw_r_deg)) + Math.abs(Number(st.yaw_l_deg)));
      }
      env.setState(env.RoomMath.clampRoom(st));
      env.liveReadout = "Front " + fmtYaw(deg);
      env.onChange();
    }
  function maxSpace(W, mcx) { var env = envStack[envStack.length - 1];
      if (env.RoomMath.maxSpace) return env.RoomMath.maxSpace(W, mcx);
      return Math.max(0, 2 * Math.min(mcx, W - mcx));
    }
  function applyRoomFloor(st, slot, x, z) { var env = envStack[envStack.length - 1];
      var patch = (global.RRDrag && RRDrag.roomFloorDragTo)
        ? RRDrag.roomFloorDragTo(st, slot, x, z) : null;
      if (patch) Object.assign(st, patch);
      else {
        st["room_" + slot + "_x"] = x;
        st["room_" + slot + "_z"] = z;
      }
      env.setState(env.RoomMath.clampRoom(st));
      env.liveReadout = slot.toUpperCase() + " " + Number(st["room_" + slot + "_x"]).toFixed(2)
        + " m, " + Number(st["room_" + slot + "_z"]).toFixed(2) + " m";
      env.onChange();
    }
  function applyRoomHeight(st, slot, y) { var env = envStack[envStack.length - 1];
      var patch = (global.RRDrag && RRDrag.roomHeightDragTo)
        ? RRDrag.roomHeightDragTo(st, slot, y) : null;
      if (patch) Object.assign(st, patch);
      else st["room_" + slot + "_y"] = y;
      env.setState(env.RoomMath.clampRoom(st));
      env.liveReadout = slot.toUpperCase() + " " + Number(st["room_" + slot + "_y"]).toFixed(2) + " m";
      env.onChange();
    }
  function applyTopDrag(kind, px, py) { var env = envStack[envStack.length - 1];
      var st = Object.assign({}, env.getState());
      var m = topToM(px, py, env.topLay);
      var geo = geoOf();
      var slot = slotOfKind(kind);
      if ((kind === "capC" || kind === "capL" || kind === "capR") && roomPlaced(st, slot)) {
        applyRoomFloor(st, slot, m.x, m.z);
        return;
      }
      if (kind === "capC") {
        st.align_horizontal = false;
        var dzMax = env.RoomMath.CENTRE_DZ_MAX != null ? env.RoomMath.CENTRE_DZ_MAX : 0.20;
        st.centre_dz = env.RoomMath.clamp(m.z - st.mcz, -dzMax, dzMax);
        env.setState(env.RoomMath.clampRoom(st));
        env.liveReadout = "C setback " + (st.centre_dz * 100).toFixed(0) + " cm";
        env.onChange();
      } else if (kind === "capL" || kind === "capR") {
        var halfWant = Math.abs(m.x - st.mcx);
        st.space = env.RoomMath.clamp(halfWant * 2, 0, maxSpace(st.W, st.mcx));
        env.setState(env.RoomMath.clampRoom(st));
        env.liveReadout = "Space " + st.space.toFixed(2) + " m";
        env.onChange();
      } else if (kind.indexOf("yaw") === 0) {
        var origin;
        if (roomPlaced(st, slot)) {
          var pose = viewMic(geo, slot);
          origin = topToPx(pose.x, pose.z, env.topLay);
        } else if (kind === "yawL") origin = topToPx(geo.mic_left.x, geo.mic_left.z, env.topLay);
        else if (kind === "yawR") origin = topToPx(geo.mic_right.x, geo.mic_right.z, env.topLay);
        else origin = topToPx(geo.mic_centre.x, geo.mic_centre.z, env.topLay);
        applyYawFromPointer(kind, px, py, origin);
      }
    }
  function applySideDrag(kind, px, py) { var env = envStack[envStack.length - 1];
      if (kind === "orbit") return;
      var m = sideToM(px, py, env.sideLay);
      var st = Object.assign({}, env.getState());
      var slot = slotOfKind(kind);
      if ((kind === "capC" || kind === "capL" || kind === "capR") && roomPlaced(st, slot)) {
        applyRoomHeight(st, slot, m.y);
        return;
      }
      var y = env.RoomMath.clamp(m.y, 0, st.H);
      var capLo = 0.02;
      var capHi = Math.max(capLo, st.H - 0.02);
      var yCap = env.RoomMath.clamp(m.y, capLo, capHi);
      if (kind === "src") {
        st.sy = y;
        if (st.link_heights) st.my = y;
        env.liveReadout = "Source " + y.toFixed(2) + " m";
      } else if (kind === "capC") {
        st.my_c = yCap;
        st.my = yCap;
        env.liveReadout = "Centre " + yCap.toFixed(2) + " m";
      } else if (kind === "capL" || kind === "capR") {
        if (st.align_horizontal) {
          st.my_l = yCap;
          st.my_r = yCap;
          env.liveReadout = "L and R " + yCap.toFixed(2) + " m";
        } else if (kind === "capL") {
          st.my_l = yCap;
          env.liveReadout = "Left " + yCap.toFixed(2) + " m";
        } else {
          st.my_r = yCap;
          env.liveReadout = "Right " + yCap.toFixed(2) + " m";
        }
      }
      env.setState(env.RoomMath.clampRoom(st));
      env.onChange();
    }
  function endDrag() { var env = envStack[envStack.length - 1];
      if (!env.drag) return;
      env.drag = null;
      env.liveReadout = "";
      env.topCanvas.classList.remove("dragging");
      setCursor(env.topCanvas, env.hover);
      redraw();
    }
  function hitPlane(px, py, geo) { var env = envStack[envStack.length - 1];
      if (env.planeMode === "side") {
        env.sideLay = sideFrame(geo);
        return hitSide(px, py, geo);
      }
      env.topLay = topFrame(geo);
      return hitTop(px, py, geo);
    }
  function wrapPi(a) { var env = envStack[envStack.length - 1];
      while (a > Math.PI) a -= Math.PI * 2;
      while (a < -Math.PI) a += Math.PI * 2;
      return a;
    }
  function capOfPolarKind(kind) { var env = envStack[envStack.length - 1];
      if (kind === "polarL") return "l";
      if (kind === "polarR") return "r";
      return "c";
    }
  function yawDegOf(cap) { var env = envStack[envStack.length - 1];
      var geo = geoOf();
      var s = geo.state;
      if (cap === "l") return s.yaw_l_deg != null ? s.yaw_l_deg : geo.toe_l_deg;
      if (cap === "r") return s.yaw_r_deg != null ? s.yaw_r_deg : geo.toe_r_deg;
      return s.yaw_c_deg != null ? s.yaw_c_deg : (geo.toe_c_deg || 0);
    }
  function polarWritable(cap) { var env = envStack[envStack.length - 1];
      var st = env.getState();
      var mode = st.colour_mode || "MEASURED_SHELF";
      if (mode === "MEASURED_SHELF" || mode === "BYPASS") return false;
      if (st.mic_setup === "binaural") return false;
      if (familyOf(st, cap) === "bi") return false;
      return true;
    }
  function screenTheta(canvas, px, py, cap) { var env = envStack[envStack.length - 1];
      var lay = polarLayout(canvas);
      var th = Math.atan2(px - lay.cx, -(py - lay.cy));
      var yaw = ((Number(yawDegOf(cap)) || 0) * Math.PI) / 180;
      return { lay: lay, theta: wrapPi(th - yaw), rad: Math.hypot(px - lay.cx, py - lay.cy) };
    }
  function polarHitMode(canvas, px, py, cap) { var env = envStack[envStack.length - 1];
      var front = polarFrontPx(canvas, yawDegOf(cap));
      if (Math.hypot(px - front.px, py - front.py) <= uiPx(14)) return "yaw";
      if (!polarWritable(cap)) return "yaw";
      var hit = screenTheta(canvas, px, py, cap);
      if (Math.abs(hit.theta) < 0.45) return "yaw";
      var st = env.getState();
      var outline = Math.abs(global.RRPattern.polarGain(hit.theta, familyOf(st, cap), polarOf(st, cap))) * hit.lay.R;
      if (Math.abs(hit.rad - outline) <= uiPx(18)) return "rim";
      return "yaw";
    }
  function polarFromRim(canvas, px, py, cap) { var env = envStack[envStack.length - 1];
      var hit = screenTheta(canvas, px, py, cap);
      if (Math.abs(hit.theta) < 0.45) return null;
      if (!(hit.lay.R > 0)) return null;
      var target = hit.rad / hit.lay.R;
      if (target > 1.35) return null;
      target = Math.max(0, Math.min(1, target));
      var fam = familyOf(env.getState(), cap);
      var best = 0.5;
      var bestErr = 1e9;
      var d, err;
      for (d = 0; d <= 1.0001; d += 0.01) {
        err = Math.abs(Math.abs(global.RRPattern.polarGain(hit.theta, fam, Math.min(1, d))) - target);
        if (err < bestErr) {
          bestErr = err;
          best = Math.min(1, d);
        }
      }
      return Math.round(best * 100) / 100;
    }
  function applyPolarValue(cap, value) { var env = envStack[envStack.length - 1];
      if (value == null || !isFinite(value)) return;
      if (!polarWritable(cap)) return;
      if (env.onPolar) {
        env.onPolar(cap, value);
        return;
      }
      var st = Object.assign({}, env.getState());
      st["polar_" + cap] = value;
      st.preset_owns_pattern = false;
      env.setState(st);
      env.onChange();
    }
  function bindPolar(canvas, kind) { var env = envStack[envStack.length - 1];
      if (!canvas) return;
      canvas.style.cursor = "crosshair";
      function act(p) {
        var cap = capOfPolarKind(kind);
        if (env.drag && env.drag.polarMode === "rim") {
          applyPolarValue(cap, polarFromRim(canvas, p.x, p.y, cap));
          return;
        }
        var lay = polarLayout(canvas);
        applyYawFromPointer(kind, p.x, p.y, { px: lay.cx, py: lay.cy });
      }
      canvas.addEventListener("pointerdown", function (evt) {
        var p = enter(env, canvasPos, canvas, evt);
        var cap = enter(env, capOfPolarKind, kind);
        var mode = enter(env, polarHitMode, canvas, p.x, p.y, cap);
        env.drag = { kind: kind, canvas: "polar", polarMode: mode, x0: p.x, y0: p.y, moved: true };
        env.selected = kind;
        act(p);
        enter(env, redraw);
        try { canvas.setPointerCapture(evt.pointerId); } catch (e) {}
        evt.preventDefault();
      });
      canvas.addEventListener("pointermove", function (evt) {
        if (!env.drag || env.drag.kind !== kind) return;
        act(enter(env, canvasPos, canvas, evt));
        enter(env, redraw);
      });
      canvas.addEventListener("pointerup", bindPass(env, endDrag));
      canvas.addEventListener("pointercancel", bindPass(env, endDrag));
    }
  function binauralHeadName(st) { var env = envStack[envStack.length - 1];
      var id = (st && st.binaural_preset) || "SADIE2_KU100";
      var sel = document.getElementById("binaural_preset");
      if (sel) {
        var opt = sel.querySelector("option[value='" + id + "']");
        if (opt && opt.textContent) return String(opt.textContent).trim();
      }
      if (id === "SADIE2_KEMAR") return "SADIE II KEMAR";
      if (id === "THK_KU100_FF") return "TH Köln KU100";
      return "SADIE II KU100";
    }
  function drawRoomPolars(geo) { var env = envStack[envStack.length - 1];
      var s = geo.state;
      var rows = [
        ["l", "L", "roomPolarL", COLORS.L, s.yaw_l_deg != null ? s.yaw_l_deg : geo.toe_l_deg],
        ["c", "C", "roomPolarC", COLORS.C, s.yaw_c_deg != null ? s.yaw_c_deg : (geo.toe_c_deg || 0)],
        ["r", "R", "roomPolarR", COLORS.R, s.yaw_r_deg != null ? s.yaw_r_deg : geo.toe_r_deg]
      ];
      var mode = s.colour_mode || "MEASURED_SHELF";
      var toys = mode === "ASSUMED_TOYS";
      var useDb = !toys && (s.polar_radius || S("polar_radius")) !== "linear";
      rows.forEach(function (row) {
        var canvas = document.getElementById(row[2]);
        if (!canvas) return;
        var slot = row[0];
        var key = row[1];
        var fam = familyOf(s, slot);
        var pol = polarOf(s, slot);
        var yaw = enter(env, aimYaw, s, slot, row[4]);
        var db = env.polarField && env.polarField.each_db && env.polarField.each_db[key];
        var grid = env.polarField && env.polarField[key];
        var note = "";
        if (!toys && (env.polarStatus === "fail" || env.polarStatus !== "ok" || (useDb && !db))) {
          note = env.polarStatus === "fail" ? "polar data unavailable" : "updating\u2026";
        }
        var fig8 = fam === "bi" || String(s["pattern_" + slot] || "") === "fig8";
        enter(env, drawPolar2d, canvas, fam, pol, yaw, row[3], key, toys ? grid : (useDb ? null : grid), "room mic", {
          db: db,
          useDb: useDb && !toys,
          note: note,
          fig8: fig8,
          pattern: s["pattern_" + slot]
        });
      });
    }
  function setPolar(data, status) { var env = envStack[envStack.length - 1];
      env.polarField = data || null;
      if (status) env.polarStatus = status;
      else if (data) env.polarStatus = "ok";
      if (env.polarField) paintRingLegend(env.polarField.ring_labels || null);
      var note = document.getElementById("micHaloHint");
      var st = env.getState() || {};
      if (st.mic_setup === "binaural") {
        var head = binauralHeadName(st);
        if (note) note.textContent = "Head: " + head + ". Left and right ears.";
        var badge = document.getElementById("micHonestyBadge");
        if (badge) {
          badge.textContent = "Head: " + head;
          badge.className = "honesty-badge honesty-measured";
        }
      } else if (note && env.polarField && env.polarField.halo_note) {
        note.textContent = env.polarField.halo_note;
      }
      redraw();
      ensureView3d();
      if (env.view3d && env.view3d.setHalo) env.view3d.setHalo(env.polarField, env.planeMode);
    }
  function drawnGrid(which) { var env = envStack[envStack.length - 1];
      var key = String(which || "L").toUpperCase();
      return env.drawnDb[key] || (env.polarField && env.polarField.each_db && env.polarField.each_db[key]) || null;
    }
  function probe() { var env = envStack[envStack.length - 1];
      var geo = geoOf();
      if (env.planeMode === "side") env.sideLay = sideFrame(geo);
      else env.topLay = topFrame(geo);
      var lay = env.planeMode === "side" ? env.sideLay : env.topLay;
      function one(cap) {
        var v = viewMic(geo, cap);
        var p = env.planeMode === "side"
          ? sideToPx(alongOf(v.x, v.z, geo), v.y, lay)
          : topToPx(v.x, v.z, lay);
        var r = env.topCanvas.getBoundingClientRect();
        var sx = env.topCanvas.width > 0 ? r.width / env.topCanvas.width : 1;
        var sy = env.topCanvas.height > 0 ? r.height / env.topCanvas.height : 1;
        return {
          x: v.x, y: v.y, z: v.z, room: !!v.room,
          px: p.px, py: p.py,
          cssX: r.left + p.px * sx,
          cssY: r.top + p.py * sy
        };
      }
      var st = geo.state || {};
      var cHit = env.planeMode === "side" ? hitSide(one("c").px, one("c").py, geo) : hitTop(one("c").px, one("c").py, geo);
      return {
        plane: env.planeMode,
        l: one("l"), c: one("c"), r: one("r"),
        cHit: cHit,
        hint: (document.getElementById("micPlaneHint") || {}).textContent || "",
        metres: (document.getElementById("liveMetresMic") || {}).textContent || "",
        stand: {
          space: st.space, centre_dz: st.centre_dz || 0,
          mcx: st.mcx, mcz: st.mcz, my: st.my, my_c: st.my_c,
          third_mic: st.third_mic, place_c: st.place_c, place_l: st.place_l,
          room_c_x: st.room_c_x, room_c_y: st.room_c_y, room_c_z: st.room_c_z,
          room_l_x: st.room_l_x
        }
      };
    }

  global.MicDesk = {
    create: create,
    drawPolarChartFrame: drawPolarChartFrame
  };
})(window);
