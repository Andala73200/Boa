from boa.modules.path.helpers import HELPERS


def expression(block: dict, port: str, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    a = lambda name, default="None": input_expr(name, default)
    empty = "''"
    if key == "path_build":
        base = a("base", repr(str(cfg.get("base_path") or "")))
        return f"str(pathlib.Path({base}) / str({a('part', empty)}))"
    path = f"pathlib.Path({a('path', repr(str(cfg.get('target_path') or '')))})"
    if key == "path_info":
        return {"name": f"{path}.name", "stem": f"{path}.stem", "suffix": f"{path}.suffix", "parent": f"str({path}.parent)", "absolute": f"str({path}.resolve())"}.get(port, "None")
    return {"exists": f"{path}.exists()", "is_file": f"{path}.is_file()", "is_dir": f"{path}.is_dir()"}.get(port, "False")


def flow(block: dict, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    a = lambda name, default="None": input_expr(name, default)
    path = lambda field: repr(str(cfg.get(field) or ""))
    empty = "''"
    if key == "path_list": return f"__boa_list_folder({a('folder', path('folder_path'))}, {str(cfg.get('pattern') or '*')!r}, {bool(cfg.get('recursive'))})"
    if key == "path_create_folder": return f"__boa_create_folder({a('folder', path('folder_path'))}, {bool(cfg.get('exist_ok', True))})"
    if key == "path_copy": return f"__boa_copy_path({a('source', path('source_path'))}, {a('destination', path('destination_path'))}, {str(cfg.get('mode') or 'file')!r}, {str(cfg.get('existing') or 'refuse')!r})"
    if key == "path_move": return f"__boa_move_path({a('source', path('source_path'))}, {a('destination', path('destination_path'))}, {str(cfg.get('existing') or 'refuse')!r})"
    if key == "path_delete": return f"__boa_delete_path({a('path', path('target_path'))}, {str(cfg.get('mode') or 'file')!r}, {bool(cfg.get('ignore_missing'))})"
    return f"__boa_text_file({str(cfg.get('mode') or '')!r}, {a('path', path('file_path'))}, {a('text', empty)}, {_encoding(cfg)!r}, {bool(cfg.get('create_parents', True))})"


def _encoding(cfg: dict) -> str:
    value = str(cfg.get("encoding") or "utf8")
    return {"utf8": "utf-8", "utf8_bom": "utf-8-sig", "ascii": "ascii", "latin1": "latin-1", "cp1252": "cp1252"}.get(value, "utf-8")


BLOCK_HELPERS = {key: {"path"} for key in ("path_list", "path_create_folder", "path_copy", "path_move", "path_delete", "file_text")}
