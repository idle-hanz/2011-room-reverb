(function () {
  "use strict";

  /* Canonical stereo mic presets (space m, toe_half_deg = L/R from forward). */
  var MIC_PRESETS = {
    ab_omni: { space: 0.80, toe_half_deg: 0, car_omni: 0, polar: ["L", "R"],
      pattern_l: "omni", pattern_c: "omni", pattern_r: "omni",
      yaw_l_deg: 0, yaw_c_deg: 0, yaw_r_deg: 0 },
    ab_card: { space: 0.80, toe_half_deg: 5, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -5, yaw_c_deg: 0, yaw_r_deg: 5 },
    xy_90:   { space: 0.01, toe_half_deg: 45, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -45, yaw_c_deg: 0, yaw_r_deg: 45 },
    xy_120:  { space: 0.01, toe_half_deg: 60, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -60, yaw_c_deg: 0, yaw_r_deg: 60 },
    ortf:    { space: 0.17, toe_half_deg: 55, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -55, yaw_c_deg: 0, yaw_r_deg: 55 },
    nos:     { space: 0.30, toe_half_deg: 45, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -45, yaw_c_deg: 0, yaw_r_deg: 45 },
    din:     { space: 0.20, toe_half_deg: 45, car_omni: 1, polar: ["L", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -45, yaw_c_deg: 0, yaw_r_deg: 45 },
    /* ASSUMED: Mid cardioid + inward side cardioids (no engine fig-8 decode) */
    ms:      { space: 0.05, toe_half_deg: 90, car_omni: 1, polar: ["L", "C", "R"],
      pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
      yaw_l_deg: -90, yaw_c_deg: 0, yaw_r_deg: 90 },
    /* ASSUMED: Mid cardioid + Side fig-8 */
    ms_classic: { space: 0.05, toe_half_deg: 90, car_omni: 1, polar: ["L", "C", "R"],
      pattern_l: "f