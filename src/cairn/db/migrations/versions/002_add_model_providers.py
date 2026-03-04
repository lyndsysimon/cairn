"""Add model_providers table

Revision ID: 002
Revises: 001
Create Date: 2026-03-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_providers",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("provider_type", sa.String(100), nullable=False),
        sa.Column("api_base_url", sa.Text, nullable=True),
        sa.Column("api_key_credential_id", sa.String(255), nullable=True),
        sa.Column("models", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_model_providers_provider_type", "model_providers", ["provider_type"])
    op.create_index("idx_model_providers_is_enabled", "model_providers", ["is_enabled"])


def downgrade() -> None:
    op.drop_table("model_providers")
