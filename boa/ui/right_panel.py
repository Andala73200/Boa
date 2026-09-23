from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGroupBox, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from boa.runtime.loop_registry import collect_loop_instances
from boa.ui.block_library import BlockLibrary


class RightPanel(QWidget):
    block_requested = Signal(str)
    loop_requested = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.library = BlockLibrary(self)
        self.loops = LoopInstancesBox(self)
        self.library.block_requested.connect(self.block_requested.emit)
        self.loops.loop_requested.connect(self.loop_requested.emit)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(6)
        layout.addWidget(self.library, 3); layout.addWidget(self.loops, 1)

    def set_project_data(self, project: dict) -> None:
        self.loops.set_instances(collect_loop_instances(project))

    def retranslate_ui(self) -> None:
        self.library.retranslate_ui(); self.loops.setTitle("Instances de boucles")


class LoopInstancesBox(QGroupBox):
    loop_requested = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__("Instances de boucles", parent)
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._open_item)
        self.list_widget.itemClicked.connect(self._open_item)
        layout = QVBoxLayout(self); layout.setContentsMargins(6, 6, 6, 6); layout.addWidget(self.list_widget)

    def set_instances(self, items: list[dict]) -> None:
        self.list_widget.clear()
        for item in sorted(items, key=lambda x: (x.get("key", ""), x.get("number", 0), x.get("depth", 0))):
            indent = "  " * int(item.get("depth", 0))
            row = QListWidgetItem(indent + item.get("label", ""))
            row.setData(Qt.ItemDataRole.UserRole, item.get("path", []))
            self.list_widget.addItem(row)

    def _open_item(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path: self.loop_requested.emit(path)
