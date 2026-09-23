from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from boa.blocks.python_native_blocks import (
    apply_class_attribute, apply_match_cases, apply_multi_assign,
    apply_return_values, apply_try_config, apply_with_config,
)


def edit_attribute_get(block, parent=None) -> bool:
    text, ok = QInputDialog.getText(parent, "Accès attribut", "Nom de l’attribut :", text=str(getattr(block, "attribute_name", "attribut")))
    if not ok:
        return False
    name = text.strip()
    if not name.isidentifier():
        QMessageBox.warning(parent, "Accès attribut", "Le nom doit être un identifiant Python valide.")
        return False
    block.attribute_name = name
    block.subtitle = name
    block.update()
    return True


def edit_class_attribute(block, parent=None) -> bool:
    dialog = QDialog(parent); dialog.setWindowTitle("Attribut")
    form = QFormLayout(dialog)
    name = QLineEdit(str(getattr(block, "attribute_name", "attribut")))
    annotation = QLineEdit(str(getattr(block, "attribute_annotation", "")))
    default = QCheckBox("Valeur par défaut")
    default.setChecked(bool(getattr(block, "attribute_has_default", False)))
    form.addRow("Nom", name); form.addRow("Type / annotation", annotation); form.addRow(default)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); form.addRow(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    if not name.text().strip().isidentifier():
        QMessageBox.warning(parent, "Attribut", "Le nom doit être un identifiant Python valide.")
        return False
    apply_class_attribute(block, name.text(), annotation.text(), default.isChecked())
    return True


def edit_return_block(block, parent=None) -> bool:
    values, accepted = _edit_ordered_names(
        parent, "Retour", list(getattr(block, "return_values", [])),
        "Ajouter une valeur retournée", allow_star=False,
    )
    if not accepted:
        return False
    apply_return_values(block, values)
    return True


def edit_multi_assign(block, parent=None) -> bool:
    values, accepted = _edit_ordered_names(
        parent, "Affectation multiple", list(getattr(block, "assign_targets", [])),
        "Ajouter une cible", allow_star=True,
    )
    if not accepted:
        return False
    apply_multi_assign(block, values)
    return True


def edit_try_block(block, parent=None) -> bool:
    dialog = QDialog(parent); dialog.setWindowTitle("Gestion d’exception"); dialog.resize(520, 330)
    layout = QVBoxLayout(dialog)
    table = QTableWidget(0, 2); table.setHorizontalHeaderLabels(["Exception", "Nom facultatif"])
    for handler in list(getattr(block, "try_handlers", [])):
        _append_row(table, [handler.get("type", ""), handler.get("name", "")])
    add = QPushButton("Ajouter except"); delete = QPushButton("Supprimer")
    row = QHBoxLayout(); row.addWidget(add); row.addWidget(delete)
    else_box = QCheckBox("Branche else"); else_box.setChecked(bool(getattr(block, "try_else_graph", {})))
    finally_box = QCheckBox("Branche finally"); finally_box.setChecked(bool(getattr(block, "try_finally_graph", {})))
    checks = QHBoxLayout(); checks.addWidget(else_box); checks.addWidget(finally_box)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    layout.addWidget(table); layout.addLayout(row); layout.addLayout(checks); layout.addWidget(buttons)
    add.clicked.connect(lambda: _append_row(table, ["Exception", ""]))
    delete.clicked.connect(lambda: _delete_row(table))
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    old = list(getattr(block, "try_handlers", [])); handlers = []
    for index in range(table.rowCount()):
        exception = _cell(table, index, 0).strip()
        name = _cell(table, index, 1).strip()
        graph = old[index].get("graph", {}) if index < len(old) else {}
        handlers.append({"type": exception, "name": name, "graph": graph})
    apply_try_config(block, handlers, else_box.isChecked(), finally_box.isChecked())
    return True


def edit_match_block(block, parent=None) -> bool:
    dialog = QDialog(parent); dialog.setWindowTitle("Correspondance"); dialog.resize(560, 350)
    layout = QVBoxLayout(dialog)
    table = QTableWidget(0, 2); table.setHorizontalHeaderLabels(["Case / motif", "Garde if facultative"])
    for case in list(getattr(block, "match_cases", [])):
        _append_row(table, [case.get("pattern", "_"), case.get("guard", "")])
    add = QPushButton("Ajouter un case"); delete = QPushButton("Supprimer")
    up = QPushButton("Monter"); down = QPushButton("Descendre")
    row = QHBoxLayout()
    for button in (add, delete, up, down): row.addWidget(button)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    layout.addWidget(table); layout.addLayout(row); layout.addWidget(buttons)
    add.clicked.connect(lambda: _append_row(table, ["_", ""]))
    delete.clicked.connect(lambda: _delete_row(table))
    up.clicked.connect(lambda: _move_table_row(table, -1)); down.clicked.connect(lambda: _move_table_row(table, 1))
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    old = list(getattr(block, "match_cases", [])); cases = []
    for index in range(table.rowCount()):
        pattern = _cell(table, index, 0).strip() or "_"
        guard = _cell(table, index, 1).strip()
        graph = old[index].get("graph", {}) if index < len(old) else {}
        cases.append({"pattern": pattern, "guard": guard, "graph": graph})
    apply_match_cases(block, cases)
    return True


def edit_with_block(block, parent=None) -> bool:
    dialog = QDialog(parent); dialog.setWindowTitle("Contexte (with)"); dialog.resize(430, 300)
    layout = QVBoxLayout(dialog)
    aliases = QListWidget(); aliases.setEditTriggers(QListWidget.EditTrigger.DoubleClicked | QListWidget.EditTrigger.EditKeyPressed)
    for item in list(getattr(block, "with_items", [])):
        aliases.addItem(str(item.get("alias", "")))
    add = QPushButton("Ajouter un contexte"); delete = QPushButton("Supprimer")
    row = QHBoxLayout(); row.addWidget(add); row.addWidget(delete)
    async_box = QCheckBox("async with"); async_box.setChecked(bool(getattr(block, "with_async", False)))
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    layout.addWidget(aliases); layout.addLayout(row); layout.addWidget(async_box); layout.addWidget(buttons)
    add.clicked.connect(lambda: aliases.addItem("")); delete.clicked.connect(lambda: aliases.takeItem(aliases.currentRow()) if aliases.currentRow() >= 0 else None)
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    items = [{"alias": aliases.item(index).text().strip()} for index in range(aliases.count())]
    apply_with_config(block, items, async_box.isChecked())
    return True


def _edit_ordered_names(parent, title: str, initial: list[str], add_label: str, allow_star: bool) -> tuple[list[str], bool]:
    dialog = QDialog(parent); dialog.setWindowTitle(title); dialog.resize(420, 330)
    layout = QVBoxLayout(dialog); widget = QListWidget()
    widget.setEditTriggers(QListWidget.EditTrigger.DoubleClicked | QListWidget.EditTrigger.EditKeyPressed)
    for value in initial: _append_name(widget, str(value))
    add = QPushButton("Ajouter"); delete = QPushButton("Supprimer"); up = QPushButton("Monter"); down = QPushButton("Descendre")
    row = QHBoxLayout()
    for button in (add, delete, up, down): row.addWidget(button)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    layout.addWidget(widget); layout.addLayout(row); layout.addWidget(buttons)
    add.clicked.connect(lambda: _append_name(widget, f"valeur_{widget.count() + 1}"))
    delete.clicked.connect(lambda: widget.takeItem(widget.currentRow()) if widget.currentRow() >= 0 else None)
    up.clicked.connect(lambda: _move_list_item(widget, -1)); down.clicked.connect(lambda: _move_list_item(widget, 1))
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return initial, False
    values = [widget.item(index).text().strip() for index in range(widget.count())]
    for value in values:
        candidate = value.lstrip("*") if allow_star else value
        if not candidate.isidentifier() or (not allow_star and value.startswith("*")):
            QMessageBox.warning(parent, title, "Chaque nom doit être un identifiant Python valide.")
            return initial, False
    if allow_star and sum(value.startswith("*") for value in values) > 1:
        QMessageBox.warning(parent, title, "Une seule cible peut commencer par *.")
        return initial, False
    return values, True


def _append_name(widget: QListWidget, value: str) -> None:
    item = QListWidgetItem(value); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable); widget.addItem(item)

def _move_list_item(widget: QListWidget, delta: int) -> None:
    row = widget.currentRow(); target = row + delta
    if row < 0 or target < 0 or target >= widget.count(): return
    item = widget.takeItem(row); widget.insertItem(target, item); widget.setCurrentRow(target)

def _append_row(table: QTableWidget, values: list[str]) -> None:
    row = table.rowCount(); table.insertRow(row)
    for column, value in enumerate(values): table.setItem(row, column, QTableWidgetItem(str(value)))

def _delete_row(table: QTableWidget) -> None:
    if table.currentRow() >= 0: table.removeRow(table.currentRow())

def _move_table_row(table: QTableWidget, delta: int) -> None:
    row = table.currentRow(); target = row + delta
    if row < 0 or target < 0 or target >= table.rowCount(): return
    values = [_cell(table, row, col) for col in range(table.columnCount())]
    table.removeRow(row); table.insertRow(target)
    for col, value in enumerate(values): table.setItem(target, col, QTableWidgetItem(value))
    table.setCurrentCell(target, 0)

def _cell(table: QTableWidget, row: int, column: int) -> str:
    item = table.item(row, column); return item.text() if item else ""
