"""Admin actor identity for audit logging.

AdminActor encapsulates the identity of the principal performing an admin
action. It is designed so that raw secret tokens are NEVER used as actor
identity and never appear in audit logs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AdminRole = Literal["viewer", "reviewer", "source_admin", "system_admin"]


@dataclass(frozen=True)
class AdminActor:
    """Stable, non-secret identity for an authenticated admin principal.

    actor_id should be a stable, human-readable label such as
    "shared-admin-token" — never the raw token value.
    """

    actor_id: str        # stable, non-secret label e.g. "shared-admin-token"
    actor_type: str      # "shared_token", "user", "service"
    role: AdminRole
    auth_method: str     # "shared_token", "jwt", "api_key"
    display_name: str | None = None
    email: str | None = None
