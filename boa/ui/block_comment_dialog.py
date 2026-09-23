from textwrap import fill

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QTextEdit

from boa.i18n import tr


def comment_editor(text: str = "") -> QTextEdit:
    editor = QTextEdit(str(text or ""))
    editor.setAcceptRichText(False)
    editor.setPlaceholderText(tr("block_editor.comment_placeholder"))
    editor.setMinimumHeight(88)
    return editor


def add_comment_row(form: QFormLayout, block) -> QTextEdit:
    editor = comment_editor(getattr(block, "comment", ""))
    form.addRow(tr("block_editor.comment"), editor)
    return editor


def apply_comment(block, editor: QTextEdit | str) -> None:
    text = editor.toPlainText() if isinstance(editor, QTextEdit) else str(editor or "")
    block.comment = text.strip()
    block.refresh_tooltip()
    block.update()


def edit_block_comment(block, parent=None) -> bool:
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("block_editor.title", name=block.title))
    dialog.resize(470, 220)
    form = QFormLayout(dialog)
    editor = add_comment_row(form, block)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    before = str(getattr(block, "comment", ""))
    apply_comment(block, editor)
    return before != block.comment


def tooltip_comment(text: str) -> str:
    wrapped = "\n".join(fill(line, width=68) if line else "" for line in str(text).splitlines())
    return tr("tooltip.block.comment", comment=wrapped)
