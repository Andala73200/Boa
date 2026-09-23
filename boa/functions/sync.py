from __future__ import annotations

from boa.functions.models import function_parameters, function_returns, visible_ports


def synchronize_calls(graph: dict, functions: dict, function_id: str | None = None) -> bool:
    changed = False; blocks = {str(block.get("id", "")): block for block in graph.get("blocks", [])}
    allowed: dict[str, tuple[set[str], set[str]]] = {}
    for uid, block in blocks.items():
        if block.get("key") != "call" or block.get("call_kind") != "project": continue
        fid = str(block.get("function_id", ""))
        if function_id and fid != function_id: continue
        function = functions.get(fid)
        if not function: allowed[uid] = ({"start"}, {"done"}); continue
        inputs = visible_ports(function_parameters(function), block.get("function_inputs", []))
        outputs = visible_ports(function_returns(function), block.get("function_outputs", []))
        allowed[uid] = ({"start", *[port["id"] for port in inputs]}, {"done", *[port["id"] for port in outputs]})
        name = str(function.get("name", "fonction"))
        if block.get("subtitle") != name: block["subtitle"] = name; changed = True
    kept = []
    for connection in graph.get("connections", []):
        source = str(connection.get("source", "")); target = str(connection.get("target", ""))
        valid = (source not in allowed or connection.get("source_port") in allowed[source][1]) and (target not in allowed or connection.get("target_port") in allowed[target][0])
        if valid: kept.append(connection)
        else: changed = True
    if changed: graph["connections"] = kept
    for block in blocks.values():
        inner = block.get("inner_graph")
        if isinstance(inner, dict): changed = synchronize_calls(inner, functions, function_id) or changed
    return changed
