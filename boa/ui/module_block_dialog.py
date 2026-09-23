from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QToolButton,
    QToolTip,
    QWidget,
)

from boa.blocks.block_factory import apply_module_config
from boa.core.module_registry import MODULE_SPECS
from boa.core.module_specs import (
    module_has_selectable_outputs,
    possible_module_ports,
    resolved_module_ports,
    unfiltered_module_ports,
)
from boa.i18n import tr
from boa.ui.block_comment_dialog import add_comment_row, apply_comment
from boa.ui.block_titles import retranslate_block


class _InfoLabel(QLabel):
    def enterEvent(self, event) -> None:
        QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()), self.toolTip(), self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        QToolTip.hideText()
        super().leaveEvent(event)


class ModuleBlockDialog(QDialog):
    def __init__(self, block, project_root: str = "", parent=None) -> None:
        super().__init__(parent)
        self.block = block
        self.spec = MODULE_SPECS[block.block_key]
        self.project_root = Path(project_root).resolve() if project_root else None
        self.widgets: dict[str, QWidget] = {}
        self.rows: dict[str, tuple[QWidget, QWidget]] = {}
        self.input_checks: dict[str, QCheckBox] = {}
        self.output_checks: dict[str, QCheckBox] = {}
        self.input_options_row: tuple[QWidget, QWidget] | None = None
        self.output_options_row: tuple[QWidget, QWidget] | None = None
        self.setWindowTitle(tr("module_dialog.title", name=block.title))
        self.resize(520, 260)
        self.form = QFormLayout(self)
        config = dict(getattr(block, "module_config", {}) or {})
        for field in self.spec.fields:
            widget = self._field_widget(field, config.get(field.key, field.default))
            container = self._with_info(widget, field.info_key)
            label = QWidget()
            label_layout = QHBoxLayout(label)
            label_layout.setContentsMargins(0, 0, 0, 0)
            label_layout.addWidget(QLabel(_translated(field.label_key, field.key)))
            self.form.addRow(label, container)
            self.widgets[field.key] = widget
            self.rows[field.key] = (label, container)
        self._add_port_option_rows(config)
        self.comment_edit = add_comment_row(self.form, block)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        self.form.addRow(buttons)
        self._connect_dependencies()
        self._update_port_options()
        self._update_visibility()

    def values(self) -> dict:
        result = self._field_values()
        inputs, outputs = unfiltered_module_ports(self.spec, result)
        value_inputs = [port for port in inputs if port.value_type != "flow"]
        value_outputs = [port for port in outputs if port.value_type != "flow"]
        if self.spec.selectable_inputs and value_inputs:
            result["_enabled_inputs"] = [port.key for port in value_inputs if self.input_checks.get(port.key) and self.input_checks[port.key].isChecked()]
        if len(value_outputs) > 1:
            result["_enabled_outputs"] = [port.key for port in value_outputs if self.output_checks.get(port.key) and self.output_checks[port.key].isChecked()]
        return result

    def _field_values(self) -> dict:
        result = {}
        for field in self.spec.fields:
            widget = self.widgets[field.key]
            if isinstance(widget, QComboBox):
                result[field.key] = widget.currentData() or ""
            elif isinstance(widget, QCheckBox):
                result[field.key] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                result[field.key] = widget.value()
            elif isinstance(widget, QLineEdit):
                result[field.key] = widget.text().strip()
        return result

    def _field_widget(self, field, value):
        if field.kind == "info":
            return QLabel(tr("module_dialog.click_info"))
        if field.kind == "choice":
            combo = QComboBox()
            if not field.default:
                combo.addItem("----", "")
            for choice in field.choices:
                combo.addItem(_translated(choice.label_key, choice.key), choice.key)
            index = combo.findData(str(value or ""))
            combo.setCurrentIndex(max(0, index))
            return combo
        if field.kind == "bool":
            check = QCheckBox()
            check.setChecked(bool(value))
            return check
        if field.kind == "int":
            spin = QSpinBox()
            spin.setRange(field.minimum, field.maximum)
            spin.setValue(int(value or 0))
            return spin
        edit = QLineEdit(str(value or ""))
        if field.kind == "path":
            edit.setProperty("boa_path_kind", field.path_kind)
            edit.setProperty("boa_path_key", field.key)
        return edit

    def _with_info(self, widget: QWidget, info_key: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget, 1)
        if isinstance(widget, QLineEdit) and widget.property("boa_path_kind"):
            if widget.property("boa_path_kind") == "any":
                browse_file = QToolButton(); browse_file.setText(tr("module_dialog.browse_file"))
                browse_folder = QToolButton(); browse_folder.setText(tr("module_dialog.browse_folder"))
                browse_file.clicked.connect(lambda: self._browse(widget, "file"))
                browse_folder.clicked.connect(lambda: self._browse(widget, "folder"))
                layout.addWidget(browse_file); layout.addWidget(browse_folder)
            else:
                browse = QToolButton()
                browse.setText(tr("module_dialog.browse"))
                browse.clicked.connect(lambda: self._browse(widget))
                layout.addWidget(browse)
        if info_key:
            info = _InfoLabel()
            info.setText("ⓘ")
            info.setCursor(Qt.CursorShape.WhatsThisCursor)
            text = _translated(info_key, info_key)
            info.setToolTip(text)
            layout.addWidget(info)
        return container

    def _add_port_option_rows(self, config: dict) -> None:
        possible_inputs, possible_outputs = possible_module_ports(self.spec)
        if self.spec.selectable_inputs and possible_inputs:
            self.input_checks, self.input_options_row = self._port_option_row(
                possible_inputs,
                config.get("_enabled_inputs"),
                "module_dialog.visible_inputs",
            )
        if module_has_selectable_outputs(self.spec):
            self.output_checks, self.output_options_row = self._port_option_row(
                possible_outputs,
                config.get("_enabled_outputs"),
                "module_dialog.visible_outputs",
            )

    def _port_option_row(self, ports, selected, label_key: str):
        selected_keys = {str(key) for key in selected} if isinstance(selected, (list, tuple, set)) else None
        label = QLabel(tr(label_key))
        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        checks = {}
        for index, port in enumerate(ports):
            check = QCheckBox(self._port_label(port))
            check.setChecked(selected_keys is None or port.key in selected_keys)
            check.toggled.connect(self._update_visibility)
            layout.addWidget(check, index // 2, index % 2)
            checks[port.key] = check
        self.form.addRow(label, container)
        return checks, (label, container)

    def _port_label(self, port) -> str:
        generic = _translated(f"port.{port.key}", port.label)
        return _translated(f"block.{self.block.block_key}.port.{port.key}", generic)

    def _browse(self, edit: QLineEdit, forced_kind: str = "") -> None:
        start = edit.text().strip()
        if start and self.project_root and not Path(start).is_absolute():
            start = str(self.project_root / start)
        if not start:
            start = str(self.project_root or Path.cwd())
        kind = forced_kind or str(edit.property("boa_path_kind") or "file")
        key = str(edit.property("boa_path_key") or "")
        current = self.values()
        if key in {"source_path", "target_path"} and current.get("mode") == "folder":
            kind = "folder"
        if kind == "folder":
            selected = QFileDialog.getExistingDirectory(self, tr("module_dialog.select_folder"), start)
        elif "destination" in key or (key == "file_path" and self.block.block_key not in {"json_read", "csv_read"} and current.get("mode") != "read"):
            selected, _ = QFileDialog.getSaveFileName(self, tr("module_dialog.select_file"), start)
        else:
            selected, _ = QFileDialog.getOpenFileName(self, tr("module_dialog.select_file"), start)
        if not selected:
            return
        relative = self.widgets.get("relative_to_project")
        if isinstance(relative, QCheckBox) and relative.isChecked() and self.project_root:
            try:
                selected = str(Path(selected).resolve().relative_to(self.project_root))
            except ValueError:
                pass
        edit.setText(selected)

    def _connect_dependencies(self) -> None:
        for key, widget in self.widgets.items():
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(lambda _index, field_key=key: self._field_changed(field_key))
            elif isinstance(widget, QCheckBox):
                widget.toggled.connect(self._update_visibility)

    def _field_changed(self, field_key: str) -> None:
        self._update_port_options(reset=field_key == self.spec.variant_field)
        self._update_visibility()

    def _update_port_options(self, reset: bool = False) -> None:
        values = self._field_values()
        inputs, outputs = unfiltered_module_ports(self.spec, values)
        input_keys = {port.key for port in inputs if port.value_type != "flow"}
        output_keys = {port.key for port in outputs if port.value_type != "flow"}
        for key, check in self.input_checks.items():
            check.setVisible(key in input_keys)
            if reset and key in input_keys:
                check.setChecked(True)
        for key, check in self.output_checks.items():
            check.setVisible(key in output_keys)
            if reset and key in output_keys:
                check.setChecked(True)
        if self.input_options_row:
            visible = bool(input_keys)
            self.input_options_row[0].setVisible(visible)
            self.input_options_row[1].setVisible(visible)
        if self.output_options_row:
            visible = len(output_keys) > 1
            self.output_options_row[0].setVisible(visible)
            self.output_options_row[1].setVisible(visible)

    def _update_visibility(self) -> None:
        values = self.values()
        values.update((f"input.{key}", not check.isHidden() and check.isChecked()) for key, check in self.input_checks.items())
        values.update((f"output.{key}", not check.isHidden() and check.isChecked()) for key, check in self.output_checks.items())
        for field in self.spec.fields:
            visible = all(_matches(values.get(key), expected) for key, expected in field.show_if)
            label, container = self.rows[field.key]
            label.setVisible(visible)
            container.setVisible(visible)

    def _accept(self) -> None:
        values = self.values()
        _, outputs = unfiltered_module_ports(self.spec, values)
        value_outputs = [port for port in outputs if port.value_type != "flow"]
        if not self.spec.flow and len(value_outputs) > 1 and not values.get("_enabled_outputs"):
            QMessageBox.warning(self, tr("module_dialog.invalid_configuration"), tr("module_dialog.output_required"))
            return
        if self.block.block_key == "datetime_create" and values.get("mode") in {"date", "datetime"}:
            try:
                date(int(values["year"]), int(values["month"]), int(values["day"]))
            except (KeyError, TypeError, ValueError):
                QMessageBox.warning(self, tr("module_dialog.invalid_configuration"), tr("module_dialog.invalid_date"))
                return
        self.accept()


def edit_module_block(block, project_root: str = "", parent=None) -> bool:
    dialog = ModuleBlockDialog(block, project_root, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    before_config = dict(getattr(block, "module_config", {}) or {})
    before_comment = str(getattr(block, "comment", "") or "")
    values = dialog.values()
    inputs, outputs = resolved_module_ports(dialog.spec, values)
    valid_inputs = {port.key for port in inputs}
    valid_outputs = {port.key for port in outputs}
    invalid_connections = [
        connection for connection in block.connections
        if (connection.target_block is block and connection.target_port not in valid_inputs)
        or (connection.source_block is block and connection.source_port not in valid_outputs)
    ]
    if invalid_connections:
        answer = QMessageBox.question(
            parent or dialog,
            tr("module_dialog.connections_title"),
            tr("module_dialog.connections_removed", count=len(invalid_connections)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
    apply_module_config(block, values)
    apply_comment(block, dialog.comment_edit)
    retranslate_block(block)
    return before_config != block.module_config or before_comment != block.comment


def _translated(key: str, fallback: str) -> str:
    value = tr(key)
    return fallback if value == key else value


def _matches(value, expected) -> bool:
    if isinstance(expected, (list, tuple, set)):
        return value in expected
    return value == expected
