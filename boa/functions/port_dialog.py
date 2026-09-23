from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QLineEdit, QMessageBox,
)

from boa.functions.blocks import apply_def_port_config
from boa.functions.models import INPUT_KEYS, VALUE_TYPES, valid_port_name
from boa.i18n import tr
from boa.ui.block_comment_dialog import apply_comment, comment_editor


PARAMETER_TYPES = [
    ("Entrée simple", "normal"),
    ("Arguments supplémentaires (*args)", "args"),
    ("Arguments nommés supplémentaires (**kwargs)", "kwargs"),
]


def edit_def_port_block(block, sibling_names: set[str], parent=None) -> bool:
    dialog = QDialog(parent)
    dialog.setWindowTitle(block.title)
    form = QFormLayout(dialog)
    name = QLineEdit(str(getattr(block, "def_port_name", "valeur")))
    value_type = QComboBox()
    value_type.addItems(VALUE_TYPES)
    value_type.setCurrentText(str(getattr(block, "def_port_type", "any")))
    is_input = block.block_key in INPUT_KEYS
    parameter_type = QComboBox()
    for label, value in PARAMETER_TYPES:
        parameter_type.addItem(label, value)
    current_kind = str(getattr(block, "def_param_kind", "normal"))
    parameter_type.setCurrentIndex(max(0, parameter_type.findData(current_kind)))
    default = QLineEdit(str(getattr(block, "def_default", "")))
    permanent = QCheckBox("Permanent")
    permanent.setChecked(block.block_key.endswith("_p"))
    comment = comment_editor(getattr(block, "comment", ""))

    form.addRow(tr("function.port.name"), name)
    form.addRow(tr("function.port.type"), value_type)
    if is_input:
        form.addRow("Type d’entrée", parameter_type)
        form.addRow(tr("function.port.default"), default)
        form.addRow(permanent)
    form.addRow(tr("block_editor.comment"), comment)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)

    def refresh_kind() -> None:
        normal = parameter_type.currentData() == "normal"
        default.setEnabled(normal)
        permanent.setEnabled(normal)
        if not normal:
            permanent.setChecked(False)

    parameter_type.currentIndexChanged.connect(refresh_kind)
    refresh_kind()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    new_name = name.text().strip()
    if not valid_port_name(new_name):
        QMessageBox.warning(parent, block.title, tr("function.invalid.port"))
        return False
    if new_name != getattr(block, "def_port_name", "") and new_name in sibling_names:
        QMessageBox.warning(parent, block.title, tr("function.invalid.port_duplicate"))
        return False
    kind = str(parameter_type.currentData() or "normal") if is_input else "normal"
    default_value = default.text().strip() if kind == "normal" else ""
    required = bool(kind == "normal" and not default_value)
    apply_def_port_config(
        block,
        new_name,
        value_type.currentText(),
        required,
        default_value,
        kind,
        permanent.isChecked() if is_input else False,
    )
    apply_comment(block, comment)
    return True
