from boa.i18n import tr
from boa.core.module_registry import MODULE_SPECS
from boa.core.module_specs import resolved_module_ports
from boa.blocks.python_native_blocks import (
    apply_await_flow, apply_match_cases, apply_multi_assign, apply_return_values, apply_set_item_count,
    apply_try_config, apply_with_config,
)


TRANSLATED_BLOCK_KEYS = {
    "and", "call", "def", "false", "for", "if", "input", "not", "or",
    "print", "run", "true", "false", "none", "value", "while", "xor", "nand", "nor", "xnor",
    "function_start", "function_return", "def_input", "def_input_p", "def_output", "def_output_p",
    "attribute_get", "class_attribute", "multi_assign", "try", "match", "with", "return",
    "await", "set_literal",
}


def retranslate_block(block) -> None:
    key = str(getattr(block, "block_key", ""))
    if key == "variable":
        block.title = tr("block.variable.constant_title") if bool(getattr(block, "variable_constant", False)) else tr("block.variable.title")
    elif key == "tp":
        block.title = f"TP#{int(getattr(block, 'tp_number', 1))}"
    elif key == "value":
        block.title = f"{tr('block.value.title')} {getattr(block, 'value_type', 'any')}"
    elif key == "input":
        block.title = f"{tr('block.input.title')} {getattr(block, 'input_type', 'any')}"
    elif key == "empty":
        if not str(getattr(block, "raw_code", "")).strip():
            block.title = tr("block.empty.title")
    elif key in {"return", "function_return"}:
        apply_return_values(block, list(getattr(block, "return_values", [])))
        block.title = tr(f"block.{key}.title")
    elif key == "multi_assign":
        apply_multi_assign(block, list(getattr(block, "assign_targets", [])))
        block.title = tr("block.multi_assign.title")
    elif key == "match":
        apply_match_cases(block, list(getattr(block, "match_cases", [])))
        block.title = tr("block.match.title")
    elif key == "try":
        apply_try_config(block, list(getattr(block, "try_handlers", [])), bool(getattr(block, "try_else_graph", {})), bool(getattr(block, "try_finally_graph", {})))
        block.title = tr("block.try.title")
    elif key == "with":
        apply_with_config(block, list(getattr(block, "with_items", [])), bool(getattr(block, "with_async", False)))
        block.title = tr("block.with.title")
    elif key == "await":
        apply_await_flow(block, bool(getattr(block, "await_flow", False)))
        block.title = tr("block.await.title")
    elif key == "set_literal":
        apply_set_item_count(block, int(getattr(block, "set_item_count", 1) or 1))
        block.title = tr("block.set_literal.title")
    elif key in MODULE_SPECS:
        spec = MODULE_SPECS[key]
        block.title = _translated(f"block.{key}.title", spec.title)
        inputs, outputs = resolved_module_ports(spec, getattr(block, "module_config", {}))
        port_specs = {item.key: item for item in (*inputs, *outputs)}
        for port in block.ports:
            item = port_specs.get(port.key)
            if item:
                generic = _translated(f"port.{item.key}", item.label)
                port.label = _translated(f"block.{key}.port.{item.key}", generic)
        if spec.fields:
            config = dict(getattr(block, "module_config", {}) or {})
            primary = next((field for field in spec.fields if field.key == spec.variant_field and field.kind == "choice"), None)
            if primary is None:
                primary = next((field for field in spec.fields if field.kind == "choice"), None)
            if primary:
                selected = str(config.get(primary.key, ""))
                block.subtitle = _translated(f"option.{selected}", selected) if selected else "----"
    elif key in TRANSLATED_BLOCK_KEYS:
        block.title = tr(f"block.{key}.title")
    if key not in MODULE_SPECS and key not in {"def_input", "def_input_p", "def_output", "def_output_p"}:
        for port in block.ports:
            specific = f"block.{key}.port.{port.key}"
            generic = f"port.{port.key}"
            if tr(specific) != specific:
                port.label = tr(specific)
            elif tr(generic) != generic:
                port.label = tr(generic)
    block.refresh_tooltip()
    block.update()


def _translated(key: str, fallback: str) -> str:
    value = tr(key)
    return fallback if value == key else value
