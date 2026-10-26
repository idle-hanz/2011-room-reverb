// SL6 Amount. The post copy scales accepted coverage. Shell and suggested rows stay.
// At 100% the stored surf_cal is the same list. Below 100% the key is omitted.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { appSource as app } from "./app_sources.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const panel = fs.readFileSync(path.join(HERE, "../static/js/sl_room_result.js"), "utf8");
const PROVED = [1, 1, 1, 0.850, 0.878, 0.870, 0.906];

function loadApply() {
  const start = app.indexOf("function applyTreatAmount");
  const end = app.indexOf("window.RRApplyTreatAmount", start);
  assert.ok(start > 0 && end > start);
  const src = app.slice(start, end);
  return new Function(`${src}\nreturn applyTreatAmount;`)();
}

const applyTreatAmount = loadApply();

function scene(amount) {
  const row = { id: "acc_d", face: "D", type: "membrane", coverage: 0.5, on: true };
  const shell = { id: "shell_A", face: "A", type: "shell", coverage: 0.3, on: true };
  const sug = { id: "sug", face: "F", type: "porous", coverage: 0.21, suggested: true };
  const body = {
    decay_lock: true,
    surf_amount: amount,
    surf_cal: PROVED.slice(),
    surf_treatment: [row, shell, sug],
  };
  return { body, row, shell, sug };
}

test("missing amount posts today's rows and the stored calibration", () => {
  const row = { id: "acc", face: "D", type: "helmholtz", coverage: 0.474 };
  const cal = PROVED.slice();
  const body = { decay_lock: true, surf_treatment: [row], surf_cal: cal };
  const out = applyTreatAmount(body);
  assert.equal(out.surf_treatment[0].coverage, 0.474);
  assert.equal(out.surf_treatment[0] === row, false);
  assert.equal(row.coverage, 0.474);
  assert.equal(out.surf_cal, cal);
  assert.equal(out.decay_lock, true);
});

test("100% posts the proved surf_cal and leaves stored coverage", () => {
  const { body, row, shell, sug } = scene(100);
  const out = applyTreatAmount(body);
  assert.deepEqual(out.surf_cal, PROVED);
  assert.equal(out.surf_cal, body.surf_cal);
  assert.equal(out.surf_treatment[0].coverage, 0.5);
  assert.equal(out.surf_treatment[1].coverage, 0.3);
  assert.equal(out.surf_treatment[2].coverage, 0.21);
  assert.equal(row.coverage, 0.5);
  assert.equal(shell.coverage, 0.3);
  assert.equal(sug.coverage, 0.21);
  assert.equal(out.surf_treatment[0] === row, false);
});

test("below 100% scales accepted coverage, skips shell and suggested, omits surf_cal", () => {
  const { body, row, shell, sug } = scene(50);
  const post = Object.assign({}, body);
  const out = applyTreatAmount(post);
  assert.equal(out.surf_treatment[0].coverage, 0.25);
  assert.equal(out.surf_treatment[1].coverage, 0.3);
  assert.equal(out.surf_treatment[2].coverage, 0.21);
  assert.equal(Object.prototype.hasOwnProperty.call(out, "surf_cal"), false);
  assert.deepEqual(body.surf_cal, PROVED);
  assert.equal(body.surf_treatment[0], row);
  assert.equal(row.coverage, 0.5);
  assert.equal(shell.coverage, 0.3);
  assert.equal(sug.coverage, 0.21);
  assert.equal(body.decay_lock, true);
});

test("0% zeroes accepted coverage and a scene with no rows gains no treatment key", () => {
  const { body, row } = scene(0);
  const out = applyTreatAmount(body);
  assert.equal(out.surf_treatment[0].coverage, 0);
  assert.equal(row.coverage, 0.5);
  const bare = { decay_mode: "flat", decay_lock: true };
  const same = applyTreatAmount(bare);
  assert.equal(Object.prototype.hasOwnProperty.call(same, "surf_treatment"), false);
  assert.equal(Object.prototype.hasOwnProperty.call(same, "surf_cal"), false);
  assert.equal(same.decay_lock, true);
});

test("the proved list is not a client default", () => {
  assert.equal(app.includes("0.850"), false);
  assert.equal(app.includes("0.878"), false);
  assert.equal(panel.includes("0.850"), false);
  const call = app.indexOf("applyTreatAmount(o);");
  assert.ok(call > app.indexOf("function heardMix"));
  assert.ok(call < app.indexOf("function applyTreatAmount"));
});

test("the Amount drag refreshes the graph and posts Play on pointer release", () => {
  const inputAt = panel.indexOf('amt.addEventListener("input"');
  const inputEnd = panel.indexOf("function postAmount", inputAt);
  const upAt = panel.indexOf('amt.addEventListener("pointerup"');
  assert.ok(inputAt > 0 && inputEnd > inputAt && upAt > inputEnd);
  const input = panel.slice(inputAt, inputEnd);
  assert.equal(input.includes("RRPushLive"), false);
  assert.equal(input.includes("postAmount"), false);
  assert.equal(input.includes("schedule()"), true);
  assert.equal(panel.includes('amt.addEventListener("pointerup", function () { amountDrag = false; postAmount(); })'), true);
  assert.equal(panel.includes('if (url === "/api/room_result" && window.RRApplyTreatAmount)'), true);
  assert.equal(panel.includes('if (url === "/api/room_result" && window.RRApplyTreatDecay)'), true);
  assert.equal(panel.includes("Decay lock is on"), true);
});

function loadDecay() {
  const start = app.indexOf("function applyTreatDecay");
  const end = app.indexOf("window.RRApplyTreatDecay", start);
  assert.ok(start > 0 && end > start);
  return new Function(`${app.slice(start, end)}\nreturn applyTreatDecay;`)();
}

const applyTreatDecay = loadDecay();

test("a missing switch leaves the lock, and Flat keeps it when the switch is on", () => {
  const locked = { decay_mode: "surfaces", decay_lock: true, decay_s: 1.8 };
  assert.equal(applyTreatDecay(locked).decay_lock, true);
  const flat = { decay_mode: "flat", decay_lock: true, decay_s: 1.8, treat_sets_decay: true };
  assert.equal(applyTreatDecay(flat).decay_lock, true);
  assert.equal(flat.decay_s, 1.8);
});

test("Surfaces with the switch on posts the lock off and does not invent a dial", () => {
  const body = { decay_mode: "surfaces", decay_lock: true, decay_s: 1.8, treat_sets_decay: true };
  const out = applyTreatDecay(body);
  assert.equal(out.decay_lock, false);
  assert.equal(out.decay_s, 1.8);
  assert.equal(out.treat_sets_decay, true);
});

test("Treatment sets decay sits beside Amount and posts Play once", () => {
  const amt = panel.indexOf('amt.id = "slAutoAmount"');
  const sw = panel.indexOf('sw.id = "slTreatDecay"');
  assert.ok(amt > 0 && sw > amt);
  assert.equal(panel.includes("SL_STAGE"), false);
  assert.equal(panel.includes("Treatment sets decay"), true);
  assert.equal(panel.includes("return !!(s && s.treat_sets_decay);"), true);
  const changeAt = panel.indexOf('box.addEventListener("change"');
  const changeEnd = panel.indexOf("panel.appendChild(at)", changeAt);
  const change = panel.slice(changeAt, changeEnd);
  assert.equal(change.includes("schedule()"), true);
  assert.equal(change.includes("if (window.RRPushLive) window.RRPushLive();"), true);
  assert.equal(panel.includes("s.decay_lock = !!held.decay_lock"), true);
  assert.equal(panel.includes("if (!s.treat_sets_decay) held = null"), true);
  const call = app.indexOf("applyTreatDecay(o);");
  assert.ok(call > app.indexOf("applyTreatAmount(o);"));
  assert.ok(call < app.indexOf("function applyTreatDecay"));
});
