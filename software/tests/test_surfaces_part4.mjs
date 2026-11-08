// Part 4. One length switch, one auto-treat button, diagram face pick, graph paint.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const panel = fs.readFileSync(path.join(here, "../static/js/sl_room_result.js"), "utf8");
const editor = fs.readFileSync(path.join(here, "../static/js/room_editor.js"), "utf8");
const page = fs.readFileSync(path.join(here, "../static/index.html"), "utf8");

function faceFns() {
  const start = editor.indexOf("function faceLetter");
  const end = editor.indexOf("function noteFaceMove");
  assert.ok(start > 0 && end > start);
  return new Function(`${editor.slice(start, end)}\nreturn { faceLetter: faceLetter, hitFloorEdge: hitFloorEdge };`)();
}

test("a diagram click names one face and a corner does not", () => {
  const { faceLetter, hitFloorEdge } = faceFns();
  assert.equal(faceLetter({ walls: ["x0"] }), "A");
  assert.equal(faceLetter({ walls: ["x1"] }), "C");
  assert.equal(faceLetter({ walls: ["z1"] }), "B");
  assert.equal(faceLetter({ walls: ["z0"] }), "D");
  assert.equal(faceLetter({ walls: ["y1"] }), "F");
  assert.equal(faceLetter({ walls: ["x1", "z1"] }), "");
  const elay = { ox: 10, oy: 20, scale: 40, L: 8, H: 3 };
  assert.equal(hitFloorEdge(10 + 4 * 40, 20 + 3 * 40, elay), true);
  assert.equal(hitFloorEdge(10 + 4 * 40, 20, elay), false);
  const floorDown = editor.indexOf('floorCanvas.addEventListener("pointerdown"');
  const floorMove = editor.indexOf('floorCanvas.addEventListener("pointermove"');
  const floor = editor.slice(floorDown, floorMove);
  assert.ok(floor.indexOf("hitFloor") < floor.indexOf("hitWall"));
  assert.match(floor, /kind:\s*"wall"/);
  assert.match(editor, /RRColourSurfaces/);
  assert.match(editor, /mode:\s*"stop"/);
});

test("materials stay first and EQ sits under Advanced", () => {
  const chips = page.indexOf('id="materialChips"');
  const absorb = page.indexOf('id="absorbCanvas"');
  const adv = page.indexOf('id="surfacesAdvanced"');
  const eq = page.indexOf('id="eqCanvas"');
  const smear = page.indexOf('id="jitterSlider"');
  assert.ok(chips > 0 && chips < absorb && absorb < adv && adv < eq && eq < smear);
  assert.match(page, /drag a wall or corner to resize/);
  assert.match(page, /drag the ceiling to resize/);
});

function makeEl() {
  const el = {
    id: "",
    className: "",
    textContent: "",
    hidden: false,
    disabled: false,
    title: "",
    value: "",
    checked: false,
    type: "",
    dataset: {},
    style: {},
    children: [],
    attrs: {},
  };
  el.classList = { toggle() {}, add() {}, remove() {} };
  el.setAttribute = (k, v) => { el.attrs[k] = String(v); };
  el.getAttribute = (k) => (Object.prototype.hasOwnProperty.call(el.attrs, k) ? el.attrs[k] : null);
  el.appendChild = (child) => {
    el.children.push(child);
    if (child && child.id && el.owner) el.owner.els[child.id] = child;
    return child;
  };
  el.insertBefore = (child) => el.appendChild(child);
  el.addEventListener = (type, fn) => {
    el._on = el._on || {};
    el._on[type] = fn;
  };
  el.querySelector = () => null;
  el.querySelectorAll = () => [];
  Object.defineProperty(el, "innerHTML", {
    get() { return ""; },
    set() { el.children = []; },
  });
  return el;
}

function bootPanel(state, fetchImpl) {
  const els = {};
  const host = makeEl();
  host.id = "surfacesPanel";
  const detail = makeEl();
  detail.id = "surfaceDetail";
  const document = {
    activeElement: null,
    body: { style: {} },
    getElementById(id) { return els[id] || null; },
    createElement() {
      const el = makeEl();
      el.owner = { els };
      return el;
    },
    createTextNode(text) { return { textContent: text }; },
    querySelectorAll(sel) {
      if (sel === "#slDecayMode button") {
        const mode = els.slDecayMode;
        return (mode && mode.children || []).filter((c) => c.tag === "button" || c.id);
      }
      return [];
    },
  };
  host.owner = { els };
  detail.owner = { els };
  els.surfacesPanel = host;
  els.surfaceDetail = detail;
  const context = {
    window: {},
    document,
    console,
    setTimeout() { return 0; },
    clearTimeout() {},
    fetch: fetchImpl || (() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })),
    getComputedStyle() { return { getPropertyValue: () => "#ddd" }; },
  };
  context.window.document = document;
  context.window.RRState = state;
  context.window.RRPushLive = () => { state._posts = (state._posts || 0) + 1; };
  context.window.RRColourSurfaces = { selected: "A", select() {}, setSurfaces() {} };
  vm.createContext(context);
  vm.runInContext(panel, context);
  return { context, els, state };
}

test("Dial is the default and the graph paint does not store calibration", () => {
  const state = { W: 6, H: 3, L: 8, decay_s: 1.8, decay_lock: true };
  const { els } = bootPanel(state);
  assert.equal(els.slMode_flat.textContent, "Dial sets length");
  assert.equal(els.slMode_surfaces.textContent, "Room sets length");
  assert.equal(els.slMode_natural.disabled, true);
  assert.equal(els.slMode_flat.attrs["aria-pressed"], "true");
  assert.equal(els.slMode_surfaces.attrs["aria-pressed"], "false");
  assert.equal(state.decay_mode, undefined);
  assert.equal(state.treat_sets_decay, undefined);
  assert.equal(state.surf_cal, undefined);
  assert.equal(els.slCalibrate.hidden, true);
  assert.equal(els.slAutoBtn.textContent, "Accept auto-treat");
  assert.ok(!state.surf_treatment || state.surf_treatment.length === 0);
});

test("Room sets length clears the lock and does not write calibration", () => {
  const state = { W: 6, H: 3, L: 8, decay_s: 1.8, decay_lock: true };
  const { els } = bootPanel(state);
  els.slMode_surfaces._on.click();
  assert.equal(state.decay_mode, "surfaces");
  assert.equal(state.treat_sets_decay, true);
  assert.equal(state.decay_lock, false);
  assert.equal(state.decay_s, 1.8);
  assert.equal(state.surf_cal, undefined);
  assert.equal(els.slCalibrate.hidden, false);
  assert.ok(state.surf_treatment.every((r) => r.type === "shell"));
  assert.equal(state.surf_treatment.some((r) => String(r.id || "").indexOf("auto_") === 0), false);
  els.slMode_flat._on.click();
  assert.equal(state.decay_mode, "flat");
  assert.equal(state.treat_sets_decay, false);
  assert.equal(state.decay_lock, true);
  assert.equal(state.decay_s, 1.8);
  assert.equal(state.surf_directional, false);
});

test("Accept writes the suggestion and the next press restores the old rows", async () => {
  const state = {
    W: 6, H: 3, L: 8, decay_s: 1.8, decay_lock: true,
    surf_treatment: [{ id: "keep", face: "B", type: "shell", coverage: 0.2, on: true }],
  };
  const { els } = bootPanel(state, (url) => {
    if (String(url).indexOf("/api/room/treat") >= 0) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          suggested: [{ id: "auto_0", face: "D", type: "porous", coverage: 0.2, suggested: true }],
          t_mid: 1.8,
        }),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  });
  els.slAutoBtn._on.click();
  assert.equal(state.surf_treatment.length, 1);
  assert.equal(state.surf_treatment[0].id, "keep");
  await new Promise((r) => setTimeout(r, 20));
  assert.equal(state.surf_treatment.length, 2);
  assert.equal(state.surf_treatment[0].id, "keep");
  assert.equal(state.surf_treatment[1].suggested, false);
  assert.equal(state.surf_treatment[1].face, "D");
  assert.equal(state.surf_cal, undefined);
  assert.equal(els.slAutoBtn.textContent, "Undo auto-treat");
  els.slAutoBtn._on.click();
  assert.equal(state.surf_treatment.length, 1);
  assert.equal(state.surf_treatment[0].id, "keep");
  assert.equal(els.slAutoBtn.textContent, "Accept auto-treat");
});
