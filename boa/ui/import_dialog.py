from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox

from boa.i18n import tr


def ask_import(parent=None) -> dict | None:
    dialog = QDialog(parent); dialog.setWindowTitle(tr("import_dialog.title"))
    form = QFormLayout(dialog)
    module_edit = QLineEdit("math")
    statement_edit = QLineEdit("import math")
    origin_edit = QLineEdit("manuel")
    module_edit.textChanged.connect(lambda text: statement_edit.setText(f"import {text.strip()}"))
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
    form.addRow(tr("import_dialog.module"), module_edit)
    form.addRow(tr("import_dialog.statement"), statement_edit)
    form.addRow(tr("import_dialog.origin"), origin_edit)
    form.addRow(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted: return None
    module = module_edit.text().strip(); statement = statement_edit.text().strip()
    if not module:
        QMessageBox.warning(parent, tr("import_dialog.title"), tr("import_dialog.error_module")); return None
    return {"module": module, "statement": statement or f"import {module}", "origin": origin_edit.text().strip() or "manuel"}
