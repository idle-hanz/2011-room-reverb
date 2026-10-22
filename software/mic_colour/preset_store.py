"""Repo-root preset loader. v3 measured index, qualified v2 assumed index.

Does not scan pending_se2200a or presets_assumed_backup/.
"""

from __future__ import annotations

import json
from pathlib import Path

from mic_colour.model import model_from_params, model_name, param_names, repo_root

DEFAULT_PRESET_ID = "ShureSM57"

_ALIASES = {
    "sm57": DEFAULT_PRESET_ID,
    "shuresm57": DEFAULT_PRESET_ID,
    "shure_sm57": DEFAULT_PRESET_ID,
    "u87": "NeumannU87AiCardioid",
    "u87cardioid": "NeumannU87AiCardioid",
    "neumannu87aicardioid": "NeumannU87AiCardioid",
    "royer": "RoyerR121",
    "royerr121": "RoyerR121",
}

_STORE = None


def _norm(raw) -> str:
    return str(raw or "").strip().lower().replace(" ", "").replace("-", "").replace("_", "")


def _qualified(data: dict) -> bool:
    if not isinstance(data, dict):
        return False
    schema = str(data.get("schema") or "")
    if schema not in ("mic_fitter.preset.v3", "mic_fitter.preset.v2"):
        return False
    if str(data.get("model") or "") != model_name():
        return False
    if model_name() != "dual_shelf_plus_soft_one_pole":
        return False
    params = data.get("params")
    if not isinstance(params, dict):
        return False
    for name in param_names():
        if name not in params:
            return False
        try:
            float(params[name])
        except (TypeError, ValueError):
            return False
    mic_id = data.get("mic_id")
    return isinstance(mic_id, str) and bool(mic_id.strip())


class PresetStore:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else repo_root()
        self._by_id: dict = {}
        base = self.root / "mic_fitter" / "presets"
        self._load_index(base / "index.json", base)
        assumed = base / "assumed"
        self._load_index(assumed / "index.json", assumed)

    def _load_index(self, index_path: Path, folder: Path) -> None:
        if not index_path.is_file():
            return
        data = json.loads(index_path.read_text(encoding="utf-8"))
        folder_r = folder.resolve()
        for row in data.get("presets") or []:
            if not isinstance(row, dict):
                continue
            fn = row.get("file")
            if not isinstance(fn, str) or not fn or "/" in fn or "\\" in fn:
                continue
            path = (folder / fn).resolve()
            if path.parent != folder_r or not path.is_file():
                continue
            preset = json.loads(path.read_text(encoding="utf-8"))
            if not _qualified(preset):
                continue
            self._by_id[str(preset["mic_id"])] = preset

    def ids(self):
        return list(self._by_id)

    def get(self, mic_id: str):
        return self._by_id.get(mic_id)

    def match(self, norm_key: str):
        for mic_id in self._by_id:
            if _norm(mic_id) == norm_key:
                return mic_id
        return None

    def family_of(self, mic_id: str) -> str:
        preset = self._by_id.get(mic_id)
        if not preset:
            raise KeyError(mic_id)
        return str(preset.get("family") or "")

    def model_for(self, mic_id: str):
        preset = self._by_id.get(mic_id)
        if not preset:
            raise KeyError(mic_id)
        return model_from_params(preset["params"])

    def hpf_of(self, mic_id: str) -> dict:
        preset = self._by_id.get(mic_id) or {}
        switches = preset.get("switches") or {}
        return {
            "hpf_hz": switches.get("hpf_hz"),
            "hpf_slope": switches.get("hpf_slope") or 12,
        }

    def summaries(self):
        from mic_colour.pattern_map import capsule_law
        out = []
        for mic_id, preset in self._by_id.items():
            hpf = self.hpf_of(mic_id)
            out.append({
                "mic_id": mic_id,
                "display_name": preset.get("display_name") or mic_id,
                "honesty": preset.get("honesty"),
                "family": preset.get("family"),
                "schema": preset.get("schema"),
                "capsule": capsule_law(preset.get("family")),
                "hpf_hz": hpf.get("hpf_hz"),
                "hpf_slope": hpf.get("hpf_slope") or 12,
            })
        return out


def get_store() -> PresetStore:
    global _STORE
    if _STORE is None:
        _STORE = PresetStore()
    return _STORE


def resolve_preset_id(raw, *, explicit: bool = False) -> str:
    """Missing → ShureSM57 (SM57). An explicit unknown id raises."""
    if raw is None:
        return DEFAULT_PRESET_ID
    text = str(raw).strip()
    if not text or text.lower() in ("null", "none"):
        return DEFAULT_PRESET_ID
    key = _norm(text)
    if key in _ALIASES:
        return _ALIASES[key]
    if text == DEFAULT_PRESET_ID:
        return text
    store = get_store()
    if text in store._by_id:
        return text
    found = store.match(key)
    if found:
        return found
    if explicit:
        raise KeyError(f"unknown mic preset {text!r}")
    return DEFAULT_PRESET_ID
