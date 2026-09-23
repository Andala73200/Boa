from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox

from boa.core.preferences import save_preferences
from boa.core.project_files import read_script_file, refresh_script_from_disk, script_changed_on_disk, script_paths
from boa.core.project_storage import default_graph, empty_project, load_project, save_project
from boa.core.project_tree_data import FILES_FOLDER_ID
from boa.i18n import tr
from boa.ui.project_tree_items import FOLDER_KIND, SCRIPT_KIND, kind_of, new_id
from boa.ui.recent_projects import remember_recent_path


_IGNORED_PROJECT_FOLDERS = {
    ".git", ".hg", ".mypy_cache", ".pytest_cache", ".svn", ".tox", ".venv",
    "__pycache__", "build", "dist", "env", "node_modules", "site-packages", "venv",
}


def convert_python_project(window) -> None:
    """Open a Python project folder, mirror its .py tree and convert every script."""
    start = str(window.current_file.parent) if window.current_file else window._default_project_dir()
    selected = QFileDialog.getExistingDirectory(
        window, tr("dialog.convert_python_project_title"), start,
    )
    if not selected:
        return

    root = Path(selected).resolve()
    current_root = window.current_file.resolve().parent if window.current_file else None
    if current_root != root:
        project_file = _project_file_for_folder(root)
        try:
            project = load_project(project_file) if project_file.exists() else empty_project()
        except Exception as error:
            QMessageBox.critical(window, tr("dialog.open_error"), str(error))
            return
        if not window._confirm_discard_changes():
            return
        window.current_file = project_file
        window._restore_project(project)
        window._reset_history()
        window._set_dirty(False)

    added, refreshed, read_errors = _sync_python_project_tree(window, root)
    script_ids = window.project_tree.script_ids_in_folder(FILES_FOLDER_ID)
    if not script_ids:
        QMessageBox.information(
            window, tr("action.convert_python_project"), tr("project.folder_no_python"),
        )
        return

    if read_errors:
        details = "\n".join(read_errors[:8])
        if len(read_errors) > 8:
            details += f"\n… +{len(read_errors) - 8}"
        QMessageBox.warning(
            window, tr("action.convert_python_project"),
            tr("project.python_project_read_errors", count=len(read_errors)) + "\n\n" + details,
        )

    if not convert_folder_to_graphs(window, FILES_FOLDER_ID):
        return
    _save_project_metadata(window)
    window.statusBar().showMessage(
        tr("project.python_project_converted", added=added, refreshed=refreshed), 5000,
    )


def _project_file_for_folder(root: Path) -> Path:
    preferred = root / "Boa_project.boa"
    if preferred.exists():
        return preferred
    candidates = [path for path in root.glob("*.boa") if _looks_like_boa_project(path)]
    return candidates[0] if len(candidates) == 1 else preferred


def _looks_like_boa_project(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and ("graphs" in data or "graph" in data)


def _sync_python_project_tree(window, root: Path) -> tuple[int, int, list[str]]:
    existing_paths = {
        relative.as_posix().casefold(): script_id
        for script_id, relative in script_paths(window.project_tree.to_data()).items()
    }
    files_root = window.project_tree._find(FILES_FOLDER_ID)
    added = refreshed = 0
    errors: list[str] = []

    window.project_tree.blockSignals(True)
    try:
        for source in _python_project_files(root):
            relative = source.relative_to(root)
            try:
                content, source_info = read_script_file(source)
            except (OSError, UnicodeError, SyntaxError, LookupError) as error:
                errors.append(f"{relative.as_posix()} : {error}")
                continue

            key = relative.as_posix().casefold()
            script_id = existing_paths.get(key)
            if script_id:
                item = window._scripts.setdefault(script_id, {})
                item.update({
                    "name": relative.name, "path": relative.as_posix(),
                    "content": content, **source_info,
                })
                refreshed += 1
                continue

            parent = _ensure_tree_folder(window, files_root, relative.parts[:-1])
            script_id = new_id("script")
            window.project_tree._append(parent, relative.name, SCRIPT_KIND, script_id)
            window._scripts[script_id] = {
                "name": relative.name, "path": relative.as_posix(),
                "content": content, **source_info,
            }
            existing_paths[key] = script_id
            added += 1
    finally:
        window.project_tree.blockSignals(False)

    window.project_tree.tree_changed.emit()
    return added, refreshed, errors


def _python_project_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for current, folders, files in os.walk(root):
        folders[:] = sorted(
            name for name in folders
            if name.casefold() not in _IGNORED_PROJECT_FOLDERS
        )
        base = Path(current)
        result.extend(base / name for name in sorted(files) if name.lower().endswith(".py"))
    return result


def _ensure_tree_folder(window, parent, parts: tuple[str, ...]):
    current = parent
    for part in parts:
        found = next((
            current.child(index) for index in range(current.childCount())
            if kind_of(current.child(index)) == FOLDER_KIND
            and current.child(index).text(0).casefold() == part.casefold()
        ), None)
        current = found or window.project_tree._append(current, part, FOLDER_KIND, new_id("folder"))
    return current


def _save_project_metadata(window) -> None:
    if not window.current_file:
        return
    project = save_project(window.current_file, window._project_data())
    window._scripts = deepcopy(project.get("scripts", {}))
    window._graphs = deepcopy(project.get("graphs", {}))
    remember_recent_path(window.preferences, window.current_file)
    save_preferences(window.preferences)
    window._reset_history()
    window._set_dirty(False)


def _is_placeholder_graph(window, script_id: str) -> bool:
    graph_id = window.project_tree.paired_graph_id(script_id)
    if graph_id != "main":
        return False
    entry = window._graphs.get(graph_id, {})
    return not entry.get("source_script_id") and entry.get("graph") == default_graph()


def convert_script_to_graph(window, script_id: str) -> None:
    if script_id not in window._scripts:
        return
    existing = window.project_tree.paired_graph_id(script_id)
    replace = False
    if existing:
        answer = QMessageBox.question(
            window,
            tr("project.graph_conflict_title"),
            tr("project.graph_conflict_message", name=_graph_name(window, script_id)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        replace = True

    from boa.ui.project_actions import store_active_graph
    store_active_graph(window)
    status, message = _convert_one(window, script_id, replace)
    if status == "error":
        QMessageBox.critical(window, tr("python_import.error_title"), message)
        return

    window._refresh_all_function_calls()
    window._record_history()
    graph_id = window.project_tree.paired_graph_id(script_id)
    if graph_id:
        window.open_graph_document(graph_id)
        QTimer.singleShot(0, window.graph_view.focus_program_start)
    QMessageBox.information(
        window,
        tr("python_import.success_title"),
        tr("python_import.success_message", name=_graph_name(window, script_id)) + "\n\n" + message,
    )


def convert_folder_to_graphs(window, folder_id: str) -> bool:
    script_ids = window.project_tree.script_ids_in_folder(folder_id)
    if not script_ids:
        QMessageBox.information(window, tr("project.convert_folder"), tr("project.folder_no_python"))
        return False

    conflicts = [
        script_id for script_id in script_ids
        if window.project_tree.paired_graph_id(script_id) and not _is_placeholder_graph(window, script_id)
    ]
    mode = _conflict_mode(window, len(conflicts)) if conflicts else "replace"
    if mode == "cancel":
        return False

    from boa.ui.project_actions import store_active_graph
    store_active_graph(window)
    batch_snapshot = deepcopy(window._project_data())
    created = replaced = skipped = 0
    errors: list[str] = []
    for script_id in script_ids:
        existing = bool(window.project_tree.paired_graph_id(script_id))
        placeholder = existing and _is_placeholder_graph(window, script_id)
        replace = not existing or placeholder
        if existing and not placeholder:
            if mode == "skip":
                skipped += 1
                continue
            if mode == "ask":
                answer = QMessageBox.question(
                    window,
                    tr("project.graph_conflict_title"),
                    tr("project.graph_conflict_message", name=_graph_name(window, script_id)),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.No,
                )
                if answer == QMessageBox.StandardButton.Cancel:
                    window._restore_project(batch_snapshot)
                    window.statusBar().showMessage(tr("project.conversion_cancelled"), 4000)
                    return False
                if answer != QMessageBox.StandardButton.Yes:
                    skipped += 1
                    continue
            replace = True

        status, message = _convert_one(window, script_id, replace)
        if status == "created":
            created += 1
        elif status == "replaced":
            replaced += 1
        else:
            errors.append(f"{_script_name(window, script_id)} : {message}")

    window._refresh_all_function_calls()
    window._record_history()
    summary = tr(
        "project.folder_conversion_summary",
        total=len(script_ids), created=created, replaced=replaced, skipped=skipped, errors=len(errors),
    )
    if errors:
        summary += "\n\n" + "\n".join(errors[:8])
        if len(errors) > 8:
            summary += f"\n… +{len(errors) - 8}"
    QMessageBox.information(window, tr("project.folder_conversion_done"), summary)
    return True


def _convert_one(window, script_id: str, replace: bool) -> tuple[str, str]:
    item = window._scripts.get(script_id)
    if not item:
        return "error", tr("project.script_missing")
    if window.current_file and script_changed_on_disk(window.current_file, item):
        refresh_script_from_disk(window.current_file, item)

    from boa.python_importer import convert_python_source
    try:
        result = convert_python_source(str(item.get("content", "")), str(item.get("name", "script.py")))
    except (ValueError, SyntaxError) as error:
        return "error", str(error)

    graph_name = _graph_name(window, script_id)
    graph_id = window.project_tree.paired_graph_id(script_id)
    status = "replaced" if graph_id else "created"
    if graph_id and not replace:
        return "error", tr("project.graph_conflict_message", name=graph_name)
    graph_id = graph_id or f"graph_{uuid4().hex[:10]}"
    new_entry = {
        "name": graph_name,
        "graph": result.graph,
        "source_script_id": script_id,
        "imported_function_ids": list(result.functions),
        "imported_class_ids": list(result.classes),
    }
    try:
        _validate_conversion(window, graph_id, new_entry, result)
    except Exception as error:
        return "error", tr("project.conversion_validation_failed", error=str(error))

    snapshot = deepcopy(window._project_data())
    try:
        existing_entry = window._graphs.get(graph_id)
        if existing_entry:
            _remove_previous_definitions(window, existing_entry)
            window.document_tabs.close_document("graph", graph_id)
        else:
            window.project_tree.add_generated_graph(
                graph_id, graph_name, window.project_tree.script_parent_id(script_id),
            )
        window._graphs[graph_id] = new_entry
        window.project_tree.set_item_name(graph_id, graph_name)
        window._functions.update(result.functions)
        window._classes.update(result.classes)
        _add_imported_definitions(window, result.functions, result.classes)
        _merge_context(window, result)
    except Exception as error:
        window._restore_project(snapshot)
        return "error", tr("project.conversion_rolled_back", error=str(error))
    return status, result.report.message()


def _validate_conversion(window, graph_id: str, entry: dict, result) -> None:
    from boa.runtime.code_generator import generate_python

    candidate = deepcopy(window._project_data())
    previous = candidate.get("graphs", {}).get(graph_id, {})
    for function_id in previous.get("imported_function_ids", []):
        candidate.get("functions", {}).pop(function_id, None)
    for class_id in previous.get("imported_class_ids", []):
        candidate.get("classes", {}).pop(class_id, None)
    candidate.setdefault("graphs", {})[graph_id] = deepcopy(entry)
    candidate.setdefault("functions", {}).update(deepcopy(result.functions))
    candidate.setdefault("classes", {}).update(deepcopy(result.classes))
    context = candidate.setdefault("context", {"imports": [], "variables": []})
    known_imports = {str(item.get("statement", "")) for item in context.setdefault("imports", [])}
    context["imports"].extend(
        deepcopy(item) for item in result.imports
        if str(item.get("statement", "")) not in known_imports
    )
    known_variables = {str(item.get("name", "")) for item in context.setdefault("variables", [])}
    context["variables"].extend(
        deepcopy(item) for item in result.variables
        if str(item.get("name", "")) not in known_variables
    )
    candidate["active_graph_id"] = graph_id
    candidate["graph"] = deepcopy(entry.get("graph", {}))
    code = generate_python(candidate)
    compile(code, str(entry.get("name", "conversion.boa")), "exec")


def _merge_context(window, result) -> None:
    for imported in result.imports:
        window.context_panel.add_import(
            str(imported.get("module", "")), str(imported.get("statement", "")),
            str(imported.get("origin", "conversion Python")),
        )
    for variable in result.variables:
        window.context_panel.add_variable(
            str(variable.get("name", "")), str(variable.get("type", "any")),
            str(variable.get("initial", "")), bool(variable.get("constant", False)),
            str(variable.get("scope", "global")),
        )


def _remove_previous_definitions(window, graph_entry: dict) -> None:
    for function_id in graph_entry.get("imported_function_ids", []):
        window.document_tabs.close_document("function", function_id)
        window._functions.pop(function_id, None)
        window.project_tree.remove_item(function_id)
    for class_id in graph_entry.get("imported_class_ids", []):
        window.document_tabs.close_document("class", class_id)
        window._classes.pop(class_id, None)
        window.project_tree.remove_item(class_id)


def _add_imported_definitions(window, functions: dict, classes: dict) -> None:
    pending_classes, pending_functions, added = dict(classes), dict(functions), set()
    while pending_classes or pending_functions:
        progressed = False
        for class_id, class_def in list(pending_classes.items()):
            parent = str(class_def.get("owner_class_id", ""))
            if parent and parent not in added:
                continue
            window.project_tree.add_generated_class(class_id, str(class_def.get("name", "Classe")), parent)
            added.add(class_id); pending_classes.pop(class_id); progressed = True
        for function_id, function in list(pending_functions.items()):
            parent = str(function.get("owner_function_id", "") or function.get("owner_class_id", ""))
            if parent and parent not in added:
                continue
            window.project_tree.add_generated_function(function_id, str(function.get("name", "fonction")), parent)
            added.add(function_id); pending_functions.pop(function_id); progressed = True
        if progressed:
            continue
        for class_id, class_def in list(pending_classes.items()):
            window.project_tree.add_generated_class(class_id, str(class_def.get("name", "Classe")))
            pending_classes.pop(class_id)
        for function_id, function in list(pending_functions.items()):
            window.project_tree.add_generated_function(function_id, str(function.get("name", "fonction")))
            pending_functions.pop(function_id)


def _conflict_mode(window, count: int) -> str:
    box = QMessageBox(window)
    box.setWindowTitle(tr("project.folder_conflicts_title"))
    box.setText(tr("project.folder_conflicts_message", count=count))
    replace = box.addButton(tr("project.replace_all"), QMessageBox.ButtonRole.AcceptRole)
    skip = box.addButton(tr("project.skip_all"), QMessageBox.ButtonRole.DestructiveRole)
    ask = box.addButton(tr("project.ask_each"), QMessageBox.ButtonRole.ActionRole)
    cancel = box.addButton(QMessageBox.StandardButton.Cancel)
    box.exec()
    clicked = box.clickedButton()
    if clicked is replace:
        return "replace"
    if clicked is skip:
        return "skip"
    if clicked is ask:
        return "ask"
    if clicked is cancel:
        return "cancel"
    return "cancel"


def _script_name(window, script_id: str) -> str:
    return str(window._scripts.get(script_id, {}).get("name", "script.py"))


def _graph_name(window, script_id: str) -> str:
    return Path(_script_name(window, script_id)).with_suffix(".boa").name
