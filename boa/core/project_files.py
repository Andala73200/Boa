from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path, PurePosixPath
from tokenize import detect_encoding

from boa.core.atomic_io import atomic_write_bytes
from boa.core.project_tree_data import FILES_FOLDER_ID, LEGACY_SCRIPTS_FOLDER_ID


def hydrate_scripts(project_file: str | Path, project: dict) -> dict:
    root = Path(project_file).resolve().parent
    paths = script_paths(project.get("tree", {}))
    for script_id, item in project.get("scripts", {}).items():
        relative = paths.get(script_id) or _stored_path(item)
        if relative is None:
            continue
        item["path"] = relative.as_posix()
        target = safe_script_path(root, relative)
        if target.is_file():
            _hydrate_item(target, item)
    return project


def sync_scripts(project_file: str | Path, project: dict) -> None:
    """Synchronize metadata only. Saving a graph must never rewrite Python."""
    paths = script_paths(project.get("tree", {}))
    for script_id, item in project.get("scripts", {}).items():
        relative = paths.get(script_id) or _stored_path(item)
        if relative is not None:
            item["path"] = relative.as_posix()


def script_paths(tree: dict) -> dict[str, Path]:
    scripts_root = _find_node(tree, FILES_FOLDER_ID) or _find_node(tree, LEGACY_SCRIPTS_FOLDER_ID)
    result: dict[str, Path] = {}
    if scripts_root:
        _collect_files(scripts_root, PurePosixPath(), result, "script", ".py")
    return result


def graph_paths(tree: dict) -> dict[str, Path]:
    files_root = _find_node(tree, FILES_FOLDER_ID)
    result: dict[str, Path] = {}
    if files_root:
        _collect_files(files_root, PurePosixPath(), result, "graph", ".boa")
    return result


def safe_script_path(root: Path, relative: str | Path) -> Path:
    return _safe_project_path(root, relative, ".py", "script")


def safe_graph_path(root: Path, relative: str | Path) -> Path:
    return _safe_project_path(root, relative, ".boa", "graphe")


def refresh_script_from_disk(project_file: str | Path, item: dict) -> bool:
    relative = _stored_path(item)
    if relative is None:
        return False
    target = safe_script_path(Path(project_file).resolve().parent, relative)
    if not target.is_file():
        return False
    _hydrate_item(target, item)
    return True


def read_script_file(path: str | Path) -> tuple[str, dict]:
    item: dict = {}
    _hydrate_item(Path(path), item)
    return str(item["content"]), item


def script_changed_on_disk(project_file: str | Path, item: dict) -> bool:
    relative = _stored_path(item)
    if relative is None:
        return False
    target = safe_script_path(Path(project_file).resolve().parent, relative)
    if not target.is_file():
        return False
    known_hash = str(item.get("content_hash", ""))
    if known_hash:
        return _digest(target.read_bytes()) != known_hash
    known_mtime = int(item.get("disk_mtime_ns", 0) or 0)
    return bool(known_mtime and target.stat().st_mtime_ns != known_mtime)


def write_script(project_file: str | Path, item: dict) -> Path:
    """Explicit script-editor save, preserving source encoding, BOM and newlines."""
    relative = _stored_path(item)
    if relative is None:
        raise ValueError("Le script ne possède pas de chemin valide.")
    target = safe_script_path(Path(project_file).resolve().parent, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    if item.get("content_hash") and not target.exists():
        raise RuntimeError(f"Le fichier {relative} a été supprimé en dehors de Boa.")
    if target.is_file() and item.get("content_hash") and script_changed_on_disk(project_file, item):
        raise RuntimeError(f"Le fichier {relative} a été modifié en dehors de Boa.")
    raw = script_bytes(item, relative)
    atomic_write_bytes(target, raw, backup=target.exists())
    _hydrate_item(target, item)
    return target


def script_bytes(item: dict, label: str | Path = "script.py") -> bytes:
    encoding = str(item.get("encoding") or "utf-8")
    newline = str(item.get("newline") or "\n")
    content = _with_newlines(str(item.get("content", "")), newline)
    try:
        return content.encode(encoding)
    except (LookupError, UnicodeEncodeError) as error:
        raise UnicodeError(f"Impossible d'enregistrer {label} en {encoding}: {error}") from error


def move_script(project_file: str | Path, item: dict, relative: Path) -> None:
    root = Path(project_file).resolve().parent
    old_relative = _stored_path(item)
    target = safe_script_path(root, relative)
    if old_relative and old_relative != relative:
        source = safe_script_path(root, old_relative)
        if source.exists():
            if target.exists():
                raise FileExistsError(str(target))
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
    item["path"] = relative.as_posix()
    if target.exists():
        _hydrate_item(target, item)


def move_graph(project_file: str | Path, item: dict, relative: Path) -> None:
    root = Path(project_file).resolve().parent
    project_path = Path(project_file).resolve()
    old_value = str(item.get("path", "")).strip()
    target = safe_graph_path(root, relative)
    if old_value:
        source = safe_graph_path(root, old_value)
        if source != target and source != project_path and source.exists():
            if target.exists():
                raise FileExistsError(str(target))
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
    item["path"] = relative.as_posix()


def archive_graph_file(project_file: str | Path, item: dict) -> None:
    value = str(item.get("path", "")).strip()
    if not value:
        return
    source = safe_graph_path(Path(project_file).resolve().parent, value)
    if source == Path(project_file).resolve() or not source.exists():
        return
    archived = source.with_name(f"{source.name}.deleted.bak")
    archived.unlink(missing_ok=True)
    source.rename(archived)


def delete_script_file(project_file: str | Path, item: dict) -> None:
    relative = _stored_path(item)
    if relative is None:
        return
    target = safe_script_path(Path(project_file).resolve().parent, relative)
    target.unlink(missing_ok=True)


def _hydrate_item(target: Path, item: dict) -> None:
    raw = target.read_bytes()
    try:
        encoding, _ = detect_encoding(BytesIO(raw).readline)
        content = raw.decode(encoding)
    except (LookupError, UnicodeError, SyntaxError) as error:
        raise UnicodeError(f"Encodage Python illisible pour {target.name}: {error}") from error
    item.update({
        "content": content,
        "encoding": encoding,
        "newline": _detect_newline(raw),
        "content_hash": _digest(raw),
        "disk_mtime_ns": target.stat().st_mtime_ns,
    })


def _collect_files(
    node: dict, parent: PurePosixPath, result: dict[str, Path], kind: str, suffix: str,
) -> None:
    for child in node.get("children", []):
        child_kind = child.get("kind")
        name = str(child.get("name", "")).strip()
        if child_kind == "folder":
            _collect_files(child, parent / name, result, kind, suffix)
        elif child_kind == kind and child.get("id") and name.lower().endswith(suffix):
            result[str(child["id"])] = Path(*(parent / name).parts)


def _find_node(node: dict, item_id: str) -> dict | None:
    if node.get("id") == item_id:
        return node
    for child in node.get("children", []):
        found = _find_node(child, item_id)
        if found:
            return found
    return None


def _stored_path(item: dict) -> Path | None:
    value = str(item.get("path") or item.get("name") or "").strip()
    return Path(value) if value else None


def _safe_project_path(root: Path, relative: str | Path, suffix: str, label: str) -> Path:
    value = PurePosixPath(str(relative).replace("\\", "/"))
    if value.is_absolute() or ".." in value.parts or value.suffix.lower() != suffix:
        raise ValueError(f"Chemin de {label} invalide : {relative}")
    target = (root / Path(*value.parts)).resolve()
    target.relative_to(root.resolve())
    return target


def _detect_newline(raw: bytes) -> str:
    first_lf = raw.find(b"\n")
    first_cr = raw.find(b"\r")
    if first_cr >= 0 and (first_lf < 0 or first_cr < first_lf):
        return "\r\n" if raw[first_cr:first_cr + 2] == b"\r\n" else "\r"
    return "\n"


def _with_newlines(content: str, newline: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return normalized if newline == "\n" else normalized.replace("\n", newline)


def _digest(content: bytes) -> str:
    return sha256(content).hexdigest()
