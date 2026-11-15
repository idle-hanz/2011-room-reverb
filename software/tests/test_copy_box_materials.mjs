// Copy box materials paints each polygon face from its shoebox letter. A box hides the button.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "../static/index.html"), "utf8");
const surfacesJs = fs.readFileSync(path.join(here, "../static/js/colour_surfaces.js"), "utf8");
const settingsJs = fs.readFileSync(path.join(here, "../static/js/rr_settings.js"), "utf8");
const RS = require("../static/js/room_shape.js");
const { copyLetterMaterials } = require("../static/js/colour_surfaces.js");

function card(material, absorb0) {
  return {
    material,
    material_name: material,
    absorb: [absorb0, 0, 0, 0, 0, 0, 0],
    honesty: material,
    eq: {
      low_shelf_hz: 200, low_shelf_db: 0,
      high_shelf_hz: 5000, high_shelf_db: 0,
      peak_hz: 1000, peak_db: 1, peak_q: 1,
    },
    jitter_D: 0.2,
    structure_dif: 0.3,
    diffusion: 0.4,
    assumed: false,
  };
}

function makeEl() {
  const el = {
    hidden: false,
    className: "",
    textContent: "",
    value: "",
    checked: false,
    disabled: false,
    style: {},
    dataset: {},
    attrs: {},
    children: [],
    listeners: {},
    _html: "",
    _bound: false,
  };
  el.classList = {
    toggle(name, on) {
      const parts = el.className.split(/\s+/).filter((p) => p && p !== name);
      const has = el.className.split(/\s+/).includes(name);
      const next = on === undefined ? !has : !!on;
      if (next) parts.push(name);
      el.className = parts.join(" ");
    },
    add(name) { this.toggle(name, true); },
    remove(name) { this.toggle(name, false); },
  };
  el.setAttribute = (k, v) => { el.attrs[k] = String(v); };
  el.getAttribute = (k) => (Object.prototype.hasOwnProperty.call(el.attrs, k) ? el.attrs[k] : null);
  el.appendChild = (child) => { el.children.push(child); return child; };
  el.addEventListener = (type, fn) => {
    (el.listeners[type] || (el.listeners[type] = [])).push(fn);
  };
  el.remove = () => {};
  el.closest = () => null;
  el.querySelector = (sel) => {
    if (sel === "[data-solo]" || sel === "[data-mute]") return makeEl();
    return null;
  };
  el.querySelectorAll = (sel) => {
    if (sel === ".surface-card") {
      return el.children.filter((c) => c.className.split(/\s+/).includes("surface-card"));
    }
    if (sel === ".rn-face") return [];
    return [];
  };
  Object.defineProperty(el, "innerHTML", {
    get() { return el._html; },
    set(v) { el._html = String(v); el.children = []; },
  });
  return el;
}

function boot() {
  const nodes = {
    surfaceCards: makeEl(),
    mirrorLrRow: makeEl(),
    mirrorLr: makeEl(),
    copyBoxMaterials: makeEl(),
  };
  const document = {
    getElementById(id) { return nodes[id] || null; },
    createElement() { return makeEl(); },
    querySelectorAll() { return []; },
  };
  const state = {
    room_shape: "box",
    mirror_lr: true,
    W: 6,
    H: 3,
    L: 8,
    surfaces_solo: null,
    surfaces_mute: null,
  };
  let posts = 0;
  const context = {
    window: {},
    document,
    fetch() {
      return Promise.resolve({ json() { return Promise.resolve({}); } });
    },
    console,
  };
  context.window.document = document;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(here, "../static/js/room_shape.js"), "utf8"), context);
  context.RoomShape = context.window.RoomShape;
  vm.runInContext(fs.readFileSync(path.join(here, "../static/js/colour_surfaces.js"), "utf8"), context);
  const cs = new context.window.ColourSurfaces({
    getState() { return state; },
    onChange() { posts += 1; },
  });
  return {
    cs,
    state,
    nodes,
    posts() { return posts; },
  };
}

test("gable faces take the shoebox letter and a box hides the button", () => {
  const rows = RS.wallRows("gable", false, 6, 3, 8);
  const labels = rows.map((row) => row.letters[0]);
  assert.ok(labels.includes("A1"));
  assert.ok(labels.includes("F1"));
  assert.ok(labels.includes("F2"));
  const bare = {
    A: card("brick_unglazed", 0.21),
    F: card("wood_parquet", 0.44),
  };
  copyLetterMaterials(bare, labels);
  assert.equal(bare.A1.material, "brick_unglazed");
  assert.equal(bare.A1.letter, "A1");
  assert.equal(bare.A1.absorb[0], 0.21);
  assert.notEqual(bare.A1.absorb, bare.A.absorb);
  assert.equal(bare.F1.material, "wood_parquet");
  assert.equal(bare.F2.material, "wood_parquet");
  assert.equal(bare.F1.eq.peak_db, 1);
  assert.notEqual(bare.F1.eq, bare.F.eq);

  assert.match(page, /id="copyBoxMaterials" hidden>Copy box materials</);
  const setFn = surfacesJs.slice(
    surfacesJs.indexOf("prototype.setSurfaces"),
    surfacesJs.indexOf("prototype._bindMaterials"),
  );
  assert.equal(setFn.includes("copyBoxMaterials"), false);
  assert.equal(setFn.includes("copyLetterMaterials"), false);
  assert.equal(settingsJs.includes("copyBoxMaterials"), false);
  assert.equal(settingsJs.includes("copyLetterMaterials"), false);
  const press = surfacesJs.slice(
    surfacesJs.indexOf("prototype.copyBoxMaterials"),
    surfacesJs.indexOf("prototype._bindCopyBox"),
  );
  assert.equal(press.includes("noteRoomEdit"), false);
  assert.equal(press.includes("surfaces_mute"), false);
  assert.equal(press.includes("surfaces_solo"), false);
  const snap = RS.createRoomHistory().snap({
    W: 6, H: 3, L: 8, room_shape: "gable", surfaces: bare,
  });
  assert.deepEqual(Object.keys(snap).sort(), ["H", "L", "W", "room_shape"]);

  const { cs, state, nodes, posts } = boot();
  assert.equal(nodes.copyBoxMaterials.hidden, true);
  const saved = {
    A: card("brick_unglazed", 0.21),
    B: card("plaster", 0.1),
    C: card("plaster", 0.1),
    D: card("plaster", 0.1),
    E: card("carpet", 0.3),
    F: card("wood_parquet", 0.44),
    A1: card("plaster", 0.05),
    F1: card("curtain", 0.5),
    F2: card("glass", 0.08),
  };
  saved.A1.letter = "A1";
  state.room_shape = "gable";
  state.surfaces_mute = { A: true, F: true, A1: false, F1: false, F2: false };
  state.surfaces_solo = "F2";
  cs.setSurfaces(saved);
  assert.equal(state.surfaces.A1.material, "plaster");
  assert.equal(state.surfaces.F1.material, "curtain");
  assert.equal(state.surfaces.F2.material, "glass");
  assert.equal(posts(), 0);
  cs.syncWallList();
  assert.equal(nodes.copyBoxMaterials.hidden, false);
  assert.equal(state.surfaces.A1.material, "plaster");
  assert.equal(state.surfaces.F1.material, "curtain");
  assert.equal(state.surfaces.F2.material, "glass");
  assert.equal(state.surfaces_solo, "F2");
  assert.equal(posts(), 0);
  nodes.copyBoxMaterials.listeners.click[0]();
  assert.equal(state.surfaces.A1.material, "brick_unglazed");
  assert.equal(state.surfaces.F1.material, "wood_parquet");
  assert.equal(state.surfaces.F2.material, "wood_parquet");
  assert.equal(state.surfaces.E1.material, "carpet");
  assert.equal(state.surfaces_mute.A, true);
  assert.equal(state.surfaces_mute.A1, false);
  assert.equal(state.surfaces_mute.F1, false);
  assert.equal(state.surfaces_solo, "F2");
  assert.equal(posts(), 1);
  state.room_shape = "box";
  cs.syncWallList();
  assert.equal(nodes.copyBoxMaterials.hidden, true);
});
