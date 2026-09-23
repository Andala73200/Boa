from boa.runtime.loop_registry import find_block_data
from boa.ui.loop_dialogs import open_instance_dialog


def open_loop_path(root_view, path: list[str]) -> bool:
    if not path:
        return False
    top = _block_by_uid(root_view, path[0])
    if top is None:
        return False
    if len(path) == 1:
        root_view._open_loop_instance(top, _required(top.block_key))
        return True
    container = getattr(top, "inner_graph", {}) or {}
    target = find_block_data(container, path[1:])
    if target is None or target.get("key") not in {"while", "for"}:
        return False
    _open_nested(root_view, top, container, target)
    return True


def _open_nested(root_view, top_block, container_graph: dict, target_data: dict) -> None:
    key = target_data.get("key", "while")
    number = int(target_data.get("loop_instance_number", 0) or 0)

    def factory(parent):
        view = root_view.__class__(parent)
        view.variable_names_provider = root_view.variable_names_provider
        view.variable_entries_provider = root_view.variable_entries_provider
        view.loop_number_provider = root_view.loop_number_provider
        view.instances_changed.connect(root_view.instances_changed.emit)
        return view

    def save_inner(data: dict) -> None:
        target_data["inner_graph"] = data
        top_block.inner_graph = container_graph
        root_view._changed()
        root_view.instances_changed.emit()

    title = f"Instance {key} #{number}"
    data = open_instance_dialog(root_view, factory, title, target_data.get("inner_graph", {}) or {}, _required(key), root_view.variable_entries_provider, save_inner)
    if data is not None:
        save_inner(data)


def _required(key: str) -> list[str]:
    return ["start", "end"] if key == "while" else ["start"]


def _block_by_uid(view, uid: str):
    return next((block for block in view._all_blocks() if block.uid == uid), None)
