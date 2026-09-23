from PySide6.QtCore import QObject, Signal, Slot

from boa.runtime.code_generator import generate_python


class GeneratorWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, project: dict) -> None:
        super().__init__()
        self.project = project

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(generate_python(self.project))
        except Exception as error:
            self.failed.emit(str(error))
