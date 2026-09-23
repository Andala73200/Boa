from PySide6.QtGui import QColor

from boa.blocks.base_block import BlockItem, PortDefinition
from boa.blocks.smart_block import SmartBlockItem
from boa.core.module_registry import FEATURED_MODULE_KEYS, MODULE_SPECS
from boa.core.module_specs import resolved_module_ports
from boa.core.operator_specs import OPERATOR_SPECS
from boa.functions.blocks import create_def_anchor, create_def_port_block
from boa.blocks.python_block import create_python_block
from boa.blocks.definition_blocks import create_decorator_block, create_definition_marker, create_return_block
from boa.blocks.python_native_blocks import (
    create_attribute_get_block, create_await_block, create_class_attribute_block, create_match_block,
    create_multi_assign_block, create_set_literal_block, create_try_block, create_with_block,
)


BLOCK_COLORS = {
    "if": QColor("#c62828"), "while": QColor("#ef6c00"), "for": QColor("#2e7d32"),
    "def": QColor("#1565c0"), "print": QColor("#6a1b9a"), "logic": QColor("#00838f"),
    "variable": QColor("#455a64"), "tp": QColor("#546e7a"), "internal": QColor("#37474f"),
    "value": QColor("#3949ab"), "input": QColor("#00796b"), "call": QColor("#00897b"), "run": QColor("#263238"),
    "math": QColor("#5e35b1"), "random": QColor("#00897b"), "operator": QColor("#6d4c41"),
    "datetime": QColor("#00695c"), "path": QColor("#455a64"), "system": QColor("#37474f"),
    "json": QColor("#ad6f00"), "csv": QColor("#2e7d32"), "collections": QColor("#3949ab"),
    "text": QColor("#7b1fa2"), "types": QColor("#5d4037"), "statistics": QColor("#283593"),
    "security": QColor("#00695c"), "archive": QColor("#546e7a"),
}


def create_block(block_key: str) -> BlockItem:
    if block_key == "empty": return SmartBlockItem()
    if block_key == "python_node": return create_python_block()
    if block_key == "decorator": return create_decorator_block()
    if block_key in {"def_marker", "class_marker"}: return create_definition_marker(block_key)
    if block_key == "return": return create_return_block()
    if block_key == "attribute_get": return create_attribute_get_block()
    if block_key == "class_attribute": return create_class_attribute_block()
    if block_key == "multi_assign": return create_multi_assign_block()
    if block_key == "try": return create_try_block()
    if block_key == "match": return create_match_block()
    if block_key == "with": return create_with_block()
    if block_key == "await": return create_await_block()
    if block_key == "set_literal": return create_set_literal_block()
    if block_key == "assign": return create_assign_block()
    if block_key == "if": return _if_block()
    if block_key == "while": return _while_block()
    if block_key == "for": return _for_block()
    if block_key in {"true", "false"}: return _boolean_constant_block(block_key)
    if block_key == "none": return _none_constant_block()
    if block_key in {"and", "or", "xor", "nand", "nor", "xnor"}: return _binary_logic_block(block_key)
    if block_key == "not": return _not_block()
    if block_key == "tp": return create_tp_block("out", 1, "")
    if block_key == "run": return _run_block()
    if block_key == "start": return _start_block()
    if block_key == "end": return _end_block()
    if block_key == "print": return _print_block()
    if block_key == "variable": return create_variable_block("variable", "any")
    if block_key == "value": return create_value_block("int", "0")
    if block_key == "input": return create_input_block("str", "Saisie ?", "")
    if block_key == "call": return create_call_block("math.sqrt", 1, "float")
    if block_key in MODULE_SPECS: return create_module_block(block_key)
    if block_key in OPERATOR_SPECS: return create_operator_block(block_key)
    if block_key in {"function_start", "function_return"}: return create_def_anchor(block_key)
    if block_key in {"def_input", "def_input_p", "def_output", "def_output_p"}: return create_def_port_block(block_key)
    return BlockItem(block_key, "", QColor("#5f6368"))


def create_module_block(block_key: str, config: dict | None = None) -> BlockItem:
    spec = MODULE_SPECS.get(block_key)
    if not spec:
        return BlockItem(block_key, "", BLOCK_COLORS["math"])
    values = default_module_config(spec)
    values.update(config or {})
    inputs, outputs = resolved_module_ports(spec, values)
    ports = []
    for i, port in enumerate(inputs):
        ports.append(PortDefinition(port.key, port.label, "input", port.value_type, "left", 30 + i * 26))
    for i, port in enumerate(outputs):
        ports.append(PortDefinition(port.key, port.label, "output", port.value_type, "right", 30 + i * 26))
    rows = max(len(inputs), len(outputs), 1)
    color = BLOCK_COLORS.get(spec.module, BLOCK_COLORS["math"])
    width = 210 if spec.fields or spec.flow else (190 if block_key in FEATURED_MODULE_KEYS else 150)
    block = BlockItem(spec.title, "", color, ports, width, max(58, 44 + rows * 26))
    block.block_key = block_key
    block.module_name = spec.module
    block.module_config = values
    return block


def default_module_config(spec) -> dict:
    return {field.key: field.default for field in getattr(spec, "fields", ())}


def apply_module_config(block: BlockItem, config: dict) -> None:
    spec = MODULE_SPECS.get(block.block_key)
    if not spec:
        return
    values = default_module_config(spec)
    values.update(config or {})
    inputs, outputs = resolved_module_ports(spec, values)
    ports = []
    for i, port in enumerate(inputs):
        ports.append(PortDefinition(port.key, port.label, "input", port.value_type, "left", 30 + i * 26))
    for i, port in enumerate(outputs):
        ports.append(PortDefinition(port.key, port.label, "output", port.value_type, "right", 30 + i * 26))
    block.prepareGeometryChange()
    block.module_config = values
    block.ports = ports
    block.HEIGHT = max(58, 44 + max(len(inputs), len(outputs), 1) * 26)
    block.update()
    block._update_connections()


def create_math_block(block_key: str) -> BlockItem:
    return create_module_block(block_key)


def create_operator_block(block_key: str) -> BlockItem:
    spec = OPERATOR_SPECS.get(block_key)
    if not spec:
        return BlockItem(block_key, "", BLOCK_COLORS["operator"])
    ports = [PortDefinition(p.key, p.label, "input", p.value_type, "left", 30 + i * 28) for i, p in enumerate(spec.inputs)]
    ports.append(PortDefinition("result", "", "output", spec.output_type, "right", 44))
    rows = max(len(spec.inputs), 1)
    block = BlockItem(spec.title, "", BLOCK_COLORS["operator"], ports, 86, max(70, 42 + rows * 24))
    block.block_key = block_key
    block.operator_key = block_key
    return block


def variable_ports(value_type: str, is_constant: bool) -> list[PortDefinition]:
    ports = [] if is_constant else [PortDefinition("in", "", "input", value_type or "any", "left", 26)]
    ports.append(PortDefinition("out", "", "output", value_type or "any", "right", 26))
    return ports



def create_assign_block(name: str = "variable", value_type: str = "any") -> BlockItem:
    ports = [
        PortDefinition("start", "start", "input", "flow", "left", 24),
        PortDefinition("value", "valeur", "input", value_type or "any", "left", 58),
        PortDefinition("done", "done", "output", "flow", "right", 24),
        PortDefinition("result", "résultat", "output", value_type or "any", "right", 58),
    ]
    block = BlockItem("AFFECTER", name or "variable", BLOCK_COLORS["variable"], ports, 180, 82)
    block.block_key = "assign"
    block.variable_name = name or "variable"
    block.variable_type = value_type or "any"
    block.python_annotation = ""
    return block

def create_variable_block(name: str, value_type: str = "any", is_constant: bool = False) -> BlockItem:
    title = "Variable [C]" if is_constant else "Variable"
    block = BlockItem(title, name or "variable", BLOCK_COLORS["variable"], variable_ports(value_type, is_constant), 150, 52)
    block.block_key = "variable"; block.variable_name = name or "variable"
    block.variable_type = value_type or "any"; block.variable_constant = bool(is_constant)
    return block


def create_tp_block(role: str, number: int, pair_id: str) -> BlockItem:
    role = "in" if role == "in" else "out"
    ports = [PortDefinition("tp", "", "input" if role == "in" else "output", "random", "left" if role == "in" else "right", 18)]
    block = BlockItem(f"TP#{number}", "", BLOCK_COLORS["tp"], ports, 78, 36)
    block.block_key = "tp"; block.tp_role = role; block.tp_number = int(number); block.tp_pair_id = pair_id
    block.tp_value_type = "random"
    return block


def create_value_block(value_type: str = "int", value: str = "0") -> BlockItem:
    ports = [PortDefinition("value", "", "output", value_type or "any", "right", 24)]
    block = BlockItem(f"VALUE {value_type or 'any'}", str(value), BLOCK_COLORS["value"], ports, 108, 48)
    block.block_key = "value"; block.value_type = value_type or "any"; block.value_value = str(value)
    return block


def create_input_block(value_type: str = "str", prompt: str = "Saisie ?", default: str = "") -> BlockItem:
    ports = [PortDefinition("start", "", "input", "flow", "left", 18), PortDefinition("done", "done", "output", "flow", "right", 18), PortDefinition("value", "value", "output", value_type or "any", "right", 42)]
    block = BlockItem(f"INPUT {value_type or 'any'}", prompt, BLOCK_COLORS["input"], ports, 150, 60)
    block.block_key = "input"; block.input_type = value_type or "any"; block.input_prompt = prompt; block.input_default = default
    return block



def call_ports(
    arg_count: int,
    result_type: str,
    vararg_count: int = 0,
    kwarg_names: list[str] | None = None,
    arg_labels: list[str] | None = None,
    flow: bool = True,
) -> list[PortDefinition]:
    count = max(0, min(32, int(arg_count or 0)))
    var_count = max(0, min(32, int(vararg_count or 0)))
    names = [str(name).strip() or f"kwarg_{index + 1}" for index, name in enumerate(kwarg_names or [])]
    labels = list(arg_labels or [])
    ports = []
    if flow:
        ports.extend([
            PortDefinition("start", "start", "input", "flow", "left", 24),
            PortDefinition("done", "done", "output", "flow", "right", 24),
        ])
    ports.append(PortDefinition("result", "result", "output", result_type or "any", "right", 58))
    row = 0
    for index in range(count):
        label = labels[index] if index < len(labels) and labels[index] else f"arg{index + 1}"
        ports.append(PortDefinition(f"arg_{index + 1}", label, "input", "any", "left", 58 + row * 26))
        row += 1
    for index in range(var_count):
        ports.append(PortDefinition(f"vararg_{index + 1}", f"arg_{index + 1}", "input", "any", "left", 58 + row * 26, "*args"))
        row += 1
    for index, name in enumerate(names):
        ports.append(PortDefinition(f"kwarg_{index + 1}", name, "input", "any", "left", 58 + row * 26, "**kwargs"))
        row += 1
    return ports


def create_call_block(target: str = "math.sqrt", arg_count: int = 1, result_type: str = "any") -> BlockItem:
    count = max(0, min(32, int(arg_count or 0)))
    block = BlockItem("CALL", target or "fonction", BLOCK_COLORS["call"], call_ports(count, result_type), 190, _call_height(count, 0, 0))
    block.block_key = "call"
    block.call_target = target or "fonction"
    block.call_arg_count = count
    block.call_result_type = result_type or "any"
    block.call_kind = "python"
    block.call_vararg_count = 0
    block.call_kwarg_names = []
    block.call_arg_labels = []
    block.call_flow = True
    block.function_id = ""
    block.function_inputs = []
    block.function_outputs = []
    return block


def apply_call_config(
    block: BlockItem,
    target: str,
    arg_count: int,
    result_type: str,
    vararg_count: int | None = None,
    kwarg_names: list[str] | None = None,
    arg_labels: list[str] | None = None,
) -> None:
    count = max(0, min(32, int(arg_count or 0)))
    var_count = int(getattr(block, "call_vararg_count", 0) if vararg_count is None else vararg_count)
    names = list(getattr(block, "call_kwarg_names", []) if kwarg_names is None else kwarg_names)
    labels = list(getattr(block, "call_arg_labels", []) if arg_labels is None else arg_labels)
    block.prepareGeometryChange()
    block.title = "CALL"
    block.subtitle = target or "fonction"
    block.call_target = target or "fonction"
    block.call_arg_count = count
    block.call_result_type = result_type or "any"
    block.call_kind = "python"
    block.function_id = ""
    block.function_inputs = []
    block.function_outputs = []
    block.call_vararg_count = max(0, var_count)
    block.call_kwarg_names = [str(name).strip() or f"kwarg_{index + 1}" for index, name in enumerate(names)]
    block.call_arg_labels = labels
    block.call_flow = bool(getattr(block, "call_flow", True))
    block.ports = call_ports(count, block.call_result_type, block.call_vararg_count, block.call_kwarg_names, labels, block.call_flow)
    block.HEIGHT = _call_height(count, block.call_vararg_count, len(block.call_kwarg_names))
    block.update()
    block._update_connections()


def _call_height(args: int, varargs: int, kwargs: int) -> int:
    rows = max(1, int(args) + int(varargs) + int(kwargs))
    return max(76, 76 + max(0, rows - 1) * 26)


def apply_for_outputs(block: BlockItem, names: list[str]) -> None:
    cleaned = []
    for name in names:
        name = str(name).strip()
        if name and name not in cleaned: cleaned.append(name)
    height = max(96, 96 + len(cleaned) * 26)
    ports = [PortDefinition("start", "start", "input", "flow", "left", 28), PortDefinition("iterable", "itérable", "input", "any", "left", 62), PortDefinition("end", "fin", "output", "flow", "right", 46)]
    ports += [PortDefinition(f"temp_{i}", name, "output", "any", "right", 84 + i * 26) for i, name in enumerate(cleaned)]
    block.prepareGeometryChange(); block.ports = ports; block.HEIGHT = height; block.for_temp_outputs = cleaned; block.update()


def _if_block() -> BlockItem:
    ports = [PortDefinition("start", "start", "input", "flow", "left", 30), PortDefinition("condition", "condition", "input", "bool", "left", 66), PortDefinition("true", "si vrai", "output", "flow", "right", 44), PortDefinition("false", "si faux", "output", "flow", "right", 82)]
    return BlockItem("if", "", BLOCK_COLORS["if"], ports, 210, 112)


def _while_block() -> BlockItem:
    ports = [PortDefinition("start", "start", "input", "flow", "left", 28), PortDefinition("condition", "condition", "input", "bool", "left", 62), PortDefinition("end", "fin", "output", "flow", "right", 46)]
    block = BlockItem("while", "", BLOCK_COLORS["while"], ports, 210, 96); block.inner_graph = {}; return block


def _for_block() -> BlockItem:
    block = BlockItem("for", "", BLOCK_COLORS["for"], [], 210, 96); block.inner_graph = {}; apply_for_outputs(block, []); return block


def _binary_logic_block(block_key: str) -> BlockItem:
    ports = [PortDefinition("a", "A", "input", "bool", "left", 34), PortDefinition("b", "B", "input", "bool", "left", 66), PortDefinition("out", "sortie", "output", "bool", "right", 50)]
    return BlockItem(block_key.upper(), "", BLOCK_COLORS["logic"], ports, 90, 100)


def _not_block() -> BlockItem:
    ports = [PortDefinition("in", "entrée", "input", "bool", "left", 28), PortDefinition("out", "sortie", "output", "bool", "right", 28)]
    return BlockItem("NOT", "", BLOCK_COLORS["logic"], ports, 80, 56)


def _boolean_constant_block(block_key: str) -> BlockItem:
    title = "TRUE" if block_key == "true" else "FALSE"
    block = BlockItem(title, "", BLOCK_COLORS["logic"], [PortDefinition("out", "", "output", "bool", "right", 18)], 82, 36)
    block.block_key = block_key; return block


def _none_constant_block() -> BlockItem:
    block = BlockItem("AUCUNE VALEUR", "", BLOCK_COLORS["logic"], [PortDefinition("out", "", "output", "any", "right", 18)], 144, 36)
    block.block_key = "none"
    return block


def _run_block() -> BlockItem:
    block = BlockItem("RUN", "", BLOCK_COLORS["run"], [PortDefinition("out", "", "output", "flow", "right", 20)], 82, 40)
    block.block_key = "run"
    block.protected = True
    return block


def _start_block() -> BlockItem:
    block = BlockItem("start", "", BLOCK_COLORS["internal"], [PortDefinition("out", "", "output", "flow", "right", 20)], 82, 40)
    block.block_key = "start"; return block


def _end_block() -> BlockItem:
    block = BlockItem("end", "", BLOCK_COLORS["internal"], [PortDefinition("in", "", "input", "flow", "left", 20)], 82, 40)
    block.block_key = "end"; return block


def _print_block() -> BlockItem:
    ports = [PortDefinition("start", "start", "input", "flow", "left", 38), PortDefinition("done", "done", "output", "flow", "right", 38)]
    block = BlockItem("print", "", BLOCK_COLORS["print"], ports, 170, 76)
    block.print_text = ""; block.print_dynamic = False; return block
