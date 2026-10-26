/* 3D polar field — mic pattern × frequency in mic–source plane (ASSUMED) */
(function (global) {
  "use strict";

  var COLORS = { L: 0xa78bfa, C: 0x2dd4bf, R: 0x34d399, sum: 0xfbbf24, base: 0x5eead4, one: 0x5eead4 };

  function PolarFieldView(opts) {
    opts = opts || {};
    this.canvas = opts.canvas || document.getElementById("polarCanvas");
    this.wrap = opts.wrap || document.getElementById("polarWrap");
    this.meta = opts.meta || document.getElementById("polarMeta");
    this.getState = opts.getState || function () { return {}; };
    this.isolated = !!opts.isolated;
    this.useBase = !!opts.useBase;
    this.onRefresh = opts.onRefresh || null;
    // Stereo pair story → default Sum only. The Mic hero passes its own set.
    this.enabled = opts.enabled || { L: false, C: false, R: false, sum: true };
    this.data = null;
    this._dragging = false;
    this._lastX = 0;
    this._lastY = 0;
    this._yaw = 0.85;
    this._pitch = 0.48;
    this._dist = 5.5;
    this._meshes = {};
    this._planeHelper = null;
    this.soloBand = null;
    this._balloonSpec = null;
    this._skipHidden = !!opts.skipHidden;
    if (!this.canvas || typeof THREE === "undefined") {
      if (this.meta) this.meta.textContent = "Three.js unavailable";
      return;
    }
    if (!this.isolated) this._syncToggleUI();
    this._initThree();
    this._bindOrbit();
    if (!this.isolated) this._bindUI();
    this._animate();
  }

  PolarFieldView.prototype._syncToggleUI = function () {
    var self = this;
    document.querySelectorAll("#polarToggles input[data-polar]").forEach(function (box) {
      var key = box.getAttribute("data-polar");
      if (key && Object.prototype.hasOwnProperty.call(self.enabled, key)) {
        box.checked = !!self.enabled[key];
      }
    });
  };

  PolarFieldView.prototype._initThree = function () {
    var canvas = this.canvas;
    var w = Math.max(320, canvas.clientWidth || 900);
    var h = Math.max(240, canvas.clientHeight || 520);
    canvas.width = w;
    canvas.height = h;
    this.renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(w, h, false);
    this.renderer.setClearColor(0x0a0b0e, 1);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(42, w / h, 0.05, 200);
    this.scene.add(new THREE.AmbientLight(0xb0b8c8, 0.55));
    var key = new THREE.DirectionalLight(0xffffff, 0.85);
    key.position.set(3, 5, 2);
    this.scene.add(key);
    this.scene.add(new THREE.AxesHelper(1.0));
    this.root = new THREE.Group();
    this.scene.add(this.root);
    this._look = new THREE.Vector3(0, 1.0, 0);
    this._updateCamera();
  };

  PolarFieldView.prototype._updateCamera = function () {
    var cp = Math.cos(this._pitch), sp = Math.sin(this._pitch);
    var cy = Math.cos(this._yaw), sy = Math.sin(this._yaw);
    var lx = this._look.x, ly = this._look.y, lz = this._look.z;
    this.camera.position.set(
      lx + this._dist * cp * sy,
      ly + this._dist * sp,
      lz + this._dist * cp * cy
    );
    this.camera.lookAt(this._look);
  };

  PolarFieldView.prototype._bindOrbit = function () {
    var self = this;
    var el = this.wrap || this.canvas;
    el.addEventListener("pointerdown", function (e) {
      if (e.target.closest && e.target.closest("button, a, input, select, label")) return;
      self._dragging = true;
      self._lastX = e.clientX;
      self._lastY = e.clientY;
      try { el.setPointerCapture(e.pointerId); } catch (err) {}
    });
    el.addEventListener("pointermove", function (e) {
      if (!self._dragging) return;
      var dx = e.clientX - self._lastX;
      var dy = e.clientY - self._lastY;
      self._lastX = e.clientX;
      self._lastY = e.clientY;
      self._yaw -= dx * 0.01;
      self._pitch = Math.max(0.08, Math.min(1.4, self._pitch + dy * 0.01));
      self._updateCamera();
    });
    function up() { self._dragging = false; }
    el.addEventListener("pointerup", up);
    el.addEventListener("pointercancel", up);
    el.addEventListener("wheel", function (e) {
      e.preventDefault();
      self._dist = Math.max(2.0, Math.min(18, self._dist + e.deltaY * 0.01));
      self._updateCamera();
    }, { passive: false });
  };

  PolarFieldView.prototype._bindUI = function () {
    var self = this;
    document.querySelectorAll("#polarToggles input[data-polar]").forEach(function (box) {
      box.addEventListener("change", function () {
        self.enabled[box.getAttribute("data-polar")] = !!box.checked;
        self._rebuildMeshes();
      });
    });
    var btn = document.getElementById("polarRefresh");
    if (btn) btn.addEventListener("click", function () {
      if (self.onRefresh) self.onRefresh();
      else self.refresh();
    });
  };

  PolarFieldView.prototype.setSoloBand = function (index) {
    this.soloBand = (index == null || index < 0) ? null : index;
    this._rebuildMeshes();
  };

  PolarFieldView.prototype.setData = function (data) {
    this.data = data;
    var pln = (this.useBase && data && data.base_plane) ? data.base_plane : (data && data.plane);
    if (pln && pln.origin) {
      var o = pln.origin;
      var stack = Number(data.stack_m) || 2.4;
      var nn = pln.normal || [0, 1, 0];
      this._look.set(
        o[0] + nn[0] * stack * 0.35,
        o[1] + nn[1] * stack * 0.35,
        o[2] + nn[2] * stack * 0.35
      );
      this._updateCamera();
    }
    this._rebuildMeshes();
    if (this.meta && data) {
      var preset = data.presets && data.presets.C;
      var name = preset && preset.display_name ? preset.display_name : "";
      var st = this.getState ? this.getState() : null;
      if (st && st.mic_setup === "binaural") {
        name = String(st.binaural_preset || "SADIE2_KU100").replace(/_/g, " ") + " head";
      }
      var law = data.measured
        ? "Measured: real mic response, relative to on-axis"
        : "Ideal pattern";
      this.meta.textContent =
        law +
        (name ? " · " + name : "");
    }
  };

  PolarFieldView.prototype._clearMeshes = function () {
    var self = this;
    Object.keys(this._meshes).forEach(function (k) {
      var m = self._meshes[k];
      self.root.remove(m);
      m.traverse(function (ch) {
        if (ch.geometry) ch.geometry.dispose();
        if (ch.material) {
          if (Array.isArray(ch.material)) ch.material.forEach(function (mm) { mm.dispose(); });
          else ch.material.dispose();
        }
      });
    });
    this._meshes = {};
    if (this._planeHelper) {
      this.root.remove(this._planeHelper);
      this._planeHelper.traverse(function (ch) {
        if (ch.geometry) ch.geometry.dispose();
        if (ch.material) {
          if (ch.material.map) ch.material.map.dispose();
          ch.material.dispose();
        }
      });
      this._planeHelper = null;
    }
  };

  PolarFieldView.prototype._drawPlaneWire = function () {
    if (!this.data || !this.data.plane) return;
    var pl = (this.useBase && this.data.base_plane) ? this.data.base_plane : this.data.plane;
    var o = pl.origin;
    var e1 = pl.e1;
    var e2 = pl.e2;
    if (!o || !e1 || !e2) return;
    var s = 1.6;
    function pt(a, b) {
      return new THREE.Vector3(
        o[0] + e1[0] * a + e2[0] * b,
        o[1] + e1[1] * a + e2[1] * b,
        o[2] + e1[2] * a + e2[2] * b
      );
    }
    var corners = [pt(-s, -s), pt(s, -s), pt(s, s), pt(-s, s), pt(-s, -s)];
    var geo = new THREE.BufferGeometry().setFromPoints(corners);
    var mat = new THREE.LineBasicMaterial({
      color: 0x6b7280,
      transparent: true,
      opacity: 0.55
    });
    var loop = new THREE.Line(geo, mat);
    // Crosshairs
    var crossPts = [pt(-s, 0), pt(s, 0), pt(0, -s), pt(0, s)];
    var crossGeo = new THREE.BufferGeometry().setFromPoints([
      crossPts[0], crossPts[1], crossPts[2], crossPts[3]
    ]);
    // Two separate segments via LineSegments
    var segPos = new Float32Array([
      crossPts[0].x, crossPts[0].y, crossPts[0].z,
      crossPts[1].x, crossPts[1].y, crossPts[1].z,
      crossPts[2].x, crossPts[2].y, crossPts[2].z,
      crossPts[3].x, crossPts[3].y, crossPts[3].z
    ]);
    var segGeo = new THREE.BufferGeometry();
    segGeo.setAttribute("position", new THREE.BufferAttribute(segPos, 3));
    var cross = new THREE.LineSegments(
      segGeo,
      new THREE.LineBasicMaterial({ color: 0x9ca3af, transparent: true, opacity: 0.4 })
    );
    var g = new THREE.Group();
    g.add(loop);
    g.add(cross);
    this._addDbRings(g, o, e1, e2);
    // Source marker in plane
    if (pl.source) {
      var src = new THREE.Mesh(
        new THREE.SphereGeometry(0.06, 10, 10),
        new THREE.MeshBasicMaterial({ color: 0xf97316 })
      );
      src.position.set(pl.source[0], pl.source[1], pl.source[2]);
      g.add(src);
    }
    this._planeHelper = g;
    this.root.add(g);
  };

  /* 0° is the array aim (yaw 0 = +Z). +angle goes toward +X, same as room yaw.
     Plane e2 is n × (right − left) = −Z, so labels that follow e2 sit on the back. */
  PolarFieldView.prototype._lookBasis = function (plane, yawRad) {
    var n = (plane && plane.normal) || [0, 1, 0];
    var yaw = Number(yawRad) || 0;
    var lookV = window.RRLook.lookVector(yaw);
    var look = [lookV.x, lookV.y, lookV.z];
    function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
    function unit(a) {
      var len = Math.hypot(a[0], a[1], a[2]);
      if (!(len > 1e-8)) return null;
      return [a[0] / len, a[1] / len, a[2] / len];
    }
    function cross(a, b) {
      return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]
      ];
    }
    var dn = dot(look, n);
    var fwd = unit([look[0] - n[0] * dn, look[1] - n[1] * dn, look[2] - n[2] * dn]) || [0, 0, 1];
    var right = unit(cross(n, fwd)) || [1, 0, 0];
    fwd = unit(cross(right, n)) || fwd;
    return { fwd: fwd, right: right, normal: n };
  };

  PolarFieldView.prototype._arrayYawRad = function () {
    var d = this.data;
    if (d && d.yaw_deg && d.yaw_deg.C != null && isFinite(Number(d.yaw_deg.C))) {
      return Number(d.yaw_deg.C) * Math.PI / 180;
    }
    return 0;
  };

  PolarFieldView.prototype._labelSprite = function (text) {
    var canvas = document.createElement("canvas");
    canvas.width = 160;
    canvas.height = 64;
    var ctx = canvas.getContext("2d");
    ctx.fillStyle = "rgba(232,230,223,0.92)";
    ctx.font = "600 28px Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, 80, 32);
    var tex = new THREE.CanvasTexture(canvas);
    var sprite = new THREE.Sprite(new THREE.SpriteMaterial({
      map: tex,
      transparent: true,
      depthTest: false
    }));
    sprite.scale.set(0.42, 0.17, 1);
    return sprite;
  };

  PolarFieldView.prototype._addDbRings = function (group, o, e1, e2) {
    var rings = [0, -6, -12, -18, -24];
    var basis = this._lookBasis(
      { normal: (this.data && (this.useBase && this.data.base_plane ? this.data.base_plane : this.data.plane) || {}).normal },
      this._arrayYawRad()
    );
    function at(radius, ang) {
      return new THREE.Vector3(
        o[0] + e1[0] * radius * Math.sin(ang) + e2[0] * radius * Math.cos(ang),
        o[1] + e1[1] * radius * Math.sin(ang) + e2[1] * radius * Math.cos(ang),
        o[2] + e1[2] * radius * Math.sin(ang) + e2[2] * radius * Math.cos(ang)
      );
    }
    function front(radius, ang) {
      return new THREE.Vector3(
        o[0] + basis.right[0] * radius * Math.sin(ang) + basis.fwd[0] * radius * Math.cos(ang),
        o[1] + basis.right[1] * radius * Math.sin(ang) + basis.fwd[1] * radius * Math.cos(ang),
        o[2] + basis.right[2] * radius * Math.sin(ang) + basis.fwd[2] * radius * Math.cos(ang)
      );
    }
    var self = this;
    rings.forEach(function (db) {
      var radius = 0.9 * window.RRDb.dbToLin(db);
      var pts = [];
      var i;
      for (i = 0; i <= 72; i++) pts.push(at(radius, (i / 72) * Math.PI * 2));
      group.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({ color: 0xd6d3cd, transparent: true, opacity: 0.45 })
      ));
      var lab = self._labelSprite((db === 0 ? "0" : String(db)) + " dB");
      var p = front(radius, 0.35);
      lab.position.copy(p);
      group.add(lab);
    });
    [[0, "0\u00b0"], [Math.PI / 2, "90\u00b0"], [Math.PI, "180\u00b0"]].forEach(function (row) {
      var lab = self._labelSprite(row[1]);
      lab.position.copy(front(1.12, row[0]));
      group.add(lab);
    });
    var origin = new THREE.Vector3(o[0], o[1], o[2]);
    var dir = new THREE.Vector3(basis.fwd[0], basis.fwd[1], basis.fwd[2]);
    group.add(new THREE.ArrowHelper(dir, origin, 0.82, 0xf59e0b, 0.16, 0.07));
  };

  /* share[key] is already in the centre-look frame. A subset is |Σ amp·e^{−jω·proj/c}| / N. */
  PolarFieldView.prototype._combinedFlat = function (members) {
    var data = this.data;
    var share = data && data.share;
    if (!share || !members || !members.length) return null;
    var pl = (this.useBase && data.base_plane) ? data.base_plane : data.plane;
    if (!pl) return null;
    var n = pl.normal || [0, 1, 0];
    var basis = this._lookBasis({ normal: n }, this._arrayYawRad());
    var origins = data.mic_origins || {};
    var centre = origins.C || pl.origin;
    if (!centre) return null;
    var bands = data.centres_hz || [];
    var nB = bands.length;
    var nAz = data.n_az || 0;
    if (!nB || !nAz) return null;
    var nBm = Math.max(1, nB - 1);
    var stack = Number(data.stack_m) || 2.4;
    var speed = 340;
    var flat = new Float32Array(nB * nAz * 3);
    var fwd = basis.fwd;
    var right = basis.right;
    var nMem = members.length;
    var ai, bi, theta, ct, st, dir, omega, re, im, r, h, ix, ph, amp, key, o, row;
    for (ai = 0; ai < nAz; ai++) {
      theta = (ai / nAz) * Math.PI * 2;
      ct = Math.cos(theta);
      st = Math.sin(theta);
      dir = [
        fwd[0] * ct + right[0] * st,
        fwd[1] * ct + right[1] * st,
        fwd[2] * ct + right[2] * st
      ];
      for (bi = 0; bi < nB; bi++) {
        omega = 2 * Math.PI * Number(bands[bi]);
        re = 0;
        im = 0;
        for (var mi = 0; mi < nMem; mi++) {
          key = members[mi];
          o = origins[key];
          row = share[key] && share[key][bi];
          amp = row ? Number(row[ai]) || 0 : 0;
          var proj = 0;
          if (o) {
            proj = dir[0] * (o[0] - centre[0]) + dir[1] * (o[1] - centre[1]) + dir[2] * (o[2] - centre[2]);
          }
          ph = -omega * proj / speed;
          re += amp * Math.cos(ph);
          im += amp * Math.sin(ph);
        }
        r = Math.hypot(re, im) / nMem;
        h = (bi / nBm) * stack;
        ix = (bi * nAz + ai) * 3;
        flat[ix] = centre[0] + n[0] * h + fwd[0] * r * ct + right[0] * r * st;
        flat[ix + 1] = centre[1] + n[1] * h + fwd[1] * r * ct + right[1] * r * st;
        flat[ix + 2] = centre[2] + n[2] * h + fwd[2] * r * ct + right[2] * r * st;
      }
    }
    return flat;
  };

  /* Presets tick the boxes without a change event. The plot follows the boxes. */
  PolarFieldView.prototype._readToggles = function () {
    if (this.isolated) return;
    var self = this;
    document.querySelectorAll("#polarToggles input[data-polar]").forEach(function (box) {
      var key = box.getAttribute("data-polar");
      if (key && Object.prototype.hasOwnProperty.call(self.enabled, key)) {
        self.enabled[key] = !!box.checked;
      }
    });
  };

  PolarFieldView.prototype._rebuildMeshes = function () {
    if (!this.root || !this.data) return;
    this._readToggles();
    this._clearMeshes();
    this._drawPlaneWire();
    var bands = this.data.centres_hz || [];
    var nAz = this.data.n_az || 0;
    if (!bands.length || !nAz) return;
    var nB = bands.length;
    var self = this;
    ["base", "one"].forEach(function (key) {
      if (!self.enabled[key]) return;
      var mesh = null;
      if (self.data.vertices && self.data.vertices[key]) {
        mesh = self._makeSurfaceFromVertices(
          self.data.vertices[key], nB, nAz, COLORS[key] || COLORS.sum, 0.32
        );
      }
      if (!mesh) return;
      self._meshes[key] = mesh;
      self.root.add(mesh);
    });
    /* Two toed solids overlap into a tube. Two or more ticked capsules
       draw one combined mesh. One ticked capsule keeps its own solid. */
    var ticked = ["L", "C", "R"].filter(function (k) { return self.enabled[k]; });
    var members = ticked.length ? ticked.slice() : (self.enabled.sum ? ["L", "C", "R"] : []);
    var mesh = null;
    if (members.length === 1 && ticked.length === 1) {
      var only = members[0];
      if (self.data.vertices && self.data.vertices[only]) {
        mesh = self._makeSurfaceFromVertices(
          self.data.vertices[only], nB, nAz, COLORS[only], 0.32
        );
      } else if (self.data[only]) {
        mesh = self._makeSurfaceFromGrid(self.data[only], nB, nAz, COLORS[only], 0.32);
      }
      if (mesh) {
        self._meshes[only] = mesh;
        self.root.add(mesh);
      }
    } else if (members.length) {
      var flat = self._combinedFlat(members);
      if (flat) {
        mesh = self._makeSurfaceFromVertices(flat, nB, nAz, COLORS.sum, 0.45);
      } else if (self.data.vertices && self.data.vertices.sum) {
        mesh = self._makeSurfaceFromVertices(
          self.data.vertices.sum, nB, nAz, COLORS.sum, 0.45
        );
      } else if (self.data.sum) {
        mesh = self._makeSurfaceFromGrid(self.data.sum, nB, nAz, COLORS.sum, 0.45);
      }
      if (mesh) {
        self._meshes.sum = mesh;
        self.root.add(mesh);
      }
    }
    this._drawIdealOutline();
  };

  PolarFieldView.prototype._drawIdealOutline = function () {
    if (!this.data || !this.data.measured || !this.root) return;
    var pl = (this.useBase && this.data.base_plane) ? this.data.base_plane : this.data.plane;
    if (!pl || !pl.origin) return;
    var st = this.getState ? (this.getState() || {}) : {};
    var ticked = [];
    var self = this;
    [["L", "l"], ["C", "c"], ["R", "r"]].forEach(function (row) {
      if (self.enabled[row[0]]) ticked.push(row);
    });
    if (!ticked.length && !this.enabled.sum) return;
    var row = ticked.length === 1 ? ticked[0] : ["C", "c"];
    var origins = this.data.mic_origins || {};
    var o = (ticked.length === 1 && origins[row[0]]) ? origins[row[0]] : (origins.C || pl.origin);
    var yaw = this._arrayYawRad();
    if (ticked.length === 1 && this.data.yaw_deg && this.data.yaw_deg[row[0]] != null) {
      var yd = Number(this.data.yaw_deg[row[0]]);
      if (isFinite(yd)) yaw = yd * Math.PI / 180;
    }
    var nn = pl.normal || [0, 1, 0];
    var basis = this._lookBasis({ normal: nn }, yaw);
    var centres = this.data.centres_hz || [];
    var bi = 0;
    if (this.soloBand != null && this.soloBand >= 0 && this.soloBand < centres.length) {
      bi = this.soloBand;
    } else {
      var i;
      for (i = 0; i < centres.length; i++) {
        if (Math.abs(Number(centres[i]) - 1000) < 1) bi = i;
      }
    }
    var h = (bi / Math.max(1, centres.length - 1)) * (Number(this.data.stack_m) || 2.4);
    var fam = st["family_" + row[1]] || "cardioid";
    var pol = st["polar_" + row[1]];
    var pts = [];
    var k;
    for (k = 0; k <= 96; k++) {
      var th = (k / 96) * Math.PI * 2;
      var g = 1;
      if (window.RoomMath && RoomMath.polarGain) g = Math.abs(RoomMath.polarGain(th, fam, pol, st["pattern_" + row[1]]));
      else if (window.MicDesk && MicDesk.patternGain) g = Math.abs(MicDesk.patternGain(th, fam, pol));
      var rad = 0.9 * g;
      pts.push(new THREE.Vector3(
        o[0] + nn[0] * h + basis.right[0] * rad * Math.sin(th) + basis.fwd[0] * rad * Math.cos(th),
        o[1] + nn[1] * h + basis.right[1] * rad * Math.sin(th) + basis.fwd[1] * rad * Math.cos(th),
        o[2] + nn[2] * h + basis.right[2] * rad * Math.sin(th) + basis.fwd[2] * rad * Math.cos(th)
      ));
    }
    var geo = new THREE.BufferGeometry().setFromPoints(pts);
    var mat = new THREE.LineDashedMaterial({
      color: 0xe8eaef,
      dashSize: 0.06,
      gapSize: 0.045,
      transparent: true,
      opacity: 0.95
    });
    var line = new THREE.Line(geo, mat);
    line.computeLineDistances();
    var group = new THREE.Group();
    group.add(line);
    this._meshes.ideal = group;
    this.root.add(group);
  };

  PolarFieldView.prototype._makeSurfaceFromVertices = function (flat, nB, nAz, color, opacity) {
    var positions = flat;
    if (!(positions instanceof Float32Array)) {
      positions = new Float32Array(flat);
    }
    var colors = [];
    var indices = [];
    var solo = this.soloBand;
    for (var bi = 0; bi < nB; bi++) {
      var band = global.FreqPalette
        ? global.FreqPalette.rgb(global.FreqPalette.at(bi, nB))
        : (global.SpectrumColors
          ? global.SpectrumColors.forIndex(bi, nB).rgb
          : { r: 225, g: 29, b: 72 });
      for (var ai = 0; ai < nAz; ai++) {
        colors.push(band.r / 255, band.g / 255, band.b / 255);
      }
    }
    for (var b = 0; b < nB - 1; b++) {
      if (solo != null) break;
      for (var a = 0; a < nAz; a++) {
        var a2 = (a + 1) % nAz;
        var i0 = b * nAz + a;
        var i1 = b * nAz + a2;
        var i2 = (b + 1) * nAz + a;
        var i3 = (b + 1) * nAz + a2;
        indices.push(i0, i2, i1, i1, i2, i3);
      }
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    geo.setIndex(indices);
    geo.computeVertexNormals();
    var mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      transparent: true,
      opacity: opacity,
      side: THREE.DoubleSide,
      metalness: 0.08,
      roughness: 0.55,
      depthWrite: false
    });
    var mesh = new THREE.Mesh(geo, mat);
    /* Rings plus one azimuth-0 seam. WireframeGeometry diagonals on a
       non-convex figure-8 read as stray flags, and the wrap edge doubled. */
    var linePos = [];
    function pushAt(bi, ai) {
      var ix = (bi * nAz + (ai % nAz)) * 3;
      linePos.push(positions[ix], positions[ix + 1], positions[ix + 2]);
    }
    for (var rb = 0; rb < nB; rb++) {
      if (solo != null && rb !== solo) continue;
      for (var ra = 0; ra < nAz; ra++) {
        pushAt(rb, ra);
        pushAt(rb, ra + 1);
      }
    }
    if (solo == null) {
      for (var sb = 0; sb < nB - 1; sb++) {
        pushAt(sb, 0);
        pushAt(sb + 1, 0);
      }
    }
    var lineGeo = new THREE.BufferGeometry();
    lineGeo.setAttribute("position", new THREE.Float32BufferAttribute(linePos, 3));
    var lineColor = color;
    if (solo != null && global.FreqPalette) lineColor = global.FreqPalette.intAt(solo, nB);
    mesh.add(new THREE.LineSegments(
      lineGeo,
      new THREE.LineBasicMaterial({ color: lineColor, transparent: true, opacity: 0.9 })
    ));
    return mesh;
  };

  PolarFieldView.prototype._makeSurfaceFromGrid = function (grid, nB, nAz, color, opacity) {
    // Fallback: local Y-up cylinder (no plane tilt)
    var positions = [];
    for (var bi = 0; bi < nB; bi++) {
      var y = (bi / Math.max(1, nB - 1)) * 2.4;
      for (var ai = 0; ai < nAz; ai++) {
        var th = (ai / nAz) * Math.PI * 2;
        var r = Math.max(0, Number(grid[bi][ai]) || 0);
        positions.push(r * Math.sin(th), y, r * Math.cos(th));
      }
    }
    return this._makeSurfaceFromVertices(positions, nB, nAz, color, opacity);
  };

  PolarFieldView.prototype.refresh = async function () {
    if (this.meta) this.meta.textContent = "Computing polar…";
    try {
      var body = Object.assign({}, this.getState());
      body.n_az = 72;
      // Optional independent source height for plane tilt (Prepare SY=MY by default)
      if (body.sy == null && body.my != null) body.sy = body.my;
      var res = await fetch("/api/polar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      var data = await res.json();
      if (!data.ok) throw new Error(data.error || "polar failed");
      this.setData(data);
    } catch (err) {
      if (this.meta) this.meta.textContent = "Polar: " + String(err);
    }
  };

  PolarFieldView.prototype.resize = function () {
    if (!this.renderer || !this.canvas) return;
    var w = Math.max(320, this.canvas.clientWidth || 900);
    var h = Math.max(240, this.canvas.clientHeight || 520);
    this.canvas.width = w;
    this.canvas.height = h;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h, false);
  };

  /* One mic, revolved around its front. The drag and the wheel are _bindOrbit. */
  PolarFieldView.prototype.showBalloon = function (spec) {
    this._balloonSpec = spec || null;
    if (!this.root || !this.renderer) return;
    this._look.set(0, 0, 0);
    this._dist = 2.8;
    this._updateCamera();
    this._rebuildBalloon();
  };

  PolarFieldView.prototype._rebuildBalloon = function () {
    if (!this.root) return;
    this._clearMeshes();
    var spec = this._balloonSpec;
    if (!spec || !spec.db || !spec.db.length) return;
    var db = spec.db;
    var nAz = db.length;
    var nTh = Math.floor(nAz / 2) + 1;
    var nPh = 48;
    function lin(dbv) {
      var v = window.RRDb.dbToLin(dbv);
      if (!isFinite(v) || v < 0) v = 0;
      if (v > 1) v = 1;
      return v;
    }
    var positions = [];
    var colors = [];
    var ti, pi, th, ph, r;
    for (ti = 0; ti < nTh; ti++) {
      th = Math.PI * ti / Math.max(1, nTh - 1);
      r = lin(db[ti]);
      for (pi = 0; pi < nPh; pi++) {
        ph = (pi / nPh) * Math.PI * 2;
        positions.push(r * Math.sin(th) * Math.cos(ph), r * Math.sin(th) * Math.sin(ph), r * Math.cos(th));
        colors.push(0.18, 0.83, 0.75);
      }
    }
    var indices = [];
    for (ti = 0; ti < nTh - 1; ti++) {
      for (pi = 0; pi < nPh; pi++) {
        var p2 = (pi + 1) % nPh;
        var i0 = ti * nPh + pi;
        var i1 = ti * nPh + p2;
        var i2 = (ti + 1) * nPh + pi;
        var i3 = (ti + 1) * nPh + p2;
        indices.push(i0, i2, i1, i1, i2, i3);
      }
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    geo.setIndex(indices);
    geo.computeVertexNormals();
    var mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.72,
      side: THREE.DoubleSide,
      metalness: 0.05,
      roughness: 0.45,
      depthWrite: false
    }));
    var rings = new THREE.Group();
    [0, -6, -12, -18, -24].forEach(function (mark) {
      var rad = lin(mark);
      var pts = [];
      var k;
      for (k = 0; k <= 64; k++) {
        var a = (k / 64) * Math.PI * 2;
        pts.push(new THREE.Vector3(rad * Math.sin(a), 0, rad * Math.cos(a)));
      }
      rings.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({ color: 0xd6d3cd, transparent: true, opacity: 0.45 })
      ));
    });
    if (spec.ideal) {
      var idealPts = [];
      var ii;
      for (ii = 0; ii <= 96; ii++) {
        var t = (ii / 96) * Math.PI * 2;
        var g = Math.abs(spec.ideal(t));
        var ir = g > 1 ? 1 : g;
        idealPts.push(new THREE.Vector3(ir * Math.sin(t), 0, ir * Math.cos(t)));
      }
      var iGeo = new THREE.BufferGeometry().setFromPoints(idealPts);
      var iMat = new THREE.LineDashedMaterial({
        color: 0xe8eaef, dashSize: 0.06, gapSize: 0.04, transparent: true, opacity: 0.95
      });
      var iLine = new THREE.Line(iGeo, iMat);
      iLine.computeLineDistances();
      rings.add(iLine);
    }
    rings.add(new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, 0), 1.05, 0xf59e0b, 0.12, 0.06));
    this._meshes.balloon = mesh;
    this._meshes.rings = rings;
    this.root.add(mesh);
    this.root.add(rings);
  };

  PolarFieldView.prototype._animate = function () {
    var self = this;
    function tick() {
      requestAnimationFrame(tick);
      if (self._skipHidden && self.canvas && self.canvas.offsetParent === null) return;
      if (self.renderer && self.scene && self.camera) {
        self.renderer.render(self.scene, self.camera);
      }
    }
    tick();
  };

  global.PolarFieldView = PolarFieldView;
})(window);
