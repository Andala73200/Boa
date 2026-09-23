from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox

from boa.ui.block_comment_dialog import add_comment_row, apply_comment
from boa.ui.block_titles import retranslate_block
from boa.i18n import tr

VALUE_TYPES = ["any", "int", "float", "str", "bool", "bytes", "list", "dict", "tuple", "set"]


def edit_value_block(block, parent=None) -> bool:
    dialog, form = _dialog(parent, "VALUE")
    type_combo = _type_combo(getattr(block, "value_type", "any"))
    value_edit = QLineEdit(str(getattr(block, "value_value", block.subtitle)))
    form.addRow(tr("value_dialog.type"), type_combo); form.addRow(tr("value_dialog.value"), value_edit)
    comment_edit = add_comment_row(form, block); form.addRow(_buttons(dialog))
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    value_type = type_combo.currentText(); value = value_edit.text()
    if not _valid(value_type, value):
        QMessageBox.warning(parent, tr("block.value.title"), tr("value_dialog.incompatible"))
        return False
    block.value_type = value_type; block.value_value = value; block.subtitle = value
    apply_comment(block, comment_edit); retranslate_block(block)
    _set_port_type(block, "value", value_type); block.update(); _refresh(block)
    return True


def edit_input_block(block, parent=None) -> bool:
    dialog, form = _dialog(parent, "INPUT")
    prompt_edit = QLineEdit(str(getattr(block, "input_prompt", block.subtitle)))
    type_combo = _type_combo(getattr(block, "input_type", "str"))
    default_edit = QLineEdit(str(getattr(block, "input_default", "")))
    form.addRow(tr("input_dialog.prompt"), prompt_edit); form.addRow(tr("value_dialog.type"), type_combo); form.addRow(tr("input_dialog.default"), default_edit)
    comment_edit = add_comment_row(form, block); form.addRow(_buttons(dialog))
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    value_type = type_combo.currentText(); default = default_edit.text()
    if default and not _valid(value_type, default):
        QMessageBox.warning(parent, tr("block.input.title"), tr("input_dialog.incompatible"))
        return False
    block.input_prompt = prompt_edit.text().strip() or tr("input_dialog.default_prompt"); block.input_type = value_type; block.input_default = default
    block.subtitle = block.input_prompt; apply_comment(block, comment_edit); retranslate_block(block)
    _set_port_type(block, "value", value_type); block.update(); _refresh(block)
    return True


def _dialog(parent, title: str):
    dialog = QDialog(parent); dialog.setWindowTitle(title)
    form = QFormLayout(dialog)
    return dialog, form


def _buttons(dialog: QDialog) -> QDialogButtonBox:
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
    return buttons


def _type_combo(selected: str) -> QComboBox:
    combo = QComboBox(); combo.addItems(VALUE_TYPES)
    combo.setCurrentText(selected if selected in VALUE_TYPES else "any")
    return combo


def _set_port_type(block, port_key: str, value_type: str) -> None:
    port = block.port_definition(port_key)
    if port: port.value_type = value_type


def _refresh(block) -> None:
    for connection in list(block.connections): connection.update_path()


def _valid(value_type: str, value: str) -> bool:
    if value_type in {"any", "str", "bytes"}: return True
    if value_type == "bool": return value.strip().lower() in {"true", "false", "1", "0", "oui", "non", "vrai", "faux"}
    try:
        if value_type == "int": int(value)
        elif value_type == "float": float(value)
        elif value_type in {"list", "dict", "tuple", "set"}: __import__("ast").literal_eval(value)
        else: return True
    except Exception:
        return False
    return True
