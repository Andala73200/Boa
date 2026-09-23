from __future__ import annotations

from boa.blocks.block_factory import apply_call_config
from boa.blocks.python_native_blocks import apply_set_item_count
from boa.functions.blocks import apply_project_call


def ensure_after_connection(view, block, target_port: str) -> None:
    if block.block_key == "set_literal":
        _ensure_set(view, block, target_port)
        return
    if block.block_key != "call":
        return
    if "__arg_" in target_port or target_port.startswith("vararg_"):
        _ensure_vararg(view, block, target_port)
    if "__kwarg_" in target_port or target_port.startswith("kwarg_"):
        _ensure_kwarg(view, block, target_port)


def trim_after_removal(view, block) -> None:
    if block.block_key == "set_literal":
        count = _used_count(view, block, "element_", minimum=1)
        apply_set_item_count(block, count)
        view._drop_invalid_connections(block)
        return
    if block.block_key != "call":
        return
    if getattr(block, "call_kind", "python") == "project":
        function = view.functions_provider().get(getattr(block, "function_id", ""))
        if not function:
            return
        arg_port = str(getattr(block, "function_vararg_port", ""))
        kwarg_port = str(getattr(block, "function_kwarg_port", ""))
        if arg_port:
            block.call_vararg_count = _used_count(view, block, f"{arg_port}__arg_", minimum=1)
        if kwarg_port:
            count = _used_count(view, block, f"{kwarg_port}__kwarg_", minimum=1)
            block.call_kwarg_names = _resize_names(list(getattr(block, "call_kwarg_names", [])), count)
        apply_project_call(block, function, _project_config(block))
    else:
        if int(getattr(block, "call_vararg_count", 0) or 0):
            block.call_vararg_count = _used_count(view, block, "vararg_", minimum=1)
        if list(getattr(block, "call_kwarg_names", [])):
            count = _used_count(view, block, "kwarg_", minimum=1)
            block.call_kwarg_names = _resize_names(list(block.call_kwarg_names), count)
        _apply_python(block)
    view._drop_invalid_connections(block)


def _ensure_set(view, block, target_port: str) -> None:
    count = int(getattr(block, "set_item_count", 1) or 1)
    if target_port != f"element_{count}":
        return
    apply_set_item_count(block, count + 1)
    view._drop_invalid_connections(block)


def _ensure_vararg(view, block, target_port: str) -> None:
    count = int(getattr(block, "call_vararg_count", 0) or 0)
    if count <= 0 or not target_port.endswith(f"_{count}"):
        return
    block.call_vararg_count = count + 1
    _rebuild(view, block)


def _ensure_kwarg(view, block, target_port: str) -> None:
    names = list(getattr(block, "call_kwarg_names", []))
    if not names or not target_port.endswith(f"_{len(names)}"):
        return
    names.append(f"kwarg_{len(names) + 1}")
    block.call_kwarg_names = names
    _rebuild(view, block)


def _rebuild(view, block) -> None:
    if getattr(block, "call_kind", "python") == "project":
        function = view.functions_provider().get(getattr(block, "function_id", ""))
        if function:
            apply_project_call(block, function, _project_config(block))
    else:
        _apply_python(block)


def _apply_python(block) -> None:
    apply_call_config(
        block,
        str(getattr(block, "call_target", "fonction")),
        int(getattr(block, "call_arg_count", 0) or 0),
        str(getattr(block, "call_result_type", "any")),
        int(getattr(block, "call_vararg_count", 0) or 0),
        list(getattr(block, "call_kwarg_names", [])),
        list(getattr(block, "call_arg_labels", [])),
    )


def _project_config(block) -> dict:
    return {
        "visible_inputs": list(getattr(block, "function_inputs", [])),
        "visible_outputs": list(getattr(block, "function_outputs", [])),
    }


def _used_count(view, block, prefix: str, minimum: int) -> int:
    used = []
    for connection in view._all_connections():
        if connection.target_block is block and connection.target_port.startswith(prefix):
            try:
                used.append(int(connection.target_port.rsplit("_", 1)[1]))
            except ValueError:
                pass
    return max(minimum, max(used, default=0) + 1)


def _resize_names(names: list[str], count: int) -> list[str]:
    result = [str(name).strip() or f"kwarg_{index + 1}" for index, name in enumerate(names[:count])]
    while len(result) < count:
        result.append(f"kwarg_{len(result) + 1}")
    return result
