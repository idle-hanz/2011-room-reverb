/* Display geometry for the 3D room and the Space image rooms.
   Box parts are the shoebox meshes the views already drew.
   Splay parts are the prism in engine/poly_room.py (faces_for "splay").
   Browser: window.RoomDraw. Node: module.exports. Display only. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.RoomDraw = api;
})(typeof window !== "undefined" ? window : (typeof self !== "undefined" ? self : this), function () {
  "use strict";

  var EPS = 1e-9;
  var FADE_MS = 15;
  var LETTER_COLOR = {
    A: 0x38bdf8,
    B: 0x2dd4bf,
    C: 0x94a3b8,
    D: 0xcbd5e1,
    E: 0x78716c,
    F: 0xe2e8f0
  };
  var MATERIAL_COLOR = {
    plaster_smooth: 0xe7e1d6,
    gypsum_painted: 0xf4f1ea,
    brick_unglazed: 0xa34b3a,
    concrete_painted: 0xb7b7b2,
    wood_parquet: 0x8b5a2b,
    plywood_panel: 0xc4a574,
    carpet_on_concrete: 0x6b4f3a,
    carpet_on_foam: 0x7a3e4a,
    glass_window: 0x7ec8e3,
    acoustic_ceiling_tile: 0xd5d8dc,
    absorber_panel_2in: 0x3d4a3a,
    absorber_panel_1in_gap1in: 0x4a5c45,
    absorber_panel_2in_gap2in: 0x2f3d30,
    absorber_panel_4in_gap4in: 0x243028,
    heavy_curtain: 0x6a2a3a
  };
  var WALL_LETTER = ["D", "C", "B", "A"];

  function normalize(raw) {
    var key = String(raw == null ? "" : raw).trim().toLowerCase().replace(/[^a-z0-9]/g, "");
    if (
      key === "splay" || key === "splayed" || key === "rfz" || key === "control" ||
      key === "splayedcontrol" || key === "splayedcontrolroom"
    ) return "splay";
    return "box";
  }

  function dot(a, b) {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  }

  function mean(verts) {
    var s = [0, 0, 0];
    var i;
    for (i = 0; i < verts.length; i++) {
      s[0] += verts[i][0];
      s[1] += verts[i][1];
      s[2] += verts[i][2];
    }
    var n = verts.length || 1;
    return [s[0] / n, s[1] / n, s[2] / n];
  }

  function Face(name, verts, letter) {
    this.name = name;
    this.letter = letter || "";
    this.v = verts.map(function (p) { return [p[0], p[1], p[2]]; });
    var n = [0, 0, 0];
    var m = this.v.length;
    var i;
    for (i = 0; i < m; i++) {
      var a = this.v[i];
      var b = this.v[(i + 1) % m];
      n[0] += (a[1] - b[1]) * (a[2] + b[2]);
      n[1] += (a[2] - b[2]) * (a[0] + b[0]);
      n[2] += (a[0] - b[0]) * (a[1] + b[1]);
    }
    var ln = Math.hypot(n[0], n[1], n[2]);
    this.n = [n[0] / ln, n[1] / ln, n[2] / ln];
    this.d = dot(this.n, mean(this.v));
    this._proj();
  }

  Face.prototype.flip = function () {
    this.n = [-this.n[0], -this.n[1], -this.n[2]];
    this.d = -this.d;
  };

  Face.prototype._proj = function () {
    var ax = 0;
    var an = Math.abs(this.n[0]);
    if (Math.abs(this.n[1]) > an) { ax = 1; an = Math.abs(this.n[1]); }
    if (Math.abs(this.n[2]) > an) ax = 2;
    var keep = [];
    var i;
    for (i = 0; i < 3; i++) if (i !== ax) keep.push(i);
    this.keep = keep;
    var self = this;
    this.p2 = this.v.map(function (p) { return [p[self.keep[0]], p[self.keep[1]]]; });
  };

  Face.prototype.sd = function (x) {
    return dot(this.n, x) - this.d;
  };

  Face.prototype.inside = function (x, tol) {
    if (tol == null) tol = 1e-7;
    var px = x[this.keep[0]];
    var py = x[this.keep[1]];
    var poly = this.p2;
    var c = false;
    var m = poly.length;
    var i;
    for (i = 0; i < m; i++) {
      var x1 = poly[i][0];
      var y1 = poly[i][1];
      var nxt = poly[(i + 1) % m];
      var x2 = nxt[0];
      var y2 = nxt[1];
      var ex = x2 - x1;
      var ey = y2 - y1;
      var length = Math.hypot(ex, ey);
      if (length > 0) {
        var t = ((px - x1) * ex + (py - y1) * ey) / (length * length);
        if (t >= -1e-9 && t <= 1 + 1e-9 && Math.abs((px - x1) * ey - (py - y1) * ex) / length < tol) {
          return false;
        }
      }
      if ((y1 > py) !== (y2 > py)) {
        var xi = x1 + (py - y1) * (x2 - x1) / (y2 - y1);
        if (px < xi) c = !c;
      }
    }
    return c;
  };

  Face.prototype.mirror = function (x) {
    var sd = this.sd(x);
    return [
      x[0] - 2 * sd * this.n[0],
      x[1] - 2 * sd * this.n[1],
      x[2] - 2 * sd * this.n[2]
    ];
  };

  var RAY = (function () {
    var d = [0.5377, 0.8338, 0.1250];
    var n = Math.hypot(d[0], d[1], d[2]);
    return [d[0] / n, d[1] / n, d[2] / n];
  })();

  function pointInRoom(x, faces) {
    var far = [x[0] + RAY[0] * 1e3, x[1] + RAY[1] * 1e3, x[2] + RAY[2] * 1e3];
    var hits = 0;
    var i;
    for (i = 0; i < faces.length; i++) {
      var face = faces[i];
      var da = face.sd(x);
      var db = face.sd(far);
      if (da * db >= 0) continue;
      var t = da / (da - db);
      var q = [
        x[0] + t * (far[0] - x[0]),
        x[1] + t * (far[1] - x[1]),
        x[2] + t * (far[2] - x[2])
      ];
      if (face.inside(q, 1e-12)) hits += 1;
    }
    return hits % 2 === 1;
  }

  function orient(faces) {
    var fi;
    for (fi = 0; fi < faces.length; fi++) {
      var face = faces[fi];
      var centre = mean(face.v);
      if (!face.inside(centre)) {
        var i;
        for (i = 1; i < face.v.length - 1; i++) {
          centre = [
            (face.v[0][0] + face.v[i][0] + face.v[i + 1][0]) / 3,
            (face.v[0][1] + face.v[i][1] + face.v[i + 1][1]) / 3,
            (face.v[0][2] + face.v[i][2] + face.v[i + 1][2]) / 3
          ];
          if (face.inside(centre)) break;
        }
      }
      var trial = [
        centre[0] + 1e-4 * face.n[0],
        centre[1] + 1e-4 * face.n[1],
        centre[2] + 1e-4 * face.n[2]
      ];
      if (!pointInRoom(trial, faces)) face.flip();
    }
    return faces;
  }

  function ceilingAt(z, H, L) {
    var t = !(L > 0) ? 0 : z / L;
    return H * (0.8125 + 0.1875 * t);
  }

  function splayFaces(W, H, L) {
    W = Number(W);
    H = Number(H);
    L = Number(L);
    var pts = [[W / 6, 0], [5 * W / 6, 0], [W, L], [0, L]];
    function h(z) { return ceilingAt(z, H, L); }
    var floor = pts.map(function (p) { return [p[0], 0, p[1]]; });
    var ceil = pts.map(function (p) { return [p[0], h(p[1]), p[1]]; });
    var faces = [new Face("floor", floor, "E"), new Face("ceiling", ceil, "F")];
    var i;
    for (i = 0; i < pts.length; i++) {
      var x1 = pts[i][0];
      var z1 = pts[i][1];
      var x2 = pts[(i + 1) % pts.length][0];
      var z2 = pts[(i + 1) % pts.length][1];
      faces.push(new Face("wall" + i, [
        [x1, 0, z1],
        [x2, 0, z2],
        [x2, h(z2), z2],
        [x1, h(z1), z1]
      ], WALL_LETTER[i]));
    }
    return orient(faces);
  }

  function aabb(faces) {
    var lo = [Infinity, Infinity, Infinity];
    var hi = [-Infinity, -Infinity, -Infinity];
    faces.forEach(function (face) {
      face.v.forEach(function (p) {
        var k;
        for (k = 0; k < 3; k++) {
          if (p[k] < lo[k]) lo[k] = p[k];
          if (p[k] > hi[k]) hi[k] = p[k];
        }
      });
    });
    return [lo, hi];
  }

  function aabbDist(point, lo, hi) {
    var s = 0;
    var k;
    for (k = 0; k < 3; k++) {
      var d = 0;
      if (lo[k] - point[k] > 0) d = lo[k] - point[k];
      if (point[k] - hi[k] > 0) d += point[k] - hi[k];
      s += d * d;
    }
    return Math.sqrt(s);
  }

  function buildTree(src, faces, order, maxDist) {
    var nodes = [{ pos: src.slice(), seq: [], parent: -1 }];
    var frontier = [0];
    var box = aabb(faces);
    var k;
    for (k = 1; k <= order; k++) {
      var nxt = [];
      var fi;
      for (fi = 0; fi < frontier.length; fi++) {
        var node = nodes[frontier[fi]];
        var last = node.seq.length ? node.seq[node.seq.length - 1] : -1;
        var g;
        for (g = 0; g < faces.length; g++) {
          if (g === last) continue;
          if (faces[g].sd(node.pos) <= EPS) continue;
          var child = faces[g].mirror(node.pos);
          if (maxDist != null && aabbDist(child, box[0], box[1]) > maxDist) continue;
          nodes.push({ pos: child, seq: node.seq.concat([g]), parent: frontier[fi] });
          nxt.push(nodes.length - 1);
        }
      }
      frontier = nxt;
    }
    return nodes;
  }

  function chain(nodes, i) {
    var out = [];
    while (i >= 0) {
      out.push(i);
      i = nodes[i].parent;
    }
    out.reverse();
    return out;
  }

  /* null when the image does not reach the receiver. Otherwise the bounce
     points, mic first. An empty list is the direct image. */
  function audibleHits(nodes, i, receiver, faces) {
    var seq = nodes[i].seq;
    var p = receiver.slice();
    var prev = null;
    var ch = chain(nodes, i);
    var hits = [];
    var j;
    for (j = seq.length - 1; j >= 0; j--) {
      var face = faces[seq[j]];
      var img = nodes[ch[j + 1]].pos;
      var dp = face.sd(p);
      var di = face.sd(img);
      if (dp <= EPS || di >= -EPS) return null;
      var t = dp / (dp - di);
      var q = [
        p[0] + t * (img[0] - p[0]),
        p[1] + t * (img[1] - p[1]),
        p[2] + t * (img[2] - p[2])
      ];
      if (!face.inside(q)) return null;
      if (prev != null && faces[prev].sd(q) <= EPS) return null;
      hits.push(q);
      p = q;
      prev = seq[j];
    }
    return hits;
  }

  function cloneRings(faces) {
    return faces.map(function (face) {
      return face.v.map(function (p) { return p.slice(); });
    });
  }

  function mirrorRings(faces, seq, rings) {
    var out = rings.map(function (ring) {
      return ring.map(function (p) { return p.slice(); });
    });
    var s;
    for (s = 0; s < seq.length; s++) {
      var face = faces[seq[s]];
      var i;
      for (i = 0; i < out.length; i++) {
        var j;
        for (j = 0; j < out[i].length; j++) out[i][j] = face.mirror(out[i][j]);
      }
    }
    return out;
  }

  function imageRooms(shape, W, H, L, source, receivers, opts) {
    if (normalize(shape) !== "splay") return null;
    opts = opts || {};
    var order = opts.order == null ? 4 : opts.order;
    var maxDist = opts.maxDist == null ? 340 : opts.maxDist;
    var faces = splayFaces(W, H, L);
    var src = [Number(source[0]), Number(source[1]), Number(source[2])];
    var nodes = buildTree(src, faces, order, maxDist);
    var home = cloneRings(faces);
    var rooms = [];
    var i;
    for (i = 0; i < nodes.length; i++) {
      var heard = {};
      var any = false;
      var r;
      for (r = 0; r < receivers.length; r++) {
        var hits = audibleHits(nodes, i, receivers[r].p, faces);
        if (hits === null) continue;
        any = true;
        var path = [src.slice()];
        var h;
        for (h = hits.length - 1; h >= 0; h--) path.push(hits[h].slice());
        path.push(receivers[r].p.slice());
        heard[receivers[r].id] = path;
      }
      if (!any) continue;
      var seq = nodes[i].seq;
      rooms.push({
        key: seq.length ? seq.join(".") : "home",
        seq: seq.slice(),
        order: seq.length,
        pos: nodes[i].pos.slice(),
        rings: mirrorRings(faces, seq, home),
        heard: heard
      });
    }
    return { faces: faces, rooms: rooms };
  }

  function materialId(surfaces, letter) {
    var card = surfaces && surfaces[letter];
    if (!card) return "";
    return card.material || card.material_id || "";
  }

  function hashColor(id) {
    var h = 0;
    var s = String(id);
    var i;
    for (i = 0; i < s.length; i++) h = (h * 33 + s.charCodeAt(i)) >>> 0;
    var r = 80 + (h & 127);
    var g = 80 + ((h >>> 8) & 127);
    var b = 80 + ((h >>> 16) & 127);
    return (r << 16) | (g << 8) | b;
  }

  function wallColor(surfaces, letter) {
    var id = materialId(surfaces, letter);
    if ((letter === "A" || letter === "C") && !id) {
      id = materialId(surfaces, letter === "A" ? "C" : "A");
    }
    if (id && MATERIAL_COLOR[id] != null) return MATERIAL_COLOR[id];
    if (id) return hashColor(id);
    return LETTER_COLOR[letter] != null ? LETTER_COLOR[letter] : 0x1a1d26;
  }

  function colorKey(surfaces) {
    return ["A", "B", "C", "D", "E", "F"].map(function (letter) {
      return wallColor(surfaces, letter);
    }).join(",");
  }

  function fadeGain(from, to, ageMs) {
    var u = Number(ageMs) / FADE_MS;
    if (!(u > 0)) u = 0;
    if (u > 1) u = 1;
    return from + (to - from) * u;
  }

  function stepFade(rows, keys, now) {
    var next = {};
    var alive = {};
    var prev = rows || {};
    var i;
    for (i = 0; i < keys.length; i++) alive[keys[i]] = true;
    Object.keys(prev).forEach(function (k) {
      next[k] = { t0: prev[k].t0, from: prev[k].from, to: prev[k].to };
    });
    for (i = 0; i < keys.length; i++) {
      var k = keys[i];
      var row = next[k];
      if (!row) next[k] = { t0: now, from: 0, to: 1 };
      else if (row.to !== 1) {
        next[k] = { t0: now, from: fadeGain(row.from, row.to, now - row.t0), to: 1 };
      }
    }
    Object.keys(next).forEach(function (k) {
      if (alive[k]) return;
      var row = next[k];
      if (row.to !== 0) {
        next[k] = { t0: now, from: fadeGain(row.from, row.to, now - row.t0), to: 0 };
      } else if (now - row.t0 >= FADE_MS) {
        delete next[k];
      }
    });
    return next;
  }

  function gainOf(row, now) {
    if (!row) return 0;
    return fadeGain(row.from, row.to, now - row.t0);
  }

  function room3dBoxGeometries(THREE, W, H, L, mapZ) {
    mapZ = mapZ || function (z) { return L - z; };
    var t = 0.04;
    var floorGeo = new THREE.PlaneGeometry(W, L);
    floorGeo.rotateX(-Math.PI / 2);
    var box = new THREE.BoxGeometry(W, H, L);
    var edges = new THREE.EdgesGeometry(box);
    box.dispose();
    return {
      floor: { geo: floorGeo, pos: [W * 0.5, 0, L * 0.5] },
      front: { geo: new THREE.BoxGeometry(W, H, t), pos: [W * 0.5, H * 0.5, mapZ(L)] },
      back: { geo: new THREE.BoxGeometry(W, H, t), pos: [W * 0.5, H * 0.5, mapZ(0)] },
      left: { geo: new THREE.BoxGeometry(t, H, L), pos: [0, H * 0.5, L * 0.5] },
      right: { geo: new THREE.BoxGeometry(t, H, L), pos: [W, H * 0.5, L * 0.5] },
      ceil: { geo: new THREE.PlaneGeometry(W, L), pos: [W * 0.5, H, L * 0.5], rotX: Math.PI / 2 },
      edges: { geo: edges, pos: [W * 0.5, H * 0.5, L * 0.5], lines: true }
    };
  }

  function imageBoxGeometries(THREE, W, H, L) {
    var hy = H * 0.5;
    var box = new THREE.BoxGeometry(W, H, L);
    var edges = new THREE.EdgesGeometry(box);
    box.dispose();
    return {
      home: { geo: edges, pos: [W * 0.5, H * 0.5, L * 0.5], lines: true },
      floor: { geo: new THREE.PlaneGeometry(W, L), pos: [W * 0.5, 0.012, L * 0.5], rotX: -Math.PI / 2 },
      z0: { geo: new THREE.PlaneGeometry(W, H), pos: [W * 0.5, hy, 0] },
      zL: { geo: new THREE.PlaneGeometry(W, H), pos: [W * 0.5, hy, L] },
      x0: { geo: new THREE.PlaneGeometry(L, H), pos: [0, hy, L * 0.5], rotY: Math.PI / 2 },
      xW: { geo: new THREE.PlaneGeometry(L, H), pos: [W, hy, L * 0.5], rotY: Math.PI / 2 },
      ceil: { geo: new THREE.PlaneGeometry(W, L), pos: [W * 0.5, H, L * 0.5], rotX: Math.PI / 2 }
    };
  }

  function cellEdges(THREE, min, max) {
    var sx = Math.max(max.x - min.x, 1e-4);
    var sy = Math.max(max.y - min.y, 1e-4);
    var sz = Math.max(max.z - min.z, 1e-4);
    var geo = new THREE.BoxGeometry(sx, sy, sz);
    var edges = new THREE.EdgesGeometry(geo);
    geo.dispose();
    return {
      geo: edges,
      pos: [(min.x + max.x) * 0.5, (min.y + max.y) * 0.5, (min.z + max.z) * 0.5],
      lines: true
    };
  }

  function placePart(THREE, part, material) {
    var mesh = part.lines
      ? new THREE.LineSegments(part.geo, material)
      : new THREE.Mesh(part.geo, material);
    mesh.position.set(part.pos[0], part.pos[1], part.pos[2]);
    if (part.rotX) mesh.rotation.x = part.rotX;
    if (part.rotY) mesh.rotation.y = part.rotY;
    return mesh;
  }

  return {
    FADE_MS: FADE_MS,
    LETTER_COLOR: LETTER_COLOR,
    normalize: normalize,
    splayFaces: splayFaces,
    imageRooms: imageRooms,
    wallColor: wallColor,
    colorKey: colorKey,
    fadeGain: fadeGain,
    stepFade: stepFade,
    gainOf: gainOf,
    room3dBoxGeometries: room3dBoxGeometries,
    imageBoxGeometries: imageBoxGeometries,
    cellEdges: cellEdges,
    placePart: placePart,
    ceilingAt: ceilingAt
  };
});
