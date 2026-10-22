// node --test test_t9_room_window.mjs
// T9 room-mic window readouts. Display maths only. Not posted.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const M = createRequire(import.meta.url)("../static/js/room_window_math.js");

test("source metres is the 3D hypot from the source to the room spot", () => {
  assert.equal(M.sourceMetres({ x: 0, y: 0, z: 0 }, { x: 3, y: 0, z: 4 }), 5);
  assert.equal(M.sourceMetres({ x: 1, y: 1, z: 2 }, { x: 1, y: 2, z: 2 }), 1);
  const diag = M.sourceMetres({ x: 2.6, y: 1.2, z: 4.75 }, { x: 1, y: 1.5, z: 6 });
  assert.equal(diag.toFixed(1), Math.hypot(2.6 - 1, 1.2 - 1.5, 4.75 - 6).toFixed(1));
  assert.equal(M.sourceMetres({ x: "2", y: "1", z: "2" }, { x: 2, y: 1, z: 5 }), 3);
});

test("nearest wall is min(x, W-x, z, L-z) and ignores height", () => {
  assert.equal(M.nearestWallMetres({ x: 1.2, z: 0.4 }, 6, 8), 0.4);
  assert.equal(M.nearestWallMetres({ x: 0.3, z: 3 }, 6, 8), 0.3);
  assert.equal(M.nearestWallMetres({ x: 5.5, z: 7.2, y: 9 }, 6, 8), 0.5);
  assert.equal(M.nearestWallMetres({ x: 1, z: 6 }, 6, 8), 1);
  assert.equal(M.nearestWallMetres({ x: 1, z: 6 }, 6, 8).toFixed(1), "1.0");
});
