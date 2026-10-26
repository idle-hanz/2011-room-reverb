"""One table of every setting the page, the posts, and the server share.

`default` is the value `params_from_body` uses when the key is missing, except
where a row sets `absent` (the body omitted the key) or `stored` (the value
kept on `DEFAULTS` for `GET /api/settings?part=defaults`). `page` is the boot value in
`rr_state.js` when that boot value is not `default`.

The JSON next to the static files is generated from this module. The page
fetches it once from `GET /api/settings`.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / "static" / "settings.json"

# Routes that receive the mix body or the raw scene.
_BOTH = [
    "/api/params/live",
    "/api/render",
    "/api/params/images",
    "/api/params/phys",
    "/api/display/polar",
    "/api/room/result",
]
_ROUTES = {
    "both": _BOTH,
    "play": ["/api/params/live"],
    "render": ["/api/render"],
    "polar": ["/api/display/polar"],
    "colour": ["/api/render"],
    "room": ["/api/room/result"],
    "none": [],
}

_MIC_SETUPS = [
    "ab_omni", "ab_card", "xy_90", "xy_120", "ortf", "ortf_c", "nos", "din",
    "ms", "ms_a", "ms_b", "ms_c", "ms_2", "mono_c", "binaural", "custom",
]
_PATTERNS = ["omni", "cardioid", "supercardioid", "hypercardioid", "fig8"]
_FAMILIES = ["cardioid", "bi"]
_CLIMATES = [
    "studio_20C_50RH", "dry_20C_20RH", "humid_20C_80RH", "warm_22C_40RH",
]
_HEADS = ["SADIE2_KU100", "SADIE2_KEMAR", "THK_KU100_FF"]
_SHAPES = ["box", "splay", "lede", "live", "gable", "hex"]
_RADIATION = [
    "omni", "talking_head", "trumpet_byu", "violin_byu",
    "cab_1x12_closed", "cab_4x12_closed", "piano_grand_lid_open",
]


def R(
    name,
    default,
    unit="",
    tab="",
    route="both",
    path="both",
    lo=None,
    hi=None,
    choices=None,
    controls=None,
    **extra,
):
    """One setting. `route` is a key of `_ROUTES` or a list of paths."""
    if choices is not None:
        span = list(choices)
    elif lo is not None and hi is not None:
        span = [lo, hi]
    elif lo is not None:
        span = [lo, None]
    else:
        span = None
    if isinstance(route, str):
        posted = list(_ROUTES[route])
    else:
        posted = list(route)
    row = {
        "name": name,
        "default": default,
        "range": span,
        "unit": unit,
        "tab": tab,
        "route": posted,
        "path": path,
    }
    if controls:
        row["controls"] = list(controls)
    row.update(extra)
    return row


def _rows():
    """Every setting. Order is the page, then keys the server reads with no control."""
    rows = []
    add = rows.append

    # Header. IR length is on Play and Render.
    add(R("ir_length_ms", 1500.0, unit="ms", tab="Header", lo=50, hi=2000, in_defaults=True))
    add(R("live_drag_render", False, tab="Header", path="neither"))
    add(R("wavInput", None, tab="Header", route="none", path="neither"))
    add(R("loadSetupFile", None, tab="Header", route="none", path="neither"))

    # Room.
    add(R("W", 6.0, unit="m", tab="Room", lo=1, hi=80, in_defaults=True))
    add(R("H", 3.0, unit="m", tab="Room", lo=1, hi=40, in_defaults=True))
    add(R("L", 8.0, unit="m", tab="Room", lo=2, hi=120, in_defaults=True))
    add(R("link_heights", False, tab="Room", controls=["link_heights", "link_heights_mic"], in_defaults=True))
    add(R("sx", 2.6, unit="m", tab="Room", in_defaults=True))
    add(R("sz", 4.75, unit="m", tab="Room", in_defaults=True))
    add(R("sy", 1.2, unit="m", tab="Mic", lo=0, hi=20, in_defaults=True))
    add(R("room_shape", None, tab="Room", choices=_SHAPES, page="box"))
    add(R("mirror_lr", False, tab="Surfaces", controls=["mirrorLr"], page=True))
    add(R("smooth", True, tab="Room", in_defaults=True))
    add(R("movement", 0.0, tab="Room", lo=0, hi=100))
    add(R("hadamard_n", 32, tab="Room", choices=[8, 16, 32, 64, 128], in_defaults=True))
    add(R("grid", None, tab="Room", choices=["8", "16", "32", "64", "64like", "128"], route="both", path="both"))

    # Source. Number boxes share the slider's row.
    add(R("source_radiation", "omni", tab="Source", choices=_RADIATION, controls=["sourcePreset"], in_defaults=True))
    add(R("source_yaw", 0.0, unit="deg", tab="Source", lo=-180, hi=180, controls=["sourceYaw", "sourceYawNum"], in_defaults=True))
    add(R("source_pitch", 0.0, unit="deg", tab="Source", lo=-89, hi=89, controls=["sourcePitch", "sourcePitchNum"], in_defaults=True))
    add(R("source_size_m", None, unit="m", tab="Source", lo=0.005, hi=0.4, controls=["sourceSize", "sourceSizeNum"]))
    add(R("source_radiation_b", None, tab="Source", choices=_RADIATION, page=None))
    add(R("source_yaw_b", None, unit="deg", tab="Source", lo=-180, hi=180, page=None))
    add(R("source_pitch_b", None, unit="deg", tab="Source", lo=-89, hi=89, page=None))
    add(R("two_sources", False, tab="Source"))
    add(R("mirror_b", True, tab="Source", controls=["mirrorB"]))
    add(R("source_balance", 0.0, tab="Source", lo=-1, hi=1, controls=["sourceBalance"]))
    add(R("sx_b", 3.4, unit="m", tab="Source"))
    add(R("sy_b", 1.2, unit="m", tab="Source"))
    add(R("sz_b", 4.75, unit="m", tab="Source"))
    add(R("path_on", False, tab="Source", in_defaults=True))
    add(R("path_preset", "still", tab="Source", in_defaults=True))
    add(R("ellipse_rate", 1.0, tab="Source", in_defaults=True))
    add(R("ellipse_rx", 0.42, unit="m", tab="Source", in_defaults=True))
    add(R("ellipse_rz", 0.35, unit="m", tab="Source", in_defaults=True))

    # Mic stand and capsules.
    add(R("mic_setup", "ortf", tab="Mic", choices=_MIC_SETUPS))
    add(R("space", 0.25, unit="m", tab="Mic", lo=0, hi=6, in_defaults=True))
    add(R("diverg", 1.0, tab="Mic", in_defaults=True))
    add(R("toe_half_deg", None, unit="deg", tab="Mic", page=None))
    add(R("car_omni", 1.0, tab="Mic", lo=0, hi=1, in_defaults=True))
    add(R("mcx", 3.0, unit="m", tab="Mic", lo=0, hi=40, in_defaults=True))
    add(R("mcz", 1.5, unit="m", tab="Mic", lo=0, hi=60, in_defaults=True))
    add(R("my", 1.5, unit="m", tab="Mic", lo=0, hi=20, in_defaults=True))
    add(R("my_l", None, unit="m", tab="Mic"))
    add(R("my_r", None, unit="m", tab="Mic"))
    add(R("my_c", None, unit="m", tab="Mic"))
    add(R("centre_dz", 0.0, unit="m", tab="Mic", lo=-0.2, hi=0.2))
    add(R("align_horizontal", False, tab="Mic", page=True))
    add(R("link_lr_yaw", True, tab="Mic", path="neither"))
    add(R("pattern_l", "cardioid", tab="Mic", choices=_PATTERNS, in_defaults=True))
    add(R("pattern_c", "cardioid", tab="Mic", choices=_PATTERNS, in_defaults=True))
    add(R("pattern_r", "cardioid", tab="Mic", choices=_PATTERNS, in_defaults=True))
    add(R("family_l", "cardioid", tab="Mic", choices=_FAMILIES))
    add(R("family_c", "cardioid", tab="Mic", choices=_FAMILIES))
    add(R("family_r", "cardioid", tab="Mic", choices=_FAMILIES))
    add(R("family_side", "cardioid", tab="Mic", choices=_FAMILIES, path="neither"))
    add(R("polar_l", 0.5, tab="Mic", lo=0, hi=1))
    add(R("polar_c", 0.5, tab="Mic", lo=0, hi=1))
    add(R("polar_r", 0.5, tab="Mic", lo=0, hi=1))
    add(R("polar_side", 0.5, tab="Mic", lo=0, hi=1, path="neither"))
    add(R("yaw_l_deg", None, unit="deg", tab="Mic", lo=-180, hi=180, in_defaults=True, page=None))
    add(R("yaw_c_deg", 0.0, unit="deg", tab="Mic", lo=-180, hi=180, in_defaults=True))
    add(R("yaw_r_deg", None, unit="deg", tab="Mic", lo=-180, hi=180, in_defaults=True, page=None))
    add(R("mic_preset_l", "NeumannU87AiCardioid", tab="Mic"))
    add(R("mic_preset_c", "NeumannU87AiCardioid", tab="Mic"))
    add(R("mic_preset_r", "NeumannU87AiCardioid", tab="Mic"))
    add(R("mic_preset", None, tab="Mic"))
    add(R("mic_preset_side", "NeumannU87AiCardioid", tab="Mic", path="neither"))
    add(R("mic_preset_centre", "NeumannU87AiCardioid", tab="Mic", path="neither"))
    add(R("preset_owns_pattern", True, tab="Mic"))
    add(R("colour_mode", "MEASURED_SHELF", tab="Mic", choices=["MEASURED_SHELF", "BYPASS", "ASSUMED_TOYS"]))
    add(R("colour_impl", "sos", tab="Advanced", choices=["sos", "iir"]))
    add(R("mic_hpf_engaged", False, tab="Mic"))
    add(R("mic_hpf_sides", False, tab="Mic"))
    add(R("mic_hpf_centre", False, tab="Mic"))
    add(R("mic_hpf_l", None, tab="Mic"))
    add(R("mic_hpf_r", None, tab="Mic"))
    add(R("mic_hp_on", False, tab="Mic"))
    add(R("mic_hp_hz", 40.0, unit="Hz", tab="Mic", lo=12, hi=250))
    add(R("mic_response_hz", 10000.0, unit="Hz", tab="Mic", lo=10000, hi=20000))
    add(R("mic_proximity", 0.25, tab="Mic", lo=0, hi=1))
    add(R("prox_l", True, tab="Mic"))
    add(R("prox_c", True, tab="Mic"))
    add(R("prox_r", True, tab="Mic"))
    add(R("capsule_mm", 17.0, unit="mm", tab="Mic", lo=8, hi=34))
    add(R("ms_decode", False, tab="Mic"))
    add(R("third_mic", "", tab="Mic", choices=["", "off", "centre", "room"], page="off"))
    add(R("pair_mode", "", tab="Mix", choices=["", "stereo", "ms", "independent"], page="stereo"))
    add(R("pan_law", "linear", tab="Mix", choices=["linear", "constant"]))
    add(R("link_mode", "", tab="Mix", choices=["", "mirror", "linked", "split"], page="mirror"))
    add(R("mic_route_l", "pan", tab="Mix", choices=["pan", "l", "r", "c", "s", "m"]))
    add(R("mic_route_c", "pan", tab="Mix", choices=["pan", "l", "r", "c", "s", "m"]))
    add(R("mic_route_r", "pan", tab="Mix", choices=["pan", "l", "r", "c", "s", "m"]))
    add(R("route_l", "pan", tab="Mix", choices=["pan", "l", "r", "c", "s", "m"]))
    add(R("route_c", "pan", tab="Mix", choices=["pan", "l", "r", "c", "s", "m"]))
    add(R("route_r", "pan", tab="Mix", choices=["pan", "l", "r", "c", "s", "m"]))
    add(R("ms_s", "l", tab="Mix", choices=["l", "c", "r"]))
    add(R("ms_m", "c", tab="Mix", choices=["l", "c", "r"]))
    add(R("s_detached", False, tab="Mix"))
    add(R("side_split", False, tab="Mic", path="neither"))
    add(R("head_yaw_deg", 0.0, unit="deg", tab="Mic", lo=-180, hi=180, controls=["head_yaw"], in_defaults=True))
    add(R("binaural_preset", "SADIE2_KU100", tab="Mic", choices=_HEADS, in_defaults=True))
    add(R("binaural_tail_mode", "diffuse_ic", tab="Mic", in_defaults=True))
    add(R("binaural_level_ref", "head_centre", tab="Mic", in_defaults=True))
    add(R("binaural_image_set", "binaural_rear32", tab="Mic", in_defaults=True))
    add(R("ear_spacing_m", 0.18, unit="m", tab="Mic", route="none", path="neither"))

    # Per-capsule room spots. The post copies them onto mic_x/y/z when Place is Room.
    for cap, xpos in (("l", None), ("c", None), ("r", None)):
        add(R("room_%s_x" % cap, xpos, unit="m", tab="Mic"))
        add(R("room_%s_y" % cap, None, unit="m", tab="Mic"))
        add(R("room_%s_z" % cap, None, unit="m", tab="Mic"))
        add(R("room_%s_yaw" % cap, None, unit="deg", tab="Mic"))
        add(R("mic_x_%s" % cap, None, unit="m", tab="Mic"))
        add(R("mic_y_%s" % cap, None, unit="m", tab="Mic"))
        add(R("mic_z_%s" % cap, None, unit="m", tab="Mic"))
        add(R("mic_pos_%s" % cap, None, tab="Mic"))
        add(R("place_%s" % cap, "array", tab="Mic", choices=["array", "room"]))
    add(R("room_slot", "r", tab="Mic", choices=["l", "c", "r"], path="neither"))
    add(R("room_x", 4.0, unit="m", tab="Mic", path="neither"))
    add(R("room_z", 2.0, unit="m", tab="Mic", path="neither"))
    add(R("room_y", 1.5, unit="m", tab="Mic", path="neither"))
    add(R("room_yaw", 0.0, unit="deg", tab="Mic", path="neither"))

    # Gains the desk derives. Empty body uses these; the page posts faders instead.
    add(R("mic_gain_l", 1.0, tab="Mix", lo=0, hi=16))
    add(R("mic_gain_c", 1.0, tab="Mix", lo=0, hi=16))
    add(R("mic_gain_r", 1.0, tab="Mix", lo=0, hi=16))
    add(R("mic_pan_l", -1.0, tab="Mix", lo=-1, hi=1))
    add(R("mic_pan_c", 0.0, tab="Mix", lo=-1, hi=1))
    add(R("mic_pan_r", 1.0, tab="Mix", lo=-1, hi=1))
    add(R("mic_phase_l", 1.0, tab="Mix", choices=[-1, 1]))
    add(R("mic_phase_c", 1.0, tab="Mix", choices=[-1, 1]))
    add(R("mic_phase_r", 1.0, tab="Mix", choices=[-1, 1]))

    # Mix desk. early_wet is 1 when the key is absent and 0 on the defaults dict.
    add(R("early_wet", 0.0, tab="Mix", lo=0, hi=1, in_defaults=True, absent=1.0, page=1.0))
    add(R("fdn_wet", 1.0, tab="Mix", lo=0, hi=1, in_defaults=True))
    add(R("direct_wet", 1.0, tab="Mix", lo=0, hi=1, in_defaults=True))
    add(R("dry_gain", 0.0, tab="Mix", lo=0, hi=1, in_defaults=True))
    add(R("fdn_g", 1.0, tab="Advanced", lo=0, hi=1, in_defaults=True))
    add(R("fader_l", 0.5, tab="Mix", lo=0, hi=1, path="both"))
    add(R("fader_c", 0.5, tab="Mix", lo=0, hi=1))
    add(R("fader_r", 0.5, tab="Mix", lo=0, hi=1))
    add(R("fader_direct", 0.0, tab="Mix", lo=0, hi=1))
    add(R("fader_fdn", 0.5, tab="Mix", lo=0, hi=1))
    add(R("fader_early", 0.0, tab="Mix", lo=0, hi=1))
    add(R("fader_dry", 0.0, tab="Mix", lo=0, hi=1, path="neither"))
    add(R("trim_l", 0.0, unit="dB", tab="Mix", lo=-12, hi=12))
    add(R("trim_c", 0.0, unit="dB", tab="Mix", lo=-12, hi=12))
    add(R("trim_r", 0.0, unit="dB", tab="Mix", lo=-12, hi=12))
    add(R("trim_direct", 0.0, unit="dB", tab="Mix", lo=-12, hi=12))
    add(R("trim_fdn", 0.0, unit="dB", tab="Mix", lo=-12, hi=12))
    add(R("trim_early", 0.0, unit="dB", tab="Mix", lo=-12, hi=12))
    add(R("trim_dry", 0.0, unit="dB", tab="Mix", lo=-12, hi=12, path="neither"))
    add(R("pan_l", -1.0, tab="Mix", lo=-1, hi=1))
    add(R("pan_c", 0.0, tab="Mix", lo=-1, hi=1))
    add(R("pan_r", 1.0, tab="Mix", lo=-1, hi=1))
    add(R("width_l", 0.0, unit="dB", tab="Mix", lo=-24, hi=24))
    add(R("width_c", 0.0, unit="dB", tab="Mix", lo=-24, hi=24))
    add(R("width_r", 0.0, unit="dB", tab="Mix", lo=-24, hi=24))
    add(R("gain_exact_l", None, tab="Mix"))
    add(R("gain_exact_c", None, tab="Mix"))
    add(R("gain_exact_r", None, tab="Mix"))
    add(R("mute_l", False, tab="Mix"))
    add(R("mute_c", False, tab="Mix"))
    add(R("mute_r", False, tab="Mix"))
    add(R("mute_direct", False, tab="Mix"))
    add(R("mute_fdn", False, tab="Mix"))
    add(R("mute_early", False, tab="Mix"))
    add(R("mute_dry", False, tab="Mix", path="neither"))
    add(R("phase_l", 1.0, tab="Mix", choices=[-1, 1]))
    add(R("phase_c", 1.0, tab="Mix", choices=[-1, 1]))
    add(R("phase_r", 1.0, tab="Mix", choices=[-1, 1]))
    add(R("solo_direct", False, tab="Mix"))
    add(R("solo_fdn", False, tab="Mix"))
    add(R("solo_early", False, tab="Mix"))
    add(R("solo_dry", False, tab="Mix", path="neither"))
    add(R("solo_l", False, tab="Mix"))
    add(R("solo_c", False, tab="Mix"))
    add(R("solo_r", False, tab="Mix"))
    add(R("stereo_mic", False, tab="Mix"))
    add(R("natural_bus", False, tab="Mix"))
    add(R("wetBypass", False, tab="Mix", route="none", path="neither"))
    add(R("desk_touched", False, tab="Mix", path="neither"))
    add(R("polar_radius", "db", tab="Mic", choices=["db", "linear"], path="neither"))
    add(R("decay_s", 1.8, unit="s", tab="Mix", lo=0.05, hi=8))
    add(R("decay_lock", True, tab="Mix"))
    add(R("decay_mode", "flat", tab="Surfaces", choices=["flat", "surfaces"]))
    add(R("treat_sets_decay", False, tab="Surfaces"))
    add(R("phys_ceiling", True, tab="Mix"))
    add(R("sub_hp", True, tab="Mix"))
    add(R("offaxis_tail", False, tab="Mix"))
    add(R("shared_tail", False, tab="Advanced", in_defaults=True))
    add(R("mirror_null", False, tab="Advanced"))
    add(R("null_mode", False, tab="Advanced"))

    # Surfaces, air, colour display.
    add(R("humidity", 0.35, tab="Surfaces", lo=0, hi=1))
    add(R("air_shelf", 1.0, tab="Surfaces", lo=0, hi=1))
    add(R("air_climate", "studio_20C_50RH", tab="Surfaces", choices=_CLIMATES, in_defaults=True))
    add(R("air_iso", True, tab="Advanced", in_defaults=True))
    add(R("diffusion_master", -0.25, tab="Surfaces", lo=-0.5, hi=0))
    add(R("diffusion_seed", 0, tab="Surfaces", lo=0, hi=None, in_defaults=True))
    add(R("lambda_ref", 0.02, unit="m", tab="Surfaces", lo=0, hi=1, in_defaults=True))
    add(R("jitterSlider", 0.15, tab="Surfaces", lo=0, hi=1, route="none", path="neither"))
    add(R("structureDifSlider", 0.15, tab="Surfaces", lo=0, hi=1, route="none", path="neither"))
    add(R("surfaces", None, tab="Surfaces"))
    add(R("surfaces_solo", None, tab="Surfaces", page=None))
    # Play monitor only. Render does not read these. The gain is held on the client.
    add(R("match_solo_level", True, tab="Surfaces", route="play"))
    add(R("solo_match_letter", None, tab="Surfaces", route="play", page=None))
    add(R("solo_match_gain", 1.0, tab="Surfaces", route="play", lo=0.0, hi=10.0 ** (24.0 / 20.0)))
    add(R("surfaces_mute", {"A": False, "B": False, "C": False, "D": False, "E": False, "F": False}, tab="Surfaces"))
    add(R("surf_treatment", [], tab="Surfaces"))
    add(R("surf_cal", None, tab="Surfaces"))
    # Suggestions stay on the page. The room-result post copies state, so the key can be present.
    add(R("surf_suggestions", [], tab="Surfaces", route="room", path="neither"))
    add(R("surf_rendered_t20", None, tab="Surfaces", route="room", path="neither"))
    add(R("surf_directional", False, tab="Surfaces"))
    add(R("surf_amount", 100.0, tab="Surfaces", lo=0, hi=100))
    add(R("colourRefMode", "peak", tab="Surfaces", choices=["peak", "rms"], route="colour", path="neither"))
    add(R("ref_mode", "peak", tab="Surfaces", choices=["peak", "rms"], route="colour", path="neither"))
    add(R("rendered_t20", None, tab="Surfaces", route="room", path="render"))

    # Routing strips. Posted only while that strip is on.
    for prefix, tab in (("array", "Mix"), ("room", "Mix"), ("master", "Mix")):
        add(R("route_%s_pre" % prefix, "none", tab=tab, path="both"))
        add(R("route_%s_drive" % prefix, 0.0, tab=tab))
        add(R("route_%s_comp" % prefix, "off", tab=tab))
        add(R("route_%s_amount" % prefix, 0.0, tab=tab, lo=0, hi=100))
    for prefix in ("array", "room", "bloom"):
        add(R("%s_preset" % prefix, "natural", tab="Mix"))
        add(R("%s_amount" % prefix, 0.0, tab="Mix", lo=0, hi=100))
    add(R("array_pre", "off", tab="Mix"))
    add(R("array_drive_db", 0.0, unit="dB", tab="Mix"))
    add(R("room_pre", "off", tab="Mix"))
    add(R("room_drive_db", 0.0, unit="dB", tab="Mix"))
    add(R("bloom_colour", False, tab="Mix"))
    add(R("glue_colour", False, tab="Mix"))
    add(R("pre_colour", "off", tab="Mix"))
    add(R("pre_drive_db", 0.0, unit="dB", tab="Mix"))
    add(R("predelay_ms", 0.0, unit="ms", tab="Mix"))
    add(R("bloom_attack_scale", 1.0, tab="Mix"))
    add(R("bloom_release_scale", 1.0, tab="Mix"))

    # Display toggles. Nothing in the audio post uses these names.
    add(R("show_mic_L", True, tab="Space", route="none", path="neither", controls=["data-mic=L"]))
    add(R("show_mic_C", False, tab="Space", route="none", path="neither", controls=["data-mic=C"]))
    add(R("show_mic_R", True, tab="Space", route="none", path="neither", controls=["data-mic=R"]))
    add(R("polar_show_L", False, tab="Polar", route="none", path="neither", controls=["data-polar=L"]))
    add(R("polar_show_C", False, tab="Polar", route="none", path="neither", controls=["data-polar=C"]))
    add(R("polar_show_R", False, tab="Polar", route="none", path="neither", controls=["data-polar=R"]))
    add(R("polar_show_sum", True, tab="Polar", route="none", path="neither", controls=["data-polar=sum"]))
    add(R("mics", ["C"], tab="Space", route="polar", path="neither"))
    add(R("selected_mics", None, tab="Space", route="polar", path="neither"))
    add(R("n_az", 72, tab="Polar", lo=24, hi=180, route="polar", path="neither"))
    add(R("sample_rate", None, unit="Hz", tab="Header", path="both"))
    add(R("colour_rev", "", tab="Header", path="both"))
    add(R("spare_off", False, tab="Mix", route="none", path="neither"))

    return rows


ROWS = _rows()
BY_NAME = {}
for _row in ROWS:
    if _row["name"] in BY_NAME:
        raise RuntimeError("duplicate setting " + _row["name"])
    BY_NAME[_row["name"]] = _row


def D(name: str):
    """Table default. Dicts and lists are copies."""
    value = BY_NAME[name]["default"]
    if isinstance(value, (dict, list)):
        return deepcopy(value)
    return value


def miss(name: str):
    """Value used when the key is absent. `absent` wins over `default`."""
    row = BY_NAME[name]
    if "absent" in row:
        return row["absent"]
    return D(name)


def span_of(name: str):
    """Low and high from the table. Both ends are numbers."""
    lo, hi = BY_NAME[name]["range"]
    return float(lo), float(hi)


def page_value(name: str):
    """Boot value for rr_state. `page` wins over `default`."""
    row = BY_NAME[name]
    if "page" in row:
        value = row["page"]
    else:
        value = row["default"]
    if isinstance(value, (dict, list)):
        return deepcopy(value)
    return value


def server_defaults() -> dict:
    """The dict `GET /api/settings?part=defaults` returns. Same keys and values as the old literal."""
    out = {}
    for row in ROWS:
        if not row.get("in_defaults"):
            continue
        if "stored" in row:
            out[row["name"]] = row["stored"]
        else:
            value = row["default"]
            out[row["name"]] = deepcopy(value) if isinstance(value, (dict, list)) else value
    return out


def payload() -> dict:
    return {"rows": ROWS, "by_name": BY_NAME}


def write_json(path: Path | None = None) -> Path:
    dest = path or JSON_PATH
    text = json.dumps(payload(), indent=2, allow_nan=False) + "\n"
    dest.write_text(text, encoding="utf-8")
    return dest


def control_ids() -> set:
    """HTML ids and data-mic / data-polar tokens this table claims."""
    found = set()
    for row in ROWS:
        found.add(row["name"])
        for item in row.get("controls") or []:
            found.add(item)
    return found


if __name__ == "__main__":
    write_json()
