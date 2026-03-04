"""Add security_middlewares column to agents table

Revision ID: 002
Revises: 001
Create Date: 2026-03-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("security_middlewares", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("agents", "security_middlewares")
