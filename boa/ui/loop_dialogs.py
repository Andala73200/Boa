from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget

from boa.ui.block_library import BlockLibrary
from boa.ui.toolbar import BoaToolBar
from boa.i18n import tr


def edit_for_block(parent, names: list[str], comment: str = "") -> tuple[list[str], str, bool, bool]:
    dialog = QDialog(parent); dialog.setWindowTitle(tr("block.for.title"))
    layout = QVBoxLayout(dialog); layout.addWidget(QLabel(tr("loop_dialog.temporary_outputs")))
    list_widget = QListWidget(); [list_widget.addItem(name) for name in names]; layout.addWidget(list_widget)
    entry = QLineEdit(); entry.setPlaceholderText(tr("loop_dialog.output_placeholder"))
    add_button = QPushButton(tr("loop_dialog.add_output")); remove_button = QPushButton(tr("loop_dialog.remove_output")); open_button = QPushButton(tr("loop_dialog.open_instance"))
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    row = QHBoxLayout(); row.addWidget(entry); row.addWidget(add_button); row.addWidget(remove_button)
    comment_edit = _comment_editor(comment)
    layout.addLayout(row); layout.addWidget(QLabel(tr("block_editor.comment"))); layout.addWidget(comment_edit)
    layout.addWidget(open_button); layout.addWidget(buttons)
    open_requested = {"value": False}

    def add_name() -> None:
        name = entry.text().strip()
        if not name: return
        current = [list_widget.item(i).text() for i in range(list_widget.count())]
        if name in current:
            QMessageBox.warning(dialog, tr("block.for.title"), tr("loop_dialog.output_exists", name=name)); return
        list_widget.addItem(name); entry.clear()

    def request_open() -> None:
        open_requested["value"] = True; dialog.accept()

    add_button.clicked.connect(add_name); remove_button.clicked.connect(lambda: list_widget.takeItem(list_widget.currentRow()))
    open_button.clicked.connect(request_open); buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    result = [list_widget.item(i).text() for i in range(list_widget.count())]
    return result, comment_edit.toPlainText().strip(), open_requested["value"], accepted


def edit_while_block(parent, comment: str = "") -> tuple[str, bool, bool]:
    dialog = QDialog(parent); dialog.setWindowTitle(tr("block.while.title"))
    layout = QVBoxLayout(dialog); comment_edit = _comment_editor(comment)
    layout.addWidget(QLabel(tr("block_editor.comment"))); layout.addWidget(comment_edit)
    open_button = QPushButton(tr("loop_dialog.open_instance"))
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    open_requested = {"value": False}
    def request_open() -> None:
        open_requested["value"] = True; dialog.accept()
    open_button.clicked.connect(request_open); buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
    layout.addWidget(open_button); layout.addWidget(buttons)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    return comment_edit.toPlainText().strip(), open_requested["value"], accepted


def open_instance_dialog(parent, view_factory, title: str, data: dict, required: list[str], variables_provider=None, on_change=None) -> dict | None:
    dialog = QDialog(parent); dialog.setWindowTitle(title); dialog.resize(1180, 740)
    layout = QVBoxLayout(dialog); toolbar = BoaToolBar(dialog); view = view_factory(dialog)
    library = BlockLibrary(dialog); variable_list = _variables_widget(view, variables_provider)
    toolbar.block_requested.connect(view.add_block); library.block_requested.connect(view.add_block)
    view.from_data(data if data and data.get("blocks") else _bootstrap_graph(required))
    autosave = _InstanceAutosave(view, on_change)
    _add_edit_shortcuts(dialog, view)
    side = QWidget(); side_layout = QVBoxLayout(side); side_layout.setContentsMargins(0, 0, 0, 0)
    side_layout.addWidget(library, 2); side_layout.addWidget(QLabel(tr("context.variables"))); side_layout.addWidget(variable_list, 1)
    splitter = QSplitter(Qt.Orientation.Horizontal); splitter.addWidget(view); splitter.addWidget(side); splitter.setSizes([880, 260])
    layout.addWidget(toolbar); layout.addWidget(splitter, 1)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
    buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(dialog.accept)
    dialog.exec(); autosave.flush()
    return view.to_data()


class _InstanceAutosave:
    def __init__(self, view, callback) -> None:
        self.view = view; self.callback = callback
        self.timer = QTimer(view); self.timer.setSingleShot(True); self.timer.setInterval(250)
        self.timer.timeout.connect(self.flush)
        if callback: view.graph_changed.connect(self.timer.start)

    def flush(self) -> None:
        if self.callback: self.callback(self.view.to_data())


def _variables_widget(view, variables_provider) -> QListWidget:
    widget = QListWidget()
    entries = variables_provider() if variables_provider else []
    for item in entries:
        widget.addItem(f"{item.get('name', '')} : {item.get('type', 'any')}{' [C]' if item.get('constant') else ''}")
        widget.item(widget.count() - 1).setData(Qt.ItemDataRole.UserRole, item)
    widget.itemDoubleClicked.connect(lambda item: _add_variable(view, item.data(Qt.ItemDataRole.UserRole)))
    return widget


def _add_variable(view, item: dict) -> None:
    if item and item.get("name"):
        view.add_variable_block(item.get("name", ""), item.get("type", "any"), bool(item.get("constant", False)))


def _add_edit_shortcuts(dialog: QDialog, view) -> None:
    for key, callback in [("Ctrl+C", view.copy_selected_blocks), ("Ctrl+X", view.cut_selected_blocks), ("Ctrl+V", view.paste_blocks), ("Ctrl+A", view.select_all_blocks), ("Del", view.delete_selected_items)]:
        action = QAction(dialog); action.setShortcut(QKeySequence(key)); action.triggered.connect(callback); dialog.addAction(action)


def _comment_editor(comment: str) -> QTextEdit:
    editor = QTextEdit(comment); editor.setAcceptRichText(False); editor.setMinimumHeight(80)
    editor.setPlaceholderText(tr("block_editor.comment_placeholder"))
    return editor


def _bootstrap_graph(required: list[str]) -> dict:
    blocks = []
    if "start" in required: blocks.append(_internal_block("internal_start", "start", 0, 0))
    if "end" in required: blocks.append(_internal_block("internal_end", "end", 520, 0))
    return {"blocks": blocks, "connections": []}


def _internal_block(uid: str, key: str, x: int, y: int) -> dict:
    return {"id": uid, "key": key, "title": key, "x": x, "y": y, "protected": True}
