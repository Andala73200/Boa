from boa.modules.archive.helpers import HELPERS


def expression(block: dict, port: str, input_expr) -> str:
    cfg = dict(block.get("module_config", {}) or {})
    mode = str(cfg.get("mode", "")); fmt = str(cfg.get("format") or "")
    a = lambda name, default="None": input_expr(name, default)
    value = a("value", "b''"); level = max(0, min(9, int(cfg.get("compression_level", 6) or 6)))
    calls = {
        ("compress", "zlib"): f"zlib.compress({value}, level={level})", ("decompress", "zlib"): f"zlib.decompress({value})",
        ("compress", "gzip"): f"gzip.compress({value}, compresslevel={level})", ("decompress", "gzip"): f"gzip.decompress({value})",
        ("compress", "bzip2"): f"bz2.compress({value}, compresslevel={max(1, level)})", ("decompress", "bzip2"): f"bz2.decompress({value})",
        ("compress", "lzma"): f"lzma.compress({value}, preset={level})", ("decompress", "lzma"): f"lzma.decompress({value})",
    }
    return calls.get((mode, fmt), "None")


def flow(block: dict, input_expr) -> str:
    key = str(block.get("key", "")); cfg = dict(block.get("module_config", {}) or {})
    a = lambda name, default="None": input_expr(name, default)
    path = lambda field: repr(str(cfg.get(field) or "")); empty = "''"
    if key == "archive_create": return f"__boa_archive_create({str(cfg.get('mode') or '')!r}, {str(cfg.get('format') or '')!r}, {a('source', path('source_path'))}, {a('destination', path('destination_path'))}, {str(cfg.get('existing') or 'refuse')!r}, {bool(cfg.get('keep_root', True))}, {int(cfg.get('compression_level',6) or 6)})"
    if key == "archive_extract": return f"__boa_archive_extract({str(cfg.get('format') or 'auto')!r}, {str(cfg.get('mode') or '')!r}, {a('archive', path('archive_path'))}, {a('destination', path('destination_path'))}, {a('selection', repr(cfg.get('selection') or []))}, {str(cfg.get('existing') or 'refuse')!r})"
    if key == "archive_inspect": return f"__boa_archive_inspect({a('archive', path('archive_path'))}, {bool(cfg.get('verify_integrity'))})"
    if key == "archive_modify_zip": return f"__boa_zip_modify({str(cfg.get('mode') or '')!r}, {a('archive', path('archive_path'))}, {a('source', path('source_path'))}, {a('member', empty)}, {a('new_member', empty)})"
    return f"__boa_compress_file({str(cfg.get('mode') or '')!r}, {str(cfg.get('format') or '')!r}, {a('source', path('source_path'))}, {a('destination', path('destination_path'))}, {int(cfg.get('compression_level',6) or 6)})"


BLOCK_HELPERS = {key: {"archive"} for key in ("archive_create", "archive_extract", "archive_inspect", "archive_modify_zip", "compress_file")}
