/* 3D polar field — mic pattern × frequency in mic–source plane (ASSUMED) */
(function (global) {
  "use strict";

  var COLORS = { L: 0xa78bfa, C: 0x2dd4bf, R: 0x34d399, sum: 0xfbbf24 };

  function PolarFieldView(opts) {
    opts = opts || {};
    this.canvas = opts.canvas || document.getElementById("polarCanvas");
    this.wrap = opts.wrap || document.getElementById("polarWrap");
    this.meta = opts.meta || document.getElementById("polarMeta");
    this.getState = opts.getState || function () { return {}; };
    // Stereo pair story → default Sum only
    this.enabled = { L: false, C: false, R: false, sum: true };
    this.data = null;
    this._dragging = false;
    this._lastX = 0;
    this._lastY = 0;
    this._yaw = 0.85;
    this._pitch = 0.48;
    this._dist = 5.5;
    this._meshes = {};
    this._planeHelper = null;
    if (!this.canvas || typeof THREE === "undefined") {
      if (this.meta) this.meta.textContent = "Three.js unavailable";
      return;
    }
    this._syncToggleUI();
    this._initThree();
    this._bindOrbit();
    this._bindUI();
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
    if (btn) btn.addEventListener("click", function () { self.refresh(); });
  };

  PolarFieldView.prototype.setData = function (data) {
    this.data = data;
    if (data && data.plane && data.plane.origin) {
      var o = data.plane.origin;
      var stack = Number(data.stack_m) || 2.4;
      this._look.set(o[0], o[1] + stack * 0.45, o[2]);
      this._updateCamera();
    }
    this._rebuildMeshes();
    if (this.meta && data) {
      var tilt = data.plane && data.plane.tilt_deg != null
        ? Number(data.plane.tilt_deg).toFixed(1)
        : "—";
      this.meta.textContent =
        (data.n_bands || (data.centres_hz || []).length) + " bands · " +
        (data.n_az || 0) + " az · car/omni " + Number(data.car_omni).toFixed(2) +
        " · plane tilt " + tilt + "° · ASSUMED mic polar×f";
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
        if (ch.material) ch.material.dispose();
      });
      this._planeHelper = null;
    }
  };

  PolarFieldView.prototype._drawPlaneWire = function () {
    if (!this.data || !this.data.plane) return;
    var pl = this.data.plane;
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

  PolarFieldView.prototype._rebuildMeshes = function () {
    if (!this.root || !this.data) return;
    this._clearMeshes();
    this._drawPlaneWire();
    var bands = this.data.centres_hz || [];
    var nAz = this.data.n_az || 0;
    if (!bands.length || !nAz) return;
    var nB = bands.length;
    var self = this;
    ["L", "C", "R", "sum"].forEach(function (key) {
      if (!self.enabled[key]) return;
      var mesh = null;
      if (self.data.vertices && self.data.vertices[key]) {
        mesh = self._makeSurfaceFromVertices(
          self.data.vertices[key], nB, nAz, COLORS[key], key === "sum" ? 0.45 : 0.32
        );
      } else if (self.data[key]) {
        mesh = self._makeSurfaceFromGrid(
          self.data[key], nB, nAz, COLORS[key], key === "sum" ? 0.45 : 0.32
        );
      }
      if (!mesh) return;
      self._meshes[key] = mesh;
      self.root.add(mesh);
    });
  };

  PolarFieldView.prototype._makeSurfaceFromVertices = function (flat, nB, nAz, color, opacity) {
    var positions = flat;
    if (!(positions instanceof Float32Array)) {
      positions = new Float32Array(flat);
    }
    var colors = [];
    var c = new THREE.Color(color);
    var indices = [];
    for (var bi = 0; bi < nB; bi++) {
      var t = bi / Math.max(1, nB - 1);
      for (var ai = 0; ai < nAz; ai++) {
        colors.push(c.r * (0.5 + 0.5 * t), c.g * (0.5 + 0.5 * t), c.b * (0.5 + 0.5 * t));
      }
    }
    for (var b = 0; b < nB - 1; b++) {
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
    mesh.add(new THREE.LineSegments(
      new THREE.WireframeGeometry(geo),
      new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: 0.2 })
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

  PolarFieldView.prototype._animate = function () {
    var self = this;
    function tick() {
      requestAnimationFrame(tick);
      if (self.renderer && self.scene && self.camera) {
        self.renderer.render(self.scene, self.camera);
      }
    }
    tick();
  };

  global.PolarFieldView = PolarFieldView;
})(window);
