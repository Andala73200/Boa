"""Façade de génération pour les modules standards.

La logique propre à chaque module vit dans ``boa.modules.<module>.codegen``.
"""

from collections.abc import Callable

from boa.core.common_specs import COMMON_SPECS
from boa.core.module_registry import MODULE_SPECS
from boa.core.module_specs import resolved_module_ports
from boa.modules.codegen_registry import BLOCK_HELPERS, EXPRESSION_HANDLERS, FLOW_HANDLERS, HELPERS


def is_common_block(key: str) -> bool:
    return key in COMMON_SPECS


def is_flow_module(key: str) -> bool:
    spec = MODULE_SPECS.get(key)
    return bool(spec and spec.flow)


def output_var(uid: str, port: str) -> str:
    clean_uid = str(uid or "tmp").replace("-", "_")
    clean_port = str(port or "result").replace("-", "_")
    return f"__boa_{clean_uid}_{clean_port}"


def common_expr(block: dict, port: str, input_expr: Callable[[str, str], str]) -> str:
    key = str(block.get("key", ""))
    if is_flow_module(key):
        return output_var(block.get("id", ""), port)
    handler = EXPRESSION_HANDLERS.get(key)
    return handler(block, port, input_expr) if handler else "None"


def flow_call(block: dict, input_expr: Callable[[str, str], str]) -> tuple[list[str], str]:
    key = str(block.get("key", ""))
    spec = MODULE_SPECS[key]
    _, outputs = resolved_module_ports(spec, block.get("module_config", {}))
    value_outputs = [port.key for port in outputs if port.value_type != "flow"]
    handler = FLOW_HANDLERS.get(key)
    return value_outputs, handler(block, input_expr) if handler else "None"


def helper_names(graph: dict) -> set[str]:
    names = set()
    for block in graph.get("blocks", []):
        names.update(BLOCK_HELPERS.get(str(block.get("key", "")), ()))
        names.update(helper_names(block.get("inner_graph", {}) or {}))
    return names


def helper_source(names: set[str]) -> str:
    return "\n\n".join(source.strip("\n") for key, source in HELPERS.items() if key in names)
