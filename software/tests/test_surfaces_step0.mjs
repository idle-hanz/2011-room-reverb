// Surfaces step 0. Room-result dots, the Surfaces chip, and place chips.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const roomSrc = fs.readFileSync(path.join(here, "../static/js/rr_room.js"), "utf8");
const panelSrc = fs.readFileSync(path.join(here, "../static/js/sl_room_result.js"), "utf8");

function makeEl(tag) {
  const el = {
    tag: tag || "div",
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
  el.classList = {
    toggle() {},
    add() {},
    remove() {},
  };
  el.setAttribute = (k, v) => { el.attrs[k] = String(v); };
  el.getAttribute = (k) => (Object.prototype.hasOwnProperty.call(el.attrs, k) ? el.attrs[k] : null);
  el.appendChild = (child) => {
    el.children.push(child);
    if (child && child.id) el.owner.els[child.id] = child;
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

function bootPanel(state) {
  const els = {};
  const host = makeEl("div");
  host.id = "surfacesPanel";
  const detail = makeEl("div");
  detail.id = "surfaceDetail";
  const document = {
    activeElement: null,
    getElementById(id) { return els[id] || null; },
    createElement(tag) {
      const el = makeEl(tag);
      el.owner = { els };
      return el;
    },
    createTextNode(text) { return { textContent: text }; },
    querySelectorAll(sel) {
      if (sel === "#slDecayMode button") {
        const mode = els.slDecayMode;
        return (mode && mode.children || []).filter((c) => c.tag === "button");
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
    fetch() { return Promise.resolve({ ok: true, json() { return Promise.resolve({}); } }); },
  };
  context.window.document = document;
  context.window.RRState = state;
  context.window.RRColourSurfaces = {
    selected: "A",
    select() {},
    setSurfaces() {},
  };
  vm.createContext(context);
  vm.runInContext(panelSrc, context);
  return { context, els, state };
}

test("room result dots drop after the scene changes", () => {
  const state = {
    W: 6, H: 3, L: 8,
    humidity: 0.35,
    surfaces: { A: { absorb: [0.1, 0.2] } },
    surf_treatment: [],
    decay_mode: "surfaces",
  };
  const { context } = bootPanel(state);
  const dots = { f: [1000], t20: [1.4] };
  context.window.SLRoomResult.rememberDots(dots);
  assert.deepEqual(context.window.SLRoomResult.currentDots(), dots);
  state.surfaces.A.absorb[0] = 0.8;
  assert.equal(context.window.SLRoomResult.currentDots(), null);
  assert.equal(state.surf_rendered_t20, null);
});

test("Surfaces chip is the room average until Calibrate", () => {
  const state = {
    W: 6, H: 3, L: 8,
    decay_mode: "flat",
    surf_directional: false,
    surfaces: { A: { absorb: [0.1] } },
  };
  const { els } = bootPanel(state);
  els.slMode_surfaces._on.click();
  assert.equal(state.decay_mode, "surfaces");
  assert.equal(state.surf_directional, false);
  state.surf_directional = true;
  els.slMode_surfaces._on.click();
  assert.equal(state.surf_directional, true);
  els.slMode_flat._on.click();
  assert.equal(state.decay_mode, "flat");
  assert.equal(state.surf_directional, false);
});

function loadPlace(state, places, hooks) {
  const start = roomSrc.indexOf("var PLACE_POS_MARGIN");
  assert.ok(start > 0);
  const src = roomSrc.slice(start);
  return new Function("state", "PLACES", "resetToFresh", "applyReaktorSnapshot", "colourSurfaces", "statusEl", "window", `
    var placeChosen = false;
    var lastPlace = "";
    var RoomMath = window.RoomMath;
    function syncHadamardUI() {}
    function syncUI() { if (colourSurfaces) colourSurfaces.syncs = (colourSurfaces.syncs || 0) + 1; }
    ${src}
    return applyPlace;
  `)(state, places, hooks.resetToFresh, hooks.applyReaktorSnapshot, hooks.colourSurfaces, null, hooks.window);
}

test("a place chip keeps Surfaces unless the place defines them", () => {
  const places = {
    studio: { W: 5.6, H: 2.8, L: 7.2, decay_lock: true, decay_s: 1.8 },
    custom: { W: 10, H: 4, L: 12, surfaces: { A: { absorb: [0.2] } } },
  };
  const boot = { A: { absorb: [0.05] } };
  const state = {
    W: 6, H: 3, L: 8,
    sx: 3, sz: 4, sy: 1.2, mcx: 3, mcz: 1.5, my: 1.2,
    surfaces: { A: { absorb: [0.42] } },
    surfaces_solo: "B",
    surfaces_mute: { A: true },
    surf_treatment: [{ id: "row", face: "A", coverage: 0.2 }],
    decay_mode: "surfaces",
    surf_directional: false,
    diffusion_seed: 7,
    lambda_ref: 0.03,
  };
  const colourSurfaces = { setSurfaces(s) { this.got = s; } };
  const applyPlace = loadPlace(state, places, {
    window: { RoomMath: { clampRoom(s) { return s; } } },
    colourSurfaces,
    resetToFresh() {
      state.W = 6; state.H = 3; state.L = 8;
      state.surfaces = JSON.parse(JSON.stringify(boot));
      state.surfaces_solo = null;
      state.surfaces_mute = null;
      delete state.surf_treatment;
      delete state.decay_mode;
      delete state.surf_directional;
      state.diffusion_seed = 0;
      state.lambda_ref = 0.02;
    },
    applyReaktorSnapshot() {
      state.W = 57; state.H = 34; state.L = 97;
      state.surfaces = { A: { absorb: [0.05], jitter_D: 0.16 } };
      state.surfaces_solo = null;
      state.surfaces_mute = { A: false };
      colourSurfaces.setSurfaces(state.surfaces);
    },
  });
  applyPlace("studio");
  assert.equal(state.W, 5.6);
  assert.equal(state.surfaces.A.absorb[0], 0.42);
  assert.equal(state.surfaces_solo, "B");
  assert.equal(state.surfaces_mute.A, true);
  assert.equal(state.surf_treatment[0].coverage, 0.2);
  assert.equal(state.decay_mode, "surfaces");
  assert.equal(state.diffusion_seed, 7);
  assert.equal(state.lambda_ref, 0.03);
  assert.equal(colourSurfaces.got, state.surfaces);

  applyPlace("hall");
  assert.equal(state.W, 57);
  assert.equal(state.surfaces.A.jitter_D, 0.16);
  assert.equal(state.surfaces.A.absorb[0], 0.05);
  assert.equal(state.surfaces_solo, null);
  assert.equal(state.surf_treatment[0].coverage, 0.2);
  assert.equal(state.diffusion_seed, 7);

  state.surfaces = { A: { absorb: [0.42] } };
  state.surf_treatment = [{ id: "row", face: "D", coverage: 0.4 }];
  applyPlace("custom");
  assert.equal(state.W, 10);
  assert.equal(state.surfaces.A.absorb[0], 0.2);
  assert.equal(state.surf_treatment[0].face, "D");
  assert.equal(state.surf_treatment[0].coverage, 0.4);
});
