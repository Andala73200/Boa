from boa.blocks.base_block import BlockItem
from boa.core.graph_clone import clone_graph_fragment
from boa.ui.block_titles import retranslate_block
from boa.ui.connection_item import ConnectionItem
from boa.ui.graph_block_data import block_to_data
from boa.ui.variable_block_sync import rename_variable_blocks, update_variable_blocks


class GraphViewStateMixin:
    def copy_selected_blocks(self) -> int:
        blocks = self._selected_blocks()
        copied = [block_to_data(block) for block in blocks if not getattr(block, "protected", False)]
        ids = {str(block.get("id", "")) for block in copied}
        connections = [
            self._connection_to_data(item) for item in self._all_connections()
            if item.source_block.uid in ids and item.target_block.uid in ids
        ]
        self._clipboard_fragment = {"blocks": copied, "connections": connections}
        return len(copied)

    def cut_selected_blocks(self) -> int:
        count = self.copy_selected_blocks()
        if count:
            self.delete_selected_items()
        return count

    def paste_blocks(self) -> int:
        if not self._clipboard_fragment.get("blocks"):
            return 0
        fragment = clone_graph_fragment(self._clipboard_fragment)
        pasted = []
        blocks_by_id = {}
        for data in fragment["blocks"]:
            block = self._block_from_data(data); self.scene.addItem(block); pasted.append(block)
            blocks_by_id[block.uid] = block
        for connection in fragment["connections"]:
            source = blocks_by_id.get(connection.get("source")); target = blocks_by_id.get(connection.get("target"))
            if not source or not target:
                continue
            source_port = self._valid_port(source, connection.get("source_port"), "output")
            target_port = self._valid_port(target, connection.get("target_port"), "input")
            if source_port and target_port:
                self.scene.addItem(ConnectionItem(source, target, source_port, target_port))
        self._clipboard_fragment = {
            "blocks": [block_to_data(block) for block in pasted],
            "connections": [
                self._connection_to_data(item) for item in self._all_connections()
                if item.source_block in pasted and item.target_block in pasted
            ],
        }
        from boa.ui.decorator_stack import reflow_all
        reflow_all(self)
        self._select_items(pasted); self._changed()
        return len(pasted)

    def select_all_blocks(self) -> int:
        blocks = self._all_blocks(); self._select_items(blocks)
        return len(blocks)

    def delete_selected_items(self) -> int:
        selected = list(self.scene.selectedItems()); count = 0
        for item in selected:
            if isinstance(item, ConnectionItem):
                self._remove_connection(item); count += 1
        for block in [item for item in selected if isinstance(item, BlockItem)]:
            count += 1 if self._remove_block(block) else 0
        if count:
            self._changed()
        return count

    def to_data(self) -> dict:
        return {
            "blocks": [block_to_data(block) for block in self._all_blocks()],
            "connections": [self._connection_to_data(item) for item in self._all_connections()],
            "class_columns": int(getattr(self.scene, "_class_columns", 1)),
        }

    def from_data(self, data: dict) -> None:
        self.scene.clear(); self._connection_source = None; self._temporary_connection = None
        self._next_uid = 1; self._view_insert_index = 0; blocks_by_id = {}
        for block_data in data.get("blocks", []):
            block = self._block_from_data(block_data); self.scene.addItem(block); blocks_by_id[block.uid] = block
        for connection in data.get("connections", []):
            source = blocks_by_id.get(connection.get("source")); target = blocks_by_id.get(connection.get("target"))
            if source and target:
                source_port = self._valid_port(source, connection.get("source_port"), "output")
                target_port = self._valid_port(target, connection.get("target_port"), "input")
                if source_port and target_port:
                    self.scene.addItem(ConnectionItem(source, target, source_port, target_port))
        self.scene.set_class_columns(int(data.get("class_columns", 1) or 1))
        from boa.ui.decorator_stack import reflow_all
        reflow_all(self)
        if self.document_kind == "class": self._reflow_class_columns()
        self._ensure_scene_bounds(); self._refresh_connection_states(); self.scene.clearSelection()

    def position_run_for_new_project(self) -> bool:
        run = next((block for block in self._all_blocks() if block.block_key == "run"), None)
        if run is None:
            return False
        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        run.setPos(visible.left() + 24, visible.center().y() - run.HEIGHT / 2); run._update_connections()
        return True

    def refresh_tooltips(self) -> None:
        for block in self._all_blocks():
            retranslate_block(block); block.refresh_tooltip()
        for connection in self._all_connections():
            connection.refresh_tooltip()

    def rename_variable_blocks(self, old_name: str, new_name: str) -> None:
        if rename_variable_blocks(self._all_blocks(), old_name, new_name):
            self._changed()

    def update_variable_blocks(self, name: str, value_type: str, is_constant: bool) -> None:
        if update_variable_blocks(self._all_blocks(), name, value_type, is_constant):
            self._refresh_connection_states(); self._changed()
