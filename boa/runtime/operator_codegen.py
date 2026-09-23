from collections.abc import Callable

from boa.core.operator_specs import OPERATOR_SPECS


def is_operator_block(key: str) -> bool:
    return key in OPERATOR_SPECS


def operator_expr(block: dict, input_expr: Callable[[str, str], str]) -> str:
    spec = OPERATOR_SPECS.get(block.get("key", ""))
    if not spec:
        return "None"
    values = {p.key: input_expr(p.key, "None") for p in spec.inputs}
    try:
        return spec.expression.format(**values)
    except KeyError:
        return "None"
