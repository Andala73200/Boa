from __future__ import annotations

from pathlib import PurePosixPath
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyle, QTreeWidgetItem, QWidget

from boa.core.project_tree_data import CLASSES_FOLDER_ID, FILES_FOLDER_ID, FUNCTIONS_FOLDER_ID
from boa.i18n import tr

ROLE_KIND = Qt.ItemDataRole.UserRole
ROLE_ID = Qt.ItemDataRole.UserRole + 1
ROLE_PROTECTED = Qt.ItemDataRole.UserRole + 2
ROOT_KIND = "root"
FOLDER_KIND = "folder"
SCRIPT_KIND = "script"
GRAPH_KIND = "graph"
FUNCTION_KIND = "function"
CLASS_KIND = "class"


def section(item: QTreeWidgetItem) -> str:
    if item_id(item) == FILES_FOLDER_ID or under_folder(item, FILES_FOLDER_ID):
        return "files"
    if item_id(item) == FUNCTIONS_FOLDER_ID or under_folder(item, FUNCTIONS_FOLDER_ID):
        return "functions"
    if item_id(item) == CLASSES_FOLDER_ID or under_folder(item, CLASSES_FOLDER_ID):
        return "classes"
    return "root"


def make_item(text: str, kind: str, uid: str, protected: bool = False) -> QTreeWidgetItem:
    item = QTreeWidgetItem([text])
    item.setData(0, ROLE_KIND, kind)
    item.setData(0, ROLE_ID, uid)
    item.setData(0, ROLE_PROTECTED, protected)
    flags = item.flags() | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
    if not protected and kind != ROOT_KIND:
        flags |= Qt.ItemFlag.ItemIsEditable
        if kind not in {FUNCTION_KIND, CLASS_KIND}:
            flags |= Qt.ItemFlag.ItemIsDragEnabled
    if kind in {ROOT_KIND, FOLDER_KIND}:
        flags |= Qt.ItemFlag.ItemIsDropEnabled
    item.setFlags(flags)
    return item


def decorate_item(owner: QWidget, item: QTreeWidgetItem) -> None:
    standard = {
        FOLDER_KIND: QStyle.StandardPixmap.SP_DirIcon,
        SCRIPT_KIND: QStyle.StandardPixmap.SP_FileIcon,
        GRAPH_KIND: QStyle.StandardPixmap.SP_DriveHDIcon,
        FUNCTION_KIND: QStyle.StandardPixmap.SP_FileIcon,
        CLASS_KIND: QStyle.StandardPixmap.SP_ComputerIcon,
    }.get(kind_of(item))
    if standard is not None:
        item.setIcon(0, owner.style().standardIcon(standard))
    tips = {SCRIPT_KIND: "Python", GRAPH_KIND: "Graphe Boa", FUNCTION_KIND: "DEF", CLASS_KIND: "Classe"}
    if kind_of(item) in tips:
        item.setToolTip(0, tips[kind_of(item)])


def kind_of(item: QTreeWidgetItem) -> str:
    return str(item.data(0, ROLE_KIND) or FOLDER_KIND)


def item_id(item: QTreeWidgetItem) -> str:
    return str(item.data(0, ROLE_ID) or "")


def is_protected(item: QTreeWidgetItem) -> bool:
    return bool(item.data(0, ROLE_PROTECTED))


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def py_name(name: str) -> str:
    return name if name.lower().endswith(".py") else f"{name}.py"


def boa_name(name: str) -> str:
    return name if name.lower().endswith(".boa") else f"{name}.boa"


def normalized_name(name: str, kind: str) -> str:
    if not valid_item_name(name):
        return ""
    if kind == SCRIPT_KIND:
        return py_name(name)
    if kind == GRAPH_KIND:
        return boa_name(name)
    if kind in {FUNCTION_KIND, CLASS_KIND}:
        return name if valid_python_name(name) else ""
    return name


def valid_item_name(name: str) -> bool:
    return bool(name and name not in {".", ".."} and not any(char in name for char in "/\\\0"))


def valid_python_name(name: str) -> bool:
    import keyword
    return name.isidentifier() and not keyword.iskeyword(name)


def child_name_exists(parent: QTreeWidgetItem, name: str) -> bool:
    wanted = name.casefold()
    return any(parent.child(index).text(0).casefold() == wanted for index in range(parent.childCount()))


def sibling_name_exists(item: QTreeWidgetItem, name: str) -> bool:
    parent = item.parent() or item.treeWidget().invisibleRootItem()
    wanted = name.casefold()
    return any(
        parent.child(index) is not item and parent.child(index).text(0).casefold() == wanted
        for index in range(parent.childCount())
    )


def item_to_data(item: QTreeWidgetItem) -> dict:
    return {
        "name": item.text(0), "kind": kind_of(item), "id": item_id(item), "protected": is_protected(item),
        "children": [item_to_data(item.child(index)) for index in range(item.childCount())],
    }


def item_from_data(data: dict) -> QTreeWidgetItem:
    item = make_item(
        str(data.get("name", tr("project.root"))), str(data.get("kind", ROOT_KIND)),
        str(data.get("id", new_id("item"))), bool(data.get("protected", False)),
    )
    for child_data in data.get("children", []):
        item.addChild(item_from_data(child_data))
    item.setExpanded(True)
    return item


def find_item(item: QTreeWidgetItem | None, uid: str) -> QTreeWidgetItem | None:
    if item is None:
        return None
    if item_id(item) == uid:
        return item
    for index in range(item.childCount()):
        found = find_item(item.child(index), uid)
        if found:
            return found
    return None


def under_folder(item: QTreeWidgetItem, folder_id: str) -> bool:
    current = item
    while current is not None:
        if item_id(current) == folder_id:
            return True
        current = current.parent()
    return False


def sort_children(parent: QTreeWidgetItem) -> None:
    children = [parent.takeChild(0) for _ in range(parent.childCount())]
    for child in children:
        if kind_of(child) == FOLDER_KIND:
            sort_children(child)
    children.sort(key=_sort_key)
    parent.addChildren(children)


def _sort_key(item: QTreeWidgetItem) -> tuple:
    name, kind = item.text(0), kind_of(item)
    if kind == FOLDER_KIND:
        return (0, name.casefold(), 0, name.casefold())
    path = PurePosixPath(name)
    return (1, path.stem.casefold(), {SCRIPT_KIND: 0, GRAPH_KIND: 1}.get(kind, 2), name.casefold())


def default_tree_data() -> dict:
    return {
        "name": tr("project.root"), "kind": ROOT_KIND, "id": "root", "protected": True,
        "children": [
            {"name": tr("project.files"), "kind": FOLDER_KIND, "id": FILES_FOLDER_ID, "protected": True, "children": [
                {"name": "main.boa", "kind": GRAPH_KIND, "id": "main", "protected": False, "children": []},
            ]},
            {"name": tr("project.functions"), "kind": FOLDER_KIND, "id": FUNCTIONS_FOLDER_ID, "protected": True, "children": []},
            {"name": tr("project.classes"), "kind": FOLDER_KIND, "id": CLASSES_FOLDER_ID, "protected": True, "children": []},
        ],
    }
