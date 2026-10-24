/* Floor outline for the room plan. Polygons match engine/poly_room.py.
   Box is the shoebox rectangle. Browser: window.RoomShape. Node: module.exports. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.RoomShape = api;
})(typeof window !== "undefined" ? window : (typeof self !== "undefined" ? self : this), function () {
  "use strict";

  var EPS = 1e-4;
  var PAIR_EPS = 1e-6;

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  function tan6() {
    return Math.tan(6 * Math.PI / 180);
  }

  function normalize(raw) {
    var key = String(raw == null ? "" : raw).trim().toLowerCase().replace(/[^a-z0-9]/g, "");
    if (
      key === "splay" || key === "splayed" || key === "rfz" || key === "control" ||
      key === "splayedcontrol" || key === "splayedcontrolroom"
    ) return "splay";
    if (key === "lede" || key === "ledestyle") return "lede";
    if (
      key === "live" || key === "nonparallel" || key === "nonparallellive" ||
      key === "nonparallelliveroom"
    ) return "live";
    if (key === "gable" || key === "gableroof") return "gable";
    if (key === "hex" || key === "hexagon") return "hex";
    return "box";
  }

  function floorOutline(shape, W, L) {
    W = Number(W);
    L = Number(L);
    var name = normalize(shape);
    if (name === "splay") return [[W / 6, 0], [5 * W / 6, 0], [W, L], [0, L]];
    if (name === "lede") {
      var z1 = (2 / 7) * L;
      return [[0.25 * W, 0], [0.75 * W, 0], [W, z1], [W, L], [0, L], [0, z1]];
    }
    if (name === "live") {
      var inset = Math.min(0.25 * W, L * tan6());
      return [[inset, 0], [W - inset, 0], [W, L], [0, L]];
    }
    /* Front and back are flat, width W/2, centred. The other walls meet the sides at mid-length. */
    if (name === "hex") {
      return [
        [W / 4, 0],
        [3 * W / 4, 0],
        [W, L / 2],
        [3 * W / 4, L],
        [W / 4, L],
        [0, L / 2]
      ];
    }
    /* Gable floor is the shoebox. The ridge is a plan guide, not an extra wall. */
    return [[0, 0], [W, 0], [W, L], [0, L]];
  }

  /* Ridge along the length at x = W/2. Eaves sit at 0.75*H. */
  function roofHeight(x, W, H) {
    W = Number(W);
    H = Number(H);
    var eave = 0.75 * H;
    var half = 0.5 * W;
    if (!(half > 0)) return H;
    var t = 1 - Math.abs(Number(x) - half) / half;
    if (t < 0) t = 0;
    if (t > 1) t = 1;
    return eave + (H - eave) * t;
  }

  function planGuides(shape, W, L) {
    if (normalize(shape) !== "gable") return [];
    W = Number(W);
    L = Number(L);
    return [[[W * 0.5, 0], [W * 0.5, L]]];
  }

  function elevGuides(shape, H, L) {
    if (normalize(shape) !== "gable") return [];
    var eave = 0.75 * Number(H);
    return [[[0, eave], [Number(L), eave]]];
  }

  function ceilingAt(shape, z, H, L) {
    H = Number(H);
    L = Number(L);
    var name = normalize(shape);
    var t = !(L > 0) ? 0 : Number(z) / L;
    if (name === "splay") return H * (0.8125 + 0.1875 * t);
    if (name === "live") {
      var insetY = Math.min(0.45 * H, L * tan6());
      return (H - insetY) + insetY * t;
    }
    return H;
  }

  function xSpan(shape, z, W, L) {
    var pts = floorOutline(shape, W, L);
    var xs = [];
    var n = pts.length;
    var i;
    for (i = 0; i < n; i++) {
      var a = pts[i];
      var b = pts[(i + 1) % n];
      var z1 = a[1];
      var z2 = b[1];
      if (Math.abs(z1 - z2) <= 1e-12) {
        if (Math.abs(z - z1) <= 1e-8) xs.push(a[0], b[0]);
        continue;
      }
      var u = (z - z1) / (z2 - z1);
      if (u >= -1e-9 && u <= 1 + 1e-9) xs.push(a[0] + u * (b[0] - a[0]));
    }
    if (!xs.length) return { lo: 0, hi: W };
    var lo = xs[0];
    var hi = xs[0];
    for (i = 1; i < xs.length; i++) {
      if (xs[i] < lo) lo = xs[i];
      if (xs[i] > hi) hi = xs[i];
    }
    return { lo: lo, hi: hi };
  }

  /* Same mapping as room_editor toPx: +X right, +Z toward the top of the plan. */
  function floorPx(shape, W, L, lay) {
    var scale = lay.scale;
    var len = lay.L != null ? lay.L : L;
    return floorOutline(shape, W, L).map(function (p) {
      return { px: lay.ox + p[0] * scale, py: lay.oy + (len - p[1]) * scale };
    });
  }

  function planGuidesPx(shape, W, L, lay) {
    var scale = lay.scale;
    var len = lay.L != null ? lay.L : L;
    return planGuides(shape, W, L).map(function (seg) {
      return seg.map(function (p) {
        return { px: lay.ox + p[0] * scale, py: lay.oy + (len - p[1]) * scale };
      });
    });
  }

  function elevOutline(shape, H, L) {
    L = Number(L);
    H = Number(H);
    var name = normalize(shape);
    /* Side view looks along X. Gable and hex fill the length. Hex's ceiling is flat. */
    if (name === "box" || name === "gable" || name === "hex") return [[0, 0], [L, 0], [L, H], [0, H]];
    return [
      [0, 0],
      [L, 0],
      [L, ceilingAt(name, L, H, L)],
      [0, ceilingAt(name, 0, H, L)]
    ];
  }

  function elevPx(shape, H, L, lay) {
    var scale = lay.scale;
    var Hh = lay.H != null ? lay.H : H;
    return elevOutline(shape, H, L).map(function (p) {
      return { px: lay.ox + p[0] * scale, py: lay.oy + (Hh - p[1]) * scale };
    });
  }

  function elevGuidesPx(shape, H, L, lay) {
    var scale = lay.scale;
    var Hh = lay.H != null ? lay.H : H;
    return elevGuides(shape, H, L).map(function (seg) {
      return seg.map(function (p) {
        return { px: lay.ox + p[0] * scale, py: lay.oy + (Hh - p[1]) * scale };
      });
    });
  }

  /* Closed polygon, inset so a dragged point is inside the outline. */
  function clampInside(x, y, z, W, H, L, shape) {
    if (shape == null) shape = "splay";
    W = Number(W);
    H = Number(H);
    L = Number(L);
    var zLo = Math.min(EPS, L * 0.5);
    var zHi = Math.max(zLo, L - EPS);
    z = clamp(Number(z), zLo, zHi);
    var lim = xSpan(shape, z, W, L);
    var span = lim.hi - lim.lo;
    if (span <= 2 * EPS) x = (lim.lo + lim.hi) * 0.5;
    else x = clamp(Number(x), lim.lo + EPS, lim.hi - EPS);
    var yTop = normalize(shape) === "gable" ? roofHeight(x, W, H) : ceilingAt(shape, z, H, L);
    var yHi = Math.max(EPS, yTop - EPS);
    y = clamp(Number(y), 0, yHi);
    return { x: x, y: y, z: z };
  }

  function maxSpace(mcx, mcz, W, L, shape) {
    if (shape == null) shape = "splay";
    W = Number(W);
    L = Number(L);
    var lim = xSpan(shape, clamp(Number(mcz), 0, L), W, L);
    return Math.max(0, 2 * Math.min(Number(mcx) - lim.lo, lim.hi - Number(mcx)));
  }

  function near(a, b) {
    return Math.abs(a[0] - b[0]) <= PAIR_EPS && Math.abs(a[1] - b[1]) <= PAIR_EPS;
  }

  function edgeRole(pts, i, W, L) {
    var n = pts.length;
    var a = pts[i];
    var b = pts[(i + 1) % n];
    var mx = (a[0] + b[0]) * 0.5;
    var mz = (a[1] + b[1]) * 0.5;
    var ma = [W - b[0], b[1]];
    var mb = [W - a[0], a[1]];
    var pair = -1;
    var j;
    for (j = 0; j < n; j++) {
      var p = pts[j];
      var q = pts[(j + 1) % n];
      if (near(p, ma) && near(q, mb)) {
        pair = j;
        break;
      }
    }
    var self = pair === i;
    var dx = Math.abs(b[0] - a[0]);
    var dz = Math.abs(b[1] - a[1]);
    var facing = (dx > 1e-6 && dz > 1e-6) ? "angled" : (dx <= 1e-6 ? "\u2212X / +X" : (mz <= L * 0.5 ? "\u2212Z" : "+Z"));
    var letter = self ? (mz <= L * 0.5 ? "D" : "B") : (mx >= W * 0.5 ? "C" : "A");
    return { pair: pair, self: self, letter: letter, mz: mz, facing: facing };
  }

  function lrSymmetric(shape, W, L) {
    var name = normalize(shape);
    if (name === "box") return true;
    W = W == null ? 6 : Number(W);
    L = L == null ? 8 : Number(L);
    var pts = floorOutline(name, W, L);
    var i;
    for (i = 0; i < pts.length; i++) {
      var want = [W - pts[i][0], pts[i][1]];
      var hit = false;
      var j;
      for (j = 0; j < pts.length; j++) {
        if (near(pts[j], want)) hit = true;
      }
      if (!hit) return false;
      var role = edgeRole(pts, i, W, L);
      if (!role.self && role.pair < 0) return false;
    }
    return true;
  }

  function labelFor(letter) {
    if (letter === "A") return "Left";
    if (letter === "C") return "Right";
    if (letter === "B") return "Front";
    return "Back";
  }

  function polyRows(shape) {
    var W = 6;
    var L = 8;
    var pts = floorOutline(shape, W, L);
    var roles = [];
    var i;
    for (i = 0; i < pts.length; i++) roles.push(edgeRole(pts, i, W, L));
    var used = {};
    var sides = [];
    var front = null;
    var back = null;
    var loose = [];
    for (i = 0; i < roles.length; i++) {
      if (used[i]) continue;
      var role = roles[i];
      if (role.self) {
        used[i] = true;
        var span = {
          letters: [role.letter],
          shared: false,
          label: labelFor(role.letter),
          facing: role.letter === "B" ? "+Z" : "\u2212Z",
          mz: role.mz
        };
        if (role.letter === "B") front = span;
        else if (role.letter === "D") back = span;
        else loose.push(span);
        continue;
      }
      if (role.pair >= 0 && role.pair !== i) {
        used[i] = true;
        used[role.pair] = true;
        var other = roles[role.pair];
        var face = role.letter === "C" ? role.facing : other.facing;
        sides.push({
          letters: ["A", "C"],
          shared: true,
          label: "Left + Right (mirrored)",
          facing: face,
          mz: Math.min(role.mz, other.mz)
        });
        continue;
      }
      used[i] = true;
      loose.push({
        id: "wall" + i,
        letters: [role.letter],
        shared: false,
        label: labelFor(role.letter),
        facing: role.facing,
        mz: role.mz
      });
    }
    sides.sort(function (a, b) { return a.mz - b.mz; });
    var rows = [];
    for (i = 0; i < sides.length; i++) {
      sides[i].id = i === 0 ? "sides" : "sides" + (i + 1);
      rows.push(sides[i]);
    }
    loose.sort(function (a, b) { return a.mz - b.mz; });
    for (i = 0; i < loose.length; i++) {
      if (!loose[i].id) loose[i].id = "wall" + i;
      rows.push(loose[i]);
    }
    if (front) {
      front.id = "front";
      rows.push(front);
    }
    if (back) {
      back.id = "back";
      rows.push(back);
    }
    rows.push({ id: "floor", letters: ["E"], shared: false, label: "Floor", facing: "\u2212Y" });
    rows.push({ id: "ceiling", letters: ["F"], shared: false, label: "Ceiling", facing: "+Y" });
    return rows;
  }

  /* Symmetric polygons stay one linked pair and have no switch. Box links only while Mirror L/R is on. */
  function showMirrorToggle(shape) {
    return normalize(shape) === "box";
  }

  function sidesLinked(shape, mirror) {
    var name = normalize(shape);
    if (name !== "box") return lrSymmetric(name);
    return !!mirror;
  }

  function gableRows() {
    return [
      { id: "sides", letters: ["A", "C"], shared: true, label: "Left + Right (mirrored)", facing: "\u2212X / +X" },
      { id: "gable0", letters: ["D"], shared: false, label: "Gable end", facing: "\u2212Z" },
      { id: "gable2", letters: ["B"], shared: false, label: "Gable end", facing: "+Z" },
      { id: "floor", letters: ["E"], shared: false, label: "Floor", facing: "\u2212Y" },
      { id: "roofL", letters: ["F"], shared: false, label: "Left roof", facing: "+Y" },
      { id: "roofR", letters: ["F"], shared: false, label: "Right roof", facing: "+Y" }
    ];
  }

  function wallRows(shape, mirror) {
    var name = normalize(shape);
    if (name === "gable") return gableRows();
    if (name !== "box") return polyRows(name);
    var shared = !!mirror;
    var rows = [];
    if (shared) {
      rows.push({
        id: "sides",
        letters: ["A", "C"],
        shared: true,
        label: "Left + Right (mirrored)",
        facing: "\u2212X / +X"
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
    planGuides: planGuides,
    planGuidesPx: planGuidesPx,
    elevOutline: elevOutline,
    elevPx: elevPx,
    elevGuides: elevGuides,
    elevGuidesPx: elevGuidesPx,
    roofHeight: roofHeight,
    ceilingAt: ceilingAt,
    clampInside: clampInside,
    maxSpace: maxSpace,
    lrSymmetric: lrSymmetric,
    showMirrorToggle: showMirrorToggle,
    sidesLinked: sidesLinked,
    wallRows: wallRows
  };
});
