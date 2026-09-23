from boa.blocks.base_block import BlockItem
from boa.blocks.block_factory import variable_ports


def rename_variable_blocks(blocks: list[BlockItem], old_name: str, new_name: str) -> bool:
    changed = False
    for block in blocks:
        if _is_variable(block, old_name):
            _set_variable_block(block, new_name, getattr(block, "variable_type", "any"), bool(getattr(block, "variable_constant", False)))
            changed = True
    return changed


def update_variable_blocks(blocks: list[BlockItem], name: str, value_type: str, is_constant: bool) -> bool:
    changed = False
    for block in blocks:
        if _is_variable(block, name):
            _set_variable_block(block, name, value_type, is_constant)
            changed = True
    return changed


def _is_variable(block: BlockItem, name: str) -> bool:
    return block.block_key == "variable" and getattr(block, "variable_name", "") == name


def _set_variable_block(block: BlockItem, name: str, value_type: str, is_constant: bool) -> None:
    block.variable_name = name; block.variable_type = value_type or "any"; block.variable_constant = bool(is_constant)
    block.title = "Variable [C]" if is_constant else "Variable"; block.subtitle = name
    block.prepareGeometryChange(); block.ports = variable_ports(block.variable_type, block.variable_constant)
    block.update()
    for connection in list(block.connections):
        connection.update_path()
