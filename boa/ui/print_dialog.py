from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from boa.i18n import tr


class PrintDialog(QDialog):
    def __init__(self, text: str = "", dynamic: bool = False, variables: list[str] | None = None, comment: str = "", parent=None) -> None:
        super().__init__(parent)
        self._variables = sorted(set(variables or []), key=str.lower)
        self.setWindowTitle(tr("print_dialog.title"))
        self.resize(520, 360)
        self.text_edit = QTextEdit(text)
        self.comment_edit = QTextEdit(comment)
        self.comment_edit.setAcceptRichText(False)
        self.comment_edit.setPlaceholderText(tr("block_editor.comment_placeholder"))
        self.comment_edit.setMaximumHeight(90)
        self.dynamic_check = QCheckBox(tr("print_dialog.dynamic"))
        self.dynamic_check.setChecked(dynamic)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("print_dialog.search"))
        self.variable_list = QListWidget()
        self.insert_button = QPushButton(tr("print_dialog.insert"))
        self._populate_variables("")
        self.search.textChanged.connect(self._populate_variables)
        self.insert_button.clicked.connect(self._insert_selected_variable)
        self.variable_list.itemDoubleClicked.connect(lambda item: self._insert_variable(item.text()))
        self.dynamic_check.toggled.connect(self._set_variable_widgets_enabled)
        self._build_layout()
        self._set_variable_widgets_enabled(dynamic)

    def print_text(self) -> str:
        return self.text_edit.toPlainText()

    def is_dynamic(self) -> bool:
        return self.dynamic_check.isChecked()

    def block_comment(self) -> str:
        return self.comment_edit.toPlainText().strip()

    def _build_layout(self) -> None:
        variable_row = QHBoxLayout()
        variable_row.addWidget(self.search)
        variable_row.addWidget(self.insert_button)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("print_dialog.text")))
        layout.addWidget(self.text_edit)
        layout.addWidget(self.dynamic_check)
        layout.addLayout(variable_row)
        layout.addWidget(self.variable_list)
        layout.addWidget(QLabel(tr("block_editor.comment")))
        layout.addWidget(self.comment_edit)
        layout.addWidget(buttons)

    def _populate_variables(self, query: str) -> None:
        self.variable_list.clear()
        query = query.strip().lower()
        for name in self._variables:
            if query in name.lower():
                self.variable_list.addItem(name)

    def _set_variable_widgets_enabled(self, enabled: bool) -> None:
        for widget in (self.search, self.variable_list, self.insert_button):
            widget.setEnabled(enabled)
            widget.setVisible(enabled)

        if enabled:
            self.resize(max(self.width(), 520), 360)
        else:
            self.resize(max(self.width(), 520), 240)

    def _insert_selected_variable(self) -> None:
        item = self.variable_list.currentItem()
        if item:
            self._insert_variable(item.text())

    def _insert_variable(self, name: str) -> None:
        if not self.dynamic_check.isChecked():
            return
        self.text_edit.insertPlainText("{" + name + "}")
        self.text_edit.setFocus(Qt.FocusReason.OtherFocusReason)
