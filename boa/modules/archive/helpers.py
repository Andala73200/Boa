HELPERS = {
"archive": r'''
def __boa_archive_create(mode, archive_format, source, destination, existing="refuse", keep_root=True, level=6):
    destination = pathlib.Path(destination)
    if destination.exists() and existing == "refuse": raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sources = [pathlib.Path(source)] if mode == "folder" else [pathlib.Path(item) for item in source]
    if archive_format == "zip":
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=max(0, min(9, level))) as archive:
            for item in sources:
                if item.is_dir():
                    base = item.parent if keep_root else item
                    for child in item.rglob("*"):
                        if child.is_file(): archive.write(child, child.relative_to(base))
                else: archive.write(item, item.name)
    else:
        modes = {"tar": "w", "tar_gz": "w:gz", "tar_bz2": "w:bz2", "tar_xz": "w:xz"}
        with tarfile.open(destination, modes[archive_format]) as archive:
            for item in sources: archive.add(item, arcname=item.name if keep_root else ".")
    return str(destination)

def __boa_safe_member(destination, name):
    root = pathlib.Path(destination).resolve(); target = (root / name).resolve()
    if root != target and root not in target.parents: raise ValueError(f"Unsafe archive path: {name}")

def __boa_archive_extract(archive_format, mode, archive_path, destination, selection=None, existing="refuse"):
    archive_path, destination = pathlib.Path(archive_path), pathlib.Path(destination); destination.mkdir(parents=True, exist_ok=True)
    if isinstance(selection, str):
        selection = [item.strip() for item in selection.replace("\n", ",").split(",") if item.strip()]
    is_zip = archive_format == "zip" or (archive_format == "auto" and zipfile.is_zipfile(archive_path)); wanted = set(selection or [])
    extracted = []
    if is_zip:
        with zipfile.ZipFile(archive_path) as archive:
            members = [m for m in archive.infolist() if mode != "extract_selection" or m.filename in wanted]
            for member in members:
                __boa_safe_member(destination, member.filename); target = destination / member.filename
                if target.exists() and existing == "refuse": raise FileExistsError(target)
                if target.exists() and existing == "ignore": continue
                archive.extract(member, destination); extracted.append(member.filename)
    else:
        with tarfile.open(archive_path, "r:*") as archive:
            members = [m for m in archive.getmembers() if mode != "extract_selection" or m.name in wanted]
            for member in members: __boa_safe_member(destination, member.name)
            archive.extractall(destination, members=members, filter="data"); extracted = [m.name for m in members]
    return str(destination), extracted

def __boa_archive_inspect(archive_path, verify=False):
    path = pathlib.Path(archive_path); items=[]; compressed=path.stat().st_size; uncompressed=0; valid=True
    try:
        if zipfile.is_zipfile(path):
            kind="zip"
            with zipfile.ZipFile(path) as archive:
                infos=archive.infolist(); items=[i.filename for i in infos]; uncompressed=sum(i.file_size for i in infos); valid=archive.testzip() is None if verify else True
        else:
            kind="tar"
            with tarfile.open(path, "r:*") as archive: infos=archive.getmembers(); items=[i.name for i in infos]; uncompressed=sum(i.size for i in infos)
    except (OSError, tarfile.TarError, zipfile.BadZipFile): kind="unknown"; valid=False
    return kind, items, len(items), compressed, uncompressed, valid

def __boa_zip_modify(mode, archive_path, source="", member="", new_member=""):
    path = pathlib.Path(archive_path)
    if mode == "add":
        with zipfile.ZipFile(path, "a", zipfile.ZIP_DEFLATED) as archive: archive.write(source, member or pathlib.Path(source).name)
        return str(path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp: temp_path = pathlib.Path(temp.name)
    try:
        with zipfile.ZipFile(path) as old, zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as new:
            for info in old.infolist():
                if info.filename == member:
                    if mode == "delete": continue
                    if mode == "replace": continue
                    if mode == "rename": info.filename = new_member
                new.writestr(info, old.read(info.filename if mode != "rename" or info.filename != new_member else member))
            if mode == "replace": new.write(source, member)
        shutil.move(temp_path, path)
    finally:
        if temp_path.exists(): temp_path.unlink()
    return str(path)

def __boa_compress_file(mode, archive_format, source, destination, level=6):
    modules = {"gzip": gzip, "bzip2": bz2, "xz": lzma}; module = modules[archive_format]
    if mode == "compress":
        target = module.open(destination, "wb", preset=max(0, min(9, level))) if archive_format == "xz" else module.open(destination, "wb", compresslevel=max(1, min(9, level)))
        with pathlib.Path(source).open("rb") as src, target as dst: shutil.copyfileobj(src, dst)
    else:
        with module.open(source, "rb") as src, pathlib.Path(destination).open("wb") as dst: shutil.copyfileobj(src, dst)
    return str(destination)
''',
}

