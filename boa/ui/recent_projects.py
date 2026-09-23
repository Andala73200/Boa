from pathlib import Path
from PySide6.QtWidgets import QMenu

from boa.core.preferences import save_preferences
from boa.core.project_storage import load_project
from boa.i18n import tr
from boa.ui.dependency_dialog import check_project_dependencies
from boa.ui.environment_controller import ensure_project_environment

MAX_RECENT = 5


def remember_recent_path(preferences: dict, path: Path | str | None) -> None:
    if not path: return
    value = str(Path(path))
    recent = [item for item in preferences.get("recent_projects", []) if item != value]
    preferences["recent_projects"] = [value, *recent][:MAX_RECENT]


def install_recent_menu(menu: QMenu, window) -> None:
    recent_menu = menu.addMenu(tr("menu.recent_projects"))
    recent = [item for item in window.preferences.get("recent_projects", []) if Path(item).exists()]
    if not recent:
        action = recent_menu.addAction(tr("app.no_recent_project")); action.setEnabled(False); return
    for item in recent:
        recent_menu.addAction(Path(item).name).triggered.connect(lambda checked=False, path=item: _open_recent(window, path))


def _open_recent(window, path: str) -> None:
    if not window._confirm_discard_changes(): return
    try:
        window._restore_project(load_project(path)); window.current_file = Path(path)
        remember_recent_path(window.preferences, path); save_preferences(window.preferences); window._reset_history(); window._set_dirty(False)
        window.statusBar().showMessage(tr("app.opened_status", name=Path(path).name), 4000)
        ensure_project_environment(window, lambda: check_project_dependencies(window))
    except Exception as error:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(window, tr("dialog.open_error"), str(error))
