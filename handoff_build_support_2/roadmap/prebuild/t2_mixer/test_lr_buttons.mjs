// node --test test_lr_buttons.mjs  — truth table (THURSDAY_LIST U7 / D-UI31) + null tests
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const M = createRequire(import.meta.url)("./lr_buttons.js");

const TABLE = [
  // l,  r,  msMid, route,  phase, mute,  pot
  [ 1,  0, false, "l",    1, false, "none"],
  [ 0,  1, false, "r",    1, false, "none"],
  [ 1,  1, false, "pan",  1, false, "balance"],
  [ 1,  1, true,  "both", 1, false, "none"],
  [ 1, -1, false, "s",    1, false, "width"],
  [-1,  1, false, "s",   -1, false, "width"],
  [-1,  0, false, "l",   -1, false, "none"],
  [ 0, -1, false, "r",   -1, false, "none"],
  [-1, -1, false, "pan", -1, false, "balance"],
  [-1, -1, true,  "both",-1, false, "none"],
  [ 0,  0, false, null,   1, true,  "none"],
  [ 1, -1, true,  "s",    1, false, "width"],
];
test("truth table: every button pair maps to the right route/phase/pot", () => {
  for (const [l, r, ms, route, phase, mute, pot] of TABLE) {
    const t = M.toRoute({ l, r }, { msMid: ms });
    assert.deepEqual(t, { route, phase, mute, pot }, `l=${l} r=${r} msMid=${ms}`);
  }
});
test("all 9 button states are reachable and distinct (non-MS)", () => {
  const seen = new Set();
  for (const l of [-1, 0, 1]) for (const r of [-1, 0, 1]) {
    const t = M.toRoute({ l, r }, {});
    seen.add(`${t.route}|${t.phase}|${t.mute}`);
  }
  assert.equal(seen.size, 9); // 3x3 button states give 9 different engine states
});
test("cycle off -> on -> Ø -> off", () => {
  assert.equal(M.cycle(0), 1); assert.equal(M.cycle(1), -1); assert.equal(M.cycle(-1), 0);
});
test("null test: every legacy route x phase x pan gives identical weights after mapping", () => {
  const routes = ["l", "r", "s", "both", "centre", "pan"];
  for (const route of routes) for (const ph of [1, -1]) for (const ms of [false, true])
    for (const pan of route === "pan" ? [-1, -0.4, 0, 0.3, 1] : [0, 0.7]) {
      const before = M.weights(route, 0.8, pan, ph);
      const f = M.fromRoute(route, ph, false, { msMid: ms, pan });
      const t = M.toRoute(f.btn, { msMid: ms, legacyBoth: f.legacyBoth, forcePan: f.forcePan });
      const pan2 = f.patch.pan === 0 ? 0 : pan;
      const after = M.weights(t.route, 0.8, pan2, t.phase);
      assert.ok(Math.abs(before[0] - after[0]) < 1e-12 && Math.abs(before[1] - after[1]) < 1e-12,
        `${route} ph=${ph} ms=${ms} pan=${pan}: ${before} vs ${after}`);
    }
});
test("MS classic scene: S on L, Mid on C (both), R muted", () => {
  const st = { pair_mode: "ms", ms_s: "l", ms_m: "c", mic_route_l: "s", mic_route_c: "both",
               mic_route_r: "pan", phase_l: 1, phase_c: 1, phase_r: 1, mute_l: false, mute_c: false, mute_r: true };
  assert.deepEqual(M.fromRoute(st.mic_route_l, 1, false, { msMid: false }).btn, { l: 1, r: -1 });
  const c = M.fromRoute(st.mic_route_c, 1, false, { msMid: M.isMsMid(st, "c") });
  assert.deepEqual(c.btn, { l: 1, r: 1 }); assert.equal(c.legacyBoth, false);
  // Clicking L on the muted R strip un-mutes it as hard-left
  const p = M.clickPatch(st, "r", "l");
  assert.deepEqual(p.patch, { mute_r: false, mic_route_r: "l", phase_r: 1 });
});
test("ORTF L strip (pan hard left) shows L only; clicking R gives L+R at the centre detent", () => {
  const st = { pair_mode: "stereo", mic_route_l: "pan", phase_l: 1, mute_l: false, pan_l: -1 };
  assert.deepEqual(M.fromRoute("pan", 1, false, { pan: -1 }).btn, { l: 1, r: 0 });
  const p = M.clickPatch(st, "l", "r");
  assert.deepEqual(p.patch, { mute_l: false, mic_route_l: "pan", phase_l: 1, pan_l: 0 });
  assert.equal(p.pot, "balance");
  // clicking L on it flips polarity, still hard left
  assert.deepEqual(M.clickPatch(st, "l", "l").patch, { mute_l: false, mic_route_l: "l", phase_l: -1 });
});
test("a panned strip (L+R lit): R on -> Ø makes the side signal", () => {
  const st = { pair_mode: "stereo", mic_route_l: "pan", phase_l: 1, mute_l: false, pan_l: -0.4 };
  const p = M.clickPatch(st, "l", "r");
  assert.deepEqual(p.patch, { mute_l: false, mic_route_l: "s", phase_l: 1 });
  assert.equal(p.pot, "width");
  assert.deepEqual(M.clickPatch(st, "l", "l").patch, { mute_l: false, mic_route_l: "s", phase_l: -1 });
});
test("centre migrates to pan at 0 (same weights under the locked linear law)", () => {
  const f = M.fromRoute("centre", 1, false, {});
  assert.deepEqual(f.btn, { l: 1, r: 1 }); assert.equal(f.patch.pan, 0);
  const st = { mic_route_c: "centre", phase_c: 1, mute_c: false, pan_c: 0.6 };
  const p = M.clickPatch(st, "c", "r");  // r: 1 -> -1 => s
  assert.equal(p.patch.mic_route_c, "s");
});
test("legacy 'both' on a non-Mid strip is kept as both (no level jump)", () => {
  const f = M.fromRoute("both", 1, false, { msMid: false });
  assert.equal(f.legacyBoth, true);
  assert.equal(M.toRoute(f.btn, { legacyBoth: true }).route, "both");
});
test("Mid strip already on pan/centre stays pan (guards the +6 dB jump)", () => {
  const f = M.fromRoute("centre", 1, false, { msMid: true });
  assert.equal(f.forcePan, true);
  assert.equal(M.toRoute(f.btn, { msMid: true, forcePan: true }).route, "pan");
});
test("labels and pot names are plain words", () => {
  assert.equal(M.buttonLabel("l", -1).text, "L\u00d8");
  assert.match(M.buttonLabel("r", 0).title, /right speaker/);
  assert.equal(M.potLabel("width"), "Width");
});
