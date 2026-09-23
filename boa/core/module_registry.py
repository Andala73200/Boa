from boa.modules.spec_registry import (
    ALL_MODULE_SPECS,
    COMMON_SPECS,
    FEATURED_MATH_KEYS,
    LEGACY_RANDOM_SPECS,
    MATH_SPECS,
)


RANDOM_SPECS = LEGACY_RANDOM_SPECS
MODULE_SPECS = ALL_MODULE_SPECS
MODULE_BLOCK_KEYS = set(MODULE_SPECS)
FEATURED_MODULE_KEYS = FEATURED_MATH_KEYS | {"random_number", "random_collection"}
MODULE_CATEGORIES = {
    "math": "Math", "random": "Random", "datetime": "DateTime", "path": "Path",
    "system": "System", "json": "JSON", "csv": "CSV", "collections": "Collections",
    "text": "Text", "types": "Types", "statistics": "Statistics",
    "security": "Security", "archive": "Archive",
}
MODULE_ORDER = tuple(MODULE_CATEGORIES)


def module_for_block(block_key: str) -> str:
    spec = MODULE_SPECS.get(block_key)
    return str(getattr(spec, "module", "")) if spec else ""


def imports_for_block(block_key: str) -> tuple[str, ...]:
    spec = MODULE_SPECS.get(block_key)
    if not spec:
        return ()
    imports = tuple(getattr(spec, "imports", ()) or ())
    if imports:
        return imports
    return (str(spec.module),) if spec.module in {"math", "random"} else ()
