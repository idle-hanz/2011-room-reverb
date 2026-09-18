/* 2011 Room Reverb — Lattice / In-room paths / Last-legs */
(function (global) {
  "use strict";

  var MIC_COLORS = { L: 0xa78bfa, C: 0x60a5fa, R: 0x34d399 };
  var POL_POS = 0x2dd4bf;
  var POL_NEG = 0xf472b6;
  var HOME = 0xfbbf24;
  var SRC = 0xfbbf24;

  function create(opts) {
    var canvas = opts.canvas;
    if (!global.THREE) {
      console.warn("Three.js missing — image views disabled");
      return null;
    }
    var THREE = global.THREE;

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
    var camSph = { theta: 0.95, phi: 1.05, radius: 22 };

    scene.add(new THREE.AmbientLight(0xb0b8c8, 0.55));
    var key = new THREE.DirectionalLight(0xfff4e6, 0.85); key.position.set(8, 14, 6); scene.add(key);
    var fill = new THREE.DirectionalLight(0x88aaff, 0.25); fill.position.set(-10, 4, -8); scene.add(fill);
    var rim = new THREE.PointLight(0x2dd4bf, 0.4, 60); scene.add(rim);

    var root = new THREE.Group(); scene.add(root);
    var mode = "lattice";
    var data = null;
    var needsRender = true;
    var disposed = false;
    var raf = 0;
    var orbiting = false;
    var panning = false;
    var lastPtr = { x: 0, y: 0 };

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
      var sx = Math.max(max.x - min.x, 1e-4), sy = Math.max(max.y - min.y, 1e-4), sz = Math.max(max.z - min.z, 1e-4);
      var geo = new THREE.BoxGeometry(sx, sy, sz);
      var edges = new THREE.EdgesGeometry(geo); geo.dispose();
      var mat = new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: opacity == null ? 0.45 : opacity });
      var line = new THREE.LineSegments(edges, mat);
      line.position.set((min.x + max.x) * 0.5, (min.y + max.y) * 0.5, (min.z + max.z) * 0.5);
      return line;
    }

    function marker(color, r) {
      return new THREE.Mesh(
        new THREE.SphereGeometry(r || 0.12, 16, 12),
        new THREE.MeshStandardMaterial({ color: color, emissive: color, emissiveIntensity: 0.35, roughness: 0.4, metalness: 0.2 })
      );
    }

    function linePts(pts, color, opacity) {
      var arr = [];
      for (var i = 0; i < pts.length; i++) arr.push(new THREE.Vector3(pts[i].x, pts[i].y, pts[i].z));
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

    function addActors(source, mics, selected) {
      var s = marker(SRC, 0.14);
      s.position.set(source.x, source.y, source.z); root.add(s);
      var sLab = makeLabel("Src", "#fbbf24");
      sLab.position.set(source.x, source.y + 0.35, source.z); root.add(sLab);
      ["L", "C", "R"].forEach(function (id) {
        if (selected.indexOf(id) < 0 && mode !== "lattice") return;
        var m = mics[id]; if (!m) return;
        var mesh = marker(MIC_COLORS[id], id === "C" ? 0.11 : 0.09);
        mesh.position.set(m.x, m.y, m.z); root.add(mesh);
        if (selected.indexOf(id) >= 0) {
          var col = id === "L" ? "#a78bfa" : id === "R" ? "#34d399" : "#60a5fa";
          var lab = makeLabel(id, col);
          lab.position.set(m.x, m.y + 0.32, m.z); root.add(lab);
        }
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

    function fitCamera(lattice) {
      if (!data) return;
      var room = data.room;
      camTarget.set(room.W * 0.5, room.H * 0.4, room.L * 0.5);
      if (lattice) {
        var span = Math.max(room.W, room.H, room.L) * 3.2;
        camSph.radius = Math.max(14, span * 1.05);
        camSph.theta = 0.95; camSph.phi = 1.05;
      } else {
        var diag = Math.sqrt(room.W * room.W + room.H * room.H + room.L * room.L);
        camSph.radius = Math.max(8, diag * 1.25);
      }
      rim.position.set(room.W * 0.5, room.H * 0.7, room.L * 0.5);
      updateCamera();
    }

    function updateCamera() {
      var s = camSph;
      s.phi = Math.max(0.12, Math.min(Math.PI * 0.48, s.phi));
      s.radius = Math.max(2.5, Math.min(120, s.radius));
      var sinPhi = Math.sin(s.phi);
      camera.position.set(
        camTarget.x + s.radius * sinPhi * Math.sin(s.theta),
        camTarget.y + s.radius * Math.cos(s.phi),
        camTarget.z + s.radius * sinPhi * Math.cos(s.theta)
      );
      camera.lookAt(camTarget);
    }

    function buildLattice() {
      if (!data) return;
      clearRoot();
      var room = data.room;
      root.add(homeBox(room));
      var grid = new THREE.GridHelper(Math.max(room.W, room.L), 8, 0x3a4155, 0x222833);
      grid.position.set(room.W * 0.5, 0.01, room.L * 0.5);
      grid.scale.set(room.W / Math.max(room.W, room.L), 1, room.L / Math.max(room.W, room.L));
      root.add(grid);
      (data.lattice || data.images || []).forEach(function (im) {
        var col = im.is_home ? HOME : (im.polarity > 0 ? POL_POS : POL_NEG);
        var op = im.is_home ? 0.95 : 0.32;
        var cb = cellBounds(im);
        if (cb) root.add(boxEdges(cb.min, cb.max, col, op));
        var xyz = imageXyz(im);
        if (xyz) {
          var m = marker(col, im.is_home ? 0.1 : 0.08);
          m.position.set(xyz.x, xyz.y, xyz.z);
          root.add(m);
        }
      });
      addActors(data.source, data.mics, data.selected_mics || ["C"]);
      fitCamera(true);
    }

    function buildPaths() {
      if (!data) return;
      clearRoot();
      var room = data.room;
      root.add(homeBox(room));
      var floor = new THREE.Mesh(
        new THREE.PlaneGeometry(room.W, room.L),
        new THREE.MeshStandardMaterial({ color: 0x12141a, roughness: 0.95, metalness: 0.05 })
      );
      floor.rotation.x = -Math.PI / 2;
      floor.position.set(room.W * 0.5, 0, room.L * 0.5);
      root.add(floor);
      var selected = data.selected_mics || ["C"];
      selected.forEach(function (micId) {
        var taps = perMicTaps(data, micId);
        taps.forEach(function (t) {
          if (!t.path || t.path.length < 2) return;
          var col = t.is_direct ? SRC : (t.polarity > 0 ? POL_POS : POL_NEG);
          var op = t.is_direct ? 0.95 : 0.35 + 0.4 / (1 + t.order);
          root.add(linePts(t.path, col, op));
        });
      });
      addActors(data.source, data.mics, selected);
      fitCamera(false);
    }

    function buildLegs() {
      if (!data) return;
      clearRoot();
      var room = data.room;
      root.add(homeBox(room));
      var selected = data.selected_mics || ["C"];
      selected.forEach(function (micId) {
        var mic = data.mics[micId];
        var taps = perMicTaps(data, micId);
        taps.forEach(function (t) {
          var leg = t.last_leg || t.lastLeg || t.leg; if (!leg) return;
          var ends = legEnds(leg); if (!ends) return;
          var col = t.is_direct ? SRC : (t.polarity > 0 ? POL_POS : POL_NEG);
          var op = t.is_direct ? 1.0 : 0.4 + 0.35 / (1 + t.order);
          root.add(linePts(ends, col, op));
          var tip = marker(col, 0.045);
          tip.position.set(ends[0].x, ends[0].y, ends[0].z);
          root.add(tip);
        });
        if (mic) {
          var hemi = new THREE.Mesh(
            new THREE.SphereGeometry(0.55, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.5),
            new THREE.MeshBasicMaterial({ color: MIC_COLORS[micId], transparent: true, opacity: 0.08, side: THREE.DoubleSide, depthWrite: false })
          );
          hemi.position.set(mic.x, mic.y, mic.z);
          root.add(hemi);
        }
      });
      addActors(data.source, data.mics, selected);
      fitCamera(false);
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
      if (evt.button === 2 || evt.button === 1 || (evt.button === 0 && evt.altKey)) {
        orbiting = true; canvas.classList.add("dragging");
        try { canvas.setPointerCapture(evt.pointerId); } catch (e) {}
        evt.preventDefault(); return;
      }
      if (evt.button === 0 && evt.shiftKey) {
        panning = true; canvas.classList.add("dragging");
        try { canvas.setPointerCapture(evt.pointerId); } catch (e) {}
        evt.preventDefault();
      }
    }

    function onPointerMove(evt) {
      var dx = evt.clientX - lastPtr.x, dy = evt.clientY - lastPtr.y;
      lastPtr.x = evt.clientX; lastPtr.y = evt.clientY;
      if (orbiting) {
        camSph.theta -= dx * 0.008; camSph.phi -= dy * 0.008;
        updateCamera(); needsRender = true; return;
      }
      if (panning) {
        var forward = new THREE.Vector3(); camera.getWorldDirection(forward);
        var right = new THREE.Vector3().crossVectors(forward, camera.up).normalize();
        var up = new THREE.Vector3().copy(camera.up).normalize();
        var scale = camSph.radius * 0.0018;
        camTarget.addScaledVector(right, -dx * scale);
        camTarget.addScaledVector(up, dy * scale);
        updateCamera(); needsRender = true;
      }
    }

    function onPointerUp() { orbiting = false; panning = false; canvas.classList.remove("dragging"); }
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
    canvas.addEventListener("contextmenu", function (e) { e.preventDefault(); });

    function frame() {
      if (disposed) return;
      raf = requestAnimationFrame(frame);
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

    return {
      setMode: function (m) {
        mode = (m === "legs") ? "legs" : (m === "paths" ? "paths" : "lattice");
        rebuild();
      },
      setData: function (d) { data = d; rebuild(); },
      resize: function () {
        resize();
        needsRender = true;
      },
      dispose: function () {
        disposed = true;
        cancelAnimationFrame(raf);
        if (ro) ro.disconnect();
        clearRoot();
        renderer.dispose();
      }
    };
  }

  global.ImageViews = { create: create };
})(window);

