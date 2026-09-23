import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from boa.blocks.block_factory import apply_call_config
from boa.functions.blocks import apply_project_call
from boa.functions.models import function_parameters, function_returns
from boa.i18n import tr
from boa.ui.block_comment_dialog import apply_comment, comment_editor
from boa.ui.block_titles import retranslate_block
from boa.ui.value_input_dialog import VALUE_TYPES

_TARGET_RE = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$")
_NAME_RE = re.compile(r"^[A-Za-z_]\w*$")


def edit_call_block(
    block, functions: dict, parent=None, known_names: set[str] | None = None,
) -> tuple[bool, str, str, str]:
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("block.call.title"))
    dialog.resize(680, 600)
    form = QFormLayout(dialog)
    mode = QComboBox()
    mode.addItem(tr("call_dialog.project_function"), "project")
    mode.addItem(tr("call_dialog.python_function"), "python")
    mode.setCurrentIndex(max(0, mode.findData(str(getattr(block, "call_kind", "python")))))
    function_box = QComboBox()
    for function in sorted(functions.values(), key=lambda item: str(item.get("name", "")).lower()):
        function_box.addItem(function.get("name", "fonction"), function.get("id", ""))
    function_box.setCurrentIndex(max(0, function_box.findData(getattr(block, "function_id", ""))))
    target_edit = QLineEdit(str(getattr(block, "call_target", "math.sqrt") or "math.sqrt"))
    arg_count = QSpinBox()
    arg_count.setRange(0, 32)
    arg_count.setValue(int(getattr(block, "call_arg_count", 1) or 0))
    result_type = QComboBox()
    result_type.addItems(VALUE_TYPES)
    result_type.setCurrentText(str(getattr(block, "call_result_type", "any") or "any"))
    varargs = QCheckBox("Entrées automatiques *args")
    varargs.setChecked(int(getattr(block, "call_vararg_count", 0) or 0) > 0)
    kwargs = QCheckBox("Entrées automatiques **kwargs")
    kwargs.setChecked(bool(getattr(block, "call_kwarg_names", [])))
    keyword_editor = KeywordNamesEditor(list(getattr(block, "call_kwarg_names", [])))
    optional_inputs = QListWidget()
    optional_outputs = QListWidget()
    tabs = QTabWidget()
    tabs.addTab(optional_inputs, tr("function.parameters"))
    tabs.addTab(optional_outputs, tr("function.returns"))
    tabs.addTab(keyword_editor, "Noms **kwargs")
    open_button = QPushButton(tr("function.open"))
    comment_edit = comment_editor(getattr(block, "comment", ""))
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    function_label = QLabel(tr("call_dialog.function"))
    target_label = QLabel(tr("call_dialog.python_target"))
    arguments_label = QLabel(tr("call_dialog.arguments"))
    result_label = QLabel(tr("call_dialog.result_type"))
    form.addRow(tr("call_dialog.source"), mode)
    form.addRow(function_label, function_box)
    form.addRow(tabs)
    form.addRow(open_button)
    form.addRow(target_label, target_edit)
    form.addRow(arguments_label, arg_count)
    form.addRow(result_label, result_type)
    form.addRow(varargs)
    form.addRow(kwargs)
    form.addRow(tr("block_editor.comment"), comment_edit)
    form.addRow(buttons)
    open_requested = {"id": ""}

    def selected_function():
        return functions.get(str(function_box.currentData() or ""))

    def fill_optional(*_args):
        optional_inputs.clear()
        optional_outputs.clear()
        function = selected_function()
        if not function:
            return
        parameters = function_parameters(function)
        _fill(optional_inputs, [item for item in parameters if item.get("kind") == "normal"], set(getattr(block, "function_inputs", [])))
        _fill(optional_outputs, function_returns(function), set(getattr(block, "function_outputs", [])))
        has_args = any(item.get("kind") == "args" for item in parameters)
        has_kwargs = any(item.get("kind") == "kwargs" for item in parameters)
        varargs.setChecked(has_args)
        kwargs.setChecked(has_kwargs)
        varargs.setEnabled(False)
        kwargs.setEnabled(False)
        if has_kwargs and not keyword_editor.names():
            keyword_editor.set_names(["kwarg_1"])

    def refresh_mode(*_args):
        project = mode.currentData() == "project"
        for widget in (function_label, function_box, tabs, open_button):
            widget.setVisible(project)
        for widget in (target_label, target_edit, arguments_label, arg_count, result_label, result_type):
            widget.setVisible(not project)
        varargs.setEnabled(not project)
        kwargs.setEnabled(not project)
        keyword_editor.setVisible(kwargs.isChecked())
        if project:
            fill_optional()

    def request_open(*_args):
        function = selected_function()
        if function:
            open_requested["id"] = function["id"]
            dialog.accept()

    function_box.currentIndexChanged.connect(fill_optional)
    mode.currentIndexChanged.connect(refresh_mode)
    kwargs.toggled.connect(keyword_editor.setVisible)
    open_button.clicked.connect(request_open)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    fill_optional()
    refresh_mode()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False, "", "", ""
    if kwargs.isChecked() and not keyword_editor.valid():
        QMessageBox.warning(parent, tr("block.call.title"), "Chaque kwarg doit être un nom Python valide et unique.")
        return False, "", "", ""
    apply_comment(block, comment_edit)
    names = keyword_editor.names() if kwargs.isChecked() else []
    if kwargs.isChecked() and not names:
        names = ["kwarg_1"]
    if mode.currentData() == "project":
        function = selected_function()
        if not function:
            QMessageBox.warning(parent, tr("block.call.title"), tr("call_dialog.no_project_function"))
            return False, "", "", ""
        block.call_vararg_count = max(1, int(getattr(block, "call_vararg_count", 1) or 1)) if varargs.isChecked() else 0
        block.call_kwarg_names = names
        apply_project_call(block, function, {"visible_inputs": _checked(optional_inputs), "visible_outputs": _checked(optional_outputs)})
        retranslate_block(block)
        return True, "", "", open_requested["id"]
    target = target_edit.text().strip()
    if not _TARGET_RE.match(target):
        QMessageBox.warning(parent, tr("block.call.title"), tr("call_dialog.invalid"))
        return False, "", "", ""
    apply_call_config(block, target, arg_count.value(), result_type.currentText(), 1 if varargs.isChecked() else 0, names)
    block.call_kind = "python"
    block.function_id = ""
    retranslate_block(block)
    module = _root_module(target)
    if module in set(known_names or ()):
        return True, "", "", ""
    return True, module, f"import {module}" if "." in target else "", ""


class KeywordNamesEditor(QWidget):
    def __init__(self, names: list[str]) -> None:
        super().__init__()
        self.list = QListWidget()
        self.list.setEditTriggers(QListWidget.EditTrigger.DoubleClicked | QListWidget.EditTrigger.EditKeyPressed)
        add = QPushButton("Ajouter")
        delete = QPushButton("Supprimer")
        row = QHBoxLayout()
        row.addWidget(add)
        row.addWidget(delete)
        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addLayout(row)
        add.clicked.connect(self._add)
        delete.clicked.connect(self._delete)
        self.set_names(names)

    def set_names(self, names: list[str]) -> None:
        self.list.clear()
        for index, name in enumerate(names):
            self._append(str(name).strip() or f"kwarg_{index + 1}")

    def names(self) -> list[str]:
        return [self.list.item(index).text().strip() for index in range(self.list.count())]

    def valid(self) -> bool:
        names = self.names()
        return len(names) == len(set(names)) and all(_NAME_RE.match(name) for name in names)

    def _append(self, name: str) -> None:
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.list.addItem(item)

    def _add(self) -> None:
        self._append(f"kwarg_{self.list.count() + 1}")

    def _delete(self) -> None:
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)


def _fill(widget: QListWidget, ports: list[dict], selected: set[str]) -> None:
    for port in ports:
        if port["persistent"] or port["required"]:
            continue
        item = QListWidgetItem(f"{port['name']} : {port['type']}")
        item.setData(Qt.ItemDataRole.UserRole, port["id"])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if port["id"] in selected else Qt.CheckState.Unchecked)
        widget.addItem(item)


def _checked(widget: QListWidget) -> list[str]:
    return [str(widget.item(index).data(Qt.ItemDataRole.UserRole)) for index in range(widget.count()) if widget.item(index).checkState() == Qt.CheckState.Checked]


def _root_module(target: str) -> str:
    return target.split(".", 1)[0] if "." in target else ""
