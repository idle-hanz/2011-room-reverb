// Room shape picker, plan outline, and the Surfaces wall list.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const RS = require("../static/js/room_shape.js");
const app = readFileSync(join(here, "../static/js/app.js"), "utf8");
const editor = readFileSync(join(here, "../static/js/room_editor.js"), "utf8");
const math = readFileSync(join(here, "../static/js/room_math.js"), "utf8");
const surfaces = readFileSync(join(here, "../static/js/colour_surfaces.js"), "utf8");
const page = readFileSync(join(here, "../static/index.html"), "utf8");

function liveRequestBodyFrom(state) {
  const start = app.indexOf("function liveRequestBody");
  const end = app.indexOf("function feedbackLawOn", start);
  assert.ok(start > 0 && end > start);
  const src = app.slice(start, end);
  const call = new Function("state", "heardMix", "window", src + "\nreturn liveRequestBody();");
  return call(state, function () { return {}; }, {});
}

function cornerKey(p) {
  return p.px + "," + p.py;
}

test("the picker posts room_shape", () => {
  const rowStart = page.indexOf('id="roomShapeRow"');
  assert.ok(rowStart > 0);
  const row = page.slice(rowStart, rowStart + 420);
  assert.match(row, /data-room-shape="box"/);
  assert.match(row, /aria-pressed="true"/);
  assert.match(row, /data-room-shape="splay"/);
  assert.match(row, />Box</);
  assert.match(row, />Splay</);
  assert.match(app, /room_shape:\s*"box"/);
  assert.match(app, /state\.room_shape = btn\.getAttribute\("data-room-shape"\)/);
  assert.match(app, /mix\.room_shape = String\(state\.room_shape\)/);
  const play = liveRequestBodyFrom({ room_shape: "splay" });
  assert.equal(play.room_shape, "splay");
  const boxed = liveRequestBodyFrom({ room_shape: "box" });
  assert.equal(boxed.room_shape, "box");
  assert.match(page, /room_shape\.js\?v=2/);
  assert.match(page, /app\.js\?v=80/);
});

test("box draws the same outline as now", () => {
  const lay = { ox: 40, oy: 36, scale: 50, L: 8, H: 3 };
  const rw = 6 * lay.scale;
  const rh = 8 * lay.scale;
  const box = RS.floorPx("box", 6, 8, lay);
  const rect = [
    { px: lay.ox, py: lay.oy },
    { px: lay.ox + rw, py: lay.oy },
    { px: lay.ox + rw, py: lay.oy + rh },
    { px: lay.ox, py: lay.oy + rh }
  ];
  assert.deepEqual(box.map(cornerKey).sort(), rect.map(cornerKey).sort());
  assert.deepEqual(RS.floorOutline("box", 6, 8), [[0, 0], [6, 0], [6, 8], [0, 8]]);
  const elev = RS.elevPx("box", 3, 8, { ox: 20, oy: 10, scale: 40, H: 3 });
  const erw = 8 * 40;
  const erh = 3 * 40;
  const erect = [
    { px: 20, py: 10 },
    { px: 20 + erw, py: 10 },
    { px: 20 + erw, py: 10 + erh },
    { px: 20, py: 10 + erh }
  ];
  assert.deepEqual(elev.map(cornerKey).sort(), erect.map(cornerKey).sort());
  assert.match(editor, /RoomShape\.floorPx/);
  const splay = RS.floorOutline("splay", 6, 8);
  assert.deepEqual(splay, [[1, 0], [5, 0], [6, 8], [0, 8]]);
  assert.notEqual(splay[0][0], splay[3][0]);
  const rows = RS.wallRows("splay");
  assert.deepEqual(rows.map(function (r) { return r.id; }), ["sides", "front", "back", "floor", "ceiling"]);
  assert.deepEqual(rows[0].letters, ["A", "C"]);
  assert.equal(rows[0].shared, true);
  rows.slice(1).forEach(function (r) {
    assert.equal(r.shared, false);
    assert.equal(r.letters.length, 1);
  });
  const boxRows = RS.wallRows("box");
  assert.deepEqual(boxRows.map(function (r) { return r.id; }), ["left", "right", "front", "back", "floor", "ceiling"]);
  assert.equal(boxRows[0].shared, false);
  assert.equal(boxRows[1].shared, false);
  assert.deepEqual(boxRows[0].letters, ["A"]);
  assert.deepEqual(boxRows[1].letters, ["C"]);
  const linked = RS.wallRows("box", true);
  assert.equal(linked[0].shared, true);
  assert.deepEqual(linked[0].letters, ["A", "C"]);
  assert.equal(linked[0].label, "Left / Right");
  assert.equal(RS.showMirrorToggle("box"), true);
  assert.equal(RS.showMirrorToggle("splay"), false);
  assert.match(surfaces, /_shareSides/);
  assert.match(surfaces, /Left and right share one material/);
});

test("splay drag stays inside the outline", () => {
  const kept = RS.clampInside(2.6, 1.2, 4.75, 6, 3, 8);
  assert.equal(kept.x, 2.6);
  assert.equal(kept.y, 1.2);
  assert.equal(kept.z, 4.75);
  const outside = RS.clampInside(0, 1.5, 0, 6, 3, 8);
  assert.ok(outside.x > 0.9 && outside.x < 1.2);
  assert.ok(outside.z > 0 && outside.z < 0.01);
  const high = RS.clampInside(3, 3, 0, 6, 3, 8);
  assert.ok(high.y < 0.8125 * 3);
  assert.match(math, /RoomShape\.clampInside/);
  assert.match(editor, /clampRoomSpotPatch/);
});
