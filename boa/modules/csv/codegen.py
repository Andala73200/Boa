from boa.modules.csv.helpers import HELPERS


def expression(block: dict, port: str, input_expr) -> str:
    cfg = dict(block.get("module_config", {}) or {})
    mode = str(cfg.get("mode", ""))
    a = lambda name, default="None": input_expr(name, default)
    delimiter = repr(_delimiter(cfg))
    empty = "''"
    if mode == "text_to_data": return f"__boa_csv_from_text({a('value', empty)}, {delimiter}, {bool(cfg.get('has_header'))}, {bool(cfg.get('auto_types'))})[0]"
    if mode == "data_to_text": return f"__boa_csv_to_text({a('value','[]')}, {delimiter}, {bool(cfg.get('has_header'))})"
    return "None"


def flow(block: dict, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    a = lambda name, default="None": input_expr(name, default)
    path = repr(str(cfg.get("file_path") or ""))
    if key == "csv_read": return f"__boa_csv_read({a('path', path)}, {_delimiter(cfg)!r}, {_encoding(cfg)!r}, {bool(cfg.get('has_header', True))}, {bool(cfg.get('auto_types'))})"
    append = key == "csv_append"
    create = bool(cfg.get("write_header_if_empty", True)) if append else bool(cfg.get("create_parents", True))
    return f"__boa_csv_write({a('path', path)}, {a('rows','[]')}, {_delimiter(cfg)!r}, {_encoding(cfg, bool(cfg.get('excel_compatible')))!r}, {bool(cfg.get('has_header', True))}, {append}, {create})"


def _delimiter(cfg: dict) -> str:
    value = str(cfg.get("separator") or "semicolon")
    return {"semicolon": ";", "comma": ",", "tab": "\t", "custom": str(cfg.get("custom_separator") or ";")[:1], "auto": ""}.get(value, ";")


def _encoding(cfg: dict, excel: bool = False) -> str:
    if excel: return "utf-8-sig"
    value = str(cfg.get("encoding") or "utf8")
    return {"utf8": "utf-8", "utf8_bom": "utf-8-sig", "ascii": "ascii", "latin1": "latin-1", "cp1252": "cp1252"}.get(value, "utf-8")


BLOCK_HELPERS = {
    "csv_convert": {"csv_memory", "scalar"},
    "csv_read": {"csv_file", "csv_memory", "scalar"},
    "csv_write": {"csv_file"},
    "csv_append": {"csv_file"},
}
