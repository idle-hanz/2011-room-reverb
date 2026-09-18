
/* 2011 Room Reverb — room math + canvas drag editor */
(function (global) {
  "use strict";

  const RoomMath = {
    clamp(v, lo, hi) {
      return Math.max(lo, Math.min(hi, v));
    },
    maxSpace(W, mcx) {
      return Math.max(0, 2 * Math.min(mcx, W - mcx));
    },
    clampRoom(s) {
      const W = s.W, H = s.H, L = s.L;
      const mcx = s.reaktor_parity ? W * 0.5 : this.clamp(s.mcx, 0, W);
      const my = this.clamp(s.my, 0, H);
      let sy = s.sy;
      if (sy == null || sy === "" || !isFinite(Number(sy))) sy = my;
      else sy = this.clamp(Number(sy), 0, H);
      return Object.assign({}, s, {
        sx: this.clamp(s.sx, 0, W),
        sz: this.clamp(s.sz, 0, L),
        my: my,
        sy: sy,
        mcz: this.clamp(s.mcz, 0, L),
        mcx: mcx,
        space: this.clamp(s.space, 0, this.maxSpace(W, mcx)),
      });
    },
    compute(raw) {
      const s = this.clampRoom(raw);
      const sox = Math.abs(s.W) > 1e-12 ? s.sx / s.W : 0;
      const denom = s.L - s.mcz;
      const soz = Math.abs(denom) > 1e-12 ? (s.sz - s.mcz) / denom : 0;
      const mz = s.L - s.mcz;
      const half = s.space * 0.5;
      const source = { x: s.sx, y: s.sy, z: s.sz };
      const centre = { x: s.mcx, y: s.my, z: s.mcz };
      const left = { x: s.mcx - half, y: s.my, z: s.mcz };
      const right = { x: s.mcx + half, y: s.my, z: s.mcz };
      let ml, mr, mc;
      if (s.yaw_l_deg != null && s.yaw_l_deg !== "" && isFinite(Number(s.yaw_l_deg))) {
        ml = (Number(s.yaw_l_deg) * Math.PI) / 180;
      } else if (s.toe_half_deg != null && s.toe_half_deg !== "" && isFinite(Number(s.toe_half_deg))) {
        ml = (-Number(s.toe_half_deg) * Math.PI) / 180;
      } else {
        ml = s.diverg * 0.3 * -0.25;
      }
      if (s.yaw_r_deg != null && s.yaw_r_deg !== "" && isFinite(Number(s.yaw_r_deg))) {
        mr = (Number(s.yaw_r_deg) * Math.PI) / 180;
      } else if (s.toe_half_deg != null && s.toe_half_deg !== "" && isFinite(Number(s.toe_half_deg))) {
        mr = (Number(s.toe_half_deg) * Math.PI) / 180;
      } else {
        mr = s.diverg * 0.3 * 0.25;
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
    mic: "#60a5fa",
    L: "#a78bfa",
    R: "#34d399",
  };
  const HIT = 18;
  const FAR = 90; /* px — beyond this, empty click uses lastDragged */

  function RoomEditorCreate(opts) {
    const floorCanvas = opts.floorCanvas;
    const elevCanvas = opts.elevCanvas;
    const view3dCanvas = opts.view3dCanvas || null;
    const getState = opts.getState;
    const setState = opts.setState;
    const onChange = opts.onChange;

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
      const cw = elevCanvas.width, ch = elevCanvas.height;
      const scale = Math.min((cw - padX * 2) / L, (ch - padY * 2) / H);
      const rw = L * scale, rh = H * scale;
      return {
        L: L, H: H, scale: scale,
        ox: (cw - rw) / 2, oy: (ch - rh) / 2,
        rw: rw, rh: rh,
      };
    }
    function toPx(x, z, lay) {
      return { px: lay.ox + x * lay.scale, py: lay.oy + (lay.L - z) * lay.scale };
    }
    function toM(px, py, lay) {
      return { x: (px - lay.ox) / lay.scale, z: lay.L - (py - lay.oy) / lay.scale };
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

    function drawFloor(geo) {
      const ctx = fctx;
      const cw = floorCanvas.width, ch = floorCanvas.height;
      fl = floorLayout(geo);
      ctx.clearRect(0, 0, cw, ch);
      ctx.fillStyle = "#0a0b0e";
      ctx.fillRect(0, 0, cw, ch);
      ctx.fillStyle = "#12141a";
      ctx.strokeStyle = "#3a4155";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.rect(fl.ox, fl.oy, fl.rw, fl.rh);
      ctx.fill();
      ctx.stroke();

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

      const Sp = toPx(geo.source.x, geo.source.z, fl);
      const Cp = toPx(geo.mic_centre.x, geo.mic_centre.z, fl);
      const Lp = toPx(geo.mic_left.x, geo.mic_left.z, fl);
      const Rp = toPx(geo.mic_right.x, geo.mic_right.z, fl);

      ctx.strokeStyle = "rgba(96,165,250,0.35)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(Lp.px, Lp.py);
      ctx.lineTo(Rp.px, Rp.py);
      ctx.stroke();

      const al = Math.max(0.45, Math.min(geo.state.W, geo.state.L) * 0.09);
      drawArrow(ctx, Lp.px, Lp.py, geo.look_l.x, geo.look_l.z, al, COLORS.L, fl.scale);
      drawArrow(ctx, Rp.px, Rp.py, geo.look_r.x, geo.look_r.z, al, COLORS.R, fl.scale);

      drawHandle(ctx, Lp.px, Lp.py, COLORS.L, "L", false, false);
      drawHandle(ctx, Rp.px, Rp.py, COLORS.R, "R", false, false);
      drawHandle(ctx, Cp.px, Cp.py, COLORS.mic, "Mic", !!(drag && drag.kind === "mic"), hover === "mic");
      drawHandle(ctx, Sp.px, Sp.py, COLORS.src, "Src", !!(drag && drag.kind === "source"), hover === "source");

      ctx.fillStyle = "#8b92a5";
      ctx.font = "600 11px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Width X →", fl.ox + fl.rw / 2, fl.oy + fl.rh + 22);
      ctx.save();
      ctx.translate(fl.ox - 22, fl.oy + fl.rh / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText("Length Z →", 0, 0);
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
      ctx.beginPath();
      ctx.rect(el.ox, el.oy, el.rw, el.rh);
      ctx.fill();
      ctx.stroke();

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

      const srcActive = !!(drag && drag.kind === "srcHeight");
      const micActive = !!(drag && (drag.kind === "micHeight" || drag.kind === "height"));
      const srcPrimary = lastDragged === "source";
      const micPrimary = lastDragged === "mic";
      drawHandle(ctx, Sp.px, Sp.py, COLORS.src, "Src H", srcActive || srcPrimary, hover === "srcHeight");
      drawHandle(ctx, Cp.px, Cp.py, COLORS.mic, "Mic H", micActive || micPrimary, hover === "micHeight" || hover === "height");

      ctx.fillStyle = "#5c6478";
      ctx.font = "12px Segoe UI, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Length Z →", el.ox + el.rw / 2, ch - 8);
      ctx.textAlign = "right";
      ctx.fillStyle = COLORS.src;
      ctx.fillText("Src " + geo.state.sy.toFixed(2) + " m", cw - 12, Sp.py + 4);
      ctx.fillStyle = COLORS.mic;
      ctx.fillText("Mic " + geo.state.my.toFixed(2) + " m", cw - 12, Cp.py + 4);
    }

    function redraw() {
      const geo = RoomMath.compute(getState());
      drawFloor(geo);
      drawElev(geo);
      if (view3d) view3d.redraw();
      return geo;
    }

    function floorDists(px, py, geo) {
      const Sp = toPx(geo.source.x, geo.source.z, fl);
      const Cp = toPx(geo.mic_centre.x, geo.mic_centre.z, fl);
      return {
        ds: Math.hypot(px - Sp.px, py - Sp.py),
        dc: Math.hypot(px - Cp.px, py - Cp.py),
      };
    }
    function elevDists(px, py, geo) {
      const Sp = ePx(geo.source.z, geo.source.y, el);
      const Cp = ePx(geo.mic_centre.z, geo.mic_centre.y, el);
      return {
        ds: Math.hypot(px - Sp.px, py - Sp.py),
        dc: Math.hypot(px - Cp.px, py - Cp.py),
      };
    }
    function hitFloor(px, py, geo) {
      const d = floorDists(px, py, geo);
      if (d.ds <= HIT && d.ds <= d.dc) return "source";
      if (d.dc <= HIT) return "mic";
      return null;
    }
    function pickFloorKind(px, py, geo) {
      const hit = hitFloor(px, py, geo);
      if (hit) return hit;
      const d = floorDists(px, py, geo);
      const nearest = d.ds <= d.dc ? "source" : "mic";
      if (Math.min(d.ds, d.dc) <= FAR) return nearest;
      return lastDragged;
    }
    function hitElev(px, py, geo) {
      const d = elevDists(px, py, geo);
      const srcHit = d.ds <= HIT;
      const micHit = d.dc <= HIT;
      if (srcHit && micHit) return d.ds <= d.dc ? "srcHeight" : "micHeight";
      if (srcHit) return "srcHeight";
      if (micHit) return "micHeight";
      return null;
    }
    function pickElevKind(px, py, geo) {
      const hit = hitElev(px, py, geo);
      if (hit) return hit;
      const d = elevDists(px, py, geo);
      const nearest = d.ds <= d.dc ? "srcHeight" : "micHeight";
      if (Math.min(d.ds, d.dc) <= FAR) return nearest;
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
      drag = null;
      floorCanvas.classList.remove("dragging");
      elevCanvas.classList.remove("dragging");
      redraw();
    }

    floorCanvas.addEventListener("pointerdown", function (evt) {
      const geo = RoomMath.compute(getState());
      fl = floorLayout(geo);
      const p = canvasPos(floorCanvas, evt);
      const onHandle = !!hitFloor(p.x, p.y, geo);
      const kind = pickFloorKind(p.x, p.y, geo);
      lastDragged = kind;
      drag = { kind: kind, canvas: "floor" };
      floorCanvas.classList.add("dragging");
      try { floorCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
      if (!onHandle) {
        /* Empty floor: move selected object to click, then drag */
        const m = toM(p.x, p.y, fl);
        const st = Object.assign({}, getState());
        if (kind === "source") {
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
        const m = toM(p.x, p.y, fl);
        const st = Object.assign({}, getState());
        if (drag.kind === "source") {
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
      const h = hitFloor(p.x, p.y, geo);
      if (h !== hover) {
        hover = h;
        redraw();
      }
    });

    elevCanvas.addEventListener("pointerdown", function (evt) {
      const geo = RoomMath.compute(getState());
      el = elevLayout(geo);
      const p = canvasPos(elevCanvas, evt);
      const onHandle = !!hitElev(p.x, p.y, geo);
      const kind = pickElevKind(p.x, p.y, geo);
      lastDragged = kind === "srcHeight" ? "source" : "mic";
      drag = { kind: kind, canvas: "elev" };
      elevCanvas.classList.add("dragging");
      try { elevCanvas.setPointerCapture(evt.pointerId); } catch (e) {}
      if (!onHandle) {
        /* Empty elev: move selected height handle to click */
        const m = eM(p.x, p.y, el);
        const st = Object.assign({}, getState());
        applyLinkedHeight(st, kind, m.y);
        if (kind === "srcHeight") {
          st.sz = RoomMath.clamp(m.z, 0, st.L);
        } else {
          st.mcz = RoomMath.clamp(m.z, 0, st.L);
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
        const m = eM(p.x, p.y, el);
        const st = Object.assign({}, getState());
        const kind = drag.kind === "height" ? "micHeight" : drag.kind;
        applyLinkedHeight(st, kind, m.y);
        if (kind === "srcHeight") {
          st.sz = RoomMath.clamp(m.z, 0, st.L);
        } else {
          st.mcz = RoomMath.clamp(m.z, 0, st.L);
        }
        setState(RoomMath.clampRoom(st));
        onChange();
        redraw();
        return;
      }
      const h = hitElev(p.x, p.y, geo);
      if (h !== hover) {
        hover = h;
        redraw();
      }
    });

    floorCanvas.addEventListener("pointerup", endDrag);
    elevCanvas.addEventListener("pointerup", endDrag);
    floorCanvas.addEventListener("pointercancel", endDrag);
    elevCanvas.addEventListener("pointercancel", endDrag);
    window.addEventListener("pointerup", endDrag);

    return { redraw: redraw, setTool: setTool, view3d: view3d };
  }

  global.RoomMath = RoomMath;
  global.RoomEditor = { create: RoomEditorCreate };
})(window);
