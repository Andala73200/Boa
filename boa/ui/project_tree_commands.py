from __future__ import annotations

from pathlib import Path, PurePosixPath

from PySide6.QtWidgets import QFileDialog, QInputDialog, QMenu, QMessageBox

from boa.core.project_tree_data import CLASSES_FOLDER_ID, FILES_FOLDER_ID, FUNCTIONS_FOLDER_ID
from boa.i18n import tr
from boa.ui.project_tree_items import (
    CLASS_KIND, FOLDER_KIND, FUNCTION_KIND, GRAPH_KIND, ROOT_KIND, SCRIPT_KIND,
    boa_name, child_name_exists, is_protected, item_id, kind_of, new_id,
    normalized_name, py_name, section, sibling_name_exists, valid_item_name, valid_python_name,
)


class ProjectTreeCommands:
    def _show_context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos) or self.tree.topLevelItem(0)
        if item is None:
            return
        self.tree.setCurrentItem(item)
        menu = QMenu(self)
        kind, area = kind_of(item), section(item)
        open_a = run_a = run_graph_a = convert_a = main_a = duplicate_a = None
        if kind == GRAPH_KIND:
            open_a = menu.addAction(tr("project.open"))
            run_graph_a = menu.addAction(tr("project.run_graph"))
            main_a = menu.addAction(tr("project.set_main_graph"))
            duplicate_a = menu.addAction(tr("project.duplicate"))
            menu.addSeparator()
        elif kind == SCRIPT_KIND:
            open_a = menu.addAction(tr("project.open"))
            run_a = menu.addAction(tr("project.run_script"))
            convert_a = menu.addAction(tr("project.convert_to_graph"))
            menu.addSeparator()
        elif kind in {FUNCTION_KIND, CLASS_KIND}:
            open_a = menu.addAction(tr("project.modify"))
            menu.addSeparator()

        add_folder = add_graph = add_script = import_script = add_function = add_class = convert_folder = None
        if kind in {ROOT_KIND, FOLDER_KIND}:
            if area in {"root", "files"}:
                add_folder = menu.addAction(tr("project.add_folder"))
                add_graph = menu.addAction(tr("project.add_graph"))
                add_script = menu.addAction(tr("project.add_script"))
                import_script = menu.addAction(tr("project.import_script"))
                convert_folder = menu.addAction(tr("project.convert_folder"))
            if area in {"root", "functions"}:
                add_function = menu.addAction(tr("project.add_function"))
            if area in {"root", "classes"}:
                add_class = menu.addAction(tr("project.add_class"))
            menu.addSeparator()

        rename = delete = None
        if kind != ROOT_KIND and not is_protected(item):
            rename = menu.addAction(tr("project.rename"))
            delete = menu.addAction(tr("project.delete"))
        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if action is None:
            return
        if action == open_a:
            self._open_item(item)
        elif action == run_graph_a:
            self.graph_run_requested.emit(item_id(item))
        elif action == run_a:
            self.script_run_requested.emit(item_id(item))
        elif action == convert_a:
            self.script_convert_requested.emit(item_id(item))
        elif action == convert_folder:
            folder = item if area == "files" else self._find(FILES_FOLDER_ID)
            self.folder_convert_requested.emit(item_id(folder))
        elif action == main_a:
            self.main_graph_changed.emit(item_id(item)); self.tree_changed.emit()
        elif action == duplicate_a:
            self._duplicate_graph(item)
        elif action == add_folder:
            self._add_folder(item)
        elif action == add_graph:
            self._add_graph(item)
        elif action == add_script:
            self._add_script(item)
        elif action == import_script:
            self._import_script(item)
        elif action == add_function:
            self._add_function()
        elif action == add_class:
            self._add_class()
        elif action == rename:
            self._rename_item(item)
        elif action == delete:
            self._delete_item(item)

    def _add_folder(self, item) -> None:
        parent = self._files_parent(item)
        name, ok = QInputDialog.getText(self, tr("project.add_folder"), tr("project.folder_name"), text=tr("project.new_folder"))
        if ok and valid_item_name(name.strip()):
            self._append(parent, name.strip(), FOLDER_KIND)

    def _add_graph(self, item) -> None:
        parent = self._files_parent(item)
        name, ok = QInputDialog.getText(self, tr("project.add_graph"), tr("project.graph_name"), text="nouveau_graphe.boa")
        if not ok or not valid_item_name(name.strip()):
            return
        name, graph_id = boa_name(name.strip()), new_id("graph")
        self._append(parent, name, GRAPH_KIND, graph_id)
        self.graph_created.emit(graph_id, name)
        self.graph_open_requested.emit(graph_id)

    def _duplicate_graph(self, item) -> None:
        parent = item.parent() or self._find(FILES_FOLDER_ID)
        default = f"{PurePosixPath(item.text(0)).stem}_copie.boa"
        name, ok = QInputDialog.getText(self, tr("project.duplicate"), tr("project.graph_name"), text=default)
        if not ok or not valid_item_name(name.strip()):
            return
        name, graph_id = boa_name(name.strip()), new_id("graph")
        self._append(parent, name, GRAPH_KIND, graph_id)
        self.graph_duplicated.emit(graph_id, item_id(item), name)

    def _add_script(self, item) -> None:
        parent = self._files_parent(item)
        name, ok = QInputDialog.getText(self, tr("project.add_script"), tr("project.script_name"), text="script.py")
        if not ok or not valid_item_name(name.strip()):
            return
        name, script_id = py_name(name.strip()), new_id("script")
        self._append(parent, name, SCRIPT_KIND, script_id)
        self.script_created.emit(script_id, name, "")
        self.script_open_requested.emit(script_id)

    def _import_script(self, item) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("project.import_script"), "", "Python (*.py)")
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            QMessageBox.critical(self, tr("project.import_script"), str(error))
            return
        script_id, name = new_id("script"), Path(path).name
        self._append(self._files_parent(item), name, SCRIPT_KIND, script_id)
        self.script_created.emit(script_id, name, text)

    def _add_function(self) -> None:
        parent = self._find(FUNCTIONS_FOLDER_ID)
        name, ok = QInputDialog.getText(self, tr("project.add_function"), tr("function.name"), text="nouvelle_fonction")
        name = name.strip()
        if not ok or not valid_python_name(name):
            if ok:
                QMessageBox.warning(self, tr("project.add_function"), tr("function.invalid.name"))
            return
        if child_name_exists(parent, name):
            QMessageBox.warning(self, tr("project.add_function"), tr("project.name_exists", name=name)); return
        function_id = new_id("function")
        self._append(parent, name, FUNCTION_KIND, function_id)
        self.function_created.emit(function_id, name)
        self.function_open_requested.emit(function_id)

    def _add_class(self) -> None:
        parent = self._find(CLASSES_FOLDER_ID)
        name, ok = QInputDialog.getText(self, tr("project.add_class"), tr("class.name"), text="NouvelleClasse")
        name = name.strip()
        if not ok or not valid_python_name(name):
            if ok:
                QMessageBox.warning(self, tr("project.add_class"), tr("class.invalid.name"))
            return
        if child_name_exists(parent, name):
            QMessageBox.warning(self, tr("project.add_class"), tr("project.name_exists", name=name)); return
        class_id = new_id("class")
        self._append(parent, name, CLASS_KIND, class_id)
        self.class_created.emit(class_id, name)
        self.class_open_requested.emit(class_id)

    def _delete_item(self, item) -> None:
        if item is None or kind_of(item) == ROOT_KIND or is_protected(item):
            return
        if QMessageBox.question(self, tr("project.delete"), tr("project.delete_confirm", name=item.text(0))) != QMessageBox.StandardButton.Yes:
            return
        self._emit_delete_recursive(item)
        (item.parent() or self.tree.invisibleRootItem()).removeChild(item)
        self._sort_files()
        self.tree_changed.emit()

    def _emit_delete_recursive(self, item) -> None:
        for index in range(item.childCount()):
            self._emit_delete_recursive(item.child(index))
        signal = {
            GRAPH_KIND: self.graph_deleted, SCRIPT_KIND: self.script_deleted,
            FUNCTION_KIND: self.function_deleted, CLASS_KIND: self.class_deleted,
        }.get(kind_of(item))
        if signal:
            signal.emit(item_id(item))

    def _rename_current_item(self) -> None:
        item = self.tree.currentItem()
        if item and kind_of(item) != ROOT_KIND and not is_protected(item):
            self._rename_item(item)

    def _rename_item(self, item) -> None:
        old_name = item.text(0)
        name, ok = QInputDialog.getText(self, tr("project.rename"), tr("project.new_name"), text=old_name)
        if not ok:
            return
        new_name = normalized_name(name.strip(), kind_of(item))
        if not new_name or new_name == old_name:
            return
        if sibling_name_exists(item, new_name):
            QMessageBox.warning(self, tr("project.rename"), tr("project.name_exists", name=new_name)); return

        pair = self._paired_sibling(item)
        if pair:
            pair_name = f"{PurePosixPath(new_name).stem}{PurePosixPath(pair.text(0)).suffix}"
            if sibling_name_exists(pair, pair_name):
                QMessageBox.warning(self, tr("project.rename"), tr("project.name_exists", name=pair_name)); return
            answer = QMessageBox.question(
                self, tr("project.rename_pair_title"),
                tr("project.rename_pair_message", old=pair.text(0), new=pair_name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.tree.blockSignals(True)
                item.setText(0, new_name)
                pair.setText(0, pair_name)
                self.tree.blockSignals(False)
                self._sort_files()
                self.item_renamed.emit(kind_of(item), item_id(item), new_name)
                self.item_renamed.emit(kind_of(pair), item_id(pair), pair_name)
                self.tree_changed.emit()
                return
        item.setText(0, new_name)

    def _paired_sibling(self, item):
        if kind_of(item) not in {SCRIPT_KIND, GRAPH_KIND} or not item.parent():
            return None
        opposite = GRAPH_KIND if kind_of(item) == SCRIPT_KIND else SCRIPT_KIND
        wanted = PurePosixPath(item.text(0)).stem.casefold()
        for index in range(item.parent().childCount()):
            sibling = item.parent().child(index)
            if kind_of(sibling) == opposite and PurePosixPath(sibling.text(0)).stem.casefold() == wanted:
                return sibling
        return None
