
/* 2011 Room Reverb — canvas drag editor. Geometry is room_math.js. */
(function (global) {
  "use strict";

  const RoomMath = global.RoomMath;

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

  var envStack = [];
  function enter(env, fn) {
    var args = [];
    var i;
    for (i = 2; i < arguments.length; i++) args.push(arguments[i]);
    envStack.push(env);
    try {
      return fn.apply(null, args);
    } finally {
      envStack.pop();
    }
  }
  function bindPass(env, fn) {
    return function () {
      envStack.push(env);
      try {
        return fn.apply(null, arguments);
      } finally {
        envStack.pop();
      }
    };
  }
  function RoomEditorCreate(opts) {
    var env = {};
    env.opts = opts;
    env.floorCanvas = env.opts.floorCanvas;
    env.elevCanvas = env.opts.elevCanvas;
    env.view3dCanvas = env.opts.view3dCanvas || null;
    env.getState = env.opts.getState;
    env.setState = env.opts.setState;
    env.onChange = env.opts.onChange;
    env.onDragEnd = env.opts.onDragEnd || function () {};
    env.sourceMeta = env.opts.sourceMeta || function () { return null; };

    env.fctx = env.floorCanvas.getContext("2d");
    env.ectx = env.elevCanvas.getContext("2d");
    env.drag = null;
    env.hover = null;
    env.lastDragged = "source"; /* "source" | "mic" — used when empty click is far from both */
    env.fl = null;
    env.el = null;

    env.view3d = null;
    if (env.view3dCanvas && global.Room3D) {
      env.view3d = global.Room3D.create({
        canvas: env.view3dCanvas,
        getState: env.getState,
        setState: env.setState,
        onChange: env.onChange,
        RoomMath: RoomMath,
        getTool: function () { return env.lastDragged; },
      });
    }

    /* Keep grabbed walls under the pointer while scale stays at pointer-down.
       x0 shifts ox; z1 and the ceiling shift oy. x1 and z0 already stay put. */

    /* Room-mic drag uses the box margin. A polygon then pulls the spot inside the outline. */

    /* Room-mic handles before the stand (hitFloor / hitElev) and before any wall hit. */

    env.RING_PX = 30;
    env.RING_HIT = 16;

    function showPlanDragNote(text) {
      var canvas = env.floorCanvas;
      var id;
      var el;
      if (!canvas || !canvas.parentNode) return;
      id = canvas.id === "srcFloorCanvas" ? "srcFloorPlanNote" : "floorPlanNote";
      el = canvas.parentNode.querySelector("#" + id);
      if (!el) return;
      el.textContent = text || "";
      el.hidden = !text;
    }

    env.floorCanvas.addEventListener("pointerdown", function (evt) {
      const geo = RoomMath.compute(env.getState());
      env.fl = enter(env, floorLayout, geo);
      const p = enter(env, canvasPos, env.floorCanvas, evt);
      const roomHit = enter(env, pickRoomHit, enter(env, roomHitsFloor, p.x, p.y, geo));
      if (roomHit && global.RRDrag && global.RRDrag.roomFloorDragTo && global.RRDrag.roomAimDragTo) {
        env.drag = { kind: "room", canvas: "floor", roomCap: roomHit.cap, roomPart: roomHit.part };
        env.floorCanvas.classList.add("dragging");
        try { env.floorCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
        enter(env, redraw);
        evt.preventDefault();
        return;
      }
      const onHandle = !!enter(env, hitFloor, p.x, p.y, geo);
      const planHit = (!onHandle && global.RoomShape && RoomShape.hitPlan)
        ? RoomShape.hitPlan(p.x, p.y, env.getState(), env.fl) : null;
      if (planHit) {
        if (RoomShape.selectPlanCorner) RoomShape.selectPlanCorner(planHit.index);
        if (typeof global.paintRoomCorners === "function") global.paintRoomCorners();
        env.drag = { kind: "plan", canvas: "floor", index: planHit.index };
        env.floorCanvas.classList.add("dragging");
        try { env.floorCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
        enter(env, redraw);
        evt.preventDefault();
        return;
      }
      const wallHit = (!onHandle && global.RRDrag && global.RRDrag.hitWall)
        ? global.RRDrag.hitWall(p.x, p.y, env.fl) : null;
      if (wallHit) {
        env.drag = {
          kind: "wall",
          canvas: "floor",
          face: faceLetter(wallHit),
          downX: p.x,
          downY: p.y,
          moved: false,
          ctx: global.RRDrag.beginWallDrag(env.getState(), wallHit, env.fl, p.x, p.y)
        };
        env.floorCanvas.classList.add("dragging");
        try { env.floorCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
        enter(env, redraw);
        evt.preventDefault();
        return;
      }
      let kind = enter(env, pickFloorKind, p.x, p.y, geo);
      if (evt.altKey) {
        const near = enter(env, nearestSrc, p.x, p.y, geo, "floor");
        if (near && near.d <= HIT + 28) kind = near.which === "b" ? "srcBSize" : "srcSize";
      }
      env.lastDragged = (kind === "mic") ? "mic"
        : (kind === "sourceB" || kind === "srcBYaw" || kind === "srcBSize") ? "sourceB"
        : "source";
      const facingKind = kind === "srcYaw" || kind === "srcBYaw" || kind === "srcSize" || kind === "srcBSize";
      env.drag = {
        kind: kind,
        canvas: "floor",
        downX: p.x,
        downY: p.y,
        moved: false,
        face: (!onHandle && !facingKind) ? "E" : ""
      };
      env.floorCanvas.classList.add("dragging");
      try { env.floorCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
      /* A still click selects the floor. A drag moves the object. */
      enter(env, redraw);
      evt.preventDefault();
    });

    env.floorCanvas.addEventListener("pointermove", function (evt) {
      const geo = RoomMath.compute(env.getState());
      env.fl = enter(env, floorLayout, geo);
      const p = enter(env, canvasPos, env.floorCanvas, evt);
      if (env.drag && env.drag.canvas === "floor") {
        const st0 = env.getState();
        if (env.drag.kind === "plan" && global.RoomShape && RoomShape.movePlanPoint) {
          const m = enter(env, toM, p.x, p.y, env.fl);
          const step = evt.shiftKey ? 0.1 : 0.01;
          const token = RoomShape.movePlanPoint(st0.room_shape, env.drag.index, m.x, m.z, st0.W, st0.L, step);
          showPlanDragNote(RoomShape.planDragNote ? RoomShape.planDragNote() : "");
          enter(env, mergePatch, { room_shape: token });
          enter(env, redraw);
          return;
        }
        if (env.drag.kind === "wall" && global.RRDrag && env.drag.ctx) {
          noteFaceMove(env.drag, p.x, p.y);
          const res = global.RRDrag.wallDragTo(env.drag.ctx, p.x, p.y, { shift: !!evt.shiftKey, mode: "stop" });
          env.drag.view = enter(env, viewForPatch, env.drag.ctx.lay, env.drag.ctx.s0, res.patch);
          enter(env, mergePatch, res.patch);
          enter(env, redraw);
          return;
        }
        if (env.drag.kind === "room" && global.RRDrag) {
          const spot = enter(env, roomSpotOf, st0, env.drag.roomCap);
          const dot = enter(env, toPx, spot.x, spot.z, env.fl);
          let patch;
          if (env.drag.roomPart === "aim") {
            const yaw = Math.atan2(p.x - dot.px, -(p.y - dot.py)) * 180 / Math.PI;
            patch = global.RRDrag.roomAimDragTo(st0, env.drag.roomCap, yaw);
          } else {
            const rm = enter(env, toM, p.x, p.y, env.fl);
            patch = global.RRDrag.roomFloorDragTo(st0, env.drag.roomCap, rm.x, rm.z);
          }
          env.setState(enter(env, clampRoomSpotPatch, st0, env.drag.roomCap, patch));
          env.onChange();
          enter(env, redraw);
          return;
        }
        if (env.drag.kind === "srcYaw" || env.drag.kind === "srcBYaw" || env.drag.kind === "srcSize" || env.drag.kind === "srcBSize") {
          const which = (env.drag.kind === "srcBYaw" || env.drag.kind === "srcBSize") ? "b" : "a";
          const src = which === "b" && geo.source_b ? geo.source_b : geo.source;
          const dot = enter(env, toPx, src.x, src.z, env.fl);
          const st = Object.assign({}, st0);
          if (env.drag.kind === "srcSize" || env.drag.kind === "srcBSize") {
            const pxR = Math.max(4, Math.hypot(p.x - dot.px, p.y - dot.py));
            st.source_size_m = Math.max(0.005, Math.min(0.6, pxR / Math.max(1e-6, env.fl.scale)));
          } else {
            let yaw = Math.atan2(p.x - dot.px, -(p.y - dot.py)) * 180 / Math.PI;
            if (evt.shiftKey) yaw = Math.round(yaw / 15) * 15;
            enter(env, setYawPitch, st, which, yaw, null);
          }
          env.setState(RoomMath.clampRoom(st));
          env.onChange();
          enter(env, redraw);
          return;
        }
        if (env.drag.face === "E") {
          noteFaceMove(env.drag, p.x, p.y);
          if (!env.drag.moved) return;
        }
        const m = enter(env, toM, p.x, p.y, env.fl);
        const st = Object.assign({}, st0);
        if (env.drag.kind === "sourceB") {
          st.mirror_b = false;
          st.sx_b = RoomMath.clamp(m.x, 0, st.W);
          st.sz_b = RoomMath.clamp(m.z, 0, st.L);
        } else if (env.drag.kind === "source") {
          st.sx = RoomMath.clamp(m.x, 0, st.W);
          st.sz = RoomMath.clamp(m.z, 0, st.L);
        } else {
          st.mcx = RoomMath.clamp(m.x, 0, st.W);
          st.mcz = RoomMath.clamp(m.z, 0, st.L);
        }
        env.setState(RoomMath.clampRoom(st));
        env.onChange();
        enter(env, redraw);
        return;
      }
      const roomHover = enter(env, pickRoomHit, enter(env, roomHitsFloor, p.x, p.y, geo));
      const h = roomHover
        ? (roomHover.part === "aim" ? "roomAim:" + roomHover.cap : "room:" + roomHover.cap)
        : enter(env, hitFloor, p.x, p.y, geo);
      let floorCursor = (h === "srcYaw" || h === "srcBYaw" || (typeof h === "string" && h.indexOf("roomAim:") === 0)) ? "all-scroll" : "";
      if (!floorCursor && !h && global.RRDrag && global.RRDrag.hitWall) {
        const wh = global.RRDrag.hitWall(p.x, p.y, env.fl);
        if (wh) floorCursor = global.RRDrag.cursorFor(wh) || "";
      }
      env.floorCanvas.style.cursor = floorCursor;
      if (h !== env.hover) {
        env.hover = h;
        enter(env, redraw);
      }
    });

    env.elevCanvas.addEventListener("pointerdown", function (evt) {
      const geo = RoomMath.compute(env.getState());
      env.el = enter(env, elevLayout, geo);
      const p = enter(env, canvasPos, env.elevCanvas, evt);
      const roomHit = enter(env, pickRoomHit, enter(env, roomHitsElev, p.x, p.y, geo));
      if (roomHit && global.RRDrag && global.RRDrag.roomHeightDragTo) {
        env.drag = { kind: "room", canvas: "elev", roomCap: roomHit.cap, roomPart: "body" };
        env.elevCanvas.classList.add("dragging");
        try { env.elevCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
        enter(env, redraw);
        evt.preventDefault();
        return;
      }
      const onHandle = !!enter(env, hitElev, p.x, p.y, geo);
      const ceilHit = (!onHandle && global.RRDrag && global.RRDrag.hitCeiling)
        ? global.RRDrag.hitCeiling(p.x, p.y, env.el) : null;
      if (ceilHit) {
        env.drag = {
          kind: "ceiling",
          canvas: "elev",
          face: faceLetter(ceilHit),
          downX: p.x,
          downY: p.y,
          moved: false,
          ctx: global.RRDrag.beginWallDrag(env.getState(), ceilHit, env.el, p.x, p.y)
        };
        env.elevCanvas.classList.add("dragging");
        try { env.elevCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
        enter(env, redraw);
        evt.preventDefault();
        return;
      }
      if (!onHandle && hitFloorEdge(p.x, p.y, env.el)) {
        env.drag = { kind: "face", canvas: "elev", face: "E", downX: p.x, downY: p.y, moved: false };
        env.elevCanvas.classList.add("dragging");
        try { env.elevCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
        enter(env, redraw);
        evt.preventDefault();
        return;
      }
      const kind = enter(env, pickElevKind, p.x, p.y, geo);
      env.lastDragged = (kind === "srcBHeight" || kind === "srcBPitch") ? "sourceB"
        : (kind === "srcHeight" || kind === "srcPitch") ? "source" : "mic";
      env.drag = { kind: kind, canvas: "elev" };
      env.elevCanvas.classList.add("dragging");
      try { env.elevCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
      if (!onHandle) {
        /* Empty elev: move selected height handle to click */
        const m = enter(env, eM, p.x, p.y, env.el);
        const st = Object.assign({}, env.getState());
        if (kind === "srcBHeight") {
          st.mirror_b = false;
          st.sy_b = RoomMath.clamp(m.y, 0, st.H);
          st.sz_b = RoomMath.clamp(m.z, 0, st.L);
        } else {
          enter(env, applyLinkedHeight, st, kind, m.y);
          if (kind === "srcHeight") {
            st.sz = RoomMath.clamp(m.z, 0, st.L);
          } else {
            st.mcz = RoomMath.clamp(m.z, 0, st.L);
          }
        }
        env.setState(RoomMath.clampRoom(st));
        env.onChange();
      }
      enter(env, redraw);
      evt.preventDefault();
    });

    env.elevCanvas.addEventListener("pointermove", function (evt) {
      const geo = RoomMath.compute(env.getState());
      env.el = enter(env, elevLayout, geo);
      const p = enter(env, canvasPos, env.elevCanvas, evt);
      if (env.drag && env.drag.canvas === "elev") {
        if (env.drag.kind === "face") {
          noteFaceMove(env.drag, p.x, p.y);
          return;
        }
        if (env.drag.kind === "ceiling" && global.RRDrag && env.drag.ctx) {
          noteFaceMove(env.drag, p.x, p.y);
          const res = global.RRDrag.ceilingDragTo(env.drag.ctx, p.x, p.y, env.el, { shift: !!evt.shiftKey });
          env.drag.view = enter(env, viewForPatch, env.drag.ctx.lay, env.drag.ctx.s0, res.patch);
          enter(env, mergePatch, res.patch);
          enter(env, redraw);
          return;
        }
        if (env.drag.kind === "room" && global.RRDrag && global.RRDrag.roomHeightDragTo) {
          const hm = enter(env, eM, p.x, p.y, env.el);
          env.setState(enter(env, clampRoomSpotPatch, 
            env.getState(), env.drag.roomCap,
            global.RRDrag.roomHeightDragTo(env.getState(), env.drag.roomCap, hm.y)
          ));
          env.onChange();
          enter(env, redraw);
          return;
        }
        if (env.drag.kind === "srcPitch" || env.drag.kind === "srcBPitch") {
          const which = env.drag.kind === "srcBPitch" ? "b" : "a";
          const src = which === "b" && geo.source_b ? geo.source_b : geo.source;
          const dot = enter(env, ePx, src.z, src.y, env.el);
          let pitch = Math.atan2(-(p.y - dot.py), p.x - dot.px) * 180 / Math.PI;
          pitch = Math.max(-89, Math.min(89, pitch));
          if (evt.shiftKey) pitch = Math.round(pitch / 15) * 15;
          const st = Object.assign({}, env.getState());
          enter(env, setYawPitch, st, which, null, pitch);
          env.setState(RoomMath.clampRoom(st));
          env.onChange();
          enter(env, redraw);
          return;
        }
        const m = enter(env, eM, p.x, p.y, env.el);
        const st = Object.assign({}, env.getState());
        const kind = env.drag.kind === "height" ? "micHeight" : env.drag.kind;
        if (kind === "srcBHeight") {
          st.mirror_b = false;
          st.sy_b = RoomMath.clamp(m.y, 0, st.H);
          st.sz_b = RoomMath.clamp(m.z, 0, st.L);
        } else {
          enter(env, applyLinkedHeight, st, kind, m.y);
          if (kind === "srcHeight") {
            st.sz = RoomMath.clamp(m.z, 0, st.L);
          } else {
            st.mcz = RoomMath.clamp(m.z, 0, st.L);
          }
        }
        env.setState(RoomMath.clampRoom(st));
        env.onChange();
        enter(env, redraw);
        return;
      }
      const roomHover = enter(env, pickRoomHit, enter(env, roomHitsElev, p.x, p.y, geo));
      const h = roomHover ? "roomH:" + roomHover.cap : enter(env, hitElev, p.x, p.y, geo);
      let elevCursor = (h === "srcPitch" || h === "srcBPitch") ? "all-scroll" : "";
      if (!elevCursor && !h && global.RRDrag && global.RRDrag.hitCeiling) {
        const chit = global.RRDrag.hitCeiling(p.x, p.y, env.el);
        if (chit) elevCursor = global.RRDrag.cursorFor(chit) || "ns-resize";
      }
      env.elevCanvas.style.cursor = elevCursor;
      if (h !== env.hover) {
        env.hover = h;
        enter(env, redraw);
      }
    });

    env.floorCanvas.tabIndex = 0;
    env.elevCanvas.tabIndex = 0;
    env.floorCanvas.addEventListener("wheel", function (evt) { enter(env, onFacingWheel, env.floorCanvas, "floor", evt); }, { passive: false });
    env.elevCanvas.addEventListener("wheel", function (evt) { enter(env, onFacingWheel, env.elevCanvas, "elev", evt); }, { passive: false });
    env.floorCanvas.addEventListener("dblclick", function (evt) { enter(env, onFacingDbl, env.floorCanvas, "floor", evt); });
    env.elevCanvas.addEventListener("dblclick", function (evt) { enter(env, onFacingDbl, env.elevCanvas, "elev", evt); });
    env.floorCanvas.addEventListener("keydown", bindPass(env, onFacingKey));
    env.elevCanvas.addEventListener("keydown", bindPass(env, onFacingKey));

    env.floorCanvas.addEventListener("pointerup", bindPass(env, endDrag));
    env.elevCanvas.addEventListener("pointerup", bindPass(env, endDrag));
    env.floorCanvas.addEventListener("pointercancel", bindPass(env, endDrag));
    env.elevCanvas.addEventListener("pointercancel", bindPass(env, endDrag));
    window.addEventListener("pointerup", bindPass(env, endDrag));

    return { redraw: bindPass(env, redraw), setTool: bindPass(env, setTool), view3d: env.view3d };
  }
  function setTool(t) { var env = envStack[envStack.length - 1];
      /* No-op kept for API compat; chips removed — optionally remember kind */
      if (t === "source" || t === "mic") env.lastDragged = t;
    }
  function floorLayout(geo) { var env = envStack[envStack.length - 1];
      const W = geo.state.W, L = geo.state.L, pad = 52;
      const held = env.drag && env.drag.kind === "wall" && env.drag.ctx && env.drag.ctx.lay;
      if (held) {
        const l = env.drag.ctx.lay;
        const ox = env.drag.view ? env.drag.view.ox : l.ox;
        const oy = env.drag.view ? env.drag.view.oy : l.oy;
        return {
          W: W, L: L, scale: l.scale,
          ox: ox, oy: oy,
          rw: W * l.scale, rh: L * l.scale,
        };
      }
      const cw = env.floorCanvas.width, ch = env.floorCanvas.height;
      const scale = Math.min((cw - pad * 2) / W, (ch - pad * 2) / L);
      const rw = W * scale, rh = L * scale;
      return {
        W: W, L: L, scale: scale,
        ox: (cw - rw) / 2, oy: (ch - rh) / 2 + 4,
        rw: rw, rh: rh,
      };
    }
  function elevLayout(geo) { var env = envStack[envStack.length - 1];
      const L = geo.state.L, H = geo.state.H, padX = 52, padY = 28;
      const held = env.drag && env.drag.kind === "ceiling" && env.drag.ctx && env.drag.ctx.lay;
      if (held) {
        const l = env.drag.ctx.lay;
        const oy = env.drag.view ? env.drag.view.oy : l.oy;
        return {
          L: L, H: H, scale: l.scale,
          ox: l.ox, oy: oy,
          rw: L * l.scale, rh: H * l.scale,
        };
      }
      const cw = env.elevCanvas.width, ch = env.elevCanvas.height;
      const scale = Math.min((cw - padX * 2) / L, (ch - padY * 2) / H);
      const rw = L * scale, rh = H * scale;
      return {
        L: L, H: H, scale: scale,
        ox: (cw - rw) / 2, oy: (ch - rh) / 2,
        rw: rw, rh: rh,
      };
    }
  function viewForPatch(lay, s0, patch) { var env = envStack[envStack.length - 1];
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
  function toPx(x, z, lay) { var env = envStack[envStack.length - 1];
      /* Ceiling view: +X right, +Z up the page (Front at top). Mic near Back/bottom. */
      return { px: lay.ox + x * lay.scale, py: lay.oy + (lay.L - z) * lay.scale };
    }
  function toM(px, py, lay) { var env = envStack[envStack.length - 1];
      return { x: (px - lay.ox) / lay.scale, z: lay.L - (py - lay.oy) / lay.scale };
    }
  function floorOutlinePx(st, lay) { var env = envStack[envStack.length - 1];
      if (global.RoomShape) return RoomShape.floorPx(st.room_shape, st.W, st.L, lay);
      return [
        { px: lay.ox, py: lay.oy + lay.rh },
        { px: lay.ox + lay.rw, py: lay.oy + lay.rh },
        { px: lay.ox + lay.rw, py: lay.oy },
        { px: lay.ox, py: lay.oy }
      ];
    }
  function elevOutlinePx(st, lay) { var env = envStack[envStack.length - 1];
      if (global.RoomShape) return RoomShape.elevPx(st.room_shape, st.H, st.L, lay);
      return [
        { px: lay.ox, py: lay.oy + lay.rh },
        { px: lay.ox + lay.rw, py: lay.oy + lay.rh },
        { px: lay.ox + lay.rw, py: lay.oy },
        { px: lay.ox, py: lay.oy }
      ];
    }
  function traceClosed(ctx, pts) { var env = envStack[envStack.length - 1];
      ctx.beginPath();
      var i;
      for (i = 0; i < pts.length; i++) {
        if (i === 0) ctx.moveTo(pts[i].px, pts[i].py);
        else ctx.lineTo(pts[i].px, pts[i].py);
      }
      ctx.closePath();
    }
  function strokeGuides(ctx, segs) { var env = envStack[envStack.length - 1];
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
  function polyOn(st) { var env = envStack[envStack.length - 1];
      return !!(global.RoomShape && RoomShape.normalize(st && st.room_shape) !== "box");
    }
  function clampRoomSpotPatch(st, cap, patch) { var env = envStack[envStack.length - 1];
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
  function ePx(z, y, lay) { var env = envStack[envStack.length - 1];
      return { px: lay.ox + z * lay.scale, py: lay.oy + (lay.H - y) * lay.scale };
    }
  function eM(px, py, lay) { var env = envStack[envStack.length - 1];
      return { z: (px - lay.ox) / lay.scale, y: lay.H - (py - lay.oy) / lay.scale };
    }
  function canvasPos(canvas, evt) { var env = envStack[envStack.length - 1];
      const r = canvas.getBoundingClientRect();
      return {
        x: (evt.clientX - r.left) * (canvas.width / r.width),
        y: (evt.clientY - r.top) * (canvas.height / r.height),
      };
    }
  function drawHandle(ctx, px, py, color, label, active, hovered) { var env = envStack[envStack.length - 1];
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
  function drawArrow(ctx, x, y, dx, dz, lenM, color, scale) { var env = envStack[envStack.length - 1];
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
  function roomOn(st, cap) { var env = envStack[envStack.length - 1];
      if (!st) return false;
      if (st["place_" + cap] === "room") return true;
      return cap === "c" && st.third_mic === "room";
    }
  function roomSpotOf(st, cap) { var env = envStack[envStack.length - 1];
      if (global.RRDrag && global.RRDrag.roomSpot) return global.RRDrag.roomSpot(st, cap);
      function pick(k) {
        var v = st["room_" + cap + "_" + k];
        if (v == null || v === "" || !isFinite(Number(v))) v = st["room_" + k];
        var n = Number(v);
        return isFinite(n) ? n : 0;
      }
      return { x: pick("x"), y: pick("y"), z: pick("z"), yaw: pick("yaw") };
    }
  function roomList(st) { var env = envStack[envStack.length - 1];
      var out = [];
      ROOM_DRAW.forEach(function (cap) {
        if (enter(env, roomOn, st, cap)) out.push(cap);
      });
      return out;
    }
  function hexRgba(hex, a) { var env = envStack[envStack.length - 1];
      var r = parseInt(hex.slice(1, 3), 16);
      var g = parseInt(hex.slice(3, 5), 16);
      var b = parseInt(hex.slice(5, 7), 16);
      return "rgba(" + r + "," + g + "," + b + "," + a + ")";
    }
  function aimFloorPx(dot, yawDeg) { var env = envStack[envStack.length - 1];
      var yaw = ((Number(yawDeg) || 0) * Math.PI) / 180;
      return {
        px: dot.px + ROOM_AIM_PX * Math.sin(yaw),
        py: dot.py - ROOM_AIM_PX * Math.cos(yaw)
      };
    }
  function drawRoomPattern(ctx, px, py, yawDeg, family, polar, color, pattern) { var env = envStack[envStack.length - 1];
      var yaw = ((Number(yawDeg) || 0) * Math.PI) / 180;
      var R = 20;
      var n = 48;
      var i, th, g, sx, sy;
      ctx.beginPath();
      for (i = 0; i <= n; i++) {
        th = (i / n) * Math.PI * 2;
        g = Math.abs(global.RRPattern.polarGain(th - yaw, family, polar, pattern));
        var rad = global.RRDb.polarLinRadius(g, R);
        sx = px + rad * Math.sin(th);
        sy = py - rad * Math.cos(th);
        if (i === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      }
      ctx.closePath();
      ctx.fillStyle = hexRgba(color, 0.22);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();
      global.RRDb.POLAR_DB_RINGS.forEach(function (mark) {
        var ringR = global.RRDb.polarRadius(mark, R);
        if (!(ringR > 1)) return;
        ctx.beginPath();
        ctx.arc(px, py, ringR, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255,255,255,0.28)";
        ctx.lineWidth = 1;
        ctx.stroke();
      });
    }
  function drawAimDot(ctx, px, py, color, active, hovered) { var env = envStack[envStack.length - 1];
      ctx.beginPath();
      ctx.arc(px, py, active || hovered ? 6.5 : 5, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "#0a0b0e";
      ctx.stroke();
    }
  function drawRoomMicsFloor(ctx, geo) { var env = envStack[envStack.length - 1];
      var caps = roomList(geo.state);
      if (!caps.length) return;
      caps.forEach(function (cap) {
        var spot = enter(env, roomSpotOf, geo.state, cap);
        var color = ROOM_COLORS[cap];
        var p = enter(env, toPx, spot.x, spot.z, env.fl);
        var src = enter(env, toPx, geo.source.x, geo.source.z, env.fl);
        ctx.strokeStyle = enter(env, hexRgba, color, 0.35);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(p.px, p.py);
        ctx.lineTo(src.px, src.py);
        ctx.stroke();
        enter(env, drawRoomPattern, 
          ctx, p.px, p.py, spot.yaw,
          geo.state["family_" + cap] || "cardioid",
          geo.state["polar_" + cap],
          color,
          geo.state["pattern_" + cap]
        );
        var bodyOn = !!(env.drag && env.drag.kind === "room" && env.drag.canvas === "floor" && env.drag.roomCap === cap && env.drag.roomPart === "body");
        enter(env, drawHandle, ctx, p.px, p.py, color, cap === "c" ? "Room mic" : cap.toUpperCase(), bodyOn, env.hover === "room:" + cap);
        var aim = enter(env, aimFloorPx, p, spot.yaw);
        var aimOn = !!(env.drag && env.drag.kind === "room" && env.drag.canvas === "floor" && env.drag.roomCap === cap && env.drag.roomPart === "aim");
        enter(env, drawAimDot, ctx, aim.px, aim.py, color, aimOn, env.hover === "roomAim:" + cap);
      });
    }
  function drawRoomMicsElev(ctx, geo) { var env = envStack[envStack.length - 1];
      var caps = roomList(geo.state);
      if (!caps.length) return;
      caps.forEach(function (cap) {
        var spot = enter(env, roomSpotOf, geo.state, cap);
        var color = ROOM_COLORS[cap];
        var p = enter(env, ePx, spot.z, spot.y, env.el);
        var src = enter(env, ePx, geo.source.z, geo.source.y, env.el);
        ctx.strokeStyle = enter(env, hexRgba, color, 0.35);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(p.px, p.py);
        ctx.lineTo(src.px, src.py);
        ctx.stroke();
        var on = !!(env.drag && env.drag.kind === "room" && env.drag.canvas === "elev" && env.drag.roomCap === cap);
        enter(env, drawHandle, ctx, p.px, p.py, color, cap === "c" ? "Room mic" : cap.toUpperCase(), on, env.hover === "roomH:" + cap);
      });
    }
  function roomHitsFloor(px, py, geo) { var env = envStack[envStack.length - 1];
      var hits = [];
      roomList(geo.state).forEach(function (cap) {
        var spot = enter(env, roomSpotOf, geo.state, cap);
        var p = enter(env, toPx, spot.x, spot.z, env.fl);
        var aim = enter(env, aimFloorPx, p, spot.yaw);
        if (Math.hypot(px - aim.px, py - aim.py) <= ROOM_AIM_HIT) hits.push({ cap: cap, part: "aim" });
        else if (Math.hypot(px - p.px, py - p.py) <= HIT) hits.push({ cap: cap, part: "body" });
      });
      return hits;
    }
  function roomHitsElev(px, py, geo) { var env = envStack[envStack.length - 1];
      var hits = [];
      roomList(geo.state).forEach(function (cap) {
        var spot = enter(env, roomSpotOf, geo.state, cap);
        var p = enter(env, ePx, spot.z, spot.y, env.el);
        if (Math.hypot(px - p.px, py - p.py) <= HIT) hits.push({ cap: cap, part: "body" });
      });
      return hits;
    }
  function pickRoomHit(hits) { var env = envStack[envStack.length - 1];
      if (!hits.length || !global.RRDrag || !global.RRDrag.pickRoomMic) return null;
      var dragging = env.drag && env.drag.kind === "room" ? env.drag.roomCap : null;
      var cap = global.RRDrag.pickRoomMic(ROOM_DRAW, hits.map(function (h) { return h.cap; }), dragging);
      if (!cap) return null;
      var i;
      for (i = hits.length - 1; i >= 0; i--) {
        if (hits[i].cap === cap) return hits[i];
      }
      return null;
    }
  function poseOf(st, which) { var env = envStack[envStack.length - 1];
      if (which === "b" && RoomMath.effectiveBPose) return RoomMath.effectiveBPose(st);
      return {
        preset: String(st.source_radiation || "omni"),
        yaw: Number(st.source_yaw) || 0,
        pitch: Number(st.source_pitch) || 0
      };
    }
  function yawOf(st, which) { var env = envStack[envStack.length - 1];
      return poseOf(st, which).yaw;
    }
  function pitchOf(st, which) { var env = envStack[envStack.length - 1];
      return poseOf(st, which).pitch;
    }
  function presetId(st, which) { var env = envStack[envStack.length - 1];
      return poseOf(st, which).preset;
    }
  function isOmniSrc(st, which) { var env = envStack[envStack.length - 1];
      return presetId(st, which).toLowerCase() === "omni";
    }
  function wrapDeg(d) { var env = envStack[envStack.length - 1];
      let x = Number(d) || 0;
      x = ((x + 540) % 360) - 180;
      return x;
    }
  function setYawPitch(st, which, yaw, pitch) { var env = envStack[envStack.length - 1];
      if (which === "b") {
        if (yaw != null) st.source_yaw_b = wrapDeg(yaw);
        if (pitch != null) st.source_pitch_b = Math.max(-89, Math.min(89, pitch));
      } else {
        if (yaw != null) st.source_yaw = wrapDeg(yaw);
        if (pitch != null) st.source_pitch = Math.max(-89, Math.min(89, pitch));
      }
    }
  function faceMicState(st, which) { var env = envStack[envStack.length - 1];
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
  function metaFor(which) { var env = envStack[envStack.length - 1];
      try { return env.sourceMeta(which) || null; } catch (e) { return null; }
    }
  function sizeMetres(st, which) { var env = envStack[envStack.length - 1];
      const raw = st.source_size_m;
      if (raw != null && raw !== "" && isFinite(Number(raw)) && Number(raw) > 0) return Number(raw);
      const meta = metaFor(which);
      if (meta && Number(meta.a_eq_m) > 0) return Number(meta.a_eq_m);
      return 0;
    }
  function ringFloor(dot, yawDeg) { var env = envStack[envStack.length - 1];
      const yaw = yawDeg * Math.PI / 180;
      return { px: dot.px + Math.sin(yaw) * env.RING_PX, py: dot.py - Math.cos(yaw) * env.RING_PX };
    }
  function ringElev(dot, pitchDeg) { var env = envStack[envStack.length - 1];
      const p = pitchDeg * Math.PI / 180;
      return { px: dot.px + Math.cos(p) * env.RING_PX, py: dot.py - Math.sin(p) * env.RING_PX };
    }
  function drawLobe(ctx, dot, yawDeg, curve, angles) { var env = envStack[envStack.length - 1];
      if (!curve || !curve.length) return;
      ctx.beginPath();
      for (let i = 0; i < curve.length; i++) {
        const azDeg = angles && angles.length === curve.length ? angles[i] : (-180 + i * 5);
        const az = azDeg * Math.PI / 180;
        const yaw = yawDeg * Math.PI / 180;
        const db = Number(curve[i]);
        const rad = global.RRDb.polarRadius(db, 70);
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
      global.RRDb.POLAR_DB_RINGS.forEach(function (mark) {
        var ringR = global.RRDb.polarRadius(mark, 70);
        var label = (mark === 0 ? "0" : String(mark));
        if (ringR > 1) {
          ctx.beginPath();
          ctx.arc(dot.px, dot.py, ringR, 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(255,255,255,0.18)";
          ctx.lineWidth = 1;
          ctx.stroke();
        }
        ctx.fillStyle = "rgba(180,184,196,0.9)";
        ctx.font = "9px Segoe UI, system-ui, sans-serif";
        ctx.textAlign = "left";
        ctx.textBaseline = ringR > 1 ? "bottom" : "middle";
        ctx.fillText(label, dot.px + 3, dot.py - ringR);
      });
    }
  function drawSizeCircle(ctx, dot, metres, scale) { var env = envStack[envStack.length - 1];
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
  function drawHollow(ctx, x, y, color, active) { var env = envStack[envStack.length - 1];
      ctx.beginPath();
      ctx.arc(x, y, active ? 8 : 6.5, 0, Math.PI * 2);
      ctx.strokeStyle = color;
      ctx.lineWidth = active ? 2.5 : 2;
      ctx.stroke();
    }
  function drawSourceUnder(ctx, geo, plane) { var env = envStack[envStack.length - 1];
      const st = geo.state;
      const items = [{ which: "a", src: geo.source }];
      if (geo.source_b) items.push({ which: "b", src: geo.source_b });
      items.forEach(function (it) {
        if (plane === "floor" && it.which === "b" && enter(env, stackedFloor, geo)) return;
        if (plane === "elev" && it.which === "b" && enter(env, stackedElev, geo)) return;
        const dot = plane === "floor"
          ? enter(env, toPx, it.src.x, it.src.z, env.fl)
          : enter(env, ePx, it.src.z, it.src.y, env.el);
        if (enter(env, isOmniSrc, st, it.which)) {
          if (plane !== "floor") return;
          ctx.beginPath();
          ctx.arc(dot.px, dot.py, 36, 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(255,179,71,0.4)";
          ctx.lineWidth = 1.25;
          ctx.stroke();
          return;
        }
        const meta = enter(env, metaFor, it.which);
        const scale = plane === "floor" ? env.fl.scale : env.el.scale;
        enter(env, drawSizeCircle, ctx, dot, enter(env, sizeMetres, st, it.which), scale);
        if (plane === "floor" && meta && meta.horizontal) {
          enter(env, drawLobe, ctx, dot, enter(env, yawOf, st, it.which), meta.horizontal["2000"] || meta.horizontal[2000], meta.angles);
        }
      });
    }
  function drawSourceRings(ctx, geo, plane) { var env = envStack[envStack.length - 1];
      const st = geo.state;
      const items = [{ which: "a", src: geo.source, color: COLORS.src }];
      if (geo.source_b) items.push({ which: "b", src: geo.source_b, color: COLORS.srcB });
      items.forEach(function (it) {
        if (enter(env, isOmniSrc, st, it.which)) return;
        if (plane === "floor" && it.which === "b" && enter(env, stackedFloor, geo)) return;
        if (plane === "elev" && it.which === "b" && enter(env, stackedElev, geo)) return;
        const dot = plane === "floor"
          ? enter(env, toPx, it.src.x, it.src.z, env.fl)
          : enter(env, ePx, it.src.z, it.src.y, env.el);
        const ring = plane === "floor"
          ? enter(env, ringFloor, dot, enter(env, yawOf, st, it.which))
          : enter(env, ringElev, dot, enter(env, pitchOf, st, it.which));
        const kind = plane === "floor"
          ? (it.which === "b" ? "srcBYaw" : "srcYaw")
          : (it.which === "b" ? "srcBPitch" : "srcPitch");
        const active = !!(env.drag && env.drag.kind === kind);
        ctx.beginPath();
        ctx.moveTo(dot.px, dot.py);
        ctx.lineTo(ring.px, ring.py);
        ctx.strokeStyle = it.color;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        enter(env, drawHollow, ctx, ring.px, ring.py, it.color, active || env.hover === kind);
        if (active || env.hover === kind) {
          const off = enter(env, offMicDeg, st, it.which);
          const label = (plane === "floor" ? "yaw " : "pitch ") +
            (plane === "floor" ? Math.round(enter(env, yawOf, st, it.which)) : Math.round(enter(env, pitchOf, st, it.which))) +
            "° · " + (off >= 0 ? "+" : "") + Math.round(off) + "° off mic";
          ctx.font = "600 11px Segoe UI, system-ui, sans-serif";
          ctx.fillStyle = "#e8eaef";
          ctx.textAlign = "left";
          ctx.fillText(label, ring.px + 12, ring.py - 8);
        }
      });
    }
  function offMicDeg(st, which) { var env = envStack[envStack.length - 1];
      const geo = RoomMath.compute(st);
      const src = which === "b" && geo.source_b ? geo.source_b : geo.source;
      const mic = geo.mic_centre;
      const dx = mic.x - src.x;
      const dz = mic.z - src.z;
      const face = Math.atan2(dx, dz) * 180 / Math.PI;
      return ((yawOf(st, which) - face + 540) % 360) - 180;
    }
  function nearestSrc(px, py, geo, plane) { var env = envStack[envStack.length - 1];
      const st = geo.state;
      let best = null;
      let bestD = 1e9;
      function consider(which, src) {
        if (!src || isOmniSrc(st, which)) return;
        if (plane === "floor" && which === "b" && stackedFloor(geo)) return;
        if (plane === "elev" && which === "b" && stackedElev(geo)) return;
        const dot = plane === "floor" ? toPx(src.x, src.z, env.fl) : ePx(src.z, src.y, env.el);
        const d = Math.hypot(px - dot.px, py - dot.py);
        if (d < bestD) { bestD = d; best = { which: which, dot: dot, d: d }; }
      }
      consider("a", geo.source);
      consider("b", geo.source_b);
      return best;
    }
  function hitRing(px, py, geo, plane) { var env = envStack[envStack.length - 1];
      const st = geo.state;
      let found = null;
      let best = env.RING_HIT;
      function consider(which, src) {
        if (!src || isOmniSrc(st, which)) return;
        if (plane === "floor" && which === "b" && stackedFloor(geo)) return;
        if (plane === "elev" && which === "b" && stackedElev(geo)) return;
        const dot = plane === "floor" ? toPx(src.x, src.z, env.fl) : ePx(src.z, src.y, env.el);
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
  function angBetween(ax, az, bx, bz) { var env = envStack[envStack.length - 1];
      var na = Math.hypot(ax, az);
      var nb = Math.hypot(bx, bz);
      if (na < 1e-9 || nb < 1e-9) return 0;
      var c = (ax * bx + az * bz) / (na * nb);
      if (c > 1) c = 1;
      if (c < -1) c = -1;
      return Math.acos(c);
    }
  function srcDbToward(st, which, from, to) { var env = envStack[envStack.length - 1];
      if (enter(env, isOmniSrc, st, which)) return 0;
      if (!global.RoomDraw || !RoomDraw.curveDb) return 0;
      var meta = enter(env, metaFor, which);
      if (!meta || !meta.horizontal) return 0;
      var curve = meta.horizontal["1000"] || meta.horizontal[1000];
      if (!curve) return 0;
      var az = Math.atan2(to.x - from.x, to.z - from.z) * 180 / Math.PI;
      var rel = ((az - enter(env, yawOf, st, which) + 540) % 360) - 180;
      return RoomDraw.curveDb(curve, meta.angles, rel);
    }
  function micPolarGain(st, cap, theta) { var env = envStack[envStack.length - 1];
      if (!global.RRPattern) return 1;
      return RRPattern.polarGain(theta, st["family_" + cap], st["polar_" + cap], st["pattern_" + cap]);
    }
  function faceImages(src, room) { var env = envStack[envStack.length - 1];
      if (!global.RRImage) return [];
      var axes = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
      return axes.map(function (n) { return RRImage.imagePoint(src, room, n); });
    }
  function boundaryHit(mic, image, room) { var env = envStack[envStack.length - 1];
      var dx = image.x - mic.x;
      var dy = image.y - mic.y;
      var dz = image.z - mic.z;
      var best = 1;
      function consider(t) {
        if (t > 1e-4 && t < best) best = t;
      }
      if (Math.abs(dx) > 1e-9) {
        consider((0 - mic.x) / dx);
        consider((room.W - mic.x) / dx);
      }
      if (Math.abs(dy) > 1e-9) {
        consider((0 - mic.y) / dy);
        consider((room.H - mic.y) / dy);
      }
      if (Math.abs(dz) > 1e-9) {
        consider((0 - mic.z) / dz);
        consider((room.L - mic.z) / dz);
      }
      return { x: mic.x + dx * best, y: mic.y + dy * best, z: mic.z + dz * best };
    }
  function drawHeat(ctx, geo) { var env = envStack[envStack.length - 1];
      var frame = env.floorCanvas.closest ? env.floorCanvas.closest(".diagram-frame") : null;
      var noteEl = (frame && frame.querySelector) ? frame.querySelector("#floorHeatNote") : null;
      var enlarged = !!(frame && frame.classList.contains("is-enlarged"));
      var st = geo.state || {};
      if (!enlarged) {
        if (noteEl) noteEl.hidden = true;
        return;
      }
      var note = (global.RoomShape && RoomShape.heatMapNote) ? RoomShape.heatMapNote(st.room_shape) : null;
      if (!note || !global.RoomDraw || !RoomDraw.reverbDistance || !RoomDraw.drrDb) {
        if (noteEl) {
          noteEl.hidden = false;
          noteEl.textContent = "Shoebox image map hidden. This outline is not a shoebox.";
        }
        return;
      }
      if (noteEl) {
        noteEl.hidden = false;
        noteEl.textContent = note;
      }
      var src = geo.source;
      var room = { W: st.W, H: st.H, L: st.L };
      var images = enter(env, faceImages, src, room);
      if (!images.length) return;
      var cols = 12;
      var rows = 8;
      var ix, iz;
      for (ix = 0; ix < cols; ix++) {
        for (iz = 0; iz < rows; iz++) {
          var x = (ix + 0.5) * st.W / cols;
          var z = (iz + 0.5) * st.L / rows;
          var y = geo.mic_centre.y;
          var direct = Math.hypot(x - src.x, y - src.y, z - src.z);
          var dists = images.map(function (im) {
            return Math.hypot(x - im.x, y - im.y, z - im.z);
          });
          var rev = RoomDraw.reverbDistance(dists);
          var drr = RoomDraw.drrDb(direct, rev);
          if (drr == null) continue;
          var t = (drr + 12) / 24;
          if (t < 0) t = 0;
          if (t > 1) t = 1;
          var p0 = enter(env, toPx, ix * st.W / cols, iz * st.L / rows, env.fl);
          var p1 = enter(env, toPx, (ix + 1) * st.W / cols, (iz + 1) * st.L / rows, env.fl);
          ctx.fillStyle = "rgba(251,146,60," + (0.04 + 0.28 * t).toFixed(3) + ")";
          ctx.fillRect(Math.min(p0.px, p1.px), Math.min(p0.py, p1.py), Math.abs(p1.px - p0.px) + 1, Math.abs(p1.py - p0.py) + 1);
        }
      }
      ctx.save();
      ctx.font = "12px sans-serif";
      ctx.fillStyle = "rgba(226,232,240,0.92)";
      ctx.fillText(note, 12, Math.max(16, env.floorCanvas.height - 16));
      ctx.restore();
    }
  function drawMicRings(ctx, geo, spots) { var env = envStack[envStack.length - 1];
      if (!global.RoomDraw || !RoomDraw.linFromDb) return;
      var st = geo.state;
      var fallOf = global.RRDistance ? RRDistance.geometricLevel : function (d) { return d > 1e-9 ? 1 / d : 0; };
      spots.forEach(function (spot) {
        var srcDb = enter(env, srcDbToward, st, "a", geo.source, spot.mic);
        var dist = Math.hypot(spot.mic.x - geo.source.x, spot.mic.y - geo.source.y, spot.mic.z - geo.source.z);
        var scale = RoomDraw.linFromDb(srcDb) * fallOf(dist);
        var n = 28;
        var i;
        for (i = 0; i < n; i++) {
          var phi = -Math.PI + (i + 0.5) * 2 * Math.PI / n;
          var theta = enter(env, angBetween, spot.look.x, spot.look.z, Math.sin(phi), Math.cos(phi));
          var micG = Math.abs(enter(env, micPolarGain, st, spot.cap, theta));
          var g = scale * micG * 1.4;
          if (g < 0) g = 0;
          if (g > 1) g = 1;
          var a0 = -Math.PI / 2 + i * 2 * Math.PI / n;
          var a1 = a0 + 2 * Math.PI / n;
          ctx.beginPath();
          ctx.moveTo(spot.p.px, spot.p.py);
          ctx.arc(spot.p.px, spot.p.py, 20, a0, a1);
          ctx.closePath();
          ctx.fillStyle = "rgba(96,165,250," + (0.06 + 0.5 * g).toFixed(3) + ")";
          ctx.fill();
        }
      });
    }
  function drawReflectDots(ctx, geo, spots) { var env = envStack[envStack.length - 1];
      if (!global.RoomDraw || !RoomDraw.arrivalGain) return;
      var st = geo.state;
      var room = { W: st.W, H: st.H, L: st.L };
      var images = enter(env, faceImages, geo.source, room);
      images.forEach(function (im) {
        var hit = enter(env, boundaryHit, geo.mic_centre, im, room);
        var p = enter(env, toPx, hit.x, hit.z, env.fl);
        var srcDb = enter(env, srcDbToward, st, "a", geo.source, im);
        var look = geo.look_c || { x: 0, z: 1 };
        var theta = enter(env, angBetween, look.x, look.z, im.x - geo.mic_centre.x, im.z - geo.mic_centre.z);
        var gain = RoomDraw.arrivalGain(srcDb, enter(env, micPolarGain, st, "c", theta));
        var mag = Math.abs(gain);
        if (mag > 1) mag = 1;
        ctx.beginPath();
        ctx.arc(p.px, p.py, 4.5, 0, Math.PI * 2);
        ctx.fillStyle = gain < 0
          ? ("rgba(96,165,250," + (0.35 + 0.6 * mag).toFixed(3) + ")")
          : ("rgba(251,191,36," + (0.35 + 0.6 * mag).toFixed(3) + ")");
        ctx.fill();
      });
    }
  function drawSourceBadge(ctx, geo, px, py) { var env = envStack[envStack.length - 1];
      if (!global.RoomDraw || !RoomDraw.sourceBadge) return;
      var st = geo.state;
      var omni = enter(env, isOmniSrc, st, "a");
      var off = enter(env, offMicDeg, st, "a");
      var db = enter(env, srcDbToward, st, "a", geo.source, geo.mic_centre);
      var kind = RoomDraw.sourceBadge(off, db, omni);
      if (!kind) return;
      ctx.font = "700 11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.textBaseline = "alphabetic";
      ctx.fillStyle = kind === "null" ? "#fb7185" : "#fbbf24";
      ctx.fillText(kind === "null" ? "Null" : "Off-axis", px + 12, py - 14);
    }
  function drawPlanPoints(ctx, geo) { var env = envStack[envStack.length - 1];
      var sel;
      if (!global.RoomShape || RoomShape.normalize(geo.state.room_shape) !== "plan") return;
      var pts = RoomShape.floorPx(geo.state.room_shape, geo.state.W, geo.state.L, env.fl);
      sel = RoomShape.planSelection ? RoomShape.planSelection() : -1;
      pts.forEach(function (p, i) {
        var on = i === sel;
        ctx.fillStyle = on ? "#f5c16c" : "#e7e1d4";
        ctx.beginPath();
        ctx.arc(p.px, p.py, on ? 8 : 5, 0, Math.PI * 2);
        ctx.fill();
      });
    }
  function drawFloor(geo) { var env = envStack[envStack.length - 1];
      const ctx = env.fctx;
      const cw = env.floorCanvas.width, ch = env.floorCanvas.height;
      env.fl = floorLayout(geo);
      ctx.clearRect(0, 0, cw, ch);
      ctx.fillStyle = "#0a0b0e";
      ctx.fillRect(0, 0, cw, ch);
      const outline = floorOutlinePx(geo.state, env.fl);
      ctx.fillStyle = "#12141a";
      ctx.strokeStyle = "#3a4155";
      ctx.lineWidth = 2;
      traceClosed(ctx, outline);
      ctx.fill();
      ctx.stroke();
      enter(env, drawPlanPoints, ctx, geo);

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
        a = toPx(x, 0, env.fl);
        b = toPx(x, geo.state.L, env.fl);
        ctx.beginPath();
        ctx.moveTo(a.px, a.py);
        ctx.lineTo(b.px, b.py);
        ctx.stroke();
      }
      for (z = 0; z <= geo.state.L + 1e-9; z += step) {
        a = toPx(0, z, env.fl);
        b = toPx(geo.state.W, z, env.fl);
        ctx.beginPath();
        ctx.moveTo(a.px, a.py);
        ctx.lineTo(b.px, b.py);
        ctx.stroke();
      }
      enter(env, drawHeat, ctx, geo);
      if (clipSplay) ctx.restore();

      if (global.RoomShape && RoomShape.planGuidesPx) {
        strokeGuides(ctx, RoomShape.planGuidesPx(geo.state.room_shape, geo.state.W, geo.state.L, env.fl));
      }

      const Sp = toPx(geo.source.x, geo.source.z, env.fl);
      const Cp = toPx(geo.mic_centre.x, geo.mic_centre.z, env.fl);
      const Lp = toPx(geo.mic_left.x, geo.mic_left.z, env.fl);
      const Rp = toPx(geo.mic_right.x, geo.mic_right.z, env.fl);
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
      if (!lRoom) drawArrow(ctx, Lp.px, Lp.py, geo.look_l.x, geo.look_l.z, al, COLORS.L, env.fl.scale);
      if (!rRoom) drawArrow(ctx, Rp.px, Rp.py, geo.look_r.x, geo.look_r.z, al, COLORS.R, env.fl.scale);
      if (geo.state.mic_setup === "binaural" && !cRoom) {
        drawArrow(ctx, Cp.px, Cp.py, geo.look_c.x, geo.look_c.z, al * 0.55, COLORS.mic, env.fl.scale);
      }

      drawSourceUnder(ctx, geo, "floor");
      var ringSpots = [
        { p: Lp, mic: geo.mic_left, look: geo.look_l, cap: "l" },
        { p: Cp, mic: geo.mic_centre, look: geo.look_c, cap: "c" },
        { p: Rp, mic: geo.mic_right, look: geo.look_r, cap: "r" }
      ];
      enter(env, drawReflectDots, ctx, geo, ringSpots);
      enter(env, drawMicRings, ctx, geo, ringSpots);
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
      drawHandle(ctx, Cp.px, Cp.py, COLORS.mic, "Mic", !!(env.drag && env.drag.kind === "mic"), env.hover === "mic");
      const two = !!geo.source_b;
      drawHandle(ctx, Sp.px, Sp.py, COLORS.src, two ? "A" : "Src", !!(env.drag && env.drag.kind === "source"), env.hover === "source");
      enter(env, drawSourceBadge, ctx, geo, Sp.px, Sp.py);
      if (two && !stackedFloor(geo)) {
        const Bp = toPx(geo.source_b.x, geo.source_b.z, env.fl);
        drawHandle(ctx, Bp.px, Bp.py, COLORS.srcB, "B", !!(env.drag && env.drag.kind === "sourceB"), env.hover === "sourceB");
      }
      drawSourceRings(ctx, geo, "floor");
      drawRoomMicsFloor(ctx, geo);

      ctx.fillStyle = "#8b92a5";
      ctx.font = "600 11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Front (+Z)", env.fl.ox + env.fl.rw / 2, Math.max(14, env.fl.oy - 10));
      ctx.fillText("Back", env.fl.ox + env.fl.rw / 2, env.fl.oy + env.fl.rh + 16);
      ctx.fillText("Width X →", env.fl.ox + env.fl.rw / 2, env.fl.oy + env.fl.rh + 30);
      ctx.textBaseline = "middle";
      ctx.textAlign = "right";
      ctx.fillText("Left", env.fl.ox - 8, env.fl.oy + env.fl.rh / 2);
      ctx.textAlign = "left";
      ctx.fillText("Right", env.fl.ox + env.fl.rw + 10, env.fl.oy + env.fl.rh / 2);
      ctx.textBaseline = "alphabetic";
      ctx.save();
      ctx.translate(env.fl.ox - 42, env.fl.oy + env.fl.rh / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = "center";
      ctx.fillText("Length +Z →", 0, 0);
      ctx.restore();
      ctx.textAlign = "left";
      ctx.fillStyle = "#5c6478";
      ctx.font = "12px Segoe UI, system-ui, sans-serif";
      ctx.fillText(geo.state.W.toFixed(1) + " × " + geo.state.L.toFixed(1) + " m", 14, 22);
      enter(env, drawFaceLabels, ctx, geo);
    }
  function drawFaceLabels(ctx, geo) { var env = envStack[envStack.length - 1];
      if (!global.RoomShape || RoomShape.normalize(geo.state.room_shape) === "box") return;
      var outline = floorOutlinePx(geo.state, env.fl);
      if (!outline || outline.length < 2) return;
      ctx.save();
      ctx.fillStyle = "#c4b5fd";
      ctx.font = "600 12px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      var i;
      var n = outline.length;
      for (i = 0; i < n; i++) {
        var a = outline[i];
        var b = outline[(i + 1) % n];
        ctx.fillText("F" + (i + 1), (a.px + b.px) / 2, (a.py + b.py) / 2);
      }
      var cx = 0;
      var cy = 0;
      for (i = 0; i < n; i++) {
        cx += outline[i].px;
        cy += outline[i].py;
      }
      ctx.fillText("F" + (n + 1), cx / n, cy / n);
      ctx.restore();
    }
  function drawElev(geo) { var env = envStack[envStack.length - 1];
      const ctx = env.ectx;
      const cw = env.elevCanvas.width, ch = env.elevCanvas.height;
      env.el = elevLayout(geo);
      ctx.clearRect(0, 0, cw, ch);
      ctx.fillStyle = "#0a0b0e";
      ctx.fillRect(0, 0, cw, ch);
      ctx.fillStyle = "#12141a";
      ctx.strokeStyle = "#3a4155";
      ctx.lineWidth = 2;
      traceClosed(ctx, elevOutlinePx(geo.state, env.el));
      ctx.fill();
      ctx.stroke();
      if (global.RoomShape && RoomShape.elevGuidesPx) {
        strokeGuides(ctx, RoomShape.elevGuidesPx(geo.state.room_shape, geo.state.H, geo.state.L, env.el));
      }

      ctx.fillStyle = "#8b92a5";
      ctx.font = "11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      var floorTag = "Floor";
      var ceilTag = "Ceiling";
      if (global.RoomShape && RoomShape.normalize(geo.state.room_shape) !== "box" && RoomShape.wallRows) {
        var faceRows = RoomShape.wallRows(geo.state.room_shape, false, geo.state.W, geo.state.H, geo.state.L);
        var floorRow = null;
        var ceilBits = [];
        var ri;
        for (ri = 0; ri < faceRows.length; ri++) {
          if (faceRows[ri].id === "floor") floorRow = faceRows[ri];
          if (faceRows[ri].id === "ceiling" || faceRows[ri].id === "roofL" || faceRows[ri].id === "roofR") {
            ceilBits.push(faceRows[ri].letters[0]);
          }
        }
        if (floorRow) floorTag = "Floor " + floorRow.letters[0];
        if (ceilBits.length) ceilTag = ceilBits.join(" ");
      }
      ctx.fillText(floorTag, env.el.ox + 6, env.el.oy + env.el.rh - 6);
      ctx.fillText(ceilTag, env.el.ox + 6, env.el.oy + 14);

      const Sp = ePx(geo.source.z, geo.source.y, env.el);
      const Cp = ePx(geo.mic_centre.z, geo.mic_centre.y, env.el);
      const Sf = ePx(geo.source.z, 0, env.el);
      const Fp = ePx(geo.mic_centre.z, 0, env.el);

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
      const srcActive = !!(env.drag && env.drag.kind === "srcHeight");
      const micActive = !!(env.drag && (env.drag.kind === "micHeight" || env.drag.kind === "height"));
      const srcPrimary = env.lastDragged === "source";
      const micPrimary = env.lastDragged === "mic";
      const two = !!geo.source_b;
      drawHandle(ctx, Sp.px, Sp.py, COLORS.src, two ? "A" : "Src H", srcActive || srcPrimary, env.hover === "srcHeight");
      if (two && !stackedElev(geo)) {
        const Bp = ePx(geo.source_b.z, geo.source_b.y, env.el);
        const Bf = ePx(geo.source_b.z, 0, env.el);
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = "rgba(244,63,94,0.4)";
        ctx.beginPath();
        ctx.moveTo(Bf.px, Bf.py);
        ctx.lineTo(Bp.px, Bp.py);
        ctx.stroke();
        ctx.setLineDash([]);
        drawHandle(
          ctx, Bp.px, Bp.py, COLORS.srcB, "B",
          !!(env.drag && env.drag.kind === "srcBHeight"), env.hover === "srcBHeight"
        );
      }
      drawSourceRings(ctx, geo, "elev");
      drawHandle(ctx, Cp.px, Cp.py, COLORS.mic, "Mic H", micActive || micPrimary, env.hover === "micHeight" || env.hover === "height");
      drawRoomMicsElev(ctx, geo);

      ctx.fillStyle = "#5c6478";
      ctx.font = "12px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText("Back", env.el.ox + 6, ch - 8);
      ctx.textAlign = "right";
      ctx.fillText("Front", env.el.ox + env.el.rw - 6, ch - 8);
      ctx.textAlign = "center";
      ctx.fillText("Length Z →", env.el.ox + env.el.rw / 2, ch - 8);
      ctx.textAlign = "left";
      ctx.textBaseline = "alphabetic";
      var heightY = Math.max(14, env.el.oy - 16);
      ctx.fillStyle = COLORS.src;
      ctx.fillText((two ? "A " : "Src ") + geo.state.sy.toFixed(2) + " m", 10, heightY);
      ctx.fillStyle = COLORS.mic;
      ctx.fillText("Mic " + geo.state.my.toFixed(2) + " m", 118, heightY);
      if (two && geo.source_b && !stackedElev(geo)) {
        ctx.fillStyle = COLORS.srcB;
        ctx.fillText("B " + geo.source_b.y.toFixed(2) + " m", 230, heightY);
      }
    }
  function fitSourceBuffer(canvas) { var env = envStack[envStack.length - 1];
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
  function redraw() { var env = envStack[envStack.length - 1];
      fitSourceBuffer(env.floorCanvas);
      fitSourceBuffer(env.elevCanvas);
      const geo = RoomMath.compute(env.getState());
      drawFloor(geo);
      drawElev(geo);
      if (env.view3d) env.view3d.redraw();
      return geo;
    }
  function stackedFloor(geo) { var env = envStack[envStack.length - 1];
      if (!geo.source_b || !geo.state.mirror_b) return false;
      return Math.hypot(geo.source.x - geo.source_b.x, geo.source.z - geo.source_b.z) < 0.03;
    }
  function stackedElev(geo) { var env = envStack[envStack.length - 1];
      if (!geo.source_b || !geo.state.mirror_b) return false;
      return Math.hypot(geo.source.z - geo.source_b.z, geo.source.y - geo.source_b.y) < 0.03;
    }
  function floorDists(px, py, geo) { var env = envStack[envStack.length - 1];
      const Sp = toPx(geo.source.x, geo.source.z, env.fl);
      const Cp = toPx(geo.mic_centre.x, geo.mic_centre.z, env.fl);
      let db = 1e9;
      if (geo.source_b) {
        const Bp = toPx(geo.source_b.x, geo.source_b.z, env.fl);
        db = Math.hypot(px - Bp.px, py - Bp.py);
      }
      return {
        ds: Math.hypot(px - Sp.px, py - Sp.py),
        dc: Math.hypot(px - Cp.px, py - Cp.py),
        db: db,
      };
    }
  function elevDists(px, py, geo) { var env = envStack[envStack.length - 1];
      const Sp = ePx(geo.source.z, geo.source.y, env.el);
      const Cp = ePx(geo.mic_centre.z, geo.mic_centre.y, env.el);
      let db = 1e9;
      if (geo.source_b) {
        const Bp = ePx(geo.source_b.z, geo.source_b.y, env.el);
        db = Math.hypot(px - Bp.px, py - Bp.py);
      }
      return {
        ds: Math.hypot(px - Sp.px, py - Sp.py),
        dc: Math.hypot(px - Cp.px, py - Cp.py),
        db: db,
      };
    }
  function hitFloor(px, py, geo) { var env = envStack[envStack.length - 1];
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
  function pickFloorKind(px, py, geo) { var env = envStack[envStack.length - 1];
      const hit = hitFloor(px, py, geo);
      if (hit) return hit;
      const d = floorDists(px, py, geo);
      let nearest = "source";
      let best = d.ds;
      if (geo.source_b && !stackedFloor(geo) && d.db < best) { nearest = "sourceB"; best = d.db; }
      if (d.dc < best) { nearest = "mic"; best = d.dc; }
      if (best <= FAR) return nearest;
      return env.lastDragged === "sourceB" ? "sourceB" : env.lastDragged;
    }
  function hitElev(px, py, geo) { var env = envStack[envStack.length - 1];
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
  function pickElevKind(px, py, geo) { var env = envStack[envStack.length - 1];
      const hit = hitElev(px, py, geo);
      if (hit) return hit;
      const d = elevDists(px, py, geo);
      let nearest = "srcHeight";
      let best = d.ds;
      if (geo.source_b && !stackedElev(geo) && d.db < best) { nearest = "srcBHeight"; best = d.db; }
      if (d.dc < best) { nearest = "micHeight"; best = d.dc; }
      if (best <= FAR) return nearest;
      if (env.lastDragged === "sourceB") return "srcBHeight";
      return env.lastDragged === "source" ? "srcHeight" : "micHeight";
    }
  function applyLinkedHeight(st, kind, y) { var env = envStack[envStack.length - 1];
      const yy = RoomMath.clamp(y, 0, st.H);
      if (kind === "srcHeight") {
        st.sy = yy;
        if (st.link_heights) st.my = yy;
      } else {
        st.my = yy;
        if (st.link_heights) st.sy = yy;
      }
    }
  function faceLetter(hit) {
      if (!hit || !hit.walls || hit.walls.length !== 1) return "";
      var w = hit.walls[0];
      if (w === "x0") return "A";
      if (w === "x1") return "C";
      if (w === "z1") return "B";
      if (w === "z0") return "D";
      if (w === "y1") return "F";
      return "";
    }
  function hitFloorEdge(px, py, elay) {
      if (!elay || !isFinite(elay.scale)) return false;
      var band = 8;
      var x0 = elay.ox, x1 = elay.ox + elay.L * elay.scale, y = elay.oy + elay.H * elay.scale;
      if (px < x0 - band || px > x1 + band) return false;
      return Math.abs(py - y) <= band;
    }
  function noteFaceMove(drag, x, y) {
      if (!drag || drag.downX == null) return;
      var dx = x - drag.downX, dy = y - drag.downY;
      if (dx * dx + dy * dy > 16) drag.moved = true;
    }
  function selectDiagramFace(letter) {
      if (!letter) return;
      var cs = global.RRColourSurfaces;
      if (!cs || typeof cs.select !== "function") return;
      cs.select(letter);
      var tab = document.querySelector('.view-tab[data-view="surfaces"]');
      if (tab && tab.getAttribute("aria-selected") !== "true") tab.click();
    }
  function endDrag() { var env = envStack[envStack.length - 1];
      var was = env.drag;
      env.drag = null;
      env.floorCanvas.classList.remove("dragging");
      env.elevCanvas.classList.remove("dragging");
      redraw();
      if (was && !was.moved && was.face) selectDiagramFace(was.face);
      if (was && !(was.kind === "face" && !was.moved)) env.onDragEnd();
    }
  function mergePatch(patch) { var env = envStack[envStack.length - 1];
      const st = Object.assign({}, env.getState(), patch);
      env.setState(RoomMath.clampRoom(st));
      env.onChange();
    }
  function onFacingWheel(canvas, plane, evt) { var env = envStack[envStack.length - 1];
      const geo = RoomMath.compute(env.getState());
      if (plane === "floor") env.fl = floorLayout(geo);
      else env.el = elevLayout(geo);
      const p = canvasPos(canvas, evt);
      const ring = hitRing(p.x, p.y, geo, plane);
      if (!ring) return;
      evt.preventDefault();
      const which = (ring === "srcBYaw" || ring === "srcBPitch") ? "b" : "a";
      const step = evt.deltaY > 0 ? -5 : 5;
      const st = Object.assign({}, env.getState());
      if (plane === "floor") setYawPitch(st, which, yawOf(st, which) + step, null);
      else setYawPitch(st, which, null, pitchOf(st, which) + step);
      env.setState(RoomMath.clampRoom(st));
      env.onChange();
      redraw();
    }
  function onFacingKey(evt) { var env = envStack[envStack.length - 1];
      const k = evt.key;
      if (k !== "ArrowLeft" && k !== "ArrowRight" && k !== "ArrowUp" && k !== "ArrowDown" &&
          k !== "f" && k !== "F" && k !== "o" && k !== "O") return;
      const which = env.lastDragged === "sourceB" ? "b" : "a";
      const st = Object.assign({}, env.getState());
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
      env.setState(RoomMath.clampRoom(st));
      env.onChange();
      redraw();
      evt.preventDefault();
    }
  function onFacingDbl(canvas, plane, evt) { var env = envStack[envStack.length - 1];
      const geo = RoomMath.compute(env.getState());
      if (plane === "floor") env.fl = floorLayout(geo);
      else env.el = elevLayout(geo);
      const p = canvasPos(canvas, evt);
      const ring = hitRing(p.x, p.y, geo, plane);
      if (!ring) return;
      const which = (ring === "srcBYaw" || ring === "srcBPitch") ? "b" : "a";
      const st = Object.assign({}, env.getState());
      faceMicState(st, which);
      env.setState(RoomMath.clampRoom(st));
      env.onChange();
      redraw();
    }

  global.RoomEditor = { create: RoomEditorCreate };
})(window);
