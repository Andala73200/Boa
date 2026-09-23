STATUS_NORMAL = "normal"
STATUS_FLOW = "flow"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"
STATUS_CONFLICT = "conflict"

_NUMERIC_WARNINGS = {
    ("int", "float"),
    ("bool", "int"),
    ("int", "bool"),
    ("float", "bool"),
    ("list", "bool"),
    ("dict", "bool"),
    ("tuple", "bool"),
    ("set", "bool"),
}


def preview_connection_status(connections, source, source_port: str, target, target_port: str) -> str:
    if _conflicts_on_input(connections, target, target_port):
        return STATUS_CONFLICT
    return _type_status(source, source_port, target, target_port)


def connection_status(connections, connection) -> str:
    if _conflicts_on_input(connections, connection.target_block, connection.target_port):
        return STATUS_CONFLICT
    return _type_status(connection.source_block, connection.source_port, connection.target_block, connection.target_port)


def refresh_connection_statuses(connections) -> None:
    all_connections = list(connections)
    for item in all_connections:
        item.set_status(connection_status(all_connections, item))


def input_port_occupied(connections, target, target_port: str) -> bool:
    return input_port_count(connections, target, target_port) > 0


def input_port_count(connections, target, target_port: str) -> int:
    return sum(item.target_block is target and item.target_port == target_port for item in connections)


def _conflicts_on_input(connections, target, target_port: str) -> bool:
    port = target.port_definition(target_port)
    return bool(port and port.value_type != "flow" and input_port_count(connections, target, target_port) > 1)


def _type_status(source, source_port: str, target, target_port: str) -> str:
    src = source.port_definition(source_port)
    dst = target.port_definition(target_port)
    if source is target or not src or not dst or src.kind != "output" or dst.kind != "input":
        return STATUS_ERROR
    source_type = src.value_type or "any"
    target_type = dst.value_type or "any"
    source_type = "any" if source_type == "random" else source_type
    target_type = "any" if target_type == "random" else target_type
    if source_type == target_type:
        return STATUS_FLOW if source_type == "flow" else STATUS_NORMAL
    if "flow" in {source_type, target_type}:
        return STATUS_ERROR
    if target_type == "any":
        return STATUS_NORMAL
    if source_type == "any" or (source_type, target_type) in _NUMERIC_WARNINGS:
        return STATUS_WARNING
    return STATUS_ERROR
