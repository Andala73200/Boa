from boa.modules.archive import codegen as archive
from boa.modules.collections import codegen as collections
from boa.modules.csv import codegen as csv
from boa.modules.datetime import codegen as datetime
from boa.modules.json import codegen as json
from boa.modules.path import codegen as path
from boa.modules.random import codegen as random
from boa.modules.security import codegen as security
from boa.modules.statistics import codegen as statistics
from boa.modules.system import codegen as system
from boa.modules.text import codegen as text
from boa.modules.types import codegen as types
from boa.modules.spec_registry import COMMON_SPEC_GROUPS


CODEGEN_MODULES = {
    "random": random,
    "datetime": datetime,
    "path": path,
    "system": system,
    "json": json,
    "csv": csv,
    "collections": collections,
    "text": text,
    "types": types,
    "statistics": statistics,
    "security": security,
    "archive": archive,
}

EXPRESSION_HANDLERS = {
    key: CODEGEN_MODULES[module_name].expression
    for module_name, specs in COMMON_SPEC_GROUPS.items()
    for key in specs
}

FLOW_HANDLERS = {
    key: CODEGEN_MODULES[module_name].flow
    for module_name, specs in COMMON_SPEC_GROUPS.items()
    if hasattr(CODEGEN_MODULES[module_name], "flow")
    for key, spec in specs.items()
    if spec.flow
}

BLOCK_HELPERS = {
    key: names
    for module in CODEGEN_MODULES.values()
    for key, names in module.BLOCK_HELPERS.items()
}

HELPERS = {
    key: source
    for module in CODEGEN_MODULES.values()
    for key, source in module.HELPERS.items()
}
