from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def atomic_write_bytes(path: str | Path, content: bytes, *, backup: bool = True) -> Path:
    """Write a file completely, then replace its destination in one operation."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="wb", dir=target.parent, prefix=f".{target.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if backup and target.is_file():
            backup_path = target.with_name(f"{target.name}.bak")
            _replace_copy(target, backup_path)
        os.replace(temporary, target)
        temporary = None
        _sync_directory(target.parent)
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_write_text(
    path: str | Path, content: str, *, encoding: str = "utf-8", backup: bool = True,
) -> Path:
    return atomic_write_bytes(path, content.encode(encoding), backup=backup)


def _replace_copy(source: Path, destination: Path) -> None:
    temporary: Path | None = None
    try:
        with source.open("rb") as input_stream, NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=f".{destination.name}.",
            suffix=".tmp", delete=False,
        ) as output_stream:
            temporary = Path(output_stream.name)
            while chunk := input_stream.read(1024 * 1024):
                output_stream.write(chunk)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _sync_directory(folder: Path) -> None:
    if os.name == "nt":
        return
    try:
        descriptor = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        try:
            os.fsync(descriptor)
        except OSError:
            pass
    finally:
        os.close(descriptor)
