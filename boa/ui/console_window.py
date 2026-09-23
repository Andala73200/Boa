import sys
import os
import shutil
import tempfile
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QPlainTextEdit, QVBoxLayout, QWidget
from boa.i18n import tr
from boa.core.project_files import read_script_file, script_bytes


class ConsoleWindow(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(tr("console.title"))
        self.resize(900, 500)
        self.output = QPlainTextEdit(); self.output.setReadOnly(True)
        self.input_line = QLineEdit(); self.input_line.setPlaceholderText(tr("console.input_placeholder"))
        self.input_line.setEnabled(False)
        self.stop_button = QPushButton(tr("console.stop"))
        self.code_button = QPushButton(tr("console.generated_code"))
        self.close_button = QPushButton(tr("console.close"))
        self.process = QProcess(self)
        self.code = ""
        self.temp_file: Path | None = None
        self.temp_dir: Path | None = None
        self._stop_requested = False
        self._build(); self._connect()

    def _build(self) -> None:
        row = QHBoxLayout()
        row.addWidget(self.input_line, 1)
        row.addWidget(self.stop_button)
        row.addWidget(self.code_button)
        row.addWidget(self.close_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.output, 1)
        layout.addLayout(row)

    def _connect(self) -> None:
        self.input_line.returnPressed.connect(self._send_input)
        self.stop_button.clicked.connect(self.stop)
        self.code_button.clicked.connect(self.show_code)
        self.close_button.clicked.connect(self.close)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._process_finished)

    def run_code(self, code: str, scripts: dict | None = None, interpreter=None, working_directory=None) -> None:
        self.stop()
        self.code = code
        self._cleanup_temp_file()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="boa_run_"))
        self.temp_file = self.temp_dir / "main.py"
        self.temp_file.write_text(code, encoding="utf-8")
        self._write_project_scripts(scripts or {})
        self.output.clear()
        self._stop_requested = False
        self.input_line.setEnabled(True)
        self.append_text(tr("console.starting") + "\n")
        self._prepare_process(working_directory, self.temp_dir)
        self.process.start(str(interpreter or sys.executable), [str(self.temp_file)])

    def run_script(self, path: Path, interpreter=None, working_directory=None) -> None:
        self.stop(); self._cleanup_temp_file()
        self.code = read_script_file(path)[0]
        self.output.clear(); self._stop_requested = False; self.input_line.setEnabled(True)
        self.append_text(tr("console.starting_script", name=path.name) + "\n")
        self._prepare_process(working_directory or path.parent, path.parent)
        self.process.start(str(interpreter or sys.executable), [str(path)])

    def show_code(self) -> None:
        self.append_text("\n" + tr("console.code_begin") + "\n" + self.code.rstrip() + "\n" + tr("console.code_end") + "\n")

    def stop(self) -> None:
        if self.process.state() == QProcess.ProcessState.NotRunning:
            return
        self._stop_requested = True
        self.process.kill()
        self.append_text("\n" + tr("console.stop_requested") + "\n")

    def append_text(self, text: str) -> None:
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        self.output.insertPlainText(text)
        self.output.moveCursor(QTextCursor.MoveOperation.End)

    def closeEvent(self, event) -> None:
        self.stop()
        event.accept()

    def _send_input(self) -> None:
        if self.process.state() == QProcess.ProcessState.NotRunning:
            return
        text = self.input_line.text()
        self.input_line.clear()
        self.process.write((text + "\n").encode())

    def _read_stdout(self) -> None:
        self.append_text(bytes(self.process.readAllStandardOutput()).decode(errors="replace"))

    def _read_stderr(self) -> None:
        self.append_text(bytes(self.process.readAllStandardError()).decode(errors="replace"))

    def _process_finished(self, code: int, status) -> None:
        self.input_line.setEnabled(False)
        if self._stop_requested:
            self.append_text(f"\n[Boa] Programme arrêté. Code retour : {code}\n")
        else:
            self.append_text(f"\n[Boa] Programme terminé. Code retour : {code}\n")
        self._cleanup_temp_file()

    def _cleanup_temp_file(self) -> None:
        if not self.temp_file:
            return
        try:
            self.temp_file.unlink(missing_ok=True)
        except Exception:
            pass
        self.temp_file = None
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = None

    def _write_project_scripts(self, scripts: dict) -> None:
        if not self.temp_dir:
            return
        for item in scripts.values():
            name = str(item.get("path") or item.get("name", "")).strip().replace("\\", "/")
            relative = Path(name)
            if not name.endswith(".py") or relative.is_absolute() or ".." in relative.parts:
                continue
            target = self.temp_dir / relative; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(script_bytes(item, relative))

    def _prepare_process(self, working_directory, import_directory) -> None:
        directory = Path(working_directory) if working_directory else Path(import_directory)
        self.process.setWorkingDirectory(str(directory))
        environment = QProcessEnvironment.systemEnvironment()
        current = environment.value("PYTHONPATH")
        paths = [str(import_directory), str(directory)]
        if current: paths.append(current)
        environment.insert("PYTHONPATH", os.pathsep.join(dict.fromkeys(paths)))
        environment.insert("PYTHONUNBUFFERED", "1")
        self.process.setProcessEnvironment(environment)
