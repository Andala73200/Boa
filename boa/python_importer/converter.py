from __future__ import annotations

import ast
from uuid import uuid4

from boa.classes.models import class_graph
from boa.functions.models import definition_graph
from boa.python_importer.analysis import (
    captured_names, comments_by_line, infer_value_type, scope_body_without_docstring,
    scope_docstring, scope_imports, scope_variables,
)
from boa.python_importer.graph_builder import GraphBuilder
from boa.python_importer.models import ConversionReport, ConversionResult


class ConversionEngine:
    def __init__(self, source: str, filename: str, tree: ast.Module) -> None:
        self.source = source
        self.filename = filename
        self.tree = tree
        self.report = ConversionReport()
        self.functions: dict[str, dict] = {}
        self.classes: dict[str, dict] = {}
        self.builder = GraphBuilder(source, comments_by_line(source), self.report, self)

    def convert(self) -> ConversionResult:
        imports = scope_imports(self.tree.body)
        self.report.imports = len(imports)
        body = scope_body_without_docstring(self.tree.body)
        graph = self.builder.module_graph(body)
        variables = scope_variables(body, scope="global")
        return ConversionResult(graph, self.functions, self.classes, imports, variables, self.report)

    def register_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        owner_function_id: str = "",
        owner_class_id: str = "",
        available_captures: set[str] | None = None,
    ) -> dict:
        function_id = f"function_{uuid4().hex[:10]}"
        graph = definition_graph()
        parameters = _parameters(node)
        captures = captured_names(node) if owner_function_id else []
        if available_captures is not None:
            captures = [name for name in captures if name in available_captures]
        initial_defs: dict[str, tuple[str, str]] = {}
        for index, parameter in enumerate(parameters):
            uid = f"def_input_{uuid4().hex[:8]}"
            key = "def_input"
            graph["blocks"].append({
                "id": uid,
                "key": key,
                "def_port_id": f"port_{uuid4().hex[:8]}",
                "def_port_name": parameter["name"],
                "def_port_type": parameter["type"],
                "def_annotation": parameter["annotation"],
                "def_param_kind": parameter["kind"],
                "def_call_mode": parameter["call_mode"],
                "def_required": parameter["required"],
                "def_default": parameter["default"],
                "def_order": index,
                "x": -650,
                "y": index * 86,
            })
            initial_defs[parameter["name"]] = (uid, "value")
        for index, name in enumerate(captures):
            uid = f"captured_{uuid4().hex[:8]}"
            graph["blocks"].append({
                "id": uid,
                "key": "variable",
                "variable_name": name,
                "variable_type": "any",
                "variable_constant": False,
                "variable_capture": True,
                "x": -650,
                "y": (len(parameters) + index) * 86,
            })
            initial_defs[name] = (uid, "out")
        for index, output in enumerate(_return_schema(node)):
            graph["blocks"].append({
                "id": f"def_output_{uuid4().hex[:8]}",
                "key": "def_output",
                "def_port_id": f"port_{uuid4().hex[:8]}",
                "def_port_name": output,
                "def_port_type": "any",
                "def_required": False,
                "def_order": index,
                "x": 760,
                "y": index * 86,
            })
        body = scope_body_without_docstring(node.body)
        self.builder.function_body(graph, body, initial_defs, function_id)
        variables = scope_variables(body, {item["name"] for item in parameters}, "local")
        known_variables = {str(item.get("name", "")) for item in variables}
        variables.extend({
            "name": name, "type": "any", "initial": "",
            "constant": False, "scope": "capturée",
        } for name in captures if name not in known_variables)
        function = {
            "id": function_id,
            "name": node.name,
            "description": "Fonction convertie depuis Python",
            "comment": "",
            "docstring": scope_docstring(node.body),
            "imports": scope_imports(body),
            "variables": variables,
            "captured_names": captures,
            "owner_function_id": owner_function_id,
            "owner_class_id": owner_class_id,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "return_annotation": ast.unparse(node.returns) if node.returns is not None else "",
            "python_inline": True,
            "python_lineno": int(getattr(node, "lineno", 0)),
            "graph": graph,
        }
        self.functions[function_id] = function
        self.report.functions += 1
        return function

    def register_class(self, node: ast.ClassDef, owner_class_id: str = "") -> dict:
        class_id = f"class_{uuid4().hex[:10]}"
        body = scope_body_without_docstring(node.body)
        class_def = {
            "id": class_id,
            "name": node.name,
            "docstring": scope_docstring(node.body),
            "imports": scope_imports(body),
            "variables": scope_variables(body, scope="classe"),
            "bases": [ast.unparse(item) for item in node.bases],
            "keywords": [ast.unparse(item) for item in node.keywords],
            "owner_class_id": owner_class_id,
            "python_inline": True,
            "python_lineno": int(getattr(node, "lineno", 0)),
            "graph": class_graph(),
        }
        self.classes[class_id] = class_def
        class_def["graph"] = self.builder.class_graph(body, class_id)
        self.report.classes += 1
        return class_def


def convert_python_source(source: str, filename: str = "script.py") -> ConversionResult:
    try:
        tree = ast.parse(source, filename=filename, type_comments=True)
    except SyntaxError as error:
        location = f"ligne {error.lineno}, colonne {error.offset}" if error.lineno else "position inconnue"
        raise ValueError(f"Syntaxe Python invalide ({location}) : {error.msg}") from error
    return ConversionEngine(source, filename, tree).convert()


def convert_python_statement(source: str) -> tuple[dict, list[dict]]:
    try:
        tree = ast.parse(source, filename="<bloc Python>", type_comments=True)
    except SyntaxError as error:
        location = f"ligne {error.lineno}, colonne {error.offset}" if error.lineno else "position inconnue"
        raise ValueError(f"Syntaxe Python invalide ({location}) : {error.msg}") from error
    if len(tree.body) != 1:
        raise ValueError("Un bloc Python doit contenir exactement une instruction principale.")
    engine = ConversionEngine(source, "<bloc Python>", tree)
    block = engine.builder.statement_block(tree.body[0])
    return block, scope_imports(tree.body)


def _parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict]:
    positional = [*node.args.posonlyargs, *node.args.args]
    defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)
    posonly_count = len(node.args.posonlyargs)
    result = [
        _parameter(
            arg,
            default,
            default is None,
            "normal",
            "posonly" if index < posonly_count else "normal",
        )
        for index, (arg, default) in enumerate(zip(positional, defaults))
    ]
    if node.args.vararg:
        result.append(_parameter(node.args.vararg, None, False, "args", "normal"))
    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        result.append(_parameter(arg, default, default is None, "normal", "kwonly"))
    if node.args.kwarg:
        result.append(_parameter(node.args.kwarg, None, False, "kwargs", "normal"))
    return result


def _parameter(
    arg: ast.arg,
    default: ast.AST | None,
    required: bool,
    kind: str,
    call_mode: str,
) -> dict:
    return {
        "name": arg.arg,
        "type": infer_value_type(arg.annotation),
        "annotation": ast.unparse(arg.annotation) if arg.annotation is not None else "",
        "required": required,
        "default": ast.unparse(default) if default is not None else "",
        "kind": kind,
        "call_mode": call_mode,
    }



def _return_schema(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    values: list[list[ast.AST]] = []

    class Finder(ast.NodeVisitor):
        def visit_Return(self, item: ast.Return) -> None:
            if item.value is None:
                values.append([])
            elif isinstance(item.value, (ast.Tuple, ast.List)):
                values.append(list(item.value.elts))
            else:
                values.append([item.value])

        def visit_FunctionDef(self, item: ast.FunctionDef) -> None:
            if item is node:
                for child in item.body:
                    self.visit(child)

        visit_AsyncFunctionDef = visit_FunctionDef
        def visit_ClassDef(self, item: ast.ClassDef) -> None: return
        def visit_Lambda(self, item: ast.Lambda) -> None: return

    Finder().visit(node)
    width = max((len(item) for item in values), default=0)
    if not width:
        return []
    result = []
    for index in range(width):
        candidates = [item[index] for item in values if index < len(item)]
        names = {_return_name(item) for item in candidates}
        names.discard("")
        result.append(next(iter(names)) if len(names) == 1 else ("resultat" if width == 1 else f"resultat_{index + 1}"))
    return result


def _return_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""
