from collections.abc import Callable

from boa.core.module_registry import MODULE_SPECS, imports_for_block
from boa.core.module_specs import resolved_module_expressions
from boa.runtime.common_codegen import common_expr, is_common_block, is_flow_module


def is_module_block(key: str) -> bool:
    return key in MODULE_SPECS


def module_expr(block: dict, port: str, input_expr: Callable[[str, str], str]) -> str:
    if is_common_block(str(block.get("key", ""))):
        return common_expr(block, port, input_expr)
    spec = MODULE_SPECS.get(block.get("key", ""))
    if not spec:
        return "None"
    expressions = resolved_module_expressions(spec, block.get("module_config", {}))
    template = expressions.get(port) or expressions.get("result") or "None"
    values = {item.key: input_expr(item.key, "None") for item in spec.inputs}
    try:
        return template.format(**values)
    except KeyError:
        return "None"


def graph_used_modules(graph: dict) -> set[str]:
    modules = set()
    for block in graph.get("blocks", []):
        modules.update(imports_for_block(str(block.get("key", ""))))
        modules.update(graph_used_modules(block.get("inner_graph", {}) or {}))
    return modules


def is_flow_module_block(key: str) -> bool:
    return is_flow_module(key)
