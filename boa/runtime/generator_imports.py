from __future__ import annotations

import ast

from boa.core.project_environment import graph_import_statements, import_bindings
from boa.functions.models import function_parameters
from boa.runtime.codegen_utils import safe_call_target, safe_name
from boa.runtime.common_codegen import helper_names, helper_source
from boa.runtime.module_codegen import graph_used_modules


class ImportMixin:
    def _header(self) -> None:
        imports: list[str] = []
        for item in self.context.get("imports", []):
            statement = str(item.get("statement", "")).strip()
            if statement and statement not in imports:
                imports.append(statement)
        for statement in graph_import_statements(self.graph):
            if statement not in imports:
                imports.append(statement)

        all_graphs = self._all_graphs()
        if self._needs_ast_import(self.graph) and "import ast" not in imports:
            imports.append("import ast")
        for module in sorted(graph_used_modules(self.graph)):
            if module not in import_bindings(imports):
                imports.append(f"import {module}")
        bindings = import_bindings(imports)
        known_names = self._known_names([self.graph]) | set(bindings)
        for module in self._call_imports(self.graph, known_names):
            if module in bindings:
                continue
            statement = f"import {module}"
            if statement not in imports and not any(
                str(item).startswith(f"import {module}")
                or str(item).startswith(f"from {module} import ")
                for item in imports
            ):
                imports.append(statement)

        for statement in imports:
            self._line(statement)
        if imports:
            self._line("")

        helpers = helper_source({name for graph in all_graphs for name in helper_names(graph)})
        if helpers:
            self.lines.extend(helpers.splitlines())
            self._line("")

    def _needs_ast_import(self, graph: dict) -> bool:
        complex_types = {"list", "dict", "tuple", "set"}
        return any(
            (block.get("key") == "input" and block.get("input_type") in complex_types)
            or self._needs_ast_import(block.get("inner_graph", {}) or {})
            for block in graph.get("blocks", [])
        )

    def _scope_imports(self, definition: dict, graph: dict) -> list[str]:
        imports: list[str] = []
        for item in definition.get("imports", []):
            statement = str(item.get("statement", item) if isinstance(item, dict) else item).strip()
            if statement and statement not in imports:
                imports.append(statement)
        for statement in graph_import_statements(graph):
            if statement not in imports:
                imports.append(statement)
        if self._needs_ast_import(graph) and "import ast" not in imports:
            imports.append("import ast")
        global_statements = [
            str(item.get("statement", "")).strip()
            for item in self.context.get("imports", [])
            if str(item.get("statement", "")).strip()
        ]
        bindings = import_bindings([*global_statements, *imports])
        for module in sorted(graph_used_modules(graph)):
            if module not in bindings:
                imports.append(f"import {module}")
                bindings[module] = module
        known_names = self._known_names([graph]) | set(bindings)
        known_names.update(
            safe_name(port.get("name", ""))
            for port in function_parameters(definition)
        )
        for module in self._call_imports(graph, known_names):
            if module in bindings:
                continue
            imports.append(f"import {module}")
            bindings[module] = module
        return imports

    def _call_imports(self, graph: dict, known_names: set[str] | None = None) -> list[str]:
        known_names = known_names or set()
        modules: list[str] = []
        for block in graph.get("blocks", []):
            if block.get("key") == "call" and block.get("call_kind") != "project":
                target = safe_call_target(block.get("call_target", ""))
                if "." in target:
                    root = target.split(".", 1)[0]
                    if root not in known_names and root not in modules:
                        modules.append(root)
            for nested in _nested_graphs(block):
                for module in self._call_imports(nested, known_names):
                    if module not in modules:
                        modules.append(module)
        return modules

    def _known_names(self, graphs: list[dict]) -> set[str]:
        names = {
            safe_name(item.get("name", ""))
            for item in self.context.get("variables", [])
            if safe_name(item.get("name", ""))
        }
        names.update(safe_name(item.get("name", "")) for item in self.functions.values())
        names.update(safe_name(item.get("name", "")) for item in self.classes.values())
        for graph in graphs:
            for current in _walk_graphs(graph):
                for block in current.get("blocks", []):
                    if block.get("key") in {"assign", "variable"}:
                        names.update(_target_names(block.get("python_target") or block.get("variable_name", "")))
                    if block.get("key") == "multi_assign":
                        for target in block.get("assign_targets", []):
                            names.update(_target_names(target))
                    if block.get("key") == "for":
                        names.update(safe_name(name) for name in block.get("for_temp_outputs", []))
                    if block.get("key") == "with":
                        for item in block.get("with_items", []):
                            names.update(_target_names(item.get("alias", "")))
                    if block.get("key") == "try":
                        names.update(safe_name(item.get("name", "")) for item in block.get("try_handlers", []))
                    if block.get("key") == "python_node":
                        names.update(safe_name(name) for name in block.get("python_outputs", []))
                        names.update(_stored_names(block.get("python_source", "")))
        return {name for name in names if name}

    def _all_graphs(self) -> list[dict]:
        graphs = [self.graph]
        graphs.extend(item.get("graph", {}) for item in self.functions.values() if isinstance(item, dict))
        graphs.extend(item.get("graph", {}) for item in self.classes.values() if isinstance(item, dict))
        return graphs


def _walk_graphs(graph: dict):
    yield graph
    for block in graph.get("blocks", []):
        for nested in _nested_graphs(block):
            yield from _walk_graphs(nested)


def _nested_graphs(block: dict) -> list[dict]:
    result = []
    for key in ("inner_graph", "try_graph", "try_else_graph", "try_finally_graph", "with_graph"):
        graph = block.get(key)
        if isinstance(graph, dict) and graph:
            result.append(graph)
    result.extend(
        item.get("graph", {}) for item in block.get("try_handlers", [])
        if isinstance(item, dict) and isinstance(item.get("graph"), dict)
    )
    result.extend(
        item.get("graph", {}) for item in block.get("match_cases", [])
        if isinstance(item, dict) and isinstance(item.get("graph"), dict)
    )
    for section in block.get("python_sections", []):
        if not isinstance(section, dict):
            continue
        if isinstance(section.get("graph"), dict):
            result.append(section["graph"])
        for child in section.get("sections", []):
            if isinstance(child, dict) and isinstance(child.get("graph"), dict):
                result.append(child["graph"])
    return result


def _target_names(expression) -> set[str]:
    text = str(expression or "").strip()
    if not text:
        return set()
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        try:
            tree = ast.parse(f"{text} = None")
        except SyntaxError:
            return {safe_name(text)} if safe_name(text) else set()
    return {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del))
    } or ({tree.body.id} if isinstance(getattr(tree, "body", None), ast.Name) else set())


def _stored_names(source) -> set[str]:
    try:
        tree = ast.parse(str(source or ""))
    except (SyntaxError, ValueError):
        return set()
    return {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del))
    }
