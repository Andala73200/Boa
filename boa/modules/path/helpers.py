HELPERS = {
"path": r'''
def __boa_list_folder(folder, pattern="*", recursive=False):
    root = pathlib.Path(folder); items = [str(item) for item in (root.rglob(pattern) if recursive else root.glob(pattern))]; return items, len(items)

def __boa_create_folder(folder, exist_ok=True):
    path = pathlib.Path(folder); path.mkdir(parents=True, exist_ok=exist_ok); return str(path)

def __boa_copy_path(source, destination, mode="file", existing="refuse"):
    src, dst = pathlib.Path(source), pathlib.Path(destination)
    if dst.exists() and existing == "refuse": raise FileExistsError(dst)
    if mode == "folder": shutil.copytree(src, dst, dirs_exist_ok=existing == "replace")
    else: dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)
    return str(dst)

def __boa_move_path(source, destination, existing="refuse"):
    src, dst = pathlib.Path(source), pathlib.Path(destination)
    if dst.exists() and existing == "refuse": raise FileExistsError(dst)
    if dst.exists() and existing == "replace":
        shutil.rmtree(dst) if dst.is_dir() else dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True); return str(shutil.move(str(src), str(dst)))

def __boa_delete_path(path, mode="file", ignore_missing=False):
    target = pathlib.Path(path)
    if not target.exists():
        if ignore_missing: return False
        raise FileNotFoundError(target)
    if mode == "folder_tree": shutil.rmtree(target)
    elif mode == "empty_folder": target.rmdir()
    else: target.unlink()
    return True

def __boa_text_file(mode, path, text="", encoding="utf-8", create_parents=True):
    target = pathlib.Path(path)
    if mode == "read": return target.read_text(encoding=encoding)
    if create_parents: target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a" if mode == "append" else "w", encoding=encoding) as stream: stream.write(str(text))
    return str(target)
''',
}

