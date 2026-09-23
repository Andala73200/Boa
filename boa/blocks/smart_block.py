import ast

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTextEdit, QVBoxLayout

from boa.blocks.base_block import BlockItem
from boa.i18n import tr


class SmartBlockItem(BlockItem):
    import_detected = Signal(str, str)
    variable_detected = Signal(str)
    content_changed = Signal()

    def __init__(self) -> None:
        super().__init__(tr("block.empty.title"), "", QColor("#5f6368"))
        self.raw_code = ""

    def mouseDoubleClickEvent(self, event) -> None:
        dialog = QDialog(); dialog.setWindowTitle(tr("block.empty.title")); dialog.resize(560, 410)
        layout = QVBoxLayout(dialog); code_edit = QTextEdit(self.raw_code); comment_edit = QTextEdit(self.comment)
        comment_edit.setAcceptRichText(False); comment_edit.setMaximumHeight(100)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
        layout.addWidget(QLabel(tr("empty_dialog.python_code"))); layout.addWidget(code_edit)
        layout.addWidget(QLabel(tr("block_editor.comment"))); layout.addWidget(comment_edit); layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.raw_code = code_edit.toPlainText().strip(); self.comment = comment_edit.toPlainText().strip()
            self._convert_from_code()
        super().mouseDoubleClickEvent(event)

    def _convert_from_code(self) -> None:
        result = detect_python_block(self.raw_code)
        self.title = result.title
        self.subtitle = result.subtitle
        self.color = result.color
        for module, statement in result.imports:
            self.import_detected.emit(module, statement)
        if result.variable_name:
            self.variable_detected.emit(result.variable_name)
        self.refresh_tooltip()
        self.update()
        self.content_changed.emit()


class DetectionResult:
    def __init__(
        self,
        title: str,
        subtitle: str,
        color: QColor,
        import_module: str = "",
        import_statement: str = "",
        variable_name: str = "",
        imports: list[tuple[str, str]] | None = None,
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.color = color
        self.import_module = import_module
        self.import_statement = import_statement
        self.variable_name = variable_name
        self.imports = imports if imports is not None else ([(import_module, import_statement)] if import_module else [])


def detect_python_block(code: str) -> DetectionResult:
    stripped = code.strip()
    if not stripped:
        return DetectionResult(tr("block.empty.title"), "", QColor("#5f6368"))

    header = _detect_header(stripped)
    try:
        tree = ast.parse(stripped)
    except SyntaxError:
        return header or DetectionResult("Python brut", "", QColor("#6d4c41"))

    imports = _import_entries(tree)
    if header:
        header.imports = imports; return header

    node = tree.body[0] if tree.body else None
    if isinstance(node, ast.Import):
        return DetectionResult("import", "", QColor("#00897b"), imports=imports)
    if isinstance(node, ast.ImportFrom):
        return DetectionResult("from import", "", QColor("#00897b"), imports=imports)
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        return DetectionResult("variable", "", QColor("#7b1fa2"), variable_name=name, imports=imports)
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        result = _detect_call(node.value, stripped); result.imports.extend(imports); return result
    return DetectionResult("Python", "", QColor("#455a64"), imports=imports)


def _import_entries(tree: ast.Module) -> list[tuple[str, str]]:
    imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                statement = f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
                imports.append((alias.name.split(".", 1)[0], statement))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or "."
            imports.append((module.split(".", 1)[0], ast.unparse(node)))
    return imports


def _detect_header(code: str) -> DetectionResult | None:
    if code.startswith("if "):
        return DetectionResult("if", "", QColor("#c62828"))
    if code.startswith("while "):
        return DetectionResult("while", "", QColor("#ef6c00"))
    if code.startswith("for "):
        return DetectionResult("for", "", QColor("#2e7d32"))
    if code.startswith("def "):
        return DetectionResult("def", "", QColor("#1565c0"))
    return None


def _detect_call(call: ast.Call, raw: str) -> DetectionResult:
    if isinstance(call.func, ast.Name) and call.func.id == "print":
        return DetectionResult("print", "", QColor("#6a1b9a"))
    if isinstance(call.func, ast.Attribute):
        root = _root_name(call.func)
        if root:
            return DetectionResult("appel module", "", QColor("#00838f"), root, f"import {root}")
    return DetectionResult("appel fonction", "", QColor("#455a64"))


def _root_name(attribute: ast.Attribute) -> str:
    current = attribute
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else ""
