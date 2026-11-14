// Undo and redo for room size and room_shape. The stack stays off the setup file.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const RS = require("../static/js/room_shape.js");
const page = readFileSync(join(here, "../static/index.html"), "utf8");
const room = readFileSync(join(here, "../static/js/rr_room.js"), "utf8");
const editor = readFileSync(join(here, "../static/js/room_editor.js"), "utf8");
const app = readFileSync(join(here, "../static/js/app.js"), "utf8");
const settings = readFileSync(join(here, "../static/js/rr_settings.js"), "utf8");

function snap(W, H, L, room_shape) {
  return { W: W, H: H, L: L, room_shape: room_shape };
}

test("shape then size undoes back, redo reapplies, and a new edit clears redo", () => {
  const hist = RS.createRoomHistory(50);
  const orig = snap(6, 3, 8, "box");
  const shaped = snap(6, 3, 8, "splay");
  const sized = snap(7, 3, 8, "splay");
  assert.equal(hist.undo(), null);
  assert.equal(hist.note(orig, orig), false);
  assert.equal(hist.note(orig, shaped), true);
  assert.equal(hist.note(shaped, sized), true);
  assert.deepEqual(hist.undo(sized), shaped);
  assert.deepEqual(hist.undo(shaped), orig);
  assert.deepEqual(hist.redo(orig), shaped);
  assert.deepEqual(hist.redo(shaped), sized);
  assert.equal(hist.note(sized, snap(7, 3, 9, "splay")), true);
  assert.equal(hist.redo(), null);
  assert.deepEqual(hist.undo(), sized);
});

test("a drag is one step and a second begin or end does nothing", () => {
  const hist = RS.createRoomHistory(50);
  assert.equal(hist.beginDrag(snap(6, 3, 8, "box")), true);
  assert.equal(hist.beginDrag(snap(1, 1, 2, "hex")), false);
  assert.equal(hist.isDragging(), true);
  assert.equal(hist.endDrag(snap(8, 3, 8, "box")), true);
  assert.equal(hist.endDrag(snap(9, 3, 8, "box")), false);
  assert.equal(hist.isDragging(), false);
  assert.equal(hist.undo().W, 6);
  assert.equal(hist.undo(), null);
  assert.equal(hist.redo().W, 8);
});

test("the stack keeps fifty steps and a box setup gains no history key", () => {
  const hist = RS.createRoomHistory(50);
  const setup = snap(6, 3, 8, "box");
  const raw = JSON.stringify(setup);
  let prev = snap(6, 3, 8, "box");
  let i;
  let n = 0;
  let last = null;
  let step;
  for (i = 1; i <= 60; i++) {
    const next = snap(6 + i, 3, 8, "box");
    hist.note(prev, next);
    prev = next;
  }
  while ((step = hist.undo())) {
    last = step;
    n += 1;
  }
  assert.equal(n, 50);
  assert.equal(last.W, 16);
  hist.note(setup, snap(7, 3, 8, "splay"));
  assert.equal(JSON.stringify(setup), raw);
  assert.deepEqual(Object.keys(JSON.parse(raw)).sort(), ["H", "L", "W", "room_shape"]);
  assert.match(settings, /JSON\.stringify\(state\)/);
  assert.equal(settings.indexOf("undoStack"), -1);
  assert.equal(room.indexOf("state.undo"), -1);
  assert.match(settings, /copy\.face_label_rev = 1/);
});

test("undo applies size through onRoomDim and keeps the shape string", () => {
  const apply = room.slice(room.indexOf("function applyRoomSnap"), room.indexOf("function undoRoom"));
  assert.match(apply, /onRoomDim\("W", next\.W\)/);
  assert.match(apply, /onRoomDim\("H", next\.H\)/);
  assert.match(apply, /onRoomDim\("L", next\.L\)/);
  assert.match(apply, /state\.room_shape = String\(next\.room_shape/);
  assert.equal(apply.indexOf("storedShape"), -1);
  assert.match(apply, /scheduleLiveParams\(\)/);
  assert.match(page, /id="roomUndo"/);
  assert.match(page, /id="roomRedo"/);
  assert.match(room, /roomUndoBtn\.addEventListener\("click", undoRoom\)/);
  assert.match(room, /roomRedoBtn\.addEventListener\("click", redoRoom\)/);
  assert.match(room, /key === "z" && !evt\.shiftKey/);
  assert.match(room, /key === "z" && evt\.shiftKey/);
  assert.match(room, /key === "y"/);
  assert.match(room, /TEXTAREA/);
  assert.match(room, /SELECT/);
  assert.match(room, /type === "number"/);
  assert.equal(room.includes('addEventListener("input"'), false);
  assert.match(room, /function beginRoomDrag\(\)/);
  assert.match(app, /\["W","H","L"\]/);
  assert.match(app, /beginRoomDrag\(\)/);
  assert.match(app, /endRoomDrag\(\)/);
  assert.match(room, /roomRatioRow\.addEventListener\("click", function \(evt\) \{[\s\S]*?\}, true\)/);
  assert.match(editor, /armRoomDrag\(\)/);
  assert.match(editor, /global\.endRoomDrag/);
});
