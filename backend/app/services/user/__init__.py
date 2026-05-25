"""User bounded context (DDD Wave 9, 2026-05-05).

Houses user identity / alias / merge concerns separate from AuthService.

Public API:
    .alias — expand_user_alias / list_canonical_only / detect_potential_aliases / merge_alias
"""
from .alias import (  # noqa: F401
    expand_user_alias,
    list_canonical_only,
    detect_potential_aliases,
    merge_alias,
)
