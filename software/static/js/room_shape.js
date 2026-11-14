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

  function prefixKind(raw) {
    var text = String(raw == null ? "" : raw).trim().toLowerCase();
    if (text.indexOf("tilt:") === 0) return tiltKind(text);
    if (text.indexOf("plan:") === 0) return planKind(text);
    return "";
  }

  function tiltPair(raw) {
    var text = String(raw == null ? "" : raw).trim().toLowerCase();
    if (text.indexOf("tilt:") !== 0) return null;
    var bits = text.split(":");
    var deg = bits.length > 1 && bits[1] !== "" ? Number(bits[1]) : 0;
    var slope = bits.length > 2 && bits[2] !== "" ? Number(bits[2]) : 0;
    if (!isFinite(deg) || !isFinite(slope)) return null;
    if (Math.abs(deg) <= 1e-6 && Math.abs(slope) <= 1e-6) return null;
    if (deg < -20) deg = -20;
    if (deg > 20) deg = 20;
    if (slope < -0.45) slope = -0.45;
    if (slope > 0.45) slope = 0.45;
    return { deg: deg, slope: slope };
  }

  function tiltKind(text) {
    return tiltPair(text) ? "tilt" : "box";
  }

  function convex(pts) {
    var n = pts.length;
    var sign = 0;
    var i;
    if (n < 3) return false;
    for (i = 0; i < n; i++) {
      var a = pts[i];
      var b = pts[(i + 1) % n];
      var c = pts[(i + 2) % n];
      var cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]);
      if (Math.abs(cross) <= 1e-8) continue;
      var s = cross > 0 ? 1 : -1;
      if (sign === 0) sign = s;
      else if (s !== sign) return false;
    }
    return sign !== 0;
  }

  function planPoints(raw) {
    var text = String(raw == null ? "" : raw).trim().toLowerCase();
    var nums;
    var pts;
    var i;
    if (text.indexOf("plan:") !== 0) return null;
    nums = text.slice(5).split(",");
    if (nums.length < 10 || nums.length > 16 || nums.length % 2) return null;
    pts = [];
    for (i = 0; i < nums.length; i += 2) {
      var x = Number(nums[i]);
      var z = Number(nums[i + 1]);
      if (!isFinite(x) || !isFinite(z)) return null;
      pts.push([x, z]);
    }
    if (pts.length < 5 || pts.length > 8 || !convex(pts)) return null;
    return pts;
  }

  function planKind(text) {
    return planPoints(text) ? "plan" : "box";
  }

  function encodePlan(pts) {
    return "plan:" + pts.map(function (p) {
      return Number(p[0]).toFixed(2) + "," + Number(p[1]).toFixed(2);
    }).join(",");
  }

  function encodeTilt(deg, slope) {
    deg = Number(deg) || 0;
    slope = Number(slope) || 0;
    if (Math.abs(deg) <= 1e-6 && Math.abs(slope) <= 1e-6) return "box";
    return "tilt:" + deg.toFixed(2) + ":" + slope.toFixed(3);
  }

  function nextStep(cur, steps) {
    var i;
    var best = 0;
    var bestD = 1e9;
    for (i = 0; i < steps.length; i++) {
      var d = Math.abs(Number(cur) - steps[i]);
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    }
    return steps[(best + 1) % steps.length];
  }

  function cycleTilt(current) {
    var pair = tiltPair(current) || { deg: 0, slope: 0 };
    return encodeTilt(nextStep(pair.deg, [0, 4, 8, 12]), pair.slope);
  }

  function cycleSlope(current) {
    var pair = tiltPair(current) || { deg: 0, slope: 0 };
    return encodeTilt(pair.deg, nextStep(pair.slope, [0, 0.1, 0.2]));
  }

  function tiltLabel(shape) {
    var pair = tiltPair(shape);
    if (!pair || Math.abs(pair.deg) <= 1e-6) return "Walls flat";
    return "Walls " + String(Math.round(pair.deg)) + "\u00b0";
  }

  function slopeLabel(shape) {
    var pair = tiltPair(shape);
    if (!pair || Math.abs(pair.slope) <= 1e-6) return "Ceiling flat";
    return "Ceiling " + String(Math.round(pair.slope * 100)) + "%";
  }

  /* LIKELY published points, not a measured room. Height is the 1.
     Bolt area 1:1.25:1.6, Sepmeyer 1:1.28:1.54, Louden 1:1.4:1.9. */
  function ratioSize(name, W, H, L) {
    var table = {
      bolt: [1.25, 1, 1.6],
      sepmeyer: [1.28, 1, 1.54],
      louden: [1.4, 1, 1.9]
    };
    var r = table[String(name || "").trim().toLowerCase()];
    var V;
    var s;
    if (!r) return null;
    V = Number(W) * Number(H) * Number(L);
    if (!(V > 0)) V = 144;
    s = Math.pow(V / (r[0] * r[1] * r[2]), 1 / 3);
    function step(v, st, lo, hi) {
      var n = Math.round(v / st) * st;
      if (n < lo) n = lo;
      if (n > hi) n = hi;
      return Math.round(n * 1000) / 1000;
    }
    return {
      W: step(r[0] * s, 0.1, 1, 80),
      H: step(r[1] * s, 0.1, 1, 40),
      L: step(r[2] * s, 0.5, 2, 120)
    };
  }

  function axialModes(W, H, L, c) {
    var speed = Number(c) > 0 ? Number(c) : 340;
    function axis(dim) {
      var out = [];
      var n;
      dim = Number(dim);
      for (n = 1; n <= 3; n++) out.push(n * speed / (2 * dim));
      return out;
    }
    return { W: axis(W), H: axis(H), L: axis(L), c: speed };
  }

  function axialText(W, H, L) {
    var m = axialModes(W, H, L, 340);
    function join(row) {
      return row.map(function (hz) { return hz.toFixed(1); }).join(" ");
    }
    return "Axial " + join(m.W) + " Hz across \u00b7 " + join(m.H) + " Hz up \u00b7 " + join(m.L) + " Hz along (340 m/s)";
  }

  function regularPlan(n, W, L) {
    var count = n | 0;
    var cx;
    var cz;
    var rx;
    var rz;
    var pts = [];
    var i;
    if (count < 5) count = 5;
    if (count > 8) count = 8;
    W = Number(W);
    L = Number(L);
    cx = W * 0.5;
    cz = L * 0.5;
    rx = W * 0.42;
    rz = L * 0.42;
    for (i = 0; i < count; i++) {
      var a = -Math.PI / 2 + i * 2 * Math.PI / count;
      pts.push([cx + rx * Math.cos(a), cz + rz * Math.sin(a)]);
    }
    return pts;
  }

  function storedShape(picked, W, H, L, current) {
    var raw = String(picked == null ? "" : picked).trim().toLowerCase();
    if (raw === "plan") {
      if (normalize(current) === "plan") return String(current);
      return encodePlan(regularPlan(6, W, L));
    }
    return normalize(picked);
  }

  function movePlanPoint(token, index, x, z, W, L) {
    var pts = planPoints(token);
    var next;
    var i;
    if (!pts) return String(token || "box");
    index = index | 0;
    if (index < 0 || index >= pts.length) return String(token);
    x = Math.max(0, Math.min(Number(W), Number(x)));
    z = Math.max(0, Math.min(Number(L), Number(z)));
    next = [];
    for (i = 0; i < pts.length; i++) next.push(pts[i].slice());
    next[index] = [x, z];
    if (!convex(next)) return String(token);
    return encodePlan(next);
  }

  function addPlanCorner(token) {
    var pts = planPoints(token);
    var best = 0;
    var bestLen = -1;
    var i;
    var mid;
    var next;
    if (!pts || pts.length >= 8) return String(token || "box");
    for (i = 0; i < pts.length; i++) {
      var a = pts[i];
      var b = pts[(i + 1) % pts.length];
      var len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len > bestLen) {
        bestLen = len;
        best = i;
      }
    }
    mid = [
      (pts[best][0] + pts[(best + 1) % pts.length][0]) * 0.5,
      (pts[best][1] + pts[(best + 1) % pts.length][1]) * 0.5
    ];
    next = pts.slice(0, best + 1).concat([mid], pts.slice(best + 1));
    if (!convex(next)) return String(token);
    return encodePlan(next);
  }

  function delPlanCorner(token) {
    var pts = planPoints(token);
    var best = 0;
    var bestLen = 1e9;
    var i;
    if (!pts || pts.length <= 5) return String(token || "box");
    for (i = 0; i < pts.length; i++) {
      var a = pts[(i + pts.length - 1) % pts.length];
      var b = pts[(i + 1) % pts.length];
      var len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < bestLen) {
        bestLen = len;
        best = i;
      }
    }
    pts = pts.slice();
    pts.splice(best, 1);
    if (!convex(pts)) return String(token);
    return encodePlan(pts);
  }

  function hitPlan(px, py, state, lay) {
    var pts;
    var best = -1;
    var bestD = 12;
    var i;
    if (!state || normalize(state.room_shape) !== "plan" || !lay) return null;
    pts = floorPx(state.room_shape, state.W, state.L, lay);
    for (i = 0; i < pts.length; i++) {
      var d = Math.hypot(px - pts[i].px, py - pts[i].py);
      if (d <= bestD) {
        bestD = d;
        best = i;
      }
    }
    return best < 0 ? null : { index: best };
  }

  function panelRow(kind) {
    var name = String(kind || "").trim().toLowerCase();
    if (name === "diffuser") {
      return {
        face: "A", type: "porous", material: "absorber_panel_2in_gap2in",
        coverage: 0.2, on: true, build: "Diffuser"
      };
    }
    if (name === "trap" || name === "bass") {
      return {
        face: "D", type: "membrane", f0: 80, q: 2, amax: 0.6,
        coverage: 0.15, on: true, build: "Bass trap"
      };
    }
    if (name === "cloud") {
      return {
        face: "F", type: "porous", material: "absorber_panel_4in_gap4in",
        coverage: 0.25, on: true, build: "Cloud"
      };
    }
    return null;
  }

  function normalize(raw) {
    var kind = prefixKind(raw);
    if (kind) return kind;
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
    var plan = planPoints(shape);
    var tilt = tiltPair(shape);
    if (plan) return plan.map(function (p) { return [p[0], p[1]]; });
    if (tilt && Math.abs(tilt.deg) > 1e-6) {
      var inset = Math.min(0.4 * W, Math.abs(L * Math.tan(tilt.deg * Math.PI / 180)));
      return [[inset, 0], [W - inset, 0], [W, L], [0, L]];
    }
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
    var tilt = tiltPair(shape);
    if (tilt) {
      var u = !(L > 0) ? 0 : Number(z) / L;
      return H * (1 - tilt.slope * (1 - u));
    }
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
      [L, ceilingAt(shape, L, H, L)],
      [0, ceilingAt(shape, 0, H, L)]
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

  /* Enlarged floor field. Six first-order shoebox images. Null on any other outline. */
  function heatMapNote(shape) {
    if (normalize(shape) !== "box") return null;
    return "First-order shoebox images, geometric 1/r, no absorption, no air, no tail";
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

  /* One card per polygon face. Walls follow the floor edge, then floor, then ceiling.
     Gable keeps the two roofs apart. The shoebox stays on A–F. */
  function faceRows(shape) {
    var name = normalize(shape);
    if (name === "box") return null;
    if (name === "gable") {
      return [
        { id: "wall0", letters: ["F1"], shared: false, label: "Wall 1", facing: "\u2212Z" },
        { id: "wall1", letters: ["F2"], shared: false, label: "Wall 2", facing: "+X" },
        { id: "wall2", letters: ["F3"], shared: false, label: "Wall 3", facing: "+Z" },
        { id: "wall3", letters: ["F4"], shared: false, label: "Wall 4", facing: "\u2212X" },
        { id: "floor", letters: ["F5"], shared: false, label: "Floor", facing: "\u2212Y" },
        { id: "roofL", letters: ["F6"], shared: false, label: "Left roof", facing: "+Y" },
        { id: "roofR", letters: ["F7"], shared: false, label: "Right roof", facing: "+Y" }
      ];
    }
    var pts = floorOutline(shape, 6, 8);
    var rows = [];
    var i;
    for (i = 0; i < pts.length; i++) {
      rows.push({
        id: "wall" + i,
        letters: ["F" + (i + 1)],
        shared: false,
        label: "Wall " + (i + 1),
        facing: "edge " + (i + 1)
      });
    }
    var n = pts.length;
    rows.push({ id: "floor", letters: ["F" + (n + 1)], shared: false, label: "Floor", facing: "\u2212Y" });
    rows.push({ id: "ceiling", letters: ["F" + (n + 2)], shared: false, label: "Ceiling", facing: "+Y" });
    return rows;
  }

  function wallRows(shape, mirror) {
    var name = normalize(shape);
    if (name !== "box") {
      var faces = faceRows(shape);
      if (faces) return faces;
    }
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

  function liveRows(rows) {
    var out = [];
    var i;
    for (i = 0; i < rows.length; i++) if (rows[i]) out.push(rows[i]);
    return out;
  }

  function paintShapeRows(rows, shape) {
    var name = normalize(shape);
    var list = liveRows(rows);
    var r, buttons, b, on;
    for (r = 0; r < list.length; r++) {
      buttons = list[r].querySelectorAll("[data-room-shape]");
      for (b = 0; b < buttons.length; b++) {
        on = buttons[b].getAttribute("data-room-shape") === name;
        if (buttons[b].classList) buttons[b].classList.toggle("active", on);
        buttons[b].setAttribute("aria-pressed", on ? "true" : "false");
      }
    }
  }

  function bindShapeRows(rows, onPick) {
    var list = liveRows(rows);
    var r, buttons, b;
    for (r = 0; r < list.length; r++) {
      buttons = list[r].querySelectorAll("[data-room-shape]");
      for (b = 0; b < buttons.length; b++) {
        (function (btn) {
          btn.addEventListener("click", function () {
            onPick(btn.getAttribute("data-room-shape"));
          });
        })(buttons[b]);
      }
    }
  }

  return {
    normalize: normalize,
    ratioSize: ratioSize,
    axialModes: axialModes,
    axialText: axialText,
    storedShape: storedShape,
    tiltPair: tiltPair,
    tiltLabel: tiltLabel,
    slopeLabel: slopeLabel,
    cycleTilt: cycleTilt,
    cycleSlope: cycleSlope,
    planPoints: planPoints,
    encodePlan: encodePlan,
    encodeTilt: encodeTilt,
    regularPlan: regularPlan,
    movePlanPoint: movePlanPoint,
    addPlanCorner: addPlanCorner,
    delPlanCorner: delPlanCorner,
    hitPlan: hitPlan,
    panelRow: panelRow,
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
    heatMapNote: heatMapNote,
    sidesLinked: sidesLinked,
    wallRows: wallRows,
    paintShapeRows: paintShapeRows,
    bindShapeRows: bindShapeRows
  };
});
