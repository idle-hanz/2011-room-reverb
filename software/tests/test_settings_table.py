"""Every control, posted key, and server read is in the shared settings table.

Orphans are names that sit on only one of those surfaces. The test prints them.
A name outside the frozen sets fails. The test does not delete orphans and it
does not rewrite the table.
"""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
JS = SW / "static" / "js"
sys.path[:0] = [str(SW), str(SW / "engine")]

from fdn import DIFFUSION_MASTER_DEFAULT, DIFFUSION_MASTER_MIN  # noqa: E402
from settings_table import (  # noqa: E402
    BY_NAME,
    D,
    JSON_PATH,
    control_ids,
    payload,
    span_of,
)
from surface_colour import DEFAULT_DIFFUSION_SEED, DEFAULT_LAMBDA_REF_M  # noqa: E402

_POST_O = {"rr_mix.js", "routing_scene.js"}
_POST_BODY = {"polar_field.js", "rr_polar.js"}
_READ_RES = (
    r'body\.get\(\s*["\']([A-Za-z0-9_]+)["\']',
    r'body\[\s*["\']([A-Za-z0-9_]+)["\']\s*\]',
    r'["\']([A-Za-z0-9_]+)["\']\s+in\s+body\b',
    r'_keyed\(\s*body\s*,\s*["\']([A-Za-z0-9_]+)["\']',
    r'_explicit_field\(\s*body\s*,\s*["\']([A-Za-z0-9_]+)["\']',
    r'_opt_height\(\s*body\s*,\s*["\']([A-Za-z0-9_]+)["\']',
    r'_optional_float\(\s*body\s*,\s*["\']([A-Za-z0-9_]+)["\']',
    r'_optional_pattern\(\s*body\s*,\s*["\']([A-Za-z0-9_]+)["\']',
    r'_fam\(\s*["\']([A-Za-z0-9_]+)["\']',
    r'_pol\(\s*["\']([A-Za-z0-9_]+)["\']',
    r'\(\s*["\'][lcr]["\']\s*,\s*["\']([A-Za-z0-9_]+)["\']\s*\)',
)


class _Controls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.bare = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "data-mic" in d:
            self.ids.add("data-mic=" + d["data-mic"])
        if "data-polar" in d:
            self.ids.add("data-polar=" + d["data-polar"])
        if tag not in ("input", "select", "textarea"):
            return
        if d.get("id"):
            self.ids.add(d["id"])
        elif "data-mic" not in d and "data-polar" not in d:
            self.bare.append(tag)


def _html_controls() -> tuple[set, list]:
    parser = _Controls()
    parser.feed((SW / "static" / "index.html").read_text(encoding="utf-8"))
    return parser.ids, parser.bare


def _posted_keys() -> set:
    found = set()
    for path in JS.rglob("*.js"):
        if "vendor" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if path.name == "rr_state.js":
            found.update(re.findall(r'\bS\(\s*["\']([A-Za-z0-9_]+)["\']\s*\)', text))
        found.update(re.findall(r'\bstate\.([A-Za-z0-9_]+)\s*=', text))
        found.update(re.findall(r'\bstate\[\s*["\']([A-Za-z0-9_]+)["\']\s*\]\s*=', text))
        if path.name in _POST_O:
            found.update(re.findall(r'\bo\.([A-Za-z0-9_]+)\s*=', text))
        if path.name in _POST_BODY:
            found.update(re.findall(r'\bbody\.([A-Za-z0-9_]+)\s*=', text))
        if path.name == "sl_room_result.js":
            found.update(re.findall(r'\bs\.([A-Za-z0-9_]+)\s*=', text))
        if path.name == "routing_scene.js" and 'name + "_preset"' in text:
            for name in ("array", "room"):
                for suffix in ("_preset", "_amount", "_pre", "_drive_db"):
                    found.add(name + suffix)
            found.update(re.findall(
                r"^\s+(bloom_preset|bloom_amount|bloom_colour|glue_colour|pre_colour|"
                r"pre_drive_db|predelay_ms|bloom_attack_scale|bloom_release_scale)\s*:",
                text,
                re.M,
            ))
        if path.name == "rr_space.js" and "mics: selectedMics" in text:
            found.add("mics")
        if path.name == "rr_mix.js" and 'o["mic_x_"' in text:
            for cap in ("l", "c", "r"):
                for axis in ("x", "y", "z"):
                    found.add("mic_%s_%s" % (axis, cap))
    return {key for key in found if not key.startswith("_")}


def _server_reads() -> set:
    text = (SW / "app_server.py").read_text(encoding="utf-8")
    found = set()
    for pattern in _READ_RES:
        found.update(re.findall(pattern, text))
    if 'body.get(_prefix + "_preset")' in text:
        for name in ("array", "room"):
            for suffix in ("_preset", "_amount", "_pre", "_drive_db"):
                found.add(name + suffix)
    if '"place_" +' in text:
        for ch in ("l", "c", "r"):
            found.add("place_" + ch)
    return {key for key in found if not key.startswith("_")}


def _row_for_control(control: str):
    if control in BY_NAME:
        return control
    for row in BY_NAME.values():
        if control in (row.get("controls") or []):
            return row["name"]
    return None


def test_generated_json_matches_the_table():
    disk = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    live = json.loads(json.dumps(payload()))
    assert disk == live


def test_diffusion_and_lambda_match_the_engine_constants():
    assert D("diffusion_master") == DIFFUSION_MASTER_DEFAULT
    assert span_of("diffusion_master") == (float(DIFFUSION_MASTER_MIN), 0.0)
    assert D("diffusion_seed") == DEFAULT_DIFFUSION_SEED
    assert D("lambda_ref") == DEFAULT_LAMBDA_REF_M


# One-surface names after the 2026-10-26 orphan rows. A name outside this
# set is a new orphan and fails. A name that later gains a second surface
# drops out and still passes.
_ORPHAN_POSTED_NOT_READ = frozenset("""
desk_touched fader_c fader_direct fader_dry fader_early fader_fdn fader_l fader_r
gain_exact_c gain_exact_l gain_exact_r link_heights link_lr_yaw live_drag_render
mute_c mute_direct mute_dry mute_early mute_fdn mute_l mute_r natural_bus
pan_c pan_l pan_r phase_c phase_l phase_r polar_radius
room_slot room_x room_y room_yaw room_z
route_array_amount route_array_comp route_array_drive route_array_pre
route_master_amount route_master_comp route_master_drive route_master_pre
route_room_amount route_room_comp route_room_drive route_room_pre
solo_c solo_direct solo_dry solo_early solo_fdn solo_l solo_r
spare_off stereo_mic surf_amount surf_rendered_t20 surf_suggestions
trim_c trim_direct trim_dry trim_early trim_fdn trim_l trim_r
wetBypass width_c width_l width_r
""".split())
_ORPHAN_READ_NOT_POSTED = frozenset("""
air_iso grid mic_pos_c mic_pos_l mic_pos_r mic_preset mirror_null null_mode
ref_mode rendered_t20 route_c route_l route_r selected_mics
""".split())
_ORPHAN_TABLE_ONLY = frozenset(
    "binaural_image_set binaural_level_ref binaural_tail_mode ear_spacing_m".split()
)


def test_controls_posts_and_reads_are_in_the_table():
    controls, bare = _html_controls()
    posted = _posted_keys()
    reads = _server_reads()
    names = set(BY_NAME)
    missing_controls = sorted(item for item in controls if _row_for_control(item) is None)
    missing_posted = sorted(key for key in posted if key not in names)
    missing_reads = sorted(key for key in reads if key not in names)
    html_names = {_row_for_control(item) for item in controls}
    html_names.discard(None)
    posted_not_read = sorted((posted & names) - reads)
    read_only = sorted((reads & names) - posted - html_names)
    table_only = sorted(names - posted - reads - html_names)
    print("ORPHANS posted-not-read: " + ", ".join(posted_not_read))
    print("ORPHANS read-not-posted: " + ", ".join(read_only))
    print("ORPHANS table-only: " + ", ".join(table_only))
    new_orphans = {
        "posted-not-read": sorted(set(posted_not_read) - _ORPHAN_POSTED_NOT_READ),
        "read-not-posted": sorted(set(read_only) - _ORPHAN_READ_NOT_POSTED),
        "table-only": sorted(set(table_only) - _ORPHAN_TABLE_ONLY),
    }
    new_orphans = {key: names for key, names in new_orphans.items() if names}
    assert not new_orphans, new_orphans
    assert not bare, bare
    assert not missing_controls, missing_controls
    assert not missing_posted, missing_posted
    assert not missing_reads, missing_reads
    assert control_ids() >= controls
