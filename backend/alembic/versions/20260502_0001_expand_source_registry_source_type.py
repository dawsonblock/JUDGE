"""Expand source_registry.source_type length.

Revision ID: 20260502_0001
Revises: 20260501_0008
Create Date: 2026-05-02
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260502_0001"
down_revision: Union[str, None] = "20260501_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("source_registry") as batch_op:
        batch_op.alter_column(
            "source_type",
            existing_type=sa.String(length=20),
            type_=sa.String(length=80),
            existing_nullable=False,
            existing_server_default="unknown",
        )


def downgrade() -> None:
    with op.batch_alter_table("source_registry") as batch_op:
        batch_op.alter_column(
            "source_type",
            existing_type=sa.String(length=80),
            type_=sa.String(length=20),
            existing_nullable=False,
            existing_server_default="unknown",
        )
