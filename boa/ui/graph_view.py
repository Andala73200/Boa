from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication, QGraphicsView, QInputDialog, QMenu, QMessageBox
from uuid import uuid4

from boa.blocks import create_block
from boa.blocks.base_block import BlockItem
from boa.blocks.definition_blocks import DecoratorBlockItem
from boa.blocks.block_factory import apply_for_outputs, create_tp_block, create_variable_block
from boa.functions.blocks import apply_def_port_config, apply_missing_call, apply_project_call
from boa.functions.models import DEF_PORT_KEYS, INPUT_KEYS, OUTPUT_KEYS
from boa.functions.port_dialog import edit_def_port_block
from boa.blocks.smart_block import SmartBlockItem
from boa.ui.block_library import BOA_BLOCK_MIME
from boa.ui.block_comment_dialog import edit_block_comment
from boa.ui.block_titles import retranslate_block
from boa.ui.block_shortcuts import remember_block_used
from boa.ui.call_dialog import edit_call_block
from boa.ui.connection_item import ConnectionItem, TemporaryConnectionItem
from boa.ui.connection_rules import preview_connection_status, refresh_connection_statuses
from boa.ui.graph_block_data import block_from_data, uid_number
from boa.ui.graph_view_state import GraphViewStateMixin
from boa.ui.grid_scene import GridScene
from boa.ui.loop_dialogs import edit_for_block, edit_while_block, open_instance_dialog
from boa.ui.loop_instance_nav import open_loop_path
from boa.ui.module_block_dialog import edit_module_block
from boa.ui.print_block_edit import edit_print_block
from boa.ui.python_block_edit import edit_python_block
from boa.ui.python_native_branch_nav import open_native_branch
from boa.ui.python_native_dialogs import (
    edit_attribute_get, edit_class_attribute, edit_match_block, edit_multi_assign,
    edit_return_block, edit_try_block, edit_with_block,
)
from boa.ui.tp_tools import edit_tp_number, next_tp_number
from boa.ui.tp_type_sync import refresh_tp_types
from boa.ui.value_input_dialog import edit_input_block, edit_value_block
from boa.ui.decorator_stack import attached_decorators, detach_target, handle_block_moved, prepare_decorator, reflow_all, reflow_target
from boa.ui.dynamic_call_ports import ensure_after_connection, trim_after_removal
from boa.core.module_registry import MODULE_SPECS
from boa.core.module_specs import module_has_selectable_outputs
from boa.i18n import tr


class GraphView(GraphViewStateMixin, QGraphicsView):
    import_detected = Signal(str, str)
    variable_detected = Signal(str)
    graph_changed = Signal()
    instances_changed = Signal()
    COMMENT_DISABLED_KEYS = {"run", "true", "false", "none", "variable", "start", "end"}

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.scene = GridScene(self); self.scene.setSceneRect(-2000, -2000, 4000, 4000); self.setScene(self.scene)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus); self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag); self.setAcceptDrops(True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self._view_insert_index = 0; self._next_uid = 1; self._clipboard_fragment: dict = {"blocks": [], "connections": []}
        self._connection_source: BlockItem | None = None; self._connection_source_port = ""; self._temporary_connection: TemporaryConnectionItem | None = None
        self._panning = False; self._pan_start = QPoint(); self._boa_drag_inside = False
        self._left_empty_press: QPoint | None = None
        self._right_empty_press: QPoint | None = None
        self._right_press_on_empty = False
        self._empty_press_had_selection = False
        self._right_empty_moved = False
        self._suppress_context_menu = False
        self.variable_names_provider = lambda: [] ; self.variable_entries_provider = lambda: []
        self.project_root_provider = lambda: ""
        self.loop_number_provider = lambda key: self._local_next_loop_number(key)
        self.functions_provider = lambda: {}
        self.functions_changed_callback = lambda functions: None
        self.function_open_callback = lambda function_id: None
        self.class_open_callback = lambda class_id: None
        self.document_kind = "graph"; self.document_id = ""
        self.blocked_block_keys: set[str] = set()

    def set_grid_size(self, size: int) -> None:
        self.scene.set_grid_size(size); BlockItem.GRID_SIZE = max(10, int(size))

    def set_snap_enabled(self, enabled: bool) -> None:
        BlockItem.SNAP_ENABLED = bool(enabled)

    def has_selection(self) -> bool:
        return bool(self.scene.selectedItems())

    def add_block(self, block_key: str) -> None:
        if block_key == "run" or block_key in self.blocked_block_keys: return
        remember_block_used(block_key)
        if block_key == "tp":
            self._add_tp_pair(self._visible_insertion_position(318, 36)); return
        block = self._new_block(block_key)
        self._add_prepared_block(block, self._visible_insertion_position(block.WIDTH, block.HEIGHT))

    def add_block_at(self, block_key: str, pos: QPointF) -> None:
        if block_key == "run" or block_key in self.blocked_block_keys: return
        remember_block_used(block_key)
        if block_key == "tp":
            self._add_tp_pair(pos); return
        self._add_prepared_block(self._new_block(block_key), pos)

    def add_variable_block(self, name: str, value_type: str = "any", is_constant: bool = False) -> None:
        block = create_variable_block(name, value_type, is_constant); self._prepare_block(block)
        self._add_prepared_block(block, self._visible_insertion_position(block.WIDTH, block.HEIGHT))

    def mouseDoubleClickEvent(self, event) -> None:
        item = self.itemAt(event.pos())
        if isinstance(item, BlockItem):
            if item.block_key == "decorator":
                text, ok = QInputDialog.getText(self, "Décorateur", "Expression après @ :", text=str(getattr(item, "decorator_expression", "decorateur")))
                if ok and text.strip():
                    item.decorator_expression = text.strip().lstrip("@")
                    item.refresh_tooltip(); item.update(); self._changed()
                event.accept(); return
            if item.block_key in {"def_marker", "class_marker"}:
                definition_id = str(getattr(item, "definition_id", ""))
                if definition_id:
                    (self.function_open_callback if item.block_key == "def_marker" else self.class_open_callback)(definition_id)
                event.accept(); return
            if item.block_key == "python_node":
                if getattr(item, "python_kind", "") == "function_marker":
                    function_id = str(getattr(item, "python_function_id", ""))
                    if function_id:
                        self.function_open_callback(function_id)
                    event.accept(); return
                changed, imports = edit_python_block(item, self)
                if changed:
                    self._drop_python_data_connections(item)
                    for imported in imports:
                        module = str(imported.get("module", ""))
                        statement = str(imported.get("statement", ""))
                        if module and statement:
                            self.import_detected.emit(module, statement)
                    self._refresh_connection_states(); self._changed()
                event.accept(); return
            if item.block_key in {"return", "function_return"}:
                if edit_return_block(item, self):
                    self._drop_invalid_connections(item); self._refresh_connection_states(); self._changed()
                event.accept(); return
            if item.block_key == "attribute_get":
                if edit_attribute_get(item, self): self._changed()
                event.accept(); return
            if item.block_key == "class_attribute":
                if edit_class_attribute(item, self): self._drop_invalid_connections(item); self._changed()
                event.accept(); return
            if item.block_key == "multi_assign":
                if edit_multi_assign(item, self): self._drop_invalid_connections(item); self._changed()
                event.accept(); return
            if item.block_key == "try":
                if edit_try_block(item, self): self._drop_invalid_connections(item); self._changed()
                event.accept(); return
            if item.block_key == "match":
                if edit_match_block(item, self): self._drop_invalid_connections(item); self._changed()
                event.accept(); return
            if item.block_key == "with":
                if edit_with_block(item, self): self._drop_invalid_connections(item); self._changed()
                event.accept(); return
            if item.block_key == "print":
                if edit_print_block(item, self.variable_names_provider, self): self._changed()
                event.accept(); return
            if item.block_key == "tp":
                if edit_tp_number(self, self._all_blocks(), item): self._changed()
                event.accept(); return
            if item.block_key == "for": self._edit_for_block(item); event.accept(); return
            if item.block_key == "while": self._edit_while_block(item); event.accept(); return
            if item.block_key == "value":
                if edit_value_block(item, self): self._refresh_connection_states(); self._changed()
                event.accept(); return
            if item.block_key == "input":
                if edit_input_block(item, self): self._refresh_connection_states(); self._changed()
                event.accept(); return
            if item.block_key == "assign":
                text, ok = QInputDialog.getText(self, "Affectation", "Variable ou attribut cible :", text=str(getattr(item, "python_target", "") or getattr(item, "variable_name", "variable")))
                target = text.strip()
                if ok and target and all(part.isidentifier() for part in target.split(".")):
                    item.variable_name = target; item.python_target = target if "." in target else ""
                    item.subtitle = target; item.update(); self._changed()
                event.accept(); return
            if item.block_key == "call":
                ok, module, statement, open_id = edit_call_block(
                    item, self.functions_provider(), self, self._known_call_roots(),
                )
                if ok:
                    if module and statement: self.import_detected.emit(module, statement)
                    self._refresh_connection_states(); self._changed()
                if open_id: self.function_open_callback(open_id)
                event.accept(); return
            if item.block_key in DEF_PORT_KEYS:
                group = INPUT_KEYS if item.block_key in INPUT_KEYS else OUTPUT_KEYS
                names = {getattr(other, "def_port_name", "") for other in self._all_blocks() if other.block_key in group and other is not item}
                if edit_def_port_block(item, names, self): self._refresh_connection_states(); self._changed()
                event.accept(); return
            if item.block_key in MODULE_SPECS and (
                MODULE_SPECS[item.block_key].fields
                or module_has_selectable_outputs(MODULE_SPECS[item.block_key])
            ):
                if edit_module_block(item, self.project_root_provider(), self):
                    self._drop_invalid_connections(item)
                    self._refresh_connection_states(); self._changed()
                event.accept(); return
            if item.block_key != "empty" and item.modifiable:
                if edit_block_comment(item, self): self._changed()
                event.accept(); return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:
        if self._suppress_context_menu:
            self._suppress_context_menu = False
            event.accept()
            return
        item = self.itemAt(event.pos())
        if isinstance(item, ConnectionItem):
            self._show_delete_menu(event, item, tr("graph.delete_connection")); return
        if isinstance(item, BlockItem):
            self._select_items([item])
            menu = QMenu(self)
            add_decorator = None
            open_branch = None
            if item.block_key in {"def_marker", "class_marker"}:
                add_decorator = menu.addAction("Ajouter un décorateur @")
                menu.addSeparator()
            if item.block_key in {"try", "match", "with"}:
                open_branch = menu.addAction("Ouvrir une branche…")
                menu.addSeparator()
            delete_action = None
            if not getattr(item, "protected", False):
                delete_action = menu.addAction(tr("graph.delete_block"))
            action = menu.exec(event.globalPos())
            if add_decorator is not None and action == add_decorator:
                self._add_decorator_to_marker(item)
            elif open_branch is not None and action == open_branch:
                open_native_branch(self, item)
            elif action == delete_action and delete_action is not None:
                if self._remove_block(item) is not False:
                    self._changed()
            return
        if item is None:
            event.accept()
            return
        super().contextMenuEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete: self.delete_selected_items(); event.accept(); return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._both_mouse_buttons(event):
            self._start_view_pan(event.pos())
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            hit = self._block_at_port(self.mapToScene(event.pos()), "output")
            if hit: self._start_connection(hit[0], hit[1]); event.accept(); return
            if self.itemAt(event.pos()) is None:
                self._left_empty_press = event.pos()
                self._empty_press_had_selection = self.has_selection()
                super().mousePressEvent(event)
                return
        if event.button() == Qt.MouseButton.RightButton:
            self._right_empty_press = event.pos()
            self._right_press_on_empty = self.itemAt(event.pos()) is None
            self._right_empty_moved = False
            self._empty_press_had_selection = self.has_selection()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._temporary_connection:
            scene_pos = self.mapToScene(event.pos()); target = self._block_at_port(scene_pos, "input"); status = "normal"
            if target and self._connection_source: status = preview_connection_status(self._all_connections(), self._connection_source, self._connection_source_port, target[0], target[1])
            self._temporary_connection.set_status(status); self._temporary_connection.update_path(scene_pos); event.accept(); return
        if self._panning:
            delta = event.pos() - self._pan_start; self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x()); self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept(); return
        if self._right_empty_press is not None:
            if (event.pos() - self._right_empty_press).manhattanLength() >= QApplication.startDragDistance():
                self._right_empty_moved = True
                self._start_view_pan(event.pos())
            event.accept(); return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._connection_source: self._finish_connection(self._block_at_port(self.mapToScene(event.pos()), "input")); event.accept(); return
        if self._panning:
            self._stop_view_pan()
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton and self._right_empty_press is not None:
            moved = self._right_empty_moved or (event.pos() - self._right_empty_press).manhattanLength() >= QApplication.startDragDistance()
            if not moved and self._right_press_on_empty and self._empty_press_had_selection:
                self.scene.clearSelection()
            self._right_empty_press = None
            self._right_press_on_empty = False
            self._right_empty_moved = False
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self._left_empty_press is not None:
            press = self._left_empty_press
            had_selection = self._empty_press_had_selection
            self._left_empty_press = None
            super().mouseReleaseEvent(event)
            if (event.pos() - press).manhattanLength() < QApplication.startDragDistance() and had_selection:
                self.scene.clearSelection()
            return
        super().mouseReleaseEvent(event)

    @staticmethod
    def _both_mouse_buttons(event) -> bool:
        buttons = event.buttons()
        return bool(buttons & Qt.MouseButton.LeftButton and buttons & Qt.MouseButton.RightButton)

    def _start_view_pan(self, pos: QPoint) -> None:
        if self._panning:
            return
        grabber = self.scene.mouseGrabberItem()
        if grabber is not None:
            grabber.ungrabMouse()
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._left_empty_press = None
        self._right_empty_press = None
        self._right_press_on_empty = False
        self._right_empty_moved = False
        self._panning = True
        self._pan_start = pos
        self._suppress_context_menu = True
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _stop_view_pan(self) -> None:
        self._panning = False
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.unsetCursor()
        QTimer.singleShot(250, self._clear_context_menu_suppression)

    def _clear_context_menu_suppression(self) -> None:
        self._suppress_context_menu = False

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(BOA_BLOCK_MIME):
            self._boa_drag_inside = True; event.acceptProposedAction(); return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(BOA_BLOCK_MIME): event.acceptProposedAction(); return
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event) -> None:
        if self._boa_drag_inside:
            self._boa_drag_inside = False; event.accept(); return
        event.accept()

    def dropEvent(self, event) -> None:
        if event.mimeData().hasFormat(BOA_BLOCK_MIME):
            self._boa_drag_inside = False
            key = bytes(event.mimeData().data(BOA_BLOCK_MIME)).decode("utf-8"); self.add_block_at(key, self.mapToScene(event.position().toPoint())); event.acceptProposedAction(); return
        self._boa_drag_inside = False; super().dropEvent(event)

    def wheelEvent(self, event) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15; self.scale(factor, factor); event.accept(); return
        super().wheelEvent(event)

    def open_loop_by_path(self, path: list[str]) -> None:
        if open_loop_path(self, path): self.instances_changed.emit()


    def focus_program_start(self) -> None:
        preferred = ("run", "function_start")
        block = next((item for key in preferred for item in self._all_blocks() if item.block_key == key), None)
        if block is None:
            block = min(self._all_blocks(), key=lambda item: (item.pos().x(), item.pos().y()), default=None)
        if block is not None:
            self.centerOn(block)

    def _add_decorator_to_marker(self, marker: BlockItem) -> None:
        block = self._new_block("decorator")
        self.scene.addItem(block)
        block.set_attached(marker.uid, len(attached_decorators(self, marker.uid)))
        reflow_target(self, marker.uid)
        self._select_items([block])
        self._changed()

    def _known_call_roots(self) -> set[str]:
        names = {str(name) for name in self.variable_names_provider() if str(name)}
        for block in self._all_blocks():
            key = str(block.block_key)
            if key in {"assign", "variable"}:
                target = str(getattr(block, "python_target", "") or getattr(block, "variable_name", ""))
                root = target.split(".", 1)[0]
                if root.isidentifier():
                    names.add(root)
            if key == "multi_assign":
                names.update(
                    str(target).lstrip("*") for target in getattr(block, "assign_targets", [])
                    if str(target).lstrip("*").isidentifier()
                )
            if key == "for":
                names.update(str(name) for name in getattr(block, "for_temp_outputs", []) if str(name).isidentifier())
            if key in DEF_PORT_KEYS:
                name = str(getattr(block, "def_port_name", ""))
                if name.isidentifier():
                    names.add(name)
        return names

    def _new_block(self, block_key: str) -> BlockItem:
        block = create_block(block_key); block.block_key = block_key
        if block_key in DEF_PORT_KEYS:
            group = INPUT_KEYS if block_key in INPUT_KEYS else OUTPUT_KEYS; base = "parametre" if block_key in INPUT_KEYS else "resultat"
            used = {getattr(item, "def_port_name", "") for item in self._all_blocks() if item.block_key in group}; index = 1; name = f"{base}_{index}"
            while name in used: index += 1; name = f"{base}_{index}"
            apply_def_port_config(block, name, "any", block_key == "def_input_p", "", "normal", block_key == "def_input_p")
        self._prepare_block(block); return block

    def _prepare_block(self, block: BlockItem) -> None:
        if not block.uid: block.uid = self._make_uid()
        if block.block_key in DEF_PORT_KEYS and not getattr(block, "def_port_id", ""): block.def_port_id = f"port_{uuid4().hex[:10]}"
        if block.block_key in {"for", "while"} and not getattr(block, "loop_instance_number", 0): block.loop_instance_number = self._next_loop_number(block.block_key)
        retranslate_block(block)
        if block.block_key in self.COMMENT_DISABLED_KEYS: block.comment = ""
        can_edit_protected = block.block_key in {"function_start", "function_return"}
        block.set_modifiable(block.block_key not in self.COMMENT_DISABLED_KEYS and (not getattr(block, "protected", False) or can_edit_protected))
        block.changed.connect(lambda current=block: self._block_changed(current))
        if isinstance(block, DecoratorBlockItem): prepare_decorator(self, block)
        if isinstance(block, SmartBlockItem):
            block.import_detected.connect(self.import_detected.emit); block.variable_detected.connect(self.variable_detected.emit); block.content_changed.connect(self.graph_changed.emit)

    def _make_uid(self) -> str:
        uid = f"b{self._next_uid}"; self._next_uid += 1; return uid

    def _block_from_data(self, data: dict) -> BlockItem:
        block = block_from_data(data)
        if block.block_key == "call" and getattr(block, "call_kind", "python") == "project":
            function = self.functions_provider().get(getattr(block, "function_id", ""))
            if function:
                apply_project_call(block, function, {"visible_inputs": getattr(block, "function_inputs", []), "visible_outputs": getattr(block, "function_outputs", [])})
            else: apply_missing_call(block)
        if not block.uid: block.uid = self._make_uid()
        self._next_uid = max(self._next_uid, uid_number(block.uid) + 1); self._prepare_block(block); return block

    def _add_tp_pair(self, pos: QPointF) -> None:
        number = next_tp_number(self._all_blocks()); pair_id = f"tp_pair_{self._next_uid}"
        left = create_tp_block("in", number, pair_id); right = create_tp_block("out", number, pair_id)
        self._prepare_block(left); self._prepare_block(right); left.setPos(pos); right.setPos(pos + QPointF(240, 0))
        self.scene.addItem(left); self.scene.addItem(right); self._select_items([left, right]); self._changed()

    def _add_prepared_block(self, block: BlockItem, pos: QPointF) -> None:
        if self.document_kind == "class" and not isinstance(block, DecoratorBlockItem):
            orders = [int(getattr(item, "class_order", -1)) for item in self._all_blocks() if int(getattr(item, "class_order", -1)) >= 0]
            block.class_order = max(orders, default=-1) + 1
        block.setPos(pos); self.scene.addItem(block); self._select_items([block]); self._changed()

    def _visible_insertion_position(self, width: float, height: float) -> QPointF:
        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        stagger = (self._view_insert_index % 6) * 24
        self._view_insert_index += 1
        x = visible.center().x() - width / 2 + stagger
        y = visible.center().y() - height / 2 + stagger
        margin = 24
        if visible.width() > width + margin * 2:
            x = min(max(x, visible.left() + margin), visible.right() - width - margin)
        if visible.height() > height + margin * 2:
            y = min(max(y, visible.top() + margin), visible.bottom() - height - margin)
        return QPointF(x, y)

    def _edit_for_block(self, block: BlockItem) -> None:
        old = list(getattr(block, "for_temp_outputs", [])); old_comment = block.comment
        names, comment, open_requested, accepted = edit_for_block(self, old, old_comment)
        if not accepted: return
        block.comment = comment; block.refresh_tooltip()
        if names != old: apply_for_outputs(block, names); self._refresh_connection_states()
        if names != old or comment != old_comment: self._changed()
        if open_requested: self._open_loop_instance(block, ["start"])

    def _edit_while_block(self, block: BlockItem) -> None:
        old_comment = block.comment
        comment, open_requested, accepted = edit_while_block(self, old_comment)
        if not accepted: return
        block.comment = comment; block.refresh_tooltip(); block.update()
        if comment != old_comment: self._changed()
        if open_requested: self._open_loop_instance(block, ["start", "end"])

    def _open_loop_instance(self, block: BlockItem, required: list[str]) -> None:
        def factory(parent):
            view = GraphView(parent); view.variable_names_provider = self.variable_names_provider; view.variable_entries_provider = self.variable_entries_provider
            view.loop_number_provider = self.loop_number_provider; view.functions_provider = self.functions_provider; view.function_open_callback = self.function_open_callback; view.class_open_callback = self.class_open_callback
            view.document_kind = "function_inner" if self.document_kind == "function" else "graph_inner"
            view.blocked_block_keys = {"run", "function_start", "function_return", "def_input", "def_input_p", "def_output", "def_output_p", "class_attribute"}
            view.instances_changed.connect(self.instances_changed.emit); return view
        def save_inner(data: dict) -> None:
            block.inner_graph = data; self._changed(); self.instances_changed.emit()
        data = open_instance_dialog(self, factory, f"Instance {block.title} #{getattr(block, 'loop_instance_number', '')}", getattr(block, "inner_graph", {}), required, self.variable_entries_provider, save_inner)
        if data is not None: save_inner(data)

    def refresh_function_calls(self) -> None:
        functions = self.functions_provider()
        for block in self._all_blocks():
            if block.block_key != "call" or getattr(block, "call_kind", "python") != "project": continue
            function = functions.get(getattr(block, "function_id", ""))
            if function:
                apply_project_call(block, function, {"visible_inputs": getattr(block, "function_inputs", []), "visible_outputs": getattr(block, "function_outputs", [])})
                self._drop_invalid_connections(block)
            else:
                apply_missing_call(block); self._drop_invalid_connections(block)
        self._refresh_connection_states()

    def _refresh_connection_states(self) -> None:
        refresh_tp_types(self._all_blocks(), self._all_connections()); refresh_connection_statuses(self._all_connections())

    def _changed(self) -> None:
        self._ensure_scene_bounds()
        self._refresh_connection_states(); self.graph_changed.emit(); self.instances_changed.emit()

    def _block_changed(self, block: BlockItem) -> None:
        if isinstance(block, DecoratorBlockItem) or block.block_key in {"def_marker", "class_marker"}:
            handle_block_moved(self, block)
        if self.document_kind == "class" and not isinstance(block, DecoratorBlockItem):
            self._reflow_class_columns()
        self._changed()

    def _reflow_class_columns(self) -> None:
        blocks = [
            block for block in self._all_blocks()
            if not isinstance(block, DecoratorBlockItem) and int(getattr(block, "class_order", -1)) >= 0
        ]
        blocks.sort(key=lambda item: (item.pos().x(), item.pos().y(), item.uid))
        for index, block in enumerate(blocks):
            block.class_order = index
            block.setPos(index * self.scene.CLASS_COLUMN_WIDTH + 44, max(48, block.pos().y()))
        self.scene.set_class_columns(max(1, len(blocks) + 1))
        reflow_all(self)

    def _ensure_scene_bounds(self) -> None:
        rect = self.scene.itemsBoundingRect()
        if rect.isNull(): rect = QRectF(-800, -500, 1600, 1000)
        rect = rect.adjusted(-420, -320, 520, 320)
        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        self.scene.setSceneRect(rect.united(visible.adjusted(-200, -200, 200, 200)))

    def _next_loop_number(self, key: str) -> int:
        try: return int(self.loop_number_provider(key))
        except Exception: return self._local_next_loop_number(key)

    def _local_next_loop_number(self, key: str) -> int:
        used = [int(getattr(b, "loop_instance_number", 0) or 0) for b in self._all_blocks() if b.block_key == key]
        return max(used, default=0) + 1

    def _selected_blocks(self) -> list[BlockItem]: return [item for item in self.scene.selectedItems() if isinstance(item, BlockItem)]
    def _all_blocks(self) -> list[BlockItem]: return sorted([item for item in self.scene.items() if isinstance(item, BlockItem)], key=lambda b: uid_number(b.uid))
    def _all_connections(self) -> list[ConnectionItem]: return [item for item in self.scene.items() if isinstance(item, ConnectionItem)]

    def _select_items(self, items: list) -> None:
        self.scene.clearSelection(); [item.setSelected(True) for item in items]

    def _start_connection(self, source: BlockItem, source_port: str) -> None:
        self.scene.clearSelection(); self._connection_source = source; self._connection_source_port = source_port
        self._temporary_connection = TemporaryConnectionItem(source.port_scene_pos(source_port)); self.scene.addItem(self._temporary_connection)

    def _finish_connection(self, target_hit: tuple[BlockItem, str] | None) -> None:
        source = self._connection_source; source_port = self._connection_source_port
        if self._temporary_connection: self.scene.removeItem(self._temporary_connection)
        self._temporary_connection = None; self._connection_source = None; self._connection_source_port = ""
        if not source or not target_hit: return
        target, target_port = target_hit; connection = ConnectionItem(source, target, source_port, target_port)
        self.scene.addItem(connection); ensure_after_connection(self, target, target_port); self._refresh_connection_states(); connection.setSelected(True); self._changed()

    def _block_at_port(self, scene_pos: QPointF, kind: str) -> tuple[BlockItem, str] | None:
        radius = BlockItem.PORT_HIT_RADIUS
        hit_rect = QRectF(scene_pos.x() - radius, scene_pos.y() - radius, radius * 2, radius * 2)
        for item in self.scene.items(hit_rect, Qt.ItemSelectionMode.IntersectsItemShape):
            if isinstance(item, BlockItem):
                port_key = item.port_at_scene_pos(scene_pos, kind)
                if port_key: return item, port_key
        return None

    def _valid_port(self, block: BlockItem, port_key: str | None, kind: str) -> str:
        port = block.port_definition(str(port_key or "")); return port.key if port and port.kind == kind else block._default_port_key(kind)

    def _show_delete_menu(self, event, item, label: str) -> None:
        menu = QMenu(self); delete_action = menu.addAction(label)
        if menu.exec(event.globalPos()) == delete_action:
            removed = self._remove_connection(item) if isinstance(item, ConnectionItem) else self._remove_block(item)
            if removed is not False: self._changed()

    def _remove_connection(self, connection: ConnectionItem) -> bool:
        target = connection.target_block
        connection.detach(); self.scene.removeItem(connection)
        trim_after_removal(self, target)
        self._refresh_connection_states(); return True

    def _remove_block(self, block: BlockItem) -> bool:
        if getattr(block, "protected", False): return False
        if block.block_key in DEF_PORT_KEYS and QMessageBox.question(
            self, tr("function.port.connected_title"), tr("function.port.delete_confirm", name=getattr(block, "def_port_name", "valeur"))
        ) != QMessageBox.StandardButton.Yes: return False
        target = str(getattr(block, "decorator_target", ""))
        if block.block_key in {"def_marker", "class_marker"}: detach_target(self, block.uid)
        for connection in list(block.connections): self._remove_connection(connection)
        self.scene.removeItem(block)
        if target: reflow_target(self, target)
        self._ensure_scene_bounds()
        return True

    def _drop_python_data_connections(self, block: BlockItem) -> None:
        for connection in list(block.connections):
            if connection.source_block is block and connection.source_port != "done":
                self._remove_connection(connection)
            elif connection.target_block is block and connection.target_port != "start":
                self._remove_connection(connection)

    def _drop_invalid_connections(self, block: BlockItem) -> None:
        valid_inputs = {port.key for port in block.ports if port.kind == "input"}
        valid_outputs = {port.key for port in block.ports if port.kind == "output"}
        for connection in list(block.connections):
            invalid = (connection.target_block is block and connection.target_port not in valid_inputs) or (connection.source_block is block and connection.source_port not in valid_outputs)
            if invalid:
                self._remove_connection(connection)

    def _connection_to_data(self, connection: ConnectionItem) -> dict:
        return {"source": connection.source_block.uid, "target": connection.target_block.uid, "source_port": connection.source_port, "target_port": connection.target_port}
