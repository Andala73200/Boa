from __future__ import annotations

from PySide6.QtWidgets import QInputDialog

from boa.ui.loop_dialogs import open_instance_dialog


def open_native_branch(root_view, block) -> bool:
    options = _options(block)
    if not options:
        return False
    labels = [item[0] for item in options]
    label, ok = QInputDialog.getItem(root_view, "Ouvrir une branche", "Branche :", labels, 0, False)
    if not ok:
        return False
    selected = options[labels.index(label)]
    graph = _get_graph(block, selected)

    def factory(parent):
        view = root_view.__class__(parent)
        view.variable_names_provider = root_view.variable_names_provider
        view.variable_entries_provider = root_view.variable_entries_provider
        view.project_root_provider = root_view.project_root_provider
        view.loop_number_provider = root_view.loop_number_provider
        view.functions_provider = root_view.functions_provider
        view.function_open_callback = root_view.function_open_callback
        view.class_open_callback = root_view.class_open_callback
        view.document_kind = root_view.document_kind
        view.blocked_block_keys = {"run", "function_start", "function_return", "def_input", "def_input_p", "def_output", "def_output_p"}
        view.instances_changed.connect(root_view.instances_changed.emit)
        return view

    def save(data: dict) -> None:
        _set_graph(block, selected, data)
        root_view._changed()

    result = open_instance_dialog(root_view, factory, label, graph, ["start"], root_view.variable_entries_provider, save)
    if result is not None:
        save(result)
    return True


def _options(block) -> list[tuple]:
    key = str(getattr(block, "block_key", ""))
    if key == "with":
        return [("Corps du contexte", "with", -1)]
    if key == "match":
        return [(_case_label(item, index), "case", index) for index, item in enumerate(getattr(block, "match_cases", []))]
    if key == "try":
        result = [("Essayer", "try", -1)]
        result += [(f"Except {item.get('type') or index + 1}", "handler", index) for index, item in enumerate(getattr(block, "try_handlers", []))]
        if getattr(block, "try_else_graph", {}): result.append(("Sinon", "else", -1))
        if getattr(block, "try_finally_graph", {}): result.append(("Finalement", "finally", -1))
        return result
    return []


def _get_graph(block, option: tuple) -> dict:
    kind, index = option[1], option[2]
    if kind == "with": return getattr(block, "with_graph", {}) or {}
    if kind == "case": return list(getattr(block, "match_cases", []))[index].get("graph", {}) or {}
    if kind == "try": return getattr(block, "try_graph", {}) or {}
    if kind == "handler": return list(getattr(block, "try_handlers", []))[index].get("graph", {}) or {}
    if kind == "else": return getattr(block, "try_else_graph", {}) or {}
    return getattr(block, "try_finally_graph", {}) or {}


def _set_graph(block, option: tuple, graph: dict) -> None:
    kind, index = option[1], option[2]
    if kind == "with": block.with_graph = graph
    elif kind == "case": block.match_cases[index]["graph"] = graph
    elif kind == "try": block.try_graph = graph
    elif kind == "handler": block.try_handlers[index]["graph"] = graph
    elif kind == "else": block.try_else_graph = graph
    else: block.try_finally_graph = graph


def _case_label(item: dict, index: int) -> str:
    pattern = str(item.get("pattern", "_")).strip() or "_"
    guard = str(item.get("guard", "")).strip()
    return f"Cas {pattern}" + (f" si {guard}" if guard else "") if pattern != "_" else "Cas par défaut"
