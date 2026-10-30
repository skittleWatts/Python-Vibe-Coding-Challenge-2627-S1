"""Small local recovery store; named blueprint saves remain separate."""
import json
from .blueprint import Blueprint, load


def recover(root):
    path = root / "session" / "recovery.json"
    if not path.exists():
        return None, ""
    try:
        return load(path), ""
    except (OSError, ValueError) as exc:
        return None, f"Recovery could not be loaded: {exc}"


def store_recovery(root, blueprint):
    data = blueprint.to_dict()
    Blueprint.from_dict(data)
    folder = root / "session"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "recovery.json"
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


def store_preferences(root, sound):
    folder = root / "session"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "preferences.json").write_text(json.dumps({"sound": bool(sound)}), encoding="utf-8")


def sound_preference(root):
    try:
        return json.loads((root / "session" / "preferences.json").read_text(encoding="utf-8")).get("sound", False) is True
    except (OSError, ValueError, AttributeError):
        return False
