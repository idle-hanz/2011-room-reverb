/** Client-side Prepare geometry (matches early_field algebra). */
window.RoomMath = (() => {
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const maxSpace = (W, mcx) => Math.max(0, 2 * Math.min(mcx, W - mcx));

  function clampRoom(state) {
    const W = state.W, H = state.H, L = state.L;
    let sx = clamp(state.sx, 0, W);
    let sz = clamp(state.sz, 0, L);
    let my = clamp(state.my, 0, H);
    let sy = state.sy != null ? clamp(state.sy, 0, H) : my;
    let mcz = clamp(state.mcz, 0, L);
    let mcx = state.reaktor_parity ? W * 0.5 : clamp(state.mcx, 0, W);
    let space = clamp(state.space, 0, maxSpace(W, mcx));
    return { ...state, sx, sz, my, sy, mcz, mcx, space };
  }

  function prepareFromMetres(W, L, sx, sz, mcz) {
    const sox = Math.abs(W) > 1e-12 ? sx / W : 0;
    const denom = L - mcz;
    const soz = Math.abs(denom) > 1e-12 ? (sz - mcz) / denom : 0;
    const mz = L - mcz;
    return { sox, soz, mz };
  }

  function yawRadFromState(s, side) {
    const key = side === "l" ? "yaw_l_deg" : side === "r" ? "yaw_r_deg" : "yaw_c_deg";
    if (s[key] != null && s[key] !== "" && isFinite(Number(s[key]))) {
      return (Number(s[key]) * Math.PI) / 180;
    }
    if (side === "c") return 0;
    if (s.toe_half_deg != null && s.toe_half_deg !== "" && isFinite(Number(s[key]))) {
      const half = (Number(s.toe_half_deg) * Math.PI) / 180;
      return side === "l" ? -half : half;
    }
    const d = (s.diverg != null ? Number(s.diverg) : 1) * 0.3 * 0.25;
    return side === "l" ? -d : d;
  }

  function lookFromYaw(yawRad) {
    return { x: -Math.sin(yawRad), z: Math.cos(yawRad) };
  }

  function compute(state) {
    const s = clampRoom(state);
    const { sox, soz, mz } = prepareFromMetres(s.W, s.L, s.sx, s.sz, s.mcz);
    const half = s.space * 0.5;
    const srcY = s.sy != null ? s.sy : s.my;
    const source = { x: s.sx, y: srcY, z: s.sz };
    const centre = { x: s.mcx, y: s.my, z: s.mcz };
    const left = { x: s.mcx - half, y: s.my, z: s.mcz };
    const right = { x: s.mcx + half, y: s.my, z: s.mcz };
    const mlalr = yawRadFromState(s, "l");
    const mralr = yawRadFromState(s, "r");
    const mcalr = yawRadFromState(s, "c");
    const look_l = lookFromYaw(mlalr);
    const look_r = lookFromYaw(mralr);
    const look_c = lookFromYaw(mcalr);
    const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
    return {
      state: { ...s, sox, soz, mz },
      source, mic_centre: centre, mic_left: left, mic_right: right,
      look_l, look_c, look_r,
      toe_l_deg: (mlalr * 180) / Math.PI,
      toe_c_deg: (mcalr * 180) / Math.PI,
      toe_r_deg: (mralr * 180) / Math.PI,
      distances: { sl: dist(source, left), sc: dist(source, centre), sr: dist(source, right) },
      max_space: maxSpace(s.W, s.mcx),
    };
  }

  return { clamp, maxSpace, clampRoom, prepareFromMetres, compute };
})();
