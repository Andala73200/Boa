from boa.blocks.base_block import BlockItem
from boa.ui.connection_item import ConnectionItem


def refresh_tp_types(blocks: list[BlockItem], connections: list[ConnectionItem]) -> None:
    pairs = _tp_pairs(blocks)
    for pair_id, pair_blocks in pairs.items():
        value_type = _incoming_type(pair_blocks, connections)
        for block in pair_blocks:
            block.tp_value_type = value_type
            for port in block.ports:
                port.value_type = value_type
            block.update()
            for connection in list(block.connections):
                connection.update_path()


def _tp_pairs(blocks: list[BlockItem]) -> dict[str, list[BlockItem]]:
    pairs: dict[str, list[BlockItem]] = {}
    for block in blocks:
        if block.block_key == "tp":
            pairs.setdefault(getattr(block, "tp_pair_id", block.uid), []).append(block)
    return pairs


def _incoming_type(pair_blocks: list[BlockItem], connections: list[ConnectionItem]) -> str:
    receivers = [block for block in pair_blocks if getattr(block, "tp_role", "out") == "in"]
    for connection in connections:
        if connection.target_block in receivers:
            source_port = connection.source_block.port_definition(connection.source_port)
            value_type = source_port.value_type if source_port else "random"
            return value_type or "random"
    return "random"
