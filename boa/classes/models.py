from __future__ import annotations

import keyword
from copy import deepcopy
from uuid import uuid4


def class_graph() -> dict:
    return {"blocks": [], "connections": [], "class_columns": 1}


def new_class(name: str = "NouvelleClasse") -> dict:
    return normalize_class({
        "id": f"class_{uuid4().hex[:10]}",
        "name": name,
        "docstring": "",
        "imports": [],
        "variables": [],
        "bases": [],
        "keywords": [],
        "owner_class_id": "",
        "graph": class_graph(),
    })


def normalize_classes(value) -> dict[str, dict]:
    items = value.values() if isinstance(value, dict) else (value if isinstance(value, list) else [])
    result: dict[str, dict] = {}
    for item in items:
        if isinstance(item, dict):
            class_def = normalize_class(item)
            result[class_def["id"]] = class_def
    return result


def normalize_class(value: dict) -> dict:
    data = deepcopy(value or {})
    data["id"] = str(data.get("id") or f"class_{uuid4().hex[:10]}")
    data["name"] = str(data.get("name") or "NouvelleClasse").strip()
    data["docstring"] = str(data.get("docstring") or "")
    data["imports"] = _normalize_imports(data.get("imports", []))
    data["variables"] = _normalize_variables(data.get("variables", []))
    data["bases"] = [str(item).strip() for item in data.get("bases", []) if str(item).strip()]
    data["keywords"] = [str(item).strip() for item in data.get("keywords", []) if str(item).strip()]
    data["owner_class_id"] = str(data.get("owner_class_id") or "")
    graph = deepcopy(data.get("graph")) if isinstance(data.get("graph"), dict) else class_graph()
    graph.setdefault("blocks", [])
    graph.setdefault("connections", [])
    graph["class_columns"] = max(1, int(graph.get("class_columns", 1) or 1))
    for index, block in enumerate(sorted(graph["blocks"], key=lambda item: (int(item.get("class_order", 10**6)), float(item.get("x", 0))))):
        block["class_order"] = int(block.get("class_order", index))
    data["graph"] = graph
    return data


def valid_class_name(name: str) -> bool:
    text = str(name)
    return text.isidentifier() and not keyword.iskeyword(text)


def _normalize_imports(value) -> list[dict]:
    result = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict):
            statement = str(item.get("statement", "")).strip()
            if statement:
                result.append({"module": str(item.get("module", "")), "statement": statement, "origin": str(item.get("origin", "conversion Python"))})
        elif str(item).strip():
            result.append({"module": "", "statement": str(item).strip(), "origin": "conversion Python"})
    return result


def _normalize_variables(value) -> list[dict]:
    result = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        result.append({
            "name": name,
            "type": str(item.get("type", "any") or "any"),
            "initial": str(item.get("initial", "") or ""),
            "constant": bool(item.get("constant", False)),
            "scope": str(item.get("scope", "classe") or "classe"),
        })
    return result
