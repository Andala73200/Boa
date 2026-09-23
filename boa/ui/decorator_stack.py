from __future__ import annotations

from PySide6.QtCore import QPointF

from boa.blocks.definition_blocks import DecoratorBlockItem


STACK_GAP = 28
SNAP_X = 120
SNAP_Y = 28
TARGET_KEYS = {"def_marker", "class_marker"}


def prepare_decorator(view, block: DecoratorBlockItem) -> None:
    block.toggle_stack_callback = lambda current: reflow_target(view, current.decorator_target)
    block.setZValue(1000)


def handle_block_moved(view, block) -> None:
    if isinstance(block, DecoratorBlockItem):
        old_target = str(block.decorator_target)
        block.set_attached("", 0)
        if old_target:
            reflow_target(view, old_target, excluded=block.uid)
        target, order = _find_target(view, block)
        if target:
            _insert(view, block, target, order)
        else:
            block.show()
        return
    if block.block_key in TARGET_KEYS:
        reflow_target(view, block.uid)


def detach_target(view, target_uid: str) -> None:
    for decorator in attached_decorators(view, target_uid):
        decorator.set_attached("", 0)
        decorator.show()


def reflow_all(view) -> None:
    for block in view._all_blocks():
        if isinstance(block, DecoratorBlockItem):
            prepare_decorator(view, block)
    targets = {str(block.decorator_target) for block in view._all_blocks() if isinstance(block, DecoratorBlockItem) and block.decorator_target}
    for target in targets:
        reflow_target(view, target)


def reflow_target(view, target_uid: str, excluded: str = "") -> None:
    if not target_uid:
        return
    target = next((item for item in view._all_blocks() if item.uid == target_uid and item.block_key in TARGET_KEYS), None)
    decorators = [item for item in attached_decorators(view, target_uid) if item.uid != excluded]
    if target is None:
        for decorator in decorators:
            decorator.set_attached("", 0)
            decorator.show()
        return
    decorators.sort(key=lambda item: (int(item.decorator_order), item.uid))
    for index, decorator in enumerate(decorators):
        decorator.set_attached(target_uid, index)
        decorator.stack_count = len(decorators) if index == 0 else 1
        decorator.stack_collapsed = bool(decorators[0].stack_collapsed) if decorators else False
    collapsed = bool(decorators and decorators[0].stack_collapsed and len(decorators) > 1)
    if collapsed:
        summary = decorators[0]
        summary.setPos(target.pos() + QPointF((target.WIDTH - summary.WIDTH) / 2, -STACK_GAP))
        summary.setZValue(1000 + len(decorators))
        summary.show()
        for decorator in decorators[1:]:
            decorator.hide()
        return
    for index, decorator in enumerate(decorators):
        y = -STACK_GAP * (len(decorators) - index)
        decorator.setPos(target.pos() + QPointF((target.WIDTH - decorator.WIDTH) / 2, y))
        decorator.setZValue(1000 + len(decorators) - index)
        decorator.show()
        decorator._update_connections()


def attached_decorators(view, target_uid: str) -> list[DecoratorBlockItem]:
    return [
        block for block in view._all_blocks()
        if isinstance(block, DecoratorBlockItem) and str(block.decorator_target) == str(target_uid)
    ]


def _find_target(view, moving: DecoratorBlockItem) -> tuple[str, int]:
    candidates = [block for block in view._all_blocks() if block.block_key in TARGET_KEYS]
    best: tuple[float, str, int] | None = None
    center = moving.pos() + QPointF(moving.WIDTH / 2, moving.HEIGHT / 2)
    moving_top = moving.pos().y()
    for marker in candidates:
        marker_center_x = marker.pos().x() + marker.WIDTH / 2
        if abs(center.x() - marker_center_x) > SNAP_X:
            continue
        stack = [item for item in attached_decorators(view, marker.uid) if item is not moving]
        stack.sort(key=lambda item: item.decorator_order)
        top_y = marker.pos().y() - STACK_GAP * (len(stack) + 1)
        bottom_y = marker.pos().y()
        if not (top_y - SNAP_Y <= moving_top <= bottom_y + SNAP_Y):
            continue
        slots = [marker.pos().y() - STACK_GAP * (len(stack) - index + 1) for index in range(len(stack) + 1)]
        order = min(range(len(slots)), key=lambda index: abs(moving_top - slots[index]))
        distance = abs(center.x() - marker_center_x) + abs(moving_top - slots[order])
        if best is None or distance < best[0]:
            best = (distance, marker.uid, order)
    return (best[1], best[2]) if best else ("", 0)


def _insert(view, moving: DecoratorBlockItem, target_uid: str, order: int) -> None:
    stack = [item for item in attached_decorators(view, target_uid) if item is not moving]
    stack.sort(key=lambda item: item.decorator_order)
    order = max(0, min(order, len(stack)))
    stack.insert(order, moving)
    for index, decorator in enumerate(stack):
        decorator.set_attached(target_uid, index)
    reflow_target(view, target_uid)
