/* 2011 Room Reverb — Lattice / In-room paths / Last-legs */
(function (global) {
  "use strict";

  var MIC_COLORS = { L: 0xa78bfa, C: 0x60a5fa, R: 0x34d399 };
  var POL_POS = 0x2dd4bf;
  var POL_NEG = 0xf472b6;
  var HOME = 0xfbbf24;
  var SRC = 0xfbbf24;
  var SRC_B = 0xf43f5e;

  function create(opts) {
    var canvas = opts.canvas;
    if (!global.THREE) {
      console.warn("Three.js missing — image views disabled");
      return null;
    }
    var THREE = global.THREE;
    var getState = opts.getState || function () { return global.RRState || null; };

    var renderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: false, preserveDrawingBuffer: true });
    } catch (err) {
      console.error("ImageViews WebGLRenderer failed", err);
      throw err;
    }
    renderer.setPixelRatio(Math.min(global.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x0a0b0e, 1);
    if (renderer.outputColorSpace !== undefined) renderer.outputColorSpace = THREE.SRGBColorSpace;

    var scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x0a0b0e, 28, 90);
    var camera = new THREE.PerspectiveCamera(42, 1, 0.05, 400);
    var camTarget = new THREE.Vector3(3, 1.2, 4);
    // Same Z mapping as Floor / room 3D: worldZ = L − z, Front far, Y-up.
    // Orbit is the only camera frame (theta / phi / radius). Pan reads the camera, it does not rebuild it.
    var camSph = { theta: 0, phi: 1.12, radius: 22 };
    var fittedRoom = null;
    var hasFit = false;

    function worldZ(z, L) {
      return L - z;
    }
    function mapPt(p, L) {
      if (!p) return p;
      if (typeof p.z === "number") return { x: p.x, y: p.y, z: worldZ(p.z, L) };
      if (Array.isArray(p) && p.length >= 3) {
        return { x: p[0], y: p[1], z: worldZ(p[2], L) };
      }
      return p;
    }
    function mapCell(min, max, L) {
      var z0 = worldZ(min.z, L);
      var z1 = worldZ(max.z, L);
      return {
        min: { x: min.x, y: min.y, z: Math.min(z0, z1) },
        max: { x: max.x, y: max.y, z: Math.max(z0, z1) }
      };
    }

    scene.add(new THREE.AmbientLight(0xb0b8c8, 0.55));
    var key = new THREE.DirectionalLight(0xfff4e6, 0.85); key.position.set(8, 14, 6); scene.add(key);
    var fill = new THREE.DirectionalLight(0x88aaff, 0.25); fill.position.set(-10, 4, -8); scene.add(fill);
    var rim = new THREE.PointLight(0x2dd4bf, 0.4, 60); scene.add(rim);

    var root = new THREE.Group(); scene.add(root);
    var mode = "lattice";
    var data = null;
    var fadeRows = {};
    var fadeMats = [];
    var roomCache = {};
    var drawnCount = null;
    var wasFading = false;

    function sceneState() {
      return getState() || null;
    }
    function isSplay() {
      return !!(global.RoomDraw && RoomDraw.normalize(sceneState() && sceneState().room_shape) === "splay");
    }
    function nowMs() {
      return (global.performance && performance.now) ? performance.now() : Date.now();
    }
    var needsRender = true;
    var disposed = false;
    var raf = 0;
    var orbiting = false;
    var panning = false;
    var lastPtr = { x: 0, y: 0 };
    var pathHits = [];
    var tip = document.createElement("div");
    tip.className = "path-tip";
    tip.hidden = true;
    if (canvas.parentElement) canvas.parentElement.appendChild(tip);

    function clearRoot() {
      while (root.children.length) {
        var ch = root.children[0];
        root.remove(ch);
        ch.traverse(function (o) {
          if (o.geometry) o.geometry.dispose();
          if (o.material) {
            if (Array.isArray(o.material)) o.material.forEach(function (m) { m.dispose(); });
            else o.material.dispose();
          }
        });
      }
    }

    function boxEdges(min, max, color, opacity) {
      var built = RoomDraw.cellEdges(THREE, min, max);
      var mat = new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: opacity == null ? 0.45 : opacity });
      var line = new THREE.LineSegments(built.geo, mat);
      line.position.set(built.pos[0], built.pos[1], built.pos[2]);
      return line;
    }

    function marker(color, r) {
      return new THREE.Mesh(
        new THREE.SphereGeometry(r || 0.12, 16, 12),
        new THREE.MeshStandardMaterial({ color: color, emissive: color, emissiveIntensity: 0.35, roughness: 0.4, metalness: 0.2 })
      );
    }

    function linePts(pts, color, opacity) {
      var L = (data && data.room) ? data.room.L : 0;
      var arr = [];
      for (var i = 0; i < pts.length; i++) {
        var q = mapPt(pts[i], L);
        arr.push(new THREE.Vector3(q.x, q.y, q.z));
      }
      var geo = new THREE.BufferGeometry().setFromPoints(arr);
      var mat = new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: opacity == null ? 0.85 : opacity });
      return new THREE.Line(geo, mat);
    }

    function makeLabel(text, color) {
      var c = document.createElement("canvas"); c.width = 160; c.height = 48;
      var ctx = c.getContext("2d");
      ctx.clearRect(0, 0, 160, 48);
      ctx.font = "600 18px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillStyle = "rgba(10,11,14,0.75)";
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(8, 8, 144, 32, 8); else ctx.rect(8, 8, 144, 32);
      ctx.fill();
      ctx.fillStyle = color; ctx.fillText(text, 80, 25);
      var tex = new THREE.CanvasTexture(c);
      var spr = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
      spr.scale.set(1.1, 0.33, 1);
      return spr;
    }

    function homeBox(room) {
      return boxEdges({ x: 0, y: 0, z: 0 }, { x: room.W, y: room.H, z: room.L }, HOME, 0.95);
    }

    /* Paths / last legs: a readable room. Front is z=0 in this view (worldZ of L). */
    function addRoomShell(room) {
      if (isSplay()) { addSplayShell(room); return; }
      root.add(homeBox(room));
      var built = RoomDraw.imageBoxGeometries(THREE, room.W, room.H, room.L);
      built.home.geo.dispose();
      var floor = RoomDraw.placePart(THREE, built.floor, new THREE.MeshStandardMaterial({
        color: 0x2a3142, roughness: 0.86, metalness: 0.04
      }));
      root.add(floor);
      var wallMat = new THREE.MeshBasicMaterial({
        color: 0x9aa3b8, transparent: true, opacity: 0.07,
        side: THREE.DoubleSide, depthWrite: false
      });
      ["z0", "zL", "x0", "xW", "ceil"].forEach(function (name) {
        root.add(RoomDraw.placePart(THREE, built[name], wallMat));
      });
      function tag(text, x, y, z) {
        var spr = makeLabel(text, "#c5cad6");
        spr.position.set(x, y, z);
        root.add(spr);
      }
      var ly = Math.max(0.4, room.H * 0.62);
      tag("A Left", 0.05, ly, room.L * 0.5);
      tag("B Front", room.W * 0.5, ly, 0.05);
      tag("C Right", room.W - 0.05, ly, room.L * 0.5);
      tag("D Back", room.W * 0.5, ly, room.L - 0.05);
      tag("E Floor", room.W * 0.5, 0.28, room.L * 0.35);
      tag("F Ceiling", room.W * 0.5, Math.max(0.5, room.H - 0.2), room.L * 0.65);
    }

    function addActors(source, mics, selected) {
      var L = (data && data.room) ? data.room.L : 0;
      var s = marker(SRC, 0.14);
      s.position.set(source.x, source.y, worldZ(source.z, L)); root.add(s);
      var sLab = makeLabel(data && data.source_b ? "A" : "Src", "#fbbf24");
      sLab.position.set(source.x, source.y + 0.35, worldZ(source.z, L)); root.add(sLab);
      if (data && data.source_b) {
        var b = data.source_b;
        var bm = marker(SRC_B, 0.13);
        bm.position.set(b.x, b.y, worldZ(b.z, L)); root.add(bm);
        var bLab = makeLabel("B", "#f43f5e");
        bLab.position.set(b.x, b.y + 0.35, worldZ(b.z, L)); root.add(bLab);
      }
      ["L", "C", "R"].forEach(function (id) {
        if (selected.indexOf(id) < 0 && mode !== "lattice") return;
        var m = mics[id]; if (!m) return;
        var mesh = marker(MIC_COLORS[id], id === "C" ? 0.11 : 0.09);
        mesh.position.set(m.x, m.y, worldZ(m.z, L)); root.add(mesh);
        if (selected.indexOf(id) >= 0) {
          var col = id === "L" ? "#a78bfa" : id === "R" ? "#34d399" : "#60a5fa";
          var lab = makeLabel(id, col);
          lab.position.set(m.x, m.y + 0.32, worldZ(m.z, L)); root.add(lab);
        }
      });
    }

    function addWallLabels(room) {
      var ly = room.H * 0.55;
      var f = makeLabel("Front", "#2dd4bf");
      f.position.set(room.W * 0.5, ly, worldZ(room.L, room.L));
      root.add(f);
      var b = makeLabel("Back", "#fb7185");
      b.position.set(room.W * 0.5, ly, worldZ(0, room.L));
      root.add(b);
    }

    function mapRing(ring, L) {
      return ring.map(function (p) { return [p[0], p[1], worldZ(p[2], L)]; });
    }

    function ringLine(ring, color, opacity) {
      var pts = ring.map(function (p) { return new THREE.Vector3(p[0], p[1], p[2]); });
      pts.push(pts[0].clone());
      var mat = new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: opacity });
      return { line: new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat), mat: mat };
    }

    function polyFill(ring, color, opacity) {
      var positions = [];
      var i;
      for (i = 1; i < ring.length - 1; i++) {
        positions.push(ring[0][0], ring[0][1], ring[0][2]);
        positions.push(ring[i][0], ring[i][1], ring[i][2]);
        positions.push(ring[i + 1][0], ring[i + 1][1], ring[i + 1][2]);
      }
      var geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
      geo.computeVertexNormals();
      var mat = new THREE.MeshStandardMaterial({
        color: color, roughness: 0.9, metalness: 0.04,
        transparent: opacity < 1, opacity: opacity, side: THREE.DoubleSide, depthWrite: opacity >= 1
      });
      return new THREE.Mesh(geo, mat);
    }

    function splayReceivers() {
      var selected = (data && data.selected_mics) || ["C"];
      var out = [];
      selected.forEach(function (id) {
        var m = data.mics && data.mics[id];
        if (!m) return;
        out.push({ id: id, p: [m.x, m.y, m.z] });
      });
      return { selected: selected, receivers: out };
    }

    function takeSplay() {
      var room = data.room;
      var ear = splayReceivers();
      var cap = (data.c || 340) * 1;
      var packs = [];
      function one(prefix, source) {
        var pack = RoomDraw.imageRooms("splay", room.W, room.H, room.L, source, ear.receivers, {
          order: 4, maxDist: cap
        });
        (pack.rooms || []).forEach(function (r) {
          roomCache[prefix + ":" + r.key] = r;
        });
        packs.push({ prefix: prefix, pack: pack });
      }
      one("a", [data.source.x, data.source.y, data.source.z]);
      if (data.source_b) one("b", [data.source_b.x, data.source_b.y, data.source_b.z]);
      var keys = [];
      packs.forEach(function (p) {
        p.pack.rooms.forEach(function (r) { keys.push(p.prefix + ":" + r.key); });
      });
      var now = nowMs();
      fadeRows = RoomDraw.stepFade(fadeRows, keys, now);
      Object.keys(roomCache).forEach(function (k) {
        if (!fadeRows[k]) delete roomCache[k];
      });
      drawnCount = keys.length;
      return { packs: packs, now: now, selected: ear.selected, surfaces: (sceneState() || {}).surfaces };
    }

    function trackFade(mat, key, base) {
      fadeMats.push({ mat: mat, key: key, base: base });
      var row = fadeRows[key];
      mat.opacity = base * RoomDraw.gainOf(row, nowMs());
    }

    function addMirroredRooms(wireOnly) {
      fadeMats = [];
      var got = takeSplay();
      var room = data.room;
      Object.keys(fadeRows).forEach(function (key) {
        var rec = roomCache[key];
        if (!rec) return;
        var force = key.charAt(0) === "b" ? SRC_B : null;
        var col = force != null ? force : (rec.order % 2 === 0 ? (rec.key === "home" ? HOME : POL_POS) : POL_NEG);
        if (rec.key === "home" && force == null) col = HOME;
        var base = rec.key === "home" ? 0.95 : (force != null ? 0.22 : 0.32);
        rec.rings.forEach(function (ring) {
          var drawn = ringLine(mapRing(ring, room.L), col, base);
          trackFade(drawn.mat, key, base);
          root.add(drawn.line);
        });
        if (!wireOnly && rec.key === "home") {
          var faces = got.packs[0].pack.faces;
          faces.forEach(function (face, i) {
            var opacity = face.letter === "E" ? 1 : (face.letter === "F" ? 0.22 : 0.45);
            var mesh = polyFill(mapRing(rec.rings[i], room.L), RoomDraw.wallColor(got.surfaces, face.letter), opacity);
            root.add(mesh);
          });
        }
        if (rec.key !== "home") {
          var p = mapPt({ x: rec.pos[0], y: rec.pos[1], z: rec.pos[2] }, room.L);
          var mark = marker(col, 0.08);
          mark.position.set(p.x, p.y, p.z);
          root.add(mark);
        }
      });
      return got;
    }

    function addSplayShell(room) {
      var got = addMirroredRooms(false);
      var faces = got.packs[0].pack.faces;
      var names = { A: ["A Left", "#38bdf8"], B: ["B Front", "#2dd4bf"], C: ["C Right", "#a78bfa"], D: ["D Back", "#fb7185"], E: ["E Floor", "#78716c"], F: ["F Ceiling", "#e2e8f0"] };
      faces.forEach(function (face) {
        var named = names[face.letter];
        if (!named) return;
        var c = [0, 0, 0];
        face.v.forEach(function (p) { c[0] += p[0]; c[1] += p[1]; c[2] += p[2]; });
        var n = face.v.length || 1;
        var tp = mapPt({ x: c[0] / n, y: c[1] / n, z: c[2] / n }, room.L);
        var spr = makeLabel(named[0], named[1]);
        spr.position.set(tp.x, tp.y, tp.z);
        root.add(spr);
      });
    }

    function addSplayPathLines(lastOnly) {
      var room = data.room;
      var selected = data.selected_mics || ["C"];
      selected.forEach(function (micId) {
        Object.keys(fadeRows).forEach(function (key) {
          var rec = roomCache[key];
          if (!rec || !rec.heard[micId]) return;
          var path = rec.heard[micId];
          var ends = lastOnly ? [path[path.length - 2], path[path.length - 1]] : path;
          if (!ends[0] || !ends[1]) return;
          var force = key.charAt(0) === "b" ? SRC_B : null;
          var col = force != null ? force : (rec.key === "home" ? SRC : (rec.order % 2 === 0 ? POL_POS : POL_NEG));
          var base = rec.key === "home" ? 0.95 : 0.45;
          var drawn = linePts(ends.map(function (p) { return { x: p[0], y: p[1], z: p[2] }; }), col, base);
          trackFade(drawn.material, key, base);
          root.add(drawn);
          rememberHit({ order: rec.order, is_direct: rec.key === "home", polarity: rec.order % 2 === 0 ? 1 : -1 }, ends, micId);
        });
      });
    }


    function perMicTaps(d, micId) {
      var pm = (d && (d.per_mic || d.by_mic || d.paths_by_mic)) || {};
      return pm[micId] || [];
    }

    function imageXyz(im) {
      if (!im) return null;
      return im.image_xyz || im.xyz || im.pos || im.position || null;
    }

    function cellBounds(im) {
      var cell = (im && (im.cell || im.bounds)) || {};
      var mn = cell.min || cell.lo || cell.lower;
      var mx = cell.max || cell.hi || cell.upper;
      return (mn && mx) ? { min: mn, max: mx } : null;
    }

    function legEnds(leg) {
      if (!leg) return null;
      var fr = leg.from || leg.start || leg.a;
      var to = leg.to || leg.end || leg.b;
      if (!fr || !to) return null;
      return [fr, to];
    }

    function roomSpan(room) {
      return Math.max(room.W, room.H, room.L);
    }

    function roomDiag(room) {
      return Math.sqrt(room.W * room.W + room.H * room.H + room.L * room.L);
    }

    function latticeFitRadius(room) {
      return Math.max(14, roomSpan(room) * 3.2 * 1.05);
    }

    function radiusLimits() {
      var room = data && data.room;
      if (!room) return { minR: 2.5, maxR: 120 };
      var minR = 0.2 * roomDiag(room);
      var maxR = (mode === "lattice") ? (3 * latticeFitRadius(room)) : (8 * roomSpan(room));
      if (!(maxR > minR)) maxR = minR * 4;
      return { minR: minR, maxR: maxR };
    }

    function roomScaleJump(room) {
      if (!fittedRoom) return true;
      function ratio(a, b) {
        var lo = Math.min(Math.abs(a), Math.abs(b));
        var hi = Math.max(Math.abs(a), Math.abs(b));
        if (lo < 1e-9) return hi > 1e-9 ? Infinity : 1;
        return hi / lo;
      }
      return ratio(room.W, fittedRoom.W) > 2
        || ratio(room.H, fittedRoom.H) > 2
        || ratio(room.L, fittedRoom.L) > 2;
    }

    function fitCamera(lattice) {
      if (!data || !data.room) return;
      var room = data.room;
      camTarget.set(room.W * 0.5, room.H * 0.4, room.L * 0.5);
      if (lattice) {
        camSph.radius = latticeFitRadius(room);
        camSph.theta = 0; camSph.phi = 0.42;
      } else {
        camSph.radius = Math.max(8, roomDiag(room) * 1.25);
        /* Three-quarter view: see the floor and two walls, not a front-on camera. */
        camSph.theta = 0.78; camSph.phi = 0.92;
      }
      fittedRoom = { W: room.W, H: room.H, L: room.L };
      hasFit = true;
      rim.position.set(room.W * 0.5, room.H * 0.7, room.L * 0.5);
      updateCamera();
    }

    /* First data, Reset, or a room axis that more than doubles. Sidebar nudges keep the camera. */
    function fitIfNeeded(lattice) {
      if (!data || !data.room) return;
      if (hasFit && !roomScaleJump(data.room)) return;
      fitCamera(lattice);
    }

    function forceFit() {
      hasFit = false;
      fittedRoom = null;
      fitCamera(mode === "lattice");
    }

    function updateCamera() {
      var s = camSph;
      var lim = radiusLimits();
      s.phi = Math.max(0.08, Math.min(Math.PI / 2, s.phi));
      s.radius = Math.max(lim.minR, Math.min(lim.maxR, s.radius));
      camera.up.set(0, 1, 0);
      var sinPhi = Math.sin(s.phi);
      camera.position.set(
        camTarget.x + s.radius * sinPhi * Math.sin(s.theta),
        camTarget.y + s.radius * Math.cos(s.phi),
        camTarget.z + s.radius * sinPhi * Math.cos(s.theta)
      );
      camera.lookAt(camTarget);
      camera.near = Math.max(0.02, Math.min(1.0, s.radius * 0.002));
      camera.far = Math.max(4 * s.radius, camera.near * 8);
      camera.updateProjectionMatrix();
      if (scene.fog) {
        scene.fog.near = 0.9 * s.radius;
        scene.fog.far = 3 * s.radius;
      }
    }

    function buildLattice() {
      pathHits = [];
      hideTip();
      if (!data) return;
      clearRoot();
      if (isSplay()) {
        addMirroredRooms(true);
        addWallLabels(data.room);
        addActors(data.source, data.mics, data.selected_mics || ["C"]);
        fitIfNeeded(true);
        return;
      }
      drawnCount = null;
      fadeRows = {};
      fadeMats = [];
      roomCache = {};
      var room = data.room;
      root.add(homeBox(room));
      var grid = new THREE.GridHelper(Math.max(room.W, room.L), 8, 0x3a4155, 0x222833);
      grid.position.set(room.W * 0.5, 0.01, room.L * 0.5);
      grid.scale.set(room.W / Math.max(room.W, room.L), 1, room.L / Math.max(room.W, room.L));
      root.add(grid);
      function addLattice(list, force) {
        (list || []).forEach(function (im) {
          var col = force != null ? force : (im.is_home ? HOME : (im.polarity > 0 ? POL_POS : POL_NEG));
          var op = force != null ? (im.is_home ? 0.8 : 0.22) : (im.is_home ? 0.95 : 0.32);
          var cb = cellBounds(im);
          if (cb) {
            var mapped = mapCell(cb.min, cb.max, room.L);
            root.add(boxEdges(mapped.min, mapped.max, col, op));
          }
          var xyz = imageXyz(im);
          if (xyz) {
            var m = marker(col, im.is_home ? 0.1 : 0.08);
            var p = mapPt(xyz, room.L);
            m.position.set(p.x, p.y, p.z);
            root.add(m);
          }
        });
      }
      addLattice(data.lattice || data.images || []);
      if (data.lattice_b) addLattice(data.lattice_b, SRC_B);
      addWallLabels(room);
      addActors(data.source, data.mics, data.selected_mics || ["C"]);
      fitIfNeeded(true);
    }

    function rememberHit(tap, pts, micId) {
      var L = (data && data.room) ? data.room.L : 0;
      (pts || []).forEach(function (pt) {
        var q = mapPt(pt, L);
        if (!q || typeof q.x !== "number") return;
        pathHits.push({ x: q.x, y: q.y, z: q.z, tap: tap, mic: micId });
      });
    }
    function fmtDb(v) {
      if (v == null || !isFinite(Number(v))) return "—";
      var n = Number(v);
      return (n >= 0 ? "+" : "−") + Math.abs(n).toFixed(1) + " dB";
    }
    function fmtDeg(v) {
      if (v == null || !isFinite(Number(v))) return "—";
      return Math.round(Number(v)) + "°";
    }

    function buildPaths() {
      if (!data) return;
      pathHits = [];
      clearRoot();
      if (isSplay()) {
        addSplayShell(data.room);
        addSplayPathLines(false);
        addActors(data.source, data.mics, data.selected_mics || ["C"]);
        fitIfNeeded(false);
        return;
      }
      drawnCount = null;
      var room = data.room;
      addRoomShell(room);
      var selected = data.selected_mics || ["C"];
      function addPathSet(taps, force, micId) {
        (taps || []).forEach(function (t) {
          if (!t.path || t.path.length < 2) return;
          var col = force != null ? force : (t.is_direct ? SRC : (t.polarity > 0 ? POL_POS : POL_NEG));
          var op = t.is_direct ? 0.95 : 0.35 + 0.4 / (1 + t.order);
          if (force != null && !t.is_direct) op *= 0.75;
          root.add(linePts(t.path, col, op));
          rememberHit(t, t.path, micId);
        });
      }
      selected.forEach(function (micId) {
        addPathSet(perMicTaps(data, micId), null, micId);
        if (data.per_mic_b) addPathSet(data.per_mic_b[micId] || [], SRC_B, micId);
      });
      addActors(data.source, data.mics, selected);
      fitIfNeeded(false);
    }

    function buildLegs() {
      if (!data) return;
      pathHits = [];
      clearRoot();
      if (isSplay()) {
        addSplayShell(data.room);
        addSplayPathLines(true);
        var selected = data.selected_mics || ["C"];
        selected.forEach(function (micId) {
          var mic = data.mics[micId];
          if (!mic) return;
          var hemi = new THREE.Mesh(
            new THREE.SphereGeometry(0.55, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.5),
            new THREE.MeshBasicMaterial({ color: MIC_COLORS[micId], transparent: true, opacity: 0.08, side: THREE.DoubleSide, depthWrite: false })
          );
          hemi.position.set(mic.x, mic.y, worldZ(mic.z, data.room.L));
          root.add(hemi);
        });
        addActors(data.source, data.mics, selected);
        fitIfNeeded(false);
        return;
      }
      drawnCount = null;
      var room = data.room;
      addRoomShell(room);
      var selected = data.selected_mics || ["C"];
      function addLegSet(taps, force, micId) {
        (taps || []).forEach(function (t) {
          var leg = t.last_leg || t.lastLeg || t.leg; if (!leg) return;
          var ends = legEnds(leg); if (!ends) return;
          var col = force != null ? force : (t.is_direct ? SRC : (t.polarity > 0 ? POL_POS : POL_NEG));
          var op = t.is_direct ? 1.0 : 0.4 + 0.35 / (1 + t.order);
          if (force != null && !t.is_direct) op *= 0.75;
          root.add(linePts(ends, col, op));
          var mark = marker(col, 0.045);
          var tp = mapPt(ends[0], room.L);
          mark.position.set(tp.x, tp.y, tp.z);
          root.add(mark);
          rememberHit(t, ends, micId);
        });
      }
      selected.forEach(function (micId) {
        var mic = data.mics[micId];
        addLegSet(perMicTaps(data, micId), null, micId);
        if (data.per_mic_b) addLegSet(data.per_mic_b[micId] || [], SRC_B, micId);
        if (mic) {
          var hemi = new THREE.Mesh(
            new THREE.SphereGeometry(0.55, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.5),
            new THREE.MeshBasicMaterial({ color: MIC_COLORS[micId], transparent: true, opacity: 0.08, side: THREE.DoubleSide, depthWrite: false })
          );
          hemi.position.set(mic.x, mic.y, worldZ(mic.z, room.L));
          root.add(hemi);
        }
      });
      addActors(data.source, data.mics, selected);
      fitIfNeeded(false);
    }

    function rebuild() {
      if (mode === "lattice") buildLattice();
      else if (mode === "paths") buildPaths();
      else buildLegs();
      needsRender = true;
    }

    function resize() {
      var rect = canvas.getBoundingClientRect();
      var cssW = Math.floor(rect.width);
      var cssH = Math.floor(rect.height);
      /* Skip while panel is hidden / layout not ready — avoid bogus 0×0→2×2 context. */
      if (cssW < 2 || cssH < 2) return;
      var pr = Math.min(global.devicePixelRatio || 1, 2);
      if (canvas.width !== cssW * pr || canvas.height !== cssH * pr) renderer.setSize(cssW, cssH, false);
      camera.aspect = cssW / Math.max(1, cssH);
      camera.updateProjectionMatrix();
      needsRender = true;
    }

    function onPointerDown(evt) {
      lastPtr.x = evt.clientX; lastPtr.y = evt.clientY;
      var pan = evt.button === 2 || (evt.button === 0 && evt.shiftKey);
      var orbit = evt.button === 1 || (evt.button === 0 && !evt.shiftKey);
      if (!pan && !orbit) return;
      panning = pan;
      orbiting = orbit;
      canvas.classList.add("dragging");
      try { canvas.setPointerCapture(evt.pointerId); } catch (e) {}
      evt.preventDefault();
    }

    function hideTip() { tip.hidden = true; }
    function hoverPath(evt) {
      if (mode === "lattice" || orbiting || panning || !pathHits.length) { hideTip(); return; }
      updateCamera();
      var rect = canvas.getBoundingClientRect();
      var mx = evt.clientX - rect.left;
      var my = evt.clientY - rect.top;
      var best = null;
      var bestD = 14;
      var v = new THREE.Vector3();
      for (var i = 0; i < pathHits.length; i++) {
        var h = pathHits[i];
        v.set(h.x, h.y, h.z).project(camera);
        if (v.z < -1 || v.z > 1) continue;
        var sx = (v.x * 0.5 + 0.5) * rect.width;
        var sy = (-v.y * 0.5 + 0.5) * rect.height;
        var d = Math.hypot(sx - mx, sy - my);
        if (d < bestD) { bestD = d; best = { h: h, sx: sx, sy: sy }; }
      }
      if (!best) { hideTip(); return; }
      var t = best.h.tap || {};
      var order = t.order != null ? t.order : "—";
      tip.hidden = false;
      tip.textContent = (t.is_direct ? "Direct" : ("Image order " + order)) +
        " · mic " + (best.h.mic || "") +
        "\naz " + fmtDeg(t.src_az_deg) + "   el " + fmtDeg(t.src_el_deg) +
        "\n1 kHz " + fmtDb(t.src_db_1k) + "   4 kHz " + fmtDb(t.src_db_4k);
      tip.style.left = Math.round(best.sx + 12) + "px";
      tip.style.top = Math.round(best.sy + 12) + "px";
    }

    function onPointerMove(evt) {
      var dx = evt.clientX - lastPtr.x, dy = evt.clientY - lastPtr.y;
      lastPtr.x = evt.clientX; lastPtr.y = evt.clientY;
      if (orbiting) {
        camSph.theta -= dx * 0.008; camSph.phi -= dy * 0.008;
        updateCamera(); needsRender = true; hideTip(); return;
      }
      if (panning) {
        var forward = new THREE.Vector3(); camera.getWorldDirection(forward);
        var right = new THREE.Vector3().crossVectors(forward, camera.up).normalize();
        var up = new THREE.Vector3().copy(camera.up).normalize();
        var scale = camSph.radius * 0.0018;
        camTarget.addScaledVector(right, -dx * scale);
        camTarget.addScaledVector(up, dy * scale);
        updateCamera(); needsRender = true; hideTip(); return;
      }
      hoverPath(evt);
    }

    function onPointerUp() { orbiting = false; panning = false; canvas.classList.remove("dragging"); }
    canvas.addEventListener("pointerleave", hideTip);
    function onWheel(evt) {
      evt.preventDefault();
      camSph.radius *= evt.deltaY > 0 ? 1.08 : 1 / 1.08;
      updateCamera(); needsRender = true;
    }

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });
    canvas.addEventListener("dblclick", function (evt) {
      evt.preventDefault();
      forceFit();
    });
    canvas.addEventListener("contextmenu", function (e) { e.preventDefault(); });

    function fadePending() {
      var now = nowMs();
      var keys = Object.keys(fadeRows);
      var i;
      for (i = 0; i < keys.length; i++) {
        if (now - fadeRows[keys[i]].t0 < RoomDraw.FADE_MS) return true;
      }
      return false;
    }

    function paintFades() {
      var now = nowMs();
      fadeMats.forEach(function (row) {
        row.mat.opacity = row.base * RoomDraw.gainOf(fadeRows[row.key], now);
      });
    }

    function frame() {
      if (disposed) return;
      raf = requestAnimationFrame(frame);
      var fading = isSplay() && fadePending();
      if (fading) {
        paintFades();
        needsRender = true;
        wasFading = true;
      } else if (wasFading) {
        wasFading = false;
        rebuild();
      }
      if (!needsRender) return;
      needsRender = false;
      resize(); updateCamera();
      renderer.render(scene, camera);
    }
    raf = requestAnimationFrame(frame);

    var ro = null;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(function () { needsRender = true; });
      ro.observe(canvas.parentElement || canvas);
    }

    var api = {
      setMode: function (m) {
        mode = (m === "legs") ? "legs" : (m === "paths" ? "paths" : "lattice");
        rebuild();
      },
      setData: function (d) { data = d; rebuild(); },
      resize: function () {
        resize();
        needsRender = true;
      },
      zoom: function (dir) {
        camSph.radius *= dir < 0 ? 1.08 : (1 / 1.08);
        updateCamera();
        needsRender = true;
      },
      resetCamera: function () { forceFit(); },
      drawnCount: function () { return drawnCount; },
      cameraState: function () {
        var lim = radiusLimits();
        return {
          theta: camSph.theta,
          phi: camSph.phi,
          radius: camSph.radius,
          target: [camTarget.x, camTarget.y, camTarget.z],
          minR: lim.minR,
          maxR: lim.maxR
        };
      },
      dispose: function () {
        disposed = true;
        cancelAnimationFrame(raf);
        if (ro) ro.disconnect();
        clearRoot();
        renderer.dispose();
      }
    };
    global.ImageViews.current = api;
    return api;
  }

  global.ImageViews = { create: create };
})(window);

