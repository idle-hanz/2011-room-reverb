/* Room-mic window readouts. Display only. Not state, and not posted.
   Source metres is the straight-line gap between geo.source and RRDrag.roomSpot.
   Nearest wall is the floor gap to the shell: min(x, W-x, z, L-z).
   RoomMath.compute().distances is the stand mic. Do not use it here.
   Browser: window.RRRoomWindow. Node: module.exports. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RRRoomWindow = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function num(v) {
    var n = Number(v);
    return isFinite(n) ? n : 0;
  }

  function sourceMetres(source, spot) {
    source = source || {};
    spot = spot || {};
    return Math.hypot(num(source.x) - num(spot.x), num(source.y) - num(spot.y), num(source.z) - num(spot.z));
  }

  function nearestWallMetres(spot, W, L) {
    spot = spot || {};
    var x = num(spot.x);
    var z = num(spot.z);
    return Math.min(x, num(W) - x, z, num(L) - z);
  }

  return { sourceMetres: sourceMetres, nearestWallMetres: nearestWallMetres };
});
