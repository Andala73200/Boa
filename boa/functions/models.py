from __future__ import annotations

import keyword
import re
from copy import deepcopy
from uuid import uuid4


VALUE_TYPES = ("any", "bool", "int", "float", "str", "list", "dict", "tuple", "set")
PARAM_KINDS = ("normal", "args", "kwargs")
CALL_MODES = ("normal", "posonly", "kwonly")
INPUT_KEYS = {"def_input", "def_input_p"}
OUTPUT_KEYS = {"def_output", "def_output_p"}
DEF_PORT_KEYS = INPUT_KEYS | OUTPUT_KEYS
_IDENTIFIER = re.compile(r"^[A-Za-z_]\w*$")


def new_function(name: str = "nouvelle_fonction") -> dict:
    return normalize_function({
        "id": f"function_{uuid4().hex[:10]}",
        "name": name,
        "description": "",
        "comment": "",
        "docstring": "",
        "imports": [],
        "variables": [],
        "captured_names": [],
        "owner_function_id": "",
        "owner_class_id": "",
        "graph": definition_graph(),
    })


def definition_graph() -> dict:
    return {
        "blocks": [
            {"id": "function_start", "key": "function_start", "title": "DÉBUT", "x": -420, "y": 0, "protected": True},
            {"id": "function_return", "key": "function_return", "title": "RETOUR", "x": 420, "y": 0, "protected": True},
        ],
        "connections": [],
    }


def normalize_functions(value) -> dict[str, dict]:
    items = value.values() if isinstance(value, dict) else (value if isinstance(value, list) else [])
    result: dict[str, dict] = {}
    for item in items:
        if isinstance(item, dict):
            function = normalize_function(item)
            result[function["id"]] = function
    return result


def normalize_function(value: dict) -> dict:
    data = deepcopy(value or {})
    data["id"] = str(data.get("id") or f"function_{uuid4().hex[:10]}")
    data["name"] = str(data.get("name") or "nouvelle_fonction").strip()
    data["description"] = str(data.get("description") or "")
    data["comment"] = str(data.get("comment") or "")
    data["docstring"] = str(data.get("docstring") or "")
    data["imports"] = _normalize_imports(data.get("imports", []))
    data["variables"] = _normalize_variables(data.get("variables", []))
    data["captured_names"] = [str(name) for name in data.get("captured_names", []) if str(name)]
    data["owner_function_id"] = str(data.get("owner_function_id") or "")
    data["owner_class_id"] = str(data.get("owner_class_id") or "")
    data["is_async"] = bool(data.get("is_async", False))
    data["return_annotation"] = str(data.get("return_annotation") or "")
    graph = deepcopy(data.get("graph")) if isinstance(data.get("graph"), dict) else definition_graph()
    graph.setdefault("blocks", [])
    graph.setdefault("connections", [])
    _migrate_legacy_definition(data, graph)
    data.pop("parameters", None)
    data.pop("returns", None)
    _ensure_anchors(graph)
    _normalize_port_blocks(graph)
    data["graph"] = graph
    return data


def function_parameters(function: dict) -> list[dict]:
    ports = _ports(function, INPUT_KEYS)
    return sorted(ports, key=lambda port: (int(port.get("order", 10**6)), float(port.get("x", 0)), float(port.get("y", 0))))


def function_returns(function: dict) -> list[dict]:
    return sorted(_ports(function, OUTPUT_KEYS), key=lambda port: (int(port.get("order", 10**6)), float(port.get("y", 0))))


def function_port(block: dict) -> dict:
    key = str(block.get("key", ""))
    parameter_kind = str(block.get("def_param_kind") or "normal")
    if parameter_kind not in PARAM_KINDS:
        parameter_kind = "normal"
    call_mode = str(block.get("def_call_mode") or "normal")
    if call_mode not in CALL_MODES or parameter_kind != "normal":
        call_mode = "normal"
    persistent = key.endswith("_p") and parameter_kind == "normal"
    return {
        "id": str(block.get("def_port_id") or f"port_{uuid4().hex[:10]}"),
        "name": str(block.get("def_port_name") or "valeur").strip(),
        "type": str(block.get("def_port_type") or "any"),
        "annotation": str(block.get("def_annotation") or ""),
        "required": bool(block.get("def_required", persistent if key in INPUT_KEYS else False)),
        "default": str(block.get("def_default") or ""),
        "persistent": persistent,
        "kind": parameter_kind,
        "call_mode": call_mode,
        "block_id": str(block.get("id", "")),
        "order": int(block.get("def_order", 10**6)),
        "x": float(block.get("x", 0)),
        "y": float(block.get("y", 0)),
    }


def visible_ports(ports: list[dict], selected: list[str] | None) -> list[dict]:
    chosen = set(selected or [])
    return [port for port in ports if port["persistent"] or port["required"] or port["id"] in chosen or port["kind"] != "normal"]


def valid_function_name(name: str) -> bool:
    return bool(_IDENTIFIER.fullmatch(str(name))) and not keyword.iskeyword(str(name))


def valid_port_name(name: str) -> bool:
    return valid_function_name(name)


def unique_function_name(functions: dict, base: str = "nouvelle_fonction") -> str:
    names = {str(item.get("name", "")) for item in functions.values()}
    candidate = base
    index = 1
    while candidate in names:
        index += 1
        candidate = f"{base}_{index}"
    return candidate


def _ports(function: dict, keys: set[str]) -> list[dict]:
    graph = normalize_function(function)["graph"]
    return [function_port(block) for block in graph["blocks"] if block.get("key") in keys]


def _ensure_anchors(graph: dict) -> None:
    keys = {block.get("key") for block in graph["blocks"]}
    if "function_start" not in keys:
        graph["blocks"].insert(0, definition_graph()["blocks"][0])
    if "function_return" not in keys:
        graph["blocks"].append(definition_graph()["blocks"][1])
    for block in graph["blocks"]:
        if block.get("key") in {"function_start", "function_return"}:
            block["protected"] = True


def _normalize_port_blocks(graph: dict) -> None:
    order = 0
    for block in graph["blocks"]:
        if block.get("key") not in DEF_PORT_KEYS:
            continue
        block["def_port_id"] = str(block.get("def_port_id") or f"port_{uuid4().hex[:10]}")
        block["def_port_name"] = str(block.get("def_port_name") or "valeur").strip()
        value_type = str(block.get("def_port_type") or "any")
        block["def_port_type"] = value_type if value_type in VALUE_TYPES else "any"
        block["def_annotation"] = str(block.get("def_annotation") or "")
        kind = str(block.get("def_param_kind") or "normal")
        block["def_param_kind"] = kind if kind in PARAM_KINDS else "normal"
        call_mode = str(block.get("def_call_mode") or "normal")
        block["def_call_mode"] = call_mode if call_mode in CALL_MODES else "normal"
        if block["def_param_kind"] != "normal":
            block["def_call_mode"] = "normal"
        if block["def_param_kind"] != "normal" and block.get("key") in INPUT_KEYS:
            block["key"] = "def_input"
        block["def_required"] = bool(block.get("def_required", str(block.get("key", "")).endswith("_p") if block.get("key") in INPUT_KEYS else False))
        block["def_default"] = str(block.get("def_default") or "")
        block["def_order"] = int(block.get("def_order", order))
        order += 1


def _normalize_imports(value) -> list[dict]:
    result = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict):
            statement = str(item.get("statement", "")).strip()
            if statement:
                result.append({"module": str(item.get("module", "")), "statement": statement, "origin": str(item.get("origin", "conversion Python"))})
        elif str(item).strip():
            result.append({"module": "", "statement": str(item).strip(), "origin": "conversion Python"})
    return result


def _migrate_legacy_definition(data: dict, graph: dict) -> None:
    old_input = next((block for block in graph["blocks"] if block.get("key") == "function_input"), None)
    old_output = next((block for block in graph["blocks"] if block.get("key") == "function_output"), None)
    if not old_input and not old_output:
        return
    replacements = {}
    for index, port in enumerate(data.get("parameters", [])):
        uid = f"def_input_{index + 1}"
        replacements[(str(old_input.get("id", "")) if old_input else "", str(port.get("id", "")))] = (uid, "value")
        graph["blocks"].append({"id": uid, "key": "def_input_p" if port.get("always_visible", True) else "def_input", "def_port_id": port.get("id"), "def_port_name": port.get("name"), "def_port_type": port.get("type", "any"), "def_required": port.get("required", True), "def_default": port.get("default", ""), "def_param_kind": "normal", "def_order": index, "x": float(old_input.get("x", -420) if old_input else -420), "y": index * 90})
    for index, port in enumerate(data.get("returns", [])):
        uid = f"def_output_{index + 1}"
        replacements[(str(old_output.get("id", "")) if old_output else "", str(port.get("id", "")))] = (uid, "value")
        graph["blocks"].append({"id": uid, "key": "def_output_p" if port.get("always_visible", True) else "def_output", "def_port_id": port.get("id"), "def_port_name": port.get("name"), "def_port_type": port.get("type", "any"), "def_required": False, "def_order": index, "x": float(old_output.get("x", 420) if old_output else 420), "y": index * 90})
    old_input_id = str(old_input.get("id", "")) if old_input else ""
    old_output_id = str(old_output.get("id", "")) if old_output else ""
    connections = []
    for item in graph["connections"]:
        connection = dict(item)
        source_key = (str(connection.get("source", "")), str(connection.get("source_port", "")))
        target_key = (str(connection.get("target", "")), str(connection.get("target_port", "")))
        if source_key == (old_input_id, "start"):
            connection.update(source="function_start", source_port="start")
        elif source_key in replacements:
            connection.update(source=replacements[source_key][0], source_port="value")
        if target_key == (old_output_id, "end"):
            connection.update(target="function_return", target_port="return")
        elif target_key in replacements:
            connection.update(target=replacements[target_key][0], target_port="value")
        connections.append(connection)
    graph["connections"] = connections
    graph["blocks"] = [block for block in graph["blocks"] if block.get("key") not in {"function_input", "function_output"}]


def _normalize_variables(value) -> list[dict]:
    result = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        result.append({
            "name": name,
            "type": str(item.get("type", "any") or "any"),
            "initial": str(item.get("initial", "") or ""),
            "constant": bool(item.get("constant", False)),
            "scope": str(item.get("scope", "local") or "local"),
        })
    return result
