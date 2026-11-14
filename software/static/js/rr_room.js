/* Room size, shape, place, and the Hadamard chips. */
"use strict";

var roomHist = (window.RoomShape && RoomShape.createRoomHistory) ? RoomShape.createRoomHistory(50) : null;
var roomHistLock = false;

function roomSnap() {
  if (!roomHist) return null;
  return roomHist.snap(state);
}

function noteRoomEdit(before) {
  if (roomHistLock || !roomHist || !before) return false;
  return roomHist.note(before, roomHist.snap(state));
}

function beginRoomDrag() {
  if (roomHistLock || !roomHist) return false;
  return roomHist.beginDrag(roomHist.snap(state));
}

function endRoomDrag() {
  if (roomHistLock || !roomHist) return false;
  return roomHist.endDrag(roomHist.snap(state));
}

/* Undo uses the same size path as a slider. The shape token is copied as stored. */
function applyRoomSnap(next) {
  if (!next) return;
  roomHistLock = true;
  try {
    if (Number(next.W) !== Number(state.W)) onRoomDim("W", next.W);
    if (Number(next.H) !== Number(state.H)) onRoomDim("H", next.H);
    if (Number(next.L) !== Number(state.L)) onRoomDim("L", next.L);
    state.room_shape = String(next.room_shape == null ? "box" : next.room_shape);
    if (window.RoomMath && RoomMath.clampRoom) Object.assign(state, RoomMath.clampRoom(state));
    syncUI();
    scheduleLiveParams();
    scheduleImagesFetch(0);
  } finally {
    roomHistLock = false;
  }
}

function undoRoom() {
  if (!roomHist) return;
  applyRoomSnap(roomHist.undo(roomHist.snap(state)));
}

function redoRoom() {
  if (!roomHist) return;
  applyRoomSnap(roomHist.redo(roomHist.snap(state)));
}

function roomHistTyping(el) {
  var tag;
  var type;
  if (!el) return false;
  if (el.isContentEditable) return true;
  tag = el.tagName;
  if (tag === "TEXTAREA" || tag === "SELECT") return true;
  if (tag !== "INPUT") return false;
  type = String(el.type || "text").toLowerCase();
  return type === "text" || type === "number" || type === "search" || type === "email" || type === "url" || type === "password" || type === "tel";
}

window.roomSnap = roomSnap;
window.noteRoomEdit = noteRoomEdit;
window.beginRoomDrag = beginRoomDrag;
window.endRoomDrag = endRoomDrag;
window.roomHistDragging = function () { return !!(roomHist && roomHist.isDragging()); };


function syncHadamardUI() {
  var n = state.hadamard_n || 32;
  var live = !!(window.LiveFDN && LiveFDN.isRunning && LiveFDN.isRunning());
  document.querySelectorAll(".hadamard-chip").forEach(function (btn) {
    var bn = parseInt(btn.getAttribute("data-n"), 10);
    var renderOnly = bn === 64 || bn === 128;
    btn.classList.toggle("active", bn === n);
    btn.disabled = false;
    if (renderOnly) btn.title = "Render only";
    else if (btn.title === "Render only") btn.title = "";
  });
  var ro = document.getElementById("hadamardReadout");
  if (!ro) return;
  if (live && (n === 64 || n === 128)) {
    ro.textContent = n + " lines: Render uses " + n + ", Play is using 32";
  } else {
    ro.textContent = n + " images · " + n + " FDN lines";
  }
}

function setHadamardN(n) {
  var allowed = [8, 16, 32, 64, 128];
  if (allowed.indexOf(n) < 0) n = 32;
  state.hadamard_n = n;
  syncHadamardUI();
  syncUI();
  scheduleImagesFetch(120);
}

function placeRoomControls() {
  placeProxR();
  function nodes(ids) {
    var out = [];
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) out.push(el);
    });
    return out;
  }
  function restore(list, parent) {
    if (!parent) return;
    list.forEach(function (el) { parent.appendChild(el); });
  }
  function into(list, cap) {
    var host = document.querySelector('[data-room-spot="' + cap + '"] [data-room-park]');
    if (!host) return;
    list.forEach(function (el) { host.appendChild(el); });
  }
  var centreNodes = nodes(["centrePresetRow", "micHpfCentreRow", "micHpfCentreHint", "proxCRow", "centrePatternBlock"]);
  if (stripIsRoom("c")) into(centreNodes, "c");
  else restore(centreNodes, document.getElementById("centreMicChoice"));
  var right = document.getElementById("sideSplitR");
  if (!right) return;
  if (stripIsRoom("r") && splitOn()) into([right], "r");
  else restore([right], document.getElementById("sidePatternSplit"));
}

function placeScaleMargin(axis) {
  return Math.max(0.3, 0.1 * axis);
}

function placeScaleInset(v, axis) {
  var lo = placeScaleMargin(axis);
  var hi = axis - lo;
  if (!(hi >= lo)) return v;
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

function placeScaleKey(st, key, ratio, axis) {
  var v = st[key];
  if (v == null || v === "" || !isFinite(Number(v))) return;
  st[key] = placeScaleInset(Number(v) * ratio, axis);
}

/* Positions on the axis that changed. Yaw stays. Unmirrored source B only. */
function scaleRoomAxis(st, key, prev, next) {
  var ratio = next / prev;
  var keys = key === "W"
    ? ["sx", "mcx", "room_x", "room_l_x", "room_c_x", "room_r_x"]
    : key === "L"
      ? ["sz", "mcz", "room_z", "room_l_z", "room_c_z", "room_r_z"]
      : ["sy", "my", "room_y", "room_l_y", "room_c_y", "room_r_y", "my_l", "my_c", "my_r"];
  var i;
  for (i = 0; i < keys.length; i++) placeScaleKey(st, keys[i], ratio, next);
  if (!st.mirror_b) {
    placeScaleKey(st, key === "W" ? "sx_b" : key === "L" ? "sz_b" : "sy_b", ratio, next);
  }
}

function placeCapsuleXs(st, space) {
  var half = Number(space) * 0.5;
  var mcx = Number(st.mcx);
  if (st.mic_setup === "binaural") {
    var psi = ((Number(st.head_yaw_deg) || 0) * Math.PI) / 180;
    var rx = Math.cos(psi);
    return [mcx - half * rx, mcx + half * rx];
  }
  return [mcx - half, mcx + half];
}

/* Put Space back when the pair still sits inside (0, W).
     Slide the stand to the room centre, then shorten Space, only when the pair is wider than the room.
     centre_dz is not touched. */
function restoreSpaceAfterSize(st, spaceWant) {
  var want = Number(spaceWant);
  var W = Number(st.W);
  if (!isFinite(want) || want < 0 || !isFinite(W) || !(W > 0)) return;
  var xs = placeCapsuleXs(st, want);
  var a = Math.min(xs[0], xs[1]);
  var b = Math.max(xs[0], xs[1]);
  if (a > 0 && b < W) {
    st.space = want;
    return;
  }
  if (!(b - a > W)) return;
  st.mcx = W * 0.5;
  st.space = Math.min(want, RoomMath.maxSpace(W, st.mcx));
}

function onRoomDim(key, val) {
  var prev = Number(state[key]);
  var next = Number(val);
  var spaceWant = state.space;
  state[key] = val;
  if (isFinite(prev) && prev > 0 && isFinite(next) && next > 0 && next !== prev) {
    scaleRoomAxis(state, key, prev, next);
  }
  Object.assign(state, RoomMath.clampRoom(state));
  restoreSpaceAfterSize(state, spaceWant);
  syncUI();
}
function refitDiagrams() {
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      if (micDesk && micDesk.redraw) micDesk.redraw();
      if (micDesk && micDesk.view3d && micDesk.view3d.resize) micDesk.view3d.resize();
      if (polarView && polarView.resize) polarView.resize();
    });
  });
}

function paintPlaceChips() {
  var name = state._place || "";
  document.querySelectorAll("#placeRow [data-place]").forEach(function (btn) {
    btn.classList.toggle("active", btn.getAttribute("data-place") === name);
  });
}

function roomShapeRows() {
  return [
    document.getElementById("roomShapeRow"),
    document.getElementById("roomDiagramShapeRow"),
    document.getElementById("spaceShapeRow"),
    document.getElementById("roomPlanRow")
  ];
}

function applyRoomShape(picked) {
  var before = roomSnap();
  var name = (window.RoomShape && RoomShape.normalize) ? RoomShape.normalize(picked) : "box";
  state.room_shape = (window.RoomShape && RoomShape.storedShape)
    ? RoomShape.storedShape(picked, state.W, state.H, state.L, state.room_shape)
    : name;
  if (window.RoomMath && RoomMath.clampRoom) Object.assign(state, RoomMath.clampRoom(state));
  syncUI();
  scheduleLiveParams();
  scheduleImagesFetch(0);
  noteRoomEdit(before);
}

function paintRoomShape() {
  var name = (window.RoomShape && RoomShape.normalize) ? RoomShape.normalize(state.room_shape) : "box";
  if (window.RoomShape && RoomShape.paintShapeRows) RoomShape.paintShapeRows(roomShapeRows(), name);
  var modes = document.getElementById("roomModes");
  if (modes && window.RoomShape && RoomShape.axialText) modes.textContent = RoomShape.axialText(state.W, state.H, state.L);
  var tiltBtn = document.getElementById("roomTiltBtn");
  var slopeBtn = document.getElementById("roomSlopeBtn");
  if (window.RoomShape && tiltBtn && RoomShape.tiltLabel) tiltBtn.textContent = RoomShape.tiltLabel(state.room_shape);
  if (window.RoomShape && slopeBtn && RoomShape.slopeLabel) slopeBtn.textContent = RoomShape.slopeLabel(state.room_shape);
  var degEl = document.getElementById("roomTiltDeg");
  var pctEl = document.getElementById("roomSlopePct");
  if (window.RoomShape && RoomShape.tiltPair && degEl && pctEl) {
    var pair = RoomShape.tiltPair(state.room_shape) || { deg: 0, slope: 0 };
    if (document.activeElement !== degEl) degEl.value = Number(pair.deg).toFixed(2);
    if (document.activeElement !== pctEl) pctEl.value = (Number(pair.slope) * 100).toFixed(1);
  }
  var planOn = name === "plan";
  var addCorner = document.getElementById("roomPlanAdd");
  var delCorner = document.getElementById("roomPlanDel");
  if (addCorner) addCorner.hidden = !planOn;
  if (delCorner) delCorner.hidden = !planOn;
  var planNoteEl = document.getElementById("roomPlanNote");
  if (planNoteEl && window.RoomShape && RoomShape.planNote) {
    var why = RoomShape.planNote();
    planNoteEl.textContent = why;
    planNoteEl.hidden = !why;
  }
  var hideSwitch = !!(window.RoomShape && RoomShape.showMirrorToggle && !RoomShape.showMirrorToggle(state.room_shape));
  var mirrorRow = document.getElementById("mirrorLrRow");
  var mirrorBox = document.getElementById("mirrorLr");
  if (mirrorRow) mirrorRow.hidden = hideSwitch;
  if (mirrorBox) {
    mirrorBox.checked = hideSwitch || !!state.mirror_lr;
    mirrorBox.disabled = hideSwitch;
  }
  if (colourSurfaces && colourSurfaces.syncWallList && paintRoomShape._shown !== name) {
    paintRoomShape._shown = name;
    colourSurfaces.syncWallList();
  }
  paintRoomCorners();
}

function setPlanDragNote(text) {
  ["roomCornerNote", "floorPlanNote", "srcFloorPlanNote"].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = text || "";
    el.hidden = !text;
  });
}

/* Corner X and Z for a plan: room. Hidden for every other shape.
   A rebuild is skipped while a field in the list is focused and the corner count matches. */
function paintRoomCorners() {
  var list = document.getElementById("roomCornerList");
  var name = (window.RoomShape && RoomShape.normalize) ? RoomShape.normalize(state.room_shape) : "box";
  var planOn = name === "plan";
  var pts = (planOn && window.RoomShape && RoomShape.planPoints) ? RoomShape.planPoints(state.room_shape) : null;
  var sel = 0;
  var rows;
  var i;
  if (!list) return;
  if (!planOn || !pts) {
    list.hidden = true;
    list.textContent = "";
    setPlanDragNote("");
    return;
  }
  list.hidden = false;
  if (window.RoomShape && RoomShape.planSelection) sel = RoomShape.planSelection();
  if (sel < 0 || sel >= pts.length) {
    sel = 0;
    if (window.RoomShape && RoomShape.selectPlanCorner) RoomShape.selectPlanCorner(0);
  }
  rows = list.querySelectorAll("[data-corner-row]");
  if (list.contains(document.activeElement) && rows.length === pts.length) {
    list.querySelectorAll("[data-corner-pick]").forEach(function (btn) {
      var on = parseInt(btn.getAttribute("data-corner-pick"), 10) === sel;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
  } else {
    list.textContent = "";
    for (i = 0; i < pts.length; i++) {
      var on = i === sel;
      var row = document.createElement("div");
      var pick = document.createElement("button");
      var xIn = document.createElement("input");
      var zIn = document.createElement("input");
      row.className = "place-row";
      row.setAttribute("data-corner-row", String(i));
      pick.type = "button";
      pick.className = "chip" + (on ? " active" : "");
      pick.setAttribute("data-corner-pick", String(i));
      pick.setAttribute("aria-pressed", on ? "true" : "false");
      pick.textContent = String(i + 1);
      xIn.type = "number";
      xIn.step = "0.01";
      xIn.style.width = "4.6rem";
      xIn.setAttribute("data-corner", String(i));
      xIn.setAttribute("data-axis", "x");
      xIn.setAttribute("aria-label", "Corner " + (i + 1) + " X metres");
      xIn.value = Number(pts[i][0]).toFixed(2);
      zIn.type = "number";
      zIn.step = "0.01";
      zIn.style.width = "4.6rem";
      zIn.setAttribute("data-corner", String(i));
      zIn.setAttribute("data-axis", "z");
      zIn.setAttribute("aria-label", "Corner " + (i + 1) + " Z metres");
      zIn.value = Number(pts[i][1]).toFixed(2);
      row.appendChild(pick);
      row.appendChild(xIn);
      row.appendChild(zIn);
      list.appendChild(row);
    }
  }
  setPlanDragNote(window.RoomShape && RoomShape.planDragNote ? RoomShape.planDragNote() : "");
}

window.paintRoomCorners = paintRoomCorners;

var roomCornerList = document.getElementById("roomCornerList");
if (roomCornerList) {
  roomCornerList.addEventListener("click", function (evt) {
    var btn = evt.target && evt.target.closest ? evt.target.closest("[data-corner-pick]") : null;
    if (!btn || !window.RoomShape || !RoomShape.selectPlanCorner) return;
    RoomShape.selectPlanCorner(btn.getAttribute("data-corner-pick"));
    paintRoomCorners();
    if (window.editor && editor.redraw) editor.redraw();
  });
  roomCornerList.addEventListener("change", function (evt) {
    var input = evt.target;
    var row;
    var xEl;
    var zEl;
    var i;
    var pts;
    if (!input || !input.getAttribute || input.getAttribute("data-corner") == null) return;
    var beforeSnap;
    if (!window.RoomShape || !RoomShape.typePlanCorner) return;
    beforeSnap = roomSnap();
    i = parseInt(input.getAttribute("data-corner"), 10);
    row = input.closest ? input.closest("[data-corner-row]") : null;
    xEl = row ? row.querySelector('[data-axis="x"]') : null;
    zEl = row ? row.querySelector('[data-axis="z"]') : null;
    if (!xEl || !zEl) return;
    RoomShape.selectPlanCorner(i);
    state.room_shape = RoomShape.typePlanCorner(state.room_shape, i, xEl.value, zEl.value, state.W, state.L);
    if (window.RoomMath && RoomMath.clampRoom) Object.assign(state, RoomMath.clampRoom(state));
    pts = RoomShape.planPoints ? RoomShape.planPoints(state.room_shape) : null;
    if (pts && pts[i]) {
      xEl.value = Number(pts[i][0]).toFixed(2);
      zEl.value = Number(pts[i][1]).toFixed(2);
    }
    syncUI();
    scheduleLiveParams();
    scheduleImagesFetch(0);
    noteRoomEdit(beforeSnap);
  });
}

function addShapePanel(kind) {
  if (!window.RoomShape || !RoomShape.panelRow) return;
  var row = RoomShape.panelRow(kind);
  if (!row) return;
  if (!Array.isArray(state.surf_treatment)) state.surf_treatment = [];
  row.id = String(kind) + "_" + state.surf_treatment.length;
  state.surf_treatment.push(row);
  if (colourSurfaces && colourSurfaces.select) colourSurfaces.select(row.face);
  if (window.SLRoomResult && SLRoomResult.paintRows) SLRoomResult.paintRows();
  syncUI();
}

function paintMicSetupLink() {
  var link = document.getElementById("roomMicSetupLink");
  var setupEl = document.getElementById("mic_setup");
  if (!link || !setupEl) return;
  var opt = setupEl.options && setupEl.selectedIndex >= 0 ? setupEl.options[setupEl.selectedIndex] : null;
  var name = opt && opt.textContent ? opt.textContent : (state.mic_setup || "ORTF");
  link.textContent = "Mic setup: " + name + " ›";
}

/* Metres from the room centre. A place chip used to write absolute x from wall 0
   (Hall left mcx at the studio stand), so the stand sat on the left wall. */
var PLACE_POS_MARGIN = 0.10;
var PLACE_POS_KEYS = [
  "sx", "sy", "sz", "mcx", "my", "mcz", "sx_b", "sy_b", "sz_b",
  "room_x", "room_y", "room_z",
  "room_l_x", "room_l_y", "room_l_z",
  "room_c_x", "room_c_y", "room_c_z",
  "room_r_x", "room_r_y", "room_r_z",
  "my_l", "my_c", "my_r"
];
var PLACE_POS_AXIS = {
  sx: "W", mcx: "W", sx_b: "W", room_x: "W",
  room_l_x: "W", room_c_x: "W", room_r_x: "W",
  sz: "L", mcz: "L", sz_b: "L", room_z: "L",
  room_l_z: "L", room_c_z: "L", room_r_z: "L",
  sy: "H", my: "H", sy_b: "H", room_y: "H",
  room_l_y: "H", room_c_y: "H", room_r_y: "H",
  my_l: "H", my_c: "H", my_r: "H"
};
var placePosStore = {};
var placeAnchor = null;

function capturePlacePositions(st) {
  var out = {};
  var i, k, v;
  for (i = 0; i < PLACE_POS_KEYS.length; i++) {
    k = PLACE_POS_KEYS[i];
    v = st[k];
    if (v == null || v === "" || !isFinite(Number(v))) continue;
    out[k] = Number(v);
  }
  return out;
}

function placeBox(st) {
  return { W: Number(st.W), H: Number(st.H), L: Number(st.L) };
}

function shiftPlacePos(v, oldSize, newSize) {
  var next = v - oldSize * 0.5 + newSize * 0.5;
  if (!(newSize < oldSize)) return next;
  var lo = PLACE_POS_MARGIN;
  var hi = newSize - lo;
  if (!(hi >= lo)) {
    if (!(newSize > 0)) return next;
    if (next < 0) return 0;
    if (next > newSize) return newSize;
    return next;
  }
  if (next < lo) return lo;
  if (next > hi) return hi;
  return next;
}

function mapPlacePositions(captured, oldBox, newBox) {
  var out = {};
  var k, axis, oldSize, newSize;
  for (k in captured) {
    if (!Object.prototype.hasOwnProperty.call(captured, k)) continue;
    axis = PLACE_POS_AXIS[k];
    oldSize = oldBox[axis];
    newSize = newBox[axis];
    if (!isFinite(oldSize) || !(oldSize > 0) || !isFinite(newSize) || !(newSize > 0)) continue;
    out[k] = shiftPlacePos(captured[k], oldSize, newSize);
  }
  return out;
}

function applyPlacePositions(pos) {
  var k;
  for (k in pos) {
    if (Object.prototype.hasOwnProperty.call(pos, k)) state[k] = pos[k];
  }
}

/* A place chip keeps these unless that place writes the key itself.
   Hall's snapshot writes the six cards, solo and mute. */
var SURFACE_KEEP = [
  "surfaces", "surfaces_solo", "surfaces_mute",
  "surf_treatment", "surf_suggestions", "surf_amount",
  "surf_cal", "surf_directional", "decay_mode", "treat_sets_decay",
  "diffusion_seed", "lambda_ref"
];

function placeOwnsSurfaceKey(name, key) {
  if (name === "hall" && (key === "surfaces" || key === "surfaces_solo" || key === "surfaces_mute")) return true;
  var p = PLACES[name];
  return !!(p && Object.prototype.hasOwnProperty.call(p, key));
}

function captureSurfaceKeep(name) {
  var kept = {};
  var i, k, raw;
  for (i = 0; i < SURFACE_KEEP.length; i++) {
    k = SURFACE_KEEP[i];
    if (placeOwnsSurfaceKey(name, k)) continue;
    if (!Object.prototype.hasOwnProperty.call(state, k)) continue;
    raw = JSON.stringify(state[k]);
    if (raw === undefined) continue;
    kept[k] = JSON.parse(raw);
  }
  return kept;
}

function restoreSurfaceKeep(kept) {
  var k;
  for (k in kept) {
    if (Object.prototype.hasOwnProperty.call(kept, k)) state[k] = kept[k];
  }
  if (Object.prototype.hasOwnProperty.call(kept, "surfaces") && colourSurfaces && colourSurfaces.setSurfaces) {
    colourSurfaces.setSurfaces(state.surfaces);
  }
}

function samePlacePositions(a, b) {
  var i, k, ak, bk;
  if (!a || !b) return false;
  for (i = 0; i < PLACE_POS_KEYS.length; i++) {
    k = PLACE_POS_KEYS[i];
    ak = Object.prototype.hasOwnProperty.call(a, k);
    bk = Object.prototype.hasOwnProperty.call(b, k);
    if (ak !== bk) return false;
    if (ak && !Object.is(a[k], b[k])) return false;
  }
  return true;
}

function applyPlace(name) {
  placeChosen = true;
  var fromName = lastPlace || state._place || "";
  var captured = capturePlacePositions(state);
  var oldBox = placeBox(state);
  if (!placeAnchor) placeAnchor = { box: oldBox, pos: captured };
  if (fromName) {
    /* A drag updates the anchor. An unmoved chip keeps the anchor, so
       Club then Studio matches a fresh Studio click exactly. */
    if (!samePlacePositions(placePosStore[fromName], captured)) {
      placeAnchor = { box: oldBox, pos: captured };
    }
    placePosStore[fromName] = captured;
  }
  var keptSurfaces = captureSurfaceKeep(name);
  resetToFresh();
  state._place = name;
  lastPlace = name;
  if (name === "hall") {
    applyReaktorSnapshot();
  } else {
    var p = PLACES[name];
    if (!p) {
      restoreSurfaceKeep(keptSurfaces);
      return;
    }
    Object.keys(p).forEach(function (k) { state[k] = p[k]; });
    if (statusEl) statusEl.textContent = name.charAt(0).toUpperCase() + name.slice(1) + " loaded. Play live or Render.";
  }
  restoreSurfaceKeep(keptSurfaces);
  var pos = placePosStore[name];
  if (!pos) {
    pos = mapPlacePositions(placeAnchor.pos, placeAnchor.box, placeBox(state));
  }
  applyPlacePositions(pos);
  if (window.RoomMath && RoomMath.clampRoom) Object.assign(state, RoomMath.clampRoom(state));
  placePosStore[name] = capturePlacePositions(state);
  syncHadamardUI();
  syncUI();
}

var roomTiltApply = typeof document !== "undefined" ? document.getElementById("roomTiltApply") : null;
if (roomTiltApply) {
  roomTiltApply.addEventListener("click", function () {
    var before = roomSnap();
    var degEl = document.getElementById("roomTiltDeg");
    var pctEl = document.getElementById("roomSlopePct");
    if (!window.RoomShape || !RoomShape.encodeTiltFields || !degEl || !pctEl) return;
    state.room_shape = RoomShape.encodeTiltFields(degEl.value, pctEl.value);
    if (window.RoomMath && RoomMath.clampRoom) Object.assign(state, RoomMath.clampRoom(state));
    syncUI();
    scheduleLiveParams();
    noteRoomEdit(before);
  });
}

if (typeof document !== "undefined") {
  var roomRatioRow = document.getElementById("roomRatioRow");
  var roomRatioBefore = null;
  if (roomRatioRow) {
    roomRatioRow.addEventListener("click", function (evt) {
      var btn = evt.target && evt.target.closest ? evt.target.closest("[data-ratio]") : null;
      if (!btn) return;
      roomRatioBefore = roomSnap();
    }, true);
    roomRatioRow.addEventListener("click", function (evt) {
      var btn = evt.target && evt.target.closest ? evt.target.closest("[data-ratio]") : null;
      if (!btn || !roomRatioBefore) return;
      noteRoomEdit(roomRatioBefore);
      roomRatioBefore = null;
    }, false);
  }

  var roomUndoBtn = document.getElementById("roomUndo");
  var roomRedoBtn = document.getElementById("roomRedo");
  if (roomUndoBtn) roomUndoBtn.addEventListener("click", undoRoom);
  if (roomRedoBtn) roomRedoBtn.addEventListener("click", redoRoom);

  document.addEventListener("keydown", function (evt) {
    var key;
    if (!(evt.ctrlKey || evt.metaKey) || evt.altKey) return;
    if (roomHistTyping(evt.target)) return;
    key = String(evt.key || "").toLowerCase();
    if (key === "z" && !evt.shiftKey) {
      evt.preventDefault();
      undoRoom();
    } else if ((key === "z" && evt.shiftKey) || key === "y") {
      evt.preventDefault();
      redoRoom();
    }
  });
}