/* Floor outline for the room plan. Splay matches engine/poly_room.py.
   Box is the shoebox rectangle. Browser: window.RoomShape. Node: module.exports. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.RoomShape = api;
})(typeof window !== "undefined" ? window : (typeof self !== "undefined" ? self : this), function () {
  "use strict";

  var EPS = 1e-4;

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  function normalize(raw) {
    var key = String(raw == null ? "" : raw).trim().toLowerCase().replace(/[^a-z0-9]/g, "");
    if (
      key === "splay" || key === "splayed" || key === "rfz" || key === "control" ||
      key === "splayedcontrol" || key === "splayedcontrolroom"
    ) return "splay";
    return "box";
  }

  function floorOutline(shape, W, L) {
    W = Number(W);
    L = Number(L);
    if (normalize(shape) === "splay") {
      return [[W / 6, 0], [5 * W / 6, 0], [W, L], [0, L]];
    }
    return [[0, 0], [W, 0], [W, L], [0, L]];
  }

  function ceilingAt(shape, z, H, L) {
    H = Number(H);
    L = Number(L);
    if (normalize(shape) !== "splay" || !(L > 0)) return H;
    var t = clamp(Number(z) / L, 0, 1);
    return H * (0.8125 + 0.1875 * t);
  }

  function xLimits(z, W, L) {
    var t = L > 0 ? clamp(z / L, 0, 1) : 0;
    return {
      lo: (W / 6) * (1 - t),
      hi: (5 * W / 6) + (W / 6) * t
    };
  }

  /* Same mapping as room_editor toPx: +X right, +Z toward the top of the plan. */
  function floorPx(shape, W, L, lay) {
    var scale = lay.scale;
    var len = lay.L != null ? lay.L : L;
    return floorOutline(shape, W, L).map(function (p) {
      return { px: lay.ox + p[0] * scale, py: lay.oy + (len - p[1]) * scale };
    });
  }

  function elevOutline(shape, H, L) {
    L = Number(L);
    H = Number(H);
    if (normalize(shape) === "splay") {
      return [
        [0, 0],
        [L, 0],
        [L, ceilingAt("splay", L, H, L)],
        [0, ceilingAt("splay", 0, H, L)]
      ];
    }
    return [[0, 0], [L, 0], [L, H], [0, H]];
  }

  function elevPx(shape, H, L, lay) {
    var scale = lay.scale;
    var Hh = lay.H != null ? lay.H : H;
    return elevOutline(shape, H, L).map(function (p) {
      return { px: lay.ox + p[0] * scale, py: lay.oy + (Hh - p[1]) * scale };
    });
  }

  /* Closed splay, inset so a dragged point is inside the outline. */
  function clampInside(x, y, z, W, H, L) {
    W = Number(W);
    H = Number(H);
    L = Number(L);
    var zLo = Math.min(EPS, L * 0.5);
    var zHi = Math.max(zLo, L - EPS);
    z = clamp(Number(z), zLo, zHi);
    var lim = xLimits(z, W, L);
    var span = lim.hi - lim.lo;
    if (span <= 2 * EPS) x = (lim.lo + lim.hi) * 0.5;
    else x = clamp(Number(x), lim.lo + EPS, lim.hi - EPS);
    var yHi = Math.max(EPS, ceilingAt("splay", z, H, L) - EPS);
    y = clamp(Number(y), 0, yHi);
    return { x: x, y: y, z: z };
  }

  function maxSpace(mcx, mcz, W, L) {
    W = Number(W);
    L = Number(L);
    var lim = xLimits(clamp(Number(mcz), 0, L), W, L);
    return Math.max(0, 2 * Math.min(Number(mcx) - lim.lo, lim.hi - Number(mcx)));
  }

  /* Splay sides are always one pair. Box sides link only while Mirror L/R is on. */
  function showMirrorToggle(shape) {
    return normalize(shape) !== "splay";
  }

  function wallRows(shape, mirror) {
    var splay = normalize(shape) === "splay";
    var shared = splay || !!mirror;
    var rows = [];
    if (shared) {
      rows.push({
        id: "sides",
        letters: ["A", "C"],
        shared: true,
        label: splay ? "Splayed sides" : "Left / Right",
        facing: splay ? "angled" : "\u2212X / +X"
      });
    } else {
      rows.push({ id: "left", letters: ["A"], shared: false, label: "Left", facing: "\u2212X" });
      rows.push({ id: "right", letters: ["C"], shared: false, label: "Right", facing: "+X" });
    }
    rows.push({ id: "front", letters: ["B"], shared: false, label: "Front", facing: "+Z" });
    rows.push({ id: "back", letters: ["D"], shared: false, label: "Back", facing: "\u2212Z" });
    rows.push({ id: "floor", letters: ["E"], shared: false, label: "Floor", facing: "\u2212Y" });
    rows.push({ id: "ceiling", letters: ["F"], shared: false, label: "Ceiling", facing: "+Y" });
    return rows;
  }

  return {
    normalize: normalize,
    floorOutline: floorOutline,
    floorPx: floorPx,
    elevOutline: elevOutline,
    elevPx: elevPx,
    ceilingAt: ceilingAt,
    clampInside: clampInside,
    maxSpace: maxSpace,
    showMirrorToggle: showMirrorToggle,
    wallRows: wallRows
  };
});
