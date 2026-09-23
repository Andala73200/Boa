EXPRESSION_KEYS = {"value", "and", "or", "xor", "nand", "nor", "xnor", "not"}

from boa.runtime.module_codegen import is_module_block


def block_comment_lines(block: dict) -> list[str]:
    text = str(block.get("comment", "") or "").strip()
    if not text:
        return []
    return [f"# {line}" if line else "#" for line in text.splitlines()]


def expression_comment_lines(uid: str, port: str, incoming: dict, blocks: dict) -> list[str]:
    links = incoming.get((uid, port), [])
    if len(links) != 1:
        return []
    comments: list[str] = []
    visited: set[str] = set()
    _visit_expression(str(links[-1].get("source", "")), incoming, blocks, visited, comments)
    return comments


def _visit_expression(uid: str, incoming: dict, blocks: dict, visited: set[str], comments: list[str]) -> None:
    if not uid or uid in visited:
        return
    visited.add(uid)
    block = blocks.get(uid, {})
    key = str(block.get("key", ""))
    if key in {"variable", "input", "call"}:
        return
    for (target_uid, _port), links in incoming.items():
        if target_uid == uid and len(links) == 1:
            _visit_expression(str(links[0].get("source", "")), incoming, blocks, visited, comments)
    if key in EXPRESSION_KEYS or key.startswith("op_") or is_module_block(key):
        comments.extend(block_comment_lines(block))
