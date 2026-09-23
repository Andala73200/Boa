from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QProcess
from PySide6.QtWidgets import QMessageBox

from boa.core.project_environment import venv_path, venv_python
from boa.i18n import tr


class EnvironmentController(QObject):
    def __init__(self, window) -> None:
        super().__init__(window)
        self.window = window
        self.project_file = Path(window.current_file)
        self.callbacks: list[Callable[[], None]] = []
        self.process = QProcess(self)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self._error_reported = False
        self._released = False

    def add_callback(self, callback: Callable[[], None] | None) -> None:
        if callback:
            self.callbacks.append(callback)

    def start(self) -> None:
        target = venv_path(self.project_file)
        self.window.statusBar().showMessage(tr("environment.creating", path=str(target)))
        self.process.setWorkingDirectory(str(target.parent))
        self.process.start(sys.executable, ["-m", "venv", str(target)])

    def _finished(self, exit_code: int, _status) -> None:
        if self._released:
            return
        if exit_code != 0 or not venv_python(self.project_file).is_file():
            self._show_error(self._process_message() or tr("environment.create_failed"))
            self._release(); return
        self.window.statusBar().showMessage(tr("environment.ready"), 3500)
        callbacks = list(self.callbacks)
        self._release()
        if self.window.current_file and Path(self.window.current_file) == self.project_file:
            for callback in callbacks:
                callback()

    def _process_error(self, _error) -> None:
        if self._released:
            return
        if self.process.state() == QProcess.ProcessState.NotRunning:
            self._show_error(self.process.errorString())
            self._release()

    def _show_error(self, detail: str) -> None:
        if self._error_reported:
            return
        self._error_reported = True
        QMessageBox.critical(
            self.window, tr("environment.title"),
            tr("environment.create_error", detail=detail.strip()),
        )

    def _process_message(self) -> str:
        stderr = bytes(self.process.readAllStandardError()).decode(errors="replace").strip()
        stdout = bytes(self.process.readAllStandardOutput()).decode(errors="replace").strip()
        return stderr or stdout

    def _release(self) -> None:
        if self._released:
            return
        self._released = True
        if getattr(self.window, "_environment_controller", None) is self:
            self.window._environment_controller = None
        self.deleteLater()


def ensure_project_environment(window, on_ready: Callable[[], None] | None = None) -> bool:
    if not window.current_file:
        if not window.save_project_as():
            return False
    python = venv_python(window.current_file)
    if python.is_file():
        if on_ready:
            on_ready()
        return True
    controller = getattr(window, "_environment_controller", None)
    if controller is not None and controller.project_file != Path(window.current_file):
        controller.process.kill(); controller._release(); controller = None
    if controller is None:
        controller = EnvironmentController(window)
        window._environment_controller = controller
        controller.add_callback(on_ready)
        controller.start()
    else:
        controller.add_callback(on_ready)
    return True
