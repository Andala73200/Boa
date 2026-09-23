from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QAction, QContextMenuEvent, QResizeEvent
from PySide6.QtWidgets import QMenu, QSizePolicy, QStyle, QToolBar

from boa.core.models import BLOCK_DEFINITIONS, BlockDefinition
from boa.i18n import tr
from boa.ui.block_shortcuts import block_available_for_document, block_shortcut_store


_DEFINITIONS = {definition.key: definition for definition in BLOCK_DEFINITIONS}


class BoaToolBar(QToolBar):
    block_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(tr("toolbar.title"), parent)
        self.setMovable(False)
        self.setFloatable(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._document_kind = "graph"
        self._block_actions: list[tuple[QAction, str]] = []
        self._store = block_shortcut_store()
        self._store.changed.connect(self._schedule_rebuild)
        self._rebuild_actions()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("toolbar.title"))
        self._rebuild_actions()

    def set_document_kind(self, kind: str) -> None:
        resolved = kind if kind in {"function", "class"} else "graph"
        if resolved == self._document_kind:
            return
        self._document_kind = resolved
        self._rebuild_actions()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_visible_actions)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        action = self.actionAt(event.pos())
        block_key = str(action.data()) if action is not None else ""
        if not block_key:
            event.ignore()
            return
        menu = QMenu(self)
        label = "toolbar.remove_favorite" if self._store.is_favorite(block_key) else "toolbar.add_favorite"
        toggle = menu.addAction(tr(label))
        if menu.exec(event.globalPos()) == toggle:
            self._store.toggle_favorite(block_key)
        event.accept()

    def _schedule_rebuild(self) -> None:
        QTimer.singleShot(0, self._rebuild_actions)

    def _rebuild_actions(self) -> None:
        self.clear()
        self._block_actions.clear()
        for block_key in self._store.displayed_blocks():
            if not block_available_for_document(block_key, self._document_kind):
                continue
            definition = _DEFINITIONS.get(block_key)
            if definition is None:
                continue
            action = self.addAction(_block_title(definition))
            action.setData(block_key)
            action.setToolTip(
                f"{_block_description(definition)}\n{tr('toolbar.favorite_hint')}"
            )
            action.triggered.connect(
                lambda checked=False, key=block_key: self.block_requested.emit(key)
            )
            self._block_actions.append((action, block_key))
        QTimer.singleShot(0, self._update_visible_actions)

    def _update_visible_actions(self) -> None:
        if not self._block_actions:
            return
        frame = self.style().pixelMetric(QStyle.PixelMetric.PM_ToolBarFrameWidth, None, self)
        spacing = self.style().pixelMetric(QStyle.PixelMetric.PM_ToolBarItemSpacing, None, self)
        budget = max(0, self.contentsRect().width() - (2 * frame) - 12)
        used = 0
        still_fitting = True
        for action, _block_key in self._block_actions:
            if not still_fitting:
                action.setVisible(False)
                continue
            action.setVisible(True)
            widget = self.widgetForAction(action)
            width = widget.sizeHint().width() if widget is not None else 0
            required = width + (spacing if used else 0)
            if width <= 0 or used + required > budget:
                action.setVisible(False)
                still_fitting = False
                continue
            used += required


def _block_title(definition: BlockDefinition) -> str:
    key = f"block.{definition.key}.title"
    title = tr(key)
    return definition.title if title == key else title


def _block_description(definition: BlockDefinition) -> str:
    key = f"block.{definition.key}.description"
    description = tr(key)
    if description == key:
        return tr("tooltip.block.generic", name=_block_title(definition))
    return description
