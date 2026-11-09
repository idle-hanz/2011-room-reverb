// node --test test_routing.mjs
// Sections 10 and 13 still pack when a message carries them.
// The page and the Python scene no longer send those fields.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

function loadPackRoom() {
  const code = fs.readFileSync(path.join(HERE, "../static/js/pack_room.js"), "utf8");
  const sandbox = {};
  vm.runInNewContext(code, sandbox);
  return sandbox.packRoom;
}

function pushMessage(params) {
  const live = fs.readFileSync(path.join(HERE, "../static/js/live_fdn.js"), "utf8");
  const start = live.indexOf("msg = {");
  const end = live.indexOf("if (colour.route)", start);
  assert.ok(start > 0 && end > start);
  return new Function(
    "params", "colour", "monoFile", "snapRoom",
    live.slice(start, end) + "\nreturn msg;"
  )(params, { on: false }, false, false);
}

function section(blob, id) {
  const n = blob[3];
  for (let s = 0; s < n; s++) {
    if (blob[5 + s * 4] !== id) continue;
    const off = blob[6 + s * 4];
    const len = blob[7 + s * 4];
    return Array.from(blob.slice(off, off + len));
  }
  return null;
}

test("master room crush reaches the worklet as section 10", () => {
  const packRoom = loadPackRoom();
  const bloom = Array(40).fill(0);
  bloom[0] = 2;
  bloom[1] = 12;
  const on = pushMessage({ ok: true, g: 0.5, bloom: bloom, predelay_n: 0, pre_colour: null });
  const packed = section(packRoom(on), 10);
  assert.ok(packed);
  assert.equal(packed.length, 40);
  assert.equal(packed[0], 2);
  assert.equal(packed[1], 12);
  const off = pushMessage({ ok: true, g: 0.5 });
  assert.equal(section(packRoom(off), 10), null);
  assert.equal(section(packRoom(off), 12), null);
});

test("an on array strip reaches the worklet as section 13", () => {
  const packRoom = loadPackRoom();
  const side = Array(217).fill(0);
  side[3] = 1;
  side[85] = 2;
  side[86] = 1;
  const on = pushMessage({ ok: true, g: 0.5, side: side });
  const packed = section(packRoom(on), 13);
  assert.ok(packed);
  assert.equal(packed.length, 217);
  assert.equal(packed[85], 2);
  assert.equal(packed[86], 1);
  const off = pushMessage({ ok: true, g: 0.5 });
  assert.equal(section(packRoom(off), 13), null);
});
