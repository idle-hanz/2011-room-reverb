// Plan and tilt keep their raw token on the existing prism. Named presets stay words.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const software = join(here, "..");
const RS = require("../static/js/room_shape.js");
global.RoomShape = RS;
const RD = require("../static/js/room_draw.js");
const room3d = readFileSync(join(software, "static/js/room_3d.js"), "utf8");
const imageViews = readFileSync(join(software, "static/js/image_views.js"), "utf8");

const W = 6;
const H = 3;
const L = 8;
const PLAN = "plan:1.50,0.00,4.50,0.00,6.00,4.00,4.50,8.00,1.50,8.00,0.00,4.00";
const TILT = "tilt:4:0.1";
const SRC = [2.6, 1.2, 4.0];
const REC = [{ id: "C", p: [3.0, 1.5, 5.0] }];

function near(a, b, eps) {
  assert.ok(Math.abs(a - b) <= eps, a + " vs " + b);
}

function faceNamed(faces, name) {
  return faces.filter(function (face) { return face.name === name; });
}

function floorXZ(faces) {
  return faceNamed(faces, "floor")[0].v.map(function (p) { return [p[0], p[2]]; });
}

function assertOutline(shape, label) {
  const faces = RD.polyFaces(shape, W, H, L);
  const want = RS.floorOutline(shape, W, L);
  const got = floorXZ(faces);
  assert.equal(got.length, want.length, label + " corners");
  for (let i = 0; i < want.length; i++) {
    near(got[i][0], want[i][0], 1e-9);
    near(got[i][1], want[i][1], 1e-9);
    faceNamed(faces, "ceiling").forEach(function (ceil) {
      ceil.v.forEach(function (p) {
        if (Math.abs(p[0] - want[i][0]) < 1e-9 && Math.abs(p[2] - want[i][1]) < 1e-9) {
          near(p[1], RS.ceilingAt(shape, want[i][1], H, L), 1e-9);
        }
      });
    });
  }
  return faces;
}

test("normalize still strips plan and tilt to the shoebox word", function () {
  assert.equal(RD.normalize(PLAN), "box");
  assert.equal(RD.normalize(TILT), "box");
  assert.equal(RD.normalize("splay"), "splay");
  assert.equal(RD.normalize("gable"), "gable");
  assert.equal(RD.shellToken("splay"), "splay");
  assert.equal(RD.shellToken("Gable roof"), "gable");
  assert.equal(RD.shellToken("box"), "box");
  assert.equal(RD.shellToken(PLAN), PLAN);
  assert.equal(RD.shellToken(TILT), TILT);
  assert.equal(RD.shellToken(RD.shellToken(PLAN)), PLAN);
});

test("tilt and plan prisms follow the floor outline", function () {
  const tilt = assertOutline(TILT, "tilt");
  const floor = floorXZ(tilt);
  assert.ok(floor[0][0] > 0.1, "tilt front is inset");
  assert.ok(floor[1][0] < W - 0.1, "tilt front is inset");
  const ceilY = faceNamed(tilt, "ceiling")[0].v.map(function (p) { return p[1]; });
  assert.ok(Math.max.apply(null, ceilY) - Math.min.apply(null, ceilY) > 0.1, "tilt ceiling slopes");

  const plan = assertOutline(PLAN, "plan");
  assert.equal(floorXZ(plan).length, 6);
  near(RS.ceilingAt(PLAN, 0, H, L), H, 1e-9);
});

test("box and splay drawings stay on their presets", function () {
  const box = assertOutline("box", "box");
  assert.deepEqual(floorXZ(box), [[0, 0], [W, 0], [W, L], [0, L]]);
  faceNamed(box, "ceiling")[0].v.forEach(function (p) { near(p[1], H, 1e-9); });

  const splay = assertOutline("splay", "splay");
  assert.deepEqual(floorXZ(splay), [[W / 6, 0], [5 * W / 6, 0], [W, L], [0, L]]);
  const ys = faceNamed(splay, "ceiling")[0].v.map(function (p) { return p[1]; });
  assert.ok(Math.max.apply(null, ys) - Math.min.apply(null, ys) > 0.1, "splay ceiling still rises");
});

test("gable stays on the pitched roof", function () {
  const faces = RD.polyFaces("gable", W, H, L);
  assert.equal(faces.length, 7);
  assert.equal(faceNamed(faces, "ceiling").length, 2);
  assert.equal(RD.shellToken("gable"), "gable");
});

test("lattice rooms open for plan and tilt and stay closed for a box", function () {
  const opts = { order: 1, maxDist: 40 };
  assert.equal(RD.imageRooms("box", W, H, L, SRC, REC, opts), null);
  assert.ok(RD.imageRooms("splay", W, H, L, SRC, REC, opts));
  assert.ok(RD.imageRooms(PLAN, W, H, L, SRC, REC, opts));
  assert.ok(RD.imageRooms(TILT, W, H, L, SRC, REC, opts));
});

test("the 3D view and the image views pass the raw token through", function () {
  assert.match(room3d, /RoomDraw\.shellToken/);
  assert.match(imageViews, /RoomDraw\.shellToken/);
  assert.match(room3d, /RoomDraw\.room3dBoxGeometries/);
  assert.match(imageViews, /imageRooms\(polyShape\(\)/);
});
