from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from boa.i18n import tr


TYPES = ["----", "any", "int", "float", "str", "bool", "list", "dict", "tuple", "set"]


class VariableDialog(QDialog):
    def __init__(self, existing_names: set[str], parent=None) -> None:
        super().__init__(parent)
        self._existing_names = {name.lower() for name in existing_names}
        self._created: list[dict] = []
        self.setWindowTitle(tr("variable_dialog.title"))
        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(TYPES)
        self.initial_edit = QLineEdit()
        self.constant_check = QCheckBox()
        self.scope_edit = QLineEdit("global")
        self.message = QLabel("")
        self.message.setStyleSheet("color: #ff8a80;")
        self._build_layout()
        self.name_edit.setFocus()

    def created_variables(self) -> list[dict]:
        return list(self._created)

    def _build_layout(self) -> None:
        form = QFormLayout()
        form.addRow(tr("variable_dialog.name"), self.name_edit)
        form.addRow(tr("variable_dialog.type"), self.type_combo)
        form.addRow(tr("variable_dialog.initial"), self.initial_edit)
        form.addRow(tr("variable_dialog.constant"), self.constant_check)
        form.addRow(tr("variable_dialog.scope"), self.scope_edit)
        add_button = QPushButton(tr("variable_dialog.add"))
        add_new_button = QPushButton(tr("variable_dialog.add_new"))
        cancel_button = QPushButton(tr("preferences.cancel"))
        add_button.clicked.connect(lambda: self._add(close_after=True))
        add_new_button.clicked.connect(lambda: self._add(close_after=False))
        cancel_button.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(add_button)
        buttons.addWidget(add_new_button)
        buttons.addWidget(cancel_button)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.message)
        layout.addLayout(buttons)

    def _add(self, close_after: bool) -> None:
        data = self._read_data()
        error = self._validate(data)
        if error:
            self.message.setText(error)
            return
        self._created.append(data)
        self._existing_names.add(data["name"].lower())
        if close_after:
            self.accept()
            return
        self.message.setText("")
        self.name_edit.clear()
        self.initial_edit.clear()
        self.constant_check.setChecked(False)
        self.type_combo.setCurrentIndex(0)
        self.name_edit.setFocus()

    def _read_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "type": self.type_combo.currentText().strip(),
            "initial": self.initial_edit.text().strip(),
            "constant": self.constant_check.isChecked(),
            "scope": self.scope_edit.text().strip() or "global",
        }

    def _validate(self, data: dict) -> str:
        if not data["name"]:
            return tr("variable_dialog.error_name")
        if data["name"].lower() in self._existing_names:
            return tr("variable_dialog.error_duplicate", name=data["name"])
        if data["type"] == "----":
            return tr("variable_dialog.error_type")
        return ""
