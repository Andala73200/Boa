from boa.modules.archive.specs import SPECS as ARCHIVE_SPECS
from boa.modules.collections.specs import SPECS as COLLECTION_SPECS
from boa.modules.csv.specs import SPECS as CSV_SPECS
from boa.modules.datetime.specs import SPECS as DATETIME_SPECS
from boa.modules.json.specs import SPECS as JSON_SPECS
from boa.modules.math.specs import FEATURED_MATH_KEYS, MATH_SPECS
from boa.modules.path.specs import SPECS as PATH_SPECS
from boa.modules.random.legacy_specs import LEGACY_SPECS as LEGACY_RANDOM_SPECS
from boa.modules.random.specs import SPECS as RANDOM_SPECS
from boa.modules.security.specs import SPECS as SECURITY_SPECS
from boa.modules.statistics.specs import SPECS as STATISTICS_SPECS
from boa.modules.system.specs import SPECS as SYSTEM_SPECS
from boa.modules.text.specs import SPECS as TEXT_SPECS
from boa.modules.types.specs import SPECS as TYPE_SPECS


COMMON_SPEC_GROUPS = {
    "random": RANDOM_SPECS,
    "datetime": DATETIME_SPECS,
    "path": PATH_SPECS,
    "system": SYSTEM_SPECS,
    "json": JSON_SPECS,
    "csv": CSV_SPECS,
    "collections": COLLECTION_SPECS,
    "text": TEXT_SPECS,
    "types": TYPE_SPECS,
    "statistics": STATISTICS_SPECS,
    "security": SECURITY_SPECS,
    "archive": ARCHIVE_SPECS,
}

COMMON_SPECS = {
    key: spec
    for specs in COMMON_SPEC_GROUPS.values()
    for key, spec in specs.items()
}

ALL_MODULE_SPECS = {
    **MATH_SPECS,
    **LEGACY_RANDOM_SPECS,
    **COMMON_SPECS,
}
