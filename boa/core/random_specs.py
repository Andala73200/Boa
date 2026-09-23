"""Façade de compatibilité des anciens blocs Random."""

from boa.modules.random.legacy_specs import LEGACY_SPECS as RANDOM_SPECS

RANDOM_BLOCK_KEYS = set(RANDOM_SPECS)

__all__ = ["RANDOM_BLOCK_KEYS", "RANDOM_SPECS"]
