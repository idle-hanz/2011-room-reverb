/* Room size, shape, place, and the Hadamard chips. */
"use strict";


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
  if (currentView === "space") scheduleImagesFetch(120);
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
    document.getElementById("spaceShapeRow")
  ];
}

function applyRoomShape(picked) {
  state.room_shape = (window.RoomShape && RoomShape.normalize) ? RoomShape.normalize(picked) : "box";
  if (window.RoomMath && RoomMath.clampRoom) Object.assign(state, RoomMath.clampRoom(state));
  syncUI();
  scheduleLiveParams();
  if (currentView === "space") scheduleImagesFetch(0);
}

function paintRoomShape() {
  var name = (window.RoomShape && RoomShape.normalize) ? RoomShape.normalize(state.room_shape) : "box";
  if (window.RoomShape && RoomShape.paintShapeRows) RoomShape.paintShapeRows(roomShapeRows(), name);
  var hideSwitch = !!(window.RoomShape && RoomShape.showMirrorToggle && !RoomShape.showMirrorToggle(name));
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
  resetToFresh();
  state._place = name;
  lastPlace = name;
  if (name === "hall") {
    applyReaktorSnapshot();
  } else {
    var p = PLACES[name];
    if (!p) return;
    Object.keys(p).forEach(function (k) { state[k] = p[k]; });
    if (statusEl) statusEl.textContent = name.charAt(0).toUpperCase() + name.slice(1) + " loaded. Play live or Render.";
  }
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