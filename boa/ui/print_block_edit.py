from PySide6.QtWidgets import QDialog

from boa.blocks.base_block import BlockItem
from boa.ui.print_dialog import PrintDialog
from boa.ui.block_comment_dialog import apply_comment


def edit_print_block(block: BlockItem, variables_provider, parent=None) -> bool:
    variables = variables_provider() if callable(variables_provider) else []
    dialog = PrintDialog(
        getattr(block, "print_text", block.subtitle),
        bool(getattr(block, "print_dynamic", False)),
        variables,
        getattr(block, "comment", ""),
        parent,
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    apply_print_values(block, dialog.print_text(), dialog.is_dynamic())
    apply_comment(block, dialog.block_comment())
    return True


def apply_print_values(block: BlockItem, text: str, dynamic: bool) -> None:
    block.print_text = text
    block.print_dynamic = bool(dynamic)
    block.subtitle = ""
    block.refresh_tooltip()
    block.update()


def apply_print_data(block: BlockItem, data: dict) -> None:
    if block.block_key == "print":
        apply_print_values(block, data.get("print_text", data.get("subtitle", "")), bool(data.get("print_dynamic", False)))


def print_block_to_data(block: BlockItem) -> dict:
    if block.block_key != "print":
        return {}
    return {"print_text": getattr(block, "print_text", block.subtitle), "print_dynamic": bool(getattr(block, "print_dynamic", False))}
