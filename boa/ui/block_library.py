from collections import defaultdict

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QAbstractItemView, QLineEdit, QMenu, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from boa.core.models import BLOCK_DEFINITIONS, BlockDefinition
from boa.core.module_registry import FEATURED_MODULE_KEYS, MODULE_CATEGORIES, MODULE_ORDER
from boa.i18n import tr
from boa.ui.block_shortcuts import block_shortcut_store

BOA_BLOCK_MIME = "application/x-boa-block-key"


class LibraryTree(QTreeWidget):
    def startDrag(self, supported_actions) -> None:
        item = self.currentItem()
        key = item.data(0, Qt.ItemDataRole.UserRole) if item else ""
        if not key: return
        mime = QMimeData(); mime.setData(BOA_BLOCK_MIME, str(key).encode("utf-8"))
        drag = QDrag(self); drag.setMimeData(mime); drag.exec(Qt.DropAction.CopyAction)


class BlockLibrary(QWidget):
    block_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._document_kind = "graph"
        self.search = QLineEdit(); self.search.setPlaceholderText(tr("library.search"))
        self.tree = LibraryTree(); self.tree.setHeaderHidden(True); self.tree.setDragEnabled(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.add_button = QPushButton(tr("library.add_selected"))
        self._items: list[tuple[QTreeWidgetItem, BlockDefinition]] = []
        self._shortcut_store = block_shortcut_store()
        self._populate()
        self.search.textChanged.connect(self._filter); self.tree.itemDoubleClicked.connect(self._on_item_activated)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self._shortcut_store.changed.connect(self._refresh_favorite_markers)
        self.add_button.clicked.connect(self._add_selected)
        layout = QVBoxLayout(self); layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.search); layout.addWidget(self.tree); layout.addWidget(self.add_button)

    def retranslate_ui(self) -> None:
        self.search.setPlaceholderText(tr("library.search")); self.add_button.setText(tr("library.add_selected"))
        self.tree.clear(); self._items.clear(); self._populate()

    def set_document_kind(self, kind: str) -> None:
        kind = kind if kind in {"function", "class"} else "graph"
        if kind == self._document_kind: return
        self._document_kind = kind; self.tree.clear(); self._items.clear(); self._populate()

    def _populate(self) -> None:
        categories: dict[str, list[BlockDefinition]] = defaultdict(list)
        special = {"def_input", "def_input_p", "def_output", "def_output_p", "return"}
        for definition in BLOCK_DEFINITIONS:
            if self._document_kind != "function" and definition.key in special: continue
            if definition.key == "class_attribute" and self._document_kind != "class": continue
            if self._document_kind in {"function", "class"} and definition.key == "run": continue
            if self._document_kind == "class" and definition.key in {"def_input", "def_input_p", "def_output", "def_output_p", "return"}: continue
            categories[definition.category].append(definition)
        module_categories = set(MODULE_CATEGORIES.values())
        for category, definitions in categories.items():
            if category in module_categories:
                continue
            category_item = self._group(self.tree, _category_label(category), True)
            for definition in definitions:
                self._add_definition(category_item, definition)
        self._add_modules(categories)

    def _add_modules(self, categories: dict[str, list[BlockDefinition]]) -> None:
        if not any(categories.get(name) for name in MODULE_CATEGORIES.values()):
            return
        modules = self._group(self.tree, tr("category.modules"), True)
        for module_key in MODULE_ORDER:
            category = MODULE_CATEGORIES[module_key]
            definitions = categories.get(category, [])
            if not definitions:
                continue
            module = self._group(modules, _category_label(category), module_key in {"math", "random"})
            if category == "Math":
                common = self._group(module, tr("category.common"), True)
                advanced = self._group(module, tr("category.advanced"), False)
                for definition in definitions:
                    parent = common if definition.key in FEATURED_MODULE_KEYS else advanced
                    self._add_definition(parent, definition)
            else:
                for definition in definitions:
                    self._add_definition(module, definition)

    def _group(self, parent, label: str, expanded: bool) -> QTreeWidgetItem:
        item = QTreeWidgetItem([label]); item.setExpanded(expanded)
        parent.addTopLevelItem(item) if parent is self.tree else parent.addChild(item)
        return item

    def _add_definition(self, parent: QTreeWidgetItem, definition: BlockDefinition) -> None:
        item = QTreeWidgetItem([self._definition_label(definition)])
        item.setData(0, Qt.ItemDataRole.UserRole, definition.key)
        item.setToolTip(0, _block_description(definition))
        parent.addChild(item); self._items.append((item, definition))

    def _definition_label(self, definition: BlockDefinition) -> str:
        marker = "★ " if self._shortcut_store.is_favorite(definition.key) else ""
        return marker + _block_title(definition)

    def _refresh_favorite_markers(self) -> None:
        for item, definition in self._items:
            item.setText(0, self._definition_label(definition))

    def _show_context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        block_key = str(item.data(0, Qt.ItemDataRole.UserRole)) if item else ""
        if not block_key:
            return
        menu = QMenu(self)
        label = "toolbar.remove_favorite" if self._shortcut_store.is_favorite(block_key) else "toolbar.add_favorite"
        toggle = menu.addAction(tr(label))
        if menu.exec(self.tree.viewport().mapToGlobal(pos)) == toggle:
            self._shortcut_store.toggle_favorite(block_key)

    def _filter(self, text: str) -> None:
        query = text.strip().lower()
        for item, definition in self._items:
            haystack = f"{_block_title(definition)} {_block_description(definition)}".lower()
            item.setHidden(query not in haystack)
        for idx in range(self.tree.topLevelItemCount()):
            self._refresh_group(self.tree.topLevelItem(idx), bool(query))

    def _refresh_group(self, item: QTreeWidgetItem, searching: bool) -> bool:
        visible = False
        for index in range(item.childCount()):
            child = item.child(index)
            child_visible = not child.isHidden() if child.data(0, Qt.ItemDataRole.UserRole) else self._refresh_group(child, searching)
            if not child.data(0, Qt.ItemDataRole.UserRole):
                child.setHidden(not child_visible)
            visible = visible or child_visible
        item.setHidden(not visible)
        if searching and visible:
            item.setExpanded(True)
        return visible

    def _on_item_activated(self, item: QTreeWidgetItem) -> None:
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if key: self.block_requested.emit(key)

    def _add_selected(self) -> None:
        item = self.tree.currentItem()
        if item is not None: self._on_item_activated(item)


def _category_label(category: str) -> str:
    mapping = {
        "Base": "category.base", "Sorties": "category.outputs", "Conditions": "category.conditions",
        "Logique": "category.logic", "Boucles": "category.loops", "Fonctions": "category.functions",
        "Valeurs": "category.values", "Opérateurs": "category.operators", "Math": "category.math",
        "Définition": "category.definition",
        "Random": "category.random", "DateTime": "category.datetime", "Path": "category.path",
        "System": "category.system", "JSON": "category.json", "CSV": "category.csv",
        "Collections": "category.collections", "Text": "category.text", "Types": "category.types",
        "Statistics": "category.statistics", "Security": "category.security", "Archive": "category.archive",
    }
    return tr(mapping.get(category, category))


def _block_title(definition: BlockDefinition) -> str:
    key = f"block.{definition.key}.title"
    title = tr(key)
    return definition.title if title == key else title


def _block_description(definition: BlockDefinition) -> str:
    key = f"block.{definition.key}.description"
    description = tr(key)
    return tr("tooltip.block.generic", name=_block_title(definition)) if description == key else description
