// Splay 3D is the poly_room prism. Box meshes stay the pre-change snapshot.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const software = join(here, "..");
const THREE = require("../static/js/vendor/three.min.js");
const RD = require("../static/js/room_draw.js");
const fixture = JSON.parse(readFileSync(join(here, "fixture_box_geometry.json"), "utf8"));
const room3d = readFileSync(join(software, "static/js/room_3d.js"), "utf8");
const imageViews = readFileSync(join(software, "static/js/image_views.js"), "utf8");
const page = readFileSync(join(software, "static/index.html"), "utf8");
const app = readFileSync(join(software, "static/js/app.js"), "utf8");

const EPS = 1e-5;
const SRC = [2.6, 1.2, 4.0];
const REC = [3.0, 1.5, 5.0];

function closeVerts(got, exp, label) {
  assert.equal(got.length, exp.length, label + " count");
  for (let i = 0; i < got.length; i++) {
    for (let k = 0; k < 3; k++) {
      const d = Math.abs(got[i][k] - exp[i][k]);
      assert.ok(d <= EPS, label + " [" + i + "," + k + "] " + got[i] + " vs " + exp[i]);
    }
  }
}

function worldPositions(mesh) {
  mesh.updateMatrix();
  const attr = mesh.geometry.getAttribute("position");
  const v = new THREE.Vector3();
  const out = [];
  for (let i = 0; i < attr.count; i++) {
    v.fromBufferAttribute(attr, i).applyMatrix4(mesh.matrix);
    out.push([v.x, v.y, v.z]);
  }
  return out;
}

function partVerts(part) {
  const mat = part.lines
    ? new THREE.LineBasicMaterial()
    : new THREE.MeshBasicMaterial();
  return worldPositions(RD.placePart(THREE, part, mat));
}

function pyOracle() {
  const code = [
    "import json, sys",
    "sys.path.insert(0, 'engine')",
    "from poly_room import faces_for, build_tree, audible",
    "faces = faces_for('splay', 6, 3, 8)",
    "src = (2.6, 1.2, 4.0)",
    "rec = (3.0, 1.5, 5.0)",
    "def pack(order):",
    "    nodes = build_tree(src, faces, order=order, max_dist=340)",
    "    aud = []",
    "    for i, (pos, seq, _parent) in enumerate(nodes):",
    "        if audible(nodes, i, rec, faces):",
    "            aud.append({'seq': list(seq), 'pos': [float(x) for x in pos]})",
    "    return len(nodes), aud",
    "n2, a2 = pack(2)",
    "n4, a4 = pack(4)",
    "print(json.dumps({",
    "  'faces': [{'name': f.name, 'v': [[float(x) for x in p] for p in f.v], 'n': [float(x) for x in f.n]} for f in faces],",
    "  'nodes2': n2, 'audible2': a2, 'nodes4': n4, 'audible4': len(a4)",
    "}))"
  ].join("\n");
  const run = spawnSync(join(software, ".venv/Scripts/python.exe"), ["-c", code], {
    cwd: software,
    encoding: "utf8"
  });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  return JSON.parse(run.stdout);
}

test("box geometry matches the snapshot from before the splay meshes", () => {
  const W = fixture.W;
  const H = fixture.H;
  const L = fixture.L;
  const room = RD.room3dBoxGeometries(THREE, W, H, L);
  ["floor", "front", "back", "left", "right", "ceil", "edges"].forEach(function (name) {
    closeVerts(partVerts(room[name]), fixture.room[name], "room " + name);
  });
  const image = RD.imageBoxGeometries(THREE, W, H, L);
  ["floor", "z0", "zL", "x0", "xW", "ceil", "home"].forEach(function (name) {
    closeVerts(partVerts(image[name]), fixture.image[name], "image " + name);
  });
  const cell = RD.cellEdges(THREE, { x: -6, y: 0, z: 0 }, { x: 0, y: 3, z: 8 });
  closeVerts(partVerts(cell), fixture.image.cell, "image cell");
  const identity = RD.room3dBoxGeometries(THREE, W, H, L, function (z) { return z; });
  assert.ok(Math.abs(room.front.pos[2]) <= EPS);
  assert.ok(Math.abs(identity.front.pos[2] - L) <= EPS);
});

test("splay faces and audible images match poly_room", () => {
  const py = pyOracle();
  const faces = RD.splayFaces(6, 3, 8);
  assert.equal(faces.length, py.faces.length);
  faces.forEach(function (face, i) {
    assert.equal(face.name, py.faces[i].name);
    closeVerts(face.v, py.faces[i].v, face.name);
    closeVerts([face.n], [py.faces[i].n], face.name + " n");
  });
  const ys = faces[1].v.map(function (p) { return p[1]; });
  assert.ok(Math.max.apply(null, ys) - Math.min.apply(null, ys) > 0.4);
  assert.ok(Math.abs(faces[0].v[0][0] - faces[0].v[faces[0].v.length - 1][0]) > 0.5);

  const pack = RD.imageRooms("splay", 6, 3, 8, SRC, [{ id: "C", p: REC }], { order: 2, maxDist: 340 });
  assert.equal(pack.rooms.length, py.audible2.length);
  const bySeq = {};
  pack.rooms.forEach(function (room) { bySeq[room.seq.join(".")] = room.pos; });
  py.audible2.forEach(function (row) {
    const got = bySeq[row.seq.join(".")];
    assert.ok(got, "missing seq " + row.seq);
    closeVerts([got], [row.pos], "pos " + row.seq);
  });

  const wide = RD.imageRooms("splay", 6, 3, 8, SRC, [{ id: "C", p: REC }], { order: 4, maxDist: 340 });
  assert.equal(py.nodes4, 623);
  assert.equal(py.audible4, 118);
  assert.equal(wide.rooms.length, 118);
  assert.equal(RD.imageRooms("box", 6, 3, 8, SRC, [{ id: "C", p: REC }]), null);

  const right = faces[3];
  assert.equal(right.name, "wall1");
  const home = faces[0].v;
  const mirrored = home.map(function (p) { return right.mirror(p); });
  function centroid(ring) {
    const c = [0, 0, 0];
    ring.forEach(function (p) { c[0] += p[0]; c[1] += p[1]; c[2] += p[2]; });
    return c.map(function (v) { return v / ring.length; });
  }
  const shift = centroid(mirrored).map(function (v, k) { return v - centroid(home)[k]; });
  assert.ok(Math.hypot(shift[0] - 6, shift[1], shift[2]) > 0.2);
});

test("heard images fade in 15 ms and walls take the surface colour", () => {
  assert.equal(RD.FADE_MS, 15);
  assert.equal(RD.fadeGain(0, 1, 0), 0);
  assert.equal(RD.fadeGain(0, 1, 7.5), 0.5);
  assert.equal(RD.fadeGain(0, 1, 15), 1);
  assert.equal(RD.fadeGain(1, 0, 15), 0);
  let rows = RD.stepFade({}, ["home"], 0);
  assert.deepEqual(rows.home, { t0: 0, from: 0, to: 1 });
  rows = RD.stepFade(rows, [], 7.5);
  assert.equal(rows.home.from, 0.5);
  assert.equal(rows.home.to, 0);
  rows = RD.stepFade(rows, ["home"], 7.5);
  assert.equal(rows.home.from, 0.5);
  assert.equal(rows.home.to, 1);
  rows = RD.stepFade(rows, [], 7.5);
  rows = RD.stepFade(rows, [], 7.5 + 15);
  assert.equal(rows.home, undefined);

  const shared = { A: { material: "plaster_smooth" } };
  assert.equal(RD.wallColor(shared, "A"), 0xe7e1d6);
  assert.equal(RD.wallColor(shared, "C"), 0xe7e1d6);
  assert.equal(RD.wallColor({}, "E"), 0x78716c);
  assert.equal(RD.wallColor({ E: { material: "wood_parquet" } }, "E"), 0x8b5a2b);
});

test("splay shows the hadamard quota Play uses, and paths hide the lattice", () => {
  const code = [
    "import json, sys",
    "sys.path.insert(0, 'engine')",
    "from poly_room import faces_for, collect_audible, quota_pick, clamp_inside",
    "faces = faces_for('splay', 6, 3, 8)",
    "src = clamp_inside((2.6, 1.2, 4.0), faces)",
    "stand = clamp_inside((3.0, 1.5, 1.5), faces)",
    "images = collect_audible(src, faces, stand, order=4, max_dist=340.0, prune=True)",
    "out = {}",
    "for n in (8, 16, 32, 64, 128):",
    "    chosen = quota_pick(images, stand, n=n)",
    "    out[str(n)] = [{'seq': list(seq), 'pos': [float(x) for x in pos]} for pos, _order, seq in chosen]",
    "print(json.dumps(out))"
  ].join("\n");
  const run = spawnSync(join(software, ".venv/Scripts/python.exe"), ["-c", code], {
    cwd: software,
    encoding: "utf8"
  });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  const py = JSON.parse(run.stdout);
  const stand = [3, 1.5, 1.5];
  [8, 16, 32, 64, 128].forEach(function (n) {
    const pack = RD.imageRooms("splay", 6, 3, 8, SRC, [{ id: "C", p: REC }], {
      order: 4, maxDist: 340, n: n, stand: stand
    });
    const exp = py[String(n)];
    assert.equal(pack.rooms.length, exp.length, "count " + n);
    pack.rooms.forEach(function (room, i) {
      assert.equal(room.seq.join("."), exp[i].seq.join("."), "seq " + n + " " + i);
      closeVerts([room.pos], [exp[i].pos], "pos " + n + " " + i);
    });
  });
  assert.equal(py["32"].length, 32);
  assert.deepEqual(
    RD.latticeKeys("lattice", ["a:home", "a:1", "b:home"]),
    ["a:home", "a:1", "b:home"]
  );
  assert.deepEqual(
    RD.latticeKeys("paths", ["a:home", "a:1", "b:2.3", "b:home"]),
    ["a:home", "b:home"]
  );
  assert.deepEqual(RD.latticeKeys("legs", ["a:home", "a:1"]), ["a:home"]);
  assert.match(imageViews, /RoomDraw\.latticeKeys\(mode/);
  assert.match(imageViews, /mode !== "lattice" && key !== "a:home"/);
  assert.match(imageViews, /n: nTap, stand: stand/);
  assert.match(imageViews, /live && n !== 8 && n !== 16 && n !== 32\) n = 32/);
});

test("the page draws box through RoomDraw and splay through the polygon", () => {
  assert.match(room3d, /RoomDraw\.room3dBoxGeometries/);
  assert.match(room3d, /RoomDraw\.wallColor/);
  assert.match(room3d, /COLORS\.wall/);
  assert.match(room3d, /COLORS\.floor/);
  assert.match(imageViews, /RoomDraw\.cellEdges/);
  assert.match(imageViews, /RoomDraw\.imageBoxGeometries/);
  assert.match(imageViews, /RoomDraw\.imageRooms/);
  assert.match(imageViews, /FADE_MS/);
  assert.match(page, /room_draw\.js\?v=2/);
  assert.match(page, /room_3d\.js\?v=22/);
  assert.match(page, /image_views\.js\?v=19/);
  assert.match(page, /app\.js\?v=81/);
  assert.match(app, /imageView\.tapCount\(\)/);
  assert.match(app, /imageView\.drawnCount\(\)/);
});
