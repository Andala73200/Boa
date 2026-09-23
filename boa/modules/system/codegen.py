from boa.modules.system.helpers import HELPERS


def expression(block: dict, port: str, input_expr) -> str:
    return {"system": "platform.system()", "release": "platform.release()", "machine": "platform.machine()", "python": "platform.python_version()"}.get(port, "None")


def flow(block: dict, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    a = lambda name, default="None": input_expr(name, default)
    path = lambda field: repr(str(cfg.get(field) or ""))
    empty = "''"
    if key == "environment_variable": return f"__boa_environment({str(cfg.get('mode') or '')!r}, {a('name', empty)}, {a('value', empty)})"
    if key == "run_program": return f"__boa_run_program({a('program', path('program_path'))}, {a('arguments','[]')}, {a('input_text', empty)}, {int(cfg.get('timeout', 0) or 0)}, {bool(cfg.get('hide_window', True))})"
    return f"__boa_open_external({str(cfg.get('mode') or '')!r}, {a('target', path('target_path'))})"


BLOCK_HELPERS = {key: {"system"} for key in ("environment_variable", "run_program", "open_external")}
