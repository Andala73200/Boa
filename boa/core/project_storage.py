import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from boa.classes.models import normalize_classes
from boa.core.atomic_io import atomic_write_text
from boa.core.project_files import (
    graph_paths, hydrate_scripts, safe_graph_path, sync_scripts,
)
from boa.core.project_tree_data import (
    CLASSES_FOLDER_ID, FILES_FOLDER_ID, FUNCTIONS_FOLDER_ID, normalize_tree_layout, sort_file_tree,
)
from boa.functions.models import normalize_functions

PROJECT_VERSION = 10
PROJECT_KIND = "boa_project"
GRAPH_KIND = "boa_graph"


def default_graph() -> dict[str, Any]:
    return {
        "blocks": [{"id": "b1", "key": "run", "title": "RUN", "subtitle": "", "color": "#263238", "x": -120, "y": 0}],
        "connections": [],
    }


def default_tree() -> dict[str, Any]:
    return {
        "name": "Projet Boa", "kind": "root", "id": "root", "protected": True,
        "children": [
            {"name": "Fichiers", "kind": "folder", "id": FILES_FOLDER_ID, "protected": True, "children": [
                {"name": "main.boa", "kind": "graph", "id": "main", "protected": False, "children": []},
            ]},
            {"name": "Fonctions", "kind": "folder", "id": FUNCTIONS_FOLDER_ID, "protected": True, "children": []},
            {"name": "Classes", "kind": "folder", "id": CLASSES_FOLDER_ID, "protected": True, "children": []},
        ],
    }


def empty_project() -> dict[str, Any]:
    graph = default_graph()
    return {
        "kind": PROJECT_KIND,
        "version": PROJECT_VERSION,
        "context": {"imports": [], "variables": []},
        "active_graph_id": "main",
        "main_graph_id": "main",
        "graphs": {"main": {"name": "main.boa", "graph": deepcopy(graph)}},
        "functions": {},
        "classes": {},
        "scripts": {},
        "graph": deepcopy(graph),
        "tree": default_tree(),
    }


def normalize_project(data: dict[str, Any]) -> dict[str, Any]:
    base = empty_project()
    base["context"] = data.get("context", base["context"])
    if isinstance(data.get("graphs"), dict) and data.get("graphs"):
        base["graphs"] = data["graphs"]
    else:
        base["graphs"] = {"main": {"name": "main.boa", "graph": data.get("graph", default_graph())}}
    base["scripts"] = data.get("scripts", {}) if isinstance(data.get("scripts"), dict) else {}
    base["functions"] = normalize_functions(data.get("functions", {}))
    base["classes"] = normalize_classes(data.get("classes", {}))
    base["active_graph_id"] = str(data.get("active_graph_id") or data.get("main_graph_id") or next(iter(base["graphs"]), "main"))
    if base["active_graph_id"] not in base["graphs"]:
        base["active_graph_id"] = next(iter(base["graphs"]), "main")
    base["main_graph_id"] = str(data.get("main_graph_id") or base["active_graph_id"])
    if base["main_graph_id"] not in base["graphs"]:
        base["main_graph_id"] = base["active_graph_id"]
    base["graph"] = deepcopy(base["graphs"][base["active_graph_id"]].get("graph", default_graph()))
    tree = data.get("tree")
    candidate = deepcopy(tree) if _valid_tree(tree) else _tree_from_project(base)
    base["tree"] = _sync_definition_tree(
        normalize_tree_layout(candidate),
        base["functions"],
        base["classes"],
    )
    base["kind"] = PROJECT_KIND
    base["version"] = PROJECT_VERSION
    return base


def load_project(path: str | Path) -> dict[str, Any]:
    project_file = Path(path)
    data, recovered = _read_json(project_file)
    if not isinstance(data, dict):
        raise ValueError("Format de projet invalide.")
    if data.get("kind") == GRAPH_KIND:
        data = _project_from_sidecar(data, project_file)
    else:
        data = _hydrate_graphs(project_file, data, prefer_backups=recovered)
    if "graph" not in data and "graphs" not in data:
        raise ValueError("Projet Boa incomplet.")
    return hydrate_scripts(project_file, normalize_project(data))


def save_project(path: str | Path, data: dict[str, Any]) -> dict[str, Any]:
    project_file = Path(path).resolve()
    project = normalize_project(data)
    sync_scripts(project_file, project)
    paths = graph_paths(project.get("tree", {}))
    root = project_file.parent
    for graph_id, entry in project.get("graphs", {}).items():
        relative = paths.get(graph_id) or Path(str(entry.get("path") or entry.get("name") or f"{graph_id}.boa"))
        target = safe_graph_path(root, relative)
        entry["path"] = relative.as_posix()
        if target == project_file:
            continue
        atomic_write_text(target, _json_text(_graph_sidecar(project, graph_id, entry)))
    colliding = [
        (graph_id, entry) for graph_id, entry in project.get("graphs", {}).items()
        if safe_graph_path(root, entry.get("path") or entry.get("name") or f"{graph_id}.boa") == project_file
    ]
    if len(project.get("graphs", {})) == 1 and len(colliding) == 1:
        graph_id, entry = colliding[0]
        atomic_write_text(project_file, _json_text(_graph_sidecar(project, graph_id, entry)))
    else:
        manifest = _project_manifest(project, project_file)
        atomic_write_text(project_file, _json_text(manifest))
    return project


def _project_manifest(project: dict, project_file: Path) -> dict:
    manifest = deepcopy(project)
    manifest["kind"] = PROJECT_KIND
    for item in manifest.get("scripts", {}).values():
        item.pop("content", None)
    for graph_id, entry in manifest.get("graphs", {}).items():
        relative = Path(str(entry.get("path") or entry.get("name") or f"{graph_id}.boa"))
        target = safe_graph_path(project_file.parent, relative)
        if target != project_file:
            entry.pop("graph", None)
    manifest.pop("graph", None)
    return manifest


def _graph_sidecar(project: dict, graph_id: str, entry: dict) -> dict:
    source_id = str(entry.get("source_script_id", ""))
    scripts = {
        source_id: deepcopy(project.get("scripts", {}).get(source_id, {}))
    } if source_id and source_id in project.get("scripts", {}) else {}
    for item in scripts.values():
        item.pop("content", None)
    return {
        "kind": GRAPH_KIND,
        "version": PROJECT_VERSION,
        "graph_id": graph_id,
        **deepcopy(entry),
        "context": deepcopy(project.get("context", {})),
        "functions": deepcopy(project.get("functions", {})),
        "classes": deepcopy(project.get("classes", {})),
        "scripts": scripts,
        "tree": deepcopy(project.get("tree", {})),
        "active_graph_id": graph_id,
        "main_graph_id": graph_id,
    }


def _hydrate_graphs(project_file: Path, data: dict, *, prefer_backups: bool = False) -> dict:
    hydrated = deepcopy(data)
    root = project_file.resolve().parent
    for graph_id, entry in hydrated.get("graphs", {}).items():
        if not isinstance(entry, dict) or isinstance(entry.get("graph"), dict):
            continue
        relative = entry.get("path") or entry.get("name") or f"{graph_id}.boa"
        sidecar_path = safe_graph_path(root, relative)
        sidecar, _ = _read_json(sidecar_path, prefer_backup=prefer_backups)
        if sidecar.get("kind") != GRAPH_KIND or not isinstance(sidecar.get("graph"), dict):
            raise ValueError(f"Fichier de graphe invalide : {relative}")
        entry["graph"] = deepcopy(sidecar["graph"])
    return hydrated


def _project_from_sidecar(sidecar: dict, sidecar_path: Path) -> dict:
    graph_id = str(sidecar.get("graph_id") or "main")
    graph_entry = {
        key: deepcopy(value) for key, value in sidecar.items()
        if key not in {
            "kind", "version", "graph_id", "context", "functions", "classes",
            "scripts", "tree", "active_graph_id", "main_graph_id",
        }
    }
    graph_entry["name"] = sidecar_path.name
    graph_entry["path"] = sidecar_path.name
    scripts = deepcopy(sidecar.get("scripts", {}))
    for item in scripts.values():
        item["path"] = str(item.get("name") or Path(str(item.get("path") or "script.py")).name)
    project = empty_project()
    project.update({
        "context": deepcopy(sidecar.get("context", {})),
        "graphs": {graph_id: graph_entry},
        "functions": deepcopy(sidecar.get("functions", {})),
        "classes": deepcopy(sidecar.get("classes", {})),
        "scripts": scripts,
        "active_graph_id": graph_id,
        "main_graph_id": graph_id,
        "graph": deepcopy(graph_entry.get("graph", default_graph())),
    })
    project["tree"] = _tree_from_project(project)
    return project


def _read_json(path: Path, *, prefer_backup: bool = False) -> tuple[dict, bool]:
    errors: list[Exception] = []
    backup = path.with_name(f"{path.name}.bak")
    candidates = (backup, path) if prefer_backup else (path, backup)
    for candidate in candidates:
        try:
            value = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                return value, candidate == backup
            errors.append(ValueError("La racine JSON n'est pas un objet."))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            errors.append(error)
    detail = str(errors[-1]) if errors else "fichier absent"
    raise ValueError(f"Impossible de lire {path.name} ni sa sauvegarde : {detail}")


def _json_text(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _tree_from_project(project: dict[str, Any]) -> dict[str, Any]:
    tree = default_tree()
    files = _tree_folder(tree, FILES_FOLDER_ID)
    files["children"] = [
        {"name": value.get("name", f"{uid}.boa"), "kind": "graph", "id": uid, "protected": False, "children": []}
        for uid, value in project.get("graphs", {}).items()
    ]
    files["children"] += [
        {"name": value.get("name", f"{uid}.py"), "kind": "script", "id": uid, "protected": False, "children": []}
        for uid, value in project.get("scripts", {}).items()
    ]
    sort_file_tree(files)
    return _sync_definition_tree(tree, project.get("functions", {}), project.get("classes", {}))


def _valid_tree(tree: Any) -> bool:
    return isinstance(tree, dict) and tree.get("id") == "root"


def _sync_definition_tree(tree: dict, functions: dict, classes: dict) -> dict:
    function_folder = _ensure_folder(tree, "functions_root", "Fonctions", 1)
    class_folder = _ensure_folder(tree, "classes_root", "Classes", 2)
    existing_functions = _flatten_existing(function_folder, "function")
    existing_classes = _flatten_existing(class_folder, "class")

    top_functions = [item for item in functions.values() if not item.get("owner_function_id") and not item.get("owner_class_id")]
    function_folder["children"] = [_function_tree_item(item, functions, existing_functions) for item in top_functions]

    top_classes = [item for item in classes.values() if not item.get("owner_class_id")]
    class_folder["children"] = [_class_tree_item(item, functions, classes, existing_functions, existing_classes) for item in top_classes]
    return tree


def _function_tree_item(function: dict, functions: dict, existing: dict) -> dict:
    uid = str(function.get("id", ""))
    local = [item for item in functions.values() if str(item.get("owner_function_id", "")) == uid]
    return {
        **existing.get(uid, {}),
        "name": function.get("name", uid),
        "kind": "function",
        "id": uid,
        "protected": False,
        "children": [_function_tree_item(item, functions, existing) for item in local],
    }


def _class_tree_item(class_def: dict, functions: dict, classes: dict, existing_functions: dict, existing_classes: dict) -> dict:
    uid = str(class_def.get("id", ""))
    methods = [item for item in functions.values() if str(item.get("owner_class_id", "")) == uid]
    nested = [item for item in classes.values() if str(item.get("owner_class_id", "")) == uid]
    children = [_function_tree_item(item, functions, existing_functions) for item in methods]
    children += [_class_tree_item(item, functions, classes, existing_functions, existing_classes) for item in nested]
    return {
        **existing_classes.get(uid, {}),
        "name": class_def.get("name", uid),
        "kind": "class",
        "id": uid,
        "protected": False,
        "children": children,
    }


def _flatten_existing(folder: dict, kind: str) -> dict[str, dict]:
    result: dict[str, dict] = {}

    def visit(item: dict) -> None:
        if item.get("kind") == kind:
            result[str(item.get("id", ""))] = item
        for child in item.get("children", []):
            if isinstance(child, dict):
                visit(child)

    visit(folder)
    return result


def _ensure_folder(tree: dict, item_id: str, name: str, index: int) -> dict:
    folder = _tree_folder(tree, item_id)
    if folder:
        return folder
    folder = {"name": name, "kind": "folder", "id": item_id, "protected": True, "children": []}
    tree.setdefault("children", []).insert(min(index, len(tree.get("children", []))), folder)
    return folder


def _tree_folder(tree: dict, item_id: str) -> dict:
    return next((item for item in tree.get("children", []) if item.get("id") == item_id), {})
