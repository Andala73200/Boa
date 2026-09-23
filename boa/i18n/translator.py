import json
from pathlib import Path

_language = "fr"
_catalog: dict[str, str] = {}


def set_language(language: str) -> None:
    global _language, _catalog
    lang = language if language else "fr"
    path = Path(__file__).resolve().parent / f"{lang}.json"
    if not path.exists():
        lang = "fr"
        path = Path(__file__).resolve().parent / "fr.json"
    catalog = {}
    for catalog_path in [path, *sorted(path.parent.glob(f"{lang}_*.json"))]:
        try:
            catalog.update(json.loads(catalog_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    _catalog = catalog
    _language = lang


def tr(key: str, **values) -> str:
    text = _catalog.get(key, key)
    if values:
        try:
            return text.format(**values)
        except (KeyError, ValueError):
            return text
    return text


set_language(_language)
