from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from boa.core.project_files import (
    archive_graph_file, delete_script_file, graph_paths, move_graph, move_script,
    refresh_script_from_disk, script_changed_on_disk, script_paths, write_script,
)
from boa.core.project_storage import default_graph
from boa.i18n import tr
from boa.ui.project_conversion import convert_folder_to_graphs, convert_script_to_graph
from boa.ui.script_editor import ScriptEditorDialog
from boa.functions.models import new_function
from boa.classes.models import new_class


def install_project_actions(window) -> None:
    tree = window.project_tree
    tree.graph_open_requested.connect(lambda gid: open_graph(window, gid))
    tree.graph_run_requested.connect(lambda gid: run_graph(window, gid))
    tree.script_open_requested.connect(lambda sid: open_script(window, sid))
    tree.script_run_requested.connect(lambda sid: run_script(window, sid))
    tree.script_convert_requested.connect(lambda sid: convert_script_to_graph(window, sid))
    tree.folder_convert_requested.connect(lambda fid: convert_folder_to_graphs(window, fid))
    tree.graph_created.connect(lambda gid, name: create_graph(window, gid, name))
    tree.graph_duplicated.connect(lambda nid, sid, name: duplicate_graph(window, nid, sid, name))
    tree.script_created.connect(lambda sid, name, content: create_script(window, sid, name, content))
    tree.graph_deleted.connect(lambda gid: delete_graph(window, gid))
    tree.script_deleted.connect(lambda sid: delete_script(window, sid))
    tree.item_renamed.connect(lambda kind, item_id, name: rename_project_item(window, kind, item_id, name))
    tree.main_graph_changed.connect(lambda gid: set_main_graph(window, gid))
    tree.function_open_requested.connect(window.open_function_document)
    tree.function_created.connect(lambda fid, name: create_function(window, fid, name))
    tree.function_deleted.connect(lambda fid: delete_function(window, fid))
    tree.class_open_requested.connect(window.open_class_document)
    tree.class_created.connect(lambda cid, name: create_class(window, cid, name))
    tree.class_deleted.connect(lambda cid: delete_class(window, cid))
    tree.tree_changed.connect(lambda: reconcile_script_paths(window))


def store_active_graph(window) -> None:
    window._store_open_documents()


def graph_data(window, graph_id: str) -> dict:
    return deepcopy(window._graphs.get(graph_id, {}).get("graph", default_graph()))


def open_graph(window, graph_id: str) -> None:
    if graph_id not in window._graphs: return
    window.open_graph_document(graph_id)
    window.statusBar().showMessage(f"Graphe ouvert : {window._graphs[graph_id].get('name', graph_id)}", 2500)


def create_graph(window, graph_id: str, name: str) -> None:
    window._graphs[graph_id] = {"name": name, "graph": default_graph()}; window._record_history()


def duplicate_graph(window, new_id: str, source_id: str, name: str) -> None:
    store_active_graph(window); window._graphs[new_id] = {"name": name, "graph": graph_data(window, source_id)}; window._record_history()


def delete_graph(window, graph_id: str) -> None:
    entry = window._graphs.get(graph_id)
    if entry and window.current_file:
        try:
            archive_graph_file(window.current_file, entry)
        except OSError as error:
            QMessageBox.warning(window, tr("project.delete"), str(error))
    window.document_tabs.close_document("graph", graph_id)
    window._graphs.pop(graph_id, None)
    if not window._graphs:
        window._graphs["main"] = {"name": "main.boa", "graph": default_graph()}
        QTimer.singleShot(0, lambda: (
            window.project_tree.add_generated_graph("main", "main.boa"),
            window.project_tree.set_main_graph_id("main"),
        ))
    if window._main_graph_id == graph_id: window._main_graph_id = next(iter(window._graphs))
    window.project_tree.set_main_graph_id(window._main_graph_id)
    if window._active_graph_id == graph_id:
        window._active_graph_id = next(iter(window._graphs)); window.open_graph_document(window._active_graph_id)


def create_script(window, script_id: str, name: str, content: str) -> None:
    paths = script_paths(window.project_tree.to_data())
    item = {"name": name, "content": content, "path": paths.get(script_id, name).as_posix()}
    window._scripts[script_id] = item
    if window.current_file:
        target = window.current_file.parent / item["path"]
        if target.exists() and QMessageBox.question(
            window, tr("project.file_exists_title"),
            tr("project.file_exists_message", name=target.name),
        ) != QMessageBox.StandardButton.Yes:
            refresh_script_from_disk(window.current_file, item)
        else:
            write_script(window.current_file, item)
    window._record_history()
    if content.strip(): _check_dependencies(window)


def open_script(window, script_id: str) -> None:
    item = window._scripts.get(script_id)
    if not item: return
    if window.current_file and script_changed_on_disk(window.current_file, item):
        answer = QMessageBox.question(
            window, tr("project.external_change_title"),
            tr("project.external_change_message", name=item.get("name", "script.py")),
        )
        if answer == QMessageBox.StandardButton.Yes:
            refresh_script_from_disk(window.current_file, item)
    dialog = ScriptEditorDialog(script_id, item.get("name", "script.py"), item.get("content", ""), window)
    dialog.script_saved.connect(lambda sid, text: save_script_content(window, sid, text)); dialog.show()
    if not hasattr(window, "_script_editors"): window._script_editors = []
    window._script_editors.append(dialog); dialog.finished.connect(lambda *_: window._script_editors.remove(dialog) if dialog in window._script_editors else None)


def save_script_content(window, script_id: str, content: str) -> None:
    if script_id in window._scripts:
        item = window._scripts[script_id]
        previous = deepcopy(item)
        item["content"] = content
        if window.current_file:
            try:
                write_script(window.current_file, item)
            except Exception as error:
                window._scripts[script_id] = previous
                QMessageBox.critical(window, tr("dialog.save_error"), str(error)); return
        window._record_history(); window.statusBar().showMessage(tr("project.script_saved"), 2500)
        _check_dependencies(window)


def delete_script(window, script_id: str) -> None:
    item = window._scripts.get(script_id)
    if item and window.current_file:
        try:
            delete_script_file(window.current_file, item)
        except OSError as error:
            QMessageBox.warning(window, tr("project.delete"), str(error))
    window._scripts.pop(script_id, None)


def rename_project_item(window, kind: str, item_id: str, name: str) -> None:
    if kind == "graph" and item_id in window._graphs:
        window._graphs[item_id]["name"] = name; window.document_tabs.rename_document("graph", item_id, name); window._record_history()
    if kind == "script" and item_id in window._scripts:
        window._scripts[item_id]["name"] = name; window._record_history()
    if kind == "folder":
        window._record_history()
    if kind == "function" and item_id in window._functions:
        window._functions[item_id]["name"] = name; window.document_tabs.rename_document("function", item_id, f"{name} (DEF)"); window._refresh_all_function_calls(); window._record_history()
    if kind == "class" and item_id in window._classes:
        window._classes[item_id]["name"] = name; window.document_tabs.rename_document("class", item_id, f"{name} (Classe)"); window._record_history()
    reconcile_script_paths(window)


def set_main_graph(window, graph_id: str) -> None:
    if graph_id in window._graphs:
        window._main_graph_id = graph_id
        window.project_tree.set_main_graph_id(graph_id)
        window.statusBar().showMessage(f"Graphe principal : {window._graphs[graph_id].get('name', graph_id)}", 2500)
        window._record_history()


def run_graph(window, graph_id: str) -> None:
    from boa.ui.runtime_actions import simulate_project
    simulate_project(window, graph_id)


def reconcile_script_paths(window) -> None:
    paths = script_paths(window.project_tree.to_data())
    for script_id, relative in paths.items():
        item = window._scripts.get(script_id)
        if not item:
            continue
        item["name"] = relative.name
        if not window.current_file:
            item["path"] = relative.as_posix(); continue
        try:
            move_script(window.current_file, item, relative)
        except (OSError, ValueError) as error:
            QMessageBox.warning(window, tr("project.rename"), str(error))
    graph_locations = graph_paths(window.project_tree.to_data())
    for graph_id, relative in graph_locations.items():
        item = window._graphs.get(graph_id)
        if not item:
            continue
        item["name"] = relative.name
        if not window.current_file:
            item["path"] = relative.as_posix()
            continue
        try:
            move_graph(window.current_file, item, relative)
        except (OSError, ValueError) as error:
            QMessageBox.warning(window, tr("project.rename"), str(error))


def run_script(window, script_id: str) -> None:
    from boa.ui.runtime_actions import execute_script
    execute_script(window, script_id)


def create_function(window, function_id: str, name: str) -> None:
    function = new_function(name); function["id"] = function_id; window._functions[function_id] = function; window._record_history()


def delete_function(window, function_id: str) -> None:
    window.document_tabs.close_document("function", function_id); window._functions.pop(function_id, None)
    window._refresh_all_function_calls(); window._record_history()


def create_class(window, class_id: str, name: str) -> None:
    class_def = new_class(name)
    class_def["id"] = class_id
    window._classes[class_id] = class_def
    window._record_history()


def delete_class(window, class_id: str) -> None:
    window.document_tabs.close_document("class", class_id)
    window._classes.pop(class_id, None)
    window._record_history()


def _check_dependencies(window) -> None:
    from boa.ui.dependency_dialog import check_project_dependencies
    from boa.ui.environment_controller import ensure_project_environment
    ensure_project_environment(window, lambda: check_project_dependencies(window))
