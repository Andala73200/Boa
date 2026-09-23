from copy import deepcopy
from pathlib import Path
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QDialog, QFileDialog, QMainWindow, QMessageBox, QSplitter, QVBoxLayout, QWidget
from boa.core.preferences import load_preferences, save_preferences
from boa.core.project_storage import default_graph, empty_project, load_project, normalize_project, save_project
from boa.core.project_environment import dedicated_project_file, import_bindings
from boa.i18n import set_language, tr
from boa.runtime.loop_registry import next_loop_number
from boa.ui.collapsible_panel import CollapsiblePanel
from boa.ui.context_panel import ContextPanel
from boa.ui.graph_view import GraphView
from boa.ui.document_tabs import DocumentTabs
from boa.ui.definition_editor import DefinitionEditor
from boa.ui.preferences_dialog import PreferencesDialog
from boa.ui.right_panel import RightPanel
from boa.ui.runtime_actions import export_python, relaunch_project, simulate_project, stop_project
from boa.ui.recent_projects import install_recent_menu, remember_recent_path
from boa.ui.project_actions import graph_data, install_project_actions, store_active_graph
from boa.ui.project_tree import ProjectTree; from boa.ui.toolbar import BoaToolBar
from boa.ui.translated_message_box import ask_yes_no
from boa.ui.environment_controller import ensure_project_environment; from boa.ui.dependency_dialog import check_project_dependencies
from boa.ui.main_window_blocks import block_actions
from boa.ui.module_import_sync import sync_project_module_imports
from boa.functions.sync import synchronize_calls
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Boa - Graph Python")
        self.resize(1400, 850)
        self.current_file: Path | None = None
        self.preferences = load_preferences()
        set_language(self.preferences.get("language", "fr"))
        self._dirty = False
        self._restoring = False
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []
        self._graphs = {}; self._scripts = {}; self._functions = {}; self._classes = {}; self._active_graph_id = "main"; self._main_graph_id = "main"; self._environment_controller = None
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._autosave_project)
        self.context_panel = ContextPanel()
        self.project_tree = ProjectTree()
        self.right_panel = RightPanel(); self.block_library = self.right_panel.library
        self.toolbar = BoaToolBar()
        self.document_tabs = DocumentTabs(); self.graph_view = self._create_graph_view("graph", "main")
        self._build_layout()
        self._build_menu_bar()
        self._connect_signals()
        self._restore_project(empty_project())
        self._apply_preferences()
        self._reset_history()
        QTimer.singleShot(0, self._finish_initial_project_layout)
        self.statusBar().showMessage(tr("app.ready"))
    def _build_layout(self) -> None:
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.context_dock = CollapsiblePanel(tr("panel.context"), self.context_panel, "top")
        self.project_dock = CollapsiblePanel(tr("panel.project_tree"), self.project_tree, "left")
        self.library_dock = CollapsiblePanel(tr("panel.library"), self.right_panel, "right")
        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.addWidget(self.project_dock)
        self.workspace_splitter.addWidget(self.document_tabs)
        self.workspace_splitter.addWidget(self.library_dock)
        self.workspace_splitter.setSizes([240, 900, 260])
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.addWidget(self.context_dock)
        self.main_splitter.addWidget(self.workspace_splitter)
        self.main_splitter.setSizes([170, 680])
        root_layout.addWidget(self.main_splitter)
        self.setCentralWidget(root)
    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu(tr("menu.file"))
        file_menu.addAction(self._action(tr("action.new_project"), "Ctrl+N", self.new_project))
        file_menu.addAction(self._action(tr("action.open_project"), "Ctrl+O", self.open_project))
        file_menu.addAction(self._action(tr("action.convert_python_project"), None, self.convert_python_project))
        install_recent_menu(file_menu, self)
        file_menu.addSeparator()
        file_menu.addAction(self._action(tr("action.save"), "Ctrl+S", self.save_project))
        file_menu.addAction(self._action(tr("action.save_as"), "Ctrl+Shift+S", self.save_project_as))
        file_menu.addSeparator()
        file_menu.addAction(self._action(tr("action.export_python"), None, lambda: export_python(self)))
        file_menu.addSeparator()
        file_menu.addAction(self._action(tr("action.quit"), "Ctrl+Q", self.close))
        edit_menu = self.menuBar().addMenu(tr("menu.edit"))
        edit_menu.addAction(self._action(tr("action.undo"), "Ctrl+Z", self.undo))
        edit_menu.addAction(self._action(tr("action.redo"), ["Ctrl+Y", "Ctrl+Shift+Z"], self.redo))
        edit_menu.addSeparator()
        edit_menu.addAction(self._action(tr("action.cut"), "Ctrl+X", self.cut_blocks))
        edit_menu.addAction(self._action(tr("action.copy"), "Ctrl+C", self.copy_blocks))
        edit_menu.addAction(self._action(tr("action.paste"), "Ctrl+V", self.paste_blocks))
        edit_menu.addAction(self._action(tr("action.select_all"), "Ctrl+A", self.select_all_blocks))
        edit_menu.addSeparator()
        edit_menu.addAction(self._action(tr("action.delete_selection"), "Del", self.delete_selection))
        run_menu = self.menuBar().addMenu(tr("menu.run"))
        run_menu.addAction(self._action(tr("action.run"), "F5", lambda: simulate_project(self)))
        run_menu.addAction(self._action(tr("action.stop"), "Shift+F5", lambda: stop_project(self)))
        run_menu.addAction(self._action(tr("action.relaunch"), "Ctrl+F5", lambda: relaunch_project(self)))
        run_menu.addAction(self._action(tr("action.dependencies"), None, lambda: ensure_project_environment(self, lambda: check_project_dependencies(self, show_all=True))))
        view_menu = self.menuBar().addMenu(tr("menu.view"))
        view_menu.addAction(self._action(tr("action.toggle_context"), "Ctrl+Alt+H", self.context_dock.toggle_collapsed))
        view_menu.addAction(self._action(tr("action.toggle_tree"), "Ctrl+Alt+G", self.project_dock.toggle_collapsed))
        view_menu.addAction(self._action(tr("action.toggle_library"), "Ctrl+Alt+B", self.library_dock.toggle_collapsed))
        view_menu.addSeparator()
        view_menu.addAction(self._action(tr("action.center_graph"), "Ctrl+0", lambda: self.graph_view.centerOn(0, 0)))
        block_menu = self.menuBar().addMenu(tr("menu.blocks"))
        for label, key, shortcut in block_actions():
            block_menu.addAction(self._action(label, shortcut, lambda checked=False, block_key=key: self.graph_view.add_block(block_key)))
        pref_menu = self.menuBar().addMenu(tr("menu.preferences"))
        pref_menu.addAction(self._action(tr("action.options"), "Ctrl+,", self.open_preferences))
        from boa.ui.help_dialogs import show_about, show_controls, show_conversion_limits, show_quick_start
        help_menu = self.menuBar().addMenu(tr("menu.help"))
        help_menu.addAction(self._action(tr("help.quick_start"), None, lambda: show_quick_start(self)))
        help_menu.addAction(self._action(tr("help.controls"), None, lambda: show_controls(self)))
        help_menu.addAction(self._action(tr("help.conversion"), None, lambda: show_conversion_limits(self)))
        help_menu.addSeparator()
        help_menu.addAction(self._action(tr("help.about"), None, lambda: show_about(self)))
    def _connect_signals(self) -> None:
        self.toolbar.block_requested.connect(lambda key: self.graph_view.add_block(key))
        self.right_panel.block_requested.connect(lambda key: self.graph_view.add_block(key)); self.right_panel.loop_requested.connect(lambda path: self.graph_view.open_loop_by_path(path))
        self.document_tabs.document_activated.connect(self._activate_document)
        self.document_tabs.document_closed.connect(lambda *_: QTimer.singleShot(0, self._ensure_document_open))
        self.context_panel.context_changed.connect(self._record_history)
        self.context_panel.variable_block_requested.connect(self._add_variable_block)
        self.context_panel.variable_renamed.connect(lambda old, new: self._each_view(lambda view: view.rename_variable_blocks(old, new)))
        self.context_panel.variable_definition_changed.connect(lambda name, value_type, constant: self._each_view(lambda view: view.update_variable_blocks(name, value_type, constant)))
        self.project_tree.tree_changed.connect(self._record_history); install_project_actions(self)

    def _create_graph_view(self, kind: str, uid: str) -> GraphView:
        view = GraphView(); view.document_kind = kind; view.document_id = uid; view.scene.set_document_mode(kind)
        view.variable_names_provider = self.context_panel._variable_names
        view.variable_entries_provider = lambda: self.context_panel.to_data().get("variables", [])
        view.project_root_provider = lambda: str(self.current_file.parent) if self.current_file else self._default_project_dir()
        view.loop_number_provider = lambda key: next_loop_number(self._project_data(), key)
        view.functions_provider = lambda: deepcopy(self._functions)
        view.function_open_callback = self.open_function_document
        view.class_open_callback = self.open_class_document
        view.import_detected.connect(lambda module, statement, current=view: self._auto_add_import_for_view(current, module, statement)); view.variable_detected.connect(self._auto_add_variable)
        view.graph_changed.connect(lambda current=view: self._document_changed(current))
        view.instances_changed.connect(lambda current=view: self.right_panel.set_project_data({"graph": current.to_data()}) if current is self.graph_view else None)
        if kind == "function":
            view.blocked_block_keys = {"run", "function_start", "function_return", "class_attribute"}
        elif kind == "class":
            view.blocked_block_keys = {"run", "start", "end", "function_start", "function_return", "def_input", "def_input_p", "def_output", "def_output_p", "return"}
        else:
            view.blocked_block_keys = {"function_start", "function_return", "def_input", "def_input_p", "def_output", "def_output_p", "class_attribute", "return"}
        view.set_grid_size(int(self.preferences.get("grid_size", 20))); view.set_snap_enabled(bool(self.preferences.get("snap_to_grid", True)))
        return view

    def open_graph_document(self, graph_id: str) -> None:
        if graph_id not in self._graphs: return
        existing = self.document_tabs.widget_for("graph", graph_id)
        view = existing if isinstance(existing, GraphView) else self._create_graph_view("graph", graph_id)
        if existing is None: view.from_data(graph_data(self, graph_id))
        self.document_tabs.open_document("graph", graph_id, self._graphs[graph_id].get("name", graph_id), view)

    def open_function_document(self, function_id: str) -> None:
        function = self._functions.get(function_id)
        if not function:
            return
        existing = self.document_tabs.widget_for("function", function_id)
        editor = existing if isinstance(existing, DefinitionEditor) else None
        if editor is None:
            view = self._create_graph_view("function", function_id)
            view.from_data(function.get("graph", {}))
            editor = DefinitionEditor("function", function_id, view)
            editor.set_metadata(function)
            editor.changed.connect(lambda current=editor: self._definition_metadata_changed(current))
        self.document_tabs.open_document("function", function_id, f"{function.get('name', function_id)} (DEF)", editor)

    def open_class_document(self, class_id: str) -> None:
        class_def = self._classes.get(class_id)
        if not class_def:
            return
        existing = self.document_tabs.widget_for("class", class_id)
        editor = existing if isinstance(existing, DefinitionEditor) else None
        if editor is None:
            view = self._create_graph_view("class", class_id)
            view.from_data(class_def.get("graph", {}))
            editor = DefinitionEditor("class", class_id, view)
            editor.set_metadata(class_def)
            editor.changed.connect(lambda current=editor: self._definition_metadata_changed(current))
        self.document_tabs.open_document("class", class_id, f"{class_def.get('name', class_id)} (Classe)", editor)

    def _activate_document(self, kind: str, uid: str, widget) -> None:
        if self._restoring:
            return
        view = self._graph_widget(widget)
        if view is None:
            return
        self.graph_view = view
        self.block_library.set_document_kind(kind)
        self.toolbar.set_document_kind(kind)
        if kind == "graph":
            self._active_graph_id = uid
        self.right_panel.set_project_data({"graph": view.to_data()})

    def _ensure_document_open(self) -> None:
        documents = self.document_tabs.documents()
        current = self.document_tabs.currentWidget()
        if self._graph_widget(current) is not None:
            for kind, uid, widget in documents:
                if widget is current: self._activate_document(kind, uid, widget); return
        if documents:
            kind, uid, widget = documents[0]; self._activate_document(kind, uid, widget); return
        graph_id = self._active_graph_id if self._active_graph_id in self._graphs else next(iter(self._graphs), "")
        if graph_id: self.open_graph_document(graph_id)

    def _document_changed(self, view: GraphView) -> None:
        if self._restoring:
            return
        if view.document_kind == "function" and view.document_id in self._functions:
            self._functions[view.document_id]["graph"] = view.to_data()
            self._refresh_all_function_calls()
        elif view.document_kind == "class" and view.document_id in self._classes:
            self._classes[view.document_id]["graph"] = view.to_data()
        elif view.document_id in self._graphs:
            self._graphs[view.document_id]["graph"] = view.to_data()
        self._record_history()

    def _definition_metadata_changed(self, editor: DefinitionEditor) -> None:
        if self._restoring:
            return
        target = self._functions.get(editor.document_id) if editor.document_kind == "function" else self._classes.get(editor.document_id)
        if target is None:
            return
        target.update(editor.metadata())
        self._record_history()

    def _refresh_all_function_calls(self) -> None:
        self._store_open_documents()
        for item in self._graphs.values(): synchronize_calls(item.get("graph", {}), self._functions)
        for function in self._functions.values(): synchronize_calls(function.get("graph", {}), self._functions)
        for class_def in self._classes.values(): synchronize_calls(class_def.get("graph", {}), self._functions)
        self._each_view(lambda view: view.refresh_function_calls())

    def _each_view(self, callback) -> None:
        for _kind, _uid, widget in self.document_tabs.documents():
            view = self._graph_widget(widget)
            if view is not None:
                callback(view)

    @staticmethod
    def _graph_widget(widget) -> GraphView | None:
        if isinstance(widget, GraphView):
            return widget
        if isinstance(widget, DefinitionEditor):
            return widget.graph_view
        return None
    def new_project(self) -> None:
        if not self._confirm_discard_changes(): return
        self.current_file = None
        self._restore_project(empty_project())
        self._position_new_project_run()
        self._reset_history()
        self._set_dirty(False)
        self.statusBar().showMessage(tr("app.new_project_status"), 3000)
        self.save_project_as()
    def open_project(self) -> None:
        if not self._confirm_discard_changes(): return
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dialog.open_title"), self._default_project_dir(), tr("dialog.open_filter"),
        )
        if not path: return
        selected = Path(path)
        if selected.suffix.lower() == ".py":
            from boa.ui.python_file_project import open_python_file_as_project
            open_python_file_as_project(self, selected)
            return
        try:
            self._restore_project(load_project(selected))
            self.current_file = selected; remember_recent_path(self.preferences, self.current_file); save_preferences(self.preferences)
            self._reset_history()
            self._set_dirty(False)
            self.statusBar().showMessage(tr("app.opened_status", name=self.current_file.name), 4000)
            ensure_project_environment(self, lambda: check_project_dependencies(self))
        except Exception as error:
            QMessageBox.critical(self, tr("dialog.open_error"), str(error))
    def convert_python_project(self) -> None:
        from boa.ui.project_conversion import convert_python_project
        convert_python_project(self)

    def save_project(self) -> bool:
        if self.current_file is None:
            return self.save_project_as()
        try:
            saved = save_project(self.current_file, self._project_data()); self._scripts = deepcopy(saved["scripts"]); self._graphs = deepcopy(saved["graphs"]); remember_recent_path(self.preferences, self.current_file); save_preferences(self.preferences)
            self._set_dirty(False)
            self.statusBar().showMessage(tr("app.saved_status", name=self.current_file.name), 3000)
            ensure_project_environment(self)
            return True
        except Exception as error:
            QMessageBox.critical(self, tr("dialog.save_error"), str(error))
            return False
    def save_project_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, tr("dialog.save_as_title"), str(Path(self._default_project_dir()) / "Boa_project.boa"), "Projet Boa (*.boa)")
        if not path: return False
        target = Path(path)
        if target.suffix.lower() != ".boa":
            target = target.with_suffix(".boa")
        target = dedicated_project_file(target); target.parent.mkdir(parents=True, exist_ok=True)
        self.current_file = target
        return self.save_project()
    def undo(self) -> None:
        if len(self._undo_stack) <= 1: return
        self._redo_stack.append(self._undo_stack.pop())
        self._restore_project(deepcopy(self._undo_stack[-1]))
        self._set_dirty(True)
        self.statusBar().showMessage(tr("app.undo"), 2000)
    def redo(self) -> None:
        if not self._redo_stack: return
        state = self._redo_stack.pop()
        self._undo_stack.append(deepcopy(state))
        self._restore_project(state)
        self._set_dirty(True)
        self.statusBar().showMessage(tr("app.redo"), 2000)
    def copy_blocks(self) -> None:
        self.statusBar().showMessage(tr("app.copied", count=self.graph_view.copy_selected_blocks()), 2500)
    def cut_blocks(self) -> None:
        self.statusBar().showMessage(tr("app.cut", count=self.graph_view.cut_selected_blocks()), 2500)
    def paste_blocks(self) -> None:
        self.statusBar().showMessage(tr("app.pasted", count=self.graph_view.paste_blocks()), 2500)
    def select_all_blocks(self) -> None:
        self.statusBar().showMessage(tr("app.selected", count=self.graph_view.select_all_blocks()), 2000)
    def delete_selection(self) -> None:
        if not self._confirm_delete_selection(): return
        count = self.graph_view.delete_selected_items()
        self.statusBar().showMessage(tr("app.deleted", count=count), 3000)
    def open_preferences(self) -> None:
        dialog = PreferencesDialog(self.preferences, self)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        self.preferences = dialog.preferences()
        save_preferences(self.preferences)
        set_language(self.preferences.get("language", "fr"))
        self._apply_preferences()
        self._retranslate_ui()
        self.statusBar().showMessage(tr("app.preferences_saved"), 3000)
    def _apply_preferences(self) -> None:
        self._each_view(lambda view: view.set_grid_size(int(self.preferences.get("grid_size", 20))))
        self._each_view(lambda view: view.set_snap_enabled(bool(self.preferences.get("snap_to_grid", True))))
        if self.preferences.get("autosave_enabled", False):
            interval = int(self.preferences.get("autosave_interval", 5)) * 60 * 1000
            self._autosave_timer.start(max(interval, 60000))
        else:
            self._autosave_timer.stop()
    def _retranslate_ui(self) -> None:
        self.menuBar().clear()
        self._build_menu_bar()
        self.toolbar.retranslate_ui()
        self.right_panel.retranslate_ui()
        self.project_tree.retranslate_ui()
        self.context_panel.retranslate_ui()
        self.context_dock.set_title(tr("panel.context"))
        self.project_dock.set_title(tr("panel.project_tree"))
        self.library_dock.set_title(tr("panel.library"))
        self._each_view(lambda view: view.refresh_tooltips())
        self._set_dirty(self._dirty)

    def _finish_initial_project_layout(self) -> None:
        self._position_new_project_run()
        self._reset_history()

    def _position_new_project_run(self) -> None:
        if self.graph_view.position_run_for_new_project():
            self._graphs.setdefault(self._active_graph_id, {"name": f"{self._active_graph_id}.boa"})["graph"] = self.graph_view.to_data()
    def _autosave_project(self) -> None:
        if not self.current_file or not self._dirty: return
        try:
            saved = save_project(self.current_file, self._project_data()); self._scripts = deepcopy(saved["scripts"]); self._graphs = deepcopy(saved["graphs"]); remember_recent_path(self.preferences, self.current_file); save_preferences(self.preferences)
            self._set_dirty(False)
        except Exception as error:
            self.statusBar().showMessage(tr("app.autosave_failed", error=str(error)), 12000)
    def closeEvent(self, event) -> None:
        event.accept() if self._confirm_discard_changes() else event.ignore()
    def _record_history(self) -> None:
        if self._restoring:
            return
        snapshot = self._project_data()
        if self._undo_stack and snapshot == self._undo_stack[-1]:
            return
        self._undo_stack.append(deepcopy(snapshot))
        self._undo_stack = self._undo_stack[-80:]
        self._redo_stack.clear()
        self._set_dirty(True)
    def _reset_history(self) -> None:
        self._undo_stack = [deepcopy(self._project_data())]
        self._redo_stack.clear()
    def _restore_project(self, data: dict) -> None:
        self._restoring = True; data = normalize_project(data)
        self._graphs = deepcopy(data.get("graphs", {})); self._scripts = deepcopy(data.get("scripts", {})); self._functions = deepcopy(data.get("functions", {})); self._classes = deepcopy(data.get("classes", {}))
        self._active_graph_id = data.get("active_graph_id", "main"); self._main_graph_id = data.get("main_graph_id", self._active_graph_id)
        self.context_panel.from_data(data.get("context", {})); self.project_tree.from_data(data.get("tree"))
        self.project_tree.set_main_graph_id(self._main_graph_id)
        self.document_tabs.clear_documents(); self.graph_view = self._create_graph_view("graph", self._active_graph_id)
        self.graph_view.from_data(graph_data(self, self._active_graph_id)); self.document_tabs.open_document("graph", self._active_graph_id, self._graphs[self._active_graph_id].get("name", self._active_graph_id), self.graph_view)
        self.block_library.set_document_kind("graph"); self.toolbar.set_document_kind("graph")
        self.right_panel.set_project_data(self._project_data())
        self._restoring = False
    def _project_data(self) -> dict:
        data = empty_project(); self._store_open_documents()
        sync_project_module_imports(self.context_panel, self._graphs)
        data["context"] = self.context_panel.to_data(); data["graphs"] = deepcopy(self._graphs); data["scripts"] = deepcopy(self._scripts); data["functions"] = deepcopy(self._functions); data["classes"] = deepcopy(self._classes)
        data["active_graph_id"] = self._active_graph_id; data["main_graph_id"] = self._main_graph_id
        data["graph"] = graph_data(self, self._main_graph_id); data["tree"] = self.project_tree.to_data(); return data
    def _store_open_documents(self) -> None:
        for kind, uid, widget in self.document_tabs.documents():
            view = self._graph_widget(widget)
            if view is None:
                continue
            if kind == "graph" and uid in self._graphs:
                self._graphs[uid]["graph"] = view.to_data()
            if kind == "function" and uid in self._functions:
                self._functions[uid]["graph"] = view.to_data()
                if isinstance(widget, DefinitionEditor):
                    self._functions[uid].update(widget.metadata())
            if kind == "class" and uid in self._classes:
                self._classes[uid]["graph"] = view.to_data()
                if isinstance(widget, DefinitionEditor):
                    self._classes[uid].update(widget.metadata())
    def _set_functions(self, functions: dict) -> None:
        if functions == self._functions: return
        self._functions = deepcopy(functions)
        self._refresh_all_function_calls()
        self._record_history()
    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        name = self.current_file.name if self.current_file else tr("app.untitled")
        marker = " *" if dirty else ""
        self.setWindowTitle(f"Boa - Graph Python - {name}{marker}")
    def _confirm_delete_selection(self) -> bool:
        if not self.preferences.get("confirm_delete", False) or not self.graph_view.has_selection(): return True
        return ask_yes_no(self, tr("dialog.delete_title"), tr("dialog.delete_message"), tr("dialog.yes"), tr("dialog.no"))
    def _default_project_dir(self) -> str:
        folder = str(self.preferences.get("default_project_dir", "")).strip()
        return folder if folder and Path(folder).exists() else ""
    def _confirm_discard_changes(self) -> bool:
        if not self._dirty: return True
        return ask_yes_no(self, tr("dialog.unsaved_title"), tr("dialog.unsaved_message"), tr("dialog.yes"), tr("dialog.no"))
    def _auto_add_import(self, module: str, statement: str) -> None:
        if not self.preferences.get("auto_imports", True):
            self.statusBar().showMessage(tr("app.import_disabled", statement=statement), 4000)
            return
        statements = [item.get("statement", "") for item in self.context_panel.to_data().get("imports", [])]
        if module in import_bindings(statements): return
        self.context_panel.add_import(module, statement, "auto")
        self.statusBar().showMessage(tr("app.import_auto", statement=statement), 4000)
    def _auto_add_import_for_view(self, view: GraphView, module: str, statement: str) -> None:
        if view.document_kind == "graph":
            self._auto_add_import(module, statement)
            return
        if not self.preferences.get("auto_imports", True):
            self.statusBar().showMessage(tr("app.import_disabled", statement=statement), 4000)
            return
        definitions = self._functions if view.document_kind == "function" else self._classes
        target = definitions.get(view.document_id)
        if target is None:
            return
        imports = list(target.get("imports", []))
        statements = [str(item.get("statement", "")) for item in imports if isinstance(item, dict)]
        global_statements = [
            str(item.get("statement", ""))
            for item in self.context_panel.to_data().get("imports", [])
            if isinstance(item, dict)
        ]
        if module in import_bindings([*global_statements, *statements]):
            return
        imports.append({"module": module, "statement": statement, "origin": "auto"})
        target["imports"] = imports
        editor = self.document_tabs.widget_for(view.document_kind, view.document_id)
        if isinstance(editor, DefinitionEditor):
            editor.imports.set_entries(imports)
        self._record_history()
        self.statusBar().showMessage(tr("app.import_auto", statement=statement), 4000)
    def _auto_add_variable(self, name: str) -> None:
        default_type = self.preferences.get("default_variable_type", "any")
        self.context_panel.add_variable(name, default_type, "", False, "global")
        self.statusBar().showMessage(tr("app.variable_detected", name=name), 4000)
    def _add_variable_block(self, name: str, value_type: str, is_constant: bool) -> None:
        self.graph_view.add_variable_block(name, value_type, is_constant)
        self.statusBar().showMessage(tr("app.variable_block_added", name=name), 2500)
    def _action(self, text: str, shortcut=None, callback=None) -> QAction:
        action = QAction(text, self)
        if shortcut:
            shortcuts = shortcut if isinstance(shortcut, list) else [shortcut]
            action.setShortcuts([QKeySequence(item) for item in shortcuts])
        if callback: action.triggered.connect(callback)
        return action
