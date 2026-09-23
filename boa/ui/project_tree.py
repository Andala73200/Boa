from __future__ import annotations

from copy import deepcopy
from pathlib import PurePosixPath

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QStyle, QTreeWidget, QVBoxLayout, QWidget

from boa.core.project_tree_data import CLASSES_FOLDER_ID, FILES_FOLDER_ID, FUNCTIONS_FOLDER_ID, normalize_tree_layout
from boa.i18n import tr
from boa.ui.project_tree_commands import ProjectTreeCommands
from boa.ui.project_tree_items import (
    CLASS_KIND, FOLDER_KIND, FUNCTION_KIND, GRAPH_KIND, ROOT_KIND, SCRIPT_KIND,
    decorate_item, default_tree_data, find_item, is_protected, item_from_data, item_id,
    item_to_data, kind_of, make_item, new_id, normalized_name, sort_children, under_folder,
)


class ProjectTree(ProjectTreeCommands, QWidget):
    tree_changed = Signal()
    graph_open_requested = Signal(str)
    graph_run_requested = Signal(str)
    script_open_requested = Signal(str)
    script_run_requested = Signal(str)
    script_convert_requested = Signal(str)
    folder_convert_requested = Signal(str)
    graph_created = Signal(str, str)
    graph_duplicated = Signal(str, str, str)
    script_created = Signal(str, str, str)
    graph_deleted = Signal(str)
    script_deleted = Signal(str)
    item_renamed = Signal(str, str, str)
    main_graph_changed = Signal(str)
    function_open_requested = Signal(str)
    function_created = Signal(str, str)
    function_deleted = Signal(str)
    class_open_requested = Signal(str)
    class_created = Signal(str, str)
    class_deleted = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._main_graph_id = "main"
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(18)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tree.installEventFilter(self)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._open_item)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.model().rowsMoved.connect(self._on_rows_moved)
        self.from_data(default_tree_data())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.tree)

    def retranslate_ui(self) -> None:
        self.from_data(self.to_data())

    def to_data(self) -> dict:
        root = self.tree.topLevelItem(0)
        return item_to_data(root) if root else default_tree_data()

    def from_data(self, data: dict | None) -> None:
        normalized = normalize_tree_layout(deepcopy(data) if data else default_tree_data())
        self.tree.blockSignals(True)
        self.tree.clear()
        root = item_from_data(normalized)
        root.setText(0, tr("project.root"))
        for uid, key in {
            FILES_FOLDER_ID: "project.files",
            FUNCTIONS_FOLDER_ID: "project.functions",
            CLASSES_FOLDER_ID: "project.classes",
        }.items():
            item = find_item(root, uid)
            if item:
                item.setText(0, tr(key))
        self.tree.addTopLevelItem(root)
        self._decorate_recursive(root)
        root.setExpanded(True)
        self.tree.blockSignals(False)
        self.set_main_graph_id(self._main_graph_id)

    def set_main_graph_id(self, graph_id: str) -> None:
        self._main_graph_id = graph_id
        root = self.tree.topLevelItem(0)
        if root is None:
            return
        self._mark_main_recursive(root)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.tree and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_F2:
                self._rename_current_item(); return True
            if event.key() == Qt.Key.Key_Delete:
                self._delete_item(self.tree.currentItem()); return True
        return super().eventFilter(watched, event)

    def add_generated_graph(self, graph_id: str, name: str, parent_id: str = "") -> None:
        self._append(self._find(parent_id or FILES_FOLDER_ID), name, GRAPH_KIND, graph_id)

    def add_generated_function(self, function_id: str, name: str, parent_id: str = "") -> None:
        self._append(self._find(parent_id or FUNCTIONS_FOLDER_ID), name, FUNCTION_KIND, function_id)

    def add_generated_class(self, class_id: str, name: str, parent_id: str = "") -> None:
        self._append(self._find(parent_id or CLASSES_FOLDER_ID), name, CLASS_KIND, class_id)

    def remove_item(self, uid: str) -> None:
        item = self._find_optional(uid)
        if item and item.parent():
            item.parent().removeChild(item)
            self._sort_files()

    def set_item_name(self, uid: str, name: str) -> None:
        item = self._find_optional(uid)
        if not item:
            return
        self.tree.blockSignals(True)
        item.setText(0, name)
        self.tree.blockSignals(False)
        self._sort_files()

    def script_ids_in_folder(self, folder_id: str) -> list[str]:
        parent = self._find_optional(folder_id)
        result: list[str] = []
        if not parent:
            return result
        def visit(node) -> None:
            for index in range(node.childCount()):
                child = node.child(index)
                if kind_of(child) == SCRIPT_KIND:
                    result.append(item_id(child))
                elif kind_of(child) == FOLDER_KIND:
                    visit(child)
        visit(parent)
        return result

    def script_parent_id(self, script_id: str) -> str:
        item = self._find_optional(script_id)
        return item_id(item.parent()) if item and item.parent() else FILES_FOLDER_ID

    def paired_graph_id(self, script_id: str) -> str:
        item = self._find_optional(script_id)
        if not item or not item.parent():
            return ""
        wanted, parent = PurePosixPath(item.text(0)).stem.casefold(), item.parent()
        for index in range(parent.childCount()):
            sibling = parent.child(index)
            if kind_of(sibling) == GRAPH_KIND and PurePosixPath(sibling.text(0)).stem.casefold() == wanted:
                return item_id(sibling)
        return ""

    def _open_item(self, item, *_args) -> None:
        signal = {
            GRAPH_KIND: self.graph_open_requested, SCRIPT_KIND: self.script_open_requested,
            FUNCTION_KIND: self.function_open_requested, CLASS_KIND: self.class_open_requested,
        }.get(kind_of(item))
        if signal:
            signal.emit(item_id(item))

    def _on_item_changed(self, item, _column: int) -> None:
        normalized = normalized_name(item.text(0), kind_of(item))
        if normalized and normalized != item.text(0):
            self.tree.blockSignals(True); item.setText(0, normalized); self.tree.blockSignals(False)
        self._sort_files()
        self.item_renamed.emit(kind_of(item), item_id(item), item.text(0))
        self.tree_changed.emit()

    def _on_rows_moved(self, *_args) -> None:
        self._sort_files()
        self.tree_changed.emit()

    def _append(self, parent, name: str, kind: str, uid: str | None = None):
        child = make_item(name, kind, uid or new_id(kind), False)
        parent.addChild(child)
        decorate_item(self, child)
        parent.setExpanded(True)
        self._sort_files()
        self.tree.setCurrentItem(child)
        self.tree_changed.emit()
        return child

    def _files_parent(self, item):
        if kind_of(item) == FOLDER_KIND and under_folder(item, FILES_FOLDER_ID):
            return item
        return self._find(FILES_FOLDER_ID)

    def _find(self, uid: str):
        return self._find_optional(uid) or self.tree.topLevelItem(0)

    def _find_optional(self, uid: str):
        return find_item(self.tree.topLevelItem(0), uid)

    def _sort_files(self) -> None:
        root = self._find_optional(FILES_FOLDER_ID)
        if root:
            self.tree.blockSignals(True); sort_children(root); self.tree.blockSignals(False)

    def _decorate_recursive(self, item) -> None:
        decorate_item(self, item)
        for index in range(item.childCount()):
            self._decorate_recursive(item.child(index))

    def _mark_main_recursive(self, item) -> None:
        if kind_of(item) == GRAPH_KIND:
            font = item.font(0)
            is_main = item_id(item) == self._main_graph_id
            font.setBold(is_main)
            item.setFont(0, font)
            if is_main:
                item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
                item.setToolTip(0, tr("project.main_graph_tip"))
            else:
                decorate_item(self, item)
        for index in range(item.childCount()):
            self._mark_main_recursive(item.child(index))
