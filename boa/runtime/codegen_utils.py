import ast
import keyword
import re

_IDENT = re.compile(r"^[A-Za-z_]\w*$")


def ports(block: dict, kind: str) -> list[tuple[str, str]]:
    flow = {"if": ["start"], "while": ["start"], "for": ["start"], "print": ["start"], "input": ["start"], "assign": ["start"], "return": ["start"], "call": ["start"], "def_marker": ["start"], "class_marker": ["start"], "function_return": ["return"], "python_node": ["start"]}
    try:
        from boa.core.module_registry import MODULE_SPECS
        spec = MODULE_SPECS.get(str(block.get("key", "")))
        if spec and spec.flow:
            flow[str(block.get("key", ""))] = ["start"]
    except ImportError:
        pass
    return [(p, "flow") for p in flow.get(block.get("key"), [])] if kind == "input" else []


def literal(value: str, value_type: str) -> str:
    value = str(value)
    if value_type == "any": return value.strip() or "None"
    if value_type == "str": return repr(value)
    if value_type == "bytes": return repr(value.encode("utf-8"))
    if value_type == "bool": return "True" if value.strip().lower() in {"true", "1", "oui", "vrai", "yes"} else "False"
    try:
        if value_type == "int": return str(int(value or 0))
        if value_type == "float": return str(float(value or 0))
        if value_type in {"list", "dict", "tuple", "set"}: return repr(ast.literal_eval(value))
    except Exception:
        return "None"
    return repr(value)


def input_call_expr(block: dict) -> str:
    prompt = str(block.get("input_prompt", block.get("subtitle", "Saisie ?"))).strip() or "Saisie ?"
    default = str(block.get("input_default", ""))
    label = f"{prompt} [{default}] " if default else f"{prompt} "
    call = f"input({label!r})"
    if default: call = f"({call} or {default!r})"
    value_type = str(block.get("input_type", "str")).lower()
    if value_type == "str": return call
    if value_type == "bytes": return f"{call}.encode('utf-8')"
    if value_type in {"int", "float"}: return f"{value_type}({call})"
    if value_type == "bool": return f"{call}.strip().lower() in {{'1', 'true', 'vrai', 'oui', 'yes'}}"
    if value_type in {"list", "dict", "tuple", "set"}: return f"ast.literal_eval({call})"
    return call


def safe_name(name: str) -> str:
    name = str(name).strip()
    return name if _IDENT.match(name) and not keyword.iskeyword(name) else ""


def temp_name(block: dict, port: str) -> str:
    try: return list(block.get("for_temp_outputs", []))[int(port.split("_", 1)[1])]
    except Exception: return "__boa_item"


def safe_call_target(target: str) -> str:
    target = str(target).strip(); parts = target.split(".") if target else []
    return target if parts and all(safe_name(part) == part for part in parts) else ""


def only_imports(code: str) -> bool:
    try:
        body = ast.parse(code).body
    except (SyntaxError, ValueError):
        return False
    return bool(body) and all(isinstance(node, (ast.Import, ast.ImportFrom)) for node in body)
