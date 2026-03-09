"""Add tools and agent_tools tables.

Revision ID: 006
Revises: 005
Create Date: 2026-03-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Tools table
    op.create_table(
        "tools",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_sandbox_safe", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "parameters_schema", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
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

    # Agent-tool junction table
    op.create_table(
        "agent_tools",
        sa.Column(
            "agent_id",
            UUID,
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tool_id",
            UUID,
            sa.ForeignKey("tools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("agent_id", "tool_id"),
    )
    op.create_index("ix_agent_tools_agent_id", "agent_tools", ["agent_id"])
    op.create_index("ix_agent_tools_tool_id", "agent_tools", ["tool_id"])

    # Seed built-in bash tool
    bash_schema = (
        '{"type": "object",'
        ' "properties": {"command": {"type": "string",'
        ' "description": "The bash command to execute"}},'
        ' "required": ["command"]}'
    )
    op.execute(
        f"""
        INSERT INTO tools (
            id, name, display_name, description,
            is_enabled, is_builtin, is_sandbox_safe,
            parameters_schema, created_at, updated_at
        ) VALUES (
            gen_random_uuid(),
            'bash',
            'Bash Command',
            'Execute a bash command in the agent runtime.',
            true, true, true,
            '{bash_schema}'::jsonb,
            now(), now()
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_agent_tools_tool_id", table_name="agent_tools")
    op.drop_index("ix_agent_tools_agent_id", table_name="agent_tools")
    op.drop_table("agent_tools")
    op.drop_table("tools")
