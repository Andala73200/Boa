from __future__ import annotations

import re


def python_output_expr(block: dict, port: str) -> str:
    if block.get("python_expression"):
        return str(block.get("python_source", "None") or "None")
    if not str(port).startswith("output_"):
        return "None"
    try:
        index = int(str(port).split("_", 1)[1])
        return str(block.get("python_outputs", [])[index])
    except (ValueError, IndexError, TypeError):
        return "None"


def function_header(function: dict, current_name: str) -> tuple[list[str], str]:
    decorators = [str(item).strip() for item in function.get("python_decorators", []) if str(item).strip()]
    header = str(function.get("python_header", "")).strip()
    if not header:
        return decorators, ""
    header = re.sub(
        r"^(\s*(?:async\s+)?def\s+)[A-Za-z_]\w*",
        lambda match: match.group(1) + current_name,
        header,
        count=1,
    )
    return decorators, header
