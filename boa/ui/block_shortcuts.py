from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from boa.core.models import BLOCK_DEFINITIONS


SHORTCUTS_FILE = Path.home() / ".boa" / "block_shortcuts.json"
MAX_RECENT_BLOCKS = 80


class BlockShortcutStore(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._favorites: list[str] = []
        self._recent: list[str] = []
        self._load()

    def favorites(self) -> list[str]:
        return list(self._favorites)

    def recent(self) -> list[str]:
        return list(self._recent)

    def displayed_blocks(self) -> list[str]:
        return self.favorites() or self.recent()

    def is_favorite(self, block_key: str) -> bool:
        return block_key in self._favorites

    def add_favorite(self, block_key: str) -> None:
        if not self._is_valid(block_key) or block_key in self._favorites:
            return
        self._favorites.append(block_key)
        self._save_and_notify()

    def remove_favorite(self, block_key: str) -> None:
        if block_key not in self._favorites:
            return
        self._favorites.remove(block_key)
        self._save_and_notify()

    def toggle_favorite(self, block_key: str) -> None:
        if self.is_favorite(block_key):
            self.remove_favorite(block_key)
        else:
            self.add_favorite(block_key)

    def remember(self, block_key: str) -> None:
        if not self._is_valid(block_key):
            return
        updated = [block_key, *(key for key in self._recent if key != block_key)]
        updated = updated[:MAX_RECENT_BLOCKS]
        if updated == self._recent:
            return
        self._recent = updated
        self._save_and_notify()

    def _load(self) -> None:
        try:
            data = json.loads(SHORTCUTS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        self._favorites = self._clean(data.get("favorites", []))
        self._recent = self._clean(data.get("recent", []))[:MAX_RECENT_BLOCKS]

    def _save_and_notify(self) -> None:
        SHORTCUTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {"favorites": self._favorites, "recent": self._recent}
        temporary = SHORTCUTS_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(SHORTCUTS_FILE)
        self.changed.emit()

    def _clean(self, values) -> list[str]:
        if not isinstance(values, list):
            return []
        valid = {definition.key for definition in BLOCK_DEFINITIONS}
        result: list[str] = []
        for value in values:
            key = str(value)
            if key in valid and key not in result:
                result.append(key)
        return result

    @staticmethod
    def _is_valid(block_key: str) -> bool:
        return any(definition.key == block_key for definition in BLOCK_DEFINITIONS)


_STORE: BlockShortcutStore | None = None


def block_shortcut_store() -> BlockShortcutStore:
    global _STORE
    if _STORE is None:
        _STORE = BlockShortcutStore()
    return _STORE


def remember_block_used(block_key: str) -> None:
    block_shortcut_store().remember(block_key)


def block_available_for_document(block_key: str, document_kind: str) -> bool:
    kind = document_kind if document_kind in {"function", "class"} else "graph"
    function_only = {"def_input", "def_input_p", "def_output", "def_output_p", "return"}
    if block_key in function_only:
        return kind == "function"
    if block_key == "class_attribute":
        return kind == "class"
    if block_key == "run":
        return kind == "graph"
    return True
