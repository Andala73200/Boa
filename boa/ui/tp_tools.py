from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QMessageBox, QSpinBox

from boa.blocks.base_block import BlockItem
from boa.ui.block_comment_dialog import add_comment_row, apply_comment
from boa.i18n import tr


def next_tp_number(blocks: list[BlockItem]) -> int:
    used = {int(getattr(block, "tp_number", 0)) for block in blocks if block.block_key == "tp"}
    number = 1
    while number in used:
        number += 1
    return number


def edit_tp_number(parent, blocks: list[BlockItem], block: BlockItem) -> bool:
    current = int(getattr(block, "tp_number", 1))
    dialog = QDialog(parent); dialog.setWindowTitle("TP")
    form = QFormLayout(dialog); number = QSpinBox(); number.setRange(1, 9999); number.setValue(current)
    form.addRow(tr("tp_dialog.number"), number); comment_edit = add_comment_row(form, block)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); form.addRow(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    value = number.value(); old_comment = block.comment
    pair_id = getattr(block, "tp_pair_id", "")
    if _number_used_by_other_pair(blocks, value, pair_id):
        QMessageBox.warning(parent, "TP", tr("tp_dialog.exists", number=value))
        return False
    if value != current:
        for item in blocks:
            if item.block_key == "tp" and getattr(item, "tp_pair_id", "") == pair_id:
                item.tp_number = value; item.title = f"TP#{value}"; item.update()
    apply_comment(block, comment_edit)
    return value != current or block.comment != old_comment


def _number_used_by_other_pair(blocks: list[BlockItem], number: int, pair_id: str) -> bool:
    for block in blocks:
        if block.block_key != "tp":
            continue
        if getattr(block, "tp_pair_id", "") != pair_id and int(getattr(block, "tp_number", 0)) == number:
            return True
    return False
