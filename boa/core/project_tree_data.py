from __future__ import annotations

from copy import deepcopy
from pathlib import PurePosixPath
from typing import Iterable

FILES_FOLDER_ID = "files_root"
FUNCTIONS_FOLDER_ID = "functions_root"
CLASSES_FOLDER_ID = "classes_root"
LEGACY_GRAPHS_FOLDER_ID = "graphs_root"
LEGACY_SCRIPTS_FOLDER_ID = "scripts_root"


def normalize_tree_layout(tree: dict | None) -> dict:
    """Migrate old separated Graphes/Python roots to one paired Files tree."""
    root = deepcopy(tree) if isinstance(tree, dict) else {}
    if root.get("id") != "root":
        root = {"name": "Projet Boa", "kind": "root", "id": "root", "protected": True, "children": []}
    root.setdefault("children", [])

    files = _take_child(root, FILES_FOLDER_ID)
    if not files:
        files = _folder("Fichiers", FILES_FOLDER_ID)

    for legacy_id in (LEGACY_GRAPHS_FOLDER_ID, LEGACY_SCRIPTS_FOLDER_ID):
        legacy = _take_child(root, legacy_id)
        if legacy:
            _merge_children(files, legacy.get("children", []))

    functions = _take_child(root, FUNCTIONS_FOLDER_ID) or _folder("Fonctions", FUNCTIONS_FOLDER_ID)
    classes = _take_child(root, CLASSES_FOLDER_ID) or _folder("Classes", CLASSES_FOLDER_ID)
    extras = [item for item in root.get("children", []) if isinstance(item, dict)]
    root["children"] = [files, functions, classes, *extras]
    root["protected"] = True
    sort_file_tree(files)
    return root


def sort_file_tree(node: dict) -> None:
    children = [item for item in node.get("children", []) if isinstance(item, dict)]
    for child in children:
        if child.get("kind") == "folder":
            sort_file_tree(child)
    children.sort(key=file_sort_key)
    node["children"] = children


def file_sort_key(item: dict) -> tuple:
    kind = str(item.get("kind", ""))
    name = str(item.get("name", ""))
    if kind == "folder":
        return (0, name.casefold(), 0, name.casefold())
    path = PurePosixPath(name)
    base = path.stem.casefold()
    type_order = {"script": 0, "graph": 1}.get(kind, 2)
    return (1, base, type_order, name.casefold())


def item_parent_id(tree: dict, item_id: str) -> str:
    parent = _find_parent(tree, item_id)
    return str(parent.get("id", "")) if parent else ""


def descendants_of_kind(tree: dict, parent_id: str, kind: str) -> list[str]:
    parent = find_node(tree, parent_id)
    if not parent:
        return []
    result: list[str] = []

    def visit(node: dict) -> None:
        for child in node.get("children", []):
            if not isinstance(child, dict):
                continue
            if child.get("kind") == kind and child.get("id"):
                result.append(str(child["id"]))
            if child.get("kind") == "folder":
                visit(child)

    visit(parent)
    return result


def paired_graph_id(tree: dict, script_id: str) -> str:
    script = find_node(tree, script_id)
    parent = _find_parent(tree, script_id)
    if not script or not parent:
        return ""
    wanted = PurePosixPath(str(script.get("name", "script.py"))).stem.casefold()
    for child in parent.get("children", []):
        if not isinstance(child, dict) or child.get("kind") != "graph":
            continue
        if PurePosixPath(str(child.get("name", ""))).stem.casefold() == wanted:
            return str(child.get("id", ""))
    return ""


def find_node(node: dict, item_id: str) -> dict | None:
    if str(node.get("id", "")) == item_id:
        return node
    for child in node.get("children", []):
        if isinstance(child, dict):
            found = find_node(child, item_id)
            if found:
                return found
    return None


def _find_parent(node: dict, item_id: str) -> dict | None:
    for child in node.get("children", []):
        if not isinstance(child, dict):
            continue
        if str(child.get("id", "")) == item_id:
            return node
        found = _find_parent(child, item_id)
        if found:
            return found
    return None


def _folder(name: str, item_id: str) -> dict:
    return {"name": name, "kind": "folder", "id": item_id, "protected": True, "children": []}


def _take_child(root: dict, item_id: str) -> dict | None:
    children = root.get("children", [])
    for index, child in enumerate(children):
        if isinstance(child, dict) and child.get("id") == item_id:
            return children.pop(index)
    return None


def _merge_children(target: dict, source_children: Iterable[dict]) -> None:
    target.setdefault("children", [])
    for source in source_children:
        if not isinstance(source, dict):
            continue
        if source.get("kind") == "folder":
            existing = next(
                (
                    child for child in target["children"]
                    if child.get("kind") == "folder"
                    and str(child.get("name", "")).casefold() == str(source.get("name", "")).casefold()
                ),
                None,
            )
            if existing:
                _merge_children(existing, source.get("children", []))
            else:
                target["children"].append(deepcopy(source))
            continue
        source_id = str(source.get("id", ""))
        if source_id and any(str(child.get("id", "")) == source_id for child in target["children"]):
            continue
        target["children"].append(deepcopy(source))
