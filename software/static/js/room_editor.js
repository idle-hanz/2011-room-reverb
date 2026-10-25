
/* 2011 Room Reverb — room math + canvas drag editor */
(function (global) {
  "use strict";

  const RoomMath = (global.RoomMath && global.RoomMath.compute) ? global.RoomMath : {
    clamp(v, lo, hi) {
      return Math.max(lo, Math.min(hi, v));
    },
    maxSpace(W, mcx) {
      return Math.max(0, 2 * Math.min(mcx, W - mcx));
    },
    CENTRE_DZ_MAX: 0.20,
    clampRoom(s) {
      const W = s.W, H = s.H, L = s.L;
      const mcx = s.reaktor_parity ? W * 0.5 : this.clamp(s.mcx, 0, W);
      const my = this.clamp(s.my, 0, H);
      let sy = s.sy;
      if (sy == null || sy === "" || !isFinite(Number(sy))) sy = my;
      else sy = this.clamp(Number(sy), 0, H);
      let centre_dz = this.clamp(Number(s.centre_dz) || 0, -this.CENTRE_DZ_MAX, this.CENTRE_DZ_MAX);
      if (s.align_horizontal) centre_dz = 0;
      return Object.assign({}, s, {
        sx: this.clamp(s.sx, 0, W),
        sz: this.clamp(s.sz, 0, L),
        my: my,
        sy: sy,
        mcz: this.clamp(s.mcz, 0, L),
        mcx: mcx,
        space: this.clamp(s.space, 0, this.maxSpace(W, mcx)),
        centre_dz: centre_dz,
      });
    },
    compute(raw) {
      const s = this.clampRoom(raw);
      const sox = Math.abs(s.W) > 1e-12 ? s.sx / s.W : 0;
      const denom = s.L - s.mcz;
      const soz = Math.abs(denom) > 1e-12 ? (s.sz - s.mcz) / denom : 0;
      const mz = s.L - s.mcz;
      const half = s.space * 0.5;
      const dz = s.centre_dz || 0;
      const source = { x: s.sx, y: s.sy, z: s.sz };
      const centre = { x: s.mcx, y: s.my, z: s.mcz + dz };
      const left = { x: s.mcx - half, y: s.my, z: s.mcz };
      const right = { x: s.mcx + half, y: s.my, z: s.mcz };
      let ml, mr, mc;
      if (s.yaw_l_deg != null && s.yaw_l_deg !== "" && isFinite(Number(s.yaw_l_deg))) {
        ml = (Number(s.yaw_l_deg) * Math.PI) / 180;
      } else if (s.toe_half_deg != null && s.toe_half_deg !== "" && isFinite(Number(s.toe_half_deg))) {
        ml = (-Number(s.toe_half_deg) * Math.PI) / 180;
      } else {
        ml = s.diverg * 0.5 - 0.25;
      }
      if (s.yaw_r_deg != null && s.yaw_r_deg !== "" && isFinite(Number(s.yaw_r_deg))) {
        mr = (Number(s.yaw_r_deg) * Math.PI) / 180;
      } else if (s.toe_half_deg != null && s.toe_half_deg !== "" && isFinite(Number(s.toe_half_deg))) {
        mr = (Number(s.toe_half_deg) * Math.PI) / 180;
      } else {
        mr = s.diverg * 0.5 + 0.25;
      }
      if (s.yaw_c_deg != null && s.yaw_c_deg !== "" && isFinite(Number(s.yaw_c_deg))) {
        mc = (Number(s.yaw_c_deg) * Math.PI) / 180;
      } else {
        mc = 0;
      }
      function dist(a, b) {
        return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
      }
      return {
        state: Object.assign({}, s, { sox: sox, soz: soz, mz: mz }),
        source: source,
        mic_centre: centre,
        mic_left: left,
        mic_right: right,
        look_l: { x: -Math.sin(ml), z: Math.cos(ml) },
        look_c: { x: -Math.sin(mc), z: Math.cos(mc) },
        look_r: { x: -Math.sin(mr), z: Math.cos(mr) },
        toe_l_deg: (ml * 180) / Math.PI,
        toe_c_deg: (mc * 180) / Math.PI,
        toe_r_deg: (mr * 180) / Math.PI,
        distances: {
          sl: dist(source, left),
          sc: dist(source, centre),
          sr: dist(source, right),
        },
        max_space: this.maxSpace(s.W, s.mcx),
      };
    },
  };

  const COLORS = {
    src: "#fbbf24",
    srcB: "#f43f5e",
    mic: "#60a5fa",
    L: "#a78bfa",
    R: "#34d399",
  };
  const HIT = 18;
  const FAR = 90; /* px — beyond this, empty click uses lastDragged */
  const ROOM_COLORS = { l: "#a78bfa", c: "#2dd4bf", r: "#34d399" };
  const ROOM_DRAW = ["l", "c", "r"];
  const ROOM_AIM_PX = 28;
  const ROOM_AIM_HIT = 11;

  function RoomEditorCreate(opts) {
    const floorCanvas = opts.floorCanvas;
    const elevCanvas = opts.elevCanvas;
    const view3dCanvas = opts.view3dCanvas || null;
    const getState = opts.getState;
    const setState = opts.setState;
    const onChange = opts.onChange;
    const onDragEnd = opts.onDragEnd || function () {};
    const sourceMeta = opts.sourceMeta || function () { return null; };

    const fctx = floorCanvas.getContext("2d");
    const ectx = elevCanvas.getContext("2d");
    let drag = null;
    let hover = null;
    let lastDragged = "source"; /* "source" | "mic" — used when empty click is far from both */
    let fl = null;
    let el = null;

    let view3d = null;
    if (view3dCanvas && global.Room3D) {
      view3d = global.Room3D.create({
        canvas: view3dCanvas,
        getState: getState,
        setState: setState,
        onChange: onChange,
        RoomMath: RoomMath,
        getTool: function () { return lastDragged; },
      });
    }

    function setTool(t) {
      /* No-op kept for API compat; chips removed — optionally remember kind */
      if (t === "source" || t === "mic") lastDragged = t;
    }

    function floorLayout(geo) {
      const W = geo.state.W, L = geo.state.L, pad = 52;
      const held = drag && drag.kind === "wall" && drag.ctx && drag.ctx.lay;
      if (held) {
        const l = drag.ctx.lay;
        const ox = drag.view ? drag.view.ox : l.ox;
        const oy = drag.view ? drag.view.oy : l.oy;
        return {
          W: W, L: L, scale: l.scale,
          ox: ox, oy: oy,
          rw: W * l.scale, rh: L * l.scale,
        };
      }
      const cw = floorCanvas.width, ch = floorCanvas.height;
      const scale = Math.min((cw - pad * 2) / W, (ch - pad * 2) / L);
      const rw = W * scale, rh = L * scale;
      return {
        W: W, L: L, scale: scale,
        ox: (cw - rw) / 2, oy: (ch - rh) / 2 + 4,
        rw: rw, rh: rh,
      };
    }
    function elevLayout(geo) {
      const L = geo.state.L, H = geo.state.H, padX = 52, padY = 28;
      const held = drag && drag.kind === "ceiling" && drag.ctx && drag.ctx.lay;
      if (held) {
        const l = drag.ctx.lay;
        const oy = drag.view ? drag.view.oy : l.oy;
        return {
          L: L, H: H, scale: l.scale,
          ox: l.ox, oy: oy,
          rw: L * l.scale, rh: H * l.scale,
        };
      }
      const cw = elevCanvas.width, ch = elevCanvas.height;
      const scale = Math.min((cw - padX * 2) / L, (ch - padY * 2) / H);
      const rw = L * scale, rh = H * scale;
      return {
        L: L, H: H, scale: scale,
        ox: (cw - rw) / 2, oy: (ch - rh) / 2,
        rw: rw, rh: rh,
      };
    }
    /* Keep grabbed walls under the pointer while scale stays at pointer-down.
       x0 shifts ox; z1 and the ceiling shift oy. x1 and z0 already stay put. */
    function viewForPatch(lay, s0, patch) {
      let ox = lay.ox, oy = lay.oy;
      const sc = lay.scale;
      if (patch.sx != null && s0.sx != null && isFinite(patch.sx) && isFinite(s0.sx)) {
        ox = lay.ox + (s0.sx - patch.sx) * sc;
      }
      if (patch.L != null && s0.L != null && patch.sz == null) {
        oy = lay.oy - (patch.L - s0.L) * sc;
      }
      if (patch.H != null && s0.H != null) {
        oy = lay.oy - (patch.H - s0.H) * sc;
      }
      return { ox: ox, oy: oy };
    }
    function toPx(x, z, lay) {
      /* Ceiling view: +X right, +Z up the page (Front at top). Mic near Back/bottom. */
      return { px: lay.ox + x * lay.scale, py: lay.oy + (lay.L - z) * lay.scale };
    }
    function toM(px, py, lay) {
      return { x: (px - lay.ox) / lay.scale, z: lay.L - (py - lay.oy) / lay.scale };
    }
    function floorOutlinePx(st, lay) {
      if (global.RoomShape) return RoomShape.floorPx(st.room_shape, st.W, st.L, lay);
      return [
        { px: lay.ox, py: lay.oy + lay.rh },
        { px: lay.ox + lay.rw, py: lay.oy + lay.rh },
        { px: lay.ox + lay.rw, py: lay.oy },
        { px: lay.ox, py: lay.oy }
      ];
    }
    function elevOutlinePx(st, lay) {
      if (global.RoomShape) return RoomShape.elevPx(st.room_shape, st.H, st.L, lay);
      return [
        { px: lay.ox, py: lay.oy + lay.rh },
        { px: lay.ox + lay.rw, py: lay.oy + lay.rh },
        { px: lay.ox + lay.rw, py: lay.oy },
        { px: lay.ox, py: lay.oy }
      ];
    }
    function traceClosed(ctx, pts) {
      ctx.beginPath();
      var i;
      for (i = 0; i < pts.length; i++) {
        if (i === 0) ctx.moveTo(pts[i].px, pts[i].py);
        else ctx.lineTo(pts[i].px, pts[i].py);
      }
      ctx.closePath();
    }
    function strokeGuides(ctx, segs) {
      if (!segs || !segs.length) return;
      ctx.save();
      ctx.setLineDash([]);
      ctx.strokeStyle = "#c4b48a";
      ctx.lineWidth = 1.5;
      var i;
      for (i = 0; i < segs.length; i++) {
        var seg = segs[i];
        if (!seg || seg.length < 2) continue;
        ctx.beginPath();
        ctx.moveTo(seg[0].px, seg[0].py);
        ctx.lineTo(seg[1].px, seg[1].py);
        ctx.stroke();
      }
      ctx.restore();
    }
    function polyOn(st) {
      return !!(global.RoomShape && RoomShape.normalize(st && st.room_shape) !== "box");
    }
    /* Room-mic drag uses the box margin. A polygon then pulls the spot inside the outline. */
    function clampRoomSpotPatch(st, cap, patch) {
      if (!polyOn(st) || !patch) return patch;
      var xk = "room_" + cap + "_x";
      var yk = "room_" + cap + "_y";
      var zk = "room_" + cap + "_z";
      var x = patch[xk] != null ? patch[xk] : st[xk];
      var y = patch[yk] != null ? patch[yk] : st[yk];
      var z = patch[zk] != null ? patch[zk] : st[zk];
      if (y == null || !isFinite(Number(y))) y = st.my;
      if (x == null || z == null || !isFinite(Number(x)) || !isFinite(Number(z))) return patch;
      var c = RoomShape.clampInside(Number(x), Number(y), Number(z), st.W, st.H, st.L, st.room_shape);
      if (patch[xk] != null) patch[xk] = c.x;
      if (patch[yk] != null) patch[yk] = c.y;
      if (patch[zk] != null) patch[zk] = c.z;
      return patch;
    }
    function ePx(z, y, lay) {
      return { px: lay.ox + z * lay.scale, py: lay.oy + (lay.H - y) * lay.scale };
    }
    function eM(px, py, lay) {
      return { z: (px - lay.ox) / lay.scale, y: lay.H - (py - lay.oy) / lay.scale };
    }
    function canvasPos(canvas, evt) {
      const r = canvas.getBoundingClientRect();
      return {
        x: (evt.clientX - r.left) * (canvas.width / r.width),
        y: (evt.clientY - r.top) * (canvas.height / r.height),
      };
    }
    function drawHandle(ctx, px, py, color, label, active, hovered) {
      const r = active ? 13 : hovered ? 12 : 10;
      ctx.beginPath();
      ctx.arc(px, py, r + 5, 0, Math.PI * 2);
      ctx.fillStyle = active || hovered ? "rgba(255,255,255,0.12)" : "transparent";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#0a0b0e";
      ctx.stroke();
      ctx.fillStyle = "#e8eaef";
      ctx.font = "600 12px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(label, px, py - r - 8);
    }
    function drawArrow(ctx, x, y, dx, dz, lenM, color, scale) {
      const ex = x + dx * lenM * scale;
      const ey = y - dz * lenM * scale;
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(ex, ey);
      ctx.stroke();
      const a = Math.atan2(ey - y, ex - x);
      ctx.beginPath();
      ctx.moveTo(ex, ey);
      ctx.lineTo(ex - 8 * Math.cos(a - 0.4), ey - 8 * Math.sin(a - 0.4));
      ctx.lineTo(ex - 8 * Math.cos(a + 0.4), ey - 8 * Math.sin(a + 0.4));
      ctx.closePath();
      ctx.fill();
    }
    function roomOn(st, cap) {
      if (!st) return false;
      if (st["place_" + cap] === "room") return true;
      return cap === "c" && st.third_mic === "room";
    }
    function roomSpotOf(st, cap) {
      if (global.RRDrag && global.RRDrag.roomSpot) return global.RRDrag.roomSpot(st, cap);
      function pick(k) {
        var v = st["room_" + cap + "_" + k];
        if (v == null || v === "" || !isFinite(Number(v))) v = st["room_" + k];
        var n = Number(v);
        return isFinite(n) ? n : 0;
      }
      return { x: pick("x"), y: pick("y"), z: pick("z"), yaw: pick("yaw") };
    }
    function roomList(st) {
      var out = [];
      ROOM_DRAW.forEach(function (cap) {
        if (roomOn(st, cap)) out.push(cap);
      });
      return out;
    }
    function hexRgba(hex, a) {
      var r = parseInt(hex.slice(1, 3), 16);
      var g = parseInt(hex.slice(3, 5), 16);
      var b = parseInt(hex.slice(5, 7), 16);
      return "rgba(" + r + "," + g + "," + b + "," + a + ")";
    }
    function aimFloorPx(dot, yawDeg) {
      var yaw = ((Number(yawDeg) || 0) * Math.PI) / 180;
      return {
        px: dot.px + ROOM_AIM_PX * Math.sin(yaw),
        py: dot.py - ROOM_AIM_PX * Math.cos(yaw)
      };
    }
    function drawRoomPattern(ctx, px, py, yawDeg, family, polar, color) {
      var RM = global.RoomMath;
      if (!RM || !RM.polarGain) return;
      var yaw = ((Number(yawDeg) || 0) * Math.PI) / 180;
      var R = 20;
      var n = 48;
      var i, th, g, sx, sy;
      ctx.beginPath();
      for (i = 0; i <= n; i++) {
        th = (i / n) * Math.PI * 2;
        g = Math.abs(RM.polarGain(th - yaw, family, polar));
        sx = px + R * g * Math.sin(th);
        sy = py - R * g * Math.cos(th);
        if (i === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      }
      ctx.closePath();
      ctx.fillStyle = hexRgba(color, 0.22);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();
    }
    function drawAimDot(ctx, px, py, color, active, hovered) {
      ctx.beginPath();
      ctx.arc(px, py, active || hovered ? 6.5 : 5, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "#0a0b0e";
      ctx.stroke();
    }
    function drawRoomMicsFloor(ctx, geo) {
      var caps = roomList(geo.state);
      if (!caps.length) return;
      caps.forEach(function (cap) {
        var spot = roomSpotOf(geo.state, cap);
        var color = ROOM_COLORS[cap];
        var p = toPx(spot.x, spot.z, fl);
        var src = toPx(geo.source.x, geo.source.z, fl);
        ctx.strokeStyle = hexRgba(color, 0.35);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(p.px, p.py);
        ctx.lineTo(src.px, src.py);
        ctx.stroke();
        drawRoomPattern(
          ctx, p.px, p.py, spot.yaw,
          geo.state["family_" + cap] || "cardioid",
          geo.state["polar_" + cap],
          color
        );
        var bodyOn = !!(drag && drag.kind === "room" && drag.canvas === "floor" && drag.roomCap === cap && drag.roomPart === "body");
        drawHandle(ctx, p.px, p.py, color, cap === "c" ? "Room mic" : cap.toUpperCase(), bodyOn, hover === "room:" + cap);
        var aim = aimFloorPx(p, spot.yaw);
        var aimOn = !!(drag && drag.kind === "room" && drag.canvas === "floor" && drag.roomCap === cap && drag.roomPart === "aim");
        drawAimDot(ctx, aim.px, aim.py, color, aimOn, hover === "roomAim:" + cap);
      });
    }
    function drawRoomMicsElev(ctx, geo) {
      var caps = roomList(geo.state);
      if (!caps.length) return;
      caps.forEach(function (cap) {
        var spot = roomSpotOf(geo.state, cap);
        var color = ROOM_COLORS[cap];
        var p = ePx(spot.z, spot.y, el);
        var src = ePx(geo.source.z, geo.source.y, el);
        ctx.strokeStyle = hexRgba(color, 0.35);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(p.px, p.py);
        ctx.lineTo(src.px, src.py);
        ctx.stroke();
        var on = !!(drag && drag.kind === "room" && drag.canvas === "elev" && drag.roomCap === cap);
        drawHandle(ctx, p.px, p.py, color, cap === "c" ? "Room mic" : cap.toUpperCase(), on, hover === "roomH:" + cap);
      });
    }
    function roomHitsFloor(px, py, geo) {
      var hits = [];
      roomList(geo.state).forEach(function (cap) {
        var spot = roomSpotOf(geo.state, cap);
        var p = toPx(spot.x, spot.z, fl);
        var aim = aimFloorPx(p, spot.yaw);
        if (Math.hypot(px - aim.px, py - aim.py) <= ROOM_AIM_HIT) hits.push({ cap: cap, part: "aim" });
        else if (Math.hypot(px - p.px, py - p.py) <= HIT) hits.push({ cap: cap, part: "body" });
      });
      return hits;
    }
    function roomHitsElev(px, py, geo) {
      var hits = [];
      roomList(geo.state).forEach(function (cap) {
        var spot = roomSpotOf(geo.state, cap);
        var p = ePx(spot.z, spot.y, el);
        if (Math.hypot(px - p.px, py - p.py) <= HIT) hits.push({ cap: cap, part: "body" });
      });
      return hits;
    }
    /* Room-mic handles before the stand (hitFloor / hitElev) and before any wall hit. */
    function pickRoomHit(hits) {
      if (!hits.length || !global.RRDrag || !global.RRDrag.pickRoomMic) return null;
      var dragging = drag && drag.kind === "room" ? drag.roomCap : null;
      var cap = global.RRDrag.pickRoomMic(ROOM_DRAW, hits.map(function (h) { return h.cap; }), dragging);
      if (!cap) return null;
      var i;
      for (i = hits.length - 1; i >= 0; i--) {
        if (hits[i].cap === cap) return hits[i];
      }
      return null;
    }

    const RING_PX = 30;
    const RING_HIT = 16;

    function poseOf(st, which) {
      if (which === "b" && RoomMath.effectiveBPose) return RoomMath.effectiveBPose(st);
      return {
        preset: String(st.source_radiation || "omni"),
        yaw: Number(st.source_yaw) || 0,
        pitch: Number(st.source_pitch) || 0
      };
    }
    function yawOf(st, which) {
      return poseOf(st, which).yaw;
    }
    function pitchOf(st, which) {
      return poseOf(st, which).pitch;
    }
    function presetId(st, which) {
      return poseOf(st, which).preset;
    }
    function isOmniSrc(st, which) {
      return presetId(st, which).toLowerCase() === "omni";
    }
    function wrapDeg(d) {
      let x = Number(d) || 0;
      x = ((x + 540) % 360) - 180;
      return x;
    }
    function setYawPitch(st, which, yaw, pitch) {
      if (which === "b") {
        if (yaw != null) st.source_yaw_b = wrapDeg(yaw);
        if (pitch != null) st.source_pitch_b = Math.max(-89, Math.min(89, pitch));
      } else {
        if (yaw != null) st.source_yaw = wrapDeg(yaw);
        if (pitch != null) st.source_pitch = Math.max(-89, Math.min(89, pitch));
      }
    }
    function faceMicState(st, which) {
      const geo = RoomMath.compute(st);
      const src = which === "b" && geo.source_b ? geo.source_b : geo.source;
      const mic = geo.mic_centre;
      const dx = mic.x - src.x;
      const dy = mic.y - src.y;
      const dz = mic.z - src.z;
      setYawPitch(
        st, which,
        Math.atan2(dx, dz) * 180 / Math.PI,
        Math.atan2(dy, Math.hypot(dx, dz)) * 180 / Math.PI
      );
    }
    function metaFor(which) {
      try { return sourceMeta(which) || null; } catch (e) { return null; }
    }
    function sizeMetres(st, which) {
      const raw = st.source_size_m;
      if (raw != null && raw !== "" && isFinite(Number(raw)) && Number(raw) > 0) return Number(raw);
      const meta = metaFor(which);
      if (meta && Number(meta.a_eq_m) > 0) return Number(meta.a_eq_m);
      return 0;
    }
    function ringFloor(dot, yawDeg) {
      const yaw = yawDeg * Math.PI / 180;
      return { px: dot.px + Math.sin(yaw) * RING_PX, py: dot.py - Math.cos(yaw) * RING_PX };
    }
    function ringElev(dot, pitchDeg) {
      const p = pitchDeg * Math.PI / 180;
      return { px: dot.px + Math.cos(p) * RING_PX, py: dot.py - Math.sin(p) * RING_PX };
    }
    function drawLobe(ctx, dot, yawDeg, curve, angles) {
      if (!curve || !curve.length) return;
      ctx.beginPath();
      for (let i = 0; i < curve.length; i++) {
        const azDeg = angles && angles.length === curve.length ? angles[i] : (-180 + i * 5);
        const az = azDeg * Math.PI / 180;
        const yaw = yawDeg * Math.PI / 180;
        const db = Number(curve[i]);
        const t = Math.max(0, Math.min(1, (db + 30) / 30));
        const rad = 8 + t * 62;
        const x = dot.px + Math.sin(az + yaw) * rad;
        const y = dot.py - Math.cos(az + yaw) * rad;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.fillStyle = "rgba(255,179,71,0.16)";
      ctx.fill();
      ctx.strokeStyle = "rgba(255,179,71,0.45)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    function drawSizeCircle(ctx, dot, metres, scale) {
      if (!(metres > 0) || !(scale > 0)) return;
      const r = Math.max(4, metres * scale);
      ctx.beginPath();
      ctx.arc(dot.px, dot.py, r, 0, Math.PI * 2);
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = "rgba(255,179,71,0.55)";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.setLineDash([]);
    }
    function drawHollow(ctx, x, y, color, active) {
      ctx.beginPath();
      ctx.arc(x, y, active ? 8 : 6.5, 0, Math.PI * 2);
      ctx.strokeStyle = color;
      ctx.lineWidth = active ? 2.5 : 2;
      ctx.stroke();
    }
    function drawSourceUnder(ctx, geo, plane) {
      const st = geo.state;
      const items = [{ which: "a", src: geo.source }];
      if (geo.source_b) items.push({ which: "b", src: geo.source_b });
      items.forEach(function (it) {
        if (isOmniSrc(st, it.which)) return;
        if (plane === "floor" && it.which === "b" && stackedFloor(geo)) return;
        if (plane === "elev" && it.which === "b" && stackedElev(geo)) return;
        const dot = plane === "floor"
          ? toPx(it.src.x, it.src.z, fl)
          : ePx(it.src.z, it.src.y, el);
        const meta = metaFor(it.which);
        const scale = plane === "floor" ? fl.scale : el.scale;
        drawSizeCircle(ctx, dot, sizeMetres(st, it.which), scale);
        if (plane === "floor" && meta && meta.horizontal) {
          drawLobe(ctx, dot, yawOf(st, it.which), meta.horizontal["2000"] || meta.horizontal[2000], meta.angles);
        }
      });
    }
    function drawSourceRings(ctx, geo, plane) {
      const st = geo.state;
      const items = [{ which: "a", src: geo.source, color: COLORS.src }];
      if (geo.source_b) items.push({ which: "b", src: geo.source_b, color: COLORS.srcB });
      items.forEach(function (it) {
        if (isOmniSrc(st, it.which)) return;
        if (plane === "floor" && it.which === "b" && stackedFloor(geo)) return;
        if (plane === "elev" && it.which === "b" && stackedElev(geo)) return;
        const dot = plane === "floor"
          ? toPx(it.src.x, it.src.z, fl)
          : ePx(it.src.z, it.src.y, el);
        const ring = plane === "floor"
          ? ringFloor(dot, yawOf(st, it.which))
          : ringElev(dot, pitchOf(st, it.which));
        const kind = plane === "floor"
          ? (it.which === "b" ? "srcBYaw" : "srcYaw")
          : (it.which === "b" ? "srcBPitch" : "srcPitch");
        const active = !!(drag && drag.kind === kind);
        ctx.beginPath();
        ctx.moveTo(dot.px, dot.py);
        ctx.lineTo(ring.px, ring.py);
        ctx.strokeStyle = it.color;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        drawHollow(ctx, ring.px, ring.py, it.color, active || hover === kind);
        if (active || hover === kind) {
          const off = offMicDeg(st, it.which);
          const label = (plane === "floor" ? "yaw " : "pitch ") +
            (plane === "floor" ? Math.round(yawOf(st, it.which)) : Math.round(pitchOf(st, it.which))) +
            "° · " + (off >= 0 ? "+" : "") + Math.round(off) + "° off mic";
          ctx.font = "600 11px Segoe UI, system-ui, sans-serif";
          ctx.fillStyle = "#e8eaef";
          ctx.textAlign = "left";
          ctx.fillText(label, ring.px + 12, ring.py - 8);
        }
      });
    }
    function offMicDeg(st, which) {
      const geo = RoomMath.compute(st);
      const src = which === "b" && geo.source_b ? geo.source_b : geo.source;
      const mic = geo.mic_centre;
      const dx = mic.x - src.x;
      const dz = mic.z - src.z;
      const face = Math.atan2(dx, dz) * 180 / Math.PI;
      return ((yawOf(st, which) - face + 540) % 360) - 180;
    }
    function nearestSrc(px, py, geo, plane) {
      const st = geo.state;
      let best = null;
      let bestD = 1e9;
      function consider(which, src) {
        if (!src || isOmniSrc(st, which)) return;
        if (plane === "floor" && which === "b" && stackedFloor(geo)) return;
        if (plane === "elev" && which === "b" && stackedElev(geo)) return;
        const dot = plane === "floor" ? toPx(src.x, src.z, fl) : ePx(src.z, src.y, el);
        const d = Math.hypot(px - dot.px, py - dot.py);
        if (d < bestD) { bestD = d; best = { which: which, dot: dot, d: d }; }
      }
      consider("a", geo.source);
      consider("b", geo.source_b);
      return best;
    }
    function hitRing(px, py, geo, plane) {
      const st = geo.state;
      let found = null;
      let best = RING_HIT;
      function consider(which, src) {
        if (!src || isOmniSrc(st, which)) return;
        if (plane === "floor" && which === "b" && stackedFloor(geo)) return;
        if (plane === "elev" && which === "b" && stackedElev(geo)) return;
        const dot = plane === "floor" ? toPx(src.x, src.z, fl) : ePx(src.z, src.y, el);
        const ring = plane === "floor" ? ringFloor(dot, yawOf(st, which)) : ringElev(dot, pitchOf(st, which));
        const d = Math.hypot(px - ring.px, py - ring.py);
        const dotD = Math.hypot(px - dot.px, py - dot.py);
        if (d <= best && d < dotD) {
          best = d;
          found = plane === "floor"
            ? (which === "b" ? "srcBYaw" : "srcYaw")
            : (which === "b" ? "srcBPitch" : "srcPitch");
        }
      }
      consider("b", geo.source_b);
      consider("a", geo.source);
      return found;
    }

    function drawFloor(geo) {
      const ctx = fctx;
      const cw = floorCanvas.width, ch = floorCanvas.height;
      fl = floorLayout(geo);
      ctx.clearRect(0, 0, cw, ch);
      ctx.fillStyle = "#0a0b0e";
      ctx.fillRect(0, 0, cw, ch);
      const outline = floorOutlinePx(geo.state, fl);
      ctx.fillStyle = "#12141a";
      ctx.strokeStyle = "#3a4155";
      ctx.lineWidth = 2;
      traceClosed(ctx, outline);
      ctx.fill();
      ctx.stroke();

      const clipSplay = polyOn(geo.state);
      if (clipSplay) {
        ctx.save();
        traceClosed(ctx, outline);
        ctx.clip();
      }
      ctx.strokeStyle = "rgba(255,255,255,0.04)";
      ctx.lineWidth = 1;
      const step = Math.max(0.5, Math.round(Math.min(geo.state.W, geo.state.L) / 8 * 2) / 2);
      let x, z, a, b;
      for (x = 0; x <= geo.state.W + 1e-9; x += step) {
        a = toPx(x, 0, fl);
        b = toPx(x, geo.state.L, fl);
        ctx.beginPath();
        ctx.moveTo(a.px, a.py);
        ctx.lineTo(b.px, b.py);
        ctx.stroke();
      }
      for (z = 0; z <= geo.state.L + 1e-9; z += step) {
        a = toPx(0, z, fl);
        b = toPx(geo.state.W, z, fl);
        ctx.beginPath();
        ctx.moveTo(a.px, a.py);
        ctx.lineTo(b.px, b.py);
        ctx.stroke();
      }
      if (clipSplay) ctx.restore();

      if (geo.state.reaktor_parity) {
        a = toPx(geo.state.W * 0.5, 0, fl);
        b = toPx(geo.state.W * 0.5, geo.state.L, fl);
        ctx.setLineDash([6, 6]);
        ctx.strokeStyle = "rgba(139,146,165,0.55)";
        ctx.beginPath();
        ctx.moveTo(a.px, a.py);
        ctx.lineTo(b.px, b.py);
        ctx.stroke();
        ctx.setLineDash([]);
      }
      if (global.RoomShape && RoomShape.planGuidesPx) {
        strokeGuides(ctx, RoomShape.planGuidesPx(geo.state.room_shape, geo.state.W, geo.state.L, fl));
      }

      const Sp = toPx(geo.source.x, geo.source.z, fl);
      const Cp = toPx(geo.mic_centre.x, geo.mic_centre.z, fl);
      const Lp = toPx(geo.mic_left.x, geo.mic_left.z, fl);
      const Rp = toPx(geo.mic_right.x, geo.mic_right.z, fl);
      const lRoom = roomOn(geo.state, "l");
      const rRoom = roomOn(geo.state, "r");
      const cRoom = roomOn(geo.state, "c");

      /* A Room strip is not on the stand, so the L–R bar does not run through that end. */
      if (!lRoom && !rRoom) {
        ctx.strokeStyle = "rgba(96,165,250,0.35)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(Lp.px, Lp.py);
        ctx.lineTo(Rp.px, Rp.py);
        ctx.stroke();
      }

      const al = Math.max(0.45, Math.min(geo.state.W, geo.state.L) * 0.09);
      if (!lRoom) drawArrow(ctx, Lp.px, Lp.py, geo.look_l.x, geo.look_l.z, al, COLORS.L, fl.scale);
      if (!rRoom) drawArrow(ctx, Rp.px, Rp.py, geo.look_r.x, geo.look_r.z, al, COLORS.R, fl.scale);
      if (geo.state.mic_setup === "binaural" && !cRoom) {
        drawArrow(ctx, Cp.px, Cp.py, geo.look_c.x, geo.look_c.z, al * 0.55, COLORS.mic, fl.scale);
      }

      drawSourceUnder(ctx, geo, "floor");
      if (!lRoom) drawHandle(ctx, Lp.px, Lp.py, COLORS.L, "", false, false);
      if (!rRoom) drawHandle(ctx, Rp.px, Rp.py, COLORS.R, "", false, false);
      function offsetCapsuleLabel(px, py, look, text) {
        var dx = Number(look && look.x) || 0;
        var dz = Number(look && look.z) || 0;
        var len = Math.hypot(dx, dz);
        if (len < 1e-6) {
          dx = text === "L" ? -1 : 1;
          dz = 0;
          len = 1;
        }
        dx /= len;
        dz /= len;
        /* Aim at ORTF points toward the source, which is also where "Mic" is drawn.
           A sideways push keeps L left of the stand and R right of it. */
        var side = text === "L" ? -1 : 1;
        var ox = dx * 14 + side * 26;
        var oy = -dz * 14;
        var mag = Math.hypot(ox, oy);
        if (mag < 30) {
          ox *= 30 / mag;
          oy *= 30 / mag;
        }
        ctx.fillStyle = "#e8eaef";
        ctx.font = "600 12px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(text, px + ox, py + oy);
      }
      if (!lRoom) offsetCapsuleLabel(Lp.px, Lp.py, geo.look_l, "L");
      if (!rRoom) offsetCapsuleLabel(Rp.px, Rp.py, geo.look_r, "R");
      ctx.textBaseline = "alphabetic";
      drawHandle(ctx, Cp.px, Cp.py, COLORS.mic, "Mic", !!(drag && drag.kind === "mic"), hover === "mic");
      const two = !!geo.source_b;
      drawHandle(ctx, Sp.px, Sp.py, COLORS.src, two ? "A" : "Src", !!(drag && drag.kind === "source"), hover === "source");
      if (two && !stackedFloor(geo)) {
        const Bp = toPx(geo.source_b.x, geo.source_b.z, fl);
        drawHandle(ctx, Bp.px, Bp.py, COLORS.srcB, "B", !!(drag && drag.kind === "sourceB"), hover === "sourceB");
      }
      drawSourceRings(ctx, geo, "floor");
      drawRoomMicsFloor(ctx, geo);

      ctx.fillStyle = "#8b92a5";
      ctx.font = "600 11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Front (+Z)", fl.ox + fl.rw / 2, Math.max(14, fl.oy - 10));
      ctx.fillText("Back", fl.ox + fl.rw / 2, fl.oy + fl.rh + 16);
      ctx.fillText("Width X →", fl.ox + fl.rw / 2, fl.oy + fl.rh + 30);
      ctx.textBaseline = "middle";
      ctx.textAlign = "right";
      ctx.fillText("Left", fl.ox - 8, fl.oy + fl.rh / 2);
      ctx.textAlign = "left";
      ctx.fillText("Right", fl.ox + fl.rw + 10, fl.oy + fl.rh / 2);
      ctx.textBaseline = "alphabetic";
      ctx.save();
      ctx.translate(fl.ox - 42, fl.oy + fl.rh / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = "center";
      ctx.fillText("Length +Z →", 0, 0);
      ctx.restore();
      ctx.textAlign = "left";
      ctx.fillStyle = "#5c6478";
      ctx.font = "12px Segoe UI, system-ui, sans-serif";
      ctx.fillText(geo.state.W.toFixed(1) + " × " + geo.state.L.toFixed(1) + " m", 14, 22);
    }

    function drawElev(geo) {
      const ctx = ectx;
      const cw = elevCanvas.width, ch = elevCanvas.height;
      el = elevLayout(geo);
      ctx.clearRect(0, 0, cw, ch);
      ctx.fillStyle = "#0a0b0e";
      ctx.fillRect(0, 0, cw, ch);
      ctx.fillStyle = "#12141a";
      ctx.strokeStyle = "#3a4155";
      ctx.lineWidth = 2;
      traceClosed(ctx, elevOutlinePx(geo.state, el));
      ctx.fill();
      ctx.stroke();
      if (global.RoomShape && RoomShape.elevGuidesPx) {
        strokeGuides(ctx, RoomShape.elevGuidesPx(geo.state.room_shape, geo.state.H, geo.state.L, el));
      }

      ctx.fillStyle = "#8b92a5";
      ctx.font = "11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText("Floor", el.ox + 6, el.oy + el.rh - 6);
      ctx.fillText("Ceiling", el.ox + 6, el.oy + 14);

      const Sp = ePx(geo.source.z, geo.source.y, el);
      const Cp = ePx(geo.mic_centre.z, geo.mic_centre.y, el);
      const Sf = ePx(geo.source.z, 0, el);
      const Fp = ePx(geo.mic_centre.z, 0, el);

      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = "rgba(251,191,36,0.35)";
      ctx.beginPath();
      ctx.moveTo(Sf.px, Sf.py);
      ctx.lineTo(Sp.px, Sp.py);
      ctx.stroke();
      ctx.strokeStyle = "rgba(96,165,250,0.4)";
      ctx.beginPath();
      ctx.moveTo(Fp.px, Fp.py);
      ctx.lineTo(Cp.px, Cp.py);
      ctx.stroke();
      ctx.setLineDash([]);

      drawSourceUnder(ctx, geo, "elev");
      const srcActive = !!(drag && drag.kind === "srcHeight");
      const micActive = !!(drag && (drag.kind === "micHeight" || drag.kind === "height"));
      const srcPrimary = lastDragged === "source";
      const micPrimary = lastDragged === "mic";
      const two = !!geo.source_b;
      drawHandle(ctx, Sp.px, Sp.py, COLORS.src, two ? "A" : "Src H", srcActive || srcPrimary, hover === "srcHeight");
      if (two && !stackedElev(geo)) {
        const Bp = ePx(geo.source_b.z, geo.source_b.y, el);
        const Bf = ePx(geo.source_b.z, 0, el);
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = "rgba(244,63,94,0.4)";
        ctx.beginPath();
        ctx.moveTo(Bf.px, Bf.py);
        ctx.lineTo(Bp.px, Bp.py);
        ctx.stroke();
        ctx.setLineDash([]);
        drawHandle(
          ctx, Bp.px, Bp.py, COLORS.srcB, "B",
          !!(drag && drag.kind === "srcBHeight"), hover === "srcBHeight"
        );
      }
      drawSourceRings(ctx, geo, "elev");
      drawHandle(ctx, Cp.px, Cp.py, COLORS.mic, "Mic H", micActive || micPrimary, hover === "micHeight" || hover === "height");
      drawRoomMicsElev(ctx, geo);

      ctx.fillStyle = "#5c6478";
      ctx.font = "12px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText("Back", el.ox + 6, ch - 8);
      ctx.textAlign = "right";
      ctx.fillText("Front", el.ox + el.rw - 6, ch - 8);
      ctx.textAlign = "center";
      ctx.fillText("Length Z →", el.ox + el.rw / 2, ch - 8);
      ctx.textAlign = "left";
      ctx.textBaseline = "alphabetic";
      var heightY = Math.max(14, el.oy - 16);
      ctx.fillStyle = COLORS.src;
      ctx.fillText((two ? "A " : "Src ") + geo.state.sy.toFixed(2) + " m", 10, heightY);
      ctx.fillStyle = COLORS.mic;
      ctx.fillText("Mic " + geo.state.my.toFixed(2) + " m", 118, heightY);
      if (two && geo.source_b && !stackedElev(geo)) {
        ctx.fillStyle = COLORS.srcB;
        ctx.fillText("B " + geo.source_b.y.toFixed(2) + " m", 230, heightY);
      }
    }

    function fitSourceBuffer(canvas) {
      if (!canvas || !canvas.id || canvas.id.indexOf("src") !== 0) return;
      var rect = canvas.getBoundingClientRect();
      var w = Math.floor(rect.width);
      var h = Math.floor(rect.height);
      if (w < 2 || h < 2) return;
      var pr = Math.min(window.devicePixelRatio || 1, 2);
      var bw = Math.floor(w * pr);
      var bh = Math.floor(h * pr);
      if (canvas.width !== bw || canvas.height !== bh) {
        canvas.width = bw;
        canvas.height = bh;
      }
    }
    function redraw() {
      fitSourceBuffer(floorCanvas);
      fitSourceBuffer(elevCanvas);
      const geo = RoomMath.compute(getState());
      drawFloor(geo);
      drawElev(geo);
      if (view3d) view3d.redraw();
      return geo;
    }

    function stackedFloor(geo) {
      if (!geo.source_b || !geo.state.mirror_b) return false;
      return Math.hypot(geo.source.x - geo.source_b.x, geo.source.z - geo.source_b.z) < 0.03;
    }
    function stackedElev(geo) {
      if (!geo.source_b || !geo.state.mirror_b) return false;
      return Math.hypot(geo.source.z - geo.source_b.z, geo.source.y - geo.source_b.y) < 0.03;
    }
    function floorDists(px, py, geo) {
      const Sp = toPx(geo.source.x, geo.source.z, fl);
      const Cp = toPx(geo.mic_centre.x, geo.mic_centre.z, fl);
      let db = 1e9;
      if (geo.source_b) {
        const Bp = toPx(geo.source_b.x, geo.source_b.z, fl);
        db = Math.hypot(px - Bp.px, py - Bp.py);
      }
      return {
        ds: Math.hypot(px - Sp.px, py - Sp.py),
        dc: Math.hypot(px - Cp.px, py - Cp.py),
        db: db,
      };
    }
    function elevDists(px, py, geo) {
      const Sp = ePx(geo.source.z, geo.source.y, el);
      const Cp = ePx(geo.mic_centre.z, geo.mic_centre.y, el);
      let db = 1e9;
      if (geo.source_b) {
        const Bp = ePx(geo.source_b.z, geo.source_b.y, el);
        db = Math.hypot(px - Bp.px, py - Bp.py);
      }
      return {
        ds: Math.hypot(px - Sp.px, py - Sp.py),
        dc: Math.hypot(px - Cp.px, py - Cp.py),
        db: db,
      };
    }
    function hitFloor(px, py, geo) {
      const ring = hitRing(px, py, geo, "floor");
      if (ring) return ring;
      const d = floorDists(px, py, geo);
      /* B wins a real overlap. A locked pair that shares one pixel stays A,
         so Mirror keeps following while you drag height or the centerline. */
      if (geo.source_b && !stackedFloor(geo) && d.db <= HIT && d.db <= d.dc) return "sourceB";
      if (d.ds <= HIT && d.ds <= d.dc) return "source";
      if (d.dc <= HIT) return "mic";
      return null;
    }
    function pickFloorKind(px, py, geo) {
      const hit = hitFloor(px, py, geo);
      if (hit) return hit;
      const d = floorDists(px, py, geo);
      let nearest = "source";
      let best = d.ds;
      if (geo.source_b && !stackedFloor(geo) && d.db < best) { nearest = "sourceB"; best = d.db; }
      if (d.dc < best) { nearest = "mic"; best = d.dc; }
      if (best <= FAR) return nearest;
      return lastDragged === "sourceB" ? "sourceB" : lastDragged;
    }
    function hitElev(px, py, geo) {
      const ring = hitRing(px, py, geo, "elev");
      if (ring) return ring;
      const d = elevDists(px, py, geo);
      const bHit = geo.source_b && !stackedElev(geo) && d.db <= HIT;
      const srcHit = d.ds <= HIT;
      const micHit = d.dc <= HIT;
      if (bHit && d.db <= d.dc) return "srcBHeight";
      if (srcHit && micHit) return d.ds <= d.dc ? "srcHeight" : "micHeight";
      if (srcHit) return "srcHeight";
      if (micHit) return "micHeight";
      return null;
    }
    function pickElevKind(px, py, geo) {
      const hit = hitElev(px, py, geo);
      if (hit) return hit;
      const d = elevDists(px, py, geo);
      let nearest = "srcHeight";
      let best = d.ds;
      if (geo.source_b && !stackedElev(geo) && d.db < best) { nearest = "srcBHeight"; best = d.db; }
      if (d.dc < best) { nearest = "micHeight"; best = d.dc; }
      if (best <= FAR) return nearest;
      if (lastDragged === "sourceB") return "srcBHeight";
      return lastDragged === "source" ? "srcHeight" : "micHeight";
    }

    function applyLinkedHeight(st, kind, y) {
      const yy = RoomMath.clamp(y, 0, st.H);
      if (kind === "srcHeight") {
        st.sy = yy;
        if (st.link_heights) st.my = yy;
      } else {
        st.my = yy;
        if (st.link_heights) st.sy = yy;
      }
    }

    function endDrag() {
      var was = drag;
      drag = null;
      floorCanvas.classList.remove("dragging");
      elevCanvas.classList.remove("dragging");
      redraw();
      if (was) onDragEnd();
    }

    function mergePatch(patch) {
      const st = Object.assign({}, getState(), patch);
      setState(RoomMath.clampRoom(st));
      onChange();
    }

    floorCanvas.addEventListener("pointerdown", function (evt) {
      const geo = RoomMath.compute(getState());
      fl = floorLayout(geo);
      const p = canvasPos(floorCanvas, evt);
      const roomHit = pickRoomHit(roomHitsFloor(p.x, p.y, geo));
      if (roomHit && global.RRDrag && global.RRDrag.roomFloorDragTo && global.RRDrag.roomAimDragTo) {
        drag = { kind: "room", canvas: "floor", roomCap: roomHit.cap, roomPart: roomHit.part };
        floorCanvas.classList.add("dragging");
        try { floorCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
        redraw();
        evt.preventDefault();
        return;
      }
      const onHandle = !!hitFloor(p.x, p.y, geo);
      const wallHit = (!onHandle && global.RRDrag && global.RRDrag.hitWall)
        ? global.RRDrag.hitWall(p.x, p.y, fl) : null;
      if (wallHit) {
        drag = {
          kind: "wall",
          canvas: "floor",
          ctx: global.RRDrag.beginWallDrag(getState(), wallHit, fl, p.x, p.y)
        };
        floorCanvas.classList.add("dragging");
        try { floorCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
        redraw();
        evt.preventDefault();
        return;
      }
      let kind = pickFloorKind(p.x, p.y, geo);
      if (evt.altKey) {
        const near = nearestSrc(p.x, p.y, geo, "floor");
        if (near && near.d <= HIT + 28) kind = near.which === "b" ? "srcBSize" : "srcSize";
      }
      lastDragged = (kind === "mic") ? "mic"
        : (kind === "sourceB" || kind === "srcBYaw" || kind === "srcBSize") ? "sourceB"
        : "source";
      drag = { kind: kind, canvas: "floor" };
      floorCanvas.classList.add("dragging");
      try { floorCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
      const facingKind = kind === "srcYaw" || kind === "srcBYaw" || kind === "srcSize" || kind === "srcBSize";
      if (!onHandle && !facingKind) {
        /* Empty floor: move selected object to click, then drag */
        const m = toM(p.x, p.y, fl);
        const st = Object.assign({}, getState());
        if (kind === "sourceB") {
          st.mirror_b = false;
          st.sx_b = RoomMath.clamp(m.x, 0, st.W);
          st.sz_b = RoomMath.clamp(m.z, 0, st.L);
        } else if (kind === "source") {
          st.sx = RoomMath.clamp(m.x, 0, st.W);
          st.sz = RoomMath.clamp(m.z, 0, st.L);
        } else {
          if (!st.reaktor_parity) st.mcx = RoomMath.clamp(m.x, 0, st.W);
          st.mcz = RoomMath.clamp(m.z, 0, st.L);
        }
        setState(RoomMath.clampRoom(st));
        onChange();
      }
      redraw();
      evt.preventDefault();
    });

    floorCanvas.addEventListener("pointermove", function (evt) {
      const geo = RoomMath.compute(getState());
      fl = floorLayout(geo);
      const p = canvasPos(floorCanvas, evt);
      if (drag && drag.canvas === "floor") {
        const st0 = getState();
        if (drag.kind === "wall" && global.RRDrag && drag.ctx) {
          const res = global.RRDrag.wallDragTo(drag.ctx, p.x, p.y, { shift: !!evt.shiftKey, mode: "stop" });
          drag.view = viewForPatch(drag.ctx.lay, drag.ctx.s0, res.patch);
          mergePatch(res.patch);
          redraw();
          return;
        }
        if (drag.kind === "room" && global.RRDrag) {
          const spot = roomSpotOf(st0, drag.roomCap);
          const dot = toPx(spot.x, spot.z, fl);
          let patch;
          if (drag.roomPart === "aim") {
            const yaw = Math.atan2(p.x - dot.px, -(p.y - dot.py)) * 180 / Math.PI;
            patch = global.RRDrag.roomAimDragTo(st0, drag.roomCap, yaw);
          } else {
            const rm = toM(p.x, p.y, fl);
            patch = global.RRDrag.roomFloorDragTo(st0, drag.roomCap, rm.x, rm.z);
          }
          setState(clampRoomSpotPatch(st0, drag.roomCap, patch));
          onChange();
          redraw();
          return;
        }
        if (drag.kind === "srcYaw" || drag.kind === "srcBYaw" || drag.kind === "srcSize" || drag.kind === "srcBSize") {
          const which = (drag.kind === "srcBYaw" || drag.kind === "srcBSize") ? "b" : "a";
          const src = which === "b" && geo.source_b ? geo.source_b : geo.source;
          const dot = toPx(src.x, src.z, fl);
          const st = Object.assign({}, st0);
          if (drag.kind === "srcSize" || drag.kind === "srcBSize") {
            const pxR = Math.max(4, Math.hypot(p.x - dot.px, p.y - dot.py));
            st.source_size_m = Math.max(0.005, Math.min(0.6, pxR / Math.max(1e-6, fl.scale)));
          } else {
            let yaw = Math.atan2(p.x - dot.px, -(p.y - dot.py)) * 180 / Math.PI;
            if (evt.shiftKey) yaw = Math.round(yaw / 15) * 15;
            setYawPitch(st, which, yaw, null);
          }
          setState(RoomMath.clampRoom(st));
          onChange();
          redraw();
          return;
        }
        const m = toM(p.x, p.y, fl);
        const st = Object.assign({}, st0);
        if (drag.kind === "sourceB") {
          st.mirror_b = false;
          st.sx_b = RoomMath.clamp(m.x, 0, st.W);
          st.sz_b = RoomMath.clamp(m.z, 0, st.L);
        } else if (drag.kind === "source") {
          st.sx = RoomMath.clamp(m.x, 0, st.W);
          st.sz = RoomMath.clamp(m.z, 0, st.L);
        } else {
          if (!st.reaktor_parity) st.mcx = RoomMath.clamp(m.x, 0, st.W);
          st.mcz = RoomMath.clamp(m.z, 0, st.L);
        }
        setState(RoomMath.clampRoom(st));
        onChange();
        redraw();
        return;
      }
      const roomHover = pickRoomHit(roomHitsFloor(p.x, p.y, geo));
      const h = roomHover
        ? (roomHover.part === "aim" ? "roomAim:" + roomHover.cap : "room:" + roomHover.cap)
        : hitFloor(p.x, p.y, geo);
      let floorCursor = (h === "srcYaw" || h === "srcBYaw" || (typeof h === "string" && h.indexOf("roomAim:") === 0)) ? "all-scroll" : "";
      if (!floorCursor && !h && global.RRDrag && global.RRDrag.hitWall) {
        const wh = global.RRDrag.hitWall(p.x, p.y, fl);
        if (wh) floorCursor = global.RRDrag.cursorFor(wh) || "";
      }
      floorCanvas.style.cursor = floorCursor;
      if (h !== hover) {
        hover = h;
        redraw();
      }
    });

    elevCanvas.addEventListener("pointerdown", function (evt) {
      const geo = RoomMath.compute(getState());
      el = elevLayout(geo);
      const p = canvasPos(elevCanvas, evt);
      const roomHit = pickRoomHit(roomHitsElev(p.x, p.y, geo));
      if (roomHit && global.RRDrag && global.RRDrag.roomHeightDragTo) {
        drag = { kind: "room", canvas: "elev", roomCap: roomHit.cap, roomPart: "body" };
        elevCanvas.classList.add("dragging");
        try { elevCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
        redraw();
        evt.preventDefault();
        return;
      }
      const onHandle = !!hitElev(p.x, p.y, geo);
      const ceilHit = (!onHandle && global.RRDrag && global.RRDrag.hitCeiling)
        ? global.RRDrag.hitCeiling(p.x, p.y, el) : null;
      if (ceilHit) {
        drag = {
          kind: "ceiling",
          canvas: "elev",
          ctx: global.RRDrag.beginWallDrag(getState(), ceilHit, el, p.x, p.y)
        };
        elevCanvas.classList.add("dragging");
        try { elevCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
        redraw();
        evt.preventDefault();
        return;
      }
      const kind = pickElevKind(p.x, p.y, geo);
      lastDragged = (kind === "srcBHeight" || kind === "srcBPitch") ? "sourceB"
        : (kind === "srcHeight" || kind === "srcPitch") ? "source" : "mic";
      drag = { kind: kind, canvas: "elev" };
      elevCanvas.classList.add("dragging");
      try { elevCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
      if (!onHandle) {
        /* Empty elev: move selected height handle to click */
        const m = eM(p.x, p.y, el);
        const st = Object.assign({}, getState());
        if (kind === "srcBHeight") {
          st.mirror_b = false;
          st.sy_b = RoomMath.clamp(m.y, 0, st.H);
          st.sz_b = RoomMath.clamp(m.z, 0, st.L);
        } else {
          applyLinkedHeight(st, kind, m.y);
          if (kind === "srcHeight") {
            st.sz = RoomMath.clamp(m.z, 0, st.L);
          } else {
            st.mcz = RoomMath.clamp(m.z, 0, st.L);
          }
        }
        setState(RoomMath.clampRoom(st));
        onChange();
      }
      redraw();
      evt.preventDefault();
    });

    elevCanvas.addEventListener("pointermove", function (evt) {
      const geo = RoomMath.compute(getState());
      el = elevLayout(geo);
      const p = canvasPos(elevCanvas, evt);
      if (drag && drag.canvas === "elev") {
        if (drag.kind === "ceiling" && global.RRDrag && drag.ctx) {
          const res = global.RRDrag.ceilingDragTo(drag.ctx, p.x, p.y, el, { shift: !!evt.shiftKey });
          drag.view = viewForPatch(drag.ctx.lay, drag.ctx.s0, res.patch);
          mergePatch(res.patch);
          redraw();
          return;
        }
        if (drag.kind === "room" && global.RRDrag && global.RRDrag.roomHeightDragTo) {
          const hm = eM(p.x, p.y, el);
          setState(clampRoomSpotPatch(
            getState(), drag.roomCap,
            global.RRDrag.roomHeightDragTo(getState(), drag.roomCap, hm.y)
          ));
          onChange();
          redraw();
          return;
        }
        if (drag.kind === "srcPitch" || drag.kind === "srcBPitch") {
          const which = drag.kind === "srcBPitch" ? "b" : "a";
          const src = which === "b" && geo.source_b ? geo.source_b : geo.source;
          const dot = ePx(src.z, src.y, el);
          let pitch = Math.atan2(-(p.y - dot.py), p.x - dot.px) * 180 / Math.PI;
          pitch = Math.max(-89, Math.min(89, pitch));
          if (evt.shiftKey) pitch = Math.round(pitch / 15) * 15;
          const st = Object.assign({}, getState());
          setYawPitch(st, which, null, pitch);
          setState(RoomMath.clampRoom(st));
          onChange();
          redraw();
          return;
        }
        const m = eM(p.x, p.y, el);
        const st = Object.assign({}, getState());
        const kind = drag.kind === "height" ? "micHeight" : drag.kind;
        if (kind === "srcBHeight") {
          st.mirror_b = false;
          st.sy_b = RoomMath.clamp(m.y, 0, st.H);
          st.sz_b = RoomMath.clamp(m.z, 0, st.L);
        } else {
          applyLinkedHeight(st, kind, m.y);
          if (kind === "srcHeight") {
            st.sz = RoomMath.clamp(m.z, 0, st.L);
          } else {
            st.mcz = RoomMath.clamp(m.z, 0, st.L);
          }
        }
        setState(RoomMath.clampRoom(st));
        onChange();
        redraw();
        return;
      }
      const roomHover = pickRoomHit(roomHitsElev(p.x, p.y, geo));
      const h = roomHover ? "roomH:" + roomHover.cap : hitElev(p.x, p.y, geo);
      let elevCursor = (h === "srcPitch" || h === "srcBPitch") ? "all-scroll" : "";
      if (!elevCursor && !h && global.RRDrag && global.RRDrag.hitCeiling) {
        const chit = global.RRDrag.hitCeiling(p.x, p.y, el);
        if (chit) elevCursor = global.RRDrag.cursorFor(chit) || "ns-resize";
      }
      elevCanvas.style.cursor = elevCursor;
      if (h !== hover) {
        hover = h;
        redraw();
      }
    });

    function onFacingWheel(canvas, plane, evt) {
      const geo = RoomMath.compute(getState());
      if (plane === "floor") fl = floorLayout(geo);
      else el = elevLayout(geo);
      const p = canvasPos(canvas, evt);
      const ring = hitRing(p.x, p.y, geo, plane);
      if (!ring) return;
      evt.preventDefault();
      const which = (ring === "srcBYaw" || ring === "srcBPitch") ? "b" : "a";
      const step = evt.deltaY > 0 ? -5 : 5;
      const st = Object.assign({}, getState());
      if (plane === "floor") setYawPitch(st, which, yawOf(st, which) + step, null);
      else setYawPitch(st, which, null, pitchOf(st, which) + step);
      setState(RoomMath.clampRoom(st));
      onChange();
      redraw();
    }
    function onFacingKey(evt) {
      const k = evt.key;
      if (k !== "ArrowLeft" && k !== "ArrowRight" && k !== "ArrowUp" && k !== "ArrowDown" &&
          k !== "f" && k !== "F" && k !== "o" && k !== "O") return;
      const which = lastDragged === "sourceB" ? "b" : "a";
      const st = Object.assign({}, getState());
      if (k === "o" || k === "O") {
        if (which === "b") st.source_radiation_b = "omni";
        else st.source_radiation = "omni";
      } else if (k === "f" || k === "F") {
        faceMicState(st, which);
      } else if (k === "ArrowLeft" || k === "ArrowRight") {
        const step = k === "ArrowLeft" ? -5 : 5;
        setYawPitch(st, which, yawOf(st, which) + step, null);
      } else {
        const step = k === "ArrowDown" ? -5 : 5;
        setYawPitch(st, which, null, pitchOf(st, which) + step);
      }
      setState(RoomMath.clampRoom(st));
      onChange();
      redraw();
      evt.preventDefault();
    }
    function onFacingDbl(canvas, plane, evt) {
      const geo = RoomMath.compute(getState());
      if (plane === "floor") fl = floorLayout(geo);
      else el = elevLayout(geo);
      const p = canvasPos(canvas, evt);
      const ring = hitRing(p.x, p.y, geo, plane);
      if (!ring) return;
      const which = (ring === "srcBYaw" || ring === "srcBPitch") ? "b" : "a";
      const st = Object.assign({}, getState());
      faceMicState(st, which);
      setState(RoomMath.clampRoom(st));
      onChange();
      redraw();
    }
    floorCanvas.tabIndex = 0;
    elevCanvas.tabIndex = 0;
    floorCanvas.addEventListener("wheel", function (evt) { onFacingWheel(floorCanvas, "floor", evt); }, { passive: false });
    elevCanvas.addEventListener("wheel", function (evt) { onFacingWheel(elevCanvas, "elev", evt); }, { passive: false });
    floorCanvas.addEventListener("dblclick", function (evt) { onFacingDbl(floorCanvas, "floor", evt); });
    elevCanvas.addEventListener("dblclick", function (evt) { onFacingDbl(elevCanvas, "elev", evt); });
    floorCanvas.addEventListener("keydown", onFacingKey);
    elevCanvas.addEventListener("keydown", onFacingKey);

    floorCanvas.addEventListener("pointerup", endDrag);
    elevCanvas.addEventListener("pointerup", endDrag);
    floorCanvas.addEventListener("pointercancel", endDrag);
    elevCanvas.addEventListener("pointercancel", endDrag);
    window.addEventListener("pointerup", endDrag);

    return { redraw: redraw, setTool: setTool, view3d: view3d };
  }

  if (!global.RoomMath || !global.RoomMath.polarGain) global.RoomMath = RoomMath;
  global.RoomEditor = { create: RoomEditorCreate };
})(window);
