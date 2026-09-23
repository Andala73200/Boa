from boa.modules.types.helpers import HELPERS


def expression(block: dict, port: str, input_expr) -> str:
    key = str(block.get("key", ""))
    mode = str(dict(block.get("module_config", {}) or {}).get("mode", ""))
    a = lambda name, default="None": input_expr(name, default)
    target = _type_object(mode)
    if key == "type_convert": return f"__boa_convert({a('value')}, {target})" if mode else "None"
    if key == "type_test": return f"isinstance({a('value')}, {target})" if mode else "False"
    if key == "type_convertible": return f"__boa_can_convert({a('value')}, {target})" if mode else "False"
    if key == "type_name": return f"type({a('value')}).__name__"
    if key == "value_length": return f"len({a('value')})"
    return f"({a('fallback')} if {a('value')} is None else {a('value')})"


def _type_object(mode: str) -> str:
    return {"int": "int", "float": "float", "str": "str", "bool": "bool", "list": "list", "tuple": "tuple", "set": "set", "dict": "dict", "bytes": "bytes"}.get(mode, "object")


BLOCK_HELPERS = {"type_convert": {"scalar"}, "type_convertible": {"scalar"}}
