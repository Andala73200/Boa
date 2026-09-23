from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QMessageBox, QTextEdit, QVBoxLayout

from boa.blocks.python_block import apply_python_block_data
from boa.python_importer import convert_python_statement


def edit_python_block(block, parent=None) -> tuple[bool, list[dict]]:
    dialog = QDialog(parent)
    dialog.setWindowTitle(str(getattr(block, "python_title", "Bloc Python")))
    dialog.resize(680, 520)
    layout = QVBoxLayout(dialog)
    source = QTextEdit(str(getattr(block, "python_source", "")))
    source.setAcceptRichText(False)
    comment = QTextEdit(str(getattr(block, "comment", "")))
    comment.setAcceptRichText(False)
    comment.setMaximumHeight(110)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(QLabel("Instruction ou structure Python :"))
    layout.addWidget(source)
    layout.addWidget(QLabel("Commentaire Boa :"))
    layout.addWidget(comment)
    layout.addWidget(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False, []
    try:
        data, imports = convert_python_statement(source.toPlainText())
    except ValueError as error:
        QMessageBox.warning(parent, "Bloc Python invalide", str(error))
        return False, []
    data["python_function_id"] = str(getattr(block, "python_function_id", ""))
    data["python_import_header"] = bool(getattr(block, "python_import_header", False))
    apply_python_block_data(block, data)
    block.comment = comment.toPlainText().strip()
    block.refresh_tooltip()
    block.update()
    return True, imports
