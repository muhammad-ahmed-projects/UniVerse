"""account requests: users.is_pending, users.password_reset_requested_at

Revision ID: d5e3f9a2b4c6
Revises: c4d2e8f1a9b3
Create Date: 2026-11-18 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5e3f9a2b4c6"
down_revision: str | Sequence[str] | None = "c4d2e8f1a9b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_pending", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("users", sa.Column("password_reset_requested_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_reset_requested_at")
    op.drop_column("users", "is_pending")
