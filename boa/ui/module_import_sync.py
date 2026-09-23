from boa.core.project_environment import import_bindings
from boa.runtime.module_codegen import graph_used_modules


MODULE_IMPORT_SOURCE = "module_blocks"


def sync_project_module_imports(panel, graphs: dict) -> bool:
    required = set()
    for item in graphs.values():
        required.update(graph_used_modules(item.get("graph", {}) or {}))
    imports = panel.to_data().get("imports", [])
    obsolete = [
        index for index, item in enumerate(imports)
        if item.get("source") == MODULE_IMPORT_SOURCE and item.get("module") not in required
    ]
    was_loading = panel._loading
    panel._loading = True
    for row in reversed(obsolete):
        panel.import_table.removeRow(row)
    statements = [
        item.get("statement", "") for item in panel.to_data().get("imports", [])
    ]
    bindings = import_bindings(statements)
    added = False
    for module in sorted(required):
        if module in bindings:
            continue
        panel.add_import(module, f"import {module}", "auto", MODULE_IMPORT_SOURCE)
        bindings[module] = module
        added = True
    panel._loading = was_loading
    return bool(obsolete) or added
