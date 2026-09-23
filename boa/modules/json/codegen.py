from boa.modules.json.helpers import HELPERS


def expression(block: dict, port: str, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    mode = str(cfg.get("mode", ""))
    a = lambda name, default="None": input_expr(name, default)
    empty = "''"
    if key == "json_convert":
        if mode == "text_to_data": return f"json.loads({a('value', empty)})"
        if mode == "data_to_text": return f"json.dumps({a('value')}, indent={int(cfg.get('indent', 2) or 0)}, sort_keys={bool(cfg.get('sort_keys'))}, ensure_ascii={bool(cfg.get('ensure_ascii'))})"
        return "None"
    data, item_key = a("data", "{}"), a("key")
    if mode == "get": return f"({data}.get({item_key}) if hasattr({data}, 'get') else None)"
    if mode == "set": return f"({{**dict({data}), {item_key}: {a('value')}}})"
    if mode == "delete": return f"({{k: v for k, v in dict({data}).items() if k != {item_key}}})"
    return "None"


def flow(block: dict, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    a = lambda name, default="None": input_expr(name, default)
    path = repr(str(cfg.get("file_path") or ""))
    if key == "json_read": return f"__boa_json_read({a('path', path)}, {_encoding(cfg)!r})"
    return f"__boa_json_write({a('path', path)}, {a('data')}, {_encoding(cfg)!r}, {int(cfg.get('indent',2) or 0)}, {bool(cfg.get('sort_keys'))}, {bool(cfg.get('ensure_ascii'))}, {bool(cfg.get('create_parents', True))})"


def _encoding(cfg: dict) -> str:
    value = str(cfg.get("encoding") or "utf8")
    return {"utf8": "utf-8", "utf8_bom": "utf-8-sig", "ascii": "ascii", "latin1": "latin-1", "cp1252": "cp1252"}.get(value, "utf-8")


BLOCK_HELPERS = {"json_read": {"json_file"}, "json_write": {"json_file"}}
