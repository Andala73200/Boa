from __future__ import annotations

from PySide6.QtGui import QColor

from boa.blocks.base_block import BlockItem, PortDefinition
from boa.blocks.python_native_blocks import create_return_block
from boa.functions.models import function_parameters, function_returns, visible_ports


FUNCTION_COLOR = QColor("#00897b")
DEF_COLOR = QColor("#1565c0")
INTERNAL_COLOR = QColor("#37474f")


def apply_project_call(block: BlockItem, function: dict, config: dict | None = None) -> None:
    config = dict(config or {})
    selected_inputs = list(config.get("visible_inputs", getattr(block, "function_inputs", [])))
    selected_outputs = list(config.get("visible_outputs", getattr(block, "function_outputs", [])))
    parameters = function_parameters(function)
    normal = [port for port in parameters if port.get("kind") == "normal"]
    args_port = next((port for port in parameters if port.get("kind") == "args"), None)
    kwargs_port = next((port for port in parameters if port.get("kind") == "kwargs"), None)
    inputs = visible_ports(normal, selected_inputs)
    outputs = visible_ports(function_returns(function), selected_outputs)

    vararg_count = int(getattr(block, "call_vararg_count", 1 if args_port else 0) or 0)
    if args_port:
        vararg_count = max(1, vararg_count)
    else:
        vararg_count = 0
    kwarg_names = list(getattr(block, "call_kwarg_names", ["kwarg_1"] if kwargs_port else []))
    if kwargs_port and not kwarg_names:
        kwarg_names = ["kwarg_1"]
    if not kwargs_port:
        kwarg_names = []

    flow = bool(getattr(block, "call_flow", True))
    ports = [PortDefinition("start", "start", "input", "flow", "left", 26)] if flow else []
    row = 0
    for port in inputs:
        ports.append(PortDefinition(port["id"], port["name"], "input", port["type"], "left", 58 + row * 26))
        row += 1
    if args_port:
        for index in range(vararg_count):
            ports.append(PortDefinition(_variadic_key(args_port["id"], "arg", index), f"arg_{index + 1}", "input", "any", "left", 58 + row * 26, "*args"))
            row += 1
    if kwargs_port:
        for index, name in enumerate(kwarg_names):
            ports.append(PortDefinition(_variadic_key(kwargs_port["id"], "kwarg", index), name, "input", "any", "left", 58 + row * 26, "**kwargs"))
            row += 1
    if flow:
        ports.append(PortDefinition("done", "done", "output", "flow", "right", 26))
    ports += [PortDefinition(port["id"], port["name"], "output", port["type"], "right", 58 + index * 26) for index, port in enumerate(outputs)]

    block.prepareGeometryChange()
    block.title = "APPEL"
    block.subtitle = str(function.get("name", "fonction"))
    block.call_kind = "project"
    block.function_id = str(function.get("id", ""))
    block.function_inputs = [port["id"] for port in inputs if not port["persistent"] and not port["required"]]
    block.function_outputs = [port["id"] for port in outputs if not port["persistent"] and not port["required"]]
    block.function_vararg_port = str(args_port.get("id", "")) if args_port else ""
    block.function_kwarg_port = str(kwargs_port.get("id", "")) if kwargs_port else ""
    block.call_vararg_count = vararg_count
    block.call_flow = flow
    block.call_kwarg_names = kwarg_names
    block.ports = ports
    block.HEIGHT = max(76, 50 + max(row, len(outputs), 1) * 26)
    block.update()
    block._update_connections()


def apply_missing_call(block: BlockItem) -> None:
    block.prepareGeometryChange()
    block.title = "APPEL"
    block.subtitle = "Fonction introuvable"
    block.ports = [
        PortDefinition("start", "start", "input", "flow", "left", 26),
        PortDefinition("done", "done", "output", "flow", "right", 26),
    ]
    block.HEIGHT = 76
    block.update()
    block._update_connections()


def create_def_anchor(key: str) -> BlockItem:
    if key == "function_start":
        block = BlockItem("DÉBUT", "", INTERNAL_COLOR, [PortDefinition("start", "start", "output", "flow", "right", 22)], 110, 44)
        block.block_key = key
        block.protected = True
        return block
    return create_return_block([], "function_return", True)


def create_def_port_block(key: str, data: dict | None = None) -> BlockItem:
    data = dict(data or {})
    is_input = key in {"def_input", "def_input_p"}
    param_kind = str(data.get("def_param_kind") or "normal") if is_input else "normal"
    persistent = key.endswith("_p") and param_kind == "normal"
    name = str(data.get("def_port_name") or ("parametre" if is_input else "resultat"))
    value_type = str(data.get("def_port_type") or "any")
    port = PortDefinition("value", "" if is_input else name, "output" if is_input else "input", value_type, "right" if is_input else "left", 28)
    title = ("ENTRÉE" if is_input else "SORTIE") + (" (P)" if persistent else "")
    prefix = "*" if param_kind == "args" else ("**" if param_kind == "kwargs" else "")
    block = BlockItem(title, f"{prefix}{name} : {value_type}", DEF_COLOR, [port], 175, 56)
    block.block_key = "def_input_p" if persistent and is_input else ("def_input" if is_input else key)
    block.def_port_id = str(data.get("def_port_id") or "")
    block.def_port_name = name
    block.def_port_type = value_type
    block.def_annotation = str(data.get("def_annotation") or "")
    block.def_param_kind = param_kind
    block.def_call_mode = str(data.get("def_call_mode") or "normal") if param_kind == "normal" else "normal"
    block.def_required = bool(data.get("def_required", persistent if is_input else False))
    block.def_default = str(data.get("def_default") or "")
    block.def_order = int(data.get("def_order", 0) or 0)
    return block


def apply_def_port_config(
    block: BlockItem,
    name: str,
    value_type: str,
    required: bool,
    default: str,
    param_kind: str = "normal",
    persistent: bool = False,
) -> None:
    is_input = block.block_key in {"def_input", "def_input_p"}
    kind = param_kind if is_input and param_kind in {"normal", "args", "kwargs"} else "normal"
    persistent = bool(persistent and is_input and kind == "normal")
    block.prepareGeometryChange()
    block.block_key = "def_input_p" if persistent else ("def_input" if is_input else block.block_key)
    block.def_port_name = name
    block.def_port_type = value_type
    block.def_param_kind = kind
    block.def_call_mode = str(getattr(block, "def_call_mode", "normal")) if kind == "normal" else "normal"
    block.def_required = bool(required if kind == "normal" else False)
    block.def_default = str(default if kind == "normal" else "")
    prefix = "*" if kind == "args" else ("**" if kind == "kwargs" else "")
    block.title = ("ENTRÉE" if is_input else "SORTIE") + (" (P)" if persistent else "")
    block.subtitle = f"{prefix}{name} : {value_type}"
    block.ports[0].label = "" if is_input else name
    block.ports[0].value_type = value_type
    block.update()
    block._update_connections()


def _variadic_key(port_id: str, kind: str, index: int) -> str:
    return f"{port_id}__{kind}_{index + 1}"
