from __future__ import annotations

from math import ceil

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)

from boa.ui.collapsible_panel import CollapsiblePanel
from boa.ui.graph_view import GraphView


VARIABLE_TYPES = ["any", "int", "float", "str", "bool", "list", "dict", "tuple", "set"]


class DefinitionEditor(QWidget):
    changed = Signal()

    def __init__(self, kind: str, uid: str, graph_view: GraphView, parent=None) -> None:
        super().__init__(parent)
        self.document_kind = kind
        self.document_id = uid
        self.graph_view = graph_view
        self._external_entries_provider = graph_view.variable_entries_provider

        self.docstring = QPlainTextEdit()
        self.docstring.setPlaceholderText("Documentation Python de la définition…")
        self.docstring.setMaximumHeight(88)
        self.imports = ImportListEditor()
        self.variables = VariableGridEditor()

        tabs = QTabWidget()
        tabs.addTab(self.imports, "Imports")
        tabs.addTab(self.variables, "Variables")

        metadata = QWidget()
        metadata_layout = QVBoxLayout(metadata)
        metadata_layout.setContentsMargins(6, 4, 6, 6)
        metadata_layout.setSpacing(4)
        metadata_layout.addWidget(QLabel("Docstring"))
        metadata_layout.addWidget(self.docstring)
        metadata_layout.addWidget(tabs)

        title = "Documentation et imports de la fonction" if kind == "function" else "Documentation et imports de la classe"
        self.metadata_panel = CollapsiblePanel(title, metadata, "top")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.metadata_panel)
        layout.addWidget(graph_view, 1)

        self.docstring.textChanged.connect(self.changed.emit)
        self.imports.changed.connect(self.changed.emit)
        self.variables.changed.connect(self.changed.emit)
        graph_view.variable_entries_provider = self._all_variable_entries
        graph_view.variable_names_provider = lambda: {item["name"].lower() for item in self._all_variable_entries() if item.get("name")}

        # Definitions and classes open with their metadata taking the minimum space.
        self.metadata_panel.set_collapsed(True)

    def set_metadata(self, definition: dict) -> None:
        self.docstring.blockSignals(True)
        self.docstring.setPlainText(str(definition.get("docstring", "")))
        self.docstring.blockSignals(False)
        self.imports.set_entries(list(definition.get("imports", [])))
        self.variables.set_entries(list(definition.get("variables", [])))

    def metadata(self) -> dict:
        return {
            "docstring": self.docstring.toPlainText(),
            "imports": self.imports.entries(),
            "variables": self.variables.entries(),
        }

    def _all_variable_entries(self) -> list[dict]:
        local = self.variables.entries()
        external = self._external_entries_provider() if callable(self._external_entries_provider) else []
        names = {str(item.get("name", "")).casefold() for item in local}
        return [*local, *(item for item in external if str(item.get("name", "")).casefold() not in names)]

    def to_data(self) -> dict:
        return self.graph_view.to_data()

    def from_data(self, data: dict) -> None:
        self.graph_view.from_data(data)

    def add_block(self, key: str) -> None:
        self.graph_view.add_block(key)

    def has_selection(self) -> bool:
        return self.graph_view.has_selection()

    def copy_selected_blocks(self) -> int:
        return self.graph_view.copy_selected_blocks()

    def cut_selected_blocks(self) -> int:
        return self.graph_view.cut_selected_blocks()

    def paste_blocks(self) -> int:
        return self.graph_view.paste_blocks()

    def select_all_blocks(self) -> int:
        return self.graph_view.select_all_blocks()

    def delete_selected_items(self) -> int:
        return self.graph_view.delete_selected_items()

    def centerOn(self, *args) -> None:
        self.graph_view.centerOn(*args)


class VariableGridEditor(QWidget):
    """Compact, responsive variable editor filled vertically by column."""

    changed = Signal()
    CARD_GAP = 6

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[VariableRow] = []
        self._reflow_pending = False

        add = QPushButton("Ajouter")
        add.clicked.connect(self._add_default)
        buttons = QHBoxLayout()
        buttons.addWidget(add)
        buttons.addStretch()

        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(2, 2, 2, 2)
        self.grid.setHorizontalSpacing(self.CARD_GAP)
        self.grid.setVerticalSpacing(4)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidget(self.container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(buttons)
        layout.addWidget(self.scroll)

    def set_entries(self, entries: list[dict]) -> None:
        for row in self._rows:
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()
        for entry in entries:
            self._append_row(entry, emit=False)
        self._schedule_reflow()

    def entries(self) -> list[dict]:
        return [row.entry() for row in self._rows if row.name.text().strip()]

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._schedule_reflow()

    def _add_default(self) -> None:
        used = {row.name.text().strip().casefold() for row in self._rows}
        index = 1
        name = f"variable_{index}"
        while name.casefold() in used:
            index += 1
            name = f"variable_{index}"
        self._append_row({"name": name, "type": "any", "initial": "", "constant": False, "scope": "local"})

    def _append_row(self, entry: dict, emit: bool = True) -> None:
        row = VariableRow(entry, self.container)
        row.changed.connect(self._row_changed)
        row.delete_requested.connect(lambda current=row: self._delete_row(current))
        self._rows.append(row)
        self._schedule_reflow()
        if emit:
            self.changed.emit()

    def _delete_row(self, row: "VariableRow") -> None:
        if row not in self._rows:
            return
        self._rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        self._schedule_reflow()
        self.changed.emit()

    def _row_changed(self) -> None:
        self._schedule_reflow()
        self.changed.emit()

    def _schedule_reflow(self) -> None:
        if self._reflow_pending:
            return
        self._reflow_pending = True
        QTimer.singleShot(0, self._reflow)

    def _reflow(self) -> None:
        self._reflow_pending = False
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().hide()
        if not self._rows:
            return

        available = max(1, self.scroll.viewport().width() - 8)
        card_width = max(row.minimum_card_width() for row in self._rows)
        columns = max(1, (available + self.CARD_GAP) // (card_width + self.CARD_GAP))
        while columns > 1 and columns * card_width + (columns - 1) * self.CARD_GAP > available:
            columns -= 1

        rows_per_column = max(1, ceil(len(self._rows) / columns))
        for index, row in enumerate(self._rows):
            column = index // rows_per_column
            line = index % rows_per_column
            row.setMinimumWidth(card_width)
            row.show()
            self.grid.addWidget(row, line, column)
        for column in range(columns):
            self.grid.setColumnStretch(column, 1)


class VariableRow(QFrame):
    changed = Signal()
    delete_requested = Signal()

    def __init__(self, entry: dict, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("definitionVariableRow")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.name = QLineEdit(str(entry.get("name", "")))
        self.name.setToolTip("Nom de la variable")
        self.name.setStyleSheet(
            "QLineEdit { background-color: rgba(255,255,255,24); border: 1px solid rgba(255,255,255,45); padding: 2px 5px; }"
        )
        self.type = QComboBox()
        self.type.addItems(VARIABLE_TYPES)
        self.type.setCurrentText(str(entry.get("type", "any")) if str(entry.get("type", "any")) in VARIABLE_TYPES else "any")
        self.type.setMaximumWidth(76)
        self.initial = QLineEdit(str(entry.get("initial", "")))
        self.initial.setPlaceholderText("initiale")
        self.initial.setMaximumWidth(110)
        self.constant = QCheckBox("C")
        self.constant.setChecked(bool(entry.get("constant", False)))
        self.scope = QLabel(str(entry.get("scope", "local")))
        self.scope.setMinimumWidth(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(4)
        layout.addWidget(self.name)
        layout.addWidget(self.type)
        layout.addWidget(self.initial)
        layout.addWidget(self.constant)
        layout.addWidget(self.scope)

        self.name.textChanged.connect(self._name_changed)
        self.type.currentTextChanged.connect(self.changed.emit)
        self.initial.textChanged.connect(self.changed.emit)
        self.constant.stateChanged.connect(self.changed.emit)
        self._install_context_menu(self)
        for widget in (self.name, self.type, self.initial, self.constant, self.scope):
            self._install_context_menu(widget)
        self._update_name_width()

    def entry(self) -> dict:
        return {
            "name": self.name.text().strip(),
            "type": self.type.currentText(),
            "initial": self.initial.text(),
            "constant": self.constant.isChecked(),
            "scope": self.scope.text() or "local",
        }

    def minimum_card_width(self) -> int:
        name_width = QFontMetrics(self.name.font()).horizontalAdvance(self.name.text() or "variable") + 28
        return max(320, name_width + 238)

    def _name_changed(self) -> None:
        self._update_name_width()
        self.changed.emit()

    def _update_name_width(self) -> None:
        width = QFontMetrics(self.name.font()).horizontalAdvance(self.name.text() or "variable") + 28
        self.name.setMinimumWidth(max(92, width))

    def _install_context_menu(self, widget: QWidget) -> None:
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(lambda pos, source=widget: self._show_context_menu(source, pos))

    def _show_context_menu(self, source: QWidget, pos) -> None:
        menu = source.createStandardContextMenu() if isinstance(source, QLineEdit) else QMenu(self)
        if menu.actions():
            menu.addSeparator()
        delete_action = menu.addAction("Supprimer la variable")
        action = menu.exec(source.mapToGlobal(pos))
        if action == delete_action:
            self.delete_requested.emit()


class ImportListEditor(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        add = QPushButton("Ajouter")
        edit = QPushButton("Modifier")
        delete = QPushButton("Supprimer")
        buttons = QHBoxLayout()
        buttons.addWidget(add)
        buttons.addWidget(edit)
        buttons.addWidget(delete)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.list)
        layout.addLayout(buttons)
        add.clicked.connect(self._add)
        edit.clicked.connect(self._edit)
        delete.clicked.connect(self._delete)
        self.list.itemDoubleClicked.connect(lambda *_: self._edit())

    def set_entries(self, entries: list[dict]) -> None:
        self.list.clear()
        for entry in entries:
            statement = str(entry.get("statement", "")).strip()
            if statement:
                self.list.addItem(statement)

    def entries(self) -> list[dict]:
        return [
            {"module": _root_module(self.list.item(index).text()), "statement": self.list.item(index).text(), "origin": "définition"}
            for index in range(self.list.count())
        ]

    def _add(self) -> None:
        statement, ok = QInputDialog.getText(self, "Ajouter un import", "Instruction Python :", text="import ")
        if ok and self._valid(statement):
            self.list.addItem(statement.strip())
            self.changed.emit()

    def _edit(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        statement, ok = QInputDialog.getText(self, "Modifier l’import", "Instruction Python :", text=item.text())
        if ok and self._valid(statement):
            item.setText(statement.strip())
            self.changed.emit()

    def _delete(self) -> None:
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)
            self.changed.emit()

    def _valid(self, statement: str) -> bool:
        text = statement.strip()
        try:
            code = compile(text, "<import>", "exec")
        except SyntaxError as error:
            QMessageBox.warning(self, "Import invalide", str(error))
            return False
        if not text.startswith(("import ", "from ")) or len(code.co_names) == 0:
            QMessageBox.warning(self, "Import invalide", "Utilise une instruction import … ou from … import …")
            return False
        return True


def _root_module(statement: str) -> str:
    text = statement.strip()
    if text.startswith("import "):
        return text[7:].split(",", 1)[0].split(" as ", 1)[0].split(".", 1)[0].strip()
    if text.startswith("from "):
        return text[5:].split(" import ", 1)[0].split(".", 1)[0].strip()
    return ""
