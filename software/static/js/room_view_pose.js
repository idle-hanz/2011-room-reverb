/* FIX-A display pose. A Room strip is drawn at its room spot.
   An on-stand strip keeps the stand point passed in.
   Nothing here is posted. centre_dz, space, and the stand stay the caller's.
   Browser: window.RRViewPose. Node: module.exports. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RRViewPose = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function num(v) {
    var n = Number(v);
    return isFinite(n) ? n : 0;
  }

  function isRoom(state, cap) {
    if (!state) return false;
    var key = String(cap || "").toLowerCase();
    return state["place_" + key] === "room" || (key === "c" && state.third_mic === "room");
  }

  /* Mix-page place click. Save third_mic before C becomes Room.
     A second Room click must not replace that saved value.
     Return writes the saved value back. L and R do not change it. */
  function mixThird(third, cap, name, wasRoom, saved) {
    var nextSaved = saved;
    var next = third;
    if (cap === "c" && name === "room" && !wasRoom) nextSaved = third;
    if (cap === "c" && name === "room") next = "room";
    else if (cap === "c" && name === "array" && wasRoom && nextSaved != null) next = nextSaved;
    return { third: next, saved: nextSaved };
  }

  function topSetback(state, spot) {
    if (!state || state.mic_setup === "binaural") return "";
    if (isRoom(state, "c")) {
      spot = spot || {};
      return " \u00b7 C " + num(spot.x).toFixed(2) + " m, " + num(spot.z).toFixed(2) + " m";
    }
    return " \u00b7 C setback " + (num(state.centre_dz) * 100).toFixed(0) + " cm";
  }

  function metresMic(state, spot) {
    state = state || {};
    var metres = "space " + num(state.space).toFixed(2) + " m";
    var high = state.my;
    if (state.mic_setup !== "binaural") {
      if (isRoom(state, "c")) {
        spot = spot || {};
        metres += " \u00b7 C " + num(spot.x).toFixed(2) + " m, " + num(spot.z).toFixed(2) + " m";
        high = spot.y;
      } else {
        metres += " \u00b7 C " + (num(state.centre_dz) * 100).toFixed(0) + " cm";
      }
    }
    metres += " \u00b7 " + num(high).toFixed(2) + " m high";
    return metres;
  }

  function sideHeightLine(state, stands, spots) {
    stands = stands || {};
    spots = spots || {};
    function yOf(cap) {
      if (isRoom(state, cap) && spots[cap]) return num(spots[cap].y);
      var stand = stands[cap] || {};
      return num(stand.y);
    }
    return "height  L " + yOf("l").toFixed(2) + "  C " + yOf("c").toFixed(2) + "  R " + yOf("r").toFixed(2) + " m";
  }

  function planeHint(plane, anyRoom) {
    if (plane === "side") {
      return anyRoom
        ? "Room mics sit at their spots. Drag one up or down to set its height. On-stand mics still move the stand. Drag left or right to turn the view."
        : "The stand, from the side. Drag left or right to turn the view. Drag a mic up or down.";
    }
    return anyRoom
      ? "Room mics sit at their spots. Drag a room capsule to move it. On-stand capsules still set spacing, and the amber front aims."
      : "The stand, from above. Scroll to zoom. Drag a capsule in or out, and the amber front to aim.";
  }

  /* Local offset from the stand group. spotWorldZ is already in the view's Z. */
  function capsuleLocal(room, standLocal, standWorld, spot, spotWorldZ) {
    standLocal = standLocal || {};
    if (!room) {
      return { x: num(standLocal.x), y: num(standLocal.y), z: num(standLocal.z), room: false };
    }
    spot = spot || {};
    standWorld = standWorld || {};
    return {
      x: num(spot.x) - num(standWorld.x),
      y: num(spot.y),
      z: num(spotWorldZ) - num(standWorld.z),
      room: true
    };
  }

  return {
    isRoom: isRoom,
    mixThird: mixThird,
    topSetback: topSetback,
    metresMic: metresMic,
    sideHeightLine: sideHeightLine,
    planeHint: planeHint,
    capsuleLocal: capsuleLocal
  };
});
