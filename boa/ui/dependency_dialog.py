from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QProcess
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHeaderView, QLabel, QMessageBox,
    QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from boa.core.project_environment import Dependency, project_dependencies, project_root, venv_python
from boa.i18n import tr

_CHECK_CODE = (
    "import importlib.util,json,sys;"
    "names=json.loads(sys.argv[1]);"
    "print(json.dumps({n: importlib.util.find_spec(n) is not None for n in names}))"
)
_PACKAGE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class DependencyCheck(QObject):
    def __init__(self, window, dependencies: list[Dependency], callback, show_all: bool) -> None:
        super().__init__(window)
        self.window = window; self.dependencies = dependencies
        self.project_file = Path(window.current_file)
        self.callback = callback; self.show_all = show_all
        self._done = False
        self.process = QProcess(self)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._failed)

    def start(self) -> None:
        modules = [item.module for item in self.dependencies]
        self.process.setWorkingDirectory(str(project_root(self.project_file)))
        self.process.start(str(venv_python(self.project_file)), ["-c", _CHECK_CODE, json.dumps(modules)])

    def _finished(self, exit_code: int, _status) -> None:
        if self._done:
            return
        self._done = True
        output = bytes(self.process.readAllStandardOutput()).decode(errors="replace").strip()
        error = bytes(self.process.readAllStandardError()).decode(errors="replace").strip()
        try:
            installed = json.loads(output) if exit_code == 0 else None
        except json.JSONDecodeError:
            installed = None
        if not isinstance(installed, dict):
            QMessageBox.critical(self.window, tr("dependencies.title"), tr("dependencies.check_error", detail=error or output))
            self._release(); return
        missing = any(not installed.get(item.module, False) for item in self.dependencies)
        if not self.window.current_file or Path(self.window.current_file) != self.project_file:
            self._release(); return
        if missing or self.show_all:
            dialog = DependencyDialog(
                self.window, self.dependencies, installed,
                self.callback if missing else None,
            )
            self.window._dependency_dialog = dialog
            dialog.finished.connect(lambda *_: setattr(self.window, "_dependency_dialog", None))
            dialog.show(); dialog.raise_(); dialog.activateWindow()
        elif self.callback:
            self.callback()
        self._release()

    def _failed(self, _error) -> None:
        if self._done or self.process.state() != QProcess.ProcessState.NotRunning:
            return
        self._done = True
        QMessageBox.critical(self.window, tr("dependencies.title"), tr("dependencies.check_error", detail=self.process.errorString()))
        self._release()

    def _release(self) -> None:
        refs = getattr(self.window, "_dependency_checks", [])
        self.window._dependency_checks = [item for item in refs if item is not self]
        self.deleteLater()


class DependencyDialog(QDialog):
    def __init__(self, window, dependencies: list[Dependency], installed: dict, callback=None) -> None:
        super().__init__(window)
        self.window = window; self.dependencies = dependencies
        self.project_file = Path(window.current_file)
        self.installed = {str(key): bool(value) for key, value in installed.items()}
        self.callback = callback; self.active_process: QProcess | None = None
        self.buttons: dict[str, QPushButton] = {}
        self.setWindowTitle(tr("dependencies.title")); self.resize(700, 390); self.setModal(True)
        self.table = QTableWidget(len(dependencies), 3)
        self.table.setHorizontalHeaderLabels([
            tr("dependencies.module"), tr("dependencies.package"), tr("dependencies.state"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        for row, dependency in enumerate(dependencies):
            self.table.setItem(row, 0, QTableWidgetItem(dependency.module))
            self.table.setItem(row, 1, QTableWidgetItem(dependency.package))
            button = QPushButton()
            button.clicked.connect(lambda checked=False, item=dependency: self._install(item))
            self.table.setCellWidget(row, 2, button); self.buttons[dependency.module] = button
            self._set_state(dependency.module, self.installed.get(dependency.module, False))
        self.details = QPlainTextEdit(); self.details.setReadOnly(True); self.details.setMaximumHeight(110)
        self.details.setPlaceholderText(tr("dependencies.details"))
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText(tr("dependencies.continue")); self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self._accept)
        layout = QVBoxLayout(self); layout.addWidget(QLabel(tr("dependencies.message")))
        layout.addWidget(self.table); layout.addWidget(self.details); layout.addWidget(self.button_box)
        self._refresh_ok()

    def _install(self, dependency: Dependency) -> None:
        if self.active_process or not _PACKAGE_RE.fullmatch(dependency.package):
            return
        process = QProcess(self); self.active_process = process
        process.setWorkingDirectory(str(project_root(self.project_file)))
        process.readyReadStandardOutput.connect(lambda: self._append_output(process, False))
        process.readyReadStandardError.connect(lambda: self._append_output(process, True))
        process.finished.connect(lambda code, status, item=dependency, proc=process: self._install_finished(item, proc, code))
        process.errorOccurred.connect(lambda error, item=dependency, proc=process: self._process_failed(item, proc))
        self._set_installing(dependency.module)
        process.start(str(venv_python(self.project_file)), ["-m", "pip", "install", dependency.package])

    def _install_finished(self, dependency: Dependency, process: QProcess, exit_code: int) -> None:
        if self.active_process is not process:
            return
        process.deleteLater(); self.active_process = None
        if exit_code == 0:
            self._verify_install(dependency); return
        self._finalize_install(dependency, False)

    def _verify_install(self, dependency: Dependency) -> None:
        process = QProcess(self); self.active_process = process
        process.finished.connect(lambda code, status, item=dependency, proc=process: self._verified(item, proc, code))
        process.errorOccurred.connect(lambda error, item=dependency, proc=process: self._process_failed(item, proc))
        process.start(
            str(venv_python(self.project_file)),
            ["-c", _CHECK_CODE, json.dumps([dependency.module])],
        )

    def _verified(self, dependency: Dependency, process: QProcess, exit_code: int) -> None:
        if self.active_process is not process:
            return
        output = bytes(process.readAllStandardOutput()).decode(errors="replace").strip()
        try:
            result = json.loads(output) if exit_code == 0 else {}
        except json.JSONDecodeError:
            result = {}
        process.deleteLater(); self.active_process = None
        self._finalize_install(dependency, bool(result.get(dependency.module, False)))

    def _process_failed(self, dependency: Dependency, process: QProcess) -> None:
        if self.active_process is not process or process.state() != QProcess.ProcessState.NotRunning:
            return
        self.details.appendPlainText(process.errorString())
        process.deleteLater(); self.active_process = None
        self._finalize_install(dependency, False)

    def _finalize_install(self, dependency: Dependency, installed: bool) -> None:
        self.installed[dependency.module] = installed
        self._set_state(dependency.module, installed, failed=not installed)
        for module, button in self.buttons.items():
            if not self.installed.get(module, False) and module != dependency.module:
                button.setEnabled(True)
        self._refresh_ok()

    def _set_state(self, module: str, installed: bool, failed: bool = False) -> None:
        button = self.buttons[module]
        button.setText(tr("dependencies.installed") if installed else tr("dependencies.retry") if failed else tr("dependencies.install"))
        button.setEnabled(not installed)

    def _set_installing(self, module: str) -> None:
        for name, button in self.buttons.items():
            button.setEnabled(False)
            if name == module:
                button.setText(tr("dependencies.installing"))

    def _append_output(self, process: QProcess, stderr: bool) -> None:
        data = process.readAllStandardError() if stderr else process.readAllStandardOutput()
        self.details.appendPlainText(bytes(data).decode(errors="replace").rstrip())

    def _refresh_ok(self) -> None:
        self.ok_button.setEnabled(all(self.installed.get(item.module, False) for item in self.dependencies))

    def _accept(self) -> None:
        self.accept()
        if self.callback:
            self.callback()

    def reject(self) -> None:
        if self.active_process:
            self.active_process.kill()
        super().reject()


def check_project_dependencies(window, callback: Callable[[], None] | None = None, show_all: bool = False) -> None:
    existing = getattr(window, "_dependency_dialog", None)
    if existing and existing.isVisible():
        if callback:
            existing.callback = callback
        existing.raise_(); existing.activateWindow(); return
    dependencies = project_dependencies(window._project_data(), window.current_file)
    if not dependencies:
        if show_all:
            QMessageBox.information(window, tr("dependencies.title"), tr("dependencies.none"))
        if callback:
            callback()
        return
    check = DependencyCheck(window, dependencies, callback, show_all)
    if not hasattr(window, "_dependency_checks"):
        window._dependency_checks = []
    window._dependency_checks.append(check); check.start()
