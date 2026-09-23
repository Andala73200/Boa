from __future__ import annotations

from PySide6.QtGui import QColor

from boa.blocks.base_block import BlockItem, PortDefinition
from boa.i18n import tr


COLORS = {
    "attribute": QColor("#455a64"),
    "return": QColor("#6a1b9a"),
    "try": QColor("#c47f00"),
    "match": QColor("#c62828"),
    "with": QColor("#00897b"),
    "multi": QColor("#455a64"),
    "await": QColor("#3949ab"),
    "set": QColor("#5d4037"),
}


def create_attribute_get_block(name: str = "attribut") -> BlockItem:
    ports = [
        PortDefinition("object", "objet", "input", "any", "left", 34),
        PortDefinition("value", "valeur", "output", "any", "right", 34),
    ]
    block = BlockItem(tr("block.attribute_get.title"), name, COLORS["attribute"], ports, 190, 68)
    block.block_key = "attribute_get"
    block.attribute_name = name
    block.modifiable = True
    return block


def create_class_attribute_block(name: str = "attribut", annotation: str = "", has_default: bool = False) -> BlockItem:
    ports = _class_attribute_ports(bool(has_default))
    subtitle = _attribute_subtitle(name, annotation, has_default)
    block = BlockItem(tr("block.class_attribute.title"), subtitle, COLORS["attribute"], ports, 205, 76 if has_default else 58)
    block.block_key = "class_attribute"
    block.attribute_name = name
    block.attribute_annotation = annotation
    block.attribute_has_default = bool(has_default)
    block.modifiable = True
    return block


def apply_class_attribute(block: BlockItem, name: str, annotation: str, has_default: bool) -> None:
    block.attribute_name = str(name).strip() or "attribut"
    block.attribute_annotation = str(annotation).strip()
    block.attribute_has_default = bool(has_default)
    block.subtitle = _attribute_subtitle(block.attribute_name, block.attribute_annotation, block.attribute_has_default)
    block.prepareGeometryChange()
    block.ports = _class_attribute_ports(block.attribute_has_default)
    block.HEIGHT = 76 if block.attribute_has_default else 58
    block.update()
    block._update_connections()


def create_return_block(values: list[str] | None = None, key: str = "return", protected: bool = False) -> BlockItem:
    labels = _clean_labels(values or [])
    block = BlockItem(tr("block.return.title"), "", COLORS["return"], _return_ports(labels), 175, _return_height(labels))
    block.block_key = key
    block.return_values = labels
    block.protected = bool(protected)
    block.modifiable = True
    return block


def apply_return_values(block: BlockItem, values: list[str]) -> None:
    labels = _clean_labels(values)
    block.prepareGeometryChange()
    block.return_values = labels
    block.ports = _return_ports(labels)
    block.HEIGHT = _return_height(labels)
    block.subtitle = "" if not labels else f"retour({', '.join(labels)})"
    block.update()
    block._update_connections()


def create_multi_assign_block(targets: list[str] | None = None) -> BlockItem:
    values = _clean_targets(targets or ["valeur_1", "valeur_2"])
    block = BlockItem(tr("block.multi_assign.title"), ", ".join(values), COLORS["multi"], _multi_ports(values), 235, _multi_height(values))
    block.block_key = "multi_assign"
    block.assign_targets = values
    block.modifiable = True
    return block


def apply_multi_assign(block: BlockItem, targets: list[str]) -> None:
    values = _clean_targets(targets)
    block.prepareGeometryChange()
    block.assign_targets = values
    block.subtitle = ", ".join(values)
    block.ports = _multi_ports(values)
    block.HEIGHT = _multi_height(values)
    block.update()
    block._update_connections()


def create_try_block(handlers: list[dict] | None = None, has_else: bool = False, has_finally: bool = False) -> BlockItem:
    entries = list(handlers or [])
    block = BlockItem(tr("block.try.title"), "", COLORS["try"], _try_ports(entries, has_else, has_finally), 245, _branch_height(2 + len(entries) + int(has_else) + int(has_finally)))
    block.block_key = "try"
    block.try_graph = {}
    block.try_handlers = entries
    block.try_else_graph = {} if has_else else {}
    block.try_finally_graph = {} if has_finally else {}
    block.modifiable = True
    return block


def create_match_block(cases: list[dict] | None = None) -> BlockItem:
    entries = list(cases or [])
    block = BlockItem(tr("block.match.title"), "", COLORS["match"], _match_ports(entries), 235, _branch_height(2 + len(entries)))
    block.block_key = "match"
    block.match_cases = entries
    block.modifiable = True
    return block


def create_with_block(items: list[dict] | None = None, is_async: bool = False) -> BlockItem:
    entries = list(items or [{"alias": ""}])
    block = BlockItem(tr("block.with.title"), "async" if is_async else "", COLORS["with"], _with_ports(entries), 235, _branch_height(2 + len(entries)))
    block.block_key = "with"
    block.with_items = entries
    block.with_graph = {}
    block.with_async = bool(is_async)
    block.modifiable = True
    return block



def create_await_block(flow: bool = False) -> BlockItem:
    block = BlockItem(tr("block.await.title"), "", COLORS["await"], _await_ports(bool(flow)), 205, 76 if flow else 62)
    block.block_key = "await"
    block.await_flow = bool(flow)
    return block


def apply_await_flow(block: BlockItem, flow: bool) -> None:
    block.prepareGeometryChange()
    block.await_flow = bool(flow)
    block.ports = _await_ports(block.await_flow)
    block.HEIGHT = 76 if block.await_flow else 62
    block.update()
    block._update_connections()


def create_set_literal_block(item_count: int = 1) -> BlockItem:
    count = max(1, int(item_count or 1))
    block = BlockItem(tr("block.set_literal.title"), "", COLORS["set"], _set_ports(count), 205, _set_height(count))
    block.block_key = "set_literal"
    block.set_item_count = count
    return block


def apply_set_item_count(block: BlockItem, item_count: int) -> None:
    count = max(1, int(item_count or 1))
    block.prepareGeometryChange()
    block.set_item_count = count
    block.ports = _set_ports(count)
    block.HEIGHT = _set_height(count)
    block.update()
    block._update_connections()


def apply_try_config(block: BlockItem, handlers: list[dict], has_else: bool, has_finally: bool) -> None:
    entries = list(handlers)
    block.prepareGeometryChange()
    block.try_handlers = entries
    block.try_else_graph = (getattr(block, "try_else_graph", {}) or _empty_inner()) if has_else else {}
    block.try_finally_graph = (getattr(block, "try_finally_graph", {}) or _empty_inner()) if has_finally else {}
    block.ports = _try_ports(entries, has_else, has_finally)
    block.HEIGHT = _branch_height(2 + len(entries) + int(has_else) + int(has_finally))
    block.update()
    block._update_connections()


def apply_match_cases(block: BlockItem, cases: list[dict]) -> None:
    entries = list(cases)
    block.prepareGeometryChange()
    block.match_cases = entries
    block.ports = _match_ports(entries)
    block.HEIGHT = _branch_height(2 + len(entries))
    block.update()
    block._update_connections()


def apply_with_config(block: BlockItem, items: list[dict], is_async: bool) -> None:
    entries = list(items) or [{"alias": ""}]
    block.prepareGeometryChange()
    block.with_items = entries
    block.with_async = bool(is_async)
    block.subtitle = "async" if block.with_async else ""
    block.ports = _with_ports(entries)
    block.HEIGHT = _branch_height(2 + len(entries))
    block.update()
    block._update_connections()



def _await_ports(flow: bool) -> list[PortDefinition]:
    ports = [
        PortDefinition("awaitable", tr("block.await.port.awaitable"), "input", "any", "left", 40),
        PortDefinition("result", tr("block.await.port.result"), "output", "any", "right", 40),
    ]
    if flow:
        ports.insert(0, PortDefinition("start", "start", "input", "flow", "left", 18))
        ports.append(PortDefinition("done", tr("port.done"), "output", "flow", "right", 18))
    return ports


def _set_ports(count: int) -> list[PortDefinition]:
    ports = []
    for index in range(count):
        ports.append(PortDefinition(
            f"element_{index + 1}",
            tr("block.set_literal.element", index=index + 1),
            "input", "any", "left", 34 + index * 28,
        ))
    ports.append(PortDefinition("result", tr("block.set_literal.port.result"), "output", "set", "right", 34))
    return ports


def _set_height(count: int) -> int:
    return max(58, 48 + max(1, count) * 28)


def _class_attribute_ports(has_default: bool) -> list[PortDefinition]:
    ports = []
    if has_default:
        ports.append(PortDefinition("value", tr("block.class_attribute.port.value"), "input", "any", "left", 34))
    ports.append(PortDefinition("attribute", tr("block.class_attribute.port.attribute"), "output", "any", "right", 34))
    return ports


def _return_ports(labels: list[str]) -> list[PortDefinition]:
    ports = [PortDefinition("start", "start", "input", "flow", "left", 28)]
    for index, label in enumerate(labels):
        y = 60 + index * 28
        ports.append(PortDefinition(f"value_{index + 1}", label, "input", "any", "left", y))
        ports.append(PortDefinition(f"result_{index + 1}", label, "output", "any", "right", y))
    return ports


def _multi_ports(targets: list[str]) -> list[PortDefinition]:
    ports = [
        PortDefinition("start", "start", "input", "flow", "left", 26),
        PortDefinition("value", "valeur", "input", "any", "left", 58),
        PortDefinition("done", tr("port.done"), "output", "flow", "right", 26),
    ]
    for index, target in enumerate(targets):
        ports.append(PortDefinition(f"result_{index + 1}", target, "output", "any", "right", 58 + index * 28))
    return ports


def _try_ports(handlers: list[dict], has_else: bool, has_finally: bool) -> list[PortDefinition]:
    ports = [PortDefinition("start", "start", "input", "flow", "left", 28)]
    labels = [tr("block.try.branch.try")]
    labels += [f"except {item.get('type') or ''}".strip() for item in handlers]
    if has_else: labels.append(tr("block.try.branch.else"))
    if has_finally: labels.append(tr("block.try.branch.finally"))
    for index, label in enumerate(labels):
        ports.append(PortDefinition(f"branch_{index + 1}", label, "output", "flow", "right", 32 + index * 28))
    ports.append(PortDefinition("done", tr("port.done"), "output", "flow", "right", 32 + len(labels) * 28))
    return ports


def _match_ports(cases: list[dict]) -> list[PortDefinition]:
    ports = [
        PortDefinition("start", "start", "input", "flow", "left", 28),
        PortDefinition("value", tr("port.value"), "input", "any", "left", 60),
    ]
    for index, item in enumerate(cases):
        ports.append(PortDefinition(f"case_{index + 1}", match_case_label(item), "output", "flow", "right", 32 + index * 28))
    ports.append(PortDefinition("done", tr("port.done"), "output", "flow", "right", 32 + len(cases) * 28))
    return ports


def _with_ports(items: list[dict]) -> list[PortDefinition]:
    ports = [PortDefinition("start", "start", "input", "flow", "left", 28)]
    for index, item in enumerate(items):
        y = 60 + index * 28
        ports.append(PortDefinition(f"context_{index + 1}", tr("block.with.context", index=index + 1), "input", "any", "left", y))
        alias = str(item.get("alias", "")).strip()
        if alias:
            ports.append(PortDefinition(f"alias_{index + 1}", alias, "output", "any", "right", y))
    ports.append(PortDefinition("done", tr("port.done"), "output", "flow", "right", 60 + len(items) * 28))
    return ports


def match_case_label(item: dict) -> str:
    pattern = str(item.get("pattern", "_")).strip() or "_"
    guard = str(item.get("guard", "")).strip()
    if pattern == "_":
        return tr("block.match.case.default")
    label = tr("block.match.case.value", pattern=pattern)
    return tr("block.match.case.guard", label=label, guard=guard) if guard else label


def _attribute_subtitle(name: str, annotation: str, has_default: bool) -> str:
    value = str(name).strip() or "attribut"
    if annotation: value += f" : {annotation}"
    if has_default: value += " = …"
    return value


def _clean_labels(values: list[str]) -> list[str]:
    return [str(value).strip() or f"valeur_{index + 1}" for index, value in enumerate(values)]


def _clean_targets(values: list[str]) -> list[str]:
    result = [str(value).strip() for value in values if str(value).strip()]
    return result or ["valeur"]


def _empty_inner() -> dict: return {"blocks": [], "connections": []}
def _return_height(labels: list[str]) -> int: return max(58, 76 + max(0, len(labels) - 1) * 28)
def _multi_height(labels: list[str]) -> int: return max(84, 84 + max(0, len(labels) - 1) * 28)
def _branch_height(rows: int) -> int: return max(82, 44 + max(1, rows) * 28)
