/* drag_model.js — T7/T8 prebuild: wall / corner / ceiling drag and mic drag on the Room plans.
   Pure maths, no DOM: room_editor.js calls it from its pointer handlers.
   Coordinates are room_editor.js's (lines 158-169): floor px = ox + x*s, py = oy + (L - z)*s
   (x = width, 0 left; z = length, 0 = Back at the bottom); elevation px = ox + z*s, py = oy + (H - y)*s.
   Browser: window.RRDrag; node: module.exports. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RRDrag = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var LIMITS = { W: [1, 80], L: [2, 120], H: [1, 40] };   /* index.html 538-540 slider ranges */
  var MARGIN = 0.10;   /* metres an object keeps from a wall while a wall is dragged */
  var CAPS = ["l", "c", "r"];

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function snapTo(v, q) { return q > 0 ? Math.round(v / q) * q : v; }
  function round(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }

  /* ---- what is on the floor: everything that has an x/z and must stay inside ---- */
  function floorObjects(s) {
    var o = [], half = Math.max(0, Number(s.space) || 0) / 2;
    o.push({ id: "source", x: s.sx, z: s.sz });
    if (s.two_sources) o.push({ id: "sourceB", x: s.sx_b, z: s.sz_b });
    o.push({ id: "stand", x: s.mcx - half, z: s.mcz });
    o.push({ id: "stand", x: s.mcx + half, z: s.mcz });
    CAPS.forEach(function (c) {
      if (s["place_" + c] === "room") {
        var rx = s["room_" + c + "_x"], rz = s["room_" + c + "_z"];
        if (rx == null) { rx = s.room_x; rz = s.room_z; }   /* T7 migration default */
        if (rx != null) o.push({ id: "room_" + c, x: rx, z: rz });
      }
    });
    return o.filter(function (p) { return isFinite(p.x) && isFinite(p.z); });
  }
  function heightObjects(s) {
    var o = [s.my, s.sy];
    if (s.two_sources) o.push(s.sy_b);
    CAPS.forEach(function (c) { if (s["place_" + c] === "room") o.push(s["room_" + c + "_y"] != null ? s["room_" + c + "_y"] : s.room_y); });
    return o.filter(function (v) { return isFinite(v); });
  }

  /* ---- hit tests (pixels; call only after the object hit-test missed) ---- */
  function hitWall(px, py, lay, band, corner) {
    band = band == null ? 8 : band; corner = corner == null ? 12 : corner;
    var x0 = lay.ox, x1 = lay.ox + lay.W * lay.scale, y0 = lay.oy, y1 = lay.oy + lay.L * lay.scale;
    if (px < x0 - band || px > x1 + band || py < y0 - band || py > y1 + band) return null;
    var dx0 = Math.abs(px - x0), dx1 = Math.abs(px - x1), dy0 = Math.abs(py - y0), dy1 = Math.abs(py - y1);
    var vx = dx0 <= dx1 ? { w: "x0", d: dx0 } : { w: "x1", d: dx1 };
    var vz = dy0 <= dy1 ? { w: "z1", d: dy0 } : { w: "z0", d: dy1 };   /* top of page = Front = z = L */
    if (vx.d <= corner && vz.d <= corner) return { kind: "corner", walls: [vx.w, vz.w] };
    if (vx.d <= band && vx.d <= vz.d) return { kind: "wall", walls: [vx.w] };
    if (vz.d <= band) return { kind: "wall", walls: [vz.w] };
    return null;
  }
  function hitCeiling(px, py, elay, band) {
    band = band == null ? 8 : band;
    var x0 = elay.ox, x1 = elay.ox + elay.L * elay.scale, y = elay.oy;
    if (px < x0 - band || px > x1 + band) return null;
    return Math.abs(py - y) <= band ? { kind: "ceiling", walls: ["y1"] } : null;
  }
  function cursorFor(hit) {
    if (!hit) return "";
    if (hit.kind === "ceiling") return "ns-resize";
    if (hit.kind === "corner") return (hit.walls[0] === "x1") === (hit.walls[1] === "z1") ? "nesw-resize" : "nwse-resize";
    return hit.walls[0].charAt(0) === "x" ? "ew-resize" : "ns-resize";
  }

  /* ---- wall drag: the opposite wall and every object stay where they are on screen ---- */
  /* px0/py0 (optional) = pointer-down point; with them the wall keeps the grab offset (no jump). */
  function beginWallDrag(state, hit, lay, px0, py0) {
    return { hit: hit, lay: { ox: lay.ox, oy: lay.oy, scale: lay.scale, W: lay.W, L: lay.L, H: lay.H },
             s0: JSON.parse(JSON.stringify(state)), p0: px0 == null ? null : { x: px0, y: py0 } };
  }
  function grabbed(ctx, px, py, wall) {
    /* pointer position in metres along the axis of `wall`, corrected for the grab offset */
    var l = ctx.lay, s0 = ctx.s0;
    if (!ctx.p0) return wall.charAt(0) === "x" ? (px - l.ox) / l.scale : (wall.charAt(0) === "z" ? l.L - (py - l.oy) / l.scale : l.H - (py - l.oy) / l.scale);
    var dx = (px - ctx.p0.x) / l.scale, dy = (py - ctx.p0.y) / l.scale;
    if (wall === "x1") return s0.W + dx;
    if (wall === "x0") return dx;
    if (wall === "z1") return s0.L - dy;
    if (wall === "z0") return -dy;
    return s0.H - dy;   /* y1 ceiling */
  }
  /* opts: {shift: bool (0.1 m snap, else 0.01), mode: "stop" (wall stops at objects, default) | "push"} */
  function wallDragTo(ctx, px, py, opts) {
    opts = opts || {};
    var s0 = ctx.s0, lay = ctx.lay, q = opts.shift ? 0.1 : 0.01, mode = opts.mode || "stop";
    var mx, mz;   /* frozen layout */
    var objs = floorObjects(s0);
    var minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
    objs.forEach(function (p) { minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x); minZ = Math.min(minZ, p.z); maxZ = Math.max(maxZ, p.z); });
    var patch = { W: s0.W, L: s0.L }, dx = 0, dz = 0, held = false;
    ctx.hit.walls.forEach(function (w) {
      if (w.charAt(0) === "x") mx = grabbed(ctx, px, py, w); else mz = grabbed(ctx, px, py, w);
      if (w === "x1") {
        var lo = Math.max(LIMITS.W[0], mode === "stop" ? maxX + MARGIN : LIMITS.W[0]);
        var W = clamp(snapTo(mx, q), lo, LIMITS.W[1]); held = held || W !== snapTo(mx, q); patch.W = W;
      } else if (w === "x0") {
        var hi = mode === "stop" ? minX - MARGIN : s0.W - LIMITS.W[0];
        var d = clamp(snapTo(mx, q), s0.W - LIMITS.W[1], Math.min(hi, s0.W - LIMITS.W[0]));
        held = held || d !== snapTo(mx, q); dx = d; patch.W = round(s0.W - d, 4);
      } else if (w === "z1") {
        var loz = Math.max(LIMITS.L[0], mode === "stop" ? maxZ + MARGIN : LIMITS.L[0]);
        var L = clamp(snapTo(mz, q), loz, LIMITS.L[1]); held = held || L !== snapTo(mz, q); patch.L = L;
      } else if (w === "z0") {
        var hiz = mode === "stop" ? minZ - MARGIN : s0.L - LIMITS.L[0];
        var dzz = clamp(snapTo(mz, q), s0.L - LIMITS.L[1], Math.min(hiz, s0.L - LIMITS.L[0]));
        held = held || dzz !== snapTo(mz, q); dz = dzz; patch.L = round(s0.L - dzz, 4);
      }
    });
    /* shift every x/z field when the origin wall moved (objects stay put on screen) */
    if (dx || dz) {
      ["sx", "sx_b", "mcx", "room_x"].concat(CAPS.map(function (c) { return "room_" + c + "_x"; })).forEach(function (k) {
        if (s0[k] != null && isFinite(s0[k])) patch[k] = round(s0[k] - dx, 4);
      });
      ["sz", "sz_b", "mcz", "room_z"].concat(CAPS.map(function (c) { return "room_" + c + "_z"; })).forEach(function (k) {
        if (s0[k] != null && isFinite(s0[k])) patch[k] = round(s0[k] - dz, 4);
      });
    }
    if (mode === "push") {   /* clamp objects into the new room (RoomMath.clampRoom does the rest) */
      var Wn = patch.W, Ln = patch.L;
      [["sx", Wn], ["sx_b", Wn], ["mcx", Wn]].forEach(function (a) { var v = patch[a[0]] != null ? patch[a[0]] : s0[a[0]]; if (v != null) patch[a[0]] = clamp(v, MARGIN, a[1] - MARGIN); });
      [["sz", Ln], ["sz_b", Ln], ["mcz", Ln]].forEach(function (a) { var v = patch[a[0]] != null ? patch[a[0]] : s0[a[0]]; if (v != null) patch[a[0]] = clamp(v, MARGIN, a[1] - MARGIN); });
    }
    return { patch: patch, held: held, label: label(ctx.hit, patch) };
  }
  function ceilingDragTo(ctx, px, py, elay, opts) {
    opts = opts || {};
    var q = opts.shift ? 0.1 : 0.01, s0 = ctx.s0;
    var y = ctx.p0 ? grabbed(ctx, px, py, "y1") : elay.H - (py - elay.oy) / elay.scale;
    var lo = Math.max(LIMITS.H[0], Math.max.apply(null, heightObjects(s0).concat([0])) + MARGIN);
    var H = clamp(snapTo(y, q), lo, LIMITS.H[1]);
    return { patch: { H: round(H, 4) }, held: H !== snapTo(y, q), label: "Ceiling " + H.toFixed(2) + " m" };
  }
  function label(hit, patch) {
    var parts = [];
    hit.walls.forEach(function (w) {
      if (w.charAt(0) === "x") parts.push("Width " + patch.W.toFixed(2) + " m");
      else if (w.charAt(0) === "z") parts.push("Length " + patch.L.toFixed(2) + " m");
    });
    return parts.join(" \u00b7 ");
  }
  /* Double-click a wall: which field to type into (use RRControls typing). */
  function fieldForWall(hit) {
    if (!hit) return null;
    if (hit.kind === "ceiling") return "H";
    return hit.walls[0].charAt(0) === "x" ? "W" : "L";
  }

  /* ---- mic drag (T8) ----
     mode "mirror": L and R stay symmetric about the stand centre; dragging L or R sets space
                    (= 2|x - mcx|, mic_desk.js 1056-1062) and z moves the stand.
     mode "linked": any array mic drags the whole stand (mcx, mcz).
     mode "split":  R is free: it moves its own room spot (place_r = "room").
     A strip with place = "room" always moves its own spot room_<cap>_x/z. */
  function maxSpace(W, mcx) { return Math.max(0, 2 * Math.min(mcx, W - mcx)); }   /* RoomMath.maxSpace idea */
  function micDragTo(state, cap, x, z, mode) {
    var s = state, W = s.W, L = s.L, p = {};
    x = clamp(x, 0, W); z = clamp(z, 0, L);
    if (s["place_" + cap] === "room" || (mode === "split" && cap === "r")) {
      p["place_" + cap] = "room";
      p["room_" + cap + "_x"] = round(x, 3); p["room_" + cap + "_z"] = round(z, 3);
      return p;
    }
    if (mode === "mirror" && cap !== "c") {
      p.space = round(clamp(2 * Math.abs(x - s.mcx), 0, maxSpace(W, s.mcx)), 4);
      p.mcz = round(z, 3);
      return p;
    }
    /* linked, or the centre mic in mirror: move the stand, keep offsets */
    var off = cap === "c" ? 0 : (cap === "l" ? -1 : 1) * (Number(s.space) || 0) / 2;
    var half = (Number(s.space) || 0) / 2;
    p.mcx = round(clamp(x - off, half, W - half), 3);
    p.mcz = round(z, 3);
    return p;
  }
  /* Where each mic is drawn (array mics from the stand, room mics from their spot). */
  function micPositions(s) {
    var half = (Number(s.space) || 0) / 2, out = {};
    CAPS.forEach(function (c) {
      if (s["place_" + c] === "room") {
        out[c] = { x: s["room_" + c + "_x"] != null ? s["room_" + c + "_x"] : s.room_x,
                   z: s["room_" + c + "_z"] != null ? s["room_" + c + "_z"] : s.room_z, room: true };
      } else {
        out[c] = { x: s.mcx + (c === "l" ? -half : (c === "r" ? half : 0)), z: s.mcz + (c === "c" ? (Number(s.centre_dz) || 0) : 0), room: false };
      }
    });
    return out;
  }
  /* T7 migration: one shared room spot -> one spot per strip (bit-exact: same numbers). */
  function migrateRoomSpots(s) {
    var p = {};
    CAPS.forEach(function (c) {
      ["x", "z", "y", "yaw"].forEach(function (k) {
        var nk = "room_" + c + "_" + k;
        if (s[nk] == null && s["room_" + k] != null) p[nk] = s["room_" + k];
      });
    });
    return p;
  }

  /* Mic drag with grab offset: pass the mic's position at pointer-down and the pointer delta in metres. */
  function micDragBy(state, cap, start, dxm, dzm, mode) { return micDragTo(state, cap, start.x + dxm, start.z + dzm, mode); }

  return { micDragBy: micDragBy, LIMITS: LIMITS, MARGIN: MARGIN, hitWall: hitWall, hitCeiling: hitCeiling, cursorFor: cursorFor,
           beginWallDrag: beginWallDrag, wallDragTo: wallDragTo, ceilingDragTo: ceilingDragTo, fieldForWall: fieldForWall,
           micDragTo: micDragTo, micPositions: micPositions, migrateRoomSpots: migrateRoomSpots, floorObjects: floorObjects };
});
