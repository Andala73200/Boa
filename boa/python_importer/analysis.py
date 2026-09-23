from __future__ import annotations

import ast
import builtins
import io
import tokenize
from dataclasses import dataclass
from textwrap import dedent

_BUILTINS = set(dir(builtins))


@dataclass(slots=True)
class NameUsage:
    reads: list[str]
    writes: list[str]


class _UsageVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.reads: list[str] = []
        self.writes: list[str] = []

    def visit_Name(self, node: ast.Name) -> None:
        target = self.writes if isinstance(node.ctx, (ast.Store, ast.Del)) else self.reads
        if node.id not in target:
            target.append(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name not in self.writes:
            self.writes.append(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.name not in self.writes:
            self.writes.append(node.name)
        for base in node.bases:
            self.visit(base)
        for decorator in node.decorator_list:
            self.visit(decorator)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self.visit(node.body)


def name_usage(node: ast.AST) -> NameUsage:
    visitor = _UsageVisitor()
    visitor.visit(node)
    reads = [name for name in visitor.reads if name not in visitor.writes and name not in _BUILTINS]
    return NameUsage(reads, visitor.writes)


def node_source(source: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    if segment:
        result = dedent(segment).rstrip()
        if isinstance(node, ast.If) and result.lstrip().startswith("elif "):
            result = result.replace("elif ", "if ", 1)
        if result:
            return result
    lines = source.splitlines()
    start = max(0, int(getattr(node, "lineno", 1)) - 1)
    end = max(start + 1, int(getattr(node, "end_lineno", start + 1)))
    return dedent("\n".join(lines[start:end])).rstrip() or ast.unparse(node)


def comments_by_line(source: str) -> dict[int, str]:
    comments: dict[int, list[str]] = {}
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type == tokenize.COMMENT:
                comments.setdefault(token.start[0], []).append(token.string.lstrip("# "))
    except (tokenize.TokenError, IndentationError):
        return {}
    return {line: "\n".join(parts) for line, parts in comments.items()}


def leading_comment(node: ast.AST, comments: dict[int, str], source: str) -> str:
    lines = source.splitlines()
    line = int(getattr(node, "lineno", 1)) - 1
    result: list[str] = []
    while line > 0:
        previous = lines[line - 1].strip()
        if previous.startswith("#"):
            result.insert(0, comments.get(line, previous.lstrip("# ")))
            line -= 1
            continue
        break
    return "\n".join(result)


def infer_value_type(annotation: ast.AST | None) -> str:
    if annotation is None:
        return "any"
    text = ast.unparse(annotation)
    root = text.split("[", 1)[0].split(".")[-1]
    return root if root in {"bool", "int", "float", "str", "list", "dict", "tuple", "set"} else "any"


def scope_docstring(nodes: list[ast.stmt]) -> str:
    if nodes and isinstance(nodes[0], ast.Expr) and isinstance(nodes[0].value, ast.Constant) and isinstance(nodes[0].value.value, str):
        return str(nodes[0].value.value)
    return ""


def scope_body_without_docstring(nodes: list[ast.stmt]) -> list[ast.stmt]:
    return nodes[1:] if scope_docstring(nodes) else list(nodes)


def scope_imports(nodes: list[ast.stmt]) -> list[dict]:
    collector = _ScopeImportCollector()
    for node in nodes:
        collector.visit(node)
    return collector.items


class _ScopeImportCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.items: list[dict] = []

    def visit_Import(self, node: ast.Import) -> None:
        self._append(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self._append(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def _append(self, node: ast.Import | ast.ImportFrom) -> None:
        statement = ast.unparse(node)
        module = node.names[0].name.split(".", 1)[0] if isinstance(node, ast.Import) else (node.module or ".").split(".", 1)[0]
        if statement not in {item["statement"] for item in self.items}:
            self.items.append({"module": module, "statement": statement, "origin": "conversion Python"})



def scope_variables(
    nodes: list[ast.stmt],
    parameters: set[str] | None = None,
    scope: str = "local",
) -> list[dict]:
    """Return variables declared in one Python scope, preserving source order."""
    collector = _VariableCollector(set(parameters or ()), scope)
    for node in nodes:
        collector.visit(node)
    return collector.items()


def captured_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return free-looking names used by a function body.

    The graph builder later keeps only names that actually exist in the parent
    graph, which avoids turning module globals into fake closure ports.
    """
    module = ast.Module(body=list(node.body), type_ignores=[])
    usage = name_usage(module)
    parameters = {
        item.arg
        for item in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
            *((node.args.vararg,) if node.args.vararg else ()),
            *((node.args.kwarg,) if node.args.kwarg else ()),
        )
    }
    declared_nonlocal: list[str] = []

    class NonlocalFinder(ast.NodeVisitor):
        def visit_Nonlocal(self, item: ast.Nonlocal) -> None:
            for name in item.names:
                if name not in declared_nonlocal:
                    declared_nonlocal.append(name)

        def visit_FunctionDef(self, item: ast.FunctionDef) -> None:
            return

        visit_AsyncFunctionDef = visit_FunctionDef
        def visit_ClassDef(self, item: ast.ClassDef) -> None:
            return

    for statement in node.body:
        if isinstance(statement, ast.Nonlocal):
            for name in statement.names:
                if name not in declared_nonlocal:
                    declared_nonlocal.append(name)
        else:
            NonlocalFinder().visit(statement)
    result: list[str] = []
    for name in [*usage.reads, *declared_nonlocal]:
        if name not in parameters and name not in result:
            result.append(name)
    return result


class _VariableCollector(ast.NodeVisitor):
    def __init__(self, excluded: set[str], scope: str) -> None:
        self.excluded = excluded
        self.scope = scope
        self._items: dict[str, dict] = {}

    def items(self) -> list[dict]:
        return list(self._items.values())

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # The function object itself is represented by a DEF/Fonction locale block.
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in (*node.args.defaults, *(item for item in node.args.kw_defaults if item is not None)):
            self.visit(default)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # The class object itself is represented by a Classe block.
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)

    def visit_Import(self, node: ast.Import) -> None:
        return

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        return

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._targets(target, node.value, None)
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._targets(node.target, node.value, node.annotation)
        if node.value is not None:
            self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._targets(node.target, None, None)
        self.visit(node.value)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._targets(node.target, node.value, None)
        self.visit(node.value)

    def visit_For(self, node: ast.For) -> None:
        self._targets(node.target, None, None)
        self.visit(node.iter)
        for item in (*node.body, *node.orelse):
            self.visit(item)

    visit_AsyncFor = visit_For

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self._targets(item.optional_vars, None, None)
        for child in node.body:
            self.visit(child)

    visit_AsyncWith = visit_With

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self._targets(node.target, None, None)
        self.visit(node.iter)
        for item in node.ifs:
            self.visit(item)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self._add(str(node.name), None, None)
        if node.type is not None:
            self.visit(node.type)
        for item in node.body:
            self.visit(item)

    def _targets(self, target: ast.AST, value: ast.AST | None, annotation: ast.AST | None) -> None:
        if isinstance(target, ast.Name):
            self._add(target.id, value, annotation)
            return
        if isinstance(target, ast.Starred):
            self._targets(target.value, None, None)
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                self._targets(item, None, None)

    def _add(self, name: str, value: ast.AST | None, annotation: ast.AST | None) -> None:
        if not name or name in self.excluded or name == "self":
            return
        entry = self._items.get(name)
        if entry is None:
            entry = {
                "name": name,
                "type": infer_value_type(annotation) if annotation is not None else _value_type(value),
                "initial": ast.unparse(value) if value is not None else "",
                "constant": name.isupper(),
                "scope": self.scope,
            }
            self._items[name] = entry
            return
        if entry.get("type") == "any" and annotation is not None:
            entry["type"] = infer_value_type(annotation)
        if not entry.get("initial") and value is not None:
            entry["initial"] = ast.unparse(value)


def _value_type(value: ast.AST | None) -> str:
    if isinstance(value, ast.Constant):
        name = type(value.value).__name__
        return name if name in {"bool", "int", "float", "str"} else "any"
    mapping = {ast.List: "list", ast.Dict: "dict", ast.Tuple: "tuple", ast.Set: "set"}
    return next((name for kind, name in mapping.items() if isinstance(value, kind)), "any")
