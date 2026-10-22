/** Client-side Prepare geometry (matches early_field algebra). */
window.RoomMath = (() => {
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const maxSpace = (W, mcx) => Math.max(0, 2 * Math.min(mcx, W - mcx));
  const CENTRE_DZ_MAX = 0.20;
  const SUPER_A = 0.37;

  function polarA(family, polar) {
    if (String(family || "cardioid") === "bi") return 0;
    const d = clamp(Number(polar) || 0, 0, 1);
    if (d <= 0.5) return 1 - d;
    return 0.5 - (d - 0.5) * (0.5 - SUPER_A) / 0.5;
  }

  function polarGain(theta, family, polar) {
    const a = polarA(family, polar);
    return a + (1 - a) * Math.cos(theta);
  }

  function polarLabel(family, polar) {
    if (String(family || "cardioid") === "bi") return "Fig\u20118";
    const d = clamp(Number(polar) || 0, 0, 1);
    if (d < 0.18) return "Omni";
    if (d < 0.42) return "Subcardioid";
    if (d < 0.72) return "Cardioid";
    return "Supercardioid";
  }

  function derivePattern(family, polar) {
    if (String(family || "cardioid") === "bi") return "fig8";
    const d = clamp(Number(polar) || 0, 0, 1);
    if (d < 0.18) return "omni";
    if (d > 0.75) return "supercardioid";
    return "cardioid";
  }

  function polarFromPattern(pattern) {
    const p = String(pattern || "cardioid").toLowerCase();
    if (p === "omni") return 0;
    if (p === "supercardioid") return 1;
    return 0.5;
  }

  function familyFromPattern(pattern) {
    const p = String(pattern || "cardioid").toLowerCase();
    return (p === "fig8" || p === "bi") ? "bi" : "cardioid";
  }

  function clampRoom(state) {
    const W = state.W, H = state.H, L = state.L;
    let sx = clamp(state.sx, 0, W);
    let sz = clamp(state.sz, 0, L);
    let my = clamp(state.my, 0, H);
    let sy = state.sy != null ? clamp(state.sy, 0, H) : my;
    let mcz = clamp(state.mcz, 0, L);
    let mcx = state.reaktor_parity ? W * 0.5 : clamp(state.mcx, 0, W);
    let space = clamp(state.space, 0, maxSpace(W, mcx));
    let centre_dz = clamp(Number(state.centre_dz) || 0, -CENTRE_DZ_MAX, CENTRE_DZ_MAX);
    if (state.align_horizontal) centre_dz = 0;
    let mirror_b = !!state.mirror_b;
    let sx_b = (state.sx_b != null && isFinite(Number(state.sx_b))) ? clamp(Number(state.sx_b), 0, W) : clamp(W - sx, 0, W);
    let sy_b = (state.sy_b != null && isFinite(Number(state.sy_b))) ? clamp(Number(state.sy_b), 0, H) : sy;
    let sz_b = (state.sz_b != null && isFinite(Number(state.sz_b))) ? clamp(Number(state.sz_b), 0, L) : sz;
    if (mirror_b) {
      sx_b = clamp(W - sx, 0, W);
      sy_b = sy;
      sz_b = sz;
    }
    let source_balance = clamp(Number(state.source_balance) || 0, -1, 1);
    return {
      ...state, sx, sz, my, sy, mcz, mcx, space, centre_dz,
      sx_b, sy_b, sz_b, mirror_b, source_balance,
      two_sources: !!state.two_sources
    };
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
    if (s.toe_half_deg != null && s.toe_half_deg !== "" && isFinite(Number(s.toe_half_deg))) {
      const half = (Number(s.toe_half_deg) * Math.PI) / 180;
      return side === "l" ? -half : half;
    }
    const mid = (s.diverg != null ? Number(s.diverg) : 1) * 0.5;
    return side === "l" ? mid - 0.25 : mid + 0.25;
  }

  /* K1 (28 Sep 2026): one yaw convention. +yaw aims toward +X (screen right).
     Must equal early_field.YAW_X_SIGN in Python. Was -1 (crossed capsules). */
  const YAW_X_SIGN = 1;

  function lookFromYaw(yawRad) {
    return { x: YAW_X_SIGN * Math.sin(yawRad), z: Math.cos(yawRad) };
  }

  function compute(state) {
    const s = clampRoom(state);
    const { sox, soz, mz } = prepareFromMetres(s.W, s.L, s.sx, s.sz, s.mcz);
    const half = s.space * 0.5;
    const srcY = s.sy != null ? s.sy : s.my;
    const dz = s.centre_dz || 0;
    const source = { x: s.sx, y: srcY, z: s.sz };
    const source_b = s.two_sources ? { x: s.sx_b, y: s.sy_b, z: s.sz_b } : null;
    const barZ = s.mcz;
    const capY = (key) => {
      const lo = 0.02;
      const hi = Math.max(lo, s.H - 0.02);
      const v = s[key];
      if (v == null || v === "" || !isFinite(Number(v))) return s.my;
      return clamp(Number(v), lo, hi);
    };
    let yL = capY("my_l");
    let yR = capY("my_r");
    const yC = capY("my_c");
    if (s.align_horizontal) yR = yL;
    const centre = { x: s.mcx, y: yC, z: barZ + dz };
    let left, right, mlalr, mralr, mcalr;
    if (s.mic_setup === "binaural") {
      /* Ears rotate with the head. L = H − (s/2)·right, same as early_field. */
      const psi = ((Number(s.head_yaw_deg) || 0) * Math.PI) / 180;
      const rx = Math.cos(psi);
      const rz = -YAW_X_SIGN * Math.sin(psi);
      left = { x: s.mcx - half * rx, y: yL, z: barZ - half * rz };
      right = { x: s.mcx + half * rx, y: yR, z: barZ + half * rz };
      mlalr = psi - Math.PI / 2;
      mralr = psi + Math.PI / 2;
      mcalr = psi;
    } else {
      left = { x: s.mcx - half, y: yL, z: barZ };
      right = { x: s.mcx + half, y: yR, z: barZ };
      mlalr = yawRadFromState(s, "l");
      mralr = yawRadFromState(s, "r");
      mcalr = yawRadFromState(s, "c");
    }
    const look_l = lookFromYaw(mlalr);
    const look_r = lookFromYaw(mralr);
    const look_c = lookFromYaw(mcalr);
    const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
    return {
      state: { ...s, sox, soz, mz },
      source, source_b, mic_centre: centre, mic_left: left, mic_right: right,
      look_l, look_c, look_r,
      toe_l_deg: (mlalr * 180) / Math.PI,
      toe_c_deg: (mcalr * 180) / Math.PI,
      toe_r_deg: (mralr * 180) / Math.PI,
      distances: { sl: dist(source, left), sc: dist(source, centre), sr: dist(source, right) },
      max_space: maxSpace(s.W, s.mcx),
    };
  }

  function poseNum(v, fallback) {
    if (v == null || v === "" || !isFinite(Number(v))) return fallback;
    return Number(v);
  }

  /* Null preset, yaw or pitch follows A. Mirror + null yaw is −yaw_A.
   * Twin of source_radiation.effective_b_pose. An explicit "omni" stays omni. */
  function effectiveBPose(st) {
    const presetA = st.source_radiation || "omni";
    const yawA = poseNum(st.source_yaw, 0);
    const pitchA = poseNum(st.source_pitch, 0);
    const mirror = st.mirror_b == null ? true : !!st.mirror_b;
    const rawP = st.source_radiation_b;
    const preset = (rawP == null || rawP === "") ? presetA : String(rawP);
    const yaw = poseNum(st.source_yaw_b, mirror ? -yawA : yawA);
    const pitch = poseNum(st.source_pitch_b, pitchA);
    return { preset: preset, yaw: yaw, pitch: pitch };
  }

  return {
    clamp, maxSpace, clampRoom, prepareFromMetres, compute,
    lookFromYaw, YAW_X_SIGN, polarA, polarGain, polarLabel, derivePattern,
    polarFromPattern, familyFromPattern, CENTRE_DZ_MAX, effectiveBPose
  };
})();
