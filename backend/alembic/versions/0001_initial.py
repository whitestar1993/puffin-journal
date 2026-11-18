"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-17
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("archived", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )
    op.create_index("ix_tags_user_id", "tags", ["user_id"])
    op.create_table(
        "prompts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.String(200), nullable=False),
        sa.Column("quick_answers", sa.JSON, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_prompts_user_id", "prompts", ["user_id"])
    op.create_table(
        "entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("mood", sa.Integer, nullable=False),
        sa.Column("energy", sa.Integer, nullable=True),
        sa.Column("sleep", sa.Integer, nullable=True),
        sa.Column("prompt_id", sa.Integer, sa.ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("prompt_text", sa.String(200), nullable=True),
        sa.Column("prompt_answer", sa.Text, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_entries_user_date"),
        sa.CheckConstraint("mood BETWEEN 1 AND 5", name="ck_entries_mood"),
        sa.CheckConstraint("energy IS NULL OR energy BETWEEN 1 AND 5", name="ck_entries_energy"),
        sa.CheckConstraint("sleep IS NULL OR sleep BETWEEN 1 AND 5", name="ck_entries_sleep"),
    )
    op.create_index("ix_entries_user_id", "entries", ["user_id"])
    op.create_table(
        "entry_tags",
        sa.Column("entry_id", sa.Integer, sa.ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_entry_tags_tag_id", "entry_tags", ["tag_id"])


def downgrade() -> None:
    op.drop_table("entry_tags")
    op.drop_table("entries")
    op.drop_table("prompts")
    op.drop_table("tags")
    op.drop_table("users")
