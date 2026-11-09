/* 2011 Room Reverb — Lattice toggle and path cycle. Display only. */
(function (global) {
  "use strict";

  var MIC_COLORS = { L: 0xa78bfa, C: 0x60a5fa, R: 0x34d399 };
  var POL_POS = 0x2dd4bf;
  var POL_NEG = 0xf472b6;
  var HOME = 0xfbbf24;
  var SRC = 0xfbbf24;
  var SRC_B = 0xf43f5e;

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
    env.canvas = env.opts.canvas;
    if (!global.THREE) {
      console.warn("Three.js missing — image views disabled");
      return null;
    }
    env.THREE = global.THREE;
    env.getState = env.opts.getState || function () { return global.RRState || null; };

    env.renderer;
    try {
      env.renderer = new env.THREE.WebGLRenderer({ canvas: env.canvas, antialias: true, alpha: false, preserveDrawingBuffer: true });
    } catch (err) {
      console.error("ImageViews WebGLRenderer failed", err);
      throw err;
    }
    env.renderer.setPixelRatio(Math.min(global.devicePixelRatio || 1, 2));
    env.renderer.setClearColor(0x0a0b0e, 1);
    if (env.renderer.outputColorSpace !== undefined) env.renderer.outputColorSpace = env.THREE.SRGBColorSpace;

    env.scene = new env.THREE.Scene();
    env.scene.fog = new env.THREE.Fog(0x0a0b0e, 28, 90);
    env.camera = new env.THREE.PerspectiveCamera(42, 1, 0.05, 400);
    env.camTarget = new env.THREE.Vector3(3, 1.2, 4);
    // Same Z mapping as Floor / room 3D: worldZ = L − z, Front far, Y-up.
    // Orbit is the only camera frame (theta / phi / radius). Pan reads the camera, it does not rebuild it.
    env.camSph = { theta: 0, phi: 1.12, radius: 22 };
    env.fittedRoom = null;
    env.hasFit = false;

    env.scene.add(new env.THREE.AmbientLight(0xb0b8c8, 0.55));
    env.key = new env.THREE.DirectionalLight(0xfff4e6, 0.85); env.key.position.set(8, 14, 6); env.scene.add(env.key);
    env.fill = new env.THREE.DirectionalLight(0x88aaff, 0.25); env.fill.position.set(-10, 4, -8); env.scene.add(env.fill);
    env.rim = new env.THREE.PointLight(0x2dd4bf, 0.4, 60); env.scene.add(env.rim);

    env.root = new env.THREE.Group(); env.scene.add(env.root);
    env.mode = "lattice";
    env.lattice = true;
    env.paths = 0;
    env.order = 0;
    env.mic = "all";
    env.polyFaces = null;
    env.data = null;
    env.fadeRows = {};
    env.fadeMats = [];
    env.roomCache = {};
    env.shownRooms = [];
    env.drawnCount = null;
    env.wasFading = false;

    env.needsRender = true;
    env.disposed = false;
    env.raf = 0;
    env.orbiting = false;
    env.panning = false;
    env.lastPtr = { x: 0, y: 0 };
    env.pathHits = [];
    env.tip = document.createElement("div");
    env.tip.className = "path-tip";
    env.tip.hidden = true;
    if (env.canvas.parentElement) env.canvas.parentElement.appendChild(env.tip);

    /* Paths / last legs: a readable room. Front is z=0 in this view (worldZ of L). */

    /* Chip size. The lattice follows the stored selection. Play audio still clamps 64 and 128 to 32. */

    /* First data, Reset, or a room axis that more than doubles. Sidebar nudges keep the camera. */

    env.canvas.addEventListener("pointerleave", bindPass(env, hideTip));

    env.canvas.addEventListener("pointerdown", bindPass(env, onPointerDown));
    env.canvas.addEventListener("pointermove", bindPass(env, onPointerMove));
    env.canvas.addEventListener("pointerup", bindPass(env, onPointerUp));
    env.canvas.addEventListener("pointercancel", bindPass(env, onPointerUp));
    env.canvas.addEventListener("wheel", bindPass(env, onWheel), { passive: false });
    env.canvas.addEventListener("dblclick", function (evt) {
      evt.preventDefault();
      enter(env, forceFit);
    });
    env.canvas.addEventListener("contextmenu", function (e) { e.preventDefault(); });

    env.raf = requestAnimationFrame(bindPass(env, frame));

    env.ro = null;
    if (typeof ResizeObserver !== "undefined") {
      env.ro = new ResizeObserver(function () { env.needsRender = true; });
      env.ro.observe(env.canvas.parentElement || env.canvas);
    }

    env.api = {
      setMode: function (m) {
        env.lattice = m !== "paths" && m !== "legs";
        env.paths = (m === "paths" || m === "legs") ? 2 : 0;
        env.mode = env.lattice ? "lattice" : "paths";
        enter(env, rebuild);
      },
      setSpace: function (view) {
        view = view || {};
        if (view.lattice != null) env.lattice = !!view.lattice;
        if (view.paths != null) env.paths = view.paths | 0;
        if (view.order != null) env.order = Number(view.order) || 0;
        if (view.mic != null) env.mic = String(view.mic || "all");
        env.mode = env.lattice ? "lattice" : "paths";
        enter(env, rebuild);
      },
      setData: function (d) { env.data = d; enter(env, rebuild); },
      resize: function () {
        enter(env, resize);
        env.needsRender = true;
      },
      zoom: function (dir) {
        env.camSph.radius *= dir < 0 ? 1.08 : (1 / 1.08);
        enter(env, updateCamera);
        env.needsRender = true;
      },
      resetCamera: function () { enter(env, forceFit); },
      drawnCount: function () { return env.drawnCount; },
      tapCount: function () { return enter(env, isPoly) ? enter(env, hadamardShown) : null; },
      cameraState: function () {
        var lim = enter(env, radiusLimits);
        return {
          theta: env.camSph.theta,
          phi: env.camSph.phi,
          radius: env.camSph.radius,
          target: [env.camTarget.x, env.camTarget.y, env.camTarget.z],
          minR: lim.minR,
          maxR: lim.maxR
        };
      },
      dispose: function () {
        env.disposed = true;
        cancelAnimationFrame(env.raf);
        if (env.ro) env.ro.disconnect();
        enter(env, clearRoot);
        env.renderer.dispose();
      }
    };
    global.ImageViews.current = env.api;
    return env.api;
  }
  function worldZ(z, L) { var env = envStack[envStack.length - 1];
      return L - z;
    }
  function mapPt(p, L) { var env = envStack[envStack.length - 1];
      if (!p) return p;
      if (typeof p.z === "number") return { x: p.x, y: p.y, z: worldZ(p.z, L) };
      if (Array.isArray(p) && p.length >= 3) {
        return { x: p[0], y: p[1], z: worldZ(p[2], L) };
      }
      return p;
    }
  function mapCell(min, max, L) { var env = envStack[envStack.length - 1];
      var z0 = worldZ(min.z, L);
      var z1 = worldZ(max.z, L);
      return {
        min: { x: min.x, y: min.y, z: Math.min(z0, z1) },
        max: { x: max.x, y: max.y, z: Math.max(z0, z1) }
      };
    }
  function sceneState() { var env = envStack[envStack.length - 1];
      return env.getState() || null;
    }
  function isPoly() { var env = envStack[envStack.length - 1];
      return !!(global.RoomDraw && RoomDraw.normalize(sceneState() && sceneState().room_shape) !== "box");
    }
  function polyShape() { var env = envStack[envStack.length - 1];
      return global.RoomDraw ? RoomDraw.normalize(sceneState() && sceneState().room_shape) : "box";
    }
  function nowMs() { var env = envStack[envStack.length - 1];
      return (global.performance && performance.now) ? performance.now() : Date.now();
    }
  function clearRoot() { var env = envStack[envStack.length - 1];
      while (env.root.children.length) {
        var ch = env.root.children[0];
        env.root.remove(ch);
        ch.traverse(function (o) {
          if (o.geometry) o.geometry.dispose();
          if (o.material) {
            if (Array.isArray(o.material)) o.material.forEach(function (m) { m.dispose(); });
            else o.material.dispose();
          }
        });
      }
    }
  function boxEdges(min, max, color, opacity) { var env = envStack[envStack.length - 1];
      var built = RoomDraw.cellEdges(env.THREE, min, max);
      var mat = new env.THREE.LineBasicMaterial({ color: color, transparent: true, opacity: opacity == null ? 0.45 : opacity });
      var line = new env.THREE.LineSegments(built.geo, mat);
      line.position.set(built.pos[0], built.pos[1], built.pos[2]);
      return line;
    }
  function marker(color, r) { var env = envStack[envStack.length - 1];
      return new env.THREE.Mesh(
        new env.THREE.SphereGeometry(r || 0.12, 16, 12),
        new env.THREE.MeshStandardMaterial({ color: color, emissive: color, emissiveIntensity: 0.35, roughness: 0.4, metalness: 0.2 })
      );
    }
  function linePts(pts, color, opacity) { var env = envStack[envStack.length - 1];
      var L = (env.data && env.data.room) ? env.data.room.L : 0;
      var arr = [];
      for (var i = 0; i < pts.length; i++) {
        var q = mapPt(pts[i], L);
        arr.push(new env.THREE.Vector3(q.x, q.y, q.z));
      }
      var geo = new env.THREE.BufferGeometry().setFromPoints(arr);
      var mat = new env.THREE.LineBasicMaterial({ color: color, transparent: true, opacity: opacity == null ? 0.85 : opacity });
      return new env.THREE.Line(geo, mat);
    }
  function makeLabel(text, color) { var env = envStack[envStack.length - 1];
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
      var tex = new env.THREE.CanvasTexture(c);
      var spr = new env.THREE.Sprite(new env.THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
      spr.scale.set(1.1, 0.33, 1);
      return spr;
    }
  function homeBox(room) { var env = envStack[envStack.length - 1];
      return boxEdges({ x: 0, y: 0, z: 0 }, { x: room.W, y: room.H, z: room.L }, HOME, 0.95);
    }
  function addRoomShell(room) { var env = envStack[envStack.length - 1];
      if (isPoly()) { addSplayShell(room); return; }
      env.root.add(homeBox(room));
      var built = RoomDraw.imageBoxGeometries(env.THREE, room.W, room.H, room.L);
      built.home.geo.dispose();
      var floor = RoomDraw.placePart(env.THREE, built.floor, new env.THREE.MeshStandardMaterial({
        color: 0x2a3142, roughness: 0.86, metalness: 0.04
      }));
      env.root.add(floor);
      var wallMat = new env.THREE.MeshBasicMaterial({
        color: 0x9aa3b8, transparent: true, opacity: 0.07,
        side: env.THREE.DoubleSide, depthWrite: false
      });
      ["z0", "zL", "x0", "xW", "ceil"].forEach(function (name) {
        env.root.add(RoomDraw.placePart(env.THREE, built[name], wallMat));
      });
      function tag(text, x, y, z) {
        var spr = makeLabel(text, "#c5cad6");
        spr.position.set(x, y, z);
        env.root.add(spr);
      }
      var ly = Math.max(0.4, room.H * 0.62);
      tag("A Left", 0.05, ly, room.L * 0.5);
      tag("B Front", room.W * 0.5, ly, 0.05);
      tag("C Right", room.W - 0.05, ly, room.L * 0.5);
      tag("D Back", room.W * 0.5, ly, room.L - 0.05);
      tag("E Floor", room.W * 0.5, 0.28, room.L * 0.35);
      tag("F Ceiling", room.W * 0.5, Math.max(0.5, room.H - 0.2), room.L * 0.65);
    }
  function addActors(source, mics, selected) { var env = envStack[envStack.length - 1];
      var L = (env.data && env.data.room) ? env.data.room.L : 0;
      var s = marker(SRC, 0.14);
      s.position.set(source.x, source.y, worldZ(source.z, L)); env.root.add(s);
      var sLab = makeLabel(env.data && env.data.source_b ? "A" : "Src", "#fbbf24");
      sLab.position.set(source.x, source.y + 0.35, worldZ(source.z, L)); env.root.add(sLab);
      if (env.data && env.data.source_b) {
        var b = env.data.source_b;
        var bm = marker(SRC_B, 0.13);
        bm.position.set(b.x, b.y, worldZ(b.z, L)); env.root.add(bm);
        var bLab = makeLabel("B", "#f43f5e");
        bLab.position.set(b.x, b.y + 0.35, worldZ(b.z, L)); env.root.add(bLab);
      }
      ["L", "C", "R"].forEach(function (id) {
        if (selected.indexOf(id) < 0 && env.mode !== "lattice") return;
        var m = mics[id]; if (!m) return;
        var mesh = enter(env, marker, MIC_COLORS[id], id === "C" ? 0.11 : 0.09);
        mesh.position.set(m.x, m.y, enter(env, worldZ, m.z, L)); env.root.add(mesh);
        if (selected.indexOf(id) >= 0) {
          var col = id === "L" ? "#a78bfa" : id === "R" ? "#34d399" : "#60a5fa";
          var lab = enter(env, makeLabel, id, col);
          lab.position.set(m.x, m.y + 0.32, enter(env, worldZ, m.z, L)); env.root.add(lab);
        }
      });
    }
  function addWallLabels(room) { var env = envStack[envStack.length - 1];
      var ly = room.H * 0.55;
      var f = makeLabel("Front", "#2dd4bf");
      f.position.set(room.W * 0.5, ly, worldZ(room.L, room.L));
      env.root.add(f);
      var b = makeLabel("Back", "#fb7185");
      b.position.set(room.W * 0.5, ly, worldZ(0, room.L));
      env.root.add(b);
    }
  function mapRing(ring, L) { var env = envStack[envStack.length - 1];
      return ring.map(function (p) { return [p[0], p[1], enter(env, worldZ, p[2], L)]; });
    }
  function ringLine(ring, color, opacity) { var env = envStack[envStack.length - 1];
      var pts = ring.map(function (p) { return new env.THREE.Vector3(p[0], p[1], p[2]); });
      pts.push(pts[0].clone());
      var mat = new env.THREE.LineBasicMaterial({ color: color, transparent: true, opacity: opacity });
      return { line: new env.THREE.Line(new env.THREE.BufferGeometry().setFromPoints(pts), mat), mat: mat };
    }
  function polyFill(ring, color, opacity) { var env = envStack[envStack.length - 1];
      var positions = [];
      var i;
      for (i = 1; i < ring.length - 1; i++) {
        positions.push(ring[0][0], ring[0][1], ring[0][2]);
        positions.push(ring[i][0], ring[i][1], ring[i][2]);
        positions.push(ring[i + 1][0], ring[i + 1][1], ring[i + 1][2]);
      }
      var geo = new env.THREE.BufferGeometry();
      geo.setAttribute("position", new env.THREE.Float32BufferAttribute(positions, 3));
      geo.computeVertexNormals();
      var mat = new env.THREE.MeshStandardMaterial({
        color: color, roughness: 0.9, metalness: 0.04,
        transparent: opacity < 1, opacity: opacity, side: env.THREE.DoubleSide, depthWrite: opacity >= 1
      });
      return new env.THREE.Mesh(geo, mat);
    }
  function splayReceivers() { var env = envStack[envStack.length - 1];
      var selected = (env.data && env.data.selected_mics) || ["C"];
      var out = [];
      selected.forEach(function (id) {
        var m = env.data.mics && env.data.mics[id];
        if (!m) return;
        out.push({ id: id, p: [m.x, m.y, m.z] });
      });
      return { selected: selected, receivers: out };
    }
  function hadamardShown() { var env = envStack[envStack.length - 1];
      var n = 32;
      if (env.data && env.data.hadamard_n != null && env.data.hadamard_n !== "") n = Number(env.data.hadamard_n);
      else {
        var st = sceneState();
        if (st && st.hadamard_n != null) n = Number(st.hadamard_n);
      }
      if (n !== 8 && n !== 16 && n !== 32 && n !== 64 && n !== 128) n = 32;
      return n;
    }
  function standPoint() { var env = envStack[envStack.length - 1];
      var st = sceneState() || {};
      var room = env.data.room;
      var x = Number(st.mcx);
      var y = Number(st.my);
      var z = Number(st.mcz);
      if (!isFinite(x)) x = room.W * 0.5;
      if (!isFinite(y)) y = room.H * 0.5;
      if (!isFinite(z)) z = room.L * 0.5;
      return [x, y, z];
    }
  function takeSplay() { var env = envStack[envStack.length - 1];
      var room = env.data.room;
      var ear = splayReceivers();
      var cap = (env.data.c || 340) * 1;
      var nTap = hadamardShown();
      var stand = standPoint();
      var packs = [];
      env.shownRooms = [];
      function one(prefix, source) {
        var pack = RoomDraw.imageRooms(polyShape(), room.W, room.H, room.L, source, ear.receivers, {
          order: 4, maxDist: cap, n: nTap, stand: stand
        });
        (pack.rooms || []).forEach(function (r) {
          var key = prefix + ":" + r.key;
          env.roomCache[key] = r;
          env.shownRooms.push({ prefix: prefix, key: key, rec: r });
        });
        packs.push({ prefix: prefix, pack: pack });
      }
      one("a", [env.data.source.x, env.data.source.y, env.data.source.z]);
      if (env.data.source_b) one("b", [env.data.source_b.x, env.data.source_b.y, env.data.source_b.z]);
      env.polyFaces = (packs[0] && packs[0].pack && packs[0].pack.faces) || [];
      var keys = env.shownRooms.map(function (row) { return row.key; });
      var now = nowMs();
      env.fadeRows = RoomDraw.stepFade(env.fadeRows, RoomDraw.latticeKeys(env.mode, keys), now);
      Object.keys(env.roomCache).forEach(function (k) {
        if (!env.fadeRows[k] && env.shownRooms.every(function (row) { return row.key !== k; })) delete env.roomCache[k];
      });
      env.drawnCount = (packs[0] && packs[0].pack.rooms) ? packs[0].pack.rooms.length : 0;
      return { packs: packs, now: now, selected: ear.selected, surfaces: (sceneState() || {}).surfaces };
    }
  function trackFade(mat, key, base) { var env = envStack[envStack.length - 1];
      env.fadeMats.push({ mat: mat, key: key, base: base });
      var row = env.fadeRows[key];
      mat.opacity = base * RoomDraw.gainOf(row, nowMs());
    }
  function addMirroredRooms(wireOnly) { var env = envStack[envStack.length - 1];
      env.fadeMats = [];
      var got = takeSplay();
      var room = env.data.room;
      Object.keys(env.fadeRows).forEach(function (key) {
        /* Lattice off keeps the home shell. */
        if (env.mode !== "lattice" && key !== "a:home") return;
        var rec = env.roomCache[key];
        if (!rec) return;
        var force = key.charAt(0) === "b" ? SRC_B : null;
        var col = force != null ? force : (rec.order % 2 === 0 ? (rec.key === "home" ? HOME : POL_POS) : POL_NEG);
        if (rec.key === "home" && force == null) col = HOME;
        var base = rec.key === "home" ? 0.95 : (force != null ? 0.22 : 0.32);
        rec.rings.forEach(function (ring) {
          var drawn = enter(env, ringLine, enter(env, mapRing, ring, room.L), col, base);
          enter(env, trackFade, drawn.mat, key, base);
          env.root.add(drawn.line);
        });
        if (!wireOnly && rec.key === "home") {
          var faces = got.packs[0].pack.faces;
          faces.forEach(function (face, i) {
            var opacity = face.letter === "E" ? 1 : (face.letter === "F" ? 0.22 : 0.45);
            var mesh = enter(env, polyFill, enter(env, mapRing, rec.rings[i], room.L), RoomDraw.wallColor(got.surfaces, face.letter), opacity);
            env.root.add(mesh);
          });
        }
        if (rec.key !== "home") {
          var p = enter(env, mapPt, { x: rec.pos[0], y: rec.pos[1], z: rec.pos[2] }, room.L);
          var mark = enter(env, marker, col, 0.08);
          mark.position.set(p.x, p.y, p.z);
          env.root.add(mark);
        }
      });
      return got;
    }
  function addSplayShell(room) { var env = envStack[envStack.length - 1];
      var got = addMirroredRooms(false);
      var faces = got.packs[0].pack.faces;
      var names = { A: ["A Left", "#38bdf8"], B: ["B Front", "#2dd4bf"], C: ["C Right", "#a78bfa"], D: ["D Back", "#fb7185"], E: ["E Floor", "#78716c"], F: ["F Ceiling", "#e2e8f0"] };
      faces.forEach(function (face) {
        var named = names[face.letter];
        if (!named) return;
        var c = [0, 0, 0];
        face.v.forEach(function (p) { c[0] += p[0]; c[1] += p[1]; c[2] += p[2]; });
        var n = face.v.length || 1;
        var tp = enter(env, mapPt, { x: c[0] / n, y: c[1] / n, z: c[2] / n }, room.L);
        var spr = enter(env, makeLabel, named[0], named[1]);
        spr.position.set(tp.x, tp.y, tp.z);
        env.root.add(spr);
      });
    }
  function perMicTaps(d, micId) { var env = envStack[envStack.length - 1];
      var pm = (d && (d.per_mic || d.by_mic || d.paths_by_mic)) || {};
      return pm[micId] || [];
    }
  function imageXyz(im) { var env = envStack[envStack.length - 1];
      if (!im) return null;
      return im.image_xyz || im.xyz || im.pos || im.position || null;
    }
  function cellBounds(im) { var env = envStack[envStack.length - 1];
      var cell = (im && (im.cell || im.bounds)) || {};
      var mn = cell.min || cell.lo || cell.lower;
      var mx = cell.max || cell.hi || cell.upper;
      return (mn && mx) ? { min: mn, max: mx } : null;
    }
  function roomSpan(room) { var env = envStack[envStack.length - 1];
      return Math.max(room.W, room.H, room.L);
    }
  function roomDiag(room) { var env = envStack[envStack.length - 1];
      return Math.sqrt(room.W * room.W + room.H * room.H + room.L * room.L);
    }
  function latticeFitRadius(room) { var env = envStack[envStack.length - 1];
      return Math.max(14, roomSpan(room) * 3.2 * 1.05);
    }
  function radiusLimits() { var env = envStack[envStack.length - 1];
      var room = env.data && env.data.room;
      if (!room) return { minR: 2.5, maxR: 120 };
      var minR = 0.2 * roomDiag(room);
      var maxR = (env.mode === "lattice") ? (3 * latticeFitRadius(room)) : (8 * roomSpan(room));
      if (!(maxR > minR)) maxR = minR * 4;
      return { minR: minR, maxR: maxR };
    }
  function roomScaleJump(room) { var env = envStack[envStack.length - 1];
      if (!env.fittedRoom) return true;
      function ratio(a, b) {
        var lo = Math.min(Math.abs(a), Math.abs(b));
        var hi = Math.max(Math.abs(a), Math.abs(b));
        if (lo < 1e-9) return hi > 1e-9 ? Infinity : 1;
        return hi / lo;
      }
      return ratio(room.W, env.fittedRoom.W) > 2
        || ratio(room.H, env.fittedRoom.H) > 2
        || ratio(room.L, env.fittedRoom.L) > 2;
    }
  function fitCamera(lattice) { var env = envStack[envStack.length - 1];
      if (!env.data || !env.data.room) return;
      var room = env.data.room;
      env.camTarget.set(room.W * 0.5, room.H * 0.4, room.L * 0.5);
      if (lattice) {
        env.camSph.radius = latticeFitRadius(room);
        env.camSph.theta = 0; env.camSph.phi = 0.42;
      } else {
        env.camSph.radius = Math.max(8, roomDiag(room) * 1.25);
        /* Three-quarter view: see the floor and two walls, not a front-on camera. */
        env.camSph.theta = 0.78; env.camSph.phi = 0.92;
      }
      env.fittedRoom = { W: room.W, H: room.H, L: room.L };
      env.hasFit = true;
      env.rim.position.set(room.W * 0.5, room.H * 0.7, room.L * 0.5);
      updateCamera();
    }
  function fitIfNeeded(lattice) { var env = envStack[envStack.length - 1];
      if (!env.data || !env.data.room) return;
      if (env.hasFit && !roomScaleJump(env.data.room)) return;
      fitCamera(lattice);
    }
  function forceFit() { var env = envStack[envStack.length - 1];
      env.hasFit = false;
      env.fittedRoom = null;
      fitCamera(env.mode === "lattice");
    }
  function updateCamera() { var env = envStack[envStack.length - 1];
      var s = env.camSph;
      var lim = radiusLimits();
      s.phi = Math.max(0.08, Math.min(Math.PI / 2, s.phi));
      s.radius = Math.max(lim.minR, Math.min(lim.maxR, s.radius));
      env.camera.up.set(0, 1, 0);
      var sinPhi = Math.sin(s.phi);
      env.camera.position.set(
        env.camTarget.x + s.radius * sinPhi * Math.sin(s.theta),
        env.camTarget.y + s.radius * Math.cos(s.phi),
        env.camTarget.z + s.radius * sinPhi * Math.cos(s.theta)
      );
      env.camera.lookAt(env.camTarget);
      env.camera.near = Math.max(0.02, Math.min(1.0, s.radius * 0.002));
      env.camera.far = Math.max(4 * s.radius, env.camera.near * 8);
      env.camera.updateProjectionMatrix();
      if (env.scene.fog) {
        env.scene.fog.near = 0.9 * s.radius;
        env.scene.fog.far = 3 * s.radius;
      }
    }
  function buildLattice() { var env = envStack[envStack.length - 1];
      env.pathHits = [];
      hideTip();
      if (!env.data) return;
      clearRoot();
      if (isPoly()) {
        addMirroredRooms(true);
        addWallLabels(env.data.room);
        addActors(env.data.source, env.data.mics, env.data.selected_mics || ["C"]);
        fitIfNeeded(true);
        return;
      }
      env.drawnCount = null;
      env.fadeRows = {};
      env.fadeMats = [];
      env.roomCache = {};
      var room = env.data.room;
      env.root.add(homeBox(room));
      var grid = new env.THREE.GridHelper(Math.max(room.W, room.L), 8, 0x3a4155, 0x222833);
      grid.position.set(room.W * 0.5, 0.01, room.L * 0.5);
      grid.scale.set(room.W / Math.max(room.W, room.L), 1, room.L / Math.max(room.W, room.L));
      env.root.add(grid);
      function addLattice(list, force) {
        (list || []).forEach(function (im) {
          var col = force != null ? force : (im.is_home ? HOME : (im.polarity > 0 ? POL_POS : POL_NEG));
          var op = force != null ? (im.is_home ? 0.8 : 0.22) : (im.is_home ? 0.95 : 0.32);
          var cb = enter(env, cellBounds, im);
          if (cb) {
            var mapped = enter(env, mapCell, cb.min, cb.max, room.L);
            env.root.add(enter(env, boxEdges, mapped.min, mapped.max, col, op));
          }
          var xyz = enter(env, imageXyz, im);
          if (xyz) {
            var m = enter(env, marker, col, im.is_home ? 0.1 : 0.08);
            var p = enter(env, mapPt, xyz, room.L);
            m.position.set(p.x, p.y, p.z);
            env.root.add(m);
          }
        });
      }
      addLattice(env.data.lattice || env.data.images || []);
      if (env.data.lattice_b) addLattice(env.data.lattice_b, SRC_B);
      addWallLabels(room);
      addActors(env.data.source, env.data.mics, env.data.selected_mics || ["C"]);
      fitIfNeeded(true);
    }
  function rememberHit(tap, pts, micId) { var env = envStack[envStack.length - 1];
      var L = (env.data && env.data.room) ? env.data.room.L : 0;
      (pts || []).forEach(function (pt) {
        var q = enter(env, mapPt, pt, L);
        if (!q || typeof q.x !== "number") return;
        env.pathHits.push({ x: q.x, y: q.y, z: q.z, tap: tap, mic: micId });
      });
    }
  function pathMicIds() { var env = envStack[envStack.length - 1];
      var selected = (env.data && env.data.selected_mics) || ["C"];
      if (!global.RoomDraw || !RoomDraw.pathMics) return selected;
      return RoomDraw.pathMics(selected, env.mic);
    }
  function tapOn(t) { var env = envStack[envStack.length - 1];
      if (!global.RoomDraw || !RoomDraw.orderShown) return true;
      var st = sceneState() || {};
      if (!RoomDraw.orderShown(t && t.order, env.order, !!(t && t.is_direct))) return false;
      return RoomDraw.surfaceShown(t && t.hit_surfaces, st.surfaces_solo, st.surfaces_mute);
    }
  function levelOpacity(dist, isDirect, dim) { var env = envStack[envStack.length - 1];
      var op = (global.RoomDraw && RoomDraw.pathOpacity) ? RoomDraw.pathOpacity(dist, isDirect) : (isDirect ? 0.95 : 0.45);
      if (dim && !isDirect) op *= 0.75;
      return op;
    }
  function coord(p, name, index) { var env = envStack[envStack.length - 1];
      if (p == null) return 0;
      if (typeof p[name] === "number") return p[name];
      if (Array.isArray(p) || typeof p[index] === "number") return Number(p[index]) || 0;
      return 0;
    }
  function dist3(a, b) { var env = envStack[envStack.length - 1];
      var dx = coord(a, "x", 0) - coord(b, "x", 0);
      var dy = coord(a, "y", 1) - coord(b, "y", 1);
      var dz = coord(a, "z", 2) - coord(b, "z", 2);
      return Math.sqrt(dx * dx + dy * dy + dz * dz);
    }
  function lettersOf(rec) { var env = envStack[envStack.length - 1];
      var faces = env.polyFaces || [];
      var out = [];
      var seq = (rec && rec.seq) || [];
      var i;
      for (i = 0; i < seq.length; i++) {
        var face = faces[seq[i]];
        var letter = face && face.letter;
        if (!letter || out.indexOf(letter) >= 0) continue;
        out.push(letter);
      }
      return out;
    }
  function polyTap(rec, mic, letters) { var env = envStack[envStack.length - 1];
      var d = dist3(rec.pos, mic);
      var c = (env.data && env.data.c) || 340;
      return {
        order: rec.order,
        is_direct: !rec.order,
        delay_ms: (d / c) * 1000,
        dist_m: d,
        hit_surfaces: letters
      };
    }
  function micPoint(mic) { var env = envStack[envStack.length - 1];
      return { x: mic.x, y: mic.y, z: mic.z };
    }
  function hitFaces() { var env = envStack[envStack.length - 1];
      if (env.hitFaces) return env.hitFaces;
      var room = env.data && env.data.room;
      env.hitFaces = [];
      if (!room || !global.RoomDraw || !RoomDraw.polyFaces) return env.hitFaces;
      env.hitFaces = RoomDraw.polyFaces(polyShape(), room.W, room.H, room.L) || [];
      return env.hitFaces;
    }
  function faceForHit(p) { var env = envStack[envStack.length - 1];
      var faces = hitFaces();
      var x = [coord(p, "x", 0), coord(p, "y", 1), coord(p, "z", 2)];
      var best = null;
      var bestD = Infinity;
      var i;
      for (i = 0; i < faces.length; i++) {
        var sd = Math.abs(faces[i].sd(x));
        if (sd < bestD) { bestD = sd; best = faces[i]; }
      }
      return best;
    }
  /* Flat disc in the plane of the hit. CircleGeometry faces +Z. */
  function discMark(p, col, op) { var env = envStack[envStack.length - 1];
      var room = env.data.room;
      var face = faceForHit(p);
      var n = face ? face.n : [0, 1, 0];
      var vn = new env.THREE.Vector3(n[0], n[1], -n[2]);
      if (vn.lengthSq() < 1e-8) vn.set(0, 1, 0);
      vn.normalize();
      var tp = mapPt(p, room.L);
      var mark = new env.THREE.Mesh(
        new env.THREE.CircleGeometry(0.06, 20),
        new env.THREE.MeshBasicMaterial({
          color: col, transparent: true, opacity: op,
          side: env.THREE.DoubleSide, depthWrite: false
        })
      );
      mark.position.set(tp.x, tp.y, tp.z);
      mark.quaternion.setFromUnitVectors(new env.THREE.Vector3(0, 0, 1), vn);
      mark.position.addScaledVector(vn, 0.012);
      return mark;
    }
  /* Interior vertices are the surface meetings. Ends are source and mic. */
  function surfaceMarks(pts, col, op) { var env = envStack[envStack.length - 1];
      if (!pts || pts.length < 3) return;
      var i;
      for (i = 1; i < pts.length - 1; i++) {
        env.root.add(enter(env, discMark, pts[i], col, op));
      }
    }
  function addHemis(selected) { var env = envStack[envStack.length - 1];
      var room = env.data.room;
      selected.forEach(function (micId) {
        var mic = env.data.mics && env.data.mics[micId];
        if (!mic) return;
        var hemi = new env.THREE.Mesh(
          new env.THREE.SphereGeometry(0.55, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.5),
          new env.THREE.MeshBasicMaterial({ color: MIC_COLORS[micId], transparent: true, opacity: 0.08, side: env.THREE.DoubleSide, depthWrite: false })
        );
        hemi.position.set(mic.x, mic.y, worldZ(mic.z, room.L));
        env.root.add(hemi);
      });
    }
  function addTapPaths(taps, force, micId, mic, folded) { var env = envStack[envStack.length - 1];
      (taps || []).forEach(function (t) {
        if (!tapOn(t)) return;
        var col = force != null ? force : (t.is_direct ? SRC : (t.polarity > 0 ? POL_POS : POL_NEG));
        var op = levelOpacity(t.dist_m, t.is_direct, force != null);
        if (!folded) {
          var xyz = imageXyz(t);
          if (!xyz || !mic) return;
          var ray = [xyz, micPoint(mic)];
          env.root.add(enter(env, linePts, ray, col, op));
          enter(env, rememberHit, t, ray, micId);
          enter(env, surfaceMarks, t.path, col, op);
          return;
        }
        if (!t.path || t.path.length < 2) return;
        env.root.add(enter(env, linePts, t.path, col, op));
        enter(env, rememberHit, t, t.path, micId);
        enter(env, surfaceMarks, t.path, col, op);
      });
    }
  function addPolyPaths(selected, folded) { var env = envStack[envStack.length - 1];
      selected.forEach(function (micId) {
        var mic = env.data.mics && env.data.mics[micId];
        if (!mic) return;
        (env.shownRooms || []).forEach(function (row) {
          var rec = row.rec;
          if (!rec) return;
          var letters = enter(env, lettersOf, rec);
          var tap = enter(env, polyTap, rec, mic, letters);
          if (!tapOn(tap)) return;
          var force = row.prefix === "b";
          var col = force ? SRC_B : (rec.key === "home" ? SRC : (rec.order % 2 === 0 ? POL_POS : POL_NEG));
          var op = levelOpacity(tap.dist_m, tap.is_direct, force);
          if (!folded) {
            var ray = [rec.pos, micPoint(mic)];
            env.root.add(enter(env, linePts, ray, col, op));
            enter(env, rememberHit, tap, ray, micId);
            var heardRay = rec.heard && rec.heard[micId];
            if (heardRay) enter(env, surfaceMarks, heardRay, col, op);
            return;
          }
          var path = rec.heard && rec.heard[micId];
          if (!path || path.length < 2) return;
          var pts = path.map(function (p) { return { x: p[0], y: p[1], z: p[2] }; });
          env.root.add(enter(env, linePts, pts, col, op));
          enter(env, rememberHit, tap, pts, micId);
          enter(env, surfaceMarks, pts, col, op);
        });
      });
    }
  function addPathLayer() { var env = envStack[envStack.length - 1];
      if (!env.data || !env.paths) return;
      var selected = pathMicIds();
      var folded = env.paths === 2;
      if (isPoly()) {
        addPolyPaths(selected, folded);
        if (folded) addHemis(selected);
        return;
      }
      selected.forEach(function (micId) {
        var mic = env.data.mics && env.data.mics[micId];
        addTapPaths(enter(env, perMicTaps, env.data, micId), null, micId, mic, folded);
        if (env.data.per_mic_b) addTapPaths(env.data.per_mic_b[micId] || [], SRC_B, micId, mic, folded);
      });
      if (folded) addHemis(selected);
    }
  function buildHome() { var env = envStack[envStack.length - 1];
      env.pathHits = [];
      hideTip();
      if (!env.data) return;
      clearRoot();
      env.drawnCount = null;
      addRoomShell(env.data.room);
      addActors(env.data.source, env.data.mics, env.data.selected_mics || ["C"]);
      fitIfNeeded(false);
    }
  function rebuild() { var env = envStack[envStack.length - 1];
      env.mode = env.lattice === false ? "paths" : "lattice";
      env.hitFaces = null;
      if (!env.data) { env.needsRender = true; return; }
      if (env.mode === "lattice") buildLattice();
      else buildHome();
      if (env.paths) addPathLayer();
      env.needsRender = true;
    }
  function resize() { var env = envStack[envStack.length - 1];
      var rect = env.canvas.getBoundingClientRect();
      var cssW = Math.floor(rect.width);
      var cssH = Math.floor(rect.height);
      /* Skip while panel is hidden / layout not ready — avoid bogus 0×0→2×2 context. */
      if (cssW < 2 || cssH < 2) return;
      var pr = Math.min(global.devicePixelRatio || 1, 2);
      if (env.canvas.width !== cssW * pr || env.canvas.height !== cssH * pr) env.renderer.setSize(cssW, cssH, false);
      env.camera.aspect = cssW / Math.max(1, cssH);
      env.camera.updateProjectionMatrix();
      env.needsRender = true;
    }
  function onPointerDown(evt) { var env = envStack[envStack.length - 1];
      env.lastPtr.x = evt.clientX; env.lastPtr.y = evt.clientY;
      var pan = evt.button === 2 || (evt.button === 0 && evt.shiftKey);
      var orbit = evt.button === 1 || (evt.button === 0 && !evt.shiftKey);
      if (!pan && !orbit) return;
      env.panning = pan;
      env.orbiting = orbit;
      env.canvas.classList.add("dragging");
      try { env.canvas.setPointerCapture(evt.pointerId); } catch (e) {}
      evt.preventDefault();
    }
  function hideTip() { var env = envStack[envStack.length - 1]; env.tip.hidden = true; }
  function hoverPath(evt) { var env = envStack[envStack.length - 1];
      if (!env.paths || env.orbiting || env.panning || !env.pathHits.length) { hideTip(); return; }
      updateCamera();
      var rect = env.canvas.getBoundingClientRect();
      var mx = evt.clientX - rect.left;
      var my = evt.clientY - rect.top;
      var best = null;
      var bestD = 14;
      var v = new env.THREE.Vector3();
      for (var i = 0; i < env.pathHits.length; i++) {
        var h = env.pathHits[i];
        v.set(h.x, h.y, h.z).project(env.camera);
        if (v.z < -1 || v.z > 1) continue;
        var sx = (v.x * 0.5 + 0.5) * rect.width;
        var sy = (-v.y * 0.5 + 0.5) * rect.height;
        var d = Math.hypot(sx - mx, sy - my);
        if (d < bestD) { bestD = d; best = { h: h, sx: sx, sy: sy }; }
      }
      if (!best) { hideTip(); return; }
      var t = best.h.tap || {};
      t.mic = best.h.mic || t.mic;
      env.tip.hidden = false;
      env.tip.textContent = (global.RoomDraw && RoomDraw.pathHover) ? RoomDraw.pathHover(t) : "";
      env.tip.style.left = Math.round(best.sx + 12) + "px";
      env.tip.style.top = Math.round(best.sy + 12) + "px";
    }
  function onPointerMove(evt) { var env = envStack[envStack.length - 1];
      var dx = evt.clientX - env.lastPtr.x, dy = evt.clientY - env.lastPtr.y;
      env.lastPtr.x = evt.clientX; env.lastPtr.y = evt.clientY;
      if (env.orbiting) {
        env.camSph.theta -= dx * 0.008; env.camSph.phi -= dy * 0.008;
        updateCamera(); env.needsRender = true; hideTip(); return;
      }
      if (env.panning) {
        var forward = new env.THREE.Vector3(); env.camera.getWorldDirection(forward);
        var right = new env.THREE.Vector3().crossVectors(forward, env.camera.up).normalize();
        var up = new env.THREE.Vector3().copy(env.camera.up).normalize();
        var scale = env.camSph.radius * 0.0018;
        env.camTarget.addScaledVector(right, -dx * scale);
        env.camTarget.addScaledVector(up, dy * scale);
        updateCamera(); env.needsRender = true; hideTip(); return;
      }
      hoverPath(evt);
    }
  function onPointerUp() { var env = envStack[envStack.length - 1]; env.orbiting = false; env.panning = false; env.canvas.classList.remove("dragging"); }
  function onWheel(evt) { var env = envStack[envStack.length - 1];
      evt.preventDefault();
      env.camSph.radius *= evt.deltaY > 0 ? 1.08 : 1 / 1.08;
      updateCamera(); env.needsRender = true;
    }
  function fadePending() { var env = envStack[envStack.length - 1];
      var now = nowMs();
      var keys = Object.keys(env.fadeRows);
      var i;
      for (i = 0; i < keys.length; i++) {
        if (now - env.fadeRows[keys[i]].t0 < RoomDraw.FADE_MS) return true;
      }
      return false;
    }
  function paintFades() { var env = envStack[envStack.length - 1];
      var now = nowMs();
      env.fadeMats.forEach(function (row) {
        row.mat.opacity = row.base * RoomDraw.gainOf(env.fadeRows[row.key], now);
      });
    }
  function frame() { var env = envStack[envStack.length - 1];
      if (env.disposed) return;
      env.raf = requestAnimationFrame(bindPass(env, frame));
      var fading = isPoly() && fadePending();
      if (fading) {
        paintFades();
        env.needsRender = true;
        env.wasFading = true;
      } else if (env.wasFading) {
        env.wasFading = false;
        rebuild();
      }
      if (!env.needsRender) return;
      env.needsRender = false;
      resize(); updateCamera();
      env.renderer.render(env.scene, env.camera);
    }

  global.ImageViews = { create: create };
})(window);

