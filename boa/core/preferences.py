import json
from pathlib import Path

from boa.core.atomic_io import atomic_write_text

CONFIG_DIR = Path.home() / ".boa"
PREFERENCES_FILE = CONFIG_DIR / "preferences.json"

DEFAULT_PREFERENCES = {
    "language": "fr",
    "grid_size": 20,
    "snap_to_grid": True,
    "confirm_delete": False,
    "auto_imports": True,
    "default_variable_type": "any",
    "autosave_enabled": False,
    "autosave_interval": 5,
    "default_project_dir": "",
    "recent_projects": [],
    "welcome_shown": False,
}


def load_preferences() -> dict:
    preferences = dict(DEFAULT_PREFERENCES)
    if not PREFERENCES_FILE.exists():
        return preferences
    try:
        data = json.loads(PREFERENCES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return preferences
    if isinstance(data, dict):
        preferences.update({key: data[key] for key in preferences if key in data})
    return preferences


def save_preferences(preferences: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    clean = dict(DEFAULT_PREFERENCES)
    clean.update({key: preferences[key] for key in clean if key in preferences})
    atomic_write_text(
        PREFERENCES_FILE, json.dumps(clean, indent=2, ensure_ascii=False) + "\n", backup=False,
    )


def available_languages() -> list[tuple[str, str]]:
    return [("fr", "Français"), ("en", "English")]
