from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from boa.core.preferences import save_preferences
from boa.core.project_files import read_script_file
from boa.core.project_storage import empty_project, load_project, normalize_project, save_project
from boa.core.project_tree_data import FILES_FOLDER_ID
from boa.i18n import tr
from boa.ui.project_tree_items import GRAPH_KIND, SCRIPT_KIND, new_id
from boa.ui.recent_projects import remember_recent_path


def open_python_file_as_project(window, source_path: str | Path) -> None:
    """Convert one selected .py file into a same-name Boa project and open it."""
    source = Path(source_path).resolve()
    target = source.with_suffix(".boa")
    if target.exists() and not _confirm_replace(window, target):
        return

    try:
        content, source_info, result = _convert_source(source)
        project = _single_file_project(source, target, content, source_info, result)
        _save_then_open(window, target, project)
    except Exception as error:
        QMessageBox.critical(window, tr("python_import.error_title"), str(error))
        return

    window.statusBar().showMessage(
        tr("project.python_file_opened", source=source.name, graph=target.name), 5000,
    )


def _confirm_replace(window, target: Path) -> bool:
    answer = QMessageBox.question(
        window,
        tr("project.python_open_conflict_title"),
        tr("project.python_open_conflict_message", name=target.name),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return answer == QMessageBox.StandardButton.Yes


def _convert_source(source: Path):
    content, source_info = read_script_file(source)
    from boa.python_importer import convert_python_source
    return content, source_info, convert_python_source(content, source.name)


def _single_file_project(source: Path, target: Path, content: str, source_info: dict, result) -> dict:
    script_id = new_id("script")
    project = empty_project()
    project["scripts"] = {
        script_id: {
            "name": source.name,
            "path": source.name,
            "content": content,
            **source_info,
        },
    }
    project["graphs"] = {
        "main": {
            "name": target.name,
            "graph": result.graph,
            "source_script_id": script_id,
            "imported_function_ids": list(result.functions),
            "imported_class_ids": list(result.classes),
        },
    }
    project["graph"] = deepcopy(result.graph)
    project["functions"] = deepcopy(result.functions)
    project["classes"] = deepcopy(result.classes)
    project["context"] = {
        "imports": [deepcopy(item) for item in result.imports],
        "variables": [deepcopy(item) for item in result.variables],
    }
    files = next(
        item for item in project["tree"]["children"]
        if item.get("id") == FILES_FOLDER_ID
    )
    files["children"] = [
        {
            "name": source.name,
            "kind": SCRIPT_KIND,
            "id": script_id,
            "protected": False,
            "children": [],
        },
        {
            "name": target.name,
            "kind": GRAPH_KIND,
            "id": "main",
            "protected": False,
            "children": [],
        },
    ]
    return normalize_project(project)


def _save_then_open(window, target: Path, project: dict) -> None:
    """Save the converted project, then reopen it through the normal Boa loader."""
    save_project(target, normalize_project(project))

    loaded = load_project(target)
    window.current_file = target
    window._restore_project(loaded)
    remember_recent_path(window.preferences, target)
    save_preferences(window.preferences)
    window._reset_history()
    window._set_dirty(False)
    window.statusBar().showMessage(
        tr("project.python_file_opened", source=target.with_suffix(".py").name, graph=target.name),
        5000,
    )
    QTimer.singleShot(0, window.graph_view.focus_program_start)
