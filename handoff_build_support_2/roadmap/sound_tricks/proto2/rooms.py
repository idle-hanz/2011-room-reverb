"""Material sets (all from the app's own Surfaces library, presets/surfaces/*.json)."""
import json, copy, os
LIB = "/workspace/st_work/software/presets/surfaces"
def mat(mid):
    m = json.load(open(os.path.join(LIB, mid + ".json"))); return m
def card(mid, diffusion=0.15):
    m = mat(mid)
    return {"absorb_hz": m["absorb_hz"], "absorb": m["absorb"], "diffusion": diffusion, "material": mid,
            "eq": {"low_shelf_hz": 200, "low_shelf_db": 0, "high_shelf_hz": 5000, "high_shelf_db": 0, "peak_hz": 1000, "peak_db": 0, "peak_q": 1}}
SETS = {
  # EQ_PLAN D-EQ real default materials: plaster walls and ceiling, parquet floor (untreated room)
  "real_default": {"A": "plaster_smooth", "C": "plaster_smooth", "B": "plaster_smooth", "D": "plaster_smooth", "E": "wood_parquet", "F": "plaster_smooth"},
  # Carpeted, panelled studio room: plywood-panelled walls, carpet floor, gypsum ceiling
  "studio_panelled": {"A": "plywood_panel", "C": "plywood_panel", "B": "plywood_panel", "D": "plywood_panel", "E": "carpet_on_concrete", "F": "gypsum_painted"},
  # Bare plaster/brick room: brick side walls, plaster end walls and ceiling, painted concrete floor
  "bare_brick_plaster": {"A": "brick_unglazed", "C": "brick_unglazed", "B": "plaster_smooth", "D": "plaster_smooth", "E": "concrete_painted", "F": "plaster_smooth"},
}
def surfaces_for(name, base):
    s = copy.deepcopy(base)
    for k, mid in SETS[name].items():
        c = card(mid); s[k].update({"absorb": c["absorb"], "absorb_hz": c["absorb_hz"], "material": mid})
    return s
