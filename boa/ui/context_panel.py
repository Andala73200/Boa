from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from boa.i18n import tr
from boa.ui.import_dialog import ask_import
from boa.ui.variable_dialog import VariableDialog
VARIABLE_TYPES = ["any", "int", "float", "str", "bool", "list", "dict", "tuple", "set"]
class ManagedTable(QTableWidget):
    delete_pressed = Signal()
    rename_pressed = Signal()
    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete:
            self.delete_pressed.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_F2:
            self.rename_pressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)
class ContextPanel(QWidget):
    context_changed = Signal()
    variable_block_requested = Signal(str, str, bool)
    variable_renamed = Signal(str, str)
    variable_definition_changed = Signal(str, str, bool)
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._loading = False
        self.import_table = self._build_import_table()
        self.variable_table = self._build_variable_table()
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_import_tab(), tr("context.imports"))
        self.tabs.addTab(self._build_variable_tab(), tr("context.variables"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.tabs)
    def retranslate_ui(self) -> None:
        self.tabs.setTabText(0, tr("context.imports"))
        self.tabs.setTabText(1, tr("context.variables"))
        self.import_table.setHorizontalHeaderLabels([tr("context.module"), tr("context.import"), tr("context.origin")])
        self.variable_table.setHorizontalHeaderLabels([tr("context.name"), tr("context.type"), tr("context.initial"), tr("context.constant"), tr("context.scope")])
        self.delete_import_button.setText(tr("context.delete"))
        self.delete_variable_button.setText(tr("context.delete"))
        self.add_import_button.setToolTip(tr("context.add_import"))
        self.delete_import_button.setToolTip(tr("context.delete_import"))
        self.add_variable_button.setToolTip(tr("context.add_variable"))
        self.delete_variable_button.setToolTip(tr("context.delete_variable"))
    def to_data(self) -> dict:
        return {"imports": self._imports_to_data(), "variables": self._variables_to_data()}
    def from_data(self, data: dict) -> None:
        self._loading = True
        self.import_table.setRowCount(0)
        self.variable_table.setRowCount(0)
        for item in data.get("imports", []):
            self.add_import(item.get("module", ""), item.get("statement", ""), item.get("origin", "manuel"), item.get("source", ""))
        for item in data.get("variables", []):
            self.add_variable(item.get("name", ""), item.get("type", "any"), item.get("initial", ""), bool(item.get("constant", False)), item.get("scope", "global"))
        self._loading = False
    def add_import(self, module: str, statement: str | None = None, origin: str = "auto", source: str = "") -> None:
        module = module.strip()
        statement = (statement or f"import {module}").strip()
        if not module or self._import_exists(statement):
            return
        was_loading = self._loading
        self._loading = True
        row = self.import_table.rowCount()
        self.import_table.insertRow(row)
        for col, value in enumerate([module, statement, origin]):
            item = QTableWidgetItem(value)
            if col == 2 and source: item.setData(Qt.ItemDataRole.UserRole, source)
            self.import_table.setItem(row, col, item)
        self._loading = was_loading
        if not was_loading:
            self._emit_changed()
    def add_variable(self, name: str, var_type: str = "any", initial_value: str = "", is_constant: bool = False, scope: str = "global") -> None:
        name = name.strip()
        if not name or self._variable_exists(name):
            return
        was_loading = self._loading
        self._loading = True
        row = self.variable_table.rowCount()
        self.variable_table.insertRow(row)
        name_item = QTableWidgetItem(name)
        name_item.setData(Qt.ItemDataRole.UserRole, name)
        self.variable_table.setItem(row, 0, name_item)
        self.variable_table.setCellWidget(row, 1, self._type_combo(var_type))
        self.variable_table.setCellWidget(row, 2, self._value_edit(initial_value))
        self.variable_table.setCellWidget(row, 3, self._constant_check(is_constant))
        self.variable_table.setItem(row, 4, QTableWidgetItem(scope))
        self._loading = was_loading
        self._emit_variable_definition(row)
        if not was_loading:
            self._emit_changed()
    def remove_selected_imports(self) -> int:
        count = self._remove_selected_rows(self.import_table)
        if count:
            self._emit_changed()
        return count
    def remove_selected_variables(self) -> int:
        count = self._remove_selected_rows(self.variable_table)
        if count:
            self._emit_changed()
        return count
    def rename_selected_variable(self) -> None:
        row = self.variable_table.currentRow()
        if row >= 0 and self.variable_table.item(row, 0):
            self.variable_table.editItem(self.variable_table.item(row, 0))
    def _build_import_table(self) -> ManagedTable:
        table = ManagedTable(0, 3)
        table.setHorizontalHeaderLabels([tr("context.module"), tr("context.import"), tr("context.origin")])
        self._configure_table(table)
        table.delete_pressed.connect(self.remove_selected_imports)
        table.itemChanged.connect(lambda item: self._emit_changed())
        table.customContextMenuRequested.connect(self._show_import_menu)
        return table
    def _build_variable_table(self) -> ManagedTable:
        table = ManagedTable(0, 5)
        table.setHorizontalHeaderLabels([tr("context.name"), tr("context.type"), tr("context.initial"), tr("context.constant"), tr("context.scope")])
        self._configure_table(table)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.delete_pressed.connect(self.remove_selected_variables)
        table.rename_pressed.connect(self.rename_selected_variable)
        table.cellDoubleClicked.connect(self._add_variable_block_from_row)
        table.itemChanged.connect(self._variable_item_changed)
        table.customContextMenuRequested.connect(self._show_variable_menu)
        return table
    def _configure_table(self, table: ManagedTable) -> None:
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    def _build_import_tab(self) -> QWidget:
        widget = QWidget()
        self.add_import_button = QPushButton("+")
        self.delete_import_button = QPushButton(tr("context.delete"))
        self.add_import_button.setToolTip(tr("context.add_import"))
        self.delete_import_button.setToolTip(tr("context.delete_import"))
        self.add_import_button.clicked.connect(self._open_import_dialog)
        self.delete_import_button.clicked.connect(self.remove_selected_imports)
        return self._tab_with_buttons(widget, self.add_import_button, self.delete_import_button, self.import_table)
    def _build_variable_tab(self) -> QWidget:
        widget = QWidget()
        self.add_variable_button = QPushButton("+")
        self.delete_variable_button = QPushButton(tr("context.delete"))
        self.add_variable_button.setToolTip(tr("context.add_variable"))
        self.delete_variable_button.setToolTip(tr("context.delete_variable"))
        self.add_variable_button.clicked.connect(self._open_variable_dialog)
        self.delete_variable_button.clicked.connect(self.remove_selected_variables)
        return self._tab_with_buttons(widget, self.add_variable_button, self.delete_variable_button, self.variable_table)
    def _tab_with_buttons(self, widget: QWidget, add_button: QPushButton, delete_button: QPushButton, table) -> QWidget:
        button_row = QHBoxLayout()
        button_row.addWidget(add_button)
        button_row.addWidget(delete_button)
        button_row.addStretch()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(button_row)
        layout.addWidget(table)
        return widget
    def _open_import_dialog(self) -> None:
        item = ask_import(self)
        if item: self.add_import(item["module"], item["statement"], item["origin"])

    def _open_variable_dialog(self) -> None:
        dialog = VariableDialog(self._variable_names(), self)
        dialog.exec()
        for item in dialog.created_variables():
            self.add_variable(item["name"], item["type"], item["initial"], item["constant"], item["scope"])
    def _add_variable_block_from_row(self, row: int, column: int) -> None:
        name = self._item_text(self.variable_table, row, 0).strip()
        if name:
            self.variable_block_requested.emit(name, self._variable_type(row), self._variable_constant(row))
    def _show_import_menu(self, pos) -> None:
        if not self.import_table.indexAt(pos).isValid():
            return
        menu = QMenu(self)
        delete_action = menu.addAction(tr("context.delete"))
        if menu.exec(self.import_table.viewport().mapToGlobal(pos)) == delete_action:
            self.remove_selected_imports()
    def _show_variable_menu(self, pos) -> None:
        index = self.variable_table.indexAt(pos)
        if not index.isValid():
            return
        self.variable_table.selectRow(index.row())
        menu = QMenu(self)
        rename_action = menu.addAction(tr("context.rename"))
        delete_action = menu.addAction(tr("context.delete"))
        action = menu.exec(self.variable_table.viewport().mapToGlobal(pos))
        if action == rename_action:
            self.rename_selected_variable()
        elif action == delete_action:
            self.remove_selected_variables()
    def _imports_to_data(self) -> list[dict]:
        rows = []
        for row in range(self.import_table.rowCount()):
            item = {"module": self._item_text(self.import_table, row, 0), "statement": self._item_text(self.import_table, row, 1), "origin": self._item_text(self.import_table, row, 2)}
            source = self.import_table.item(row, 2).data(Qt.ItemDataRole.UserRole) if self.import_table.item(row, 2) else ""
            if source: item["source"] = source
            rows.append(item)
        return rows
    def _variables_to_data(self) -> list[dict]:
        rows = []
        for row in range(self.variable_table.rowCount()):
            name = self._item_text(self.variable_table, row, 0).strip()
            if not name:
                continue
            value_widget = self.variable_table.cellWidget(row, 2)
            rows.append({
                "name": name,
                "type": self._variable_type(row),
                "initial": value_widget.text() if isinstance(value_widget, QLineEdit) else "",
                "constant": self._variable_constant(row),
                "scope": self._item_text(self.variable_table, row, 4) or "global",
            })
        return rows
    def _variable_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        if item.column() == 0:
            old_name = str(item.data(Qt.ItemDataRole.UserRole) or "")
            new_name = item.text().strip()
            if old_name and new_name and old_name != new_name:
                item.setData(Qt.ItemDataRole.UserRole, new_name)
                self.variable_renamed.emit(old_name, new_name)
                self._emit_variable_definition(item.row())
        self._emit_changed()
    def _emit_variable_definition(self, row: int) -> None:
        if self._loading or row < 0:
            return
        name = self._item_text(self.variable_table, row, 0).strip()
        if name:
            self.variable_definition_changed.emit(name, self._variable_type(row), self._variable_constant(row))
    def _variable_type(self, row: int) -> str:
        type_widget = self.variable_table.cellWidget(row, 1)
        return type_widget.currentText() if isinstance(type_widget, QComboBox) else "any"
    def _variable_constant(self, row: int) -> bool:
        widget = self.variable_table.cellWidget(row, 3)
        return widget.isChecked() if isinstance(widget, QCheckBox) else False
    def _remove_selected_rows(self, table: QTableWidget) -> int:
        rows = {index.row() for index in table.selectedIndexes()}
        if not rows and table.currentRow() >= 0:
            rows.add(table.currentRow())
        for row in sorted(rows, reverse=True):
            table.removeRow(row)
        return len(rows)
    def _type_combo(self, selected: str) -> QComboBox:
        combo = QComboBox()
        combo.addItems(VARIABLE_TYPES)
        combo.setCurrentText(selected if selected in VARIABLE_TYPES else "any")
        combo.currentTextChanged.connect(lambda text, widget=combo: self._widget_definition_changed(widget))
        return combo
    def _value_edit(self, value: str) -> QLineEdit:
        edit = QLineEdit(value)
        edit.textChanged.connect(lambda text: self._emit_changed())
        return edit
    def _constant_check(self, checked: bool) -> QCheckBox:
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.stateChanged.connect(lambda state, widget=checkbox: self._widget_definition_changed(widget))
        return checkbox
    def _widget_definition_changed(self, widget) -> None:
        self._emit_variable_definition(self._row_for_widget(widget))
        self._emit_changed()
    def _row_for_widget(self, widget) -> int:
        for row in range(self.variable_table.rowCount()):
            for col in range(self.variable_table.columnCount()):
                if self.variable_table.cellWidget(row, col) is widget:
                    return row
        return -1
    def _emit_changed(self) -> None:
        if not self._loading:
            self.context_changed.emit()
    def _item_text(self, table: QTableWidget, row: int, col: int) -> str:
        item = table.item(row, col)
        return item.text() if item else ""
    def _import_exists(self, statement: str) -> bool:
        return any(self._item_text(self.import_table, row, 1).strip() == statement for row in range(self.import_table.rowCount()))
    def _variable_exists(self, name: str) -> bool:
        return name.lower() in self._variable_names()
    def _variable_names(self) -> set[str]:
        return {self._item_text(self.variable_table, row, 0).lower() for row in range(self.variable_table.rowCount())}
