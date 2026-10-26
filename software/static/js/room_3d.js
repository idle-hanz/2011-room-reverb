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

  function create(opts) {
    var canvas = opts.canvas;
    if (!global.THREE) {
      console.warn("Three.js missing — 3D view disabled");
      return {
        redraw: function () {},
        dispose: function () {},
        resize: function () {},
      };
    }
    var THREE = global.THREE;
    var getState = opts.getState;
    var setState = opts.setState;
    var onChange = opts.onChange;
    var RoomMath = opts.RoomMath || global.RoomMath;
    var focusMic = !!opts.focusMic;

    var renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
      preserveDrawingBuffer: true,
    });
    renderer.setPixelRatio(Math.min(global.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x0a0b0e, 1);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    if (renderer.outputColorSpace !== undefined) {
      renderer.outputColorSpace = THREE.SRGBColorSpace;
    }

    var scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x0a0b0e, 18, 42);

    var camera = new THREE.PerspectiveCamera(42, 1, 0.05, 400);
    var camTarget = new THREE.Vector3(3, 1.2, 4);
    // Room view uses the floor-plan Z mapping (threeZ = L − z), so Front is
    // far and the default camera looks along −Z: Left stays on the left.
    // Mic close-up keeps +Z = Front. phi: above-ground only.
    var ROOM_THETA0 = 0;
    var ROOM_PHI0 = 1.12;
    var camSpherical = { theta: ROOM_THETA0, phi: ROOM_PHI0, radius: 14 };

    // Lighting — soft studio feel
    var amb = new THREE.AmbientLight(0xb0b8c8, 0.48);
    scene.add(amb);
    var key = new THREE.DirectionalLight(0xfff4e6, 1.05);
    key.position.set(6, 12, 4);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.camera.near = 0.5;
    key.shadow.camera.far = 40;
    key.shadow.bias = -0.0005;
    scene.add(key);
    var fill = new THREE.DirectionalLight(0x88aaff, 0.28);
    fill.position.set(-8, 4, -6);
    scene.add(fill);
    var rim = new THREE.PointLight(0x2dd4bf, 0.35, 30);
    rim.position.set(0, 2.5, 0);
    scene.add(rim);

    // Room group (rebuilt on dim change)
    var roomGroup = new THREE.Group();
    scene.add(roomGroup);
    var actors = new THREE.Group();
    scene.add(actors);
    var haloGroup = new THREE.Group();
    scene.add(haloGroup);
    var haloData = null;
    var haloPlane = "top";
    var srcMesh = null;
    var srcMeshB = null;
    var micStand = null;
    var micCentre = null;
    var micL = null;
    var micR = null;
    var coneL = null;
    var coneC = null;
    var coneR = null;
    var srcCone = null;
    var srcConeB = null;
    var labelSprites = [];

    var lastWHL = { W: -1, H: -1, L: -1 };
    var lastShell = "";
    function worldZ(z, L) {
      if (focusMic) return z;
      return (L != null ? L : lastWHL.L) - z;
    }
    var drag = null; // { kind, planeY }
    var orbiting = false;
    var panning = false;
    var lastPtr = { x: 0, y: 0 };
    var hoverKind = null;
    var raycaster = new THREE.Raycaster();
    var pointerNDC = new THREE.Vector2();
    var floorPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    var hitPoint = new THREE.Vector3();
    var needsRender = true;
    var raf = 0;
    var disposed = false;

    function makeLabel(text, color, depthTest) {
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
      var tex = new THREE.CanvasTexture(c);
      tex.needsUpdate = true;
      var mat = new THREE.SpriteMaterial({
        map: tex,
        transparent: true,
        depthTest: !!depthTest,
      });
      var spr = new THREE.Sprite(mat);
      spr.scale.set(0.85, 0.32, 1);
      return spr;
    }

    function roundRect(ctx, x, y, w, h, r) {
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + w, y, x + w, y + h, r);
      ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + w, y, r);
      ctx.closePath();
    }

    function mapRoom(p, L) {
      return [p[0], p[1], worldZ(p[2], L)];
    }

    function polyMesh(ring, material) {
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
      return new THREE.Mesh(geo, material);
    }

    function loopLine(ring, material) {
      var pts = ring.map(function (p) { return new THREE.Vector3(p[0], p[1], p[2]); });
      pts.push(pts[0].clone());
      return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), material);
    }

    function rebuildRoom(W, H, L, shape, surfaces) {
      while (roomGroup.children.length) {
        var ch = roomGroup.children[0];
        roomGroup.remove(ch);
        if (ch.geometry) ch.geometry.dispose();
        if (ch.material) {
          var mats = Array.isArray(ch.material) ? ch.material : [ch.material];
          mats.forEach(function (m) {
            if (m.map) m.map.dispose();
            m.dispose();
          });
        }
      }
      shape = global.RoomDraw ? RoomDraw.normalize(shape) : "box";

      function wallLabel(text, color, x, y, z) {
        var spr = makeLabel(text, color, true);
        spr.position.set(x, y, z);
        spr.scale.set(1.2, 0.44, 1);
        roomGroup.add(spr);
      }

      if (shape !== "box" && global.RoomDraw) {
        var faces = RoomDraw.polyFaces(shape, W, H, L);
        var edgeMatS = new THREE.LineBasicMaterial({
          color: 0x5a6478,
          transparent: true,
          opacity: 0.7
        });
        var labelName = { A: ["Left", "#38bdf8"], B: ["Front", "#2dd4bf"], C: ["Right", "#a78bfa"], D: ["Back", "#fb7185"] };
        faces.forEach(function (face) {
          var ring = face.v.map(function (p) { return mapRoom(p, L); });
          var col = RoomDraw.wallColor(surfaces, face.letter);
          var floorFace = face.letter === "E";
          var mat = new THREE.MeshStandardMaterial({
            color: col,
            roughness: floorFace ? 0.92 : 0.88,
            metalness: 0.05,
            transparent: !floorFace,
            opacity: floorFace ? 1 : (face.letter === "F" ? 0.28 : 0.55),
            side: THREE.DoubleSide,
            depthWrite: floorFace
          });
          var mesh = polyMesh(ring, mat);
          mesh.receiveShadow = true;
          if (floorFace) mesh.name = "floor";
          roomGroup.add(mesh);
          roomGroup.add(loopLine(ring, edgeMatS));
          var named = labelName[face.letter];
          if (!named) return;
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
          var tp = mapRoom(outP, L);
          wallLabel(named[0], named[1], tp[0], tp[1], tp[2]);
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
        var aoGeoS = new THREE.CircleGeometry(Math.min(W, L) * 0.4, 48);
        aoGeoS.rotateX(-Math.PI / 2);
        var aoS = new THREE.Mesh(aoGeoS, new THREE.MeshBasicMaterial({
          color: 0x000000, transparent: true, opacity: 0.22, depthWrite: false
        }));
        aoS.position.set(f3[0], 0.003, f3[2]);
        roomGroup.add(aoS);
      } else if (global.RoomDraw) {
      var built = RoomDraw.room3dBoxGeometries(THREE, W, H, L, function (z) { return worldZ(z, L); });
      // Floor with soft AO-ish dark edge via vertex colors feel: dark plane + grid
      var floorMat = new THREE.MeshStandardMaterial({
        color: COLORS.floor,
        roughness: 0.92,
        metalness: 0.05,
      });
      var floor = RoomDraw.placePart(THREE, built.floor, floorMat);
      floor.receiveShadow = true;
      floor.name = "floor";
      roomGroup.add(floor);

      // Grid helper sized to room
      var gridDiv = Math.max(4, Math.round(Math.max(W, L)));
      var grid = new THREE.GridHelper(Math.max(W, L), gridDiv, 0x4a5568, 0x2a3140);
      grid.position.set(W * 0.5, 0.002, L * 0.5);
      // Scale non-uniformly so grid matches W×L
      grid.scale.set(W / Math.max(W, L), 1, L / Math.max(W, L));
      roomGroup.add(grid);

      // Subtle walls (transparent boxes / planes)
      var wallMat = new THREE.MeshStandardMaterial({
        color: COLORS.wall,
        transparent: true,
        opacity: 0.38,
        roughness: 0.88,
        metalness: 0.05,
        side: THREE.DoubleSide,
        depthWrite: false,
      });
      var edgeMat = new THREE.LineBasicMaterial({
        color: 0x5a6478,
        transparent: true,
        opacity: 0.55,
      });

      ["front", "back", "left", "right"].forEach(function (name) {
        var m = RoomDraw.placePart(THREE, built[name], wallMat.clone());
        m.receiveShadow = true;
        roomGroup.add(m);
      });
      var ly = H * 0.5;
      var out = 0.15;
      wallLabel("Front", "#2dd4bf", W * 0.5, ly, worldZ(L, L) - out);
      wallLabel("Back", "#fb7185", W * 0.5, ly, worldZ(0, L) + out);
      wallLabel("Left", "#38bdf8", -out, ly, L * 0.5);
      wallLabel("Right", "#a78bfa", W + out, ly, L * 0.5);

      // Ceiling (very subtle)
      var ceil = RoomDraw.placePart(THREE, built.ceil, new THREE.MeshStandardMaterial({
        color: 0x161820,
        transparent: true,
        opacity: 0.18,
        side: THREE.DoubleSide,
        depthWrite: false,
      }));
      roomGroup.add(ceil);

      // Wireframe room edges
      roomGroup.add(RoomDraw.placePart(THREE, built.edges, edgeMat));

      // Soft floor shadow disk (fake AO)
      var aoGeo = new THREE.CircleGeometry(Math.min(W, L) * 0.55, 48);
      aoGeo.rotateX(-Math.PI / 2);
      var aoMat = new THREE.MeshBasicMaterial({
        color: 0x000000,
        transparent: true,
        opacity: 0.22,
        depthWrite: false,
      });
      var ao = new THREE.Mesh(aoGeo, aoMat);
      ao.position.set(W * 0.5, 0.003, L * 0.5);
      roomGroup.add(ao);
      }

      rim.position.set(W * 0.5, H * 0.75, L * 0.5);
      key.shadow.camera.left = -Math.max(W, L);
      key.shadow.camera.right = Math.max(W, L);
      key.shadow.camera.top = Math.max(W, L);
      key.shadow.camera.bottom = -Math.max(W, L);
      key.shadow.camera.updateProjectionMatrix();

      var first = lastWHL.W < 0;
      lastWHL = { W: W, H: H, L: L };
      lastShell = shape + "|" + W + "|" + H + "|" + L;
      if (shape !== "box" && global.RoomDraw) lastShell += "|" + RoomDraw.colorKey(surfaces);
      var diag = Math.sqrt(W * W + H * H + L * L);
      var fogFar = Math.max(42, diag * 2.2);
      scene.fog.near = fogFar * 0.4;
      scene.fog.far = fogFar;
      camera.far = Math.max(400, fogFar * 2);
      camera.updateProjectionMatrix();
      // Keep orbit when resizing; only re-centre / fit on first build
      if (focusMic) {
        /* close-up framing is applied each redraw from mic pose */
      } else if (first) {
        camTarget.set(W * 0.5, H * 0.42, L * 0.5);
        camSpherical.radius = Math.max(10, Math.max(L, H) * 1.05 + W * 0.55);
        camSpherical.theta = ROOM_THETA0;
        camSpherical.phi = ROOM_PHI0;
      } else {
        camTarget.x = W * 0.5;
        camTarget.y = Math.min(camTarget.y, H * 0.9);
        camTarget.z = L * 0.5;
      }
    }

    function ensureActors() {
      if (srcMesh) return;
      // Source
      var srcGeo = new THREE.SphereGeometry(0.14, 24, 16);
      var srcMat = new THREE.MeshStandardMaterial({
        color: COLORS.src,
        emissive: COLORS.src,
        emissiveIntensity: 0.35,
        roughness: 0.35,
        metalness: 0.2,
      });
      srcMesh = new THREE.Mesh(srcGeo, srcMat);
      srcMesh.castShadow = true;
      srcMesh.name = "source";
      actors.add(srcMesh);
      var srcShadow = new THREE.Mesh(
        new THREE.CircleGeometry(0.2, 24),
        new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35, depthWrite: false })
      );
      srcShadow.rotation.x = -Math.PI / 2;
      srcShadow.position.y = 0.015;
      srcShadow.name = "srcShadow";
      actors.add(srcShadow);
      actors.userData.srcShadow = srcShadow;
      var srcStem = new THREE.Mesh(
        new THREE.CylinderGeometry(0.012, 0.012, 1, 8),
        new THREE.MeshStandardMaterial({
          color: 0xfbbf24, transparent: true, opacity: 0.35, roughness: 0.6, metalness: 0.1,
        })
      );
      srcStem.name = "srcStem";
      actors.add(srcStem);
      actors.userData.srcStem = srcStem;
      var srcLabel = makeLabel("Src", "#fbbf24");
      srcLabel.position.y = 0.38;
      srcMesh.add(srcLabel);
      labelSprites.push(srcLabel);
      actors.userData.srcLabel = srcLabel;
      var srcLabelA = makeLabel("A", "#fbbf24");
      srcLabelA.position.y = 0.38;
      srcLabelA.visible = false;
      srcMesh.add(srcLabelA);
      labelSprites.push(srcLabelA);
      actors.userData.srcLabelA = srcLabelA;

      var srcGeoB = new THREE.SphereGeometry(0.13, 24, 16);
      var srcMatB = new THREE.MeshStandardMaterial({
        color: COLORS.srcB,
        emissive: COLORS.srcB,
        emissiveIntensity: 0.35,
        roughness: 0.35,
        metalness: 0.2,
      });
      srcMeshB = new THREE.Mesh(srcGeoB, srcMatB);
      srcMeshB.castShadow = true;
      srcMeshB.name = "sourceB";
      srcMeshB.visible = false;
      actors.add(srcMeshB);
      var srcShadowB = new THREE.Mesh(
        new THREE.CircleGeometry(0.18, 24),
        new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35, depthWrite: false })
      );
      srcShadowB.rotation.x = -Math.PI / 2;
      srcShadowB.position.y = 0.015;
      srcShadowB.name = "srcShadowB";
      srcShadowB.visible = false;
      actors.add(srcShadowB);
      actors.userData.srcShadowB = srcShadowB;
      var srcStemB = new THREE.Mesh(
        new THREE.CylinderGeometry(0.012, 0.012, 1, 8),
        new THREE.MeshStandardMaterial({
          color: COLORS.srcB, transparent: true, opacity: 0.35, roughness: 0.6, metalness: 0.1,
        })
      );
      srcStemB.name = "srcStemB";
      srcStemB.visible = false;
      actors.add(srcStemB);
      actors.userData.srcStemB = srcStemB;
      var srcLabelB = makeLabel("B", "#f43f5e");
      srcLabelB.position.y = 0.38;
      srcMeshB.add(srcLabelB);
      labelSprites.push(srcLabelB);

      // Mic stand group
      micStand = new THREE.Group();
      micStand.name = "mic";
      actors.add(micStand);

      var poleGeo = new THREE.CylinderGeometry(0.018, 0.022, 1, 10);
      var poleMat = new THREE.MeshStandardMaterial({
        color: 0x8b92a5,
        roughness: 0.55,
        metalness: 0.45,
      });
      var pole = new THREE.Mesh(poleGeo, poleMat);
      pole.name = "pole";
      pole.castShadow = true;
      micStand.add(pole);

      var baseGeo = new THREE.CylinderGeometry(0.12, 0.14, 0.03, 16);
      var base = new THREE.Mesh(baseGeo, poleMat);
      base.position.y = 0.015;
      micStand.add(base);

      function capsule(color, name) {
        var g = new THREE.Group();
        g.name = name;
        var body = new THREE.Mesh(
          new THREE.SphereGeometry(0.07, 16, 12),
          new THREE.MeshStandardMaterial({
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
      micCentre = capsule(COLORS.mic, "micCentre");
      micL = capsule(COLORS.L, "micL");
      micR = capsule(COLORS.R, "micR");
      micStand.add(micCentre);
      micStand.add(micL);
      micStand.add(micR);

      var micLabel = makeLabel("Mic", "#60a5fa");
      micLabel.position.y = 0.28;
      micCentre.add(micLabel);
      labelSprites.push(micLabel);

      var lLab = makeLabel("L", "#a78bfa");
      lLab.position.y = 0.22;
      lLab.scale.set(0.55, 0.22, 1);
      micL.add(lLab);
      var rLab = makeLabel("R", "#34d399");
      rLab.position.y = 0.22;
      rLab.scale.set(0.55, 0.22, 1);
      micR.add(rLab);

      // Look cones (open toward +Z with toe-in)
      function lookCone(color) {
        var geo = new THREE.ConeGeometry(0.28, 0.7, 20, 1, true);
        geo.translate(0, -0.275, 0);
        geo.rotateX(-Math.PI / 2);
        var mat = new THREE.MeshStandardMaterial({
          color: color,
          transparent: true,
          opacity: 0.42,
          emissive: color,
          emissiveIntensity: 0.15,
          roughness: 1,
          metalness: 0,
          side: THREE.DoubleSide,
          depthWrite: false,
        });
        var m = new THREE.Mesh(geo, mat);
        return m;
      }
      coneL = lookCone(COLORS.L);
      coneC = lookCone(COLORS.C);
      coneR = lookCone(COLORS.R);
      micL.add(coneL);
      micCentre.add(coneC);
      micR.add(coneR);

      function sourceCone(color) {
        var geo = new THREE.ConeGeometry(0.12, 0.48, 16, 1, true);
        geo.translate(0, -0.2, 0);
        geo.rotateX(-Math.PI / 2);
        var mat = new THREE.MeshStandardMaterial({
          color: color,
          transparent: true,
          opacity: 0.55,
          emissive: color,
          emissiveIntensity: 0.2,
          roughness: 1,
          metalness: 0,
          side: THREE.DoubleSide,
          depthWrite: false,
        });
        var m = new THREE.Mesh(geo, mat);
        m.visible = false;
        actors.add(m);
        return m;
      }
      srcCone = sourceCone(COLORS.src);
      srcConeB = sourceCone(COLORS.srcB);

      // Floor path line Src → Mic (XZ)
      var linkGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0.01, 0),
        new THREE.Vector3(0, 0.01, 1),
      ]);
      var linkMat = new THREE.LineBasicMaterial({
        color: 0x2dd4bf,
        transparent: true,
        opacity: 0.35,
      });
      actors.userData.link = new THREE.Line(linkGeo, linkMat);
      actors.add(actors.userData.link);

      // Crossbar
      var bar = new THREE.Mesh(
        new THREE.BoxGeometry(1, 0.015, 0.015),
        new THREE.MeshStandardMaterial({ color: 0x6b7280, metalness: 0.5, roughness: 0.4 })
      );
      bar.name = "crossbar";
      micStand.add(bar);
    }

    function updateActors(geo) {
      ensureActors();
      var s = geo.state;
      // Same geo as Floor / Side: source.y = sy, mic_centre.y = my.
      // Do not place the source at my (that looks like Link heights stuck on).
      var sy = geo.source.y;
      var my = geo.mic_centre.y;

      srcMesh.position.set(geo.source.x, sy, worldZ(geo.source.z, s.L));
      srcMesh.visible = true;
      if (actors.userData.srcLabel) actors.userData.srcLabel.visible = !geo.source_b;
      if (actors.userData.srcLabelA) actors.userData.srcLabelA.visible = !!geo.source_b;
      if (actors.userData.srcShadow) {
        actors.userData.srcShadow.visible = true;
        actors.userData.srcShadow.position.set(geo.source.x, 0.015, worldZ(geo.source.z, s.L));
      }
      if (actors.userData.srcStem) {
        actors.userData.srcStem.visible = true;
        actors.userData.srcStem.position.set(geo.source.x, sy * 0.5, worldZ(geo.source.z, s.L));
        actors.userData.srcStem.scale.y = Math.max(0.05, sy);
      }
      var showB = !!geo.source_b;
      if (showB) {
        var bx = geo.source.x - geo.source_b.x;
        var bys = geo.source.y - geo.source_b.y;
        var bz = geo.source.z - geo.source_b.z;
        if (bx * bx + bys * bys + bz * bz < 1e-4) showB = false;
      }
      if (srcMeshB) {
        srcMeshB.visible = showB;
        if (showB) {
          var by = geo.source_b.y;
          srcMeshB.position.set(geo.source_b.x, by, worldZ(geo.source_b.z, s.L));
        }
      }
      if (actors.userData.srcShadowB) {
        actors.userData.srcShadowB.visible = showB;
        if (showB) {
          actors.userData.srcShadowB.position.set(geo.source_b.x, 0.015, worldZ(geo.source_b.z, s.L));
        }
      }
      if (actors.userData.srcStemB) {
        actors.userData.srcStemB.visible = showB;
        if (showB) {
          var by2 = geo.source_b.y;
          actors.userData.srcStemB.position.set(geo.source_b.x, by2 * 0.5, worldZ(geo.source_b.z, s.L));
          actors.userData.srcStemB.scale.y = Math.max(0.05, by2);
        }
      }

      micStand.position.set(geo.mic_centre.x, 0, worldZ(geo.mic_centre.z, s.L));
      var pole = micStand.getObjectByName("pole");
      if (pole) {
        pole.scale.y = Math.max(0.05, my);
        pole.position.y = my * 0.5;
      }
      var dz = s.centre_dz || 0;
      var half = s.space * 0.5;
      /* On-stand locals stay (0, y, ±dz), (−half, y, 0), (half, y, 0).
         A Room strip is offset from this stand group to its room spot.
         spot world Z uses the same worldZ as the stand. */
      var standWorld = { x: micStand.position.x, z: micStand.position.z };
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
      putCapsule(micCentre, "c", 0, geo.mic_centre.y, focusMic ? dz : -dz);
      putCapsule(micL, "l", -half, geo.mic_left.y, 0);
      putCapsule(micR, "r", half, geo.mic_right.y, 0);
      var bar = micStand.getObjectByName("crossbar");
      if (bar) {
        bar.position.set(0, my, 0);
        bar.scale.x = Math.max(0.05, s.space);
      }

      // Orient look cones from look vectors (XZ). Same aim for stand and room.
      function aim(cone, look) {
        if (!cone) return;
        var yaw = Math.atan2(look.x, focusMic ? look.z : -look.z);
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
      aim(coneL, roomLook("l", geo.look_l));
      aim(coneC, roomLook("c", geo.look_c || { x: 0, z: 1 }));
      aim(coneR, roomLook("r", geo.look_r));

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
      aimSource(srcCone, srcMesh.position, s.source_yaw, s.source_pitch, srcShow(s.source_radiation));
      if (srcConeB) {
        var originB = showB && srcMeshB ? srcMeshB.position : srcMesh.position;
        aimSource(
          srcConeB, originB, poseB.yaw, poseB.pitch,
          showB && srcShow(poseB.preset)
        );
      }

      if (actors.userData.link) {
        var pts = actors.userData.link.geometry.attributes.position;
        pts.setXYZ(0, geo.source.x, 0.02, worldZ(geo.source.z, s.L));
        pts.setXYZ(1, geo.mic_centre.x, 0.02, worldZ(geo.mic_centre.z, s.L));
        pts.needsUpdate = true;
      }
    }

    function updateCamera() {
      var s = camSpherical;
      s.radius = Math.max(2.5, Math.min(220, s.radius));
      camera.up.set(0, 1, 0);
      if (focusMic) {
        s.phi = Math.max(0.12, Math.min(Math.PI * 0.48, s.phi));
      } else {
        /* Room: above the floor only. ε < phi ≤ π/2 (ceiling down to horizon). */
        s.phi = Math.max(0.08, Math.min(Math.PI / 2, s.phi));
      }
      var sinPhi = Math.sin(s.phi);
      camera.position.set(
        camTarget.x + s.radius * sinPhi * Math.sin(s.theta),
        camTarget.y + s.radius * Math.cos(s.phi),
        camTarget.z + s.radius * sinPhi * Math.cos(s.theta)
      );
      camera.lookAt(camTarget);
    }

    function resize() {
      var rect = canvas.getBoundingClientRect();
      var w = Math.max(2, Math.floor(rect.width * (global.devicePixelRatio || 1)));
      var h = Math.max(2, Math.floor(rect.height * (global.devicePixelRatio || 1)));
      // Use CSS size for aspect; set drawing buffer
      var cssW = Math.max(2, Math.floor(rect.width));
      var cssH = Math.max(2, Math.floor(rect.height));
      if (canvas.width !== cssW * Math.min(global.devicePixelRatio || 1, 2) ||
          canvas.height !== cssH * Math.min(global.devicePixelRatio || 1, 2)) {
        renderer.setSize(cssW, cssH, false);
      }
      camera.aspect = cssW / Math.max(1, cssH);
      camera.updateProjectionMatrix();
      needsRender = true;
    }

    function setPointerFromEvent(evt) {
      var rect = canvas.getBoundingClientRect();
      pointerNDC.x = ((evt.clientX - rect.left) / rect.width) * 2 - 1;
      pointerNDC.y = -((evt.clientY - rect.top) / rect.height) * 2 + 1;
    }

    function rayHitFloor(planeY) {
      floorPlane.constant = -planeY;
      floorPlane.normal.set(0, 1, 0);
      raycaster.setFromCamera(pointerNDC, camera);
      if (raycaster.ray.intersectPlane(floorPlane, hitPoint)) {
        return hitPoint;
      }
      return null;
    }

    function pickActor() {
      raycaster.setFromCamera(pointerNDC, camera);
      var targets = [];
      if (srcMesh) targets.push(srcMesh);
      if (micStand) targets.push(micStand);
      var hits = raycaster.intersectObjects(targets, true);
      if (!hits.length) return null;
      var obj = hits[0].object;
      while (obj) {
        if (obj === srcMesh || obj.name === "source") return "source";
        if (obj === micStand || obj.name === "mic") return "mic";
        obj = obj.parent;
      }
      return null;
    }

    function applyXZ(kind, x, z) {
      var st = Object.assign({}, getState());
      if (kind === "source") {
        st.sx = RoomMath.clamp(x, 0, st.W);
        st.sz = RoomMath.clamp(z, 0, st.L);
      } else {
        st.mcx = RoomMath.clamp(x, 0, st.W);
        st.mcz = RoomMath.clamp(z, 0, st.L);
      }
      setState(RoomMath.clampRoom(st));
      onChange();
      needsRender = true;
    }

    function onPointerDown(evt) {
      setPointerFromEvent(evt);
      lastPtr.x = evt.clientX;
      lastPtr.y = evt.clientY;

      // Camera only: no source/mic placement in 3D (use Floor / Side / Mic tab).
      // Left = orbit; Shift+left = pan; RMB/MMB/Alt+left = orbit; scroll = zoom.
      if (evt.button === 0 && evt.shiftKey) {
        panning = true;
        canvas.classList.add("dragging");
        try { canvas.setPointerCapture(evt.pointerId); } catch (e) {}
        evt.preventDefault();
        return;
      }
      if (evt.button === 0 || evt.button === 2 || evt.button === 1) {
        orbiting = true;
        canvas.classList.add("dragging");
        try { canvas.setPointerCapture(evt.pointerId); } catch (e) {}
        evt.preventDefault();
        return;
      }
    }

    function onPointerMove(evt) {
      setPointerFromEvent(evt);
      var dx = evt.clientX - lastPtr.x;
      var dy = evt.clientY - lastPtr.y;
      lastPtr.x = evt.clientX;
      lastPtr.y = evt.clientY;

      if (orbiting) {
        camSpherical.theta -= dx * 0.008;
        if (focusMic) {
          camSpherical.phi += dy * 0.008;
        } else {
          camSpherical.phi -= dy * 0.008;
        }
        updateCamera();
        needsRender = true;
        return;
      }
      if (panning) {
        var forward = new THREE.Vector3();
        camera.getWorldDirection(forward);
        var right = new THREE.Vector3().crossVectors(forward, camera.up).normalize();
        var up = new THREE.Vector3().copy(camera.up).normalize();
        var scale = camSpherical.radius * 0.0018;
        camTarget.addScaledVector(right, -dx * scale);
        camTarget.addScaledVector(up, dy * scale);
        updateCamera();
        needsRender = true;
        return;
      }
      // No object drag in 3D — cursor stays default / grabbing while orbiting
      if (!orbiting && !panning) {
        canvas.style.cursor = "grab";
      }
    }

    function onPointerUp(evt) {
      drag = null;
      orbiting = false;
      panning = false;
      canvas.classList.remove("dragging");
      needsRender = true;
    }

    function onWheel(evt) {
      evt.preventDefault();
      var factor = evt.deltaY > 0 ? 1.08 : 1 / 1.08;
      camSpherical.radius *= factor;
      updateCamera();
      needsRender = true;
    }

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });
    canvas.addEventListener("contextmenu", function (e) { e.preventDefault(); });

    function clearHalo() {
      while (haloGroup.children.length) {
        var ch = haloGroup.children[0];
        haloGroup.remove(ch);
        if (ch.geometry) ch.geometry.dispose();
        if (ch.material) ch.material.dispose();
      }
    }

    function sampleMag(row, theta) {
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

    function rebuildHalo(geo) {
      clearHalo();
      if (!focusMic || !haloData || !geo || !geo.mic_centre) return;
      var freqs = haloData.centres_hz || [];
      var gL = haloData.L, gC = haloData.C, gR = haloData.R;
      if (!gL || !gL.length || !freqs.length) return;
      camera.updateMatrixWorld(true);
      var right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
      var up = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
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
          var rad = rings[bi][k] / peak * reach;
          pts.push(new THREE.Vector3(
            c.x + (Math.cos(phi) * right.x + Math.sin(phi) * up.x) * rad,
            c.y + (Math.cos(phi) * right.y + Math.sin(phi) * up.y) * rad,
            c.z + (Math.cos(phi) * right.z + Math.sin(phi) * up.z) * rad
          ));
        }
        haloGroup.add(new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(pts),
          new THREE.LineBasicMaterial({
            color: (global.FreqPalette ? global.FreqPalette.intAt(bi, nB) : 0xe11d48),
            transparent: true,
            opacity: 0.92
          })
        ));
      }
    }

    function frameHalo() {
      if (!focusMic || !haloGroup || !haloGroup.children.length) return;
      var box = new THREE.Box3().setFromObject(haloGroup);
      if (box.isEmpty()) return;
      var sphere = box.getBoundingSphere(new THREE.Sphere());
      if (!isFinite(sphere.radius) || sphere.radius <= 0) return;
      camTarget.copy(sphere.center);
      var fov = (camera.fov || 42) * Math.PI / 180;
      var dist = sphere.radius / Math.sin(fov * 0.5);
      camSpherical.radius = Math.max(0.8, dist * 1.2);
      camSpherical._micFramed = true;
      updateCamera();
    }

    function setHalo(data) {
      haloData = data || null;
      redraw();
    }

    function setHaloPlane() {
      /* The 3D slice follows the camera. Top / Side does not move it. */
    }

    function redraw() {
      if (disposed) return;
      var geo = RoomMath.compute(getState());
      var s = geo.state;
      var shape = global.RoomDraw ? RoomDraw.normalize(s.room_shape) : "box";
      var shell = shape + "|" + s.W + "|" + s.H + "|" + s.L;
      if (shape !== "box" && global.RoomDraw) shell += "|" + RoomDraw.colorKey(s.surfaces);
      if (shell !== lastShell) {
        rebuildRoom(s.W, s.H, s.L, shape, s.surfaces);
        updateCamera();
      }
      updateActors(geo);
      if (focusMic && geo.mic_centre) {
        camTarget.set(geo.mic_centre.x, geo.mic_centre.y || s.my || 1.5, geo.mic_centre.z);
        var wantR = Math.max(1.2, Math.min(3.8, (s.space || 0.2) * 4 + 1.6));
        if (!camSpherical._micFramed) {
          camSpherical.radius = wantR;
          camSpherical.phi = 0.58;
          camSpherical.theta = 0.35;
          camSpherical._micFramed = true;
        } else {
          /* gently keep radius in close-up band without fighting user zoom */
          if (camSpherical.radius > 5.5) camSpherical.radius = wantR;
          if (camSpherical.radius < 0.8) camSpherical.radius = 0.8;
        }
        updateCamera();
        /* hide source for a cleaner desk close-up */
        if (srcMesh) srcMesh.visible = false;
        if (srcMeshB) srcMeshB.visible = false;
        if (actors.userData.srcShadow) actors.userData.srcShadow.visible = false;
        if (actors.userData.srcShadowB) actors.userData.srcShadowB.visible = false;
        if (actors.userData.srcStem) actors.userData.srcStem.visible = false;
        if (actors.userData.srcStemB) actors.userData.srcStemB.visible = false;
        if (actors.userData.link) actors.userData.link.visible = false;
      }
      if (roomGroup) roomGroup.visible = !focusMic;
      labelSprites.forEach(function (spr) { spr.visible = !focusMic; });
      if (focusMic) {
        rebuildHalo(geo);
        frameHalo();
      }
      needsRender = true;
    }

    function frame() {
      if (disposed) return;
      raf = requestAnimationFrame(frame);
      if (!needsRender) return;
      needsRender = false;
      resize();
      updateCamera();
      if (focusMic && haloData) rebuildHalo(RoomMath.compute(getState()));
      renderer.render(scene, camera);
    }

    // Initial
    resize();
    rebuildRoom(6, 3, 8);
    updateCamera();
    redraw();
    raf = requestAnimationFrame(frame);

    var ro = null;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(function () {
        needsRender = true;
      });
      ro.observe(canvas.parentElement || canvas);
    }

    function capsuleWorld() {
      function one(mesh) {
        if (!mesh) return null;
        mesh.updateWorldMatrix(true, false);
        var p = new THREE.Vector3();
        mesh.getWorldPosition(p);
        return {
          x: p.x, y: p.y, z: p.z,
          lx: mesh.position.x, ly: mesh.position.y, lz: mesh.position.z
        };
      }
      return {
        l: one(micL), c: one(micCentre), r: one(micR),
        focusMic: !!focusMic
      };
    }

    var api = {
      redraw: redraw,
      setHalo: setHalo,
      setHaloPlane: setHaloPlane,
      capsuleWorld: capsuleWorld,
      resize: function () { needsRender = true; },
      dispose: function () {
        disposed = true;
        cancelAnimationFrame(raf);
        if (ro) ro.disconnect();
        renderer.dispose();
      },
    };
    canvas._room3d = api;
    return api;
  }

  global.Room3D = { create: create };
})(window);
