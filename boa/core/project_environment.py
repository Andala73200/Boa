from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Dependency:
    module: str
    package: str


def project_root(project_file: str | Path) -> Path:
    return Path(project_file).resolve().parent


def dedicated_project_file(requested: str | Path) -> Path:
    target = Path(requested)
    if target.exists() or target.parent.name.casefold() == target.stem.casefold():
        return target
    return target.parent / target.stem / target.name


def venv_path(project_file: str | Path) -> Path:
    return project_root(project_file) / ".venv"


def venv_python(project_file: str | Path) -> Path:
    root = venv_path(project_file)
    return root / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def project_dependencies(project: dict, project_file: str | Path) -> list[Dependency]:
    modules = imported_modules(_project_sources(project))
    local = local_module_names(project, project_root(project_file))
    standard = set(getattr(sys, "stdlib_module_names", ())) | set(sys.builtin_module_names)
    mapping = _package_mapping()
    result = []
    for module in modules:
        root = module.split(".", 1)[0]
        if not root or root in standard or root in local:
            continue
        result.append(Dependency(root, mapping.get(root, root)))
    return _unique_dependencies(result)


def imported_modules(sources: list[str]) -> list[str]:
    modules = []
    for source in sources:
        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.append(node.module)
    return list(dict.fromkeys(modules))


def local_module_names(project: dict, root: Path) -> set[str]:
    names = set()
    for item in project.get("scripts", {}).values():
        script_name = str(item.get("path") or item.get("name") or "")
        if script_name:
            names.add(Path(script_name).parts[0].removesuffix(".py"))
    try:
        children = list(root.iterdir())
    except OSError:
        children = []
    for path in children:
        if path.name == ".venv":
            continue
        if path.is_file() and path.suffix.lower() == ".py":
            names.add(path.stem)
        elif path.is_dir():
            try:
                has_python = (path / "__init__.py").is_file() or any(path.glob("*.py"))
            except OSError:
                has_python = False
            if has_python:
                names.add(path.name)
    return names


def import_bindings(statements: list[str]) -> dict[str, str]:
    bindings = {}
    for statement in statements:
        try:
            tree = ast.parse(statement)
        except (SyntaxError, ValueError):
            continue
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    bound = alias.asname or alias.name.split(".", 1)[0]
                    bindings[bound] = alias.name.split(".", 1)[0]
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        bindings[alias.asname or alias.name] = (node.module or "").split(".", 1)[0]
    return bindings


def graph_import_statements(graph: dict) -> list[str]:
    statements = []
    for source in _graph_sources(graph):
        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError):
            continue
        statements.extend(ast.unparse(node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom)))
    return list(dict.fromkeys(statements))


def _project_sources(project: dict) -> list[str]:
    sources: list[str] = []
    imports = project.get("context", {}).get("imports", [])
    statements = [_import_statement(item) for item in imports]
    if any(statements):
        sources.append("\n".join(item for item in statements if item))
    sources.extend(str(item.get("content", "")) for item in project.get("scripts", {}).values())
    graphs = [item.get("graph", {}) for item in project.get("graphs", {}).values()]
    for graph in graphs or [project.get("graph", {})]:
        sources.extend(_graph_sources(graph))
    for collection in (project.get("functions", {}), project.get("classes", {})):
        for definition in collection.values():
            definition_imports = [_import_statement(item) for item in definition.get("imports", [])]
            if any(definition_imports):
                sources.append("\n".join(item for item in definition_imports if item))
            sources.extend(_graph_sources(definition.get("graph", {}) or {}))
    return sources


def _graph_sources(graph: dict) -> list[str]:
    sources: list[str] = []
    for block in graph.get("blocks", []):
        for key in ("raw_code", "python_source"):
            source = str(block.get(key, "")).strip()
            if source:
                sources.append(source)
        for nested in _nested_graphs(block):
            sources.extend(_graph_sources(nested))
    return sources


def _nested_graphs(block: dict) -> list[dict]:
    result: list[dict] = []
    for key in ("inner_graph", "try_graph", "try_else_graph", "try_finally_graph", "with_graph"):
        graph = block.get(key)
        if isinstance(graph, dict) and graph:
            result.append(graph)
    for key in ("try_handlers", "match_cases"):
        result.extend(
            item.get("graph", {}) for item in block.get(key, [])
            if isinstance(item, dict) and isinstance(item.get("graph"), dict)
        )
    for section in block.get("python_sections", []):
        if not isinstance(section, dict):
            continue
        if isinstance(section.get("graph"), dict):
            result.append(section["graph"])
        result.extend(
            item.get("graph", {}) for item in section.get("sections", [])
            if isinstance(item, dict) and isinstance(item.get("graph"), dict)
        )
    return result


def _import_statement(item) -> str:
    if isinstance(item, dict):
        return str(item.get("statement", "")).strip()
    return str(item).strip()


def _package_mapping() -> dict[str, str]:
    path = Path(__file__).resolve().parents[1] / "resources" / "import_packages.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(key): str(value) for key, value in data.items() if key and value}


def _unique_dependencies(items: list[Dependency]) -> list[Dependency]:
    unique = {}
    for item in items:
        unique.setdefault(item.module, item)
    return list(unique.values())
