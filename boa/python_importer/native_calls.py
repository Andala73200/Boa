from __future__ import annotations

import ast


def input_spec(node: ast.AST) -> dict | None:
    value_type = "str"
    call = node
    if isinstance(node, ast.Call) and _name(node.func) in {"int", "float"}:
        if len(node.args) != 1 or node.keywords:
            return None
        value_type = _name(node.func)
        call = node.args[0]
    if not isinstance(call, ast.Call) or _name(call.func) != "input":
        return None
    if call.keywords or len(call.args) > 1:
        return None
    if call.args and not isinstance(call.args[0], ast.Constant):
        return None
    if call.args and not isinstance(call.args[0].value, str):
        return None
    return {
        "input_type": value_type,
        "input_prompt": str(call.args[0].value) if call.args else "",
        "input_has_prompt": bool(call.args),
        "input_default": "",
    }


def print_spec(node: ast.AST) -> dict | None:
    if not isinstance(node, ast.Call) or _name(node.func) != "print":
        return None
    if node.keywords or any(isinstance(arg, ast.Starred) for arg in node.args):
        return None
    dynamic = any(not _string_constant(arg) for arg in node.args)
    parts = [_print_part(arg, dynamic) for arg in node.args]
    return {
        "print_text": " ".join(parts),
        "print_dynamic": dynamic,
    }


def _print_part(node: ast.AST, dynamic: bool) -> str:
    if _string_constant(node):
        text = str(node.value)
        return text.replace("{", "{{").replace("}", "}}") if dynamic else text
    return "{" + ast.unparse(node) + "}"


def _string_constant(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _name(node: ast.AST) -> str:
    return node.id if isinstance(node, ast.Name) else ""
