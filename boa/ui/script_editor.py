from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QVBoxLayout

from boa.i18n import tr


class ScriptEditorDialog(QDialog):
    script_saved = Signal(str, str)

    def __init__(self, script_id: str, name: str, content: str, parent=None) -> None:
        super().__init__(parent)
        self.script_id = script_id
        self.setWindowTitle(f"{tr('project.script_editor')} - {name}")
        self.resize(900, 650)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(content or "")
        self.editor.setReadOnly(True)
        self.notice = QLabel(tr("project.script_read_only"))
        self.edit_button = QPushButton(tr("project.edit_script"))
        self.save_button = QPushButton(tr("action.save"))
        self.save_button.setEnabled(False)
        self.close_button = QPushButton(tr("action.quit"))
        self.edit_button.clicked.connect(self._enable_editing)
        self.save_button.clicked.connect(self._save)
        self.close_button.clicked.connect(self.close)
        buttons = QHBoxLayout(); buttons.addWidget(self.notice); buttons.addStretch(1); buttons.addWidget(self.edit_button); buttons.addWidget(self.save_button); buttons.addWidget(self.close_button)
        layout = QVBoxLayout(self); layout.addWidget(self.editor); layout.addLayout(buttons)

    def _enable_editing(self) -> None:
        self.editor.setReadOnly(False)
        self.editor.setFocus()
        self.edit_button.setEnabled(False)
        self.save_button.setEnabled(True)
        self.notice.setText(tr("project.script_editing"))

    def _save(self) -> None:
        self.script_saved.emit(self.script_id, self.editor.toPlainText())
