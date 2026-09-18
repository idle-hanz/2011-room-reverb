/* 2011 Room Reverb — Three.js 3D room viewport (camera orbit/pan/zoom only) */
(function (global) {
  "use strict";

  var COLORS = {
    src: 0xfbbf24,
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

    var camera = new THREE.PerspectiveCamera(42, 1, 0.05, 200);
    var camTarget = new THREE.Vector3(3, 1.2, 4);
    var camSpherical = { theta: 0.85, phi: 1.05, radius: 14 };

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

    var srcMesh = null;
    var micStand = null;
    var micCentre = null;
    var micL = null;
    var micR = null;
    var coneL = null;
    var coneC = null;
    var coneR = null;
    var labelSprites = [];

    var lastWHL = { W: -1, H: -1, L: -1 };
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

    function makeLabel(text, color) {
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
        depthTest: false,
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

    function rebuildRoom(W, H, L) {
      while (roomGroup.children.length) {
        var ch = roomGroup.children[0];
        roomGroup.remove(ch);
        if (ch.geometry) ch.geometry.dispose();
        if (ch.material) {
          if (Array.isArray(ch.material)) ch.material.forEach(function (m) { m.dispose(); });
          else ch.material.dispose();
        }
      }

      // Floor with soft AO-ish dark edge via vertex colors feel: dark plane + grid
      var floorGeo = new THREE.PlaneGeometry(W, L);
      floorGeo.rotateX(-Math.PI / 2);
      var floorMat = new THREE.MeshStandardMaterial({
        color: COLORS.floor,
        roughness: 0.92,
        metalness: 0.05,
      });
      var floor = new THREE.Mesh(floorGeo, floorMat);
      floor.position.set(W * 0.5, 0, L * 0.5);
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

      function wall(w, h, d, x, y, z) {
        var m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), wallMat.clone());
        m.position.set(x, y, z);
        m.receiveShadow = true;
        roomGroup.add(m);
      }
      var t = 0.04;
      // Back (+Z), Front (z=0), Left (x=0), Right (+X)
      wall(W, H, t, W * 0.5, H * 0.5, L);
      wall(W, H, t, W * 0.5, H * 0.5, 0);
      wall(t, H, L, 0, H * 0.5, L * 0.5);
      wall(t, H, L, W, H * 0.5, L * 0.5);

      // Ceiling (very subtle)
      var ceil = new THREE.Mesh(
        new THREE.PlaneGeometry(W, L),
        new THREE.MeshStandardMaterial({
          color: 0x161820,
          transparent: true,
          opacity: 0.18,
          side: THREE.DoubleSide,
          depthWrite: false,
        })
      );
      ceil.rotation.x = Math.PI / 2;
      ceil.position.set(W * 0.5, H, L * 0.5);
      roomGroup.add(ceil);

      // Wireframe room edges
      var box = new THREE.BoxGeometry(W, H, L);
      var edges = new THREE.EdgesGeometry(box);
      var line = new THREE.LineSegments(edges, edgeMat);
      line.position.set(W * 0.5, H * 0.5, L * 0.5);
      roomGroup.add(line);

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

      rim.position.set(W * 0.5, H * 0.75, L * 0.5);
      key.shadow.camera.left = -Math.max(W, L);
      key.shadow.camera.right = Math.max(W, L);
      key.shadow.camera.top = Math.max(W, L);
      key.shadow.camera.bottom = -Math.max(W, L);
      key.shadow.camera.updateProjectionMatrix();

      var first = lastWHL.W < 0;
      lastWHL = { W: W, H: H, L: L };
      // Keep orbit when resizing; only re-centre / fit on first build
      if (focusMic) {
        /* close-up framing is applied each redraw from mic pose */
      } else if (first) {
        camTarget.set(W * 0.5, H * 0.35, L * 0.5);
        var diag = Math.sqrt(W * W + H * H + L * L);
        camSpherical.radius = Math.max(8, diag * 1.15);
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
      var my = s.my;

      srcMesh.position.set(geo.source.x, my, geo.source.z);
      if (actors.userData.srcShadow) {
        actors.userData.srcShadow.position.set(geo.source.x, 0.015, geo.source.z);
      }
      if (actors.userData.srcStem) {
        actors.userData.srcStem.position.set(geo.source.x, my * 0.5, geo.source.z);
        actors.userData.srcStem.scale.y = Math.max(0.05, my);
      }

      micStand.position.set(geo.mic_centre.x, 0, geo.mic_centre.z);
      var pole = micStand.getObjectByName("pole");
      if (pole) {
        pole.scale.y = Math.max(0.05, my);
        pole.position.y = my * 0.5;
      }
      micCentre.position.set(0, my, 0);
      var half = s.space * 0.5;
      micL.position.set(-half, my, 0);
      micR.position.set(half, my, 0);
      var bar = micStand.getObjectByName("crossbar");
      if (bar) {
        bar.position.set(0, my, 0);
        bar.scale.x = Math.max(0.05, s.space);
      }

      // Orient look cones from look vectors (XZ)
      function aim(cone, look) {
        if (!cone) return;
        var yaw = Math.atan2(look.x, look.z);
        cone.rotation.set(0, yaw, 0);
      }
      aim(coneL, geo.look_l);
      aim(coneC, geo.look_c || { x: 0, z: 1 });
      aim(coneR, geo.look_r);

      if (actors.userData.link) {
        var pts = actors.userData.link.geometry.attributes.position;
        pts.setXYZ(0, geo.source.x, 0.02, geo.source.z);
        pts.setXYZ(1, geo.mic_centre.x, 0.02, geo.mic_centre.z);
        pts.needsUpdate = true;
      }
    }

    function updateCamera() {
      var s = camSpherical;
      s.phi = Math.max(0.12, Math.min(Math.PI * 0.48, s.phi));
      s.radius = Math.max(2.5, Math.min(60, s.radius));
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
        if (!st.reaktor_parity) st.mcx = RoomMath.clamp(x, 0, st.W);
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
        camSpherical.phi -= dy * 0.008;
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

    function redraw() {
      if (disposed) return;
      var geo = RoomMath.compute(getState());
      var s = geo.state;
      if (s.W !== lastWHL.W || s.H !== lastWHL.H || s.L !== lastWHL.L) {
        rebuildRoom(s.W, s.H, s.L);
        updateCamera();
      }
      updateActors(geo);
      if (focusMic && geo.mic_centre) {
        camTarget.set(geo.mic_centre.x, geo.mic_centre.y || s.my || 1.5, geo.mic_centre.z);
        var wantR = Math.max(1.2, Math.min(3.8, (s.space || 0.2) * 4 + 1.6));
        if (!camSpherical._micFramed) {
          camSpherical.radius = wantR;
          camSpherical.phi = 1.05;
          camSpherical.theta = 0.65;
          camSpherical._micFramed = true;
        } else {
          /* gently keep radius in close-up band without fighting user zoom */
          if (camSpherical.radius > 5.5) camSpherical.radius = wantR;
          if (camSpherical.radius < 0.8) camSpherical.radius = 0.8;
        }
        updateCamera();
        /* hide source for a cleaner desk close-up */
        if (srcMesh) srcMesh.visible = false;
        if (actors.userData.srcShadow) actors.userData.srcShadow.visible = false;
        if (actors.userData.srcStem) actors.userData.srcStem.visible = false;
        if (actors.userData.link) actors.userData.link.visible = false;
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

    return {
      redraw: redraw,
      resize: function () { needsRender = true; },
      dispose: function () {
        disposed = true;
        cancelAnimationFrame(raf);
        if (ro) ro.disconnect();
        renderer.dispose();
      },
    };
  }

  global.Room3D = { create: create };
})(window);
