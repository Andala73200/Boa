from PySide6.QtGui import QColor

from boa.blocks import create_block
from boa.blocks.base_block import BlockItem
from boa.blocks.block_factory import (
    apply_call_config, apply_for_outputs, create_assign_block, create_call_block, create_input_block,
    create_module_block, create_operator_block, create_tp_block, create_value_block,
    create_variable_block,
)
from boa.blocks.definition_blocks import (
    DecoratorBlockItem, create_decorator_block, create_definition_marker, create_return_block,
)
from boa.blocks.python_native_blocks import (
    apply_await_flow, apply_class_attribute, apply_multi_assign, apply_return_values,
    apply_set_item_count, create_attribute_get_block, create_await_block, create_class_attribute_block, create_match_block,
    create_multi_assign_block, create_set_literal_block, create_try_block, create_with_block,
)
from boa.blocks.python_block import python_block_from_data, python_block_to_data
from boa.blocks.smart_block import SmartBlockItem
from boa.core.module_registry import MODULE_SPECS
from boa.core.operator_specs import OPERATOR_SPECS
from boa.functions.blocks import create_def_anchor, create_def_port_block
from boa.ui.block_titles import retranslate_block
from boa.ui.print_block_edit import apply_print_data, print_block_to_data


def block_from_data(data: dict) -> BlockItem:
    key = str(data.get("key", "empty"))
    if key == "python_node":
        block = python_block_from_data(data)
    elif key == "decorator":
        block = create_decorator_block(str(data.get("decorator_expression", "decorateur")))
    elif key in {"def_marker", "class_marker"}:
        block = create_definition_marker(
            key,
            str(data.get("definition_name", data.get("subtitle", "définition"))),
            str(data.get("definition_id", "")),
            list(data.get("definition_captures", [])),
        )
    elif key == "return":
        block = create_return_block(list(data.get("return_values", [])))
    elif key == "attribute_get":
        block = create_attribute_get_block(str(data.get("attribute_name", "attribut")))
    elif key == "class_attribute":
        block = create_class_attribute_block(
            str(data.get("attribute_name", "attribut")),
            str(data.get("attribute_annotation", "")),
            bool(data.get("attribute_has_default", False)),
        )
    elif key == "multi_assign":
        block = create_multi_assign_block(list(data.get("assign_targets", [])))
    elif key == "try":
        handlers = list(data.get("try_handlers", []))
        block = create_try_block(handlers, bool(data.get("try_else_graph")), bool(data.get("try_finally_graph")))
        block.try_graph = data.get("try_graph", {}) or {}
        block.try_handlers = handlers
        block.try_else_graph = data.get("try_else_graph", {}) or {}
        block.try_finally_graph = data.get("try_finally_graph", {}) or {}
    elif key == "match":
        block = create_match_block(list(data.get("match_cases", [])))
        block.match_cases = list(data.get("match_cases", []))
    elif key == "with":
        block = create_with_block(list(data.get("with_items", [])), bool(data.get("with_async", False)))
        block.with_items = list(data.get("with_items", []))
        block.with_graph = data.get("with_graph", {}) or {}
        block.with_async = bool(data.get("with_async", False))
    elif key == "await":
        block = create_await_block(bool(data.get("await_flow", False)))
        block.await_flow = bool(data.get("await_flow", False))
    elif key == "set_literal":
        block = create_set_literal_block(int(data.get("set_item_count", 1) or 1))
        block.set_item_count = int(data.get("set_item_count", 1) or 1)
    elif key == "assign":
        block = create_assign_block(data.get("variable_name", data.get("subtitle", "variable")), data.get("variable_type", "any"))
        block.python_annotation = str(data.get("python_annotation", ""))
        block.python_target = str(data.get("python_target", ""))
    elif key == "variable":
        block = create_variable_block(data.get("variable_name", data.get("subtitle", "variable")), data.get("variable_type", "any"), bool(data.get("variable_constant", False)))
        block.variable_capture = bool(data.get("variable_capture", False))
    elif key == "tp":
        block = create_tp_block(data.get("tp_role", "out"), int(data.get("tp_number", 1)), data.get("tp_pair_id", ""))
        block.tp_value_type = data.get("tp_value_type", "random")
        for port in block.ports:
            port.value_type = block.tp_value_type
    elif key == "value":
        block = create_value_block(data.get("value_type", "any"), data.get("value_value", data.get("subtitle", "")))
    elif key == "input":
        block = create_input_block(data.get("input_type", "str"), data.get("input_prompt", data.get("subtitle", "Saisie ?")), data.get("input_default", ""))
    elif key == "call":
        block = create_call_block(data.get("call_target", data.get("subtitle", "math.sqrt")), int(data.get("call_arg_count", 1) or 0), data.get("call_result_type", "any"))
        block.call_flow = bool(data.get("call_flow", True))
        apply_call_config(
            block,
            str(data.get("call_target", data.get("subtitle", "math.sqrt"))),
            int(data.get("call_arg_count", 1) or 0),
            str(data.get("call_result_type", "any")),
            int(data.get("call_vararg_count", 0) or 0),
            list(data.get("call_kwarg_names", [])),
            list(data.get("call_arg_labels", [])),
        )
        block.call_kind = str(data.get("call_kind", "python"))
        block.function_id = str(data.get("function_id", ""))
        block.function_inputs = list(data.get("function_inputs", []))
        block.function_outputs = list(data.get("function_outputs", []))
        block.function_vararg_port = str(data.get("function_vararg_port", ""))
        block.function_kwarg_port = str(data.get("function_kwarg_port", ""))
    elif key in {"function_start", "function_return"}:
        block = create_def_anchor(key)
        if key == "function_return":
            apply_return_values(block, list(data.get("return_values", [])))
    elif key in {"def_input", "def_input_p", "def_output", "def_output_p"}:
        block = create_def_port_block(key, data)
    elif key in MODULE_SPECS:
        block = create_module_block(key, data.get("module_config", {}))
    elif key in OPERATOR_SPECS:
        block = create_operator_block(key)
    else:
        block = create_block(key)
        block.title = data.get("title", block.title)
        block.subtitle = data.get("subtitle", block.subtitle)

    block.uid = str(data.get("id", ""))
    block.block_key = key
    block.color = QColor(data.get("color", block.color.name()))
    block.comment = str(data.get("comment", "") or "")
    block.protected = key == "run" or bool(data.get("protected", False))
    raw_class_order = data.get("class_order", -1)
    block.class_order = int(raw_class_order if raw_class_order is not None else -1)
    if key == "if":
        block.python_has_else = data.get("python_has_else")
    if key == "for":
        apply_for_outputs(block, list(data.get("for_temp_outputs", [])))
        block.python_async = bool(data.get("python_async", False))
    if key in {"for", "while"}:
        block.inner_graph = data.get("inner_graph", {}) or {}
        block.loop_instance_number = int(data.get("loop_instance_number", 0) or 0)
    if isinstance(block, DecoratorBlockItem):
        block.decorator_target = str(data.get("decorator_target", ""))
        block.decorator_order = int(data.get("decorator_order", 0) or 0)
        block.decorator_attached = bool(data.get("decorator_attached", bool(block.decorator_target)))
        block.stack_collapsed = bool(data.get("stack_collapsed", False))
        block.refresh_tooltip()
    if key in {"def_marker", "class_marker"}:
        block.definition_id = str(data.get("definition_id", ""))
        block.definition_name = str(data.get("definition_name", block.subtitle))
        block.definition_captures = list(data.get("definition_captures", []))
    if isinstance(block, SmartBlockItem):
        block.raw_code = data.get("raw_code", "")
    apply_print_data(block, data)
    retranslate_block(block)
    block.setPos(float(data.get("x", 0)), float(data.get("y", 0)))
    return block


def block_to_data(block: BlockItem) -> dict:
    data = {
        "id": block.uid,
        "key": block.block_key,
        "title": block.title,
        "subtitle": block.subtitle,
        "color": block.color.name(),
        "x": block.pos().x(),
        "y": block.pos().y(),
    }
    if str(getattr(block, "comment", "")).strip():
        data["comment"] = block.comment
    if getattr(block, "protected", False):
        data["protected"] = True
    if int(getattr(block, "class_order", -1)) >= 0:
        data["class_order"] = int(block.class_order)
    if block.block_key == "python_node":
        data.update(python_block_to_data(block))
    if block.block_key == "decorator":
        data.update({
            "decorator_expression": getattr(block, "decorator_expression", "decorateur"),
            "decorator_target": getattr(block, "decorator_target", ""),
            "decorator_order": int(getattr(block, "decorator_order", 0)),
            "decorator_attached": bool(getattr(block, "decorator_attached", False)),
            "stack_collapsed": bool(getattr(block, "stack_collapsed", False)),
        })
    if block.block_key in {"def_marker", "class_marker"}:
        data.update({
            "definition_id": getattr(block, "definition_id", ""),
            "definition_name": getattr(block, "definition_name", block.subtitle),
            "definition_captures": list(getattr(block, "definition_captures", [])),
        })
    if block.block_key in {"return", "function_return"}:
        data["return_values"] = list(getattr(block, "return_values", []))
    if block.block_key == "attribute_get":
        data["attribute_name"] = getattr(block, "attribute_name", "attribut")
    if block.block_key == "class_attribute":
        data.update({
            "attribute_name": getattr(block, "attribute_name", "attribut"),
            "attribute_annotation": getattr(block, "attribute_annotation", ""),
            "attribute_has_default": bool(getattr(block, "attribute_has_default", False)),
        })
    if block.block_key == "multi_assign":
        data["assign_targets"] = list(getattr(block, "assign_targets", []))
    if block.block_key == "try":
        data.update({
            "try_graph": getattr(block, "try_graph", {}) or {},
            "try_handlers": list(getattr(block, "try_handlers", [])),
            "try_else_graph": getattr(block, "try_else_graph", {}) or {},
            "try_finally_graph": getattr(block, "try_finally_graph", {}) or {},
        })
    if block.block_key == "match":
        data["match_cases"] = list(getattr(block, "match_cases", []))
    if block.block_key == "with":
        data.update({
            "with_items": list(getattr(block, "with_items", [])),
            "with_graph": getattr(block, "with_graph", {}) or {},
            "with_async": bool(getattr(block, "with_async", False)),
        })
    if block.block_key == "await":
        data["await_flow"] = bool(getattr(block, "await_flow", False))
    if block.block_key == "set_literal":
        data["set_item_count"] = int(getattr(block, "set_item_count", 1) or 1)
    if block.block_key == "assign":
        data.update({"variable_name": getattr(block, "variable_name", block.subtitle), "variable_type": getattr(block, "variable_type", "any"), "python_annotation": getattr(block, "python_annotation", ""), "python_target": getattr(block, "python_target", "")})
    if block.block_key == "variable":
        data.update({
            "variable_name": getattr(block, "variable_name", block.subtitle),
            "variable_type": getattr(block, "variable_type", "any"),
            "variable_constant": bool(getattr(block, "variable_constant", False)),
            "variable_capture": bool(getattr(block, "variable_capture", False)),
        })
    if block.block_key == "tp":
        data.update({"tp_role": getattr(block, "tp_role", "out"), "tp_number": int(getattr(block, "tp_number", 1)), "tp_pair_id": getattr(block, "tp_pair_id", ""), "tp_value_type": getattr(block, "tp_value_type", "random")})
    if block.block_key == "value":
        data.update({"value_type": getattr(block, "value_type", "any"), "value_value": getattr(block, "value_value", block.subtitle)})
    if block.block_key == "input":
        data.update({"input_type": getattr(block, "input_type", "str"), "input_prompt": getattr(block, "input_prompt", block.subtitle), "input_default": getattr(block, "input_default", "")})
    if block.block_key == "call":
        data.update({
            "call_target": getattr(block, "call_target", block.subtitle),
            "call_arg_count": int(getattr(block, "call_arg_count", 0) or 0),
            "call_result_type": getattr(block, "call_result_type", "any"),
            "call_vararg_count": int(getattr(block, "call_vararg_count", 0) or 0),
            "call_kwarg_names": list(getattr(block, "call_kwarg_names", [])),
            "call_arg_labels": list(getattr(block, "call_arg_labels", [])),
            "call_kind": getattr(block, "call_kind", "python"),
            "function_id": getattr(block, "function_id", ""),
            "function_inputs": list(getattr(block, "function_inputs", [])),
            "function_outputs": list(getattr(block, "function_outputs", [])),
            "function_vararg_port": getattr(block, "function_vararg_port", ""),
            "function_kwarg_port": getattr(block, "function_kwarg_port", ""),
            "call_flow": bool(getattr(block, "call_flow", True)),
        })
    if block.block_key in {"def_input", "def_input_p", "def_output", "def_output_p"}:
        data.update({
            "def_port_id": getattr(block, "def_port_id", ""),
            "def_port_name": getattr(block, "def_port_name", "valeur"),
            "def_port_type": getattr(block, "def_port_type", "any"),
            "def_annotation": getattr(block, "def_annotation", ""),
            "def_required": bool(getattr(block, "def_required", True)),
            "def_default": getattr(block, "def_default", ""),
            "def_param_kind": getattr(block, "def_param_kind", "normal"),
            "def_call_mode": getattr(block, "def_call_mode", "normal"),
            "def_order": int(getattr(block, "def_order", 0)),
        })
    if block.block_key in MODULE_SPECS and getattr(block, "module_config", None) is not None:
        data["module_config"] = dict(block.module_config)
    if block.block_key == "if" and hasattr(block, "python_has_else"):
        data["python_has_else"] = getattr(block, "python_has_else")
    if block.block_key == "for":
        data["for_temp_outputs"] = list(getattr(block, "for_temp_outputs", []))
        if hasattr(block, "python_async"):
            data["python_async"] = bool(getattr(block, "python_async", False))
    if block.block_key in {"for", "while"}:
        data["inner_graph"] = getattr(block, "inner_graph", {}) or {}
        data["loop_instance_number"] = int(getattr(block, "loop_instance_number", 0) or 0)
    data.update(print_block_to_data(block))
    if isinstance(block, SmartBlockItem):
        data["raw_code"] = block.raw_code
    return data


def uid_number(uid: str) -> int:
    raw = str(uid).lstrip("b")
    return int(raw) if raw.isdigit() else 0
