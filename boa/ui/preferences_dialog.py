from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from boa.core.preferences import DEFAULT_PREFERENCES, available_languages
from boa.i18n import tr


class PreferencesDialog(QDialog):
    def __init__(self, preferences: dict, parent=None) -> None:
        super().__init__(parent)
        self._preferences = dict(DEFAULT_PREFERENCES)
        self._preferences.update(preferences)
        self.setWindowTitle(tr("preferences.title"))
        self.resize(520, 360)

        self.language_combo = QComboBox()
        for code, label in available_languages():
            self.language_combo.addItem(label, code)
        self._set_combo_data(self.language_combo, self._preferences.get("language", "fr"))

        self.confirm_delete_check = QCheckBox(tr("preferences.confirm_delete"))
        self.confirm_delete_check.setChecked(bool(self._preferences.get("confirm_delete", False)))

        self.grid_size_spin = QSpinBox()
        self.grid_size_spin.setRange(10, 100)
        self.grid_size_spin.setSingleStep(5)
        self.grid_size_spin.setValue(int(self._preferences.get("grid_size", 20)))

        self.snap_check = QCheckBox(tr("preferences.snap"))
        self.snap_check.setChecked(bool(self._preferences.get("snap_to_grid", True)))

        self.auto_imports_check = QCheckBox(tr("preferences.auto_imports"))
        self.auto_imports_check.setChecked(bool(self._preferences.get("auto_imports", True)))

        self.default_type_combo = QComboBox()
        self.default_type_combo.addItems(["any", "int", "float", "str", "bool", "list", "dict", "tuple", "set"])
        self.default_type_combo.setCurrentText(str(self._preferences.get("default_variable_type", "any")))

        self.autosave_check = QCheckBox(tr("preferences.autosave"))
        self.autosave_check.setChecked(bool(self._preferences.get("autosave_enabled", False)))

        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(1, 120)
        self.autosave_interval_spin.setValue(int(self._preferences.get("autosave_interval", 5)))

        self.default_folder_edit = QLineEdit(str(self._preferences.get("default_project_dir", "")))
        self.browse_button = QPushButton(tr("preferences.browse"))
        self.browse_button.clicked.connect(self._browse_default_folder)

        tabs = QTabWidget()
        tabs.addTab(self._general_tab(), tr("preferences.general"))
        tabs.addTab(self._graph_tab(), tr("preferences.graph"))
        tabs.addTab(self._automation_tab(), tr("preferences.automation"))
        tabs.addTab(self._save_tab(), tr("preferences.save"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("preferences.ok"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("preferences.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def preferences(self) -> dict:
        data = dict(self._preferences)
        data.update({
            "language": self.language_combo.currentData(),
            "confirm_delete": self.confirm_delete_check.isChecked(),
            "grid_size": self.grid_size_spin.value(),
            "snap_to_grid": self.snap_check.isChecked(),
            "auto_imports": self.auto_imports_check.isChecked(),
            "default_variable_type": self.default_type_combo.currentText(),
            "autosave_enabled": self.autosave_check.isChecked(),
            "autosave_interval": self.autosave_interval_spin.value(),
            "default_project_dir": self.default_folder_edit.text().strip(),
        })
        return data

    def _general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.addRow(tr("preferences.language"), self.language_combo)
        layout.addRow("", self.confirm_delete_check)
        return widget

    def _graph_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.addRow(tr("preferences.grid_size"), self.grid_size_spin)
        layout.addRow("", self.snap_check)
        return widget

    def _automation_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.addRow("", self.auto_imports_check)
        layout.addRow(tr("preferences.default_type"), self.default_type_combo)
        return widget

    def _save_tab(self) -> QWidget:
        widget = QWidget()
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.default_folder_edit)
        folder_row.addWidget(self.browse_button)
        layout = QFormLayout(widget)
        layout.addRow("", self.autosave_check)
        layout.addRow(tr("preferences.autosave_interval"), self.autosave_interval_spin)
        layout.addRow(tr("preferences.default_folder"), folder_row)
        return widget

    def _browse_default_folder(self) -> None:
        start = self.default_folder_edit.text().strip()
        if not start or not Path(start).exists():
            start = str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, tr("preferences.default_folder"), start)
        if folder:
            self.default_folder_edit.setText(folder)

    def _set_combo_data(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)
