"""Add CheckConstraint on memory_rebuild_runs.rebuild_scope.

Enforce that rebuild_scope is one of 'full' or 'entity' (Option B from the
production hardening plan).  The 'snapshot' scope was never consumed by the
NLP pipeline and the enqueue site has been removed from snapshot_writer.py.

Revision ID: 20260505_0001
Revises: 20260504_0011
Create Date: 2026-05-05 00:01:00.000000
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260505_0001"
down_revision = "20260504_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_memory_rebuild_scope_valid",
        "memory_rebuild_runs",
        "rebuild_scope IN ('full', 'entity')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_memory_rebuild_scope_valid",
        "memory_rebuild_runs",
        type_="check",
    )
