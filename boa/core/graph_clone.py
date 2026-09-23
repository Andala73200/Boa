from __future__ import annotations

from copy import deepcopy
from uuid import uuid4


def clone_graph_fragment(fragment: dict, offset: float = 40) -> dict:
    """Clone blocks, their internal links and every nested graph with fresh IDs."""
    cloned = deepcopy(fragment)
    graph = {
        "blocks": list(cloned.get("blocks", [])),
        "connections": list(cloned.get("connections", [])),
    }
    _remap_graph(graph)
    for block in graph["blocks"]:
        block["x"] = float(block.get("x", 0)) + offset
        block["y"] = float(block.get("y", 0)) + offset
    return graph


def _remap_graph(graph: dict) -> None:
    blocks = [item for item in graph.get("blocks", []) if isinstance(item, dict)]
    id_map = {
        str(block.get("id", "")): f"b_{uuid4().hex[:12]}"
        for block in blocks if str(block.get("id", ""))
    }
    pair_map: dict[str, str] = {}
    for block in blocks:
        old_id = str(block.get("id", ""))
        if old_id in id_map:
            block["id"] = id_map[old_id]
        target = str(block.get("decorator_target", ""))
        if target:
            block["decorator_target"] = id_map.get(target, "")
            block["decorator_attached"] = bool(block["decorator_target"])
        pair_id = str(block.get("tp_pair_id", ""))
        if pair_id:
            block["tp_pair_id"] = pair_map.setdefault(pair_id, f"tp_pair_{uuid4().hex[:12]}")
        if block.get("key") in {"for", "while"}:
            block.pop("loop_instance_number", None)
        for nested in _nested_graphs(block):
            _remap_graph(nested)
    valid_connections = []
    for connection in graph.get("connections", []):
        if not isinstance(connection, dict):
            continue
        source = id_map.get(str(connection.get("source", "")))
        target = id_map.get(str(connection.get("target", "")))
        if source and target:
            connection["source"] = source
            connection["target"] = target
            valid_connections.append(connection)
    graph["connections"] = valid_connections


def _nested_graphs(block: dict) -> list[dict]:
    result: list[dict] = []
    for key in ("inner_graph", "try_graph", "try_else_graph", "try_finally_graph", "with_graph"):
        value = block.get(key)
        if isinstance(value, dict) and value:
            result.append(value)
    for key in ("try_handlers", "match_cases"):
        result.extend(
            item["graph"] for item in block.get(key, [])
            if isinstance(item, dict) and isinstance(item.get("graph"), dict)
        )
    for section in block.get("python_sections", []):
        if not isinstance(section, dict):
            continue
        if isinstance(section.get("graph"), dict):
            result.append(section["graph"])
        result.extend(
            item["graph"] for item in section.get("sections", [])
            if isinstance(item, dict) and isinstance(item.get("graph"), dict)
        )
    return result
