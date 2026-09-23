from __future__ import annotations

import ast


TRY_STAR_TYPE = getattr(ast, "TryStar", None)
TRY_TYPES = (ast.Try,) + ((TRY_STAR_TYPE,) if TRY_STAR_TYPE is not None else ())


def node_identity(node: ast.stmt) -> tuple[str, str]:
    if isinstance(node, ast.Match): return "condition", "Correspondance (match)"
    if isinstance(node, TRY_TYPES + (ast.Raise, ast.Assert)): return "exception", "Gestion d’exception"
    if isinstance(node, (ast.With, ast.AsyncWith)): return "context", "Contexte Python (with)"
    if isinstance(node, (ast.Break, ast.Continue)): return "statement", "Interrompre" if isinstance(node, ast.Break) else "Continuer"
    titles = {ast.Pass: "Pass", ast.Delete: "Supprimer (del)", ast.Global: "Variables globales", ast.Nonlocal: "Variables non locales"}
    return "statement", titles.get(type(node), type(node).__name__)


def sections_for(node: ast.stmt, inner_graph) -> list[dict]:
    if isinstance(node, (ast.With, ast.AsyncWith)):
        prefix = "async with" if isinstance(node, ast.AsyncWith) else "with"
        items = ", ".join(ast.unparse(item) for item in node.items)
        return [{"header": f"{prefix} {items}:", "graph": inner_graph(node.body)}]
    if isinstance(node, TRY_TYPES):
        sections = [{"header": "try:", "graph": inner_graph(node.body)}]
        star = "*" if TRY_STAR_TYPE is not None and isinstance(node, TRY_STAR_TYPE) else ""
        for handler in node.handlers:
            suffix = f" {ast.unparse(handler.type)}" if handler.type else ""
            if handler.name:
                suffix += f" as {handler.name}"
            sections.append({"header": f"except{star}{suffix}:", "graph": inner_graph(handler.body)})
        if node.orelse:
            sections.append({"header": "else:", "graph": inner_graph(node.orelse)})
        if node.finalbody:
            sections.append({"header": "finally:", "graph": inner_graph(node.finalbody)})
        return sections
    if isinstance(node, ast.Match):
        sections = []
        for case in node.cases:
            guard = f" if {ast.unparse(case.guard)}" if case.guard else ""
            sections.append({"header": f"case {ast.unparse(case.pattern)}{guard}:", "graph": inner_graph(case.body)})
        return [{"header": f"match {ast.unparse(node.subject)}:", "sections": sections}]
    return []
