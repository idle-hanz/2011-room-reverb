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
  const row = page.slice(rowStart, rowStart + 1100);
  assert.match(row, /data-room-shape="box"/);
  assert.match(row, /aria-pressed="true"/);
  assert.match(row, /data-room-shape="splay"/);
  assert.match(row, /data-room-shape="lede"/);
  assert.match(row, /data-room-shape="live"/);
  assert.match(row, /data-room-shape="gable"/);
  assert.match(row, /data-room-shape="hex"/);
  assert.match(row, />Box</);
  assert.match(row, />Splay</);
  assert.match(row, />LEDE</);
  assert.match(row, />Live room</);
  assert.match(row, />Gable</);
  assert.match(row, />Hex</);
  assert.match(app, /room_shape:\s*"box"/);
  assert.match(app, /RoomShape\.normalize\(picked\)/);
  assert.match(app, /mix\.room_shape = String\(state\.room_shape\)/);
  const play = liveRequestBodyFrom({ room_shape: "splay" });
  assert.equal(play.room_shape, "splay");
  const boxed = liveRequestBodyFrom({ room_shape: "box" });
  assert.equal(boxed.room_shape, "box");
  assert.equal(liveRequestBodyFrom({ room_shape: "lede" }).room_shape, "lede");
  assert.equal(liveRequestBodyFrom({ room_shape: "live" }).room_shape, "live");
  assert.equal(liveRequestBodyFrom({ room_shape: "gable" }).room_shape, "gable");
  assert.equal(liveRequestBodyFrom({ room_shape: "hex" }).room_shape, "hex");
  assert.match(page, /room_shape\.js\?v=7/);
  assert.match(page, /app\.js\?v=84/);
  assert.match(app, /function applyRoomShape/);
  assert.match(app, /RoomShape\.bindShapeRows\(roomShapeRows\(\), applyRoomShape\)/);
  assert.match(app, /RoomShape\.paintShapeRows\(roomShapeRows\(\), name\)/);
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
  assert.equal(linked[0].label, "Left + Right (mirrored)");
  assert.equal(rows[0].label, "Left + Right (mirrored)");
  assert.equal(RS.showMirrorToggle("box"), true);
  assert.equal(RS.showMirrorToggle("splay"), false);
  assert.equal(RS.showMirrorToggle("lede"), false);
  assert.equal(RS.showMirrorToggle("live"), false);
  assert.equal(RS.lrSymmetric("splay"), true);
  assert.equal(RS.lrSymmetric("lede"), true);
  assert.equal(RS.lrSymmetric("live"), true);
  assert.equal(RS.sidesLinked("lede", false), true);
  assert.equal(RS.sidesLinked("live", false), true);
  assert.equal(RS.sidesLinked("box", false), false);
  assert.equal(RS.normalize("Gable roof"), "gable");
  assert.equal(RS.showMirrorToggle("gable"), false);
  assert.equal(RS.lrSymmetric("gable"), true);
  assert.equal(RS.sidesLinked("gable", false), true);
  assert.deepEqual(RS.floorOutline("gable", 6, 8), [[0, 0], [6, 0], [6, 8], [0, 8]]);
  assert.deepEqual(RS.planGuides("gable", 6, 8), [[[3, 0], [3, 8]]]);
  assert.deepEqual(RS.planGuides("box", 6, 8), []);
  assert.deepEqual(RS.elevGuides("gable", 3, 8), [[[0, 2.25], [8, 2.25]]]);
  assert.equal(RS.roofHeight(0, 6, 3), 2.25);
  assert.equal(RS.roofHeight(3, 6, 3), 3);
  assert.equal(RS.roofHeight(6, 6, 3), 2.25);
  const gableRows = RS.wallRows("gable", false);
  assert.deepEqual(gableRows.map(function (r) { return r.id; }), ["sides", "gable0", "gable2", "floor", "roofL", "roofR"]);
  assert.equal(gableRows[0].label, "Left + Right (mirrored)");
  assert.equal(gableRows[0].shared, true);
  assert.deepEqual(gableRows[0].letters, ["A", "C"]);
  assert.equal(gableRows[1].label, "Gable end");
  assert.deepEqual(gableRows[1].letters, ["D"]);
  assert.equal(gableRows[2].label, "Gable end");
  assert.deepEqual(gableRows[2].letters, ["B"]);
  assert.equal(gableRows[4].label, "Left roof");
  assert.deepEqual(gableRows[4].letters, ["F"]);
  assert.equal(gableRows[5].label, "Right roof");
  assert.deepEqual(gableRows[5].letters, ["F"]);
  assert.equal(RS.normalize("Hexagon"), "hex");
  assert.equal(RS.showMirrorToggle("hex"), false);
  assert.equal(RS.lrSymmetric("hex"), true);
  assert.equal(RS.sidesLinked("hex", false), true);
  assert.deepEqual(RS.floorOutline("hex", 6, 8), [
    [1.5, 0], [4.5, 0], [6, 4], [4.5, 8], [1.5, 8], [0, 4]
  ]);
  assert.deepEqual(RS.planGuides("hex", 6, 8), []);
  assert.deepEqual(RS.elevOutline("hex", 3, 8), [[0, 0], [8, 0], [8, 3], [0, 3]]);
  const hexRows = RS.wallRows("hex", false);
  assert.deepEqual(hexRows.map(function (r) { return r.id; }), ["sides", "sides2", "front", "back", "floor", "ceiling"]);
  hexRows.slice(0, 2).forEach(function (r) {
    assert.equal(r.shared, true);
    assert.equal(r.label, "Left + Right (mirrored)");
    assert.deepEqual(r.letters, ["A", "C"]);
  });
  assert.equal(hexRows[2].shared, false);
  assert.equal(hexRows[2].label, "Front");
  assert.deepEqual(hexRows[2].letters, ["B"]);
  assert.equal(hexRows[3].shared, false);
  assert.equal(hexRows[3].label, "Back");
  assert.deepEqual(hexRows[3].letters, ["D"]);
  assert.deepEqual(hexRows[4].letters, ["E"]);
  assert.deepEqual(hexRows[5].letters, ["F"]);
  assert.match(editor, /RoomShape\.planGuidesPx/);
  assert.match(editor, /RoomShape\.elevGuidesPx/);
  const z1 = (2 / 7) * 8;
  assert.deepEqual(RS.floorOutline("lede", 6, 8), [
    [1.5, 0], [4.5, 0], [6, z1], [6, 8], [0, 8], [0, z1]
  ]);
  const inset = Math.min(0.25 * 6, 8 * Math.tan((6 * Math.PI) / 180));
  assert.deepEqual(RS.floorOutline("live", 6, 8), [
    [inset, 0], [6 - inset, 0], [6, 8], [0, 8]
  ]);
  const ledeRows = RS.wallRows("lede");
  assert.deepEqual(ledeRows.map(function (r) { return r.id; }), ["sides", "sides2", "front", "back", "floor", "ceiling"]);
  ledeRows.slice(0, 2).forEach(function (r) {
    assert.equal(r.shared, true);
    assert.equal(r.label, "Left + Right (mirrored)");
    assert.deepEqual(r.letters, ["A", "C"]);
  });
  const liveRows = RS.wallRows("live", false);
  assert.deepEqual(liveRows.map(function (r) { return r.id; }), ["sides", "front", "back", "floor", "ceiling"]);
  assert.equal(liveRows[0].label, "Left + Right (mirrored)");
  assert.equal(liveRows[0].shared, true);
  assert.match(surfaces, /_shareSides/);
  assert.match(surfaces, /Left and right share one material/);
  assert.match(surfaces, /RoomShape\.sidesLinked/);
});

function shapeChip(shape, on) {
  const classes = new Set(on ? ["chip", "active"] : ["chip"]);
  return {
    attrs: { "data-room-shape": shape, "aria-pressed": on ? "true" : "false" },
    classList: {
      toggle(name, force) {
        if (force) classes.add(name);
        else classes.delete(name);
      },
      contains(name) { return classes.has(name); }
    },
    getAttribute(key) { return this.attrs[key]; },
    setAttribute(key, value) { this.attrs[key] = String(value); },
    addEventListener(type, fn) {
      if (type === "click") this.onclick = fn;
    },
    click() { this.onclick(); }
  };
}

function shapeRow(pressed) {
  const names = ["box", "splay", "lede", "live", "gable", "hex"];
  const buttons = names.map(function (name) { return shapeChip(name, name === pressed); });
  return {
    querySelectorAll(sel) {
      if (sel !== "[data-room-shape]") throw new Error(sel);
      return buttons;
    },
    buttons: buttons
  };
}

function pressedName(row) {
  const on = row.buttons.filter(function (btn) {
    return btn.getAttribute("aria-pressed") === "true" && btn.classList.contains("active");
  });
  assert.equal(on.length, 1);
  return on[0].getAttribute("data-room-shape");
}

test("the space picker shares room_shape with the room picker", () => {
  const views = page.indexOf('id="imageViews"');
  const spaceStart = page.indexOf('id="spaceShapeRow"');
  assert.ok(views > 0 && spaceStart > views);
  const row = page.slice(spaceStart, spaceStart + 1100);
  assert.match(row, /aria-label="Room shape"/);
  assert.match(row, /class="chip active" data-room-shape="box" aria-pressed="true"/);
  ["splay", "lede", "live", "gable", "hex"].forEach(function (name) {
    assert.match(row, new RegExp('data-room-shape="' + name + '"'));
  });
  assert.match(row, />Box</);
  assert.match(row, />Splay</);
  assert.match(row, />LEDE</);
  assert.match(row, />Live room</);
  assert.match(row, />Gable</);
  assert.match(row, />Hex</);
  const applyStart = app.indexOf("function applyRoomShape");
  const applyEnd = app.indexOf("function paintRoomShape", applyStart);
  assert.ok(applyStart > 0 && applyEnd > applyStart);
  const apply = app.slice(applyStart, applyEnd);
  assert.match(apply, /RoomMath\.clampRoom/);
  assert.match(apply, /syncUI\(\)/);
  assert.match(apply, /scheduleLiveParams\(\)/);
  assert.match(apply, /scheduleImagesFetch\(0\)/);
  assert.match(app, /getElementById\("roomShapeRow"\)/);
  assert.match(app, /getElementById\("spaceShapeRow"\)/);
  assert.equal(app.split("bindShapeRows(").length - 1, 1);

  const room = shapeRow("box");
  const space = shapeRow("box");
  let shape = "box";
  RS.bindShapeRows([room, space], function (picked) {
    shape = RS.normalize(picked);
    RS.paintShapeRows([room, space], shape);
  });
  space.buttons[5].click();
  assert.equal(shape, "hex");
  assert.equal(pressedName(room), "hex");
  assert.equal(pressedName(space), "hex");
  room.buttons[1].click();
  assert.equal(shape, "splay");
  assert.equal(pressedName(room), "splay");
  assert.equal(pressedName(space), "splay");
  space.buttons[0].click();
  assert.equal(shape, "box");
  assert.equal(pressedName(room), "box");
  assert.equal(pressedName(space), "box");
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
  const ledeKept = RS.clampInside(2.6, 1.2, 4.75, 6, 3, 8, "lede");
  assert.equal(ledeKept.x, 2.6);
  assert.equal(ledeKept.z, 4.75);
  const ledeOut = RS.clampInside(0.05, 1.2, 0.2, 6, 3, 8, "lede");
  assert.ok(ledeOut.x > 0.2);
  assert.ok(ledeOut.z > 0 && ledeOut.z < 0.3);
  const liveKept = RS.clampInside(3, 1.5, 1.5, 6, 3, 8, "live");
  assert.equal(liveKept.x, 3);
  assert.equal(liveKept.y, 1.5);
  const insetY = Math.min(0.45 * 3, 8 * Math.tan((6 * Math.PI) / 180));
  const liveHigh = RS.clampInside(3, 3, 0, 6, 3, 8, "live");
  assert.ok(liveHigh.y < (3 - insetY) + 1e-3);
  const gableKept = RS.clampInside(2.6, 1.2, 4.75, 6, 3, 8, "gable");
  assert.equal(gableKept.x, 2.6);
  assert.equal(gableKept.y, 1.2);
  assert.equal(gableKept.z, 4.75);
  const gableCorner = RS.clampInside(0, 1.2, 0, 6, 3, 8, "gable");
  assert.ok(gableCorner.x < 0.01);
  assert.ok(gableCorner.z < 0.01);
  const gableEave = RS.clampInside(0, 2.9, 4, 6, 3, 8, "gable");
  assert.ok(gableEave.y < 2.26);
  assert.ok(gableEave.y > 2.2);
  const gableRidge = RS.clampInside(3, 3, 4, 6, 3, 8, "gable");
  assert.ok(gableRidge.y > 2.99);
  assert.ok(gableRidge.y < 3);
  const hexKept = RS.clampInside(2.6, 1.2, 4.75, 6, 3, 8, "hex");
  assert.equal(hexKept.x, 2.6);
  assert.equal(hexKept.y, 1.2);
  assert.equal(hexKept.z, 4.75);
  const hexCorner = RS.clampInside(0.05, 1.2, 0.05, 6, 3, 8, "hex");
  assert.ok(hexCorner.x > 1.4);
  assert.ok(hexCorner.x < 1.6);
  assert.ok(hexCorner.z > 0 && hexCorner.z < 0.06);
  const hexHigh = RS.clampInside(3, 3, 4, 6, 3, 8, "hex");
  assert.ok(hexHigh.y > 2.99);
  assert.ok(hexHigh.y < 3);
});
