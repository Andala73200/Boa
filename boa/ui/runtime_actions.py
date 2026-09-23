from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Slot
from PySide6.QtWidgets import QFileDialog, QMessageBox

from boa.runtime.code_generator import generate_python
from boa.core.atomic_io import atomic_write_text
from boa.runtime.generator_worker import GeneratorWorker
from boa.ui.console_window import ConsoleWindow
from boa.core.project_environment import project_root, venv_python
from boa.core.project_files import safe_script_path
from boa.ui.dependency_dialog import check_project_dependencies
from boa.ui.environment_controller import ensure_project_environment
from boa.i18n import tr


class _RuntimeController(QObject):
    def __init__(self, window, thread: QThread, worker: GeneratorWorker, console: ConsoleWindow) -> None:
        super().__init__(window)
        self.window = window
        self.thread = thread
        self.worker = worker
        self.console = console

    @Slot(str)
    def on_generated(self, code: str) -> None:
        self._finish_thread()
        project = self.window._project_data()
        self.console.run_code(
            code, project.get("scripts", {}), venv_python(self.window.current_file),
            project_root(self.window.current_file),
        )

    @Slot(str)
    def on_failed(self, error: str) -> None:
        self._finish_thread()
        self.console.append_text(tr("runtime.generation_error", error=error) + "\n")

    @Slot()
    def on_thread_finished(self) -> None:
        if hasattr(self.window, "_runtime_refs"):
            self.window._runtime_refs = [item for item in self.window._runtime_refs if item[0] is not self.thread]
        self.thread.deleteLater()
        self.deleteLater()

    def _finish_thread(self) -> None:
        self.worker.deleteLater()
        self.thread.quit()


def export_python(window) -> None:
    path, _ = QFileDialog.getSaveFileName(window, tr("runtime.export_title"), "boa_generated.py", "Python (*.py)")
    if not path:
        return
    try:
        target = Path(path)
        if target.suffix.lower() != ".py":
            target = target.with_suffix(".py")
        atomic_write_text(target, generate_python(project_for_graph(window)))
        window.statusBar().showMessage(tr("runtime.exported", name=target.name), 3000)
    except Exception as error:
        QMessageBox.critical(window, tr("runtime.export_title"), str(error))


def simulate_project(window, graph_id: str | None = None) -> None:
    ensure_project_environment(
        window,
        lambda: check_project_dependencies(window, lambda: _simulate_project_ready(window, graph_id)),
    )


def _simulate_project_ready(window, graph_id: str | None = None) -> None:
    console = _console(window)
    console.show(); console.raise_(); console.activateWindow()
    console.append_text(tr("runtime.generating") + "\n")
    thread = QThread(window)
    worker = GeneratorWorker(project_for_graph(window, graph_id))
    controller = _RuntimeController(window, thread, worker, console)
    worker.moveToThread(thread)
    _keep_runtime_ref(window, thread, worker, controller)
    thread.started.connect(worker.run)
    worker.finished.connect(controller.on_generated, Qt.ConnectionType.QueuedConnection)
    worker.failed.connect(controller.on_failed, Qt.ConnectionType.QueuedConnection)
    thread.finished.connect(controller.on_thread_finished)
    thread.start()


def execute_script(window, script_id: str) -> None:
    ensure_project_environment(
        window,
        lambda: check_project_dependencies(window, lambda: _execute_script_ready(window, script_id)),
    )


def _execute_script_ready(window, script_id: str) -> None:
    item = window._scripts.get(script_id)
    if not item:
        return
    try:
        if not window.current_file:
            raise ValueError(tr("runtime.save_before_script"))
        relative = item.get("path") or item.get("name")
        path = safe_script_path(project_root(window.current_file), relative)
        if not path.is_file():
            raise FileNotFoundError(str(path))
    except Exception as error:
        QMessageBox.critical(window, tr("runtime.execute_title"), str(error)); return
    console = _console(window); console.show(); console.raise_(); console.activateWindow()
    console.run_script(path, venv_python(window.current_file), project_root(window.current_file))


def stop_project(window) -> None:
    console = getattr(window, "_boa_console", None)
    if console is not None:
        console.stop()


def relaunch_project(window) -> None:
    stop_project(window)
    simulate_project(window)


def project_for_graph(window, graph_id: str | None = None) -> dict:
    project = window._project_data()
    selected = graph_id or project.get("main_graph_id") or project.get("active_graph_id")
    graphs = project.get("graphs", {})
    if selected not in graphs:
        raise ValueError(tr("runtime.graph_missing"))
    project["active_graph_id"] = selected
    project["graph"] = deepcopy(graphs[selected].get("graph", {}))
    return project


def _console(window) -> ConsoleWindow:
    console = getattr(window, "_boa_console", None)
    if console is None:
        console = ConsoleWindow(window)
        window._boa_console = console
    return console


def _keep_runtime_ref(window, thread, worker, controller) -> None:
    if not hasattr(window, "_runtime_refs"):
        window._runtime_refs = []
    window._runtime_refs.append((thread, worker, controller))
