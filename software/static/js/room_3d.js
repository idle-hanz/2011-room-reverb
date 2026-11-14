/* 2011 Room Reverb — Three.js 3D room viewport (Y-up orbit / pan / zoom) */
(function (global) {
  "use strict";

  var COLORS = {
    src: 0xfbbf24,
    srcB: 0xf43f5e,
    mic: 0x60a5fa,
    L: 0xa78bfa,
    C: 0x2dd4bf,
    R: 0x34d399,
    floor: 0x12141a,
    wall: 0x1a1d26,
    grid: 0x3a4155,
    accent: 0x2dd4bf,
  };

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
      console.warn("Three.js missing — 3D view disabled");
      return {
        redraw: function () {},
        dispose: function () {},
        resize: function () {},
      };
    }
    env.THREE = global.THREE;
    env.getState = env.opts.getState;
    env.setState = env.opts.setState;
    env.onChange = env.opts.onChange;
    env.RoomMath = env.opts.RoomMath || global.RoomMath;
    env.focusMic = !!env.opts.focusMic;

    env.renderer = new env.THREE.WebGLRenderer({
      canvas: env.canvas,
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
      preserveDrawingBuffer: true,
    });
    env.renderer.setPixelRatio(Math.min(global.devicePixelRatio || 1, 2));
    env.renderer.setClearColor(0x0a0b0e, 1);
    env.renderer.shadowMap.enabled = true;
    env.renderer.shadowMap.type = env.THREE.PCFSoftShadowMap;
    if (env.renderer.outputColorSpace !== undefined) {
      env.renderer.outputColorSpace = env.THREE.SRGBColorSpace;
    }

    env.scene = new env.THREE.Scene();
    env.scene.fog = new env.THREE.Fog(0x0a0b0e, 18, 42);

    env.camera = new env.THREE.PerspectiveCamera(42, 1, 0.05, 400);
    env.camTarget = new env.THREE.Vector3(3, 1.2, 4);
    // Room view uses the floor-plan Z mapping (threeZ = L − z), so Front is
    // far and the default camera looks along −Z: Left stays on the left.
    // Mic close-up keeps +Z = Front. phi: above-ground only.
    env.ROOM_THETA0 = 0;
    env.ROOM_PHI0 = 1.12;
    env.camSpherical = { theta: env.ROOM_THETA0, phi: env.ROOM_PHI0, radius: 14 };

    // Lighting — soft studio feel
    env.amb = new env.THREE.AmbientLight(0xb0b8c8, 0.48);
    env.scene.add(env.amb);
    env.key = new env.THREE.DirectionalLight(0xfff4e6, 1.05);
    env.key.position.set(6, 12, 4);
    env.key.castShadow = true;
    env.key.shadow.mapSize.set(1024, 1024);
    env.key.shadow.camera.near = 0.5;
    env.key.shadow.camera.far = 40;
    env.key.shadow.bias = -0.0005;
    env.scene.add(env.key);
    env.fill = new env.THREE.DirectionalLight(0x88aaff, 0.28);
    env.fill.position.set(-8, 4, -6);
    env.scene.add(env.fill);
    env.rim = new env.THREE.PointLight(0x2dd4bf, 0.35, 30);
    env.rim.position.set(0, 2.5, 0);
    env.scene.add(env.rim);

    // Room group (rebuilt on dim change)
    env.roomGroup = new env.THREE.Group();
    env.scene.add(env.roomGroup);
    env.actors = new env.THREE.Group();
    env.scene.add(env.actors);
    env.haloGroup = new env.THREE.Group();
    env.scene.add(env.haloGroup);
    env.haloData = null;
    env.haloPlane = "top";
    env.srcMesh = null;
    env.srcMeshB = null;
    env.micStand = null;
    env.micCentre = null;
    env.micL = null;
    env.micR = null;
    env.coneL = null;
    env.coneC = null;
    env.coneR = null;
    env.srcCone = null;
    env.srcConeB = null;
    env.labelSprites = [];

    env.lastWHL = { W: -1, H: -1, L: -1 };
    env.lastShell = "";
    
    env.drag = null; // { kind, planeY }
    env.orbiting = false;
    env.panning = false;
    env.lastPtr = { x: 0, y: 0 };
    env.hoverKind = null;
    env.raycaster = new env.THREE.Raycaster();
    env.pointerNDC = new env.THREE.Vector2();
    env.floorPlane = new env.THREE.Plane(new env.THREE.Vector3(0, 1, 0), 0);
    env.hitPoint = new env.THREE.Vector3();
    env.needsRender = true;
    env.raf = 0;
    env.disposed = false;

    env.canvas.addEventListener("pointerdown", bindPass(env, onPointerDown));
    env.canvas.addEventListener("pointermove", bindPass(env, onPointerMove));
    env.canvas.addEventListener("pointerup", bindPass(env, onPointerUp));
    env.canvas.addEventListener("pointercancel", bindPass(env, onPointerUp));
    env.canvas.addEventListener("wheel", bindPass(env, onWheel), { passive: false });
    env.canvas.addEventListener("contextmenu", function (e) { e.preventDefault(); });

    // Initial
    enter(env, resize);
    enter(env, rebuildRoom, 6, 3, 8);
    enter(env, updateCamera);
    enter(env, redraw);
    env.raf = requestAnimationFrame(bindPass(env, frame));

    env.ro = null;
    if (typeof ResizeObserver !== "undefined") {
      env.ro = new ResizeObserver(function () {
        env.needsRender = true;
      });
      env.ro.observe(env.canvas.parentElement || env.canvas);
    }

    env.api = {
      redraw: bindPass(env, redraw),
      setHalo: bindPass(env, setHalo),
      setHaloPlane: bindPass(env, setHaloPlane),
      capsuleWorld: bindPass(env, capsuleWorld),
      resize: function () { env.needsRender = true; },
      dispose: function () {
        env.disposed = true;
        cancelAnimationFrame(env.raf);
        if (env.ro) env.ro.disconnect();
        env.renderer.dispose();
      },
    };
    env.canvas._room3d = env.api;
    return env.api;
  }
  function worldZ(z, L) { var env = envStack[envStack.length - 1];
      if (env.focusMic) return z;
      return (L != null ? L : env.lastWHL.L) - z;
    }
  function makeLabel(text, color, depthTest) { var env = envStack[envStack.length - 1];
      var c = document.createElement("canvas");
      c.width = 128;
      c.height = 48;
      var ctx = c.getContext("2d");
      ctx.clearRect(0, 0, 128, 48);
      ctx.font = "600 22px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "rgba(10,11,14,0.72)";
      roundRect(ctx, 16, 8, 96, 32, 8);
      ctx.fill();
      ctx.fillStyle = color;
      ctx.fillText(text, 64, 25);
      var tex = new env.THREE.CanvasTexture(c);
      tex.needsUpdate = true;
      var mat = new env.THREE.SpriteMaterial({
        map: tex,
        transparent: true,
        depthTest: !!depthTest,
      });
      var spr = new env.THREE.Sprite(mat);
      spr.scale.set(0.85, 0.32, 1);
      return spr;
    }
  function roundRect(ctx, x, y, w, h, r) { var env = envStack[envStack.length - 1];
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + w, y, x + w, y + h, r);
      ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + w, y, r);
      ctx.closePath();
    }
  function mapRoom(p, L) { var env = envStack[envStack.length - 1];
      return [p[0], p[1], worldZ(p[2], L)];
    }
  function polyMesh(ring, material) { var env = envStack[envStack.length - 1];
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
      return new env.THREE.Mesh(geo, material);
    }
  function loopLine(ring, material) { var env = envStack[envStack.length - 1];
      var pts = ring.map(function (p) { return new env.THREE.Vector3(p[0], p[1], p[2]); });
      pts.push(pts[0].clone());
      return new env.THREE.Line(new env.THREE.BufferGeometry().setFromPoints(pts), material);
    }
  function rebuildRoom(W, H, L, shape, surfaces) { var env = envStack[envStack.length - 1];
      while (env.roomGroup.children.length) {
        var ch = env.roomGroup.children[0];
        env.roomGroup.remove(ch);
        if (ch.geometry) ch.geometry.dispose();
        if (ch.material) {
          var mats = Array.isArray(ch.material) ? ch.material : [ch.material];
          mats.forEach(function (m) {
            if (m.map) m.map.dispose();
            m.dispose();
          });
        }
      }
      shape = global.RoomDraw ? RoomDraw.shellToken(shape) : "box";

      function wallLabel(text, color, x, y, z) {
        var spr = makeLabel(text, color, true);
        spr.position.set(x, y, z);
        spr.scale.set(1.2, 0.44, 1);
        env.roomGroup.add(spr);
      }

      if (shape !== "box" && global.RoomDraw) {
        var faces = RoomDraw.polyFaces(shape, W, H, L);
        var edgeMatS = new env.THREE.LineBasicMaterial({
          color: 0x5a6478,
          transparent: true,
          opacity: 0.7
        });
        var labelName = {
          A: ["Left", "#38bdf8"], B: ["Front", "#2dd4bf"], C: ["Right", "#a78bfa"],
          D: ["Back", "#fb7185"], E: ["Floor", "#78716c"], F: ["Ceiling", "#e2e8f0"]
        };
        faces.forEach(function (face) {
          var ring = face.v.map(function (p) { return enter(env, mapRoom, p, L); });
          var col = RoomDraw.wallColor(surfaces, face.letter);
          var floorFace = face.name === "floor";
          var ceilFace = face.name === "ceiling";
          var mat = new env.THREE.MeshStandardMaterial({
            color: col,
            roughness: floorFace ? 0.92 : 0.88,
            metalness: 0.05,
            transparent: !floorFace,
            opacity: floorFace ? 1 : (ceilFace ? 0.28 : 0.55),
            side: env.THREE.DoubleSide,
            depthWrite: floorFace
          });
          var mesh = enter(env, polyMesh, ring, mat);
          mesh.receiveShadow = true;
          if (floorFace) mesh.name = "floor";
          env.roomGroup.add(mesh);
          env.roomGroup.add(enter(env, loopLine, ring, edgeMatS));
          var key = String(face.letter || "");
          var named = labelName[key] || labelName[key.charAt(0)];
          var text = named ? (key.length > 1 ? key + " " + named[0] : named[0]) : (key || face.name);
          var tint = named ? named[1] : "#c4b5fd";
          var c = [0, 0, 0];
          face.v.forEach(function (p) {
            c[0] += p[0];
            c[1] += p[1];
            c[2] += p[2];
          });
          var n = face.v.length || 1;
          var outP = [
            c[0] / n - face.n[0] * 0.2,
            c[1] / n - face.n[1] * 0.2,
            c[2] / n - face.n[2] * 0.2
          ];
          var tp = enter(env, mapRoom, outP, L);
          wallLabel(text, tint, tp[0], tp[1], tp[2]);
        });
        var floorFace0 = faces[0];
        var fc = [0, 0, 0];
        floorFace0.v.forEach(function (p) {
          fc[0] += p[0];
          fc[1] += p[1];
          fc[2] += p[2];
        });
        var fn = floorFace0.v.length || 1;
        var f3 = mapRoom([fc[0] / fn, 0, fc[2] / fn], L);
        var aoGeoS = new env.THREE.CircleGeometry(Math.min(W, L) * 0.4, 48);
        aoGeoS.rotateX(-Math.PI / 2);
        var aoS = new env.THREE.Mesh(aoGeoS, new env.THREE.MeshBasicMaterial({
          color: 0x000000, transparent: true, opacity: 0.22, depthWrite: false
        }));
        aoS.position.set(f3[0], 0.003, f3[2]);
        env.roomGroup.add(aoS);
      } else if (global.RoomDraw) {
      var built = RoomDraw.room3dBoxGeometries(env.THREE, W, H, L, function (z) { return enter(env, worldZ, z, L); });
      // Floor with soft AO-ish dark edge via vertex colors feel: dark plane + grid
      var floorMat = new env.THREE.MeshStandardMaterial({
        color: COLORS.floor,
        roughness: 0.92,
        metalness: 0.05,
      });
      var floor = RoomDraw.placePart(env.THREE, built.floor, floorMat);
      floor.receiveShadow = true;
      floor.name = "floor";
      env.roomGroup.add(floor);

      // Grid helper sized to room
      var gridDiv = Math.max(4, Math.round(Math.max(W, L)));
      var grid = new env.THREE.GridHelper(Math.max(W, L), gridDiv, 0x4a5568, 0x2a3140);
      grid.position.set(W * 0.5, 0.002, L * 0.5);
      // Scale non-uniformly so grid matches W×L
      grid.scale.set(W / Math.max(W, L), 1, L / Math.max(W, L));
      env.roomGroup.add(grid);

      // Subtle walls (transparent boxes / planes)
      var wallMat = new env.THREE.MeshStandardMaterial({
        color: COLORS.wall,
        transparent: true,
        opacity: 0.38,
        roughness: 0.88,
        metalness: 0.05,
        side: env.THREE.DoubleSide,
        depthWrite: false,
      });
      var edgeMat = new env.THREE.LineBasicMaterial({
        color: 0x5a6478,
        transparent: true,
        opacity: 0.55,
      });

      ["front", "back", "left", "right"].forEach(function (name) {
        var m = RoomDraw.placePart(env.THREE, built[name], wallMat.clone());
        m.receiveShadow = true;
        env.roomGroup.add(m);
      });
      var ly = H * 0.5;
      var out = 0.15;
      wallLabel("Front", "#2dd4bf", W * 0.5, ly, worldZ(L, L) - out);
      wallLabel("Back", "#fb7185", W * 0.5, ly, worldZ(0, L) + out);
      wallLabel("Left", "#38bdf8", -out, ly, L * 0.5);
      wallLabel("Right", "#a78bfa", W + out, ly, L * 0.5);

      // Ceiling (very subtle)
      var ceil = RoomDraw.placePart(env.THREE, built.ceil, new env.THREE.MeshStandardMaterial({
        color: 0x161820,
        transparent: true,
        opacity: 0.18,
        side: env.THREE.DoubleSide,
        depthWrite: false,
      }));
      env.roomGroup.add(ceil);

      // Wireframe room edges
      env.roomGroup.add(RoomDraw.placePart(env.THREE, built.edges, edgeMat));

      // Soft floor shadow disk (fake AO)
      var aoGeo = new env.THREE.CircleGeometry(Math.min(W, L) * 0.55, 48);
      aoGeo.rotateX(-Math.PI / 2);
      var aoMat = new env.THREE.MeshBasicMaterial({
        color: 0x000000,
        transparent: true,
        opacity: 0.22,
        depthWrite: false,
      });
      var ao = new env.THREE.Mesh(aoGeo, aoMat);
      ao.position.set(W * 0.5, 0.003, L * 0.5);
      env.roomGroup.add(ao);
      }

      env.rim.position.set(W * 0.5, H * 0.75, L * 0.5);
      env.key.shadow.camera.left = -Math.max(W, L);
      env.key.shadow.camera.right = Math.max(W, L);
      env.key.shadow.camera.top = Math.max(W, L);
      env.key.shadow.camera.bottom = -Math.max(W, L);
      env.key.shadow.camera.updateProjectionMatrix();

      var first = env.lastWHL.W < 0;
      env.lastWHL = { W: W, H: H, L: L };
      env.lastShell = shape + "|" + W + "|" + H + "|" + L;
      if (shape !== "box" && global.RoomDraw) env.lastShell += "|" + RoomDraw.colorKey(surfaces);
      var diag = Math.sqrt(W * W + H * H + L * L);
      var fogFar = Math.max(42, diag * 2.2);
      env.scene.fog.near = fogFar * 0.4;
      env.scene.fog.far = fogFar;
      env.camera.far = Math.max(400, fogFar * 2);
      env.camera.updateProjectionMatrix();
      // Keep orbit when resizing; only re-centre / fit on first build
      if (env.focusMic) {
        /* close-up framing is applied each redraw from mic pose */
      } else if (first) {
        env.camTarget.set(W * 0.5, H * 0.42, L * 0.5);
        env.camSpherical.radius = Math.max(10, Math.max(L, H) * 1.05 + W * 0.55);
        env.camSpherical.theta = env.ROOM_THETA0;
        env.camSpherical.phi = env.ROOM_PHI0;
      } else {
        env.camTarget.x = W * 0.5;
        env.camTarget.y = Math.min(env.camTarget.y, H * 0.9);
        env.camTarget.z = L * 0.5;
      }
    }
  function ensureActors() { var env = envStack[envStack.length - 1];
      if (env.srcMesh) return;
      // Source
      var srcGeo = new env.THREE.SphereGeometry(0.14, 24, 16);
      var srcMat = new env.THREE.MeshStandardMaterial({
        color: COLORS.src,
        emissive: COLORS.src,
        emissiveIntensity: 0.35,
        roughness: 0.35,
        metalness: 0.2,
      });
      env.srcMesh = new env.THREE.Mesh(srcGeo, srcMat);
      env.srcMesh.castShadow = true;
      env.srcMesh.name = "source";
      env.actors.add(env.srcMesh);
      var srcShadow = new env.THREE.Mesh(
        new env.THREE.CircleGeometry(0.2, 24),
        new env.THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35, depthWrite: false })
      );
      srcShadow.rotation.x = -Math.PI / 2;
      srcShadow.position.y = 0.015;
      srcShadow.name = "srcShadow";
      env.actors.add(srcShadow);
      env.actors.userData.srcShadow = srcShadow;
      var srcStem = new env.THREE.Mesh(
        new env.THREE.CylinderGeometry(0.012, 0.012, 1, 8),
        new env.THREE.MeshStandardMaterial({
          color: 0xfbbf24, transparent: true, opacity: 0.35, roughness: 0.6, metalness: 0.1,
        })
      );
      srcStem.name = "srcStem";
      env.actors.add(srcStem);
      env.actors.userData.srcStem = srcStem;
      var srcLabel = makeLabel("Src", "#fbbf24");
      srcLabel.position.y = 0.38;
      env.srcMesh.add(srcLabel);
      env.labelSprites.push(srcLabel);
      env.actors.userData.srcLabel = srcLabel;
      var srcLabelA = makeLabel("A", "#fbbf24");
      srcLabelA.position.y = 0.38;
      srcLabelA.visible = false;
      env.srcMesh.add(srcLabelA);
      env.labelSprites.push(srcLabelA);
      env.actors.userData.srcLabelA = srcLabelA;

      var srcGeoB = new env.THREE.SphereGeometry(0.13, 24, 16);
      var srcMatB = new env.THREE.MeshStandardMaterial({
        color: COLORS.srcB,
        emissive: COLORS.srcB,
        emissiveIntensity: 0.35,
        roughness: 0.35,
        metalness: 0.2,
      });
      env.srcMeshB = new env.THREE.Mesh(srcGeoB, srcMatB);
      env.srcMeshB.castShadow = true;
      env.srcMeshB.name = "sourceB";
      env.srcMeshB.visible = false;
      env.actors.add(env.srcMeshB);
      var srcShadowB = new env.THREE.Mesh(
        new env.THREE.CircleGeometry(0.18, 24),
        new env.THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35, depthWrite: false })
      );
      srcShadowB.rotation.x = -Math.PI / 2;
      srcShadowB.position.y = 0.015;
      srcShadowB.name = "srcShadowB";
      srcShadowB.visible = false;
      env.actors.add(srcShadowB);
      env.actors.userData.srcShadowB = srcShadowB;
      var srcStemB = new env.THREE.Mesh(
        new env.THREE.CylinderGeometry(0.012, 0.012, 1, 8),
        new env.THREE.MeshStandardMaterial({
          color: COLORS.srcB, transparent: true, opacity: 0.35, roughness: 0.6, metalness: 0.1,
        })
      );
      srcStemB.name = "srcStemB";
      srcStemB.visible = false;
      env.actors.add(srcStemB);
      env.actors.userData.srcStemB = srcStemB;
      var srcLabelB = makeLabel("B", "#f43f5e");
      srcLabelB.position.y = 0.38;
      env.srcMeshB.add(srcLabelB);
      env.labelSprites.push(srcLabelB);

      // Mic stand group
      env.micStand = new env.THREE.Group();
      env.micStand.name = "mic";
      env.actors.add(env.micStand);

      var poleGeo = new env.THREE.CylinderGeometry(0.018, 0.022, 1, 10);
      var poleMat = new env.THREE.MeshStandardMaterial({
        color: 0x8b92a5,
        roughness: 0.55,
        metalness: 0.45,
      });
      var pole = new env.THREE.Mesh(poleGeo, poleMat);
      pole.name = "pole";
      pole.castShadow = true;
      env.micStand.add(pole);

      var baseGeo = new env.THREE.CylinderGeometry(0.12, 0.14, 0.03, 16);
      var base = new env.THREE.Mesh(baseGeo, poleMat);
      base.position.y = 0.015;
      env.micStand.add(base);

      function capsule(color, name) {
        var g = new env.THREE.Group();
        g.name = name;
        var body = new env.THREE.Mesh(
          new env.THREE.SphereGeometry(0.07, 16, 12),
          new env.THREE.MeshStandardMaterial({
            color: color,
            emissive: color,
            emissiveIntensity: 0.2,
            roughness: 0.4,
            metalness: 0.25,
          })
        );
        body.castShadow = true;
        g.add(body);
        return g;
      }
      env.micCentre = capsule(COLORS.mic, "micCentre");
      env.micL = capsule(COLORS.L, "micL");
      env.micR = capsule(COLORS.R, "micR");
      env.micStand.add(env.micCentre);
      env.micStand.add(env.micL);
      env.micStand.add(env.micR);

      var micLabel = makeLabel("Mic", "#60a5fa");
      micLabel.position.y = 0.28;
      env.micCentre.add(micLabel);
      env.labelSprites.push(micLabel);

      var lLab = makeLabel("L", "#a78bfa");
      lLab.position.y = 0.22;
      lLab.scale.set(0.55, 0.22, 1);
      env.micL.add(lLab);
      var rLab = makeLabel("R", "#34d399");
      rLab.position.y = 0.22;
      rLab.scale.set(0.55, 0.22, 1);
      env.micR.add(rLab);

      // Look cones (open toward +Z with toe-in)
      function lookCone(color) {
        var geo = new env.THREE.ConeGeometry(0.28, 0.7, 20, 1, true);
        geo.translate(0, -0.275, 0);
        geo.rotateX(-Math.PI / 2);
        var mat = new env.THREE.MeshStandardMaterial({
          color: color,
          transparent: true,
          opacity: 0.42,
          emissive: color,
          emissiveIntensity: 0.15,
          roughness: 1,
          metalness: 0,
          side: env.THREE.DoubleSide,
          depthWrite: false,
        });
        var m = new env.THREE.Mesh(geo, mat);
        return m;
      }
      env.coneL = lookCone(COLORS.L);
      env.coneC = lookCone(COLORS.C);
      env.coneR = lookCone(COLORS.R);
      env.micL.add(env.coneL);
      env.micCentre.add(env.coneC);
      env.micR.add(env.coneR);

      function sourceCone(color) {
        var geo = new env.THREE.ConeGeometry(0.12, 0.48, 16, 1, true);
        geo.translate(0, -0.2, 0);
        geo.rotateX(-Math.PI / 2);
        var mat = new env.THREE.MeshStandardMaterial({
          color: color,
          transparent: true,
          opacity: 0.55,
          emissive: color,
          emissiveIntensity: 0.2,
          roughness: 1,
          metalness: 0,
          side: env.THREE.DoubleSide,
          depthWrite: false,
        });
        var m = new env.THREE.Mesh(geo, mat);
        m.visible = false;
        env.actors.add(m);
        return m;
      }
      env.srcCone = sourceCone(COLORS.src);
      env.srcConeB = sourceCone(COLORS.srcB);

      // Floor path line Src → Mic (XZ)
      var linkGeo = new env.THREE.BufferGeometry().setFromPoints([
        new env.THREE.Vector3(0, 0.01, 0),
        new env.THREE.Vector3(0, 0.01, 1),
      ]);
      var linkMat = new env.THREE.LineBasicMaterial({
        color: 0x2dd4bf,
        transparent: true,
        opacity: 0.35,
      });
      env.actors.userData.link = new env.THREE.Line(linkGeo, linkMat);
      env.actors.add(env.actors.userData.link);

      // Crossbar
      var bar = new env.THREE.Mesh(
        new env.THREE.BoxGeometry(1, 0.015, 0.015),
        new env.THREE.MeshStandardMaterial({ color: 0x6b7280, metalness: 0.5, roughness: 0.4 })
      );
      bar.name = "crossbar";
      env.micStand.add(bar);
    }
  function updateActors(geo) { var env = envStack[envStack.length - 1];
      ensureActors();
      var s = geo.state;
      // Same geo as Floor / Side: source.y = sy, mic_centre.y = my.
      // Do not place the source at my (that looks like Link heights stuck on).
      var sy = geo.source.y;
      var my = geo.mic_centre.y;

      env.srcMesh.position.set(geo.source.x, sy, worldZ(geo.source.z, s.L));
      env.srcMesh.visible = true;
      if (env.actors.userData.srcLabel) env.actors.userData.srcLabel.visible = !geo.source_b;
      if (env.actors.userData.srcLabelA) env.actors.userData.srcLabelA.visible = !!geo.source_b;
      if (env.actors.userData.srcShadow) {
        env.actors.userData.srcShadow.visible = true;
        env.actors.userData.srcShadow.position.set(geo.source.x, 0.015, worldZ(geo.source.z, s.L));
      }
      if (env.actors.userData.srcStem) {
        env.actors.userData.srcStem.visible = true;
        env.actors.userData.srcStem.position.set(geo.source.x, sy * 0.5, worldZ(geo.source.z, s.L));
        env.actors.userData.srcStem.scale.y = Math.max(0.05, sy);
      }
      var showB = !!geo.source_b;
      if (showB) {
        var bx = geo.source.x - geo.source_b.x;
        var bys = geo.source.y - geo.source_b.y;
        var bz = geo.source.z - geo.source_b.z;
        if (bx * bx + bys * bys + bz * bz < 1e-4) showB = false;
      }
      if (env.srcMeshB) {
        env.srcMeshB.visible = showB;
        if (showB) {
          var by = geo.source_b.y;
          env.srcMeshB.position.set(geo.source_b.x, by, worldZ(geo.source_b.z, s.L));
        }
      }
      if (env.actors.userData.srcShadowB) {
        env.actors.userData.srcShadowB.visible = showB;
        if (showB) {
          env.actors.userData.srcShadowB.position.set(geo.source_b.x, 0.015, worldZ(geo.source_b.z, s.L));
        }
      }
      if (env.actors.userData.srcStemB) {
        env.actors.userData.srcStemB.visible = showB;
        if (showB) {
          var by2 = geo.source_b.y;
          env.actors.userData.srcStemB.position.set(geo.source_b.x, by2 * 0.5, worldZ(geo.source_b.z, s.L));
          env.actors.userData.srcStemB.scale.y = Math.max(0.05, by2);
        }
      }

      env.micStand.position.set(geo.mic_centre.x, 0, worldZ(geo.mic_centre.z, s.L));
      var pole = env.micStand.getObjectByName("pole");
      if (pole) {
        pole.scale.y = Math.max(0.05, my);
        pole.position.y = my * 0.5;
      }
      var dz = s.centre_dz || 0;
      var half = s.space * 0.5;
      /* On-stand locals stay (0, y, ±dz), (−half, y, 0), (half, y, 0).
         A Room strip is offset from this stand group to its room spot.
         spot world Z uses the same worldZ as the stand. */
      var standWorld = { x: env.micStand.position.x, z: env.micStand.position.z };
      function putCapsule(mesh, cap, lx, ly, lz) {
        var pose = global.RRViewPose;
        var room = !!(pose && pose.isRoom && pose.isRoom(s, cap));
        if (!room) {
          mesh.position.set(lx, ly, lz);
          return;
        }
        var drag = global.RRDrag;
        var spot = drag && drag.roomSpot ? drag.roomSpot(s, cap) : null;
        var local = pose.capsuleLocal(
          true,
          { x: lx, y: ly, z: lz },
          standWorld,
          spot,
          spot ? worldZ(spot.z, s.L) : 0
        );
        mesh.position.set(local.x, local.y, local.z);
      }
      putCapsule(env.micCentre, "c", 0, geo.mic_centre.y, env.focusMic ? dz : -dz);
      putCapsule(env.micL, "l", -half, geo.mic_left.y, 0);
      putCapsule(env.micR, "r", half, geo.mic_right.y, 0);
      var bar = env.micStand.getObjectByName("crossbar");
      if (bar) {
        bar.position.set(0, my, 0);
        bar.scale.x = Math.max(0.05, s.space);
      }

      // Orient look cones from look vectors (XZ). Same aim for stand and room.
      function aim(cone, look) {
        if (!cone) return;
        var yaw = Math.atan2(look.x, env.focusMic ? look.z : -look.z);
        cone.rotation.set(0, yaw, 0);
      }
      function roomLook(cap, standLook) {
        var pose = global.RRViewPose;
        var drag = global.RRDrag;
        if (!pose || !pose.isRoom || !pose.isRoom(s, cap) || !drag || !drag.roomSpot) return standLook;
        var spot = drag.roomSpot(s, cap);
        var rad = (Number(spot.yaw) || 0) * Math.PI / 180;
        return global.RRLook.lookFromYaw(rad);
      }
      aim(env.coneL, roomLook("l", geo.look_l));
      aim(env.coneC, roomLook("c", geo.look_c || { x: 0, z: 1 }));
      aim(env.coneR, roomLook("r", geo.look_r));

      function aimSource(cone, origin, yawDeg, pitchDeg, show) {
        if (!cone) return;
        cone.visible = !!show;
        if (!show) return;
        var yaw = (Number(yawDeg) || 0) * Math.PI / 180;
        var pitch = (Number(pitchDeg) || 0) * Math.PI / 180;
        var fx = Math.sin(yaw) * Math.cos(pitch);
        var fy = Math.sin(pitch);
        var fz = Math.cos(yaw) * Math.cos(pitch);
        cone.position.set(origin.x + fx * 0.22, origin.y + fy * 0.22, origin.z - fz * 0.22);
        cone.lookAt(cone.position.x - fx, cone.position.y - fy, cone.position.z + fz);
      }
      function srcShow(id) {
        return String(id || "omni").toLowerCase() !== "omni";
      }
      var poseB = global.RoomMath.effectiveBPose(s);
      aimSource(env.srcCone, env.srcMesh.position, s.source_yaw, s.source_pitch, srcShow(s.source_radiation));
      if (env.srcConeB) {
        var originB = showB && env.srcMeshB ? env.srcMeshB.position : env.srcMesh.position;
        aimSource(
          env.srcConeB, originB, poseB.yaw, poseB.pitch,
          showB && srcShow(poseB.preset)
        );
      }

      if (env.actors.userData.link) {
        var pts = env.actors.userData.link.geometry.attributes.position;
        pts.setXYZ(0, geo.source.x, 0.02, worldZ(geo.source.z, s.L));
        pts.setXYZ(1, geo.mic_centre.x, 0.02, worldZ(geo.mic_centre.z, s.L));
        pts.needsUpdate = true;
      }
    }
  function updateCamera() { var env = envStack[envStack.length - 1];
      var s = env.camSpherical;
      s.radius = Math.max(2.5, Math.min(220, s.radius));
      env.camera.up.set(0, 1, 0);
      if (env.focusMic) {
        s.phi = Math.max(0.12, Math.min(Math.PI * 0.48, s.phi));
      } else {
        /* Room: above the floor only. ε < phi ≤ π/2 (ceiling down to horizon). */
        s.phi = Math.max(0.08, Math.min(Math.PI / 2, s.phi));
      }
      var sinPhi = Math.sin(s.phi);
      env.camera.position.set(
        env.camTarget.x + s.radius * sinPhi * Math.sin(s.theta),
        env.camTarget.y + s.radius * Math.cos(s.phi),
        env.camTarget.z + s.radius * sinPhi * Math.cos(s.theta)
      );
      env.camera.lookAt(env.camTarget);
    }
  function resize() { var env = envStack[envStack.length - 1];
      var rect = env.canvas.getBoundingClientRect();
      var w = Math.max(2, Math.floor(rect.width * (global.devicePixelRatio || 1)));
      var h = Math.max(2, Math.floor(rect.height * (global.devicePixelRatio || 1)));
      // Use CSS size for aspect; set drawing buffer
      var cssW = Math.max(2, Math.floor(rect.width));
      var cssH = Math.max(2, Math.floor(rect.height));
      if (env.canvas.width !== cssW * Math.min(global.devicePixelRatio || 1, 2) ||
          env.canvas.height !== cssH * Math.min(global.devicePixelRatio || 1, 2)) {
        env.renderer.setSize(cssW, cssH, false);
      }
      env.camera.aspect = cssW / Math.max(1, cssH);
      env.camera.updateProjectionMatrix();
      env.needsRender = true;
    }
  function setPointerFromEvent(evt) { var env = envStack[envStack.length - 1];
      var rect = env.canvas.getBoundingClientRect();
      env.pointerNDC.x = ((evt.clientX - rect.left) / rect.width) * 2 - 1;
      env.pointerNDC.y = -((evt.clientY - rect.top) / rect.height) * 2 + 1;
    }
  function rayHitFloor(planeY) { var env = envStack[envStack.length - 1];
      env.floorPlane.constant = -planeY;
      env.floorPlane.normal.set(0, 1, 0);
      env.raycaster.setFromCamera(env.pointerNDC, env.camera);
      if (env.raycaster.ray.intersectPlane(env.floorPlane, env.hitPoint)) {
        return env.hitPoint;
      }
      return null;
    }
  function pickActor() { var env = envStack[envStack.length - 1];
      env.raycaster.setFromCamera(env.pointerNDC, env.camera);
      var targets = [];
      if (env.srcMesh) targets.push(env.srcMesh);
      if (env.micStand) targets.push(env.micStand);
      var hits = env.raycaster.intersectObjects(targets, true);
      if (!hits.length) return null;
      var obj = hits[0].object;
      while (obj) {
        if (obj === env.srcMesh || obj.name === "source") return "source";
        if (obj === env.micStand || obj.name === "mic") return "mic";
        obj = obj.parent;
      }
      return null;
    }
  function applyXZ(kind, x, z) { var env = envStack[envStack.length - 1];
      var st = Object.assign({}, env.getState());
      if (kind === "source") {
        st.sx = env.RoomMath.clamp(x, 0, st.W);
        st.sz = env.RoomMath.clamp(z, 0, st.L);
      } else {
        st.mcx = env.RoomMath.clamp(x, 0, st.W);
        st.mcz = env.RoomMath.clamp(z, 0, st.L);
      }
      env.setState(env.RoomMath.clampRoom(st));
      env.onChange();
      env.needsRender = true;
    }
  function onPointerDown(evt) { var env = envStack[envStack.length - 1];
      setPointerFromEvent(evt);
      env.lastPtr.x = evt.clientX;
      env.lastPtr.y = evt.clientY;

      // Camera only: no source/mic placement in 3D (use Floor / Side / Mic tab).
      // Left = orbit; Shift+left = pan; RMB/MMB/Alt+left = orbit; scroll = zoom.
      if (evt.button === 0 && evt.shiftKey) {
        env.panning = true;
        env.canvas.classList.add("dragging");
        try { env.canvas.setPointerCapture(evt.pointerId); } catch (e) {}
        evt.preventDefault();
        return;
      }
      if (evt.button === 0 || evt.button === 2 || evt.button === 1) {
        env.orbiting = true;
        env.canvas.classList.add("dragging");
        try { env.canvas.setPointerCapture(evt.pointerId); } catch (e) {}
        evt.preventDefault();
        return;
      }
    }
  function onPointerMove(evt) { var env = envStack[envStack.length - 1];
      setPointerFromEvent(evt);
      var dx = evt.clientX - env.lastPtr.x;
      var dy = evt.clientY - env.lastPtr.y;
      env.lastPtr.x = evt.clientX;
      env.lastPtr.y = evt.clientY;

      if (env.orbiting) {
        env.camSpherical.theta -= dx * 0.008;
        if (env.focusMic) {
          env.camSpherical.phi += dy * 0.008;
        } else {
          env.camSpherical.phi -= dy * 0.008;
        }
        updateCamera();
        env.needsRender = true;
        return;
      }
      if (env.panning) {
        var forward = new env.THREE.Vector3();
        env.camera.getWorldDirection(forward);
        var right = new env.THREE.Vector3().crossVectors(forward, env.camera.up).normalize();
        var up = new env.THREE.Vector3().copy(env.camera.up).normalize();
        var scale = env.camSpherical.radius * 0.0018;
        env.camTarget.addScaledVector(right, -dx * scale);
        env.camTarget.addScaledVector(up, dy * scale);
        updateCamera();
        env.needsRender = true;
        return;
      }
      // No object drag in 3D — cursor stays default / grabbing while orbiting
      if (!env.orbiting && !env.panning) {
        env.canvas.style.cursor = "grab";
      }
    }
  function onPointerUp(evt) { var env = envStack[envStack.length - 1];
      env.drag = null;
      env.orbiting = false;
      env.panning = false;
      env.canvas.classList.remove("dragging");
      env.needsRender = true;
    }
  function onWheel(evt) { var env = envStack[envStack.length - 1];
      evt.preventDefault();
      var factor = evt.deltaY > 0 ? 1.08 : 1 / 1.08;
      env.camSpherical.radius *= factor;
      updateCamera();
      env.needsRender = true;
    }
  function clearHalo() { var env = envStack[envStack.length - 1];
      while (env.haloGroup.children.length) {
        var ch = env.haloGroup.children[0];
        env.haloGroup.remove(ch);
        if (ch.geometry) ch.geometry.dispose();
        if (ch.material) ch.material.dispose();
      }
    }
  function sampleMag(row, theta) { var env = envStack[envStack.length - 1];
      var n = row.length;
      var ang = Math.abs(theta);
      var turns = ang / (Math.PI * 2);
      var x = (turns - Math.floor(turns)) * n;
      var i0 = Math.floor(x) % n;
      var i1 = (i0 + 1) % n;
      var f = x - Math.floor(x);
      var a = Number(row[i0]);
      var b = Number(row[i1]);
      if (!isFinite(a)) a = 0;
      if (!isFinite(b)) b = 0;
      return a * (1 - f) + b * f;
    }
  function rebuildHalo(geo) { var env = envStack[envStack.length - 1];
      clearHalo();
      if (!env.focusMic || !env.haloData || !geo || !geo.mic_centre) return;
      var freqs = env.haloData.centres_hz || [];
      var gL = env.haloData.L, gC = env.haloData.C, gR = env.haloData.R;
      if (!gL || !gL.length || !freqs.length) return;
      env.camera.updateMatrixWorld(true);
      var right = new env.THREE.Vector3().setFromMatrixColumn(env.camera.matrixWorld, 0);
      var up = new env.THREE.Vector3().setFromMatrixColumn(env.camera.matrixWorld, 1);
      var nB = Math.min(freqs.length, gL.length, (gC || gL).length, (gR || gL).length);
      var nAz = 96;
      var c = geo.mic_centre;
      var mics = [
        { pos: geo.mic_left, look: geo.look_l, family: geo.state.family_l, polar: geo.state.polar_l, pattern: geo.state.pattern_l, grid: gL },
        { pos: geo.mic_centre, look: geo.look_c || { x: 0, z: 1 }, family: geo.state.family_c, polar: geo.state.polar_c, pattern: geo.state.pattern_c, grid: gC || gL },
        { pos: geo.mic_right, look: geo.look_r, family: geo.state.family_r, polar: geo.state.polar_r, pattern: geo.state.pattern_r, grid: gR || gL }
      ];
      var rings = [];
      var peak = 1e-6;
      var bi, ai;
      for (bi = 0; bi < nB; bi++) rings.push(new Array(nAz));
      for (ai = 0; ai < nAz; ai++) {
        var phi = (ai / nAz) * Math.PI * 2;
        var ux = Math.cos(phi) * right.x + Math.sin(phi) * up.x;
        var uy = Math.cos(phi) * right.y + Math.sin(phi) * up.y;
        var uz = Math.cos(phi) * right.z + Math.sin(phi) * up.z;
        for (bi = 0; bi < nB; bi++) {
          var re = 0, im = 0, mi;
          var freq = Number(freqs[bi]) || 0;
          for (mi = 0; mi < mics.length; mi++) {
            var mic = mics[mi];
            var look = mic.look || { x: 0, z: 1 };
            var cosT = look.x * ux + look.z * uz;
            if (cosT > 1) cosT = 1;
            if (cosT < -1) cosT = -1;
            var theta = Math.acos(cosT);
            var row = mic.grid[bi] || mic.grid[0];
            var mag = sampleMag(row, theta);
            var signed = mag;
            var g = global.RRPattern.polarGain(theta, mic.family, mic.polar, mic.pattern);
            signed = g < 0 ? -mag : (g === 0 ? 0 : mag);
            var dx = mic.pos.x - c.x;
            var dy = mic.pos.y - c.y;
            var dz = mic.pos.z - c.z;
            var phase = ((dx * ux + dy * uy + dz * uz) / 340) * Math.PI * 2 * freq;
            re += signed * Math.cos(phase);
            im += signed * Math.sin(phase);
          }
          var amp = Math.sqrt(re * re + im * im);
          rings[bi][ai] = amp;
          if (amp > peak) peak = amp;
        }
      }
      var reach = 0.95;
      for (bi = 0; bi < nB; bi++) {
        var pts = [];
        for (ai = 0; ai <= nAz; ai++) {
          var k = ai % nAz;
          phi = (k / nAz) * Math.PI * 2;
          var rad = global.RRDb.polarLinRadius(rings[bi][k] / peak, reach);
          pts.push(new env.THREE.Vector3(
            c.x + (Math.cos(phi) * right.x + Math.sin(phi) * up.x) * rad,
            c.y + (Math.cos(phi) * right.y + Math.sin(phi) * up.y) * rad,
            c.z + (Math.cos(phi) * right.z + Math.sin(phi) * up.z) * rad
          ));
        }
        env.haloGroup.add(new env.THREE.Line(
          new env.THREE.BufferGeometry().setFromPoints(pts),
          new env.THREE.LineBasicMaterial({
            color: (global.FreqPalette ? global.FreqPalette.intAt(bi, nB) : 0xe11d48),
            transparent: true,
            opacity: 0.92
          })
        ));
      }
      global.RRDb.POLAR_DB_RINGS.forEach(function (db) {
        var ringR = global.RRDb.polarRadius(db, reach);
        if (!(ringR > 0.01)) return;
        var ringPts = [];
        var rk;
        for (rk = 0; rk <= 48; rk++) {
          var rphi = (rk / 48) * Math.PI * 2;
          ringPts.push(new env.THREE.Vector3(
            c.x + (Math.cos(rphi) * right.x + Math.sin(rphi) * up.x) * ringR,
            c.y + (Math.cos(rphi) * right.y + Math.sin(rphi) * up.y) * ringR,
            c.z + (Math.cos(rphi) * right.z + Math.sin(rphi) * up.z) * ringR
          ));
        }
        env.haloGroup.add(new env.THREE.Line(
          new env.THREE.BufferGeometry().setFromPoints(ringPts),
          new env.THREE.LineBasicMaterial({ color: 0xd6d3cd, transparent: true, opacity: 0.4 })
        ));
      });
    }
  function frameHalo() { var env = envStack[envStack.length - 1];
      if (!env.focusMic || !env.haloGroup || !env.haloGroup.children.length) return;
      var box = new env.THREE.Box3().setFromObject(env.haloGroup);
      if (box.isEmpty()) return;
      var sphere = box.getBoundingSphere(new env.THREE.Sphere());
      if (!isFinite(sphere.radius) || sphere.radius <= 0) return;
      env.camTarget.copy(sphere.center);
      var fov = (env.camera.fov || 42) * Math.PI / 180;
      var dist = sphere.radius / Math.sin(fov * 0.5);
      env.camSpherical.radius = Math.max(0.8, dist * 1.2);
      env.camSpherical._micFramed = true;
      updateCamera();
    }
  function setHalo(data) { var env = envStack[envStack.length - 1];
      env.haloData = data || null;
      redraw();
    }
  function setHaloPlane() { var env = envStack[envStack.length - 1];
      /* The 3D slice follows the camera. Top / Side does not move it. */
    }
  function redraw() { var env = envStack[envStack.length - 1];
      if (env.disposed) return;
      var geo = env.RoomMath.compute(env.getState());
      var s = geo.state;
      var shape = global.RoomDraw ? RoomDraw.shellToken(s.room_shape) : "box";
      var shell = shape + "|" + s.W + "|" + s.H + "|" + s.L;
      if (shape !== "box" && global.RoomDraw) shell += "|" + RoomDraw.colorKey(s.surfaces);
      if (shell !== env.lastShell) {
        rebuildRoom(s.W, s.H, s.L, shape, s.surfaces);
        updateCamera();
      }
      updateActors(geo);
      if (env.focusMic && geo.mic_centre) {
        env.camTarget.set(geo.mic_centre.x, geo.mic_centre.y || s.my || 1.5, geo.mic_centre.z);
        var wantR = Math.max(1.2, Math.min(3.8, (s.space || 0.2) * 4 + 1.6));
        if (!env.camSpherical._micFramed) {
          env.camSpherical.radius = wantR;
          env.camSpherical.phi = 0.58;
          env.camSpherical.theta = 0.35;
          env.camSpherical._micFramed = true;
        } else {
          /* gently keep radius in close-up band without fighting user zoom */
          if (env.camSpherical.radius > 5.5) env.camSpherical.radius = wantR;
          if (env.camSpherical.radius < 0.8) env.camSpherical.radius = 0.8;
        }
        updateCamera();
        /* hide source for a cleaner desk close-up */
        if (env.srcMesh) env.srcMesh.visible = false;
        if (env.srcMeshB) env.srcMeshB.visible = false;
        if (env.actors.userData.srcShadow) env.actors.userData.srcShadow.visible = false;
        if (env.actors.userData.srcShadowB) env.actors.userData.srcShadowB.visible = false;
        if (env.actors.userData.srcStem) env.actors.userData.srcStem.visible = false;
        if (env.actors.userData.srcStemB) env.actors.userData.srcStemB.visible = false;
        if (env.actors.userData.link) env.actors.userData.link.visible = false;
      }
      if (env.roomGroup) env.roomGroup.visible = !env.focusMic;
      env.labelSprites.forEach(function (spr) { spr.visible = !env.focusMic; });
      if (env.focusMic) {
        rebuildHalo(geo);
        frameHalo();
      }
      env.needsRender = true;
    }
  function frame() { var env = envStack[envStack.length - 1];
      if (env.disposed) return;
      env.raf = requestAnimationFrame(bindPass(env, frame));
      if (!env.needsRender) return;
      env.needsRender = false;
      resize();
      updateCamera();
      if (env.focusMic && env.haloData) rebuildHalo(env.RoomMath.compute(env.getState()));
      env.renderer.render(env.scene, env.camera);
    }
  function capsuleWorld() { var env = envStack[envStack.length - 1];
      function one(mesh) {
        if (!mesh) return null;
        mesh.updateWorldMatrix(true, false);
        var p = new env.THREE.Vector3();
        mesh.getWorldPosition(p);
        return {
          x: p.x, y: p.y, z: p.z,
          lx: mesh.position.x, ly: mesh.position.y, lz: mesh.position.z
        };
      }
      return {
        l: one(env.micL), c: one(env.micCentre), r: one(env.micR),
        focusMic: !!env.focusMic
      };
    }

  global.Room3D = { create: create };
})(window);
