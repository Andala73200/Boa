from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OperatorPortSpec:
    key: str
    label: str
    value_type: str


@dataclass(frozen=True, slots=True)
class OperatorBlockSpec:
    key: str
    title: str
    description: str
    inputs: tuple[OperatorPortSpec, ...]
    output_type: str
    expression: str


A = OperatorPortSpec("a", "a", "any")
B = OperatorPortSpec("b", "b", "any")


def _op(name: str, title: str, desc: str, out_type: str, expr: str) -> OperatorBlockSpec:
    return OperatorBlockSpec(f"op_{name}", title, desc, (A, B), out_type, expr)


OPERATOR_SPECS: dict[str, OperatorBlockSpec] = {spec.key: spec for spec in [
    _op("add", "+", "Addition.", "any", "({a} + {b})"),
    _op("sub", "−", "Soustraction.", "any", "({a} - {b})"),
    _op("mul", "×", "Multiplication.", "any", "({a} * {b})"),
    _op("div", "÷", "Division.", "float", "({a} / {b})"),
    _op("floordiv", "//", "Division entière.", "any", "({a} // {b})"),
    _op("mod", "%", "Modulo.", "any", "({a} % {b})"),
    _op("pow", "**", "Puissance Python.", "any", "({a} ** {b})"),
    _op("eq", "=", "Égalité.", "bool", "({a} == {b})"),
    _op("ne", "≠", "Différent.", "bool", "({a} != {b})"),
    _op("gt", ">", "Supérieur.", "bool", "({a} > {b})"),
    _op("lt", "<", "Inférieur.", "bool", "({a} < {b})"),
    _op("ge", "≥", "Supérieur ou égal.", "bool", "({a} >= {b})"),
    _op("le", "≤", "Inférieur ou égal.", "bool", "({a} <= {b})"),
]}

OPERATOR_BLOCK_KEYS = set(OPERATOR_SPECS)
