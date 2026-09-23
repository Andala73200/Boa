from collections.abc import Callable

from boa.core.math_specs import MATH_SPECS
from boa.runtime.module_codegen import module_expr


def is_math_block(key: str) -> bool:
    return key in MATH_SPECS


def math_expr(block: dict, port: str, input_expr: Callable[[str, str], str]) -> str:
    return module_expr(block, port, input_expr)


def graph_uses_math(graph: dict) -> bool:
    for block in graph.get("blocks", []):
        if is_math_block(block.get("key", "")):
            return True
        if graph_uses_math(block.get("inner_graph", {}) or {}):
            return True
    return False
